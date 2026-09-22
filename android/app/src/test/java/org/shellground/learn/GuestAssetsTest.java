package org.shellground.learn;

import android.util.Base64;
import org.json.*;
import org.junit.*;
import org.junit.rules.TemporaryFolder;
import org.junit.runner.RunWith;
import org.robolectric.RobolectricTestRunner;
import org.robolectric.annotation.Config;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.util.*;
import static org.junit.Assert.*;

/** Runs the shipped installer script against temporary files, not a guest VM. */
@RunWith(RobolectricTestRunner.class)
@Config(manifest=Config.NONE,sdk=35)
public class GuestAssetsTest {
    @Rule public TemporaryFolder temporary=new TemporaryFolder();
    private int calls;
    private JSONObject execute(String action,JSONObject payload,long timeout)throws Exception{
        calls++;JSONArray argv=payload.getJSONArray("argv");String script=argv.getString(2);
        byte[] input=Base64.decode(payload.optString("input"),Base64.DEFAULT);
        ArrayList<String> command=new ArrayList<>();String python=System.getenv("SHELLGROUND_BUILD_PYTHON");command.add(python==null?"python3":python);command.add("-c");command.add(script);
        if(argv.length()==3){JSONObject original=new JSONObject(new String(input,StandardCharsets.UTF_8)),mapped=new JSONObject();
            for(Iterator<String> it=original.keys();it.hasNext();){String name=it.next();mapped.put(path(name).toString(),original.get(name));}input=mapped.toString().getBytes(StandardCharsets.UTF_8);
        }else{command.add(path(argv.getString(3)).toString());command.add(argv.getString(4));}
        Process process=new ProcessBuilder(command).start();try(var stdin=process.getOutputStream()){stdin.write(input);}
        byte[] out=process.getInputStream().readAllBytes(),err=process.getErrorStream().readAllBytes();int code=process.waitFor();
        if(argv.length()==3&&code==0){JSONArray mapped=new JSONArray(new String(out,StandardCharsets.UTF_8)),names=new JSONArray();for(int i=0;i<mapped.length();i++)names.put("/opt/shellground/"+Paths.get(mapped.getString(i)).getFileName());out=names.toString().getBytes(StandardCharsets.UTF_8);}
        return new JSONObject().put("code",code).put("out",Base64.encodeToString(out,Base64.NO_WRAP)).put("err",Base64.encodeToString(err,Base64.NO_WRAP));
    }
    private Path path(String guest){return temporary.getRoot().toPath().resolve(Paths.get(guest).getFileName());}
    @Test public void changedSourceUsesOneInstallAndUnchangedSourceIsNotSent()throws Exception{
        String name="/opt/shellground/lab.py";byte[] source=("# actual teaching source\n".repeat(9000)).getBytes(StandardCharsets.UTF_8);
        GuestAssets.sync(this::execute,Map.of(name,source));assertArrayEquals(source,Files.readAllBytes(path(name)));assertEquals(2,calls);
        GuestAssets.sync(this::execute,Map.of(name,source));assertEquals(3,calls);
        source[5]='Z';GuestAssets.sync(this::execute,Map.of(name,source));assertArrayEquals(source,Files.readAllBytes(path(name)));assertEquals(5,calls);
        assertEquals(1,temporary.getRoot().list().length);
    }
    @Test public void emptySourceIsInstalledCorrectly()throws Exception{
        String name="/opt/shellground/bashrc";GuestAssets.sync(this::execute,Map.of(name,new byte[0]));assertTrue(Files.exists(path(name)));assertEquals(0,Files.size(path(name)));
    }
    @Test public void unapprovedPathIsRejectedBeforeTransport()throws Exception{
        try{GuestAssets.sync(this::execute,Map.of("/etc/profile",new byte[0]));fail();}catch(java.io.IOException expected){assertEquals(0,calls);}
    }
}
