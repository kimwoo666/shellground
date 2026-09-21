package org.shellground.learn;

import com.hierynomus.smbj.*;
import com.hierynomus.smbj.auth.AuthenticationContext;
import com.hierynomus.smbj.connection.Connection;
import com.hierynomus.smbj.session.Session;
import com.hierynomus.smbj.share.*;
import com.hierynomus.msdtyp.AccessMask;
import com.hierynomus.msfscc.FileAttributes;
import com.hierynomus.mssmb2.*;
import java.io.*;
import java.nio.charset.StandardCharsets;
import java.util.*;
import java.util.concurrent.TimeUnit;
import org.json.JSONObject;

/** Restricts NAS operations to tiny snapshots in an existing dedicated folder. */
public final class SmbProgressStore implements AutoCloseable {
    private final SMBClient client;
    private Connection connection;
    private Session session;
    private DiskShare share;
    private final String folder;
    private static final int LIMIT=4*1024*1024;
    private final long deadline=System.nanoTime()+TimeUnit.SECONDS.toNanos(20);
    private void budget()throws IOException{if(System.nanoTime()>deadline)throw new IOException("NAS 연결 시간 제한");}
    public SmbProgressStore(JSONObject config)throws Exception {
        folder=clean(config.getString("folder"));
        if(folder.isEmpty())throw new IOException("진도 전용 하위 폴더가 필요합니다.");
        String server=config.getString("server").trim(),shareName=config.getString("share").trim();
        if(server.isEmpty()||server.contains("/")||server.contains("\\")||shareName.isEmpty()||shareName.contains("/")||shareName.contains("\\"))throw new IOException("NAS 주소와 공유 이름을 확인하세요.");
        client=new SMBClient(SmbConfig.builder().withTimeout(6,TimeUnit.SECONDS)
            .withSoTimeout(6,TimeUnit.SECONDS).withSigningRequired(true).build());
        try{
            connection=client.connect(server);
            budget();
            char[] password=config.getString("password").toCharArray();
            try{session=connection.authenticate(new AuthenticationContext(config.getString("username"),password,config.optString("domain","")));}
            finally{Arrays.fill(password,'\0');}
            share=(DiskShare)session.connectShare(shareName);
            budget();
            if(!share.folderExists(folder))throw new IOException("진도 전용 폴더가 없습니다.");
        }catch(Exception error){close();throw error;}
    }
    private static String clean(String path)throws IOException{
        path=path.replace('/','\\');
        if(path.startsWith("\\")||path.endsWith("\\")||path.contains(":"))throw new IOException("공유 폴더 안의 상대 경로를 입력하세요.");
        for(String part:path.split("\\\\",-1))if(part.equals(".")||part.equals("..")||part.isEmpty())throw new IOException("잘못된 진도 폴더 경로입니다.");
        return path;
    }
    private String path(String name)throws IOException{
        budget();
        if(!name.equals("shellground-profile.json")&&!name.matches("device-[0-9a-f]{32}\\.json"))throw new IOException("허용되지 않은 진도 파일입니다.");
        return folder+"\\"+name;
    }
    public String read(String name)throws Exception{
        try(com.hierynomus.smbj.share.File file=share.openFile(path(name),EnumSet.of(AccessMask.FILE_READ_DATA),null,
                SMB2ShareAccess.ALL,SMB2CreateDisposition.FILE_OPEN,EnumSet.of(SMB2CreateOptions.FILE_NON_DIRECTORY_FILE));
            InputStream input=file.getInputStream();ByteArrayOutputStream bytes=new ByteArrayOutputStream()){
            byte[] buffer=new byte[8192];int count;
            while((count=input.read(buffer))!=-1){budget();if(bytes.size()+count>LIMIT)throw new IOException("진도 크기 제한");bytes.write(buffer,0,count);}
            return bytes.toString("UTF-8");
        }
    }
    public String[] names()throws Exception{
        budget();
        ArrayList<String> result=new ArrayList<>();
        for(var item:share.list(folder,"device-*.json")){
            budget();
            String name=item.getFileName();if(name.matches("device-[0-9a-f]{32}\\.json"))result.add(name);
            if(result.size()>64)throw new IOException("연결 기기 수 제한");
        }
        return result.toArray(new String[0]);
    }
    public void write(String name,String json)throws Exception{
        if(!name.matches("device-[0-9a-f]{32}\\.json"))throw new IOException("프로필 덮어쓰기는 허용되지 않습니다.");
        String destination=path(name),temporary=folder+"\\.shellground-"+UUID.randomUUID()+".tmp";
        byte[] bytes=json.getBytes(StandardCharsets.UTF_8);if(bytes.length>LIMIT)throw new IOException("진도 크기 제한");
        boolean moved=false;
        try{
            try(com.hierynomus.smbj.share.File file=share.openFile(temporary,
                    EnumSet.of(AccessMask.FILE_WRITE_DATA,AccessMask.DELETE),EnumSet.of(FileAttributes.FILE_ATTRIBUTE_NORMAL),
                    SMB2ShareAccess.ALL,SMB2CreateDisposition.FILE_CREATE,EnumSet.of(SMB2CreateOptions.FILE_NON_DIRECTORY_FILE))){
                if(file.write(bytes,0)!=bytes.length)throw new IOException("진도를 모두 전송하지 못했습니다.");
                file.flush();file.rename(destination,true);moved=true;
            }
        }finally{if(!moved)try{share.rm(temporary);}catch(Exception ignored){}}
    }
    @Override public void close(){
        try{if(share!=null)share.close();}catch(Exception ignored){}
        try{if(session!=null)session.close();}catch(Exception ignored){}
        try{if(connection!=null)connection.close();}catch(Exception ignored){}
        try{client.close();}catch(Exception ignored){}
    }
}
