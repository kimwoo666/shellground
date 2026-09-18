package org.shellground.learn;

import android.content.*;
import android.os.*;
import android.util.Base64;
import androidx.test.platform.app.InstrumentationRegistry;
import androidx.test.ext.junit.runners.AndroidJUnit4;
import com.chaquo.python.Python;
import com.chaquo.python.android.AndroidPlatform;
import org.shellground.runtime.GuestMachine;
import org.json.*;
import org.junit.*;
import org.junit.runner.RunWith;
import java.io.*;
import java.nio.charset.StandardCharsets;
import java.util.concurrent.*;
import static org.junit.Assert.*;

@RunWith(AndroidJUnit4.class)
public final class LinuxRuntimeTest {
    private Context context(){return InstrumentationRegistry.getInstrumentation().getTargetContext();}
    private JSONObject course()throws Exception{
        try(InputStream input=context().getAssets().open("real-course.json")){
            ByteArrayOutputStream bytes=new ByteArrayOutputStream();byte[] buffer=new byte[8192];int count;
            while((count=input.read(buffer))!=-1)bytes.write(buffer,0,count);
            return new JSONObject(bytes.toString(StandardCharsets.UTF_8.name()));
        }
    }
    @Test public void testExistingRealCourseIsPackagedWithoutSimulation()throws Exception{
        JSONObject data=course();assertEquals("real-guest",data.getString("execution"));
        assertEquals(138,data.getJSONArray("units").length());assertEquals(27,data.getJSONArray("reviews").length());
        for(int i=0;i<138;i++){JSONObject unit=data.getJSONArray("units").getJSONObject(i);assertTrue(unit.getJSONArray("learning_steps").length()>0);assertEquals(3,unit.getJSONArray("problems").length());}
    }
    @Test public void testActualAndroidVTParser()throws Exception{
        if(!Python.isStarted())Python.start(new AndroidPlatform(context()));
        String code="import base64,json\nfrom linux_terminal import Terminal\nt=Terminal(30,6)\n"
            +"raw='\\x1b[32m한글\\x1b[0m'.encode()\nfor b in raw:t.feed(base64.b64encode(bytes([b])).decode())\n"
            +"f=json.loads(t.frame())\nassert f['rows'][0][0][1:3]==['한','green']\n"
            +"t.feed(base64.b64encode(('\\r\\n'.join(str(i) for i in range(20))+'\\r\\n').encode()).decode())\n"
            +"t.scroll(-4)\nbefore=json.loads(t.frame())\nt.feed(base64.b64encode(b'new\\r\\n').decode())\nafter=json.loads(t.frame())\n"
            +"assert before['top']==after['top'] and before['rows']==after['rows']\nassert not after['cursor'][2]\n"
            +"assert '한글' in t.output()\n";
        // Java has no Python caller frame from which exec can inherit globals.
        com.chaquo.python.PyObject builtins=Python.getInstance().getModule("builtins");
        builtins.callAttr("exec",code,builtins.callAttr("dict"));
    }

    @Test public void testCancelledGuestCannotStartLater()throws Exception{
        GuestMachine guest=new GuestMachine();guest.close();
        try{guest.boot(context(),new File(context().getFilesDir(),"training-pack"),event->{});fail("Closed guest must not boot");}
        catch(IOException expected){assertTrue(expected.getMessage().contains("취소"));}
        assertFalse(guest.isAlive());assertFalse(guest.readerAlive());guest.close();
    }

    @Test public void testInterruptedStartupStillReapsOwnedProcess()throws Exception{
        // An actual, disposable app-owned child, not a simulated Linux command.
        // No guest image is needed to reproduce the interrupted waitFor path.
        java.lang.Process child=new ProcessBuilder("/system/bin/sleep","60").start();
        GuestMachine guest=new GuestMachine();
        java.lang.reflect.Field process=GuestMachine.class.getDeclaredField("process");
        process.setAccessible(true);process.set(guest,child);
        try{
            Thread.currentThread().interrupt();
            guest.close();
            assertTrue("Cleanup preserves cancellation for its caller",Thread.currentThread().isInterrupted());
            Thread.interrupted();
            assertFalse("Cancellation must reap the child",child.isAlive());
            guest.close();
        }finally{
            Thread.interrupted();
            if(child.isAlive()){child.destroyForcibly();child.waitFor(5,TimeUnit.SECONDS);}
        }
    }

    @Test public void testInterruptedCleanupCanBeRetried()throws Exception{
        // Unit-only fault injection: fail one wait in the middle of close.
        // This is not evidence of a guest boot or a curriculum command.
        java.lang.Process child=new java.lang.Process(){
            boolean alive=true,first=true;
            public OutputStream getOutputStream(){return new ByteArrayOutputStream();}
            public InputStream getInputStream(){return new ByteArrayInputStream(new byte[0]);}
            public InputStream getErrorStream(){return new ByteArrayInputStream(new byte[0]);}
            public int waitFor(){return 0;}
            public boolean waitFor(long time,TimeUnit unit)throws InterruptedException{
                if(first){first=false;throw new InterruptedException("injected cancellation");}
                return !alive;
            }
            public int exitValue(){if(alive)throw new IllegalThreadStateException();return 0;}
            public void destroy(){alive=false;}
            public boolean isAlive(){return alive;}
        };
        GuestMachine guest=new GuestMachine();
        java.lang.reflect.Field process=GuestMachine.class.getDeclaredField("process");process.setAccessible(true);process.set(guest,child);
        try{guest.close();fail("Injected interruption must remain visible");}
        catch(InterruptedException expected){}
        assertTrue(child.isAlive());
        guest.close();
        assertFalse("A previous interrupted close must not suppress cleanup",child.isAlive());
    }

    @Test public void testImmediateRoomExitCancelsStartup()throws Exception{
        Assume.assumeTrue(BuildConfig.LINUX_RUNTIME);
        CountDownLatch connected=new CountDownLatch(1),stopped=new CountDownLatch(1);
        HandlerThread callbacks=new HandlerThread("linux-cancel-test");callbacks.start();
        Messenger reply=new Messenger(new Handler(callbacks.getLooper(),message->{
            try{JSONObject result=new JSONObject(message.getData().getString("result","{}"));
                if(message.what==LinuxService.EVENT&&result.optBoolean("stopped"))stopped.countDown();
            }catch(JSONException ignored){}return true;
        }));
        Messenger[] remote={null};
        ServiceConnection connection=new ServiceConnection(){
            public void onServiceConnected(ComponentName name,IBinder binder){remote[0]=new Messenger(binder);connected.countDown();}
            public void onServiceDisconnected(ComponentName name){}
        };
        boolean bound=context().bindService(new Intent(context(),LinuxService.class),connection,Context.BIND_AUTO_CREATE);
        try{
            assertTrue(bound);assertTrue(connected.await(10,TimeUnit.SECONDS));
            for(String action:new String[]{"start","stop"}){
                Message request=Message.obtain(null,LinuxService.REQUEST);request.replyTo=reply;
                Bundle data=new Bundle();data.putString("request",new JSONObject().put("action",action).toString());request.setData(data);remote[0].send(request);
            }
            assertTrue("Startup cancel must finish, not leave a VM behind",stopped.await(25,TimeUnit.SECONDS));
        }finally{
            if(bound)context().unbindService(connection);context().stopService(new Intent(context(),LinuxService.class));callbacks.quitSafely();
        }
    }

    /** Opt-in VM proof through the actual learner application's service. */
    @Test public void testLearnerServiceRealNanoGradeMultipleTerminalsAndStop()throws Exception{
        Assume.assumeTrue("Explicit fullGuest=true and staged private image required",
            "true".equals(InstrumentationRegistry.getArguments().getString("fullGuest")));
        BlockingQueue<JSONObject> answers=new LinkedBlockingQueue<>();
        BlockingQueue<JSONObject> frames=new LinkedBlockingQueue<>();
        CountDownLatch stopped=new CountDownLatch(1);
        HandlerThread callbacks=new HandlerThread("linux-service-test");callbacks.start();
        Messenger reply=new Messenger(new Handler(callbacks.getLooper(),message->{
            try{JSONObject data=new JSONObject(message.getData().getString("result","{}"));
                if(message.what==LinuxService.RESULT)answers.offer(data);
                else if(message.what==LinuxService.FRAME)frames.offer(data);
                else if(message.what==LinuxService.EVENT&&data.optBoolean("stopped"))stopped.countDown();
            }catch(Exception ignored){}return true;
        }));
        Messenger[] remote={null};CountDownLatch connected=new CountDownLatch(1);
        ServiceConnection connection=new ServiceConnection(){public void onServiceConnected(ComponentName name,IBinder binder){remote[0]=new Messenger(binder);connected.countDown();}public void onServiceDisconnected(ComponentName name){}};
        assertTrue(context().bindService(new Intent(context(),LinuxService.class),connection,Context.BIND_AUTO_CREATE));
        try{
            assertTrue(connected.await(10,TimeUnit.SECONDS));
            class Client{
                JSONObject request(String action,JSONObject data,int seconds)throws Exception{
                    data.put("action",action);Message message=Message.obtain(null,LinuxService.REQUEST);message.replyTo=reply;
                    Bundle bundle=new Bundle();bundle.putString("request",data.toString());message.setData(bundle);remote[0].send(message);
                    if(action.equals("stop"))return new JSONObject();
                    JSONObject answer=answers.poll(seconds,TimeUnit.SECONDS);assertNotNull("Request timed out: "+action,answer);assertFalse(answer.toString(),answer.has("error"));return answer;
                }
                void keys(String text)throws Exception{request("input",new JSONObject().put("data",Base64.encodeToString(text.getBytes(StandardCharsets.UTF_8),Base64.NO_WRAP)),10);}
                void until(String needle)throws Exception{
                    long end=System.nanoTime()+TimeUnit.SECONDS.toNanos(35);String visible="";
                    while(System.nanoTime()<end){JSONObject frame=frames.poll(1,TimeUnit.SECONDS);if(frame==null)continue;
                        StringBuilder screen=new StringBuilder();JSONArray rows=frame.getJSONArray("rows");for(int y=0;y<rows.length();y++){JSONArray cells=rows.getJSONArray(y);for(int x=0;x<cells.length();x++)screen.append(cells.getJSONArray(x).getString(1));screen.append('\n');}
                        visible=screen.toString();if(visible.contains(needle))return;
                    }fail("Missing rendered terminal text "+needle+"\n"+visible);
                }
            }
            Client client=new Client();assertTrue(client.request("start",new JSONObject(),240).getBoolean("ready"));
            JSONObject edit=null;JSONArray units=course().getJSONArray("units");for(int i=0;i<units.length();i++)if(units.getJSONObject(i).getString("key").equals("edit"))edit=units.getJSONObject(i).getJSONArray("problems").getJSONObject(0);
            assertNotNull(edit);
            String first=client.request("prepare",new JSONObject().put("mission",edit),120).getString("session");
            client.request("resize",new JSONObject().put("columns",80).put("rows",24),10);
            assertFalse(client.request("grade",new JSONObject(),60).getJSONObject("grade").getBoolean("passed"));
            client.keys("nano note.txt\r");client.until("GNU nano");
            client.keys("\u000bstatus=ready\u000f");client.until("File Name to Write");
            client.keys("\r");client.until("Wrote");client.keys("\u0018");
            client.keys("printf '\\nSG_%s\\n' SAVED\r");client.until("SG_SAVED");
            assertTrue(client.request("grade",new JSONObject(),60).getJSONObject("grade").getBoolean("passed"));
            String second=client.request("open",new JSONObject(),30).getString("session");assertNotEquals(first,second);
            client.keys("printf '\\nSG_%s\\n' SECOND\r");client.until("SG_SECOND");
            client.request("select",new JSONObject().put("session",first),10);client.until("SG_SAVED");
            JSONObject copy=client.request("copy",new JSONObject(),10);assertTrue(copy.getString("copy").contains("SG_SAVED"));
            client.request("stop",new JSONObject(),1);
            assertTrue("Real VM/reader did not stop",stopped.await(25,TimeUnit.SECONDS));
            Bundle evidence=new Bundle();evidence.putString("stream","\nANDROID_LEARNER_REAL_SERVICE_OK\n");InstrumentationRegistry.getInstrumentation().sendStatus(0,evidence);
        }finally{
            if(remote[0]!=null)try{Message stop=Message.obtain(null,LinuxService.REQUEST);stop.replyTo=reply;Bundle b=new Bundle();b.putString("request","{\"action\":\"stop\"}");stop.setData(b);remote[0].send(stop);}catch(Exception ignored){}
            context().unbindService(connection);context().stopService(new Intent(context(),LinuxService.class));callbacks.quitSafely();
        }
    }
}
