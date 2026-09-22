package org.shellground.learn;

import android.content.Context;
import org.shellground.runtime.PackVerifier;
import org.json.JSONObject;
import org.junit.*;
import org.junit.runner.RunWith;
import org.robolectric.*;
import org.robolectric.annotation.Config;
import java.io.*;
import java.nio.file.*;
import java.nio.file.attribute.FileTime;
import java.security.MessageDigest;
import java.util.*;
import static org.junit.Assert.*;

@RunWith(RobolectricTestRunner.class)
@Config(manifest=Config.NONE,sdk=35)
public class PackVerifierTest {
    private final Context context=RuntimeEnvironment.getApplication();
    private File pack;private JSONObject files;
    @Before public void setup()throws Exception{
        PackVerifier.invalidate(context);pack=Files.createTempDirectory(context.getFilesDir().toPath(),"pack-test-").toFile();files=new JSONObject();
        for(String name:new String[]{"base.qcow2","kernel","initrd"}){
            byte[] bytes=("fixture "+name).getBytes(java.nio.charset.StandardCharsets.UTF_8);Files.write(new File(pack,name).toPath(),bytes);
            StringBuilder hash=new StringBuilder();for(byte b:MessageDigest.getInstance("SHA-256").digest(bytes))hash.append(String.format(Locale.ROOT,"%02x",b&255));
            files.put(name,new JSONObject().put("size",bytes.length).put("sha256",hash.toString()));
        }
    }
    @After public void cleanup()throws Exception{PackVerifier.invalidate(context);for(File f:pack.listFiles()){f.setWritable(true);Files.delete(f.toPath());}Files.delete(pack.toPath());}
    @Test public void unchangedPrivatePackUsesReceiptAndInvalidationForcesHashes()throws Exception{
        assertTrue(PackVerifier.verify(context,pack,files,s->{}));assertFalse(PackVerifier.verify(context,pack,files,s->{}));
        PackVerifier.invalidate(context);assertTrue(PackVerifier.verify(context,pack,files,s->{}));
    }
    @Test public void sameLengthChangedImageCannotReuseReceipt()throws Exception{
        assertTrue(PackVerifier.verify(context,pack,files,s->{}));File image=new File(pack,"base.qcow2");assertTrue(image.setWritable(true));
        byte[] bytes=Files.readAllBytes(image.toPath());bytes[0]^=1;Files.write(image.toPath(),bytes);Files.setLastModifiedTime(image.toPath(),FileTime.fromMillis(System.currentTimeMillis()+5000));
        try{PackVerifier.verify(context,pack,files,s->{});fail("Changed image was accepted");}catch(IOException expected){assertTrue(expected.getMessage().contains("무결성"));}
    }
    @Test public void changedManifestDigestCannotReuseReceipt()throws Exception{
        assertTrue(PackVerifier.verify(context,pack,files,s->{}));files.getJSONObject("kernel").put("sha256","0".repeat(64));
        try{PackVerifier.verify(context,pack,files,s->{});fail("Changed manifest was accepted");}catch(IOException expected){assertTrue(expected.getMessage().contains("무결성"));}
    }
}
