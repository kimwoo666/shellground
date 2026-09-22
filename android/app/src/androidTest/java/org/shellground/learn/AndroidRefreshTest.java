package org.shellground.learn;

import android.app.*;
import android.content.*;
import android.os.*;
import android.view.*;
import android.widget.*;
import androidx.test.platform.app.InstrumentationRegistry;
import androidx.test.ext.junit.runners.AndroidJUnit4;
import org.junit.*;
import org.junit.runner.RunWith;
import java.util.concurrent.*;
import static org.junit.Assert.*;

@RunWith(AndroidJUnit4.class)
public class AndroidRefreshTest {
    private final Instrumentation inst=InstrumentationRegistry.getInstrumentation();
    private final Context context=inst.getTargetContext();
    @Before public void syncReady()throws Exception{
        CountDownLatch loaded=new CountDownLatch(1);inst.runOnMainSync(()->NasSync.get(context).startup(loaded::countDown));assertTrue(loaded.await(60,TimeUnit.SECONDS));
    }
    @After public void close(){ScreenTestLifecycle.closeActivities(inst);}
    private View tagged(Activity a,String tag){return a.getWindow().getDecorView().findViewWithTag(tag);}
    private LinuxActivity open(boolean prewarm){
        LinuxActivity a=(LinuxActivity)inst.startActivitySync(new Intent(context,LinuxActivity.class).putExtra("prewarm",prewarm).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK));ScreenTestLifecycle.studyReady(inst,a,"linux-workspace");return a;
    }
    @Test public void completionHeaderDistinguishesReadingFromPassing(){
        context.getSharedPreferences("real-linux-progress-v1",0).edit().putString("last","navigate").putInt("navigate:phase",2).putBoolean("navigate:done:1",true).remove("navigate:done:2").commit();
        LinuxActivity a=open(false);inst.runOnMainSync(()->{
            String summary=((TextView)tagged(a,"progress-summary")).getText().toString();assertTrue(summary,summary.contains("진행 중"));assertTrue(summary,summary.contains("활용 1 완료"));assertTrue(summary,summary.contains("활용 2 미완료"));
            assertTrue("Previously solved application can advance after reopening",tagged(a,"linux-next").isEnabled());
        });
    }
    @Test public void preparationKeepsReadingAvailableAndCanBeCancelled(){
        context.getSharedPreferences("real-linux-progress-v1",0).edit().putString("last","navigate").putInt("navigate:phase",0).putInt("navigate:step",0).commit();
        LinuxActivity a=open(true);inst.runOnMainSync(()->{
            ViewGroup row=(ViewGroup)tagged(a,"course-navigation");assertEquals("Linux",((Button)row.getChildAt(0)).getText().toString());assertEquals("Python",((Button)row.getChildAt(1)).getText().toString());
            assertEquals("준비 취소",((Button)tagged(a,"linux-start")).getText().toString());assertTrue(tagged(a,"linux-next").isEnabled());tagged(a,"linux-next").performClick();
            assertTrue(context.getSharedPreferences("real-linux-progress-v1",0).getInt("navigate:step",0)>0);
            tagged(a,"linux-start").performClick();assertEquals("실습 시작",((Button)tagged(a,"linux-start")).getText().toString());assertFalse(tagged(a,"linux-grade").isEnabled());
        });
    }
    @Test public void failedPreparationReturnsToStart()throws Exception{
        context.getSharedPreferences("real-linux-progress-v1",0).edit().putString("last","navigate").putInt("navigate:phase",2).commit();
        LinuxActivity a=open(true);
        inst.runOnMainSync(()->{
            try{
                for(String name:new String[]{"ready","busy","preparing"}){java.lang.reflect.Field field=LinuxActivity.class.getDeclaredField(name);field.setAccessible(true);field.setBoolean(a,true);}
                java.lang.reflect.Field field=LinuxActivity.class.getDeclaredField("replies");field.setAccessible(true);
                Message result=Message.obtain(null,LinuxService.RESULT);result.arg1=Integer.MAX_VALUE;
                Bundle data=new Bundle();data.putString("result","{\"error\":\"Test preparation failure\"}");result.setData(data);
                ((Messenger)field.get(a)).send(result);
            }catch(Exception failure){throw new AssertionError(failure);}
        });
        inst.waitForIdleSync();
        inst.runOnMainSync(()->{
            assertEquals("Failed preparation can restart from the main button","실습 시작",((Button)tagged(a,"linux-start")).getText().toString());
            assertTrue(tagged(a,"linux-start").isEnabled());assertFalse("No grading without a prepared session",tagged(a,"linux-grade").isEnabled());
        });
    }
    @Test public void launcherOpensLinux(){
        Instrumentation.ActivityMonitor monitor=inst.addMonitor(LinuxActivity.class.getName(),null,false);
        try{
            context.startActivity(new Intent(Intent.ACTION_MAIN).setClass(context,MainActivity.class).addCategory(Intent.CATEGORY_LAUNCHER).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK));
            Activity a=inst.waitForMonitorWithTimeout(monitor,60000);assertNotNull("Launcher routed to Linux",a);ScreenTestLifecycle.studyReady(inst,a,"linux-workspace");
            inst.runOnMainSync(()->assertNotNull(tagged(a,"course-linux")));
        }finally{inst.removeMonitor(monitor);}
    }
}
