package org.shellground.learn;

import android.app.Activity;
import android.app.AlertDialog;
import android.content.Intent;
import android.content.SharedPreferences;
import android.graphics.Color;
import android.os.Build;
import android.view.View;
import android.view.ViewGroup;
import android.widget.*;
import org.json.JSONObject;
import java.util.*;
import java.util.function.IntConsumer;

/** Shared course order and completion vocabulary for the native study screens. */
final class StudyNavigation {
    static final String[] COURSES={"linux","python","conda","notebook"};
    static final String[] LABELS={"Linux","Python","Conda·pip","Jupyter"};
    static int dp(Activity a,int n){return Math.round(n*a.getResources().getDisplayMetrics().density);}

    static View courses(Activity activity,String selected,java.util.function.Consumer<Runnable> leave){
        LinearLayout row=new LinearLayout(activity);row.setTag("course-navigation");
        row.setBackgroundColor(0xffeef1f4);
        for(int i=0;i<COURSES.length;i++){
            String course=COURSES[i];Button button=new Button(activity);button.setText(LABELS[i]);
            button.setTag("course-"+course);button.setAllCaps(false);button.setTextSize(12);
            button.setMinWidth(0);button.setMinimumWidth(0);button.setPadding(0,0,0,0);
            button.setContentDescription(LABELS[i]+(course.equals(selected)?" · 현재 과정":" 과정"));
            button.setTextColor(course.equals(selected)?Color.WHITE:0xff202b33);
            button.setBackgroundTintList(android.content.res.ColorStateList.valueOf(course.equals(selected)?0xff246586:0xffeef1f4));
            button.setEnabled(course.equals("python")||(BuildConfig.LINUX_RUNTIME&&Build.VERSION.SDK_INT>=28));
            button.setOnClickListener(v->{
                if(course.equals(selected))return;
                leave.accept(()->{
                Intent intent=new Intent(activity,course.equals("python")?MainActivity.class:LinuxActivity.class);
                if(!course.equals("python"))intent.putExtra("course",course).putExtra("prewarm",true);
                activity.startActivity(intent);activity.finish();
                });
            });
            row.addView(button,new LinearLayout.LayoutParams(0,dp(activity,48),1));
        }
        return row;
    }

    static boolean done(SharedPreferences p,String key,boolean python,int variant){
        return p.getBoolean(key+(python?":":":done:")+variant,false);
    }
    static String state(SharedPreferences p,String key,boolean python){
        if(done(p,key,python,1)&&done(p,key,python,2))return "완료";
        if(p.contains(key+(python?".phase":":phase"))||key.equals(p.getString("last",""))
                ||done(p,key,python,0)||done(p,key,python,1)||done(p,key,python,2))return "진행 중";
        return "미시작";
    }
    static String checks(SharedPreferences p,String key,boolean python){
        return "예시 "+(done(p,key,python,0)?"완료":"미완료")+" · 활용 1 "+(done(p,key,python,1)?"완료":"미완료")
                +" · 활용 2 "+(done(p,key,python,2)?"완료":"미완료");
    }
    static List<String> topics(List<JSONObject> units){
        LinkedHashSet<String> names=new LinkedHashSet<>();
        for(JSONObject unit:units)names.add(unit.optString("topic"));
        return new ArrayList<>(names);
    }
    static void pick(Activity activity,List<JSONObject> units,int current,SharedPreferences progress,boolean python,IntConsumer select){
        LinearLayout content=new LinearLayout(activity);content.setOrientation(LinearLayout.VERTICAL);
        Spinner topics=new Spinner(activity);List<String> names=topics(units);
        topics.setAdapter(new ArrayAdapter<>(activity,android.R.layout.simple_spinner_dropdown_item,names));
        content.addView(topics,new LinearLayout.LayoutParams(-1,dp(activity,48)));
        ListView list=new ListView(activity);list.setTag("study-unit-list");list.setDividerHeight(dp(activity,1));
        content.addView(list,new LinearLayout.LayoutParams(-1,0,1));
        AlertDialog dialog=new AlertDialog.Builder(activity).setTitle("단원 선택").setView(content).setNegativeButton("닫기",null).create();
        topics.setOnItemSelectedListener(new AdapterView.OnItemSelectedListener(){
            public void onNothingSelected(AdapterView<?> p){}
            public void onItemSelected(AdapterView<?> p,View view,int position,long id){
                ArrayList<Integer> targets=new ArrayList<>();
                for(int i=0;i<units.size();i++)if(units.get(i).optString("topic").equals(names.get(position)))targets.add(i);
                list.setAdapter(new BaseAdapter(){
                    public int getCount(){return targets.size();}public Object getItem(int i){return targets.get(i);}public long getItemId(int i){return targets.get(i);}
                    public View getView(int i,View recycled,ViewGroup parent){
                        int at=targets.get(i);JSONObject unit=units.get(at);String key=unit.optString("key"),state=state(progress,key,python);
                        LinearLayout row=new LinearLayout(activity);row.setOrientation(LinearLayout.VERTICAL);
                        row.setPadding(dp(activity,16),dp(activity,12),dp(activity,16),dp(activity,12));
                        TextView title=new TextView(activity);title.setTextSize(15);title.setTextColor(0xff202b33);
                        title.setText((at==current?"현재 · ":"")+state+" · "+unit.optString("title"));row.addView(title);
                        TextView details=new TextView(activity);details.setTextSize(12);details.setTextColor(0xff64717b);
                        details.setPadding(0,dp(activity,5),0,0);details.setText(checks(progress,key,python));row.addView(details);
                        if(at==current)row.setBackgroundColor(0xffe4eef4);
                        row.setContentDescription(title.getText()+". "+details.getText());return row;
                    }
                });
                list.setOnItemClickListener((p2,v,n,rowId)->{dialog.dismiss();select.accept(targets.get(n));});
                int selected=targets.indexOf(current);if(selected>=0)list.setSelection(selected);
            }
        });
        topics.setSelection(names.indexOf(units.get(current).optString("topic")));dialog.show();
        dialog.getWindow().setLayout(-1,Math.round(activity.getResources().getDisplayMetrics().heightPixels*0.82f));
    }

    /** A wide screen keeps instructions next to the selected work pane. */
    static void panes(Activity activity,FrameLayout workspace,View[] panes,int selected){
        int width=workspace.getWidth();boolean wide=width>=dp(activity,680);
        int work=selected==0?1:selected,notes=wide?Math.round(width*0.4f):0;
        for(int i=0;i<panes.length;i++){
            boolean visible=wide?(i==0||i==work):i==selected;
            panes[i].setVisibility(visible?View.VISIBLE:View.GONE);
            FrameLayout.LayoutParams p=(FrameLayout.LayoutParams)panes[i].getLayoutParams();
            int targetWidth=wide?(i==0?notes:width-notes):ViewGroup.LayoutParams.MATCH_PARENT;
            int margin=wide&&i!=0?notes:0;
            if(p.width!=targetWidth||p.leftMargin!=margin){p.width=targetWidth;p.leftMargin=margin;panes[i].setLayoutParams(p);}
        }
    }
}
