package org.shellground.learn;

import android.app.Service;
import android.content.Intent;
import android.os.*;
import android.util.Base64;
import com.chaquo.python.Python;
import com.chaquo.python.PyObject;
import com.chaquo.python.android.AndroidPlatform;
import org.shellground.runtime.GuestMachine;
import org.json.*;
import java.io.*;
import java.util.*;
import java.util.concurrent.*;

/** Real guest lifecycle and PTYs in a separate process, never in the UI thread.
 * The bounded display queue applies back-pressure by stopping on overflow, not
 * by silently dropping terminal bytes. No polling timers run while idle.
 */
public final class LinuxService extends Service {
    public static final int REQUEST=21, RESULT=22, FRAME=23, EVENT=24;
    private final ThreadPoolExecutor worker=new ThreadPoolExecutor(1,1,0,TimeUnit.MILLISECONDS,
        new ArrayBlockingQueue<>(64));
    private final ThreadPoolExecutor display=new ThreadPoolExecutor(1,1,0,TimeUnit.MILLISECONDS,
        new ArrayBlockingQueue<>(64));
    private final Map<String,PyObject> terminals=new ConcurrentHashMap<>();
    private final Handler ui=new Handler(Looper.getMainLooper());
    private volatile GuestMachine machine;
    private volatile Messenger client;
    private volatile String selected="";
    private volatile boolean closing;
    private volatile int closedThrough;
    private int lastOpened;
    private JSONObject mission;
    private String course="linux",startDirectory;
    private CondaGuest conda;
    private volatile NotebookGuest notebook;
    private PyObject terminalModule;
    private int columns=80,rows=24;
    private final Messenger binder=new Messenger(new Handler(Looper.getMainLooper(),message->{
        if(message.what!=REQUEST)return false;
        final Messenger destination=message.replyTo;
        if(!closing)client=destination;
        final String raw=message.getData().getString("request","{}");final int id=message.arg1;
        try {
            JSONObject request=new JSONObject(raw);
            if("stop".equals(request.optString("action"))){stopOwned();return true;}
            if("notebook_interrupt".equals(request.optString("action"))){
                new Thread(()->{try{NotebookGuest n=notebook;if(n!=null)n.interrupt();reply(destination,EVENT,id,new JSONObject().put("interrupted",true));}
                    catch(Exception error){reply(destination,EVENT,id,error(error));}},"notebook-interrupt").start();return true;
            }
            if(closing){
                if("start".equals(request.optString("action"))){reply(destination,RESULT,id,new JSONObject().put("stopping",true));return true;}
                throw new IOException("Linux 종료 중입니다.");
            }
            worker.execute(()->{
                android.os.Process.setThreadPriority(android.os.Process.THREAD_PRIORITY_BACKGROUND);
                try {reply(destination,RESULT,id,dispatch(request));}
                catch(Exception error){reply(destination,RESULT,id,error(error));}
            });
        }catch(Exception error){reply(destination,RESULT,id,error(error));}
        return true;
    }));

    private JSONObject error(Exception error){
        try{return new JSONObject().put("ok",false).put("error",error.toString());}
        catch(JSONException impossible){return new JSONObject();}
    }
    private void reply(int what,int id,JSONObject result){
        reply(client,what,id,result);
    }
    private void reply(Messenger destination,int what,int id,JSONObject result){
        if(destination==null)return;
        Message message=Message.obtain(null,what);message.arg1=id;
        Bundle data=new Bundle();data.putString("result",result.toString());message.setData(data);
        try{destination.send(message);}catch(RemoteException ignored){}
    }
    private void sendKeys(String sid,String encoded)throws Exception{
        GuestMachine guest=machine;if(guest==null||closing)return;
        guest.channel().send(new JSONObject().put("action","input").put("session",sid).put("data",encoded));
    }
    private void startup(String message){
        try{reply(EVENT,0,new JSONObject().put("startup",message));}catch(JSONException ignored){}
    }
    private void paint(String sid,PyObject terminal)throws Exception{
        JSONObject frame=new JSONObject(terminal.callAttr("frame").toString());
        String response=frame.optString("reply");
        if(!response.isEmpty())sendKeys(sid,response);
        frame.remove("reply");frame.put("session",sid);
        if(sid.equals(selected))reply(FRAME,0,frame);
    }
    private void output(JSONObject event){
        if(closing||event.optInt("session",-1)<=closedThrough)return;
        try{display.execute(()->{
            try{
                String sid=event.getString("session");
                PyObject terminal=terminals.computeIfAbsent(sid,key->terminalModule.callAttr("Terminal",columns,rows));
                if(event.has("output"))terminal.callAttr("feed",event.getString("output"));
                if(event.optBoolean("ended"))reply(EVENT,0,new JSONObject().put("ended",sid));
                paint(sid,terminal);
            }catch(Exception failure){reply(EVENT,0,error(failure));}
        });}catch(RejectedExecutionException full){
            if(!closing){reply(EVENT,0,error(new IOException("출력이 처리 한도를 넘어 실습을 중단합니다.")));ui.post(this::stopOwned);}
        }
    }

    private JSONObject dispatch(JSONObject request)throws Exception{
        String action=request.getString("action");
        if("start".equals(action)){
            if(Build.VERSION.SDK_INT<28)throw new IOException("실제 Linux 실습은 Android 9 이상이 필요합니다.");
            String requested=request.optString("course","linux");
            if(!Arrays.asList("linux","conda","notebook").contains(requested))throw new IOException("지원하지 않는 과정입니다.");
            if(machine!=null&&!course.equals(requested))throw new IOException("실습을 종료한 뒤 다른 과정을 시작하세요.");
            if(machine==null){
                startup("터미널 실행기 준비 중");
                if(!Python.isStarted())Python.start(new AndroidPlatform(this));
                terminalModule=Python.getInstance().getModule("linux_terminal");
                File pack=new File(getFilesDir(),"training-pack-4.7.4");
                if(!new File(pack,"manifest.json").isFile())installBundledPack(pack);
                if(requested.equals("conda")||requested.equals("notebook")){
                    File info=new File(pack,"manifest.json");
                    if(info.length()>256*1024)throw new IOException("실습 이미지 정보가 너무 큽니다.");
                    JSONObject manifest=new JSONObject(new String(java.nio.file.Files.readAllBytes(info.toPath()),java.nio.charset.StandardCharsets.UTF_8));
                    if(!manifest.optBoolean(requested.equals("conda")?"conda_course":"notebook_course"))throw new IOException("이 실습 팩에 요청한 과정이 없습니다.");
                }
                GuestMachine owned=new GuestMachine();
                synchronized(this){
                    // stopOwned takes this same lock. Once closing is set,
                    // a slow Python import/asset copy cannot publish a new VM
                    // after the stopping thread has already captured its owner.
                    if(closing||Thread.currentThread().isInterrupted())throw new InterruptedException("Linux 시작 취소");
                    machine=owned;
                }
                try{
                    android.util.Log.i("ShellgroundLinux","Booting verified guest");
                    owned.boot(this,pack,this::output,this::startup);
                    android.util.Log.i("ShellgroundLinux","Guest boot ready; checking grader assets");
                    cleanupPreviousPack();
                    startup("Linux 부팅 완료 · 채점 자료 확인 중");
                    configureGraders(owned,requested);
                    android.util.Log.i("ShellgroundLinux","Grader assets ready");
                    if(requested.equals("conda")){
                        startup("Conda 실습 준비 중");
                        CondaGuest adapter=new CondaGuest((a,p,t)->owned.channel().request(a,p,t),this::condaAsset);
                        adapter.configure();conda=adapter;
                    }
                    if(requested.equals("notebook")){
                        startup("Jupyter 실습 준비 중");
                        NotebookGuest adapter=new NotebookGuest((a,p,t)->owned.channel().request(a,p,t));
                        adapter.start();notebook=adapter;
                    }
                    course=requested;
                }
                catch(Exception failure){
                    try{owned.close();}catch(Exception cleanup){failure.addSuppressed(cleanup);}
                    // Retain ownership if cleanup failed, so stopOwned can retry
                    // instead of losing the only handle to a live child/reader.
                    if(!owned.isAlive()&&!owned.readerAlive())machine=null;
                    throw failure;
                }
            }
            return new JSONObject().put("ok",true).put("ready",true);
        }
        GuestMachine guest=machine;
        if(guest==null||!guest.isAlive())throw new IOException("먼저 실제 Linux 환경을 시작하세요.");
        if("notebook".equals(action)){
            if(notebook==null)throw new IOException("노트북 실습을 먼저 여세요.");
            String operation=request.getString("operation");
            if(!Arrays.asList("list","select","identity","restart","execute","save","run_all").contains(operation))throw new IOException("지원하지 않는 노트북 동작");
            return new JSONObject().put("ok",true).put("operation",operation)
                .put("notebook_result",notebook.perform(operation,request.getJSONObject("arguments")));
        }
        if("conda_setup".equals(action)){
            if(conda==null)throw new IOException("Conda 과정을 먼저 여세요.");
            closeTerminals(guest);
            JSONObject prepared=conda.prepareSetup();mission=new JSONObject().put("kind","conda_setup");
            startDirectory=prepared.getString("start");
            return open(guest).put("setup",prepared);
        }
        if("prepare".equals(action)){
            startup("선택한 문제의 실습 환경 준비 중");
            JSONObject next=request.getJSONObject("mission");
            if(("conda".equals(next.optString("kind")))!=course.equals("conda"))throw new IOException("실행 중인 과정과 문제가 다릅니다.");
            mission=null;startDirectory=null;
            closedThrough=lastOpened;
            if(notebook!=null)closeTerminals(guest);
            if(course.equals("linux"))for(String helper:new String[]{"system_lab.py","process_lab.py","auth_lab.py"}){
                JSONObject cleaned=(JSONObject)guest.channel().request("exec",new JSONObject().put("root",true).put("cwd","/tmp")
                    .put("run_timeout",20).put("argv",new JSONArray().put("/usr/bin/python3").put("/opt/shellground/"+helper).put("cleanup")),25000);
                if(cleaned.getInt("code")!=0)throw new IOException("이전 문제 정리 실패: "+NotebookGuest.decode(cleaned,"err"));
            }
            JSONObject preparation=notebook!=null?notebook.prepare(next.getJSONObject("problem")):
                conda!=null?conda.prepare(next):(JSONObject)guest.channel().request("prepare",new JSONObject().put("mission",next),360000);
            display.submit(()->terminals.clear()).get(5,TimeUnit.SECONDS);
            startDirectory=conda!=null||notebook!=null?preparation.getString("start"):next.getString("start");
            mission=next;return open(guest).put("preparation",preparation);
        }
        if("open".equals(action))return open(guest);
        if("select".equals(action)){
            String sid=request.getString("session");
            if(!terminals.containsKey(sid))throw new IOException("터미널이 없습니다.");
            selected=sid;display.submit(()->{try{paint(sid,terminals.get(sid));}catch(Exception e){reply(EVENT,0,error(e));}}).get(5,TimeUnit.SECONDS);
        }else if("input".equals(action)){
            String data=request.getString("data");if(data.length()>64000)throw new IOException("한 번에 입력할 내용이 너무 깁니다.");
            sendKeys(selected,data);
        }else if("resize".equals(action)){
            columns=Math.max(10,Math.min(160,request.getInt("columns")));rows=Math.max(4,Math.min(60,request.getInt("rows")));
            for(String sid:terminals.keySet()){
                guest.channel().send(new JSONObject().put("action","resize").put("session",sid).put("size",new JSONArray(new int[]{rows,columns})));
                display.submit(()->{try{PyObject term=terminals.get(sid);if(term!=null){term.callAttr("resize",columns,rows);paint(sid,term);}}catch(Exception e){reply(EVENT,0,error(e));}}).get(5,TimeUnit.SECONDS);
            }
        }else if("scroll".equals(action)||"live".equals(action)){
            display.submit(()->{try{PyObject term=terminals.get(selected);if(term!=null){
                if("live".equals(action))term.callAttr("live");else term.callAttr("scroll",request.optInt("delta"));paint(selected,term);
            }}catch(Exception e){reply(EVENT,0,error(e));}}).get(5,TimeUnit.SECONDS);
        }else if("copy".equals(action)){
            String text=display.submit(()->terminals.get(selected).callAttr("text").toString()).get(5,TimeUnit.SECONDS);
            return new JSONObject().put("ok",true).put("copy",text);
        }else if("grade".equals(action)){
            if(mission==null)throw new IOException("준비된 문제가 없습니다.");
            if(notebook!=null)return new JSONObject().put("ok",true).put("grade",notebook.grade(request.getJSONArray("cells")));
            if(conda!=null){
                JSONObject answers=request.optJSONObject("answers");
                if(answers==null)answers=new JSONObject();
                return new JSONObject().put("ok",true).put("grade",conda.grade(selected,answers));
            }
            String text=display.submit(()->{StringBuilder result=new StringBuilder();for(PyObject term:terminals.values())result.append(term.callAttr("output")).append('\n');return result.toString();}).get(5,TimeUnit.SECONDS);
            Object grade=guest.channel().request("grade",new JSONObject().put("mission",mission).put("session",selected).put("output",text),120000);
            return new JSONObject().put("ok",true).put("grade",grade);
        }else if("files".equals(action)){
            if(conda==null)throw new IOException("이 과정에는 Conda 파일 보기가 없습니다.");
            return new JSONObject().put("ok",true).put("files",conda.files(request.has("path")?request.getString("path"):null));
        }else throw new IOException("지원하지 않는 실습 동작: "+action);
        return new JSONObject().put("ok",true);
    }

    private JSONObject open(GuestMachine guest)throws Exception{
        if(mission==null)throw new IOException("먼저 문제를 준비하세요.");
        if(terminals.size()>=4)throw new IOException("터미널은 최대4개입니다. 문제 다시 시작으로 정리할 수 있습니다.");
        JSONObject opened=(JSONObject)guest.channel().request("open",new JSONObject().put("cwd",startDirectory),30000);
        selected=opened.getString("session");
        lastOpened=Integer.parseInt(selected);
        final String sid=selected;
        display.submit(()->terminals.computeIfAbsent(sid,key->terminalModule.callAttr("Terminal",columns,rows))).get(5,TimeUnit.SECONDS);
        guest.channel().send(new JSONObject().put("action","resize").put("session",sid).put("size",new JSONArray(new int[]{rows,columns})));
        return new JSONObject().put("ok",true).put("session",sid);
    }

    private void closeTerminals(GuestMachine guest)throws Exception{
        closedThrough=lastOpened;
        for(String sid:new ArrayList<>(terminals.keySet()))guest.channel().request("close",new JSONObject().put("session",sid),10000);
        display.submit(()->terminals.clear()).get(5,TimeUnit.SECONDS);
    }

    private void configureGraders(GuestMachine guest,String requested)throws Exception{
        List<String> names=Arrays.asList("lab.py","ros_lab.py","ros_controls_lab.py","ros_observer.py","apt_lab.py",
            "auth_lab.py","shell_lab.py","process_lab.py","io_lab.py","system_lab.py","docker_lab.py",
            "docker_sessions_lab.py","docker_runtime_lab.py","shell_snapshot.py","bashrc");
        Map<String,byte[]> files=new LinkedHashMap<>();
        for(String name:names)files.put("/opt/shellground/"+name,readAsset("real-guest/"+name));
        // The agent imports this lazily on the first Conda prepare. Sync the
        // adapter as well as its runtime, otherwise the immutable base keeps
        // using the old desktop deadline even after an APK update.
        if(requested.equals("conda"))files.put("/opt/shellground/conda_lab.py",readAsset("real-guest/conda_lab.py"));
        if(requested.equals("notebook"))for(String name:new String[]{"guest_setup.py","guest_service.py","guest_lessons.py"})
            files.put("/opt/shellground/notebook-assets/"+name,readAsset("notebook-guest/"+name));
        GuestAssets.sync((a,p,t)->guest.channel().request(a,p,t),files);
    }
    private byte[] readAsset(String asset)throws Exception{
        byte[] content;
        try(InputStream input=getAssets().open(asset);ByteArrayOutputStream bytes=new ByteArrayOutputStream()){
            byte[] block=new byte[8192];int n;while((n=input.read(block))!=-1){
                if(bytes.size()+n>512*1024)throw new IOException("채점 자료 크기가 잘못되었습니다.");bytes.write(block,0,n);
            }content=bytes.toByteArray();
        }
        return content;
    }

    private byte[] condaAsset(String name)throws Exception{
        if(!Arrays.asList("conda_runtime.py","shell_snapshot.py","bashrc","guest_files.py","pip_runtime.py","pip_wheel.py","conda_setup.py","installer_sources.py").contains(name))throw new IOException("잘못된 Conda 자산 이름");
        try(InputStream input=getAssets().open("conda-guest/"+name);ByteArrayOutputStream bytes=new ByteArrayOutputStream()){
            byte[] buffer=new byte[8192];int count;
            while((count=input.read(buffer))!=-1){
                if(Thread.currentThread().isInterrupted())throw new InterruptedException("Conda 시작 취소");
                if(bytes.size()+count>512*1024)throw new IOException("Conda 자산이 너무 큽니다.");bytes.write(buffer,0,count);
            }
            return bytes.toByteArray();
        }
    }

    private void installBundledPack(File pack)throws Exception{
        // User distribution will carry the image as data assets, not require
        // Termux, adb, root, WSL, a PC server, or executable downloads.
        String[] names={"kernel","initrd","manifest.json"};
        if(!Arrays.asList(getAssets().list("training-pack")).contains("manifest.json"))
            throw new IOException("이 APK에는 실제 Linux 실습 팩이 포함되지 않았습니다. Python 실습은 계속 사용할 수 있습니다.");
        File pending=new File(getFilesDir(),"training-pack-install");
        if(!pending.isDirectory()&&!pending.mkdirs())throw new IOException("실습 저장 폴더를 만들지 못했습니다.");
        JSONObject packaging;
        try(InputStream input=getAssets().open("training-pack/packaging.json")){
            ByteArrayOutputStream bytes=new ByteArrayOutputStream();byte[] buffer=new byte[8192];int count;
            while((count=input.read(buffer))!=-1){if(bytes.size()>262144)throw new IOException("실습 팩 정보가 너무 큽니다.");bytes.write(buffer,0,count);}
            packaging=new JSONObject(bytes.toString(java.nio.charset.StandardCharsets.UTF_8.name()));
        }
        JSONArray parts=packaging.getJSONArray("base_parts");
        long required=0;for(int i=0;i<parts.length();i++)required+=parts.getJSONObject(i).getLong("size");
        long replaceable=new File(pending,"base.qcow2").length();
        if(required<1||getFilesDir().getUsableSpace()+replaceable<required+512L*1024*1024)throw new IOException(String.format(Locale.ROOT,"실습 준비에 약 %.1fGB의 추가 여유 공간이 필요합니다.",(required+512L*1024*1024)/1e9));
        try(OutputStream out=new FileOutputStream(new File(pending,"base.qcow2"))){
            byte[] bytes=new byte[1024*1024];
            long copied=0;int reported=-1;
            for(int i=0;i<parts.length();i++){
                String name=parts.getJSONObject(i).getString("name");
                if(!name.matches("base-[0-9]{4}\\.sgpart"))throw new IOException("잘못된 실습 이미지 조각 이름");
                try(InputStream input=getAssets().open("training-pack/"+name)){
                    int count;while((count=input.read(bytes))!=-1){if(Thread.currentThread().isInterrupted())throw new InterruptedException("설치 취소");out.write(bytes,0,count);copied+=count;int percent=(int)Math.min(100,copied*100/required);if(percent!=reported){reported=percent;startup("첫 실행 · 실습 이미지 설치 "+percent+"%");}}
                }
            }
        }
        for(String name:names){
            if(Thread.currentThread().isInterrupted())throw new InterruptedException("설치 취소");
            try(InputStream input=getAssets().open("training-pack/"+name);OutputStream out=new FileOutputStream(new File(pending,name))){
                byte[] bytes=new byte[1024*1024];int count;
                while((count=input.read(bytes))!=-1){if(Thread.currentThread().isInterrupted())throw new InterruptedException("설치 취소");out.write(bytes,0,count);}
            }
        }
        if(pack.exists()||!pending.renameTo(pack))throw new IOException("실습 이미지 설치를 완료하지 못했습니다.");
    }

    private void cleanupPreviousPack(){
        // These four names are the previous app-owned immutable cache only.
        // Progress lives in SharedPreferences and is never in this directory.
        File old=new File(getFilesDir(),"training-pack");
        File[] entries=old.listFiles();if(entries==null)return;
        Set<String> allowed=new HashSet<>(Arrays.asList("base.qcow2","kernel","initrd","manifest.json"));
        for(File entry:entries)if(!allowed.contains(entry.getName())||!entry.isFile())return;
        for(File entry:entries)entry.delete();old.delete();
    }

    private synchronized void stopOwned(){
        if(closing)return;closing=true;worker.shutdownNow();
        android.util.Log.i("ShellgroundLinux","Stopping owned VM");
        new Thread(()->{
            try{
                GuestMachine owned=machine;if(owned!=null)owned.close();
                worker.awaitTermination(5,TimeUnit.SECONDS);
            }catch(Exception failure){reply(EVENT,0,error(failure));}
            finally{
                display.shutdownNow();
                try{reply(EVENT,0,new JSONObject().put("stopped",machine==null||(!machine.isAlive()&&!machine.readerAlive())));}catch(JSONException ignored){}
                ui.post(()->{android.util.Log.i("ShellgroundLinux","Owned cleanup finished");stopSelf();android.os.Process.killProcess(android.os.Process.myPid());});
            }
        },"shellground-linux-stop").start();
    }
    @Override public IBinder onBind(Intent intent){return binder.getBinder();}
    @Override public int onStartCommand(Intent intent,int flags,int startId){return START_NOT_STICKY;}
    @Override public boolean onUnbind(Intent intent){stopOwned();return false;}
    @Override public void onTaskRemoved(Intent intent){stopOwned();super.onTaskRemoved(intent);}
    @Override public void onDestroy(){stopOwned();super.onDestroy();}
}
