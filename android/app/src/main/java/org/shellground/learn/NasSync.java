package org.shellground.learn;

import android.app.*;
import android.content.*;
import android.os.*;
import android.text.InputType;
import android.widget.*;
import com.chaquo.python.Python;
import com.chaquo.python.android.AndroidPlatform;
import java.io.*;
import java.util.*;
import java.util.concurrent.*;
import org.json.*;

/** One metadata worker, no VM, no polling while the app is in the background. */
public final class NasSync {
    private static NasSync instance;
    static synchronized NasSync get(Context context){if(instance==null)instance=new NasSync(context.getApplicationContext());return instance;}
    private static final String[] SCOPES={"python-progress-v1","real-linux-progress-v1","real-conda-progress-v1","real-notebook-progress-v1"};
    private final Context context;
    private final Handler main=new Handler(Looper.getMainLooper());
    private final ExecutorService worker=Executors.newSingleThreadExecutor();
    private final NasCredentials credentials;
    private final ArrayList<Runnable> waiting=new ArrayList<>();
    private final ArrayList<SharedPreferences> prefs=new ArrayList<>();
    private JSONObject catalogs,config=new JSONObject();
    private boolean started,starting,busy,dirty;
    private long lastNetwork;
    private String status="NAS 미연결 · 로컬 진도 저장";
    private final Runnable delayed=this::flush;
    private final SharedPreferences.OnSharedPreferenceChangeListener listener=(p,k)->{dirty=true;main.removeCallbacks(delayed);main.postDelayed(delayed,1000);};
    private NasSync(Context context){this.context=context;credentials=new NasCredentials(context);for(String scope:SCOPES)prefs.add(context.getSharedPreferences(scope,Context.MODE_PRIVATE));}
    private JSONObject asset(String name)throws Exception{
        try(InputStream input=context.getAssets().open(name);ByteArrayOutputStream bytes=new ByteArrayOutputStream()){
            byte[] buffer=new byte[8192];int count;while((count=input.read(buffer))!=-1)bytes.write(buffer,0,count);
            return new JSONObject(bytes.toString("UTF-8"));
        }
    }
    private JSONObject catalogs()throws Exception{
        if(catalogs!=null)return catalogs;
        JSONObject python=asset("python-course.json"),linux=asset("real-course.json");JSONArray units=linux.getJSONArray("units"),reviews=linux.getJSONArray("reviews");
        for(int i=0;i<reviews.length();i++)units.put(new JSONObject(reviews.getJSONObject(i).toString()).put("review",true));
        catalogs=new JSONObject().put(SCOPES[0],python.getJSONArray("lessons")).put(SCOPES[1],units)
            .put(SCOPES[2],asset("conda-course.json").getJSONArray("units")).put(SCOPES[3],asset("notebook-course.json").getJSONArray("units"))
            .put("quizzes",python.getJSONArray("quizzes")).put("cards",python.getJSONArray("concept_cards"));
        return catalogs;
    }
    private JSONObject snapshot()throws JSONException{
        JSONObject all=new JSONObject();for(int i=0;i<SCOPES.length;i++)all.put(SCOPES[i],new JSONObject(prefs.get(i).getAll()));return all;
    }
    private void apply(JSONObject values)throws JSONException{
        for(int i=0;i<SCOPES.length;i++){
            JSONObject data=values.optJSONObject(SCOPES[i]);if(data==null)continue;
            SharedPreferences.Editor editor=prefs.get(i).edit();Iterator<String> keys=data.keys();
            while(keys.hasNext()){
                String key=keys.next();Object value=data.get(key);
                if(value instanceof Boolean)editor.putBoolean(key,(Boolean)value);
                else if(value instanceof Number)editor.putInt(key,((Number)value).intValue());
                else if(value instanceof String)editor.putString(key,(String)value);
            }
            if(!editor.commit())throw new IllegalStateException("기기 진도 저장 실패");
        }
    }
    void startup(Runnable callback){
        if(started){callback.run();return;}waiting.add(callback);if(starting)return;starting=true;
        work(true,null);
    }
    void flush(){
        main.removeCallbacks(delayed);
        if(!started||busy){dirty=true;return;}
        work(false,null);
    }
    private void work(boolean startup,JSONObject candidate){
        if(busy)return;busy=true;
        final String local;
        try{local=snapshot().toString();}catch(Exception e){busy=false;finishStartup();return;}
        dirty=false;
        worker.execute(()->{
            android.os.Process.setThreadPriority(android.os.Process.THREAD_PRIORITY_BACKGROUND);
            JSONObject result=null;String note;boolean network=false;
            try{
                if(startup)config=credentials.load();
                JSONObject selected=candidate==null?config:candidate;
                if(!Python.isStarted())Python.start(new AndroidPlatform(context));
                var bridge=Python.getInstance().getModule("mobile_progress");
                String directory=new File(context.getFilesDir(),"progress").getAbsolutePath(),course=catalogs().toString();
                // Commit local metadata even if login or the NAS is unavailable.
                result=new JSONObject(bridge.callAttr("exchange",directory,local,course,null,startup).toString());
                network=selected.optBoolean("enabled")&&(startup||candidate!=null||SystemClock.elapsedRealtime()-lastNetwork>=30000);
                if(network){
                    lastNetwork=SystemClock.elapsedRealtime();
                    try(SmbProgressStore store=new SmbProgressStore(selected)){
                        result=new JSONObject(bridge.callAttr("exchange",directory,local,course,store,startup).toString());
                    }
                    if(candidate!=null){credentials.save(candidate);config=candidate;}
                }
                note=selected.optBoolean("enabled")?(network?"NAS 저장 완료"+(result.optBoolean("remote_changes")&&!startup?" · 받은 진도는 앱 재시작에 적용":""):status):"NAS 미연결 · 로컬 진도 저장";
            }catch(Throwable error){
                // Protocol exceptions can contain addresses and account names.
                // Do not log them or copy them into progress/crash reports.
                note="NAS 연결 대기 · 로컬 진도 유지. 주소·공유·폴더·로그인을 확인하세요.";
            }
            final JSONObject received=result;final String message=note;final boolean triedNetwork=network;
            main.post(()->{
                status=message;
                try{if(startup&&received!=null&&received.has("preferences"))apply(received.getJSONObject("preferences"));}
                catch(Exception error){status="받은 진도를 적용하지 못했습니다. 기존 진도를 유지합니다.";}
                busy=false;
                if(startup)finishStartup();
                if(candidate!=null)Toast.makeText(context,status,Toast.LENGTH_LONG).show();
                if(dirty)main.postDelayed(delayed,triedNetwork?30000:1000);
            });
        });
    }
    private void finishStartup(){
        if(started)return;started=true;starting=false;
        for(SharedPreferences pref:prefs)pref.registerOnSharedPreferenceChangeListener(listener);
        ArrayList<Runnable> callbacks=new ArrayList<>(waiting);waiting.clear();for(Runnable callback:callbacks)callback.run();
    }
    void settings(Activity activity){
        if(busy){Toast.makeText(activity,"진도를 저장 중입니다. 잠시 후 다시 열어 주세요.",Toast.LENGTH_SHORT).show();return;}
        LinearLayout form=new LinearLayout(activity);form.setOrientation(LinearLayout.VERTICAL);int pad=(int)(20*activity.getResources().getDisplayMetrics().density);form.setPadding(pad,pad,pad,pad);
        TextView info=new TextView(activity);info.setText(status+"\n\nPC에서 만든 Shellground 진도 전용 폴더에 연결하세요. 같은 NAS의 공유 이름과 그 안의 하위 폴더를 입력합니다.\n\n완료·소단계·퀴즈만 동기화합니다. 코드는 보내지 않습니다. 로그인 정보는 이 기기에만 암호화해 저장합니다. 같은 Wi-Fi 또는 개인 VPN에서 사용하세요. SMB 포트를 인터넷에 공개하지 마세요.");form.addView(info);
        String[] names={"NAS 주소 (예: nas.local)","공유 이름 (예: study)","하위 폴더 (예: Shellground/progress-v1)","사용자 이름","비밀번호","도메인 (선택)"};
        String[] fields={"server","share","folder","username","password","domain"};EditText[] inputs=new EditText[fields.length];
        for(int i=0;i<inputs.length;i++){
            TextView label=new TextView(activity);label.setText(names[i]);label.setPadding(0,pad/2,0,0);form.addView(label);
            EditText input=new EditText(activity);input.setSingleLine(true);input.setText(config.optString(fields[i]));input.setInputType(InputType.TYPE_CLASS_TEXT|(i==4?InputType.TYPE_TEXT_VARIATION_PASSWORD:InputType.TYPE_TEXT_FLAG_NO_SUGGESTIONS));
            if(Build.VERSION.SDK_INT>=26)input.setImportantForAutofill(android.view.View.IMPORTANT_FOR_AUTOFILL_NO);
            form.addView(input);inputs[i]=input;
        }
        Button sync=new Button(activity);sync.setText("지금 NAS에 저장");sync.setOnClickListener(v->{lastNetwork=0;flush();Toast.makeText(activity,"저장 요청됨 · 받은 진도는 앱을 완전히 닫고 다시 열면 적용됩니다.",Toast.LENGTH_LONG).show();});form.addView(sync);
        ScrollView scroll=new ScrollView(activity);scroll.addView(form);
        AlertDialog dialog=new AlertDialog.Builder(activity).setTitle("NAS 학습 진도").setView(scroll)
            .setNegativeButton("닫기",null).setNeutralButton("연결 해제",null).setPositiveButton("연결·저장",null).create();dialog.show();
        dialog.getButton(AlertDialog.BUTTON_POSITIVE).setOnClickListener(v->{
            try{
                JSONObject candidate=new JSONObject().put("enabled",true);for(int i=0;i<fields.length;i++)candidate.put(fields[i],i==4?inputs[i].getText().toString():inputs[i].getText().toString().trim());
                dialog.dismiss();work(false,candidate);
            }catch(Exception error){Toast.makeText(activity,"입력 내용을 확인하세요.",Toast.LENGTH_SHORT).show();}
        });
        dialog.getButton(AlertDialog.BUTTON_NEUTRAL).setOnClickListener(v->{credentials.remove();config=new JSONObject();status="NAS 연결 해제 · 로컬 진도 유지";dialog.dismiss();});
    }
}
