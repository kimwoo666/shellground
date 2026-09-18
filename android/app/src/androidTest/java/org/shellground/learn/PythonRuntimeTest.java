package org.shellground.learn;

import android.content.*;
import android.os.*;
import androidx.test.platform.app.InstrumentationRegistry;
import androidx.test.ext.junit.runners.AndroidJUnit4;
import org.junit.Before;
import org.junit.After;
import org.junit.Test;
import org.junit.runner.RunWith;
import static org.junit.Assert.*;
import org.json.JSONObject;
import java.util.concurrent.*;

/** Exercises the shipped Android native wheels, not the host's Python. */
@RunWith(AndroidJUnit4.class)
public final class PythonRuntimeTest {
    private Messenger remote;
    private Context context;
    private HandlerThread callbackThread;
    private BlockingQueue<String> responses;
    private Messenger reply;
    private ServiceConnection connection;
    @Before public void setUp() throws Exception {
        context=InstrumentationRegistry.getInstrumentation().getTargetContext(); responses=new LinkedBlockingQueue<>();
        callbackThread=new HandlerThread("runtime-test");callbackThread.start();
        reply=new Messenger(new Handler(callbackThread.getLooper(),message->{responses.add(message.getData().getString("result"));return true;}));
        CountDownLatch connected=new CountDownLatch(1);
        connection=new ServiceConnection(){
            public void onServiceConnected(ComponentName name,IBinder binder){ remote=new Messenger(binder);connected.countDown(); }
            public void onServiceDisconnected(ComponentName name){ remote=null; }
        };
        assertTrue(context.bindService(new Intent(context,PythonService.class),connection,Context.BIND_AUTO_CREATE));
        assertTrue("service connection",connected.await(15,TimeUnit.SECONDS));
    }
    @After public void tearDown() throws Exception {
        if(remote!=null)try{remote.send(Message.obtain(null,PythonService.STOP));}catch(RemoteException ignored){}
        context.unbindService(connection);context.stopService(new Intent(context,PythonService.class));
        callbackThread.quitSafely();
    }
    private JSONObject request(String action,String code) throws Exception {
        JSONObject request=new JSONObject().put("unit","np_elementwise").put("variant",0).put("action",action).put("code",code);
        Message message=Message.obtain(null,PythonService.RUN);message.replyTo=reply;Bundle data=new Bundle();data.putString("request",request.toString());message.setData(data);remote.send(message);
        String raw=responses.poll(45,TimeUnit.SECONDS);assertNotNull("response timeout",raw);return new JSONObject(raw);
    }
    @Test public void testActualLibrariesAndRetry() throws Exception {
        String code="import numpy as np\nimport pandas as pd\nimport matplotlib.pyplot as plt\nfrom scipy.stats import norm\nimport seaborn as sns\nfrom sklearn.linear_model import LinearRegression\n"
            +"assert np.array([1,2,3]).sum()==6\nassert pd.Series([1,3,5]).mean()==3\nassert abs(norm.pdf(0)-0.3989422804014327)<1e-8\n"
            +"model=LinearRegression().fit([[0],[1],[2]],[1,3,5])\nassert abs(model.predict([[3]])[0]-7)<1e-6\n"
            +"fig,ax=plt.subplots()\nax.plot([0,1,2],[0,1,4])\nresult=a+b\nprint('ANDROID_NATIVE_LIBRARIES_OK')";
        JSONObject result=request("execute",code);assertTrue(result.toString(),result.optBoolean("ok"));
        assertTrue(result.toString(),result.optString("output").contains("ANDROID_NATIVE_LIBRARIES_OK"));
        assertTrue(result.toString(),result.has("figurePath"));
        assertTrue(request("grade","").getJSONObject("grade").getBoolean("passed"));
        JSONObject bad=request("execute","a + np.array([1,2])");assertFalse(bad.toString(),bad.getBoolean("ok"));
        request("execute","result=a+b");assertTrue(request("grade","").getJSONObject("grade").getBoolean("passed"));
    }
    @Test public void testEveryPublishedPracticalOnAndroid() throws Exception {
        String code=String.join("\n",
            "from pathlib import Path", "from python_teaching.course import lessons",
            "from python_teaching.worker import Kernel", "from python_teaching.values import grade_snapshot",
            "kernel=Kernel(Path.cwd())", "checked=0", "for unit in lessons():",
            "    for variant,task in enumerate(unit.problems):",
            "        kernel.plt.close('all')", "        kernel.namespace={'__name__':'__main__'}",
            "        for name,spec in task.files.items():",
            "            path=Path(name)", "            path.parent.mkdir(parents=True,exist_ok=True)",
            "            path.write_text(spec['text'],encoding=spec.get('encoding','utf-8'))",
            "        prepared=kernel.execute(task.initial)",
            "        assert prepared['ok'],(unit.key,variant,prepared)",
            "        before,_=kernel.inspect_values(task.targets,task.probes)",
            "        assert not grade_snapshot(before,task.checks)['passed'],(unit.key,'already complete')",
            "        result=kernel.execute(task.solution)", "        assert result['ok'],(unit.key,variant,result)",
            "        values,errors=kernel.inspect_values(task.targets,task.probes)",
            "        grade=grade_snapshot(values,task.checks)",
            "        assert grade['passed'],(unit.key,variant,grade,errors)", "        checked+=1",
            "kernel.plt.close('all')", "print('ANDROID_ALL_PRACTICALS_OK',checked)");
        JSONObject result=request("execute",code);
        assertTrue(result.toString(),result.optBoolean("ok"));
        assertTrue(result.toString(),result.optString("output").contains("ANDROID_ALL_PRACTICALS_OK"));
    }
    @Test public void testOnlyFourNewPandasUnits() throws Exception {
        String code=String.join("\n",
            "from pathlib import Path", "from python_teaching.course import lessons",
            "from python_teaching.worker import Kernel", "from python_teaching.values import grade_snapshot",
            "changed={'pd_datetime_index','pd_weather_audit','pd_series_charts','pd_concat_labels'}",
            "kernel=Kernel(Path.cwd())", "checked=0", "for unit in lessons():",
            "    if unit.key not in changed: continue",
            "    for variant,task in enumerate(unit.problems):",
            "        kernel.plt.close('all')", "        kernel.namespace={'__name__':'__main__'}",
            "        for name,spec in task.files.items():",
            "            path=Path(name)", "            path.parent.mkdir(parents=True,exist_ok=True)",
            "            path.write_text(spec['text'],encoding=spec.get('encoding','utf-8'))",
            "        prepared=kernel.execute(task.initial)", "        assert prepared['ok'],(unit.key,variant,prepared)",
            "        before,_=kernel.inspect_values(task.targets,task.probes)",
            "        assert not grade_snapshot(before,task.checks)['passed'],(unit.key,'already solved')",
            "        result=kernel.execute(task.solution)", "        assert result['ok'],(unit.key,variant,result)",
            "        values,errors=kernel.inspect_values(task.targets,task.probes)",
            "        grade=grade_snapshot(values,task.checks)", "        assert grade['passed'],(unit.key,variant,grade,errors)",
            "        checked+=1", "kernel.plt.close('all')", "assert checked==12,checked",
            "print('ANDROID_NEW_PANDAS_ONLY_OK',checked)");
        JSONObject result=request("execute",code);
        assertTrue(result.toString(),result.optBoolean("ok"));
        assertTrue(result.optString("output"),result.optString("output").contains("ANDROID_NEW_PANDAS_ONLY_OK 12"));
    }
    @Test public void testSupplementalLibraryWrongAndEquivalentAnswers() throws Exception {
        String code=String.join("\n",
            "from pathlib import Path", "from python_teaching.library_course import lessons,validation_cases",
            "from python_teaching.worker import Kernel", "from python_teaching.values import grade_snapshot",
            "kernel=Kernel(Path.cwd())", "units={unit.key:unit for unit in lessons()}", "checked=0",
            "for case in validation_cases():", "    task=units[case['lesson']].problems[case['problem']]",
            "    for kind,expected in [('wrong',False),('equivalent',True)]:",
            "        kernel.plt.close('all')", "        kernel.namespace={'__name__':'__main__'}",
            "        prepared=kernel.execute(task.initial)", "        assert prepared['ok'],prepared",
            "        result=kernel.execute(case[kind])", "        assert result['ok'],result",
            "        values,errors=kernel.inspect_values(task.targets,task.probes)",
            "        grade=grade_snapshot(values,task.checks)",
            "        assert grade['passed']==expected,(case['lesson'],case['problem'],kind,grade,errors)",
            "        checked+=1", "kernel.plt.close('all')", "assert checked==46,checked",
            "print('ANDROID_LIBRARY_VARIANTS_OK',checked)");
        JSONObject result=request("execute",code);
        assertTrue(result.toString(),result.optBoolean("ok"));
        assertTrue(result.toString(),result.optString("output").contains("ANDROID_LIBRARY_VARIANTS_OK 46"));
    }
    @Test public void testReviewWrongAndEquivalentAnswers() throws Exception {
        String code=String.join("\n",
            "from pathlib import Path", "from python_teaching.course import lessons",
            "from python_teaching.review_validation import validation_cases",
            "from python_teaching.worker import Kernel", "from python_teaching.values import grade_snapshot",
            "kernel=Kernel(Path.cwd())", "units={unit.key:unit for unit in lessons()}", "checked=0",
            "cases=validation_cases()", "assert len(cases)>=9", "for case in cases:",
            "    task=units[case['lesson']].problems[case['problem']]",
            "    for kind,expected in [('wrong',False),('equivalent',True)]:",
            "        kernel.plt.close('all')", "        kernel.namespace={'__name__':'__main__'}",
            "        for name,spec in task.files.items():",
            "            path=Path(name)", "            path.parent.mkdir(parents=True,exist_ok=True)",
            "            path.write_text(spec['text'],encoding=spec.get('encoding','utf-8'))",
            "        prepared=kernel.execute(task.initial)", "        assert prepared['ok'],prepared",
            "        result=kernel.execute(case[kind])", "        assert result['ok'],result",
            "        values,errors=kernel.inspect_values(task.targets,task.probes)",
            "        grade=grade_snapshot(values,task.checks)",
            "        assert grade['passed']==expected,(case['id'],kind,grade,errors)",
            "        checked+=1", "kernel.plt.close('all')", "assert checked==2*len(cases)",
            "print('ANDROID_REVIEW_VARIANTS_OK',checked)");
        JSONObject result=request("execute",code);
        assertTrue(result.toString(),result.optBoolean("ok"));
        assertTrue(result.toString(),result.optString("output").contains("ANDROID_REVIEW_VARIANTS_OK"));
    }
}
