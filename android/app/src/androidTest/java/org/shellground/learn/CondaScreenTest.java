package org.shellground.learn;

import android.app.*;
import android.content.*;
import android.graphics.Bitmap;
import android.os.SystemClock;
import android.view.*;
import android.widget.*;
import androidx.test.platform.app.InstrumentationRegistry;
import androidx.test.ext.junit.runners.AndroidJUnit4;
import org.json.*;
import org.junit.*;
import org.junit.runner.RunWith;
import java.io.*;
import static org.junit.Assert.*;

/** Real Android widgets and saved progress, not a claim of actual Conda startup. */
@RunWith(AndroidJUnit4.class)
public final class CondaScreenTest {
    private final Instrumentation inst=InstrumentationRegistry.getInstrumentation();
    @After public void closeScreens(){ScreenTestLifecycle.closeActivities(inst);}
    private LinuxActivity open(String key,int phase,int step){
        inst.getTargetContext().getSharedPreferences("real-conda-progress-v1",0).edit()
            .putString("last",key).putInt(key+":phase",phase).putInt(key+":step",step).commit();
        return launch();
    }
    private LinuxActivity launch(){return (LinuxActivity)inst.startActivitySync(new Intent(inst.getTargetContext(),LinuxActivity.class).putExtra("course","conda").addFlags(Intent.FLAG_ACTIVITY_NEW_TASK));}
    private Button button(View root,String text){
        if(root instanceof Button&&((Button)root).getText().toString().equals(text))return (Button)root;
        if(root instanceof ViewGroup)for(int i=0;i<((ViewGroup)root).getChildCount();i++){Button found=button(((ViewGroup)root).getChildAt(i),text);if(found!=null)return found;}return null;
    }
    private String text(View view){
        StringBuilder result=new StringBuilder();if(view instanceof TextView)result.append(((TextView)view).getText());
        if(view instanceof ViewGroup)for(int i=0;i<((ViewGroup)view).getChildCount();i++)result.append('\n').append(text(((ViewGroup)view).getChildAt(i)));
        return result.toString();
    }
    private EditText edit(View view){
        if(view instanceof EditText)return (EditText)view;
        if(view instanceof ViewGroup)for(int i=0;i<((ViewGroup)view).getChildCount();i++){EditText found=edit(((ViewGroup)view).getChildAt(i));if(found!=null)return found;}return null;
    }
    private void capture(LinuxActivity activity,String name)throws Exception{
        if(!"true".equals(InstrumentationRegistry.getArguments().getString("captureScreens")))return;
        boolean[] visible={false};long deadline=SystemClock.uptimeMillis()+10000;
        while(SystemClock.uptimeMillis()<deadline){
            inst.runOnMainSync(()->{View root=activity.getWindow().getDecorView();visible[0]=root.hasWindowFocus()&&root.isShown()&&root.getWidth()>0&&root.getHeight()>0;});
            if(visible[0])break;SystemClock.sleep(50);
        }
        assertTrue("Capture requires the actual focused window, not its launch background",visible[0]);
        inst.waitForIdleSync();SystemClock.sleep(300);Bitmap shot=inst.getUiAutomation().takeScreenshot();
        try(OutputStream out=new FileOutputStream(new File(inst.getTargetContext().getExternalFilesDir(null),"conda-"+name+".png"))){shot.compress(Bitmap.CompressFormat.PNG,100,out);}shot.recycle();
    }
    @Test public void applicationShowsDiagnosticsButNotInstallOrActivationSolution()throws Exception{
        LinuxActivity activity=open("conda_install",2,0);inst.waitForIdleSync();
        inst.runOnMainSync(()->{
            View pane=activity.getWindow().getDecorView().findViewWithTag("linux-pane-0");String visible=text(pane);
            assertTrue(visible,visible.contains("training_text.normalize"));
            assertFalse(visible,visible.contains("conda install"));assertFalse(visible,visible.contains("conda activate"));
            assertFalse(activity.getWindow().getDecorView().findViewWithTag("linux-grade").isEnabled());
        });capture(activity,"application");
    }
    @Test public void nativeBooleanInputKeepsBlankAndFalseDistinct()throws Exception{
        inst.runOnMainSync(()->{
            try{
                CondaAnswerForm form=new CondaAnswerForm(inst.getTargetContext());
                form.show(new JSONArray().put(new JSONObject().put("key","exists").put("label","환경이 있나요?").put("input","boolean")));
                assertFalse(form.answers().has("exists"));
                Spinner input=form.findViewWithTag("conda-answer-exists");input.setSelection(2);
                assertEquals(Boolean.FALSE,form.answers().get("exists"));input.setSelection(1);assertEquals(Boolean.TRUE,form.answers().get("exists"));
            }catch(Exception error){throw new AssertionError(error);}
        });
    }
    @Test public void typedAnswerSurvivesProblemTerminalTabSwitch()throws Exception{
        LinuxActivity activity=open("conda_identity",1,0);inst.waitForIdleSync();
        inst.runOnMainSync(()->{
            View root=activity.getWindow().getDecorView();EditText input=edit(root);assertNotNull(input);input.setText("learner observation");
            button(root,"터미널").performClick();button(root,"문제·설명").performClick();
            assertEquals("learner observation",edit(root).getText().toString());
        });capture(activity,"answer");
    }
    @Test public void microstepProgressIsSeparateFromLinuxWithoutStartingVm()throws Exception{
        SharedPreferences linux=inst.getTargetContext().getSharedPreferences("real-linux-progress-v1",0);
        java.util.Map<String,?> before=linux.getAll();
        boolean wasDone=inst.getTargetContext().getSharedPreferences("real-conda-progress-v1",0).getBoolean("conda_identity:done:0",false);
        LinuxActivity activity=open("conda_identity",0,1);inst.waitForIdleSync();
        inst.runOnMainSync(()->{activity.getWindow().getDecorView().findViewWithTag("linux-next").performClick();activity.finish();});inst.waitForIdleSync();
        SharedPreferences conda=inst.getTargetContext().getSharedPreferences("real-conda-progress-v1",0);
        assertEquals(2,conda.getInt("conda_identity:step",-1));assertEquals(before,linux.getAll());
        LinuxActivity resumed=launch();inst.waitForIdleSync();
        inst.runOnMainSync(()->{
            View root=resumed.getWindow().getDecorView();assertTrue(text(root.findViewWithTag("linux-pane-0")).contains("3 / 3"));
            assertFalse(root.findViewWithTag("linux-grade").isEnabled());assertEquals(wasDone,conda.getBoolean("conda_identity:done:0",false));
        });
    }
}
