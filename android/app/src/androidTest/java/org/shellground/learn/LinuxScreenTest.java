package org.shellground.learn;

import android.app.*;
import android.content.*;
import android.graphics.*;
import android.os.SystemClock;
import android.view.*;
import android.view.inputmethod.*;
import android.widget.*;
import androidx.test.platform.app.InstrumentationRegistry;
import androidx.test.ext.junit.runners.AndroidJUnit4;
import org.junit.Test;
import org.junit.After;
import org.junit.Assume;
import org.junit.runner.RunWith;
import java.io.*;
import org.json.*;
import static org.junit.Assert.*;

/** Layout and saved learning position tests; these do not claim real VM execution. */
@RunWith(AndroidJUnit4.class)
public final class LinuxScreenTest {
    private final Instrumentation inst=InstrumentationRegistry.getInstrumentation();
    @After public void closeScreens(){ScreenTestLifecycle.closeActivities(inst);}
    private LinuxActivity open(){
        inst.getTargetContext().getSharedPreferences("real-linux-progress-v1",0).edit()
            .putString("last","navigate").putInt("navigate:phase",0).putInt("navigate:step",0).commit();
        LinuxActivity activity=(LinuxActivity)inst.startActivitySync(new Intent(inst.getTargetContext(),LinuxActivity.class).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK));
        ScreenTestLifecycle.studyReady(inst,activity,"linux-workspace");return activity;
    }
    private Button button(View root,String text){
        if(root instanceof Button&&((Button)root).getText().toString().equals(text))return (Button)root;
        if(root instanceof ViewGroup)for(int i=0;i<((ViewGroup)root).getChildCount();i++){Button found=button(((ViewGroup)root).getChildAt(i),text);if(found!=null)return found;}return null;
    }
    private View tag(LinuxActivity a,String name){return a.getWindow().getDecorView().findViewWithTag(name);}
    private void capture(String name)throws Exception{
        if(!"true".equals(InstrumentationRegistry.getArguments().getString("captureScreens")))return;
        inst.waitForIdleSync();SystemClock.sleep(300);Bitmap image=inst.getUiAutomation().takeScreenshot();
        try(OutputStream out=new FileOutputStream(new File(inst.getTargetContext().getExternalFilesDir(null),"linux-"+name+".png"))){image.compress(Bitmap.CompressFormat.PNG,100,out);}image.recycle();
    }
    @Test public void testWorkingSpaceAndNativeTouchTargets()throws Exception{
        LinuxActivity a=open();inst.waitForIdleSync();
        inst.runOnMainSync(()->{
            float dp=a.getResources().getDisplayMetrics().density;
            assertTrue("Workspace is too short: "+tag(a,"linux-workspace").getHeight()/dp+"dp",tag(a,"linux-workspace").getHeight()>dp*180);
            for(String id:new String[]{"linux-start","linux-grade","linux-next"}){
                View control=tag(a,id);Rect bounds=new Rect();assertTrue(control.getGlobalVisibleRect(bounds));assertTrue(control.getHeight()>=dp*48-1);assertEquals(control.getHeight(),bounds.height());
            }
            assertEquals(View.VISIBLE,tag(a,"linux-pane-0").getVisibility());
        });capture("lesson");
        inst.runOnMainSync(()->button(a.getWindow().getDecorView(),"터미널").performClick());inst.waitForIdleSync();capture("terminal");
        inst.runOnMainSync(a::finish);
    }
    @Test public void testKeyboardKeepsTerminalAndActionsVisible()throws Exception{
        LinuxActivity a=open();inst.waitForIdleSync();
        inst.runOnMainSync(()->{
            button(a.getWindow().getDecorView(),"터미널").performClick();View terminal=tag(a,"linux-terminal");terminal.requestFocus();
        });
        ScreenTestLifecycle.showKeyboard(inst,a,tag(a,"linux-terminal"));
        boolean[] keyboard={false};long end=SystemClock.uptimeMillis()+5000;
        while(SystemClock.uptimeMillis()<end){inst.runOnMainSync(()->{WindowInsets insets=a.getWindow().getDecorView().getRootWindowInsets();keyboard[0]=insets!=null&&insets.isVisible(WindowInsets.Type.ime());});if(keyboard[0])break;SystemClock.sleep(100);}
        assertTrue("IME opened",keyboard[0]);inst.waitForIdleSync();SystemClock.sleep(250);capture("keyboard");
        inst.runOnMainSync(()->{
            View decor=a.getWindow().getDecorView();int ime=decor.getRootWindowInsets().getInsets(WindowInsets.Type.ime()).bottom;
            for(String id:new String[]{"linux-start","linux-grade","linux-next"}){Rect bounds=new Rect();assertTrue(tag(a,id).getGlobalVisibleRect(bounds));assertTrue(bounds.bottom<=decor.getHeight()-ime);}
            assertTrue("Terminal has usable height: "+tag(a,"linux-terminal").getHeight(),tag(a,"linux-terminal").getHeight()>=a.getResources().getDisplayMetrics().density*90);
            a.finish();
        });
    }
    @Test public void testMicrostepIsSavedWithoutTypedCommands()throws Exception{
        LinuxActivity a=open();inst.waitForIdleSync();
        inst.runOnMainSync(()->{tag(a,"linux-next").performClick();a.finish();});inst.waitForIdleSync();
        android.content.SharedPreferences p=inst.getTargetContext().getSharedPreferences("real-linux-progress-v1",0);
        assertEquals("navigate",p.getString("last",""));assertTrue(p.getInt("navigate:step",0)>0||p.getInt("navigate:phase",0)>0);
        for(String key:p.getAll().keySet())assertFalse(key.contains("input")||key.contains("command"));
    }
    @Test public void testInputSurfaceSendsActualControlBytes()throws Exception{
        StringBuilder sent=new StringBuilder();
        inst.runOnMainSync(()->{
            LinuxTerminalView view=new LinuxTerminalView(inst.getTargetContext(),new LinuxTerminalView.Actions(){
                public void input(String text){sent.append(text);}public void resize(int c,int r){}public void scroll(int n){}public void copy(){}
            });
            InputConnection input=view.onCreateInputConnection(new EditorInfo());input.commitText("한글",1);input.deleteSurroundingText(1,0);
            view.onKeyDown(KeyEvent.KEYCODE_ENTER,new KeyEvent(KeyEvent.ACTION_DOWN,KeyEvent.KEYCODE_ENTER));
            view.onKeyDown(KeyEvent.KEYCODE_C,new KeyEvent(0,0,KeyEvent.ACTION_DOWN,KeyEvent.KEYCODE_C,0,KeyEvent.META_CTRL_ON));
        });assertEquals("한글\u007f\r\u0003",sent.toString());
    }
    @Test public void testCompletionRequiresBothPracticeProblems()throws Exception{
        LinuxActivity activity=open();inst.waitForIdleSync();
        android.content.SharedPreferences progress=inst.getTargetContext().getSharedPreferences("real-linux-progress-v1",0);
        String first="__completion_test__:done:1",second="__completion_test__:done:2";
        java.lang.reflect.Method completed=LinuxActivity.class.getDeclaredMethod("completed",JSONObject.class);completed.setAccessible(true);
        JSONObject unit=new JSONObject().put("key","__completion_test__");
        try{
            progress.edit().remove(first).putBoolean(second,true).commit();
            assertEquals(false,completed.invoke(activity,unit));
            progress.edit().putBoolean(first,true).putBoolean(second,false).commit();
            assertEquals(false,completed.invoke(activity,unit));
            progress.edit().putBoolean(second,true).commit();
            assertEquals(true,completed.invoke(activity,unit));
        }finally{progress.edit().remove(first).remove(second).commit();inst.runOnMainSync(activity::finish);}
    }
    @Test public void testResumedMicrostepCanReadPreviousPreparationAndGoBack()throws Exception{
        JSONObject chosen=null;
        try(InputStream stream=inst.getTargetContext().getAssets().open("real-course.json")){
            ByteArrayOutputStream bytes=new ByteArrayOutputStream();byte[] block=new byte[8192];int n;
            while((n=stream.read(block))!=-1)bytes.write(block,0,n);
            JSONArray units=new JSONObject(bytes.toString("UTF-8")).getJSONArray("units");
            for(int i=0;i<units.length();i++)if(units.getJSONObject(i).getJSONArray("learning_steps").length()>1){chosen=units.getJSONObject(i);break;}
        }
        assertNotNull(chosen);String key=chosen.getString("key");
        android.content.SharedPreferences progress=inst.getTargetContext().getSharedPreferences("real-linux-progress-v1",0);
        progress.edit().putString("last",key).putInt(key+":phase",0).putInt(key+":step",1).commit();
        LinuxActivity activity=(LinuxActivity)inst.startActivitySync(new Intent(inst.getTargetContext(),LinuxActivity.class).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK));
        try{
            ScreenTestLifecycle.studyReady(inst,activity,"linux-workspace");
            inst.waitForIdleSync();
            java.lang.reflect.Method preparation=LinuxActivity.class.getDeclaredMethod("preparationText");preparation.setAccessible(true);
            String text=(String)preparation.invoke(activity);
            assertTrue(text.contains(chosen.getJSONArray("learning_steps").getJSONObject(0).getString("commands")));
            assertTrue(text.contains("자동 실행하거나 완료 처리하지 않습니다"));
            assertFalse(tag(activity,"linux-grade").isEnabled());
            java.lang.reflect.Method previous=LinuxActivity.class.getDeclaredMethod("previousStep");previous.setAccessible(true);
            inst.runOnMainSync(()->{try{previous.invoke(activity);}catch(Exception error){throw new AssertionError(error);}});
            assertEquals(0,progress.getInt(key+":step",-1));
            assertFalse("Reading previous steps must not start a VM",tag(activity,"linux-grade").isEnabled());
        }finally{inst.runOnMainSync(activity::finish);}
    }
    private void await(LinuxActivity activity,java.util.function.BooleanSupplier test,int seconds)throws Exception{
        long deadline=SystemClock.uptimeMillis()+seconds*1000L;boolean[] success={false};
        while(SystemClock.uptimeMillis()<deadline){inst.runOnMainSync(()->success[0]=test.getAsBoolean());if(success[0])return;SystemClock.sleep(100);}
        fail("UI condition timeout");
    }
    private String visibleTerminal(LinuxActivity activity){
        try{
            java.lang.reflect.Field field=LinuxTerminalView.class.getDeclaredField("frame");field.setAccessible(true);
            JSONObject frame=(JSONObject)field.get(tag(activity,"linux-terminal"));if(frame==null)return "";
            StringBuilder text=new StringBuilder();JSONArray rows=frame.getJSONArray("rows");
            for(int y=0;y<rows.length();y++){JSONArray cells=rows.getJSONArray(y);for(int x=0;x<cells.length();x++)text.append(cells.getJSONArray(x).getString(1));text.append('\n');}return text.toString();
        }catch(Exception e){throw new AssertionError(e);}
    }
    private void type(LinuxActivity activity,String text){inst.runOnMainSync(()->((LinuxTerminalView)tag(activity,"linux-terminal")).onCreateInputConnection(new EditorInfo()).commitText(text,1));}
    @Test public void testRealNanoThroughVisibleLearnerScreen()throws Exception{
        Assume.assumeTrue("Opt-in actual guest UI acceptance", "true".equals(InstrumentationRegistry.getArguments().getString("fullGuestUI")));
        inst.getTargetContext().getSharedPreferences("real-linux-progress-v1",0).edit().putString("last","edit").putInt("edit:phase",1).putInt("edit:step",0).remove("edit:done:0").commit();
        LinuxActivity activity=(LinuxActivity)inst.startActivitySync(new Intent(inst.getTargetContext(),LinuxActivity.class).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK));
        try{
            ScreenTestLifecycle.studyReady(inst,activity,"linux-workspace");
            inst.waitForIdleSync();inst.runOnMainSync(()->tag(activity,"linux-start").performClick());
            // The host emulator runs an ARM guest through TCG. Account for
            // both the bounded boot and prepare transactions in this opt-in test.
            await(activity,()->tag(activity,"linux-grade").isEnabled(),900);
            inst.runOnMainSync(()->button(activity.getWindow().getDecorView(),"터미널").performClick());
            type(activity,"nano note.txt\r");await(activity,()->visibleTerminal(activity).contains("GNU nano"),30);capture("real-nano");
            type(activity,"\u000bstatus=ready\u000f");await(activity,()->visibleTerminal(activity).contains("File Name to Write"),30);
            type(activity,"\r");await(activity,()->visibleTerminal(activity).contains("Wrote"),30);type(activity,"\u0018");
            type(activity,"printf '\\nSG_%s\\n' READY\r");await(activity,()->visibleTerminal(activity).contains("SG_READY"),30);
            inst.runOnMainSync(()->tag(activity,"linux-grade").performClick());
            await(activity,()->tag(activity,"linux-pane-2").getVisibility()==View.VISIBLE&&tag(activity,"linux-next").isEnabled(),60);capture("real-grade");
            inst.runOnMainSync(()->assertTrue(((TextView)tag(activity,"linux-assessment")).getText().toString().startsWith("목표를 완료했습니다.")));
            assertTrue(inst.getTargetContext().getSharedPreferences("real-linux-progress-v1",0).getBoolean("edit:done:0",false));
        }catch(Throwable failure){
            capture("real-failure");
            throw failure;
        }finally{
            inst.runOnMainSync(activity::finish);inst.waitForIdleSync();
            // Do not let the test runner kill the UID before onStop's actual
            // bounded VM cleanup completes in the separate service process.
            ActivityManager manager=(ActivityManager)inst.getTargetContext().getSystemService(Context.ACTIVITY_SERVICE);
            long deadline=SystemClock.uptimeMillis()+30000;boolean live;
            do{
                live=false;java.util.List<ActivityManager.RunningAppProcessInfo> processes=manager.getRunningAppProcesses();
                if(processes!=null)for(ActivityManager.RunningAppProcessInfo p:processes)if(p.processName.equals("org.shellground.learn:linux"))live=true;
                if(live)SystemClock.sleep(100);
            }while(live&&SystemClock.uptimeMillis()<deadline);
            assertFalse("Leaving the room must terminate its Linux service",live);
        }
    }
}
