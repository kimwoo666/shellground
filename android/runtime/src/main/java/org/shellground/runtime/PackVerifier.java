package org.shellground.runtime;

import android.content.Context;
import android.system.Os;
import android.system.StructStat;
import org.json.JSONObject;
import java.io.*;
import java.nio.file.Files;
import java.security.MessageDigest;
import java.util.Locale;
import java.util.function.Consumer;

/** Cache verification of read-only app-private images, never of external files. */
public final class PackVerifier {
    private static final String PREFS="linux-pack-verification-v1";
    private static final String[] NAMES={"base.qcow2","kernel","initrd"};
    private static String hash(File file)throws Exception{
        MessageDigest digest=MessageDigest.getInstance("SHA-256");
        try(InputStream input=new FileInputStream(file)){
            byte[] block=new byte[1024*1024];int count;
            while((count=input.read(block))!=-1){
                if(Thread.currentThread().isInterrupted())throw new InterruptedException("실습 시작 취소");
                digest.update(block,0,count);
            }
        }
        StringBuilder result=new StringBuilder();for(byte b:digest.digest())result.append(String.format(Locale.ROOT,"%02x",b&255));return result.toString();
    }
    private static String identity(Context context,File pack,JSONObject files)throws Exception{
        if(!pack.getCanonicalPath().startsWith(context.getFilesDir().getCanonicalPath()+File.separator))throw new IOException("앱 전용 실습 이미지 폴더가 아닙니다.");
        StringBuilder value=new StringBuilder("v1|").append(context.getPackageManager().getPackageInfo(context.getPackageName(),0).lastUpdateTime).append('|').append(pack.getCanonicalPath());
        for(String name:NAMES){
            File file=new File(pack,name);JSONObject expected=files.getJSONObject(name);
            if(!file.getCanonicalPath().equals(new File(pack.getCanonicalFile(),name).getAbsolutePath())||!file.isFile()||file.length()!=expected.getLong("size"))throw new IOException("실습 이미지 크기/경로 확인 실패: "+name);
            StructStat stat=Os.stat(file.getAbsolutePath());
            value.append('|').append(name).append(':').append(expected.getString("sha256")).append(':').append(stat.st_dev).append(':').append(stat.st_ino)
                .append(':').append(stat.st_size).append(':').append(stat.st_ctime).append(':').append(stat.st_mode)
                .append(':').append(Files.getLastModifiedTime(file.toPath()));
        }
        return value.toString();
    }
    /** Returns true only when all three hashes were read in this call. */
    public static boolean verify(Context context,File pack,JSONObject files,Consumer<String> stage)throws Exception{
        var receipt=context.getSharedPreferences(PREFS,Context.MODE_PRIVATE);
        String before=identity(context,pack,files);
        if(before.equals(receipt.getString("verified",""))){stage.accept("실습 이미지 확인 완료 · Linux 시작 중");return false;}
        receipt.edit().remove("verified").commit();
        for(String name:NAMES){
            stage.accept("실습 이미지 검사 중 · "+name);
            File file=new File(pack,name);
            if(!hash(file).equals(files.getJSONObject(name).getString("sha256")))throw new IOException("실습 이미지 무결성 확인 실패: "+name);
        }
        if(!before.equals(identity(context,pack,files)))throw new IOException("검사 중 실습 이미지가 변경되었습니다.");
        for(String name:NAMES)if(!new File(pack,name).setReadOnly())throw new IOException("실습 이미지를 읽기 전용으로 보호하지 못했습니다.");
        // If persistence fails, the next startup simply verifies again.
        receipt.edit().putString("verified",identity(context,pack,files)).commit();return true;
    }
    public static void invalidate(Context context){context.getSharedPreferences(PREFS,Context.MODE_PRIVATE).edit().remove("verified").commit();}
}
