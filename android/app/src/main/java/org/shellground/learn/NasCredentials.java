package org.shellground.learn;

import android.content.Context;
import android.security.keystore.*;
import android.util.AtomicFile;
import java.io.*;
import java.security.KeyStore;
import java.nio.charset.StandardCharsets;
import javax.crypto.*;
import javax.crypto.spec.GCMParameterSpec;
import org.json.JSONObject;

/** Local-only connection details. Never exported with the learning snapshots. */
final class NasCredentials {
    private static final String ALIAS="shellground-nas-v1";
    private final AtomicFile file;
    NasCredentials(Context context){file=new AtomicFile(new File(context.getNoBackupFilesDir(),"nas-credentials-v1.enc"));}
    private SecretKey key()throws Exception{
        KeyStore store=KeyStore.getInstance("AndroidKeyStore");store.load(null);
        if(!store.containsAlias(ALIAS)){
            KeyGenerator generator=KeyGenerator.getInstance(KeyProperties.KEY_ALGORITHM_AES,"AndroidKeyStore");
            generator.init(new KeyGenParameterSpec.Builder(ALIAS,KeyProperties.PURPOSE_ENCRYPT|KeyProperties.PURPOSE_DECRYPT)
                .setBlockModes(KeyProperties.BLOCK_MODE_GCM).setEncryptionPaddings(KeyProperties.ENCRYPTION_PADDING_NONE).build());generator.generateKey();
        }
        return (SecretKey)store.getKey(ALIAS,null);
    }
    JSONObject load()throws Exception{
        if(!file.getBaseFile().exists())return new JSONObject();
        try(DataInputStream input=new DataInputStream(file.openRead())){
            int size=input.readUnsignedByte();if(size!=12)throw new IOException("잘못된 로컬 NAS 설정");
            byte[] iv=new byte[size];input.readFully(iv);
            ByteArrayOutputStream bytes=new ByteArrayOutputStream();byte[] buffer=new byte[4096];int count;
            while((count=input.read(buffer))!=-1){if(bytes.size()+count>16384)throw new IOException("설정 크기 제한");bytes.write(buffer,0,count);}
            Cipher cipher=Cipher.getInstance("AES/GCM/NoPadding");cipher.init(Cipher.DECRYPT_MODE,key(),new GCMParameterSpec(128,iv));
            return new JSONObject(new String(cipher.doFinal(bytes.toByteArray()),StandardCharsets.UTF_8));
        }
    }
    void save(JSONObject data)throws Exception{
        Cipher cipher=Cipher.getInstance("AES/GCM/NoPadding");cipher.init(Cipher.ENCRYPT_MODE,key());
        byte[] encrypted=cipher.doFinal(data.toString().getBytes(StandardCharsets.UTF_8));
        FileOutputStream stream=file.startWrite();
        try{stream.write(cipher.getIV().length);stream.write(cipher.getIV());stream.write(encrypted);file.finishWrite(stream);}
        catch(Exception error){file.failWrite(stream);throw error;}
    }
    void remove(){file.delete();}
}
