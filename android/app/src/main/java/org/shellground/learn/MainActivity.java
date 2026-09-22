package org.shellground.learn;

import android.app.*;
import android.content.*;
import android.content.res.Configuration;
import android.graphics.*;
import android.graphics.drawable.GradientDrawable;
import android.content.res.ColorStateList;
import android.os.*;
import android.text.InputType;
import android.text.TextUtils;
import android.view.*;
import android.view.inputmethod.InputMethodManager;
import android.view.inputmethod.EditorInfo;
import android.widget.*;
import java.nio.charset.StandardCharsets;
import java.io.InputStream;
import java.io.ByteArrayOutputStream;
import java.util.*;
import org.json.*;

/** Native study screen. Optional private NAS sync; no external Python app. */
public final class MainActivity extends Activity {
    private JSONArray units, quizzes, cards;
    private int index=0,phase=0,step=0,variant=0,requestId=0;
    private int[] randomReturn=null;
    private boolean solved=false,busy=false,bound=false;
    private SharedPreferences progress;
    private static final int INK=0xff202b33, MUTED=0xff64717b, GREEN=0xff16725d,
        PAPER=0xfff5f6f8, LINE=0xffdce2e5, TERMINAL=0xff111d25;
    private TextView heading,unitTitle,phaseLabel,status,output,outputEmpty,gradeSummary,completion;
    private LinearLayout root,toolbar,lessonHeader,questionContent,gradeContent,actionRow,progressTrack,codeTitle,codeKeys,statusRow,tabRow,bottom;
    private FrameLayout workspace;
    private final View[] panes=new View[4];
    private final Button[] tabs=new Button[4];
    private Button unitPicker,more;
    private int activePane=0;
    private boolean keyboardVisible=false,compactActions=false;
    private EditText editor;
    private ImageView image;
    private Spinner figurePicker;
    private JSONArray figurePaths=new JSONArray();
    private Button execute,grade,next,stop;
    private String feedback="아직 채점하지 않았습니다.",pending=null;
    private Messenger service;
    private final Handler handler=new Handler(Looper.getMainLooper());
    private final Runnable timeout=()->{ cancelWorker(); output.setText("실행 시간이 초과되어 Python만 중단했습니다. 입력 코드는 남아 있습니다."); showPane(2); };
    private final Messenger replies=new Messenger(new Handler(Looper.getMainLooper(),message->{
        if(message.what!=PythonService.RESULT || message.arg1!=requestId) return true;
        handler.removeCallbacks(timeout); busy=false; controls();
        try {
            JSONObject result=new JSONObject(message.getData().getString("result","{}"));
            if(result.has("grade")) showGrade(result.getJSONObject("grade"));
            else {
                solved=false;
                output.append("\n"+result.optString("output",""));
                if(output.length()>70000) output.setText(output.getText().subSequence(output.length()-65000,output.length()));
                showFigures(result);
                JSONArray previewErrors=result.optJSONArray("preview_errors");
                if(previewErrors!=null&&previewErrors.length()>0)output.append("\n그래프 표시 오류: "+previewErrors.toString());
                outputEmpty.setText(result.optBoolean("ok")?"실행을 마쳤습니다.\n화면 출력이 없는 코드입니다. 결과는 채점으로 확인할 수 있습니다.":"실행 결과를 확인하세요.");
                showPane(2);
            }
        } catch(Exception error) { output.setText(error.toString()); }
        controls(); return true;
    }));
    private final ServiceConnection connection=new ServiceConnection() {
        @Override public void onServiceConnected(ComponentName name,IBinder binder) {
            service=new Messenger(binder);
            if(pending!=null) { String request=pending; pending=null; send(request); }
        }
        @Override public void onServiceDisconnected(ComponentName name) {
            service=null;
            if(busy) { busy=false; handler.removeCallbacks(timeout); output.append("\nPython 프로세스가 종료되었습니다. 다시 실행하면 새 실습을 준비합니다."); controls(); }
        }
    };

    @Override public void onCreate(Bundle state) {
        super.onCreate(state);
        if(Intent.ACTION_MAIN.equals(getIntent().getAction())&&BuildConfig.LINUX_RUNTIME&&Build.VERSION.SDK_INT>=28){
            startActivity(new Intent(this,LinuxActivity.class).putExtra("prewarm",true));finish();return;
        }
        TextView waiting=new TextView(this);waiting.setText("학습 진도를 불러오는 중…");setContentView(waiting);
        NasSync.get(this).startup(()->{if(!isFinishing()&&!isDestroyed())openStudy();});
    }
    private void openStudy(){
        progress=getSharedPreferences("python-progress-v1",MODE_PRIVATE);
        try {
            ByteArrayOutputStream bytes=new ByteArrayOutputStream();
            try(InputStream input=getAssets().open("python-course.json")) {
                byte[] buffer=new byte[8192]; int count;
                while((count=input.read(buffer))!=-1) bytes.write(buffer,0,count);
            }
            JSONObject data=new JSONObject(new String(bytes.toByteArray(),StandardCharsets.UTF_8));
            units=data.getJSONArray("lessons"); quizzes=data.getJSONArray("quizzes"); cards=data.getJSONArray("concept_cards");
            String last=progress.getString("last","");
            for(int i=0;i<units.length();i++) if(units.getJSONObject(i).getString("key").equals(last)) index=i;
        } catch(Exception error) {
            TextView failure=new TextView(this); failure.setText("학습 자료를 열지 못했습니다.\n"+error); setContentView(failure); return;
        }
        buildScreen();
        loadPosition(); render();
    }
    private void buildScreen(){
        root=vertical(); root.setBackgroundColor(PAPER); root.setFocusableInTouchMode(true);
        setContentView(root);
        if(Build.VERSION.SDK_INT>=30) getWindow().setDecorFitsSystemWindows(false);
        root.setOnApplyWindowInsetsListener((view,insets)->{
            int left,top,right,bottom;
            if(Build.VERSION.SDK_INT>=30){
                android.graphics.Insets safe=insets.getInsets(WindowInsets.Type.systemBars()|WindowInsets.Type.ime());
                left=safe.left;top=safe.top;right=safe.right;bottom=safe.bottom;
                keyboardVisible=insets.isVisible(WindowInsets.Type.ime());
            }else{
                left=insets.getSystemWindowInsetLeft();top=insets.getSystemWindowInsetTop();
                right=insets.getSystemWindowInsetRight();bottom=insets.getSystemWindowInsetBottom();
                keyboardVisible=bottom>dp(160);
            }
            view.setPadding(left,top,right,bottom); compactHeader();
            return Build.VERSION.SDK_INT>=30?WindowInsets.CONSUMED:insets;
        });
        root.setSystemUiVisibility(View.SYSTEM_UI_FLAG_LIGHT_STATUS_BAR|View.SYSTEM_UI_FLAG_LIGHT_NAVIGATION_BAR);
        root.requestApplyInsets();
        toolbar=row(); toolbar.setGravity(Gravity.CENTER_VERTICAL); toolbar.setPadding(dp(18),0,dp(8),0);
        root.addView(toolbar,new LinearLayout.LayoutParams(-1,dp(52)));
        TextView brand=text(13);brand.setSingleLine(true);brand.setText("›_ SHELLGROUND");brand.setTypeface(Typeface.MONOSPACE,Typeface.BOLD);toolbar.addView(brand,weight());
        more=button("⋮",this::menu);more.setTextSize(26);more.setContentDescription("학습 메뉴");more.setTag("more");
        toolbar.addView(more,new LinearLayout.LayoutParams(dp(48),dp(48)));
        root.addView(StudyNavigation.courses(this,"python",go->replaceCode(()->{save();cancelWorker();go.run();})));

        lessonHeader=vertical();lessonHeader.setPadding(dp(20),dp(4),dp(16),dp(12));root.addView(lessonHeader);
        LinearLayout meta=row();meta.setGravity(Gravity.CENTER_VERTICAL);lessonHeader.addView(meta);
        heading=text(12);heading.setTextColor(MUTED);meta.addView(heading,weight());
        phaseLabel=text(11);phaseLabel.setTextColor(GREEN);phaseLabel.setPadding(dp(8),dp(4),dp(8),dp(4));phaseLabel.setBackground(shape(0xffe1eee9,6,0));meta.addView(phaseLabel);
        unitTitle=text(19);unitTitle.setTypeface(null,Typeface.BOLD);unitTitle.setLineSpacing(dp(2),1);unitTitle.setMaxLines(2);
        unitTitle.setPadding(0,dp(8),0,dp(6));unitTitle.setTag("unit-title");lessonHeader.addView(unitTitle);
        progressTrack=row();lessonHeader.addView(progressTrack,new LinearLayout.LayoutParams(-1,dp(3)));
        completion=text(12);completion.setTag("progress-summary");completion.setPadding(0,dp(6),0,0);lessonHeader.addView(completion);
        unitPicker=button("단원 선택  ⌄",this::pickUnit);unitPicker.setTextSize(12);unitPicker.setTag("unit-picker");
        // The full title remains readable; the separate 48dp target opens all units.
        toolbar.addView(unitPicker,1,new LinearLayout.LayoutParams(-2,dp(48)));

        tabRow=row();tabRow.setBackgroundColor(Color.WHITE);tabRow.setPadding(dp(8),dp(4),dp(8),dp(4));root.addView(tabRow);
        String[] names={"설명","코드","출력","채점"};
        for(int i=0;i<4;i++){final int page=i;tabs[i]=button(names[i],()->showPane(page));tabs[i].setTag("tab-"+i);tabRow.addView(tabs[i],new LinearLayout.LayoutParams(0,dp(48),1));}
        workspace=new FrameLayout(this);workspace.setTag("workspace");workspace.setBackgroundColor(Color.WHITE);
        root.addView(workspace,new LinearLayout.LayoutParams(-1,0,1));
        workspace.addOnLayoutChangeListener((v,l,t,r,b,ol,ot,or,ob)->{if(panes[3]!=null)StudyNavigation.panes(this,workspace,panes,activePane);});
        ScrollView questionScroll=new ScrollView(this);questionScroll.setFillViewport(true);questionScroll.setTag("question-scroll");
        questionContent=vertical();questionContent.setPadding(dp(20),dp(22),dp(20),dp(24));questionScroll.addView(questionContent);panes[0]=questionScroll;

        LinearLayout code=vertical();code.setBackgroundColor(TERMINAL);panes[1]=code;
        codeTitle=row();codeTitle.setPadding(dp(16),0,dp(10),0);codeTitle.setGravity(Gravity.CENTER_VERTICAL);code.addView(codeTitle,new LinearLayout.LayoutParams(-1,dp(42)));
        TextView file=text(12);file.setText("practice.py");file.setTextColor(0xffa1b4c1);file.setTypeface(Typeface.MONOSPACE);codeTitle.addView(file,weight());
        TextView runtime=text(11);runtime.setText("●  Python");runtime.setTextColor(0xff7ad7b1);codeTitle.addView(runtime);
        editor=new EditText(this);editor.setTag("code-editor");editor.setTextSize(15);editor.setTypeface(Typeface.MONOSPACE);
        editor.setTextColor(0xffe2ede9);editor.setBackgroundColor(TERMINAL);editor.setPadding(dp(16),dp(10),dp(16),dp(16));
        editor.setGravity(Gravity.TOP|Gravity.START); editor.setSingleLine(false);
        editor.setInputType(InputType.TYPE_CLASS_TEXT|InputType.TYPE_TEXT_FLAG_MULTI_LINE|InputType.TYPE_TEXT_FLAG_NO_SUGGESTIONS);
        editor.setImeOptions(EditorInfo.IME_FLAG_NO_EXTRACT_UI|EditorInfo.IME_FLAG_NO_PERSONALIZED_LEARNING);
        editor.setHint("# 여기에 코드를 입력하세요");editor.setHintTextColor(0xff7d929f);editor.setHorizontallyScrolling(true);editor.setLineSpacing(dp(4),1);
        if(Build.VERSION.SDK_INT>=26)editor.setImportantForAutofill(View.IMPORTANT_FOR_AUTOFILL_NO);
        code.addView(editor,new LinearLayout.LayoutParams(-1,0,1));
        codeKeys=row();codeKeys.setPadding(dp(8),0,dp(8),dp(4));code.addView(codeKeys);
        String[] keyLabels={"들여쓰기",":","( )","[ ]","\" \""};String[] inserts={"    ",":","()","[]","\"\""};
        for(int i=0;i<keyLabels.length;i++){final String insertion=inserts[i];Button b=button(keyLabels[i],()->insertCode(insertion));b.setTextColor(0xffc0d4df);b.setTextSize(12);codeKeys.addView(b,new LinearLayout.LayoutParams(0,dp(48),i==0?1.6f:1));}

        ScrollView resultsScroll=new ScrollView(this);resultsScroll.setFillViewport(true);panes[2]=resultsScroll;
        LinearLayout results=vertical();results.setPadding(dp(18),dp(20),dp(18),dp(24));resultsScroll.addView(results);
        outputEmpty=text(15);outputEmpty.setText("아직 실행 결과가 없습니다.\n코드 탭에서 입력한 뒤 실행해 보세요.");outputEmpty.setTextColor(MUTED);outputEmpty.setPadding(0,dp(24),0,dp(24));results.addView(outputEmpty);
        output=text(14);output.setTag("output");output.setTypeface(Typeface.MONOSPACE);output.setTextIsSelectable(true);output.setLineSpacing(dp(4),1);results.addView(output);
        figurePicker=new Spinner(this);figurePicker.setVisibility(View.GONE);results.addView(figurePicker);
        figurePicker.setOnItemSelectedListener(new SimpleSelection(){public void onItemSelected(AdapterView<?> p,View v,int at,long id){showFigure(at);}});
        image=new ImageView(this); image.setAdjustViewBounds(true);image.setScaleType(ImageView.ScaleType.FIT_CENTER); image.setVisibility(View.GONE); results.addView(image,new LinearLayout.LayoutParams(-1,-2));
        ScrollView gradeScroll=new ScrollView(this);gradeScroll.setFillViewport(true);panes[3]=gradeScroll;
        gradeContent=vertical();gradeContent.setPadding(dp(20),dp(24),dp(20),dp(24));gradeScroll.addView(gradeContent);
        for(int i=0;i<panes.length;i++){panes[i].setTag("pane-"+i);workspace.addView(panes[i],new FrameLayout.LayoutParams(-1,-1));}
        bottom=vertical();bottom.setPadding(dp(12),dp(6),dp(12),dp(10));root.addView(bottom);
        statusRow=row();statusRow.setGravity(Gravity.CENTER_VERTICAL);bottom.addView(statusRow,new LinearLayout.LayoutParams(-1,dp(24)));
        status=text(11);status.setTextColor(MUTED);status.setSingleLine(true);status.setEllipsize(TextUtils.TruncateAt.END);statusRow.addView(status,weight());
        actionRow=row();bottom.addView(actionRow);
        execute=button("실행",this::run);execute.setTag("run");grade=button("채점",()->request("grade"));grade.setTag("grade");next=button("다음",this::advance);next.setTag("next");
        stop=button("중단",this::cancelWorker);stop.setTag("stop");
        for(Button b:new Button[]{execute,stop,grade,next}){LinearLayout.LayoutParams p=new LinearLayout.LayoutParams(0,dp(48),1);p.setMargins(dp(3),0,dp(3),0);actionRow.addView(b,p);}
        renderGrade(null);showPane(0);
    }
    private int dp(float value){return Math.round(value*getResources().getDisplayMetrics().density);}
    private LinearLayout vertical(){ LinearLayout l=new LinearLayout(this); l.setOrientation(LinearLayout.VERTICAL); return l; }
    private LinearLayout row(){ LinearLayout l=new LinearLayout(this); l.setOrientation(LinearLayout.HORIZONTAL); return l; }
    private LinearLayout.LayoutParams weight(){ return new LinearLayout.LayoutParams(0,-2,1); }
    private TextView text(int size){TextView t=new TextView(this);t.setTextSize(size);t.setTextColor(INK);t.setIncludeFontPadding(false);return t;}
    private GradientDrawable shape(int color,int radius,int stroke){GradientDrawable d=new GradientDrawable();d.setColor(color);d.setCornerRadius(dp(radius));if(stroke!=0)d.setStroke(dp(1),stroke);return d;}
    private Button button(String label,Runnable action){
        Button b=new Button(this);b.setText(label);b.setTextSize(14);b.setAllCaps(false);b.setMinWidth(0);b.setMinimumWidth(0);b.setMinHeight(dp(48));b.setMinimumHeight(dp(48));
        b.setPadding(dp(8),0,dp(8),0);b.setStateListAnimator(null);b.setBackground(shape(Color.TRANSPARENT,8,0));
        b.setTextColor(new ColorStateList(new int[][]{new int[]{-android.R.attr.state_enabled},new int[]{}},new int[]{0xffa8b2b7,INK}));
        b.setOnClickListener(v->action.run());return b;
    }
    private void compactHeader(){
        if(lessonHeader==null)return;
        boolean compact=keyboardVisible||getResources().getConfiguration().screenHeightDp<440;
        lessonHeader.setVisibility(compact?View.GONE:View.VISIBLE);
        toolbar.setVisibility(keyboardVisible?View.GONE:View.VISIBLE);
        root.findViewWithTag("course-navigation").setVisibility(keyboardVisible?View.GONE:View.VISIBLE);
        boolean shortScreen=getResources().getConfiguration().screenHeightDp<620;
        if(codeTitle!=null)codeTitle.setVisibility(compact||shortScreen?View.GONE:View.VISIBLE);
        if(statusRow!=null)statusRow.setVisibility(compact||shortScreen||activePane==3?View.GONE:View.VISIBLE);
        if(codeKeys!=null)codeKeys.setVisibility(compact&&getResources().getConfiguration().screenHeightDp<620?View.GONE:View.VISIBLE);
        // In landscape the IME may leave only ~160dp. Share one control strip
        // instead of trapping the editor between separate top and bottom bars.
        boolean combine=keyboardVisible&&getResources().getConfiguration().orientation==Configuration.ORIENTATION_LANDSCAPE;
        if(actionRow!=null&&combine!=compactActions){
            ((ViewGroup)actionRow.getParent()).removeView(actionRow);compactActions=combine;
            if(combine){tabRow.addView(actionRow,new LinearLayout.LayoutParams(0,dp(48),3));bottom.setVisibility(View.GONE);}
            else{bottom.addView(actionRow,new LinearLayout.LayoutParams(-1,-2));bottom.setVisibility(View.VISIBLE);}
        }
    }
    @Override public void onConfigurationChanged(Configuration configuration){super.onConfigurationChanged(configuration);compactHeader();}
    private void hideKeyboard(){editor.clearFocus();((InputMethodManager)getSystemService(INPUT_METHOD_SERVICE)).hideSoftInputFromWindow(editor.getWindowToken(),0);}
    private void showPane(int selected){
        activePane=selected;
        if(editor!=null&&selected!=1)hideKeyboard();
        for(int i=0;i<4;i++){
            panes[i].setVisibility(i==selected?View.VISIBLE:View.GONE);tabs[i].setSelected(i==selected);
            tabs[i].setBackground(shape(i==selected?0xffe5f1ec:Color.TRANSPARENT,8,0));tabs[i].setTextColor(i==selected?GREEN:MUTED);
            tabs[i].setTypeface(null,i==selected?Typeface.BOLD:Typeface.NORMAL);
        }
        if(outputEmpty!=null)outputEmpty.setVisibility(output.length()==0&&image.getVisibility()!=View.VISIBLE?View.VISIBLE:View.GONE);
        StudyNavigation.panes(this,workspace,panes,selected);
        compactHeader();
    }
    private void insertCode(String insertion){
        int start=Math.max(0,editor.getSelectionStart()),end=Math.max(0,editor.getSelectionEnd());
        editor.getText().replace(Math.min(start,end),Math.max(start,end),insertion);
        editor.setSelection(Math.min(start,end)+insertion.length()-(insertion.length()==2?1:0));editor.requestFocus();
    }
    private JSONObject unit(){ return units.optJSONObject(index); }
    private boolean guided(){JSONArray pages=unit().optJSONArray("guided_steps");return phase==0&&pages!=null&&pages.length()>0;}
    private int stepCount(){JSONArray pages=unit().optJSONArray("learning_steps");return pages==null?2:Math.max(1,pages.length());}
    private JSONObject task(){return guided()?unit().optJSONArray("guided_steps").optJSONObject(step).optJSONObject("practice"):unit().optJSONArray("problems").optJSONObject(variant);}
    private String key(){ return unit().optString("key"); }
    private void loadPosition(){ phase=Math.max(0,Math.min(3,progress.getInt(key()+".phase",0))); step=Math.max(0,Math.min(stepCount()-1,progress.getInt(key()+".step",0))); variant=Math.max(0,phase-1); }
    private void save(){
        if(phase==4) return;
        progress.edit().putString("last",key()).putInt(key()+".phase",phase).putInt(key()+".step",step).apply();
    }
    private boolean completed(String key){ return progress.getBoolean(key+":1",false)&&progress.getBoolean(key+":2",false); }
    private void render(){
        String phaseText=new String[]{"배우기 "+(step+1)+"/"+stepCount(),"예시","활용 1","활용 2","올랜덤"}[phase];
        heading.setText(unit().optString("topic")+"  /  "+unitNumber(index));phaseLabel.setText(phaseText);
        unitTitle.setText(phase<2?unit().optString("title"):(phase==4?"배운 범위 올랜덤":"활용 문제"));
        progressTrack.removeAllViews();
        for(int i=0;i<4;i++){
            View segment=new View(this);segment.setBackground(shape(i==phase?0xff246586:i>0&&StudyNavigation.done(progress,key(),true,i-1)?GREEN:LINE,2,0));
            LinearLayout.LayoutParams p=new LinearLayout.LayoutParams(0,-1,1);p.setMargins(0,0,i<3?dp(4):0,0);progressTrack.addView(segment,p);
        }
        save();updateCompletion();renderProblem();showPane(0);controls();
    }
    private void updateCompletion(){
        if(completion!=null)completion.setText((phase==4?"올랜덤 연습":StudyNavigation.state(progress,key(),true))+" · "+StudyNavigation.checks(progress,key(),true));
    }
    private void renderProblem(){
        questionContent.removeAllViews();
        if(phase==0){
            JSONArray page=unit().optJSONArray("learning_steps").optJSONArray(step);
            section(questionContent,page.optString(0),page.optString(1));
            if(guided())questionContent.addView(button("소단계 코드 넣기",()->replaceCode(()->{editor.setText(task().optString("solution"));showPane(1);})));
            if(step>0)questionContent.addView(button("← 이전 소단계",()->replaceCode(()->{cancelWorker();step--;solved=false;clearWork();render();})));
        }else{
            section(questionContent,"이번 실습의 목표",task().optString("goal"));
            if(phase==1)codeBlock(questionContent,"직접 입력할 예시",task().optString("solution"));
        }
        String prepared=task().optString("display_initial",task().optString("initial"));
        if(!prepared.isEmpty())codeBlock(questionContent,"준비된 데이터",prepared);
        JSONObject files=task().optJSONObject("files");if(files!=null&&files.length()>0)section(questionContent,"실습 파일",files.names().toString());
        Button write=button("코드 입력하기  →",()->showPane(1));write.setTextColor(GREEN);write.setGravity(Gravity.START|Gravity.CENTER_VERTICAL);questionContent.addView(write);
        ((ScrollView)panes[0]).scrollTo(0,0);
    }
    private void section(LinearLayout into,String title,String body){
        TextView label=text(12);label.setTextColor(GREEN);label.setTypeface(null,Typeface.BOLD);label.setText(title);into.addView(label);
        TextView content=text(16);content.setText(body);content.setTextIsSelectable(true);content.setLineSpacing(dp(6),1);content.setPadding(0,dp(10),0,dp(26));into.addView(content);
    }
    private void codeBlock(LinearLayout into,String title,String code){
        TextView label=text(12);label.setText(title);label.setTextColor(MUTED);label.setPadding(0,0,0,dp(10));into.addView(label);
        HorizontalScrollView scroll=new HorizontalScrollView(this);scroll.setBackground(shape(0xffedf2f3,8,0));
        TextView content=text(14);content.setTypeface(Typeface.MONOSPACE);content.setText(code);content.setTextIsSelectable(true);content.setLineSpacing(dp(5),1);content.setPadding(dp(14),dp(14),dp(14),dp(14));scroll.addView(content);
        LinearLayout.LayoutParams p=new LinearLayout.LayoutParams(-1,-2);p.bottomMargin=dp(26);into.addView(scroll,p);
    }
    private void controls(){
        if(execute==null)return;
        execute.setVisibility(busy?View.GONE:View.VISIBLE);stop.setVisibility(busy?View.VISIBLE:View.GONE);
        grade.setEnabled(!busy&&(phase>0||guided()));grade.setText(guided()?"결과 확인":"채점");next.setEnabled(!busy&&(phase==0||solved||progress.getBoolean(key()+":"+variant,false)));unitPicker.setEnabled(!busy);
        execute.setBackground(shape(GREEN,8,0));execute.setTextColor(Color.WHITE);
        stop.setBackground(shape(0xfffae9e5,8,0));stop.setTextColor(0xffad4230);
        grade.setBackground(shape(Color.WHITE,8,LINE));next.setBackground(shape(next.isEnabled()?0xffe1eee9:0xffe9edef,8,0));
        status.setText(busy?"Python 실행 중…  ·  중단해도 입력은 유지됩니다":phase==4?"올랜덤 모드  ·  메뉴에서 원래 학습으로 복귀":phase==0?"설명을 보며 자유롭게 실행  ·  진도 자동 저장":solved?"목표 달성  ·  다음 실습으로 이동할 수 있습니다":"실행 후 채점  ·  미완료 항목은 이어서 수정");
    }
    private String unitNumber(int at){
        JSONObject u=units.optJSONObject(at);if(u.optString("key").startsWith("review_"))return "종합 복습";
        int n=0;for(int i=0;i<=at;i++){JSONObject item=units.optJSONObject(i);if(item.optString("topic").equals(u.optString("topic"))&&!item.optString("key").startsWith("review_"))n++;}
        return String.format(Locale.ROOT,"%02d",n);
    }
    private void pickUnit(){
        if(busy)return;
        ArrayList<JSONObject> choices=new ArrayList<>();for(int i=0;i<units.length();i++)choices.add(units.optJSONObject(i));
        StudyNavigation.pick(this,choices,index,progress,true,at->{if(at!=index)choose(at);});
    }
    private void menu(){
        PopupMenu popup=new PopupMenu(this,more);
        String[] labels={"힌트","실습 초기화","개념 퀴즈",phase==4?"올랜덤 끝내기":"배운 범위 올랜덤","사용 안내"};
        for(int i=0;i<labels.length;i++)popup.getMenu().add(0,i,i,labels[i]).setEnabled(!busy||i==4);
        if(BuildConfig.LINUX_RUNTIME)popup.getMenu().add(0,5,5,"Linux · Docker · ROS 2").setEnabled(!busy);
        if(BuildConfig.LINUX_RUNTIME){popup.getMenu().add(0,6,6,"Conda · pip").setEnabled(!busy);popup.getMenu().add(0,7,7,"Jupyter 노트북").setEnabled(!busy);}
        popup.getMenu().add(0,8,8,"NAS 진도 동기화");
        popup.getMenu().add(0,9,9,"이 단원 문법 처음부터").setEnabled(!busy);
        popup.setOnMenuItemClickListener(item->{switch(item.getItemId()){
            case 8:NasSync.get(this).settings(this);break;
            case 9:replaceCode(()->{cancelWorker();randomReturn=null;phase=0;step=0;variant=0;solved=false;clearWork();render();});break;
            case 5:save();cancelWorker();startActivity(new Intent(this,LinuxActivity.class));break;
            case 6:save();cancelWorker();startActivity(new Intent(this,LinuxActivity.class).putExtra("course","conda"));break;
            case 7:save();cancelWorker();startActivity(new Intent(this,LinuxActivity.class).putExtra("course","notebook"));break;
            case 0:hint();break;case 1:restart();break;case 2:quiz();break;case 3:if(phase==4)stopRandom();else startRandom();break;
            case 4:new AlertDialog.Builder(this).setTitle("Shellground 사용 안내").setMessage("설명 → 코드 입력 → 실행 → 채점 순서로 연습합니다. 미완료 항목은 초기화하지 않고 계속 수정할 수 있습니다.\n\n학습 완료와 소단계 위치는 자동 저장됩니다. 입력 코드와 임시 실습 파일은 종료하면 남기지 않습니다.\n\n신뢰할 수 없는 외부 코드는 실행하지 마세요.\n\n"+(BuildConfig.LINUX_RUNTIME?"메뉴에서 Linux · Docker · ROS 2, Conda · pip, Jupyter를 선택합니다. PC 연결·외부 서버 없이 앱에 포함된 환경을 사용합니다. 최초 Linux 시작 시 실습 이미지 크기만큼 추가 저장 공간이 필요하며 부팅에 시간이 걸립니다. 앱을 벗어나면 실습 환경을 종료하고 학습 진도는 유지합니다.\n\nLinux 기반 과정은 Android 9 이상에서 동작합니다. Jupyter의 커널 선택과 Bash 활성 환경은 별개입니다. 하드웨어 키보드는 Shift+Enter로 코드 셀을 실행합니다.":"이 경량판은 Python 학습용입니다.")).setPositiveButton("확인",null).show();break;
        }return true;});popup.show();
    }
    private void choose(int selected){
        if(editor.length()>0) new AlertDialog.Builder(this).setMessage("진도는 유지하고 입력 코드·임시 실습을 버릴까요?")
            .setNegativeButton("취소",(d,w)->render()).setPositiveButton("이동",(d,w)->select(selected)).show();
        else select(selected);
    }
    private void select(int selected){ save(); cancelWorker(); index=selected; randomReturn=null; loadPosition(); solved=false; clearWork(); render(); }
    private void clearWork(){ editor.setText(""); output.setText("");outputEmpty.setText("아직 실행 결과가 없습니다.\n코드 탭에서 입력한 뒤 실행해 보세요.");image.setVisibility(View.GONE);figurePicker.setVisibility(View.GONE);figurePaths=new JSONArray();feedback="아직 채점하지 않았습니다.";renderGrade(null); }
    private void run(){if(busy)return;if(editor.getText().toString().trim().isEmpty()){showPane(1);editor.requestFocus();Toast.makeText(this,"실행할 코드를 입력하세요.",Toast.LENGTH_SHORT).show();return;}hideKeyboard();request("execute");}
    private void request(String action){
        if(busy) return;
        try {
            JSONObject request=new JSONObject().put("action",action).put("unit",key()).put("variant",variant);
            if(phase==0)request.put("phase","learn").put("step",step);
            if(action.equals("execute")) request.put("code",editor.getText().toString());
            busy=true; requestId++; controls(); handler.postDelayed(timeout,service==null?30000:8000);
            if(service==null) {
                pending=request.toString();
                if(!bound) bound=bindService(new Intent(this,PythonService.class),connection,Context.BIND_AUTO_CREATE);
                if(!bound) throw new IllegalStateException("Python 프로세스를 시작하지 못했습니다.");
            } else send(request.toString());
        } catch(Exception e){ busy=false; handler.removeCallbacks(timeout); output.append("\n"+e); controls(); }
    }
    private void send(String request){
        try { Message m=Message.obtain(null,PythonService.RUN); m.arg1=requestId; m.replyTo=replies; Bundle b=new Bundle(); b.putString("request",request); m.setData(b); service.send(m); }
        catch(RemoteException e){ busy=false; output.append("\nPython 연결이 끊겼습니다. 다시 시작하세요."); controls(); }
    }
    private void cancelWorker(){
        requestId++; handler.removeCallbacks(timeout); pending=null;
        if(service!=null) try{ service.send(Message.obtain(null,PythonService.STOP)); }catch(RemoteException ignored){}
        service=null;
        if(bound){ unbindService(connection); bound=false; }
        stopService(new Intent(this,PythonService.class)); busy=false; controls();
    }
    private void showGrade(JSONObject result){
        solved=result.optBoolean("passed"); StringBuilder lines=new StringBuilder(solved?"목표 달성\n":"미완료 항목을 수정하고 다시 채점하세요.\n");
        JSONArray checks=result.optJSONArray("checks");
        for(int i=0;i<checks.length();i++){ JSONObject check=checks.optJSONObject(i); lines.append("\n").append(check.optBoolean("passed")?"✓ ":"· ").append(check.optString("label")); if(!check.optBoolean("passed")) lines.append("\n").append(check.optString("detail")); }
        feedback=lines.toString();renderGrade(result);showPane(3);
        if(solved&&phase>0&&phase!=4) progress.edit().putBoolean(key()+":"+variant,true).apply();
        updateCompletion();
    }
    private void renderGrade(JSONObject result){
        gradeContent.removeAllViews();gradeContent.setPadding(dp(20),dp(16),dp(20),dp(16));gradeSummary=text(20);gradeSummary.setTypeface(null,Typeface.BOLD);gradeSummary.setPadding(0,0,0,dp(8));gradeContent.addView(gradeSummary);
        if(result==null){gradeSummary.setText("아직 채점하지 않았습니다");TextView info=text(15);info.setText("코드를 실행한 뒤 채점하면\n목표별 달성 여부가 여기에 표시됩니다.");info.setTextColor(MUTED);info.setLineSpacing(dp(6),1);gradeContent.addView(info);return;}
        JSONArray checks=result.optJSONArray("checks");int passed=0;for(int i=0;i<checks.length();i++)if(checks.optJSONObject(i).optBoolean("passed"))passed++;
        gradeSummary.setText(result.optBoolean("passed")?"목표를 달성했습니다":"조금 더 다듬어 보세요");gradeSummary.setTextColor(result.optBoolean("passed")?GREEN:INK);
        TextView count=text(13);count.setText(passed+" / "+checks.length()+" 항목 완료");count.setTextColor(MUTED);count.setPadding(0,0,0,dp(12));gradeContent.addView(count);
        for(int i=0;i<checks.length();i++){
            JSONObject check=checks.optJSONObject(i);boolean ok=check.optBoolean("passed");
            LinearLayout checkRow=row();checkRow.setPadding(0,dp(8),0,dp(8));gradeContent.addView(checkRow);
            TextView mark=text(18);mark.setText(ok?"✓":"○");mark.setTextColor(ok?GREEN:0xffb56825);checkRow.addView(mark,new LinearLayout.LayoutParams(dp(30),-2));
            LinearLayout words=vertical();checkRow.addView(words,weight());TextView label=text(15);label.setTag("check-"+i);label.setText(check.optString("label"));label.setLineSpacing(dp(4),1);words.addView(label);
            if(!ok){TextView detail=text(13);detail.setText(check.optString("detail"));detail.setTextColor(MUTED);detail.setPadding(0,dp(4),0,0);detail.setLineSpacing(dp(3),1);words.addView(detail);}
            View divider=new View(this);divider.setBackgroundColor(LINE);gradeContent.addView(divider,new LinearLayout.LayoutParams(-1,dp(1)));
        }
        ((ScrollView)panes[3]).scrollTo(0,0);
    }
    private void advance(){
        if(phase==0&&step+1<stepCount()){replaceCode(()->{cancelWorker();step++;solved=false;clearWork();render();});return;}
        if(phase!=0&&!solved&&(phase==4||!StudyNavigation.done(progress,key(),true,variant))) return;
        cancelWorker(); solved=false;clearWork();
        if(phase==4){pickRandom();return;}
        if(phase==3){ if(index+1<units.length()) select(index+1); return; }
        phase++; variant=Math.max(0,phase-1);render();
    }
    private void restart(){ new AlertDialog.Builder(this).setMessage("코드는 남기고 변수·실습 파일만 초기화할까요?")
        .setNegativeButton("취소",null).setPositiveButton("초기화",(d,w)->{cancelWorker();solved=false;output.setText("");image.setVisibility(View.GONE);controls();}).show(); }
    private void hint(){ new AlertDialog.Builder(this).setTitle("힌트").setMessage(unit().optString("pitfall")+"\n\n"+unit().optString("syntax")).setPositiveButton("닫기",null).show(); }
    private void startRandom(){
        if(phase!=4) {save();randomReturn=new int[]{index,phase,step,variant};}
        pickRandom();
    }
    private void pickRandom(){
        ArrayList<Integer> available=new ArrayList<>(); for(int i=0;i<units.length();i++) if(completed(units.optJSONObject(i).optString("key"))) available.add(i);
        if(available.isEmpty()){ new AlertDialog.Builder(this).setMessage("활용1·2를 완료한 단원이 아직 없습니다.").setPositiveButton("닫기",null).show();return; }
        cancelWorker();Random rng=new Random();index=available.get(rng.nextInt(available.size()));phase=4;variant=1+rng.nextInt(2);solved=false;clearWork();render();
    }
    private void stopRandom(){
        if(phase!=4||randomReturn==null)return;cancelWorker();index=randomReturn[0];phase=randomReturn[1];step=randomReturn[2];variant=randomReturn[3];randomReturn=null;solved=false;clearWork();render();
    }
    private void quiz(){
        int number=Math.max(0,Math.min(quizzes.length()-1,progress.getInt("quiz.position",0)));
        String id=quizzes.optJSONObject(number).optString("id");
        ArrayList<JSONObject> related=new ArrayList<>();
        for(int i=0;i<cards.length();i++){
            JSONObject card=cards.optJSONObject(i); JSONArray links=card.optJSONArray("quiz_ids");
            for(int j=0;j<links.length();j++)if(id.equals(links.optString(j))){related.add(card);break;}
        }
        if(related.isEmpty()){quizQuestion();return;}
        showConcept(related,Math.max(0,Math.min(related.size()-1,progress.getInt("card."+id,0))),id);
    }
    private void showConcept(ArrayList<JSONObject> related,int position,String id){
        JSONObject card=related.get(position); JSONObject source=card.optJSONObject("source");
        progress.edit().putInt("card."+id,position).apply();
        new AlertDialog.Builder(this).setTitle("개념 "+(position+1)+"/"+related.size()+" · "+card.optString("title"))
            .setMessage("왜 배우나요?\n"+card.optString("why")+"\n\n"+card.optString("explanation")+"\n\n예시\n"+card.optString("example")+"\n\n헷갈리기 쉬운 점\n"+card.optString("misconception")+"\n\n"+source.optString("document")+" "+source.optJSONArray("pages"))
            .setNegativeButton(position>0?"이전":"닫기",(d,w)->{if(position>0)showConcept(related,position-1,id);})
            .setNeutralButton("직접 풀기",(d,w)->quizQuestion())
            .setPositiveButton(position+1<related.size()?"다음 개념":"퀴즈 시작",(d,w)->{if(position+1<related.size())showConcept(related,position+1,id);else quizQuestion();}).show();
    }
    private void quizQuestion(){
        int number=Math.max(0,Math.min(quizzes.length()-1,progress.getInt("quiz.position",0)));
        JSONObject q=quizzes.optJSONObject(number);JSONArray options=q.optJSONArray("choices");
        final int[] selected={-1};
        AlertDialog dialog=new AlertDialog.Builder(this).setTitle("개념 퀴즈 "+(number+1)+"/"+quizzes.length())
            .setNegativeButton("닫기",null).setPositiveButton("답 확인",null).create();
        ScrollView scroll=new ScrollView(this);LinearLayout container=vertical();container.setPadding(dp(20),dp(8),dp(20),dp(12));scroll.addView(container);
        TextView prompt=text(16);prompt.setText(q.optString("prompt"));prompt.setLineSpacing(dp(5),1);prompt.setPadding(0,0,0,dp(20));container.addView(prompt);
        RadioGroup group=new RadioGroup(this);container.addView(group);
        for(int i=0;i<options.length();i++){
            RadioButton option=new RadioButton(this);option.setId(View.generateViewId());option.setTag(i);option.setText(options.optString(i));option.setTextSize(15);option.setTextColor(INK);
            option.setMinHeight(dp(52));option.setPadding(dp(4),dp(10),dp(4),dp(10));option.setLineSpacing(dp(4),1);group.addView(option,new RadioGroup.LayoutParams(-1,-2));
        }
        group.setOnCheckedChangeListener((g,id)->selected[0]=(Integer)g.findViewById(id).getTag());
        dialog.setView(scroll);dialog.show();
        dialog.getButton(AlertDialog.BUTTON_POSITIVE).setOnClickListener(v->{
            if(selected[0]<0)return;boolean ok=selected[0]==q.optInt("answer");
            if(ok)progress.edit().putBoolean("quiz."+q.optString("id"),true).putInt("quiz.position",(number+1)%quizzes.length()).apply();
            dialog.dismiss();new AlertDialog.Builder(this).setTitle(ok?"정답":"다시 생각해 보세요").setMessage(q.optString("explanation")+"\n\n흔한 오해: "+q.optString("misconception"))
                .setPositiveButton(ok?"다음":"다시 풀기",(d,w)->quiz()).setNegativeButton("닫기",null).show();
        });
    }
    @Override public boolean onKeyUp(int keyCode,KeyEvent event){
        if(keyCode==KeyEvent.KEYCODE_F1){hint();return true;}
        if(keyCode==KeyEvent.KEYCODE_F2){restart();return true;}
        if(keyCode==KeyEvent.KEYCODE_F5&&!busy&&(phase>0||guided())){request("grade");return true;}
        if(keyCode==KeyEvent.KEYCODE_F6&&!busy){advance();return true;}
        if(keyCode==KeyEvent.KEYCODE_ENTER&&event.isShiftPressed()&&!busy){run();return true;}
        return super.onKeyUp(keyCode,event);
    }
    @Override public boolean dispatchKeyEvent(KeyEvent event){
        if(editor!=null&&(event.getKeyCode()==KeyEvent.KEYCODE_ENTER||event.getKeyCode()==KeyEvent.KEYCODE_NUMPAD_ENTER)&&event.isShiftPressed()){
            if(event.getAction()==KeyEvent.ACTION_DOWN&&event.getRepeatCount()==0&&!busy)run();return true;
        }
        return super.dispatchKeyEvent(event);
    }
    private void replaceCode(Runnable action){if(editor.length()==0)action.run();else new AlertDialog.Builder(this).setMessage("완료 진도는 유지하고 입력 코드를 바꿀까요?").setNegativeButton("취소",null).setPositiveButton("계속",(d,w)->action.run()).show();}
    private static abstract class SimpleSelection implements AdapterView.OnItemSelectedListener {public void onNothingSelected(AdapterView<?> parent){}}
    private void showFigures(JSONObject result){
        figurePaths=result.optJSONArray("figurePaths");if(figurePaths==null)figurePaths=new JSONArray();
        JSONArray numbers=result.optJSONArray("figure_numbers");ArrayList<String> labels=new ArrayList<>();
        for(int i=0;i<figurePaths.length();i++)labels.add("Figure "+(numbers==null?i+1:numbers.optInt(i,i+1))+(i==0?" · 현재 그림":""));
        figurePicker.setAdapter(new ArrayAdapter<>(this,android.R.layout.simple_spinner_dropdown_item,labels));
        figurePicker.setVisibility(labels.size()>1?View.VISIBLE:View.GONE);showFigure(0);
    }
    private void showFigure(int at){
        Bitmap picture=at<figurePaths.length()?BitmapFactory.decodeFile(figurePaths.optString(at)):null;
        image.setImageBitmap(picture);image.setVisibility(picture==null?View.GONE:View.VISIBLE);
        if(picture==null&&figurePaths.length()>0)output.append("\n그래프 이미지를 읽지 못했습니다.");
    }
    @Override protected void onStop(){ if(units!=null)save(); if(execute!=null)cancelWorker();NasSync.get(this).flush(); super.onStop(); }
}
