package org.shellground.learn;

import android.app.*;
import android.content.*;
import android.view.*;
import android.view.inputmethod.InputMethodManager;
import android.widget.*;
import android.graphics.Bitmap;
import android.graphics.Rect;
import android.os.SystemClock;
import java.io.File;
import java.io.FileOutputStream;
import java.lang.reflect.Method;
import org.json.*;
import androidx.test.platform.app.InstrumentationRegistry;
import androidx.test.ext.junit.runners.AndroidJUnit4;
import org.junit.Test;
import org.junit.After;
import org.junit.runner.RunWith;
import static org.junit.Assert.*;

/** Native screen lifecycle, without a WebView or a host Python process. */
@RunWith(AndroidJUnit4.class)
public class NativeScreenTest {
    private final Instrumentation inst=InstrumentationRegistry.getInstrumentation();
    @After public void closeScreens(){ScreenTestLifecycle.closeActivities(inst);}
    private <T extends View> T find(View root,Class<T> type,String text){
        if(type.isInstance(root)&&(text==null||(root instanceof TextView&&((TextView)root).getText().toString().equals(text))))return type.cast(root);
        if(root instanceof ViewGroup)for(int i=0;i<((ViewGroup)root).getChildCount();i++){
            T match=find(((ViewGroup)root).getChildAt(i),type,text);if(match!=null)return match;
        }
        return null;
    }
    private MainActivity open(){
        return (MainActivity)inst.startActivitySync(new Intent(inst.getTargetContext(),MainActivity.class).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK));
    }
    private void firstUnit(int phase){
        inst.getTargetContext().getSharedPreferences("python-progress-v1",0).edit().putString("last","py_values")
            .putInt("py_values.phase",phase).putInt("py_values.step",0).commit();
    }
    private View tagged(MainActivity activity,String tag){return activity.getWindow().getDecorView().findViewWithTag(tag);}
    private void capture(String name) throws Exception {
        if(!"true".equals(InstrumentationRegistry.getArguments().getString("captureScreens")))return;
        inst.waitForIdleSync();SystemClock.sleep(400);Bitmap bitmap=inst.getUiAutomation().takeScreenshot();
        File file=new File(inst.getTargetContext().getExternalFilesDir(null),"ui-"+name+".png");
        try(FileOutputStream output=new FileOutputStream(file)){bitmap.compress(Bitmap.CompressFormat.PNG,100,output);}bitmap.recycle();
    }
    @Test public void testMicrostepPersistsWithoutInput() throws Exception {
        Context context=inst.getTargetContext();
        context.getSharedPreferences("python-progress-v1",0).edit().putString("last","py_values").putInt("py_values.phase",0).putInt("py_values.step",0).commit();
        MainActivity first=open();inst.waitForIdleSync();
        inst.runOnMainSync(()->{
            View root=first.getWindow().getDecorView();
            Button next=find(root,Button.class,"다음");assertNotNull(next);next.performClick();
            find(root,EditText.class,null).setText("private_input = 123");
            first.finish();
        });inst.waitForIdleSync();
        assertEquals(1,context.getSharedPreferences("python-progress-v1",0).getInt("py_values.step",-1));
        MainActivity second=open();inst.waitForIdleSync();
        inst.runOnMainSync(()->{
            assertEquals("",find(second.getWindow().getDecorView(),EditText.class,null).getText().toString());
            assertNotNull(tagged(second,"more"));
            second.finish();
        });
    }
    @Test public void testWorkspaceTabsAndTouchTargets() throws Exception {
        firstUnit(0);MainActivity activity=open();inst.waitForIdleSync();
        inst.runOnMainSync(()->{
            float density=activity.getResources().getDisplayMetrics().density;
            View workspace=tagged(activity,"workspace");assertTrue("content has real working room",workspace.getHeight()>density*180);
            for(String tag:new String[]{"more","unit-picker","run","grade","next","tab-0","tab-1","tab-2","tab-3"}){
                View control=tagged(activity,tag);assertTrue(tag+" has a 48dp touch target",control.getHeight()>=density*48-1);
                Rect bounds=new Rect();assertTrue(tag+" is visible",control.getGlobalVisibleRect(bounds));assertEquals(tag+" is not clipped",control.getHeight(),bounds.height());
            }
            assertEquals(View.VISIBLE,tagged(activity,"pane-0").getVisibility());
            assertEquals(View.GONE,tagged(activity,"pane-1").getVisibility());
        });capture("lesson");
        inst.runOnMainSync(()->{
            tagged(activity,"tab-1").performClick();EditText editor=(EditText)tagged(activity,"code-editor");editor.setText("count = 3\nprice = 2.5\ntotal = count * price\nprint(total)");
        });inst.waitForIdleSync();
        inst.runOnMainSync(()->{
            EditText editor=(EditText)tagged(activity,"code-editor");
            assertTrue(editor.getHeight()>activity.getResources().getDisplayMetrics().density*130);
            tagged(activity,"tab-0").performClick();tagged(activity,"tab-1").performClick();assertTrue(editor.getText().toString().contains("total = count"));
        });capture("code");inst.runOnMainSync(activity::finish);
    }
    @Test public void testPreparedDataHidesObserverInternals() throws Exception {
        inst.getTargetContext().getSharedPreferences("python-progress-v1",0).edit()
            .putString("last","sns_summary").putInt("sns_summary.phase",0).putInt("sns_summary.step",0).commit();
        MainActivity activity=open();inst.waitForIdleSync();
        inst.runOnMainSync(()->{
            View pane=tagged(activity,"pane-0");
            assertNotNull(find(pane,TextView.class,"준비된 데이터"));
            StringBuilder visible=new StringBuilder();collectText(pane,visible);
            assertTrue(visible.toString().contains("readings=pd.DataFrame"));
            assertFalse(visible.toString().contains("def _bar_values"));
            activity.finish();
        });
    }
    private void collectText(View view,StringBuilder into){
        if(view instanceof TextView)into.append(((TextView)view).getText()).append('\n');
        if(view instanceof ViewGroup)for(int i=0;i<((ViewGroup)view).getChildCount();i++)collectText(((ViewGroup)view).getChildAt(i),into);
    }
    @Test public void testKeyboardKeepsActionsVisible() throws Exception {
        firstUnit(0);MainActivity activity=open();inst.waitForIdleSync();
        inst.runOnMainSync(()->{
            tagged(activity,"tab-1").performClick();EditText editor=(EditText)tagged(activity,"code-editor");editor.requestFocus();
        });
        ScreenTestLifecycle.showKeyboard(inst,activity,tagged(activity,"code-editor"));
        long until=SystemClock.uptimeMillis()+4000;boolean[] visible={false};
        while(SystemClock.uptimeMillis()<until){
            inst.runOnMainSync(()->{WindowInsets insets=activity.getWindow().getDecorView().getRootWindowInsets();visible[0]=insets!=null&&insets.isVisible(WindowInsets.Type.ime());});
            if(visible[0])break;SystemClock.sleep(100);
        }
        assertTrue("keyboard opens",visible[0]);inst.waitForIdleSync();SystemClock.sleep(250);capture("keyboard");
        inst.runOnMainSync(()->{
            View decor=activity.getWindow().getDecorView();int ime=decor.getRootWindowInsets().getInsets(WindowInsets.Type.ime()).bottom;
            for(String tag:new String[]{"run","grade","next"}){
                Rect bounds=new Rect();assertTrue(tagged(activity,tag).getGlobalVisibleRect(bounds));assertTrue(tag+" stays above keyboard",bounds.bottom<=decor.getHeight()-ime);
            }
            assertTrue("editor stays usable: "+tagged(activity,"code-editor").getHeight(),tagged(activity,"code-editor").getHeight()>=activity.getResources().getDisplayMetrics().density*90);
        });inst.runOnMainSync(activity::finish);
    }
    @Test public void testSevenChecksAndReturnToCode() throws Exception {
        firstUnit(2);MainActivity activity=open();inst.waitForIdleSync();
        JSONArray checks=new JSONArray();for(int i=0;i<7;i++)checks.put(new JSONObject().put("label","목표 "+(i+1)+" · 결과 값과 자료형 확인").put("passed",i!=3).put("detail","변수에 저장된 값을 다시 확인하세요."));
        JSONObject result=new JSONObject().put("passed",false).put("checks",checks);
        Method show=MainActivity.class.getDeclaredMethod("showGrade",JSONObject.class);show.setAccessible(true);
        inst.runOnMainSync(()->{
            try{show.invoke(activity,result);}catch(Exception error){throw new AssertionError(error);}
            assertEquals(View.VISIBLE,tagged(activity,"pane-3").getVisibility());
            assertEquals("활용 문제",((TextView)tagged(activity,"unit-title")).getText().toString());
            assertNotNull(find(activity.getWindow().getDecorView(),TextView.class,"6 / 7 항목 완료"));
        });inst.waitForIdleSync();
        inst.runOnMainSync(()->{
            android.content.res.Configuration config=activity.getResources().getConfiguration();
            if(config.screenHeightDp>=680&&config.fontScale<=1){
                View last=tagged(activity,"check-6");Rect visible=new Rect();assertTrue("all seven labels visible",last.getGlobalVisibleRect(visible));assertEquals(last.getHeight(),visible.height());
            }
        });capture("grading");
        inst.runOnMainSync(()->{tagged(activity,"tab-1").performClick();assertTrue(tagged(activity,"code-editor").isEnabled());activity.finish();});
    }
    private void awaitPane(MainActivity activity,int pane) throws Exception {
        long until=SystemClock.uptimeMillis()+35000;boolean[] ready={false};
        while(SystemClock.uptimeMillis()<until){
            inst.runOnMainSync(()->ready[0]=tagged(activity,"pane-"+pane).getVisibility()==View.VISIBLE&&tagged(activity,"stop").getVisibility()==View.GONE);
            if(ready[0])break;SystemClock.sleep(100);
        }
        assertTrue("request finished on pane "+pane,ready[0]);inst.waitForIdleSync();
    }
    @Test public void testRunAndGradeUsesVisibleTabs() throws Exception {
        firstUnit(1);MainActivity activity=open();inst.waitForIdleSync();
        inst.runOnMainSync(()->{
            tagged(activity,"tab-1").performClick();((EditText)tagged(activity,"code-editor")).setText("total = 3 * 2.5\nprint(total)");tagged(activity,"run").performClick();
        });awaitPane(activity,2);
        inst.runOnMainSync(()->assertTrue(((TextView)tagged(activity,"output")).getText().toString().contains("7.5")));capture("output");
        inst.runOnMainSync(()->tagged(activity,"grade").performClick());awaitPane(activity,3);
        inst.runOnMainSync(()->{assertTrue(tagged(activity,"next").isEnabled());activity.finish();});
    }
}
