package org.shellground.learn;

import android.util.Base64;
import org.json.*;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.util.*;
import java.io.ByteArrayOutputStream;
import java.util.zip.DeflaterOutputStream;

/** Verify bundled guest files first; don't retransmit unchanged source at boot. */
final class GuestAssets {
    static void sync(CondaGuest.Transport transport,Map<String,byte[]> files)throws Exception{
        JSONObject expected=new JSONObject();
        for(Map.Entry<String,byte[]> entry:files.entrySet()){
            if(!entry.getKey().matches("/opt/shellground/(notebook-assets/)?[a-zA-Z0-9_.]+"))throw new IOException("잘못된 채점 자료 경로");
            if(entry.getValue().length>512*1024)throw new IOException("채점 자료 크기 제한 초과");
            StringBuilder hash=new StringBuilder();for(byte b:MessageDigest.getInstance("SHA-256").digest(entry.getValue()))hash.append(String.format(Locale.ROOT,"%02x",b&255));
            expected.put(entry.getKey(),hash.toString());
        }
        String check="import sys,json,hashlib;from pathlib import Path;d=json.load(sys.stdin);print(json.dumps([n for n,h in d.items() if not Path(n).is_file() or hashlib.sha256(Path(n).read_bytes()).hexdigest()!=h]))";
        JSONArray missing=new JSONArray(exec(transport,check,new JSONArray(),expected.toString().getBytes(StandardCharsets.UTF_8)));
        for(int i=0;i<missing.length();i++){
            String name=missing.getString(i);byte[] data=files.get(name);if(data==null)throw new IOException("예상하지 않은 자료 응답");
            // Compress before crossing the guest serial link. One Python process
            // per changed file replaces one process per 4 KB of source.
            ByteArrayOutputStream packed=new ByteArrayOutputStream();
            try(DeflaterOutputStream zip=new DeflaterOutputStream(packed)){zip.write(data);}
            exec(transport,INSTALL,new JSONArray().put(name).put(expected.getString(name)),packed.toByteArray());
        }
    }
    static final String INSTALL="""
        import sys,hashlib,zlib,tempfile,os
        from pathlib import Path
        target=Path(sys.argv[1])
        decoder=zlib.decompressobj()
        data=decoder.decompress(sys.stdin.buffer.read(600000),524289)
        if len(data)>524288 or not decoder.eof or decoder.unused_data or decoder.unconsumed_tail:
            raise ValueError('Invalid compressed teaching asset')
        if hashlib.sha256(data).hexdigest()!=sys.argv[2]:
            raise ValueError('Teaching asset checksum mismatch')
        temporary=None
        try:
            with tempfile.NamedTemporaryFile(dir=target.parent,prefix='.sg-asset-',delete=False) as output:
                temporary=Path(output.name)
                output.write(data)
            temporary.chmod(0o644)
            os.replace(temporary,target)
        finally:
            if temporary is not None: temporary.unlink(missing_ok=True)
        """;
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
