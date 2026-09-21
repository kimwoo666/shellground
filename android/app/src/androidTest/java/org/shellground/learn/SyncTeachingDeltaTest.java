package org.shellground.learn;

import android.app.Instrumentation;
import android.content.*;
import android.os.*;
import androidx.test.platform.app.InstrumentationRegistry;
import androidx.test.ext.junit.runners.AndroidJUnit4;
import org.junit.*;
import org.junit.runner.RunWith;
import org.json.*;
import java.io.*;
import java.util.concurrent.*;
import static org.junit.Assert.*;

/** Changed sync, guided practice and graph features only. No guest VM. */
@RunWith(AndroidJUnit4.class)
public final class SyncTeachingDeltaTest {
    private final Instrumentation inst=InstrumentationRegistry.getInstrumentation();
    private final Context context=inst.getTargetContext();
    @After public void close(){ScreenTestLifecycle.closeActivities(inst);}
    private JSONObject asset()throws Exception{
        try(InputStream input=context.getAssets().open("python-course.json");ByteArrayOutputStream out=new ByteArrayOutputStream()){
            byte[] bytes=new byte[8192];int n;while((n=input.read(bytes))!=-1)out.write(bytes,0,n);return new JSONObject(out.toString("UTF-8"));
        }
    }
    @Test public void encryptedCredentialsAreLocalAndReversible()throws Exception{
        NasCredentials credentials=new NasCredentials(context);
        // This class runs only on the owned test emulator with no user account.
        JSONObject fixture=new JSONObject().put("server","nas.example.invalid").put("password","test-secret-not-real");
        try{
            credentials.save(fixture);assertEquals(fixture.toString(),credentials.load().toString());
            File file=new File(context.getNoBackupFilesDir(),"nas-credentials-v1.enc");
            byte[] bytes=new byte[(int)file.length()];try(DataInputStream input=new DataInputStream(new FileInputStream(file))){input.readFully(bytes);}
            assertFalse(new String(bytes,java.nio.charset.StandardCharsets.ISO_8859_1).contains("test-secret-not-real"));
        }finally{credentials.remove();}
    }
    @Test public void eightyOnePagesExportedAndFirstGuidedExampleReallyGrades()throws Exception{
        JSONArray units=asset().getJSONArray("lessons");int pages=0;JSONObject selected=null;
        for(int i=0;i<units.length();i++){
            JSONObject unit=units.getJSONObject(i);JSONArray guided=unit.getJSONArray("guided_steps");pages+=guided.length();
            if(selected==null&&guided.length()>1)selected=unit;
        }
        assertEquals(81,pages);assertNotNull(selected);
        try(Bridge bridge=new Bridge()){
            JSONObject request=new JSONObject().put("unit",selected.getString("key")).put("phase","learn").put("step",1).put("variant",0);
            JSONObject executed=bridge.request(new JSONObject(request.toString()).put("action","execute").put("code",selected.getJSONArray("guided_steps").getJSONObject(1).getJSONObject("practice").getString("solution")));
            assertTrue(executed.toString(),executed.getBoolean("ok"));
            assertTrue(bridge.request(new JSONObject(request.toString()).put("action","grade")).getJSONObject("grade").getBoolean("passed"));
            assertFalse(context.getSharedPreferences("python-progress-v1",Context.MODE_PRIVATE).getBoolean(selected.getString("key")+":1",false));
        }
    }
    @Test public void currentGraphWinsAndErrorsRemainVisible()throws Exception{
        JSONArray units=asset().getJSONArray("lessons");String key=null;
        for(int i=0;i<units.length();i++)if(units.getJSONObject(i).getString("key").equals("plot_line"))key="plot_line";
        assertNotNull(key);
        try(Bridge bridge=new Bridge()){
            JSONObject base=new JSONObject().put("unit",key).put("variant",0).put("action","execute");
            JSONObject plotted=bridge.request(new JSONObject(base.toString()).put("code","import matplotlib.pyplot as plt\nplt.close('all')\nplt.figure()\nfig, ax = plt.subplots()\nax.plot([0,1], [1,3])"));
            assertTrue(plotted.toString(),plotted.getBoolean("ok"));
            assertEquals(2,plotted.getJSONArray("figure_numbers").getInt(0));
            assertEquals(2,plotted.getJSONArray("figurePaths").length());
            assertTrue(new File(plotted.getJSONArray("figurePaths").getString(0)).length()>1000);
            JSONObject failed=bridge.request(new JSONObject(base.toString()).put("code","not_a_defined_name"));
            assertFalse(failed.getBoolean("ok"));assertTrue(failed.getString("output").contains("NameError"));
        }
    }
    public static final class MemoryRemote {
        public final java.util.Map<String,String> records=new java.util.HashMap<>();
        public String read(String name){return name.equals("shellground-profile.json")?"{\"schema\":1,\"profile\":\"delta-test\"}":records.get(name);}
        public String[] names(){return records.keySet().toArray(new String[0]);}
        public void write(String name,String value){records.put(name,value);}
    }
    @Test public void androidPythonBridgeWritesOnlyLearningMetadata()throws Exception{
        if(!com.chaquo.python.Python.isStarted())com.chaquo.python.Python.start(new com.chaquo.python.android.AndroidPlatform(context));
        File directory=new File(context.getCacheDir(),"sync-delta-"+java.util.UUID.randomUUID());assertTrue(directory.mkdir());
        try{
            JSONObject catalogs=new JSONObject();
            String[] scopes={"python-progress-v1","real-linux-progress-v1","real-conda-progress-v1","real-notebook-progress-v1"};
            for(String scope:scopes)catalogs.put(scope,new JSONArray("[{\"key\":\"unit\",\"learning_steps\":[{\"title\":\"A\"},{\"title\":\"B\"}]}]"));
            catalogs.put("quizzes",new JSONArray()).put("cards",new JSONArray());
            String preferences="{\"python-progress-v1\":{\"last\":\"unit\",\"unit.phase\":0,\"unit.step\":1,\"unit:1\":true,\"password\":\"NEVER-EXPORT\"}}";
            MemoryRemote remote=new MemoryRemote();
            JSONObject result=new JSONObject(com.chaquo.python.Python.getInstance().getModule("mobile_progress")
                .callAttr("exchange",directory.getAbsolutePath(),preferences,catalogs.toString(),remote,true).toString());
            assertEquals(1,result.getJSONObject("preferences").getJSONObject(scopes[0]).getInt("unit.step"));
            assertEquals(1,remote.records.size());assertFalse(remote.records.toString().contains("NEVER-EXPORT"));
            assertTrue(remote.records.toString().contains("unit:1"));
        }finally{File[] files=directory.listFiles();if(files!=null)for(File file:files)if(file.isFile())file.delete();directory.delete();}
    }
    private final class Bridge implements AutoCloseable{
        private final BlockingQueue<JSONObject> results=new LinkedBlockingQueue<>();
        private final CompletableFuture<Messenger> connected=new CompletableFuture<>();
        private final ServiceConnection connection=new ServiceConnection(){public void onServiceConnected(ComponentName n,IBinder b){connected.complete(new Messenger(b));}public void onServiceDisconnected(ComponentName n){}};
        private final Messenger replies=new Messenger(new Handler(Looper.getMainLooper(),message->{try{results.add(new JSONObject(message.getData().getString("result")));}catch(Exception e){throw new AssertionError(e);}return true;}));
        Bridge(){assertTrue(context.bindService(new Intent(context,PythonService.class),connection,Context.BIND_AUTO_CREATE));}
        JSONObject request(JSONObject value)throws Exception{
            Message message=Message.obtain(null,PythonService.RUN);message.replyTo=replies;Bundle data=new Bundle();data.putString("request",value.toString());message.setData(data);connected.get(15,TimeUnit.SECONDS).send(message);
            JSONObject result=results.poll(90,TimeUnit.SECONDS);assertNotNull("Python service response timeout",result);return result;
        }
        public void close()throws Exception{connected.get(5,TimeUnit.SECONDS).send(Message.obtain(null,PythonService.STOP));context.unbindService(connection);context.stopService(new Intent(context,PythonService.class));Thread.sleep(500);}
    }
}
