package org.shellground.learn;

import android.app.*;
import android.content.*;
import android.os.*;
import android.view.*;
import android.widget.*;
import androidx.test.platform.app.InstrumentationRegistry;
import androidx.test.ext.junit.runners.AndroidJUnit4;
import org.json.*;
import org.junit.*;
import org.junit.runner.RunWith;
import java.io.*;
import java.nio.charset.StandardCharsets;
import java.util.concurrent.*;
import static org.junit.Assert.*;

/** New port boundary only; does not replay the previously checked curriculum. */
@RunWith(AndroidJUnit4.class)
public final class PortDeltaTest {
    private final Instrumentation inst=InstrumentationRegistry.getInstrumentation();
    @After public void closeScreens(){ScreenTestLifecycle.closeActivities(inst);}
    private JSONObject asset(String name)throws Exception{
        try(InputStream input=inst.getTargetContext().getAssets().open(name);ByteArrayOutputStream out=new ByteArrayOutputStream()){
            byte[] bytes=new byte[8192];int n;while((n=input.read(bytes))!=-1)out.write(bytes,0,n);
            return new JSONObject(out.toString(StandardCharsets.UTF_8.name()));
        }
    }
    private EditText editor(View view){if(view instanceof EditText)return (EditText)view;
        if(view instanceof ViewGroup)for(int i=0;i<((ViewGroup)view).getChildCount();i++){EditText found=editor(((ViewGroup)view).getChildAt(i));if(found!=null)return found;}return null;}

    @Test public void notebookShiftEnterExecutesWithoutInsertingNewline()throws Exception{
        final int[] calls={0};final String[] code={""};
        inst.runOnMainSync(()->{
            try{
                NotebookEditor view=new NotebookEditor(inst.getTargetContext(),new NotebookEditor.Actions(){
                    public void perform(String operation,JSONObject arguments){assertEquals("execute",operation);calls[0]++;code[0]=arguments.optString("code");}
                    public void interrupt(){}public void changed(){}
                });
                view.load(new JSONArray().put(new JSONObject().put("id","cell1").put("type","code").put("source","total = 7")));
                view.available(true);EditText input=editor(view);assertNotNull(input);
                KeyEvent down=new KeyEvent(0,0,KeyEvent.ACTION_DOWN,KeyEvent.KEYCODE_ENTER,0,KeyEvent.META_SHIFT_ON);
                KeyEvent up=new KeyEvent(0,0,KeyEvent.ACTION_UP,KeyEvent.KEYCODE_ENTER,0,KeyEvent.META_SHIFT_ON);
                assertTrue(input.dispatchKeyEvent(down));assertTrue(input.dispatchKeyEvent(up));
                assertEquals("total = 7",input.getText().toString());assertEquals("total = 7",code[0]);assertEquals(1,calls[0]);
                assertEquals("total = 7",view.snapshot().getJSONObject(0).getString("source"));
            }catch(Exception e){throw new AssertionError(e);}
        });
    }

    @Test public void currentPortCatalogsArePresent()throws Exception{
        JSONObject conda=asset("conda-course.json"),notebook=asset("notebook-course.json");
        assertEquals(20,conda.getJSONArray("units").length());assertEquals(6,notebook.getJSONArray("units").length());
        assertEquals("pip_remove_repair",conda.getJSONArray("units").getJSONObject(19).getString("key"));
        assertEquals(138,asset("real-course.json").getJSONArray("units").length());
    }

    @Test public void actualNotebookKernelRetrySaveAndCleanup()throws Exception{
        Assume.assumeTrue("Explicit new ARM runtime check only",InstrumentationRegistry.getArguments().getString("real_port","false").equals("true"));
        Context context=inst.getTargetContext();
        LinuxActivity activity=(LinuxActivity)inst.startActivitySync(new Intent(context,LinuxActivity.class)
            .putExtra("course","notebook").addFlags(Intent.FLAG_ACTIVITY_NEW_TASK));
        CompletableFuture<Messenger> connected=new CompletableFuture<>();BlockingQueue<JSONObject> replies=new LinkedBlockingQueue<>(),events=new LinkedBlockingQueue<>();
        Messenger receiver=new Messenger(new Handler(Looper.getMainLooper(),m->{
            try{JSONObject value=new JSONObject(m.getData().getString("result","{}"));
                if(m.what==LinuxService.RESULT)replies.add(value);
                if(m.what==LinuxService.EVENT&&value.has("stopped"))events.add(value);
            }catch(JSONException e){throw new AssertionError(e);}return true;
        }));
        ServiceConnection connection=new ServiceConnection(){public void onServiceConnected(ComponentName n,IBinder b){connected.complete(new Messenger(b));}public void onServiceDisconnected(ComponentName n){}};
        Intent service=new Intent(context,LinuxService.class);context.startService(service);
        assertTrue(context.bindService(service,connection,Context.BIND_AUTO_CREATE));
        Messenger remote=connected.get(10,TimeUnit.SECONDS);
        try{
            assertTrue(request(remote,receiver,replies,new JSONObject().put("action","start").put("course","notebook"),900).getBoolean("ready"));
            JSONObject problem=asset("notebook-course.json").getJSONArray("units").getJSONObject(0).getJSONArray("problems").getJSONObject(0);
            JSONObject prepared=request(remote,receiver,replies,new JSONObject().put("action","prepare")
                .put("mission",new JSONObject().put("kind","notebook").put("problem",problem)),960);
            assertTrue(prepared.has("session"));
            JSONObject before=request(remote,receiver,replies,new JSONObject().put("action","grade").put("cells",problem.getJSONArray("cells")),960);
            assertFalse(before.getJSONObject("grade").getBoolean("passed"));
            JSONObject identity=operation(remote,receiver,replies,"select",new JSONObject().put("name","sg-data"));
            assertEquals("/home/learner/notebook-envs/data",identity.getJSONObject("values").getString("prefix"));
            JSONObject run=operation(remote,receiver,replies,"run_all",new JSONObject().put("cells",problem.getJSONArray("cells")));
            JSONArray batch=run.getJSONArray("batch");assertEquals(2,batch.length());
            for(int i=0;i<batch.length();i++)assertTrue(batch.getJSONObject(i).getJSONObject("result").getBoolean("ok"));
            JSONObject after=request(remote,receiver,replies,new JSONObject().put("action","grade").put("cells",problem.getJSONArray("cells")),960);
            assertTrue(after.toString(),after.getJSONObject("grade").getBoolean("passed"));
            JSONObject saved=operation(remote,receiver,replies,"save",new JSONObject().put("filename","portable-check.ipynb").put("cells",problem.getJSONArray("cells")));
            assertEquals("/home/learner/notebook-work/portable-check.ipynb",saved.getString("path"));
        }finally{
            Message stop=Message.obtain(null,LinuxService.REQUEST);Bundle data=new Bundle();data.putString("request","{\"action\":\"stop\"}");stop.setData(data);stop.replyTo=receiver;
            try{remote.send(stop);}catch(RemoteException ignored){}context.unbindService(connection);
            JSONObject stopped=events.poll(45,TimeUnit.SECONDS);
            assertNotNull("Owned VM cleanup did not finish",stopped);assertTrue(stopped.toString(),stopped.getBoolean("stopped"));
            context.stopService(service);
            inst.runOnMainSync(activity::finish);
        }
    }
    @Test public void actualCondaVersionRetryAndCleanup()throws Exception{
        Assume.assumeTrue(InstrumentationRegistry.getArguments().getString("real_port","false").equals("true"));
        Context context=inst.getTargetContext();
        LinuxActivity activity=(LinuxActivity)inst.startActivitySync(new Intent(context,LinuxActivity.class)
            .putExtra("course","conda").addFlags(Intent.FLAG_ACTIVITY_NEW_TASK));
        CompletableFuture<Messenger> connected=new CompletableFuture<>();
        BlockingQueue<JSONObject> replies=new LinkedBlockingQueue<>(),events=new LinkedBlockingQueue<>();
        Messenger receiver=new Messenger(new Handler(Looper.getMainLooper(),m->{try{
            JSONObject value=new JSONObject(m.getData().getString("result","{}"));
            if(m.what==LinuxService.RESULT)replies.add(value);
            if(m.what==LinuxService.EVENT&&value.has("stopped"))events.add(value);
        }catch(JSONException e){throw new AssertionError(e);}return true;}));
        ServiceConnection connection=new ServiceConnection(){public void onServiceConnected(ComponentName n,IBinder b){connected.complete(new Messenger(b));}public void onServiceDisconnected(ComponentName n){}};
        Intent service=new Intent(context,LinuxService.class);context.startService(service);assertTrue(context.bindService(service,connection,Context.BIND_AUTO_CREATE));
        Messenger remote=connected.get(10,TimeUnit.SECONDS);
        try{
            assertTrue(request(remote,receiver,replies,new JSONObject().put("action","start").put("course","conda"),900).getBoolean("ready"));
            JSONObject mission=asset("conda-course.json").getJSONArray("units").getJSONObject(0).getJSONArray("problems").getJSONObject(0).getJSONObject("mission");
            JSONObject prepared=request(remote,receiver,replies,new JSONObject().put("action","prepare").put("mission",mission),420);
            String version=prepared.getJSONObject("preparation").getJSONObject("runtime").getString("conda_version");
            JSONObject listing=request(remote,receiver,replies,new JSONObject().put("action","files"),90).getJSONObject("files");
            assertNotNull(listing.getJSONArray("files"));assertFalse(listing.getBoolean("truncated"));
            JSONObject before=request(remote,receiver,replies,new JSONObject().put("action","grade").put("answers",new JSONObject()),420);
            assertFalse(before.getJSONObject("grade").getBoolean("passed"));
            String code="conda --version\n";
            request(remote,receiver,replies,new JSONObject().put("action","input").put("data",android.util.Base64.encodeToString(code.getBytes(StandardCharsets.UTF_8),android.util.Base64.NO_WRAP)),30);
            long deadline=SystemClock.elapsedRealtime()+90000;String text="";
            do{Thread.sleep(1000);text=request(remote,receiver,replies,new JSONObject().put("action","copy"),15).optString("copy");}
            while(!text.contains("conda "+version)&&SystemClock.elapsedRealtime()<deadline);
            assertTrue(text,text.contains("conda "+version));
            JSONObject after=request(remote,receiver,replies,new JSONObject().put("action","grade").put("answers",new JSONObject().put("manager_version",version)),420);
            assertTrue(after.toString(),after.getJSONObject("grade").getBoolean("passed"));
        }finally{
            Message stop=Message.obtain(null,LinuxService.REQUEST);Bundle data=new Bundle();data.putString("request","{\"action\":\"stop\"}");stop.setData(data);stop.replyTo=receiver;
            try{remote.send(stop);}catch(RemoteException ignored){}context.unbindService(connection);
            JSONObject stopped=events.poll(45,TimeUnit.SECONDS);assertNotNull(stopped);assertTrue(stopped.toString(),stopped.getBoolean("stopped"));context.stopService(service);inst.runOnMainSync(activity::finish);
        }
    }
    private JSONObject operation(Messenger remote,Messenger receiver,BlockingQueue<JSONObject> replies,String name,JSONObject args)throws Exception{
        return request(remote,receiver,replies,new JSONObject().put("action","notebook").put("operation",name).put("arguments",args),960).getJSONObject("notebook_result");
    }
    private JSONObject request(Messenger remote,Messenger receiver,BlockingQueue<JSONObject> replies,JSONObject data,int seconds)throws Exception{
        android.util.Log.i("PortDelta","Request "+data.optString("action")+" "+data.optString("operation"));
        Message message=Message.obtain(null,LinuxService.REQUEST);message.replyTo=receiver;Bundle bundle=new Bundle();bundle.putString("request",data.toString());message.setData(bundle);remote.send(message);
        JSONObject result=replies.poll(seconds,TimeUnit.SECONDS);android.util.Log.i("PortDelta","Reply "+data.optString("action"));assertNotNull("New port operation timed out",result);assertFalse(result.toString(),result.has("error"));return result;
    }
}
