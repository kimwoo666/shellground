package org.shellground.learn;

import android.app.Service;
import android.content.Intent;
import android.os.*;
import android.util.Base64;
import com.chaquo.python.Python;
import com.chaquo.python.android.AndroidPlatform;
import java.io.File;
import java.io.FileOutputStream;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import org.json.*;

/** No interpreter work on the Activity or service main thread. */
public final class PythonService extends Service {
    public static final int RUN=1, STOP=2, RESULT=3;
    private final ExecutorService executor=Executors.newSingleThreadExecutor();
    private final Messenger messenger=new Messenger(new Handler(Looper.getMainLooper(), message -> {
        if(message.what==STOP) { android.os.Process.killProcess(android.os.Process.myPid()); return true; }
        if(message.what!=RUN) return false;
        final String input=message.getData().getString("request", "{}");
        final Messenger reply=message.replyTo;
        final int id=message.arg1;
        executor.execute(() -> {
            String output;
            try {
                android.os.Process.setThreadPriority(android.os.Process.THREAD_PRIORITY_BACKGROUND);
                if(!Python.isStarted()) Python.start(new AndroidPlatform(this));
                String raw=Python.getInstance().getModule("mobile_bridge")
                    .callAttr("dispatch",input,getCacheDir().getAbsolutePath()).toString();
                JSONObject result=new JSONObject(raw);
                JSONArray figures=result.optJSONArray("figures");
                if(figures!=null && figures.length()>0) {
                    File picture=new File(getCacheDir(),"python-preview.png");
                    try(FileOutputStream stream=new FileOutputStream(picture)) {
                        stream.write(Base64.decode(figures.getString(0),Base64.DEFAULT));
                    }
                    result.put("figurePath",picture.getAbsolutePath());
                }
                result.remove("figures");
                output=result.toString();
                if(output.length()>200000) throw new IllegalStateException("출력 상한을 초과했습니다.");
            } catch(Throwable error) {
                output=new JSONObject().toString();
                try { output=new JSONObject().put("ok",false).put("output",error.toString()).toString(); }
                catch(JSONException ignored) { }
            }
            Message response=Message.obtain(null,RESULT); response.arg1=id;
            Bundle bundle=new Bundle(); bundle.putString("result",output); response.setData(bundle);
            try { reply.send(response); } catch(RemoteException ignored) { }
        });
        return true;
    }));
    @Override public IBinder onBind(Intent intent) { return messenger.getBinder(); }
    @Override public void onDestroy() {
        executor.shutdownNow();
        super.onDestroy();
        android.os.Process.killProcess(android.os.Process.myPid());
    }
}
