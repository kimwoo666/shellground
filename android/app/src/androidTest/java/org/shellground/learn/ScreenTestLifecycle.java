package org.shellground.learn;

import android.app.Activity;
import android.app.Instrumentation;
import android.content.Context;
import android.os.SystemClock;
import android.view.View;
import android.view.inputmethod.InputMethodManager;
import androidx.test.runner.lifecycle.ActivityLifecycleMonitorRegistry;
import androidx.test.runner.lifecycle.Stage;
import java.util.ArrayList;
import static org.junit.Assert.assertTrue;

/** Wait for actual Android lifecycle/input readiness, not just an idle looper. */
final class ScreenTestLifecycle {
    static void showKeyboard(Instrumentation inst, Activity activity, View editor) {
        InputMethodManager manager=(InputMethodManager)activity.getSystemService(Context.INPUT_METHOD_SERVICE);
        boolean[] ready={false};long deadline=SystemClock.uptimeMillis()+10000;
        while(SystemClock.uptimeMillis()<deadline){
            inst.runOnMainSync(()->{
                editor.requestFocus();
                ready[0]=editor.isShown()&&editor.getWidth()>0&&editor.getHeight()>0
                    &&editor.hasWindowFocus()&&editor.hasFocus()&&manager.isActive(editor);
            });
            if(ready[0])break;
            SystemClock.sleep(50);
        }
        assertTrue("Input view is laid out, focused, and served by Android",ready[0]);
        inst.runOnMainSync(()->manager.showSoftInput(editor,InputMethodManager.SHOW_IMPLICIT));
    }

    static void closeActivities(Instrumentation inst) {
        boolean[] closed={false};long deadline=SystemClock.uptimeMillis()+10000;
        while(SystemClock.uptimeMillis()<deadline){
            inst.runOnMainSync(()->{
                ArrayList<Activity> active=new ArrayList<>();
                for(Stage stage:Stage.values())if(stage!=Stage.DESTROYED)
                    active.addAll(ActivityLifecycleMonitorRegistry.getInstance().getActivitiesInStage(stage));
                closed[0]=active.isEmpty();
                for(Activity activity:active)if(!activity.isFinishing())activity.finish();
            });
            if(closed[0])return;
            SystemClock.sleep(50);
        }
        assertTrue("Previous test activity completed onStop/onDestroy before changing saved progress",closed[0]);
    }
}
