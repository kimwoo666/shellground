package org.shellground.learn;

import android.app.Activity;
import android.content.*;
import android.view.*;
import android.widget.*;
import org.json.JSONObject;
import org.junit.*;
import org.junit.runner.RunWith;
import org.robolectric.*;
import org.robolectric.annotation.Config;
import java.util.*;
import static org.junit.Assert.*;

@RunWith(RobolectricTestRunner.class)
@Config(manifest=Config.NONE,sdk=35)
public class AndroidNavigationTest {
    @Test public void readingPositionIsNeverCountedAsSolved(){
        SharedPreferences p=RuntimeEnvironment.getApplication().getSharedPreferences("navigation-test",0);p.edit().clear().commit();
        for(boolean python:new boolean[]{false,true}){
            String key=python?"python":"linux";assertEquals("미시작",StudyNavigation.state(p,key,python));
            p.edit().putInt(key+(python?".phase":":phase"),3).commit();assertEquals("진행 중",StudyNavigation.state(p,key,python));
            assertTrue(StudyNavigation.checks(p,key,python).contains("활용 2 미완료"));
            p.edit().putBoolean(key+(python?":":":done:")+1,true).commit();assertEquals("진행 중",StudyNavigation.state(p,key,python));
            p.edit().putBoolean(key+(python?":":":done:")+2,true).commit();assertEquals("완료",StudyNavigation.state(p,key,python));
        }
    }
    @Test public void topicsKeepCurriculumOrder()throws Exception{
        List<JSONObject> units=Arrays.asList(new JSONObject().put("topic","Linux"),new JSONObject().put("topic","Shell"),new JSONObject().put("topic","Docker"),new JSONObject().put("topic","Linux"));
        assertEquals(Arrays.asList("Linux","Shell","Docker"),StudyNavigation.topics(units));
    }
    @Test public void courseChangeWaitsForInputLossDecision(){
        Activity a=Robolectric.buildActivity(Activity.class).setup().get();
        Runnable[] pending={null};ViewGroup courses=(ViewGroup)StudyNavigation.courses(a,"linux",go->pending[0]=go);
        assertEquals("Linux",((Button)courses.getChildAt(0)).getText().toString());assertEquals("Python",((Button)courses.getChildAt(1)).getText().toString());
        courses.getChildAt(1).performClick();assertNotNull(pending[0]);assertFalse(a.isFinishing());
        assertNull(Shadows.shadowOf(a).getNextStartedActivity());pending[0].run();
        assertEquals(MainActivity.class.getName(),Shadows.shadowOf(a).getNextStartedActivity().getComponent().getClassName());assertTrue(a.isFinishing());
    }
    @Test public void wideLayoutKeepsNotesAndSelectedWorkWithoutOverlap(){
        Activity a=Robolectric.buildActivity(Activity.class).setup().get();FrameLayout frame=new FrameLayout(a);
        View[] panes={new TextView(a),new TextView(a),new TextView(a)};for(View pane:panes)frame.addView(pane,new FrameLayout.LayoutParams(-1,-1));
        int width=StudyNavigation.dp(a,900),height=StudyNavigation.dp(a,450);frame.layout(0,0,width,height);
        StudyNavigation.panes(a,frame,panes,2);assertEquals(View.VISIBLE,panes[0].getVisibility());assertEquals(View.GONE,panes[1].getVisibility());assertEquals(View.VISIBLE,panes[2].getVisibility());
        FrameLayout.LayoutParams notes=(FrameLayout.LayoutParams)panes[0].getLayoutParams(),work=(FrameLayout.LayoutParams)panes[2].getLayoutParams();
        assertEquals(notes.width,work.leftMargin);assertEquals(width,notes.width+work.width);
        frame.layout(0,0,StudyNavigation.dp(a,360),height);StudyNavigation.panes(a,frame,panes,1);
        assertEquals(View.GONE,panes[0].getVisibility());assertEquals(View.VISIBLE,panes[1].getVisibility());assertEquals(-1,panes[1].getLayoutParams().width);
    }
}
