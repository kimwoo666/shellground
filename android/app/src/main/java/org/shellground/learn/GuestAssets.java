package org.shellground.learn;

import android.util.Base64;
import org.json.*;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.util.*;

/** Verify bundled guest files first; don't retransmit unchanged source at boot. */
final class GuestAssets {
    static void sync(CondaGuest.Transport transport,Map<String,byte[]> files)throws Exception{
        JSONObject expected=new JSONObject();
        for(Map.Entry<String,byte[]> entry:files.entrySet()){
            if(!entry.getKey().matches("/opt/shellground/(notebook-assets/)?[a-zA-Z0-9_.]+"))throw new IOException("잘못된 채점 자료 경로");
            StringBuilder hash=new StringBuilder();for(byte b:MessageDigest.getInstance("SHA-256").digest(entry.getValue()))hash.append(String.format(Locale.ROOT,"%02x",b&255));
            expected.put(entry.getKey(),hash.toString());
        }
        String check="import sys,json,hashlib;from pathlib import Path;d=json.load(sys.stdin);print(json.dumps([n for n,h in d.items() if not Path(n).is_file() or hashlib.sha256(Path(n).read_bytes()).hexdigest()!=h]))";
        JSONArray missing=new JSONArray(exec(transport,check,new JSONArray(),expected.toString().getBytes(StandardCharsets.UTF_8)));
        for(int i=0;i<missing.length();i++){
            String name=missing.getString(i);byte[] data=files.get(name);if(data==null)throw new IOException("예상하지 않은 자료 응답");
            // The existing guest serial reader is byte-oriented. Bounded chunks
            // avoid sending large source files as one slow control transaction.
            for(int offset=0;offset<data.length;offset+=4096){
                String write="import sys;from pathlib import Path;p=Path(sys.argv[1]+'.new');f=p.open(sys.argv[2]);f.write(sys.stdin.buffer.read());f.close()";
                exec(transport,write,new JSONArray().put(name).put(offset==0?"wb":"ab"),Arrays.copyOfRange(data,offset,Math.min(data.length,offset+4096)));
            }
            String finish="import sys,hashlib;from pathlib import Path;p=Path(sys.argv[1]+'.new');assert hashlib.sha256(p.read_bytes()).hexdigest()==sys.argv[2];p.chmod(0o644);p.replace(sys.argv[1])";
            exec(transport,finish,new JSONArray().put(name).put(expected.getString(name)),null);
        }
    }
    private static String exec(CondaGuest.Transport transport,String script,JSONArray args,byte[] input)throws Exception{
        JSONArray argv=new JSONArray().put("/usr/bin/python3").put("-c").put(script);
        for(int i=0;i<args.length();i++)argv.put(args.get(i));
        // The guest's serial framing and first Python import are also part of
        // this transaction. Allow cold TCG startup, with an outer hard bound;
        // no UI thread waits here and stopOwned closes the channel immediately.
        JSONObject request=new JSONObject().put("root",true).put("cwd","/tmp").put("run_timeout",120).put("argv",argv);
        if(input!=null)request.put("input",Base64.encodeToString(input,Base64.NO_WRAP));
        try{
            JSONObject result=(JSONObject)transport.request("exec",request,150000);
            if(result.getInt("code")!=0)throw new IOException(NotebookGuest.decode(result,"err"));
            return NotebookGuest.decode(result,"out");
        }catch(Exception failure){throw new IOException("채점 자료 동기화 "+args+": "+failure.getMessage(),failure);}
    }
}
