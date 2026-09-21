package org.shellground.learn;

import com.hierynomus.smbj.share.DiskShare;
import java.nio.charset.StandardCharsets;
import java.util.UUID;
import org.json.JSONObject;

/** Optional integration probe. Private connection JSON arrives only on stdin.
 * Uses the existing profile, writes one valid empty device snapshot, reads it
 * back, then removes exactly that owned probe. Never prints account details.
 */
public final class SmbTransportCheck {
    public static void main(String[] args)throws Exception {
        JSONObject config=new JSONObject(new String(System.in.readAllBytes(),StandardCharsets.UTF_8));
        String id=UUID.randomUUID().toString().replace("-",""),name="device-"+id+".json";
        try(SmbProgressStore store=new SmbProgressStore(config)) {
            JSONObject marker=new JSONObject(store.read("shellground-profile.json"));
            if(marker.getInt("schema")!=1)throw new IllegalStateException("Profile format");
            int before=store.names().length;
            String snapshot=new JSONObject().put("schema",1).put("profile",marker.getString("profile"))
                .put("clock",new JSONObject().put(id,1)).put("records",new JSONObject()).toString();
            boolean attempted=false;
            try {
                attempted=true;store.write(name,snapshot);
                if(!store.read(name).equals(snapshot))throw new IllegalStateException("Roundtrip mismatch");
                store.write(name,snapshot); // Existing-file atomic replacement.
                if(!store.read(name).equals(snapshot))throw new IllegalStateException("Replacement mismatch");
            } finally {
                if(attempted){var field=SmbProgressStore.class.getDeclaredField("share");field.setAccessible(true);
                    DiskShare share=(DiskShare)field.get(store);
                    String path=config.getString("folder").replace('/','\\')+"\\"+name;
                    if(share.fileExists(path))share.rm(path);
                }
            }
            if(store.names().length!=before)throw new IllegalStateException("Probe cleanup mismatch");
            System.out.println("SMB signed connection, read, write, atomic replace, cleanup: PASS");
        }catch(Exception error){System.err.println("SMB probe failed: "+error.getClass().getSimpleName());System.exit(1);}
    }
}
