package org.shellground.learn;

import android.app.*;
import android.content.*;
import android.graphics.Color;
import android.graphics.drawable.GradientDrawable;
import android.content.res.ColorStateList;
import android.os.*;
import android.view.*;
import android.view.inputmethod.InputMethodManager;
import android.widget.*;
import android.util.Base64;
import org.json.*;
import java.io.*;
import java.nio.charset.StandardCharsets;
import java.util.*;

/** Native mobile room using exported existing lessons and real guest grading. */
public final class LinuxActivity extends Activity {
    private final List<JSONObject> units=new ArrayList<>();
    private final LinkedHashMap<String,String> sessions=new LinkedHashMap<>();
    private SharedPreferences progress;
    private int index,phase,step,requestId,activePane,firstReply;
    private int[] randomReturn;
    private String session="";
    private boolean bound,ready,busy,solved,booting,foreground,prewarmPending;
    private long bootStarted;
    private boolean restartAfterStop,preparing;
    private String preparingLesson="";
    private View courseNavigation;
    private ProgressBar startupProgress;
    private boolean condaCourse,notebookCourse,setupMode;
    private NotebookEditor notebookEditor;
    private JSONObject courseData;
    private CondaAnswerForm condaAnswers;
    private String runtimeStatus="";
    private Messenger remote;
    private TextView title,status,lesson,assessment,completion;
    private Button start,grade,next;
    private FrameLayout workspace;
    private LinearLayout toolbar,tabBar,actionBar,rootLayout;
    private HorizontalScrollView shortcutBar;
    private boolean compactActions;
    private LinuxTerminalView terminal;
    private View[] panes;
    private Button[] tabButtons;
    private final Messenger replies=new Messenger(new Handler(Looper.getMainLooper(),message->{
        if(!bound)return true; // Ignore queued replies after leaving or cancelling this room.
        try{
            JSONObject result=new JSONObject(message.getData().getString("result","{}"));
            if(message.what==LinuxService.FRAME){if(session.equals(result.optString("session")))terminal.display(result);return true;}
            if(message.what==LinuxService.EVENT){
                if(result.has("startup"))status.setText(result.getString("startup"));
                if(result.has("error"))status.setText(result.getString("error"));
                if(result.has("ended"))status.setText("터미널이 종료되었습니다. 메뉴에서 새 터미널을 열 수 있습니다.");return true;
            }
            if(message.what!=LinuxService.RESULT)return false;
            if(message.arg1<firstReply)return true;
            if(result.optBoolean("stopping")){restartAfterStop=true;status.setText("이전 실습을 종료한 뒤 새 과정을 시작합니다…");return true;}
            if(result.has("error")){busy=false;preparing=false;status.setText(result.getString("error"));if(!ready)closeRoom();controls();return true;}
            if(result.optBoolean("ready")){booting=false;ready=true;if(setupMode){busy=true;controls();send("conda_setup",new JSONObject());}else prepare();return true;}
            if(result.has("session")){
                session=result.getString("session");sessions.put(session,"터미널 "+(sessions.size()+1));
                JSONObject prepared=result.optJSONObject("preparation");
                if(prepared!=null){preparing=false;if(!preparingLesson.equals(lessonIdentity())){prepare();return true;}}
                if(condaCourse&&prepared!=null){JSONObject actual=prepared.getJSONObject("runtime");runtimeStatus="실제 Linux guest · "+actual.getString("platform")+" · Conda "+actual.getString("conda_version");}
                if(notebookCourse&&prepared!=null){notebookEditor.kernels(prepared.getJSONArray("kernels"));notebookEditor.identity(prepared.getJSONObject("notebook").getJSONObject("identity"));}
                if(result.has("setup"))showSetup(result.getJSONObject("setup"));
                busy=false;resize(terminal.columns(),terminal.rows());status.setText(setupMode?"Miniconda 설치 실습":condaCourse?runtimeStatus:notebookCourse?"Jupyter · 학습 진도 자동 저장":"Linux · 학습 진도 자동 저장");if(bootStarted>0){long elapsed=(SystemClock.elapsedRealtime()-bootStarted)/1000;status.append(" · 준비 "+elapsed+"초");bootStarted=0;}controls();return true;
            }
            if(result.has("notebook_result")){busy=false;notebookEditor.result(result.getString("operation"),result.getJSONObject("notebook_result"));controls();return true;}
            if(result.has("grade")){
                busy=false;JSONObject evaluated=result.getJSONObject("grade");solved=evaluated.getBoolean("passed");
                StringBuilder text=new StringBuilder(solved?"목표를 완료했습니다.\n\n":"아직 남은 목표가 있습니다.\n\n");
                JSONArray checks=evaluated.getJSONArray("checks");
                for(int i=0;i<checks.length();i++){JSONObject check=checks.getJSONObject(i);text.append(check.optBoolean("passed")?"✓ ":"○ ").append(check.optString("label")).append('\n');
                    if(check.has("detail"))text.append(check.getString("detail")).append('\n');text.append('\n');}
                assessment.setText(text);if(solved){progress.edit().putBoolean(setupMode?"conda_install_once:done":key()+":done:"+variant(),true).apply();if(!setupMode)save();}
                updateCompletion();showPane(2);controls();return true;
            }
            if(result.has("copy")){((ClipboardManager)getSystemService(CLIPBOARD_SERVICE)).setPrimaryClip(ClipData.newPlainText("Linux 터미널",result.getString("copy")));Toast.makeText(this,"터미널 기록을 복사했습니다.",Toast.LENGTH_SHORT).show();}
            if(result.has("files")){busy=false;showFiles(result.getJSONObject("files"));controls();}
        }catch(Exception error){busy=false;status.setText(error.toString());controls();}return true;
    }));
    private final ServiceConnection connection=new ServiceConnection(){
        public void onServiceConnected(ComponentName name,IBinder binder){if(!bound)return;remote=new Messenger(binder);send("start",object("course",notebookCourse?"notebook":condaCourse?"conda":"linux"));}
        public void onServiceDisconnected(ComponentName name){
            if(bound){unbindService(this);bound=false;}
            remote=null;ready=false;booting=false;preparing=false;busy=false;firstReply=requestId+1;
            boolean retry=restartAfterStop&&foreground;restartAfterStop=false;
            status.setText("Linux 연결이 종료되었습니다. 다시 시작할 수 있습니다.");controls();
            if(retry)start();
        }
    };

    @Override public void onCreate(Bundle state){
        super.onCreate(state);condaCourse="conda".equals(getIntent().getStringExtra("course"));
        notebookCourse="notebook".equals(getIntent().getStringExtra("course"));
        prewarmPending=getIntent().getBooleanExtra("prewarm",false);
        TextView waiting=new TextView(this);waiting.setText("학습 진도를 불러오는 중…");setContentView(waiting);
        NasSync.get(this).startup(()->{if(!isFinishing()&&!isDestroyed())openStudy();});
    }
    private void openStudy(){
        progress=getSharedPreferences(notebookCourse?"real-notebook-progress-v1":condaCourse?"real-conda-progress-v1":"real-linux-progress-v1",MODE_PRIVATE);
        try(InputStream input=getAssets().open(notebookCourse?"notebook-course.json":condaCourse?"conda-course.json":"real-course.json")){
            ByteArrayOutputStream bytes=new ByteArrayOutputStream();byte[] block=new byte[8192];int n;
            while((n=input.read(block))!=-1)bytes.write(block,0,n);
            JSONObject course=new JSONObject(bytes.toString(StandardCharsets.UTF_8.name()));courseData=course;
            if(condaCourse&&course.getInt("schema")!=2)throw new IOException("지원하지 않는 Conda 자료 버전입니다.");
            JSONArray normal=course.getJSONArray("units"),reviews=condaCourse||notebookCourse?new JSONArray():course.getJSONArray("reviews");
            for(int i=0;i<normal.length();i++){
                JSONObject unit=normal.getJSONObject(i);units.add(unit);
                for(int j=0;j<reviews.length();j++){JSONObject review=reviews.getJSONObject(j);if(review.getString("after").equals(unit.getString("key")))units.add(review);}
            }
            String last=progress.getString("last","");for(int i=0;i<units.size();i++)if(units.get(i).getString("key").equals(last))index=i;
            restore();build();render();maybePrewarm();
        }catch(Exception error){TextView text=new TextView(this);text.setText("실습 자료를 열지 못했습니다.\n"+error);setContentView(text);}
    }
    private int dp(int value){return Math.round(value*getResources().getDisplayMetrics().density);}
    private LinearLayout row(){LinearLayout view=new LinearLayout(this);view.setOrientation(LinearLayout.HORIZONTAL);return view;}
    private LinearLayout column(){LinearLayout view=new LinearLayout(this);view.setOrientation(LinearLayout.VERTICAL);return view;}
    private GradientDrawable surface(int color,int border){GradientDrawable d=new GradientDrawable();d.setColor(color);d.setCornerRadius(dp(8));if(border!=0)d.setStroke(dp(1),border);return d;}
    private Button button(String text,Runnable action){Button b=new Button(this);b.setText(text);b.setTextSize(13);b.setAllCaps(false);b.setMinWidth(0);b.setMinimumWidth(0);b.setMinHeight(dp(48));b.setMinimumHeight(dp(48));b.setPadding(dp(8),0,dp(8),0);b.setStateListAnimator(null);b.setBackground(surface(Color.TRANSPARENT,0));
        b.setTextColor(new ColorStateList(new int[][]{new int[]{-android.R.attr.state_enabled},new int[]{}},new int[]{0xffa8b2b7,0xff202b33}));b.setOnClickListener(v->action.run());return b;}
    private TextView text(int size){TextView v=new TextView(this);v.setTextColor(0xff202b33);v.setTextSize(size);v.setPadding(dp(16),dp(12),dp(16),dp(12));v.setTextIsSelectable(true);return v;}
    private void build(){
        LinearLayout root=column();rootLayout=root;root.setBackgroundColor(Color.WHITE);setContentView(root);
        if(Build.VERSION.SDK_INT>=30)getWindow().setDecorFitsSystemWindows(false);
        root.setOnApplyWindowInsetsListener((v,insets)->{
            boolean keyboard;
            if(Build.VERSION.SDK_INT>=30){android.graphics.Insets safe=insets.getInsets(WindowInsets.Type.systemBars()|WindowInsets.Type.ime());v.setPadding(safe.left,safe.top,safe.right,safe.bottom);keyboard=insets.isVisible(WindowInsets.Type.ime());}
            else{v.setPadding(insets.getSystemWindowInsetLeft(),insets.getSystemWindowInsetTop(),insets.getSystemWindowInsetRight(),insets.getSystemWindowInsetBottom());keyboard=insets.getSystemWindowInsetBottom()>dp(160);}
            compact(keyboard);return insets;
        });root.requestApplyInsets();
        LinearLayout top=row();toolbar=top;root.addView(top);TextView brand=text(17);brand.setText("Shellground");top.addView(brand);
        top.addView(button("단원 선택",this::pickUnit),new LinearLayout.LayoutParams(0,dp(48),1));top.addView(button("메뉴",this::menu));
        courseNavigation=StudyNavigation.courses(this,notebookCourse?"notebook":condaCourse?"conda":"linux",go->{
            Runnable leave=()->{save();closeRoom();go.run();};
            if(ready&&!session.isEmpty())new AlertDialog.Builder(this).setMessage("과목을 바꾸면 현재 터미널과 임시 실습 파일은 종료됩니다. 학습 진도는 유지됩니다.").setNegativeButton("취소",null).setPositiveButton("과목 변경",(d,n)->leave.run()).show();else leave.run();
        });root.addView(courseNavigation);
        title=text(15);title.setMaxLines(2);root.addView(title);
        completion=text(12);completion.setTag("progress-summary");completion.setPadding(dp(16),0,dp(16),dp(6));root.addView(completion);
        LinearLayout tabs=row();tabBar=tabs;root.addView(tabs);
        tabs.setPadding(dp(8),dp(4),dp(8),dp(4));
        String[] names=notebookCourse?new String[]{"문제·설명","Bash","채점","노트북"}:new String[]{"문제·설명","터미널","채점"};
        tabButtons=new Button[names.length];for(int i=0;i<names.length;i++){int page=i;tabButtons[i]=button(names[i],()->showPane(page));tabs.addView(tabButtons[i],new LinearLayout.LayoutParams(0,dp(48),1));}
        workspace=new FrameLayout(this);workspace.setTag("linux-workspace");root.addView(workspace,new LinearLayout.LayoutParams(-1,0,1));
        lesson=text(15);ScrollView scroll=new ScrollView(this);LinearLayout question=column();question.addView(lesson);
        condaAnswers=new CondaAnswerForm(this);condaAnswers.setVisibility(View.GONE);question.addView(condaAnswers);
        scroll.addView(question);scroll.setFillViewport(true);
        terminal=new LinuxTerminalView(this,new LinuxTerminalView.Actions(){
            public void input(String text){if(ready&&!busy&&!session.isEmpty())send("input",object("data",Base64.encodeToString(text.getBytes(StandardCharsets.UTF_8),Base64.NO_WRAP)));}
            public void resize(int c,int r){LinuxActivity.this.resize(c,r);}
            public void scroll(int delta){if(ready)send("scroll",object("delta",delta));}
            public void copy(){if(ready)send("copy",new JSONObject());}
        });
        LinearLayout terminalPane=column();terminalPane.setBackgroundColor(0xff101b20);terminalPane.addView(terminal,new LinearLayout.LayoutParams(-1,0,1));
        HorizontalScrollView keys=new HorizontalScrollView(this);shortcutBar=keys;LinearLayout keyRow=row();keys.addView(keyRow);terminalPane.addView(keys);
        String[] labels={"Enter","Tab","Ctrl+C","Ctrl+O","Ctrl+X","Ctrl+K","Esc","↑","↓","←","→","맨 아래"};
        String[] inputs={"\r","\t","\u0003","\u000f","\u0018","\u000b","\u001b","\u001b[A","\u001b[B","\u001b[D","\u001b[C"};
        for(int i=0;i<labels.length;i++){final int k=i;Button b=button(labels[i],()->{if(k==inputs.length)send("live",new JSONObject());else send("input",object("data",Base64.encodeToString(inputs[k].getBytes(StandardCharsets.UTF_8),Base64.NO_WRAP)));});b.setTextColor(0xffc0d4df);keyRow.addView(b);}
        assessment=text(15);assessment.setTag("linux-assessment");assessment.setText("아직 채점하지 않았습니다.");ScrollView grades=new ScrollView(this);grades.addView(assessment);
        if(notebookCourse){
            notebookEditor=new NotebookEditor(this,new NotebookEditor.Actions(){
                public void perform(String operation,JSONObject arguments){try{busy=true;controls();send("notebook",new JSONObject().put("operation",operation).put("arguments",arguments));}catch(JSONException e){status.setText(e.toString());}}
                public void interrupt(){send("notebook_interrupt",new JSONObject());}
                public void changed(){solved=false;}
            });
            panes=new View[]{scroll,terminalPane,grades,notebookEditor};
        }else panes=new View[]{scroll,terminalPane,grades};
        for(int i=0;i<panes.length;i++){panes[i].setTag("linux-pane-"+i);workspace.addView(panes[i],new FrameLayout.LayoutParams(-1,-1));}
        workspace.addOnLayoutChangeListener((v,l,t,r,b,ol,ot,or,ob)->StudyNavigation.panes(this,workspace,panes,activePane));
        startupProgress=new ProgressBar(this,null,android.R.attr.progressBarStyleHorizontal);startupProgress.setIndeterminate(true);startupProgress.setTag("linux-startup-progress");root.addView(startupProgress,new LinearLayout.LayoutParams(-1,dp(3)));
        status=text(11);status.setMaxLines(2);status.setText("Linux · 학습 진도 자동 저장");root.addView(status);
        LinearLayout actions=row();actions.setPadding(dp(10),dp(4),dp(10),dp(8));actionBar=actions;root.addView(actions);
        start=button("실습 시작",this::start);grade=button("채점",()->{
            try{JSONObject request=new JSONObject();if(condaCourse)request.put("answers",condaAnswers.answers());if(notebookCourse)request.put("cells",notebookEditor.snapshot());busy=true;controls();send("grade",request);}
            catch(Exception error){status.setText(error.toString());}
        });next=button("다음",this::next);
        for(Button b:new Button[]{start,grade,next}){LinearLayout.LayoutParams p=new LinearLayout.LayoutParams(0,dp(48),1);p.setMargins(dp(3),0,dp(3),0);actions.addView(b,p);}
        start.setTag("linux-start");grade.setTag("linux-grade");next.setTag("linux-next");
        showPane(0);controls();
    }
    private JSONObject object(String key,Object value){try{return new JSONObject().put(key,value);}catch(JSONException e){throw new IllegalArgumentException(e);}}
    private JSONObject unit(){return units.get(index);}
    private String key(){return unit().optString("key");}
    private boolean completed(JSONObject unit){String key=unit.optString("key");return progress.getBoolean(key+":done:1",false)&&progress.getBoolean(key+":done:2",false);}
    private int variant(){return Math.max(0,Math.min(2,phase-1));}
    private JSONObject currentProblem(){try{return unit().getJSONArray("problems").getJSONObject(variant());}catch(JSONException e){throw new IllegalStateException(e);}}
    private JSONObject mission(){try{return notebookCourse?new JSONObject().put("kind","notebook").put("problem",currentProblem()):condaCourse?currentProblem().getJSONObject("mission"):currentProblem();}catch(JSONException e){throw new IllegalStateException(e);}}
    private void save(){
        if(randomReturn!=null||setupMode)return; // Random/installation rooms must not overwrite the saved return lesson.
        progress.edit().putString("last",key()).putInt(key()+":phase",phase).putInt(key()+":step",step).apply();
    }
    private void restore(){phase=Math.max(0,Math.min(3,progress.getInt(key()+":phase",0)));step=Math.max(0,progress.getInt(key()+":step",0));}
    private void render(){
        String label=phase==0?"배우기":phase==1?"예시 실습":"활용 "+(phase-1);
        title.setText(unit().optString("topic")+" · "+label+"\n"+(phase<2?unit().optString("title"):"목표를 보고 해결하세요"));
        if(notebookCourse){
            if(phase==0){JSONArray steps=unit().optJSONArray("learning_steps");step=Math.min(step,steps.length()-1);JSONObject page=steps.optJSONObject(step);
                lesson.setText((step+1)+" / "+steps.length()+" · "+page.optString("title")+"\n\n"+page.optString("explanation")+"\n\n"+courseData.optString("environment"));}
            else{
                StringBuilder text=new StringBuilder(currentProblem().optString("goal"));
                if(phase==1){text.append("\n\n예시 코드\n");JSONArray example=currentProblem().optJSONArray("solution");
                    for(int i=0;i<example.length();i++)text.append(example.optJSONObject(i).optString("source")).append("\n\n");
                    text.append("Bash 예시\n").append(CondaLesson.lines(currentProblem().optJSONArray("commands")));}
                text.append("\n\n").append(courseData.optString("environment"));lesson.setText(text);
            }
            if(!ready)notebookEditor.load(currentProblem().optJSONArray("cells"));
        }else if(condaCourse){
            try{
                if(phase==0){JSONArray steps=unit().getJSONArray("learning_steps");step=Math.min(step,steps.length()-1);JSONObject page=steps.getJSONObject(step);
                    lesson.setText((step+1)+" / "+steps.length()+" · "+page.getString("title")+"\n\n"+CondaLesson.step(page));}
                else lesson.setText(CondaLesson.problem(currentProblem(),phase==1));
                condaAnswers.show(phase==0?new JSONArray():currentProblem().getJSONArray("answer_fields"));
            }catch(JSONException error){throw new IllegalStateException(error);}
        }else if(phase==0){JSONArray steps=unit().optJSONArray("learning_steps");if(steps!=null&&steps.length()>0){step=Math.min(step,steps.length()-1);JSONObject page=steps.optJSONObject(step);lesson.setText((step+1)+" / "+steps.length()+" · "+page.optString("title")+"\n\n"+page.optString("explanation")+"\n\n직접 해볼 예시\n"+page.optString("commands")+"\n\n"+page.optString("observation"));}
            else lesson.setText(unit().optString("title")+"\n\n앞서 배운 내용을 조합해 목표를 해결합니다.\n\n"+mission().optString("prompt"));}
        else lesson.setText("시작 위치: "+mission().optString("start")+"\n\n목표\n"+mission().optString("prompt")+(phase==1?"\n\n예시\n"+mission().optString("solution"):""));
        if(phase==0&&step>0&&!ready)lesson.append("\n\n학습 위치만 복원됩니다. 실습 환경은 새로 준비하므로 필요한 이전 작업은 메뉴의 ‘앞 소단계 준비 보기’에서 확인하세요.");
        save();updateCompletion();controls();
    }
    private void updateCompletion(){completion.setText((setupMode?"설치 실습":randomReturn!=null?"올랜덤 연습":StudyNavigation.state(progress,key(),false))+"\n"+StudyNavigation.checks(progress,key(),false));}
    private void controls(){
        if(start==null)return;
        start.setEnabled(!busy||booting||preparing);start.setText(booting||preparing?"준비 취소":ready?(notebookCourse?"노트북":activePane==1?"단축키":"터미널"):"실습 시작");
        start.setBackground(surface(busy?0xffdce2e5:0xff16725d,0));start.setTextColor(busy?0xff64717b:Color.WHITE);
        startupProgress.setVisibility(booting||busy?View.VISIBLE:View.GONE);
        grade.setEnabled(ready&&!busy&&(phase>0||setupMode));next.setText(setupMode?"단원 복귀":"다음");
        next.setEnabled((!busy||preparing)&&(setupMode||phase==0||solved||progress.getBoolean(key()+":done:"+variant(),false)));
        next.setBackground(surface(0xffe5f1ec,0));if(notebookEditor!=null)notebookEditor.available(ready&&!busy);
    }
    private void showPane(int pane){activePane=pane;for(int i=0;i<panes.length;i++){panes[i].setVisibility(i==pane?View.VISIBLE:View.GONE);tabButtons[i].setBackground(surface(i==pane?0xffe5f1ec:Color.TRANSPARENT,0));tabButtons[i].setTextColor(i==pane?0xff16725d:0xff64717b);}
        StudyNavigation.panes(this,workspace,panes,pane);
        if(pane!=1&&pane!=3)((InputMethodManager)getSystemService(INPUT_METHOD_SERVICE)).hideSoftInputFromWindow(terminal.getWindowToken(),0);else if(pane==1)terminal.requestFocus();controls();}
    private void compact(boolean keyboard){
        if(toolbar==null||actionBar==null)return;
        boolean landscape=getResources().getConfiguration().orientation==android.content.res.Configuration.ORIENTATION_LANDSCAPE;
        toolbar.setVisibility(keyboard?View.GONE:View.VISIBLE);title.setVisibility(keyboard||landscape?View.GONE:View.VISIBLE);status.setVisibility(keyboard||landscape?View.GONE:View.VISIBLE);
        courseNavigation.setVisibility(keyboard?View.GONE:View.VISIBLE);completion.setVisibility(keyboard||landscape?View.GONE:View.VISIBLE);
        boolean combine=landscape;
        shortcutBar.setVisibility(combine?View.GONE:View.VISIBLE);
        if(combine!=compactActions){((ViewGroup)actionBar.getParent()).removeView(actionBar);compactActions=combine;
            actionBar.setPadding(combine?0:dp(10),combine?0:dp(4),combine?0:dp(10),combine?0:dp(8));
            if(combine)tabBar.addView(actionBar,new LinearLayout.LayoutParams(0,dp(48),3));else rootLayout.addView(actionBar,new LinearLayout.LayoutParams(-1,-2));}
    }
    private void shortcuts(){
        String[] names={"Enter","Tab","Ctrl+C · 중단","Ctrl+O · 저장","Ctrl+X · 나가기","Ctrl+K · 줄 삭제","Esc","↑","↓","←","→"};
        String[] keys={"\r","\t","\u0003","\u000f","\u0018","\u000b","\u001b","\u001b[A","\u001b[B","\u001b[D","\u001b[C"};
        new AlertDialog.Builder(this).setTitle("터미널 키").setItems(names,(d,n)->send("input",object("data",Base64.encodeToString(keys[n].getBytes(StandardCharsets.UTF_8),Base64.NO_WRAP)))).show();
    }
    private void maybePrewarm(){
        if(foreground&&rootLayout!=null&&prewarmPending){prewarmPending=false;start();}
    }
    @Override protected void onResume(){super.onResume();foreground=true;maybePrewarm();}
    private void start(){
        if(booting||preparing){closeRoom();status.setText("Linux 준비를 취소했습니다. 설명은 계속 읽을 수 있습니다.");controls();return;}
        if(ready){if(notebookCourse)showPane(3);else if(activePane==1)shortcuts();else showPane(1);return;}
        if(bound)return;
        booting=true;busy=false;bootStarted=SystemClock.elapsedRealtime();controls();status.setText("Linux 준비 중 · 설명을 읽거나 단원을 선택할 수 있습니다.");
        Intent service=new Intent(this,LinuxService.class);
        try{
            // Start while this Activity is foreground. Keep the service alive
            // briefly after unbind so Android's cached-process freezer cannot
            // suspend the bounded VM shutdown halfway through. No sticky restart.
            startService(service);
            bound=bindService(service,connection,BIND_AUTO_CREATE);
            if(!bound)throw new IllegalStateException("실습 서비스를 연결하지 못했습니다.");
        }catch(Exception error){
            stopService(service);booting=false;busy=false;status.setText(error.toString());controls();
        }
    }
    private void send(String action,JSONObject request){
        if(remote==null)return;
        if(Arrays.asList("input","live","copy","scroll").contains(action)&&(!ready||busy||session.isEmpty()))return;
        try{request.put("action",action);String raw=request.toString();if(raw.getBytes(StandardCharsets.UTF_8).length>512*1024)throw new IllegalArgumentException("한 번에 전송할 코드가 너무 큽니다. 셀을 나누거나 줄여 주세요.");Message message=Message.obtain(null,LinuxService.REQUEST);message.arg1=++requestId;message.replyTo=replies;Bundle data=new Bundle();data.putString("request",raw);message.setData(data);remote.send(message);}
        catch(Exception error){busy=false;status.setText(error.toString());controls();}
    }
    private void resize(int c,int r){if(ready)try{send("resize",new JSONObject().put("columns",c).put("rows",r));}catch(JSONException ignored){}}
    private String lessonIdentity(){return key()+":"+variant();}
    private void prepare(){
        if(preparing)return; // The current request will prepare the latest selected lesson when it completes.
        preparing=true;preparingLesson=lessonIdentity();setupMode=false;sessions.clear();session="";solved=false;busy=true;
        if(notebookCourse)notebookEditor.load(currentProblem().optJSONArray("cells"));controls();status.setText("문제 환경을 준비하고 있습니다…");send("prepare",object("mission",mission()));
    }
    private void next(){
        if(setupMode){setupMode=false;render();showPane(0);if(ready)prepare();return;}
        if(randomReturn!=null){randomNext();return;}
        JSONArray pages=unit().optJSONArray("learning_steps");
        if(phase==0&&pages!=null&&step+1<pages.length()){step++;render();showPane(0);return;}
        if(phase<3){phase++;step=0;}else{index=(index+1)%units.size();restore();}
        solved=false;render();showPane(0);if(ready)prepare();
    }
    private void pickUnit(){
        if(busy&&!preparing)return;
        StudyNavigation.pick(this,units,index,progress,false,at->{
            if((busy&&!preparing)||at==index)return;index=at;randomReturn=null;restore();solved=false;render();showPane(0);if(ready)prepare();
        });
    }
    private void menu(){
        List<String> items=new ArrayList<>(Arrays.asList("힌트","문제 다시 시작","새 터미널","터미널 선택","전체 기록 복사","배운 범위 올랜덤","올랜덤 종료·복귀","실습 종료"));
        if(phase==0){items.add("이전 소단계");items.add("앞 소단계 준비 보기");}
        if(condaCourse){items.add("실습 파일 보기");items.add("Conda 설치·실행 안내");items.add("Miniconda 설치 실습");}
        items.add("NAS 진도 동기화");
        new AlertDialog.Builder(this).setItems(items.toArray(new String[0]),(dialog,which)->{
            String chosen=items.get(which);
            if(chosen.equals("NAS 진도 동기화")){NasSync.get(this).settings(this);return;}
            if(chosen.equals("Miniconda 설치 실습")){if(!busy){setupMode=true;solved=false;if(ready){busy=true;controls();send("conda_setup",new JSONObject());}else start();}return;}
            if(chosen.equals("Conda 설치·실행 안내")){try{showText("Conda 설치·실행 안내",CondaLesson.bootstrap(courseData));}catch(JSONException error){status.setText(error.toString());}return;}
            if(chosen.equals("실습 파일 보기")){if(ready&&!busy){busy=true;controls();send("files",new JSONObject());}else Toast.makeText(this,"실습 시작 후 파일을 볼 수 있습니다.",Toast.LENGTH_SHORT).show();return;}
            if(busy&&which!=0&&which!=7)return;
            if(which==0)new AlertDialog.Builder(this).setTitle("힌트").setMessage((condaCourse?currentProblem():unit()).optString("hint","앞서 배운 설명과 목표 조건을 비교하세요.")).setPositiveButton("닫기",null).show();
            if(which==1&&ready)new AlertDialog.Builder(this).setMessage("이번 문제의 실습 파일과 터미널을 초기화할까요? 학습 완료 기록은 유지됩니다.").setPositiveButton("다시 시작",(d,n)->{if(setupMode){busy=true;controls();send("conda_setup",new JSONObject());}else prepare();}).setNegativeButton("취소",null).show();
            if(which==2&&ready){busy=true;controls();send("open",new JSONObject());}
            if(which==3){String[] ids=sessions.keySet().toArray(new String[0]);new AlertDialog.Builder(this).setTitle("터미널 선택").setItems(sessions.values().toArray(new String[0]),(d,n)->{session=ids[n];send("select",object("session",session));showPane(1);}).show();}
            if(which==4)send("copy",new JSONObject());
            if(which==5)randomNext();
            if(which==6&&randomReturn!=null){index=randomReturn[0];phase=randomReturn[1];step=randomReturn[2];randomReturn=null;render();showPane(0);if(ready)prepare();}
            if(which==7)finish();
            if(which==8)previousStep();
            if(which==9)new AlertDialog.Builder(this).setTitle("앞 소단계 준비").setMessage(preparationText()).setPositiveButton("닫기",null).show();
        }).show();
    }
    private void previousStep(){
        if(phase!=0||busy)return;
        if(step==0){Toast.makeText(this,"첫 소단계입니다.",Toast.LENGTH_SHORT).show();return;}
        step--;render();showPane(0); // Reading earlier instructions must not reset a live guest.
    }
    private void showSetup(JSONObject actual)throws JSONException{
        setupMode=true;solved=false;sessions.clear();sessions.put(session,"설치 실습");
        JSONObject installer=actual.getJSONObject("installer");String prefix=actual.getString("prefix");
        JSONObject definition=courseData.getJSONObject("bootstrap").getJSONObject("optional_install_exercise");
        String goal="시작 위치: "+actual.getString("start")+"\n\n목표\n"+definition.getString("goal")+
            "\n\n이번 설치 경로: "+prefix+"\n보존할 관리 환경: /opt/shellground/miniconda\n\n"+
            "공식 설치 파일: "+installer.getString("path")+"\n출처: "+installer.getString("url")+
            "\nSHA256: "+installer.getString("sha256")+"\n\n"+definition.getString("explanation");
        title.setText("Conda · Miniconda 설치 실습");condaAnswers.show(new JSONArray());lesson.setText(goal);showPane(0);
        TextView license=text(13);license.setText(installer.getString("license"));ScrollView scroll=new ScrollView(this);scroll.addView(license);
        new AlertDialog.Builder(this).setTitle("설치 라이선스 확인").setView(scroll)
            .setPositiveButton("동의하고 명령 보기",(d,n)->{
                String commands=CondaLesson.lines(definition.optJSONArray("reference_commands"))
                    .replace("{{installer_path}}",installer.optString("path")).replace("{{student_install_prefix}}",prefix);
                lesson.setText(goal+"\n\n직접 실행할 명령\n"+commands+"\n\n관리용 base와 기존 설정 파일은 변경하지 마세요.");
            }).setNegativeButton("동의하지 않음",(d,n)->{setupMode=false;render();if(ready)prepare();}).show();
    }
    private String preparationText(){
        if(phase!=0||step==0)return "앞서 준비할 소단계가 없습니다.";
        StringBuilder text=new StringBuilder("진도 위치는 저장되지만 종료 전 파일·셸 상태는 복원되지 않습니다. 새 실습에서는 아래에서 필요한 준비를 직접 다시 수행하세요.\n\n현재 실습을 계속 쓰고 있다면 생성·삭제 같은 작업을 무조건 반복하지 말고 실제 상태부터 확인하세요. 이 안내는 명령을 자동 실행하거나 완료 처리하지 않습니다.\n");
        JSONArray pages=unit().optJSONArray("learning_steps");
        if(pages!=null)for(int i=0;i<Math.min(step,pages.length());i++){
            JSONObject part=pages.optJSONObject(i);
            if(condaCourse){text.append('\n').append(i+1).append(" · ").append(part.optString("title")).append('\n').append(CondaLesson.step(part)).append('\n');continue;}
            text.append('\n').append(i+1).append(" · ").append(part.optString("title")).append('\n')
                .append(part.optString("explanation")).append("\n\n").append(part.optString("commands"))
                .append('\n').append(part.optString("observation")).append('\n');
        }
        return text.toString();
    }
    private void showText(String heading,String content){
        TextView text=text(14);text.setText(content);ScrollView scroll=new ScrollView(this);scroll.addView(text);
        new AlertDialog.Builder(this).setTitle(heading).setView(scroll).setPositiveButton("닫기",null).show();
    }
    private void showFiles(JSONObject response)throws JSONException{
        if(response.has("text")){showText(response.getString("path"),response.getString("text")+(response.optBoolean("truncated")?"\n\n[표시 크기 제한으로 뒷부분 생략]":""));return;}
        JSONArray files=response.getJSONArray("files");String[] names=new String[files.length()];for(int i=0;i<names.length;i++)names[i]=files.getString(i);
        if(names.length==0){showText("실습 파일",response.optBoolean("truncated")?"조회 한도 안에서 표시할 일반 파일이 없습니다.":"실습 폴더에 아직 파일이 없습니다.");return;}
        new AlertDialog.Builder(this).setTitle(response.optBoolean("truncated")?"실습 파일 (일부 목록)":"실습 파일 · 읽기 전용")
            .setItems(names,(d,n)->{busy=true;controls();send("files",object("path",names[n]));}).setNegativeButton("닫기",null).show();
    }
    private void randomNext(){
        List<Integer> candidates=new ArrayList<>();for(int i=0;i<units.size();i++)if(completed(units.get(i)))candidates.add(i);
        if(candidates.isEmpty()){Toast.makeText(this,"완료한 단원부터 올랜덤에 포함됩니다.",Toast.LENGTH_LONG).show();return;}
        if(randomReturn==null){save();randomReturn=new int[]{index,phase,step};}
        index=candidates.get(new Random().nextInt(candidates.size()));phase=2+new Random().nextInt(2);step=0;
        solved=false;render();showPane(0);if(ready)prepare();
    }
    private void closeRoom(){
        if(bound){send("stop",new JSONObject());unbindService(connection);bound=false;}
        // If binding was cancelled before the Messenger arrived there is no
        // stop message. No VM has been requested in that case.
        if(remote==null)stopService(new Intent(this,LinuxService.class));
        remote=null;ready=false;busy=false;booting=false;preparing=false;restartAfterStop=false;bootStarted=0;firstReply=requestId+1;
    }
    @Override protected void onStop(){
        foreground=false;
        if(progress!=null&&!units.isEmpty())save();
        closeRoom();
        NasSync.get(this).flush();super.onStop();
    }
    @Override protected void onRestart(){super.onRestart();prewarmPending=getIntent().getBooleanExtra("prewarm",false);controls();if(status!=null)status.setText("학습 위치를 복원했습니다.");}
}
