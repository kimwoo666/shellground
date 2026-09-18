package org.shellground.learn;

import android.content.Context;
import android.util.Base64;
import androidx.test.platform.app.InstrumentationRegistry;
import androidx.test.ext.junit.runners.AndroidJUnit4;
import org.json.*;
import org.junit.*;
import org.junit.runner.RunWith;
import java.io.*;
import java.nio.charset.StandardCharsets;
import java.util.*;
import static org.junit.Assert.*;

/** Protocol/asset tests only. Synthetic transport replies below must never be
 * reported as real Conda or ARM execution evidence. */
@RunWith(AndroidJUnit4.class)
public final class CondaGuestTest {
    private JSONObject mission()throws Exception{
        return new JSONObject("{\"kind\":\"conda\",\"problem\":{\"id\":\"protocol-only\","
            +"\"answer_fields\":[{\"key\":\"exists\",\"expected\":true},{\"key\":\"version\",\"expected_ref\":\"runtime.conda_version\"}]},\"probes\":{}}");
    }
    private JSONObject ready()throws Exception{
        return new JSONObject().put("ready",true).put("start",CondaGuest.WORKSPACE)
            .put("runtime",new JSONObject().put("root_prefix","/opt/shellground/miniconda").put("platform","linux-aarch64"));
    }
    private JSONObject output(String value)throws Exception{
        return new JSONObject().put("code",0).put("err","").put("out",Base64.encodeToString(value.getBytes(StandardCharsets.UTF_8),Base64.NO_WRAP));
    }
    private byte[] asset(String name)throws Exception{
        Context context=InstrumentationRegistry.getInstrumentation().getTargetContext();
        try(InputStream input=context.getAssets().open(name);ByteArrayOutputStream out=new ByteArrayOutputStream()){
            byte[] buffer=new byte[8192];int count;while((count=input.read(buffer))!=-1)out.write(buffer,0,count);return out.toByteArray();
        }
    }

    @Test public void packagedTeachingKeepsBootstrapWithoutGrantingReadiness()throws Exception{
        JSONObject course=new JSONObject(new String(asset("conda-course.json"),StandardCharsets.UTF_8));
        assertEquals(2,course.getInt("schema"));assertEquals(20,course.getJSONArray("units").length());
        assertEquals("conda_install_once",course.getJSONObject("bootstrap").getJSONObject("optional_install_exercise").getString("key"));
        assertEquals("real-guest",course.getString("execution"));
        assertFalse("Data export is not an execution report",course.has("validation_passed"));
        for(int i=0;i<20;i++){
            JSONArray problems=course.getJSONArray("units").getJSONObject(i).getJSONArray("problems");assertEquals(3,problems.length());
            for(int j=0;j<3;j++){
                JSONObject problem=problems.getJSONObject(j);assertFalse(problem.has("reference_commands"));
                if(j>0)assertEquals(0,problem.getJSONArray("example_commands").length());
                if(problem.getString("id").equals("conda_identity_example"))
                    assertFalse("Version lookup has no transaction to approve",CondaLesson.problem(problem,true).contains("확인 질문"));
                JSONArray fields=problem.getJSONArray("answer_fields");
                for(int f=0;f<fields.length();f++)assertEquals(3,fields.getJSONObject(f).length());
            }
        }
    }

    @Test public void failedActualReplyAndTypedAnswersAreNotOverridden()throws Exception{
        JSONObject failed=new JSONObject().put("passed",false).put("checks",new JSONArray().put(new JSONObject().put("passed",false).put("label","remaining")));
        List<JSONObject> requests=new ArrayList<>();
        CondaGuest adapter=new CondaGuest((action,payload,time)->{
            if(action.equals("prepare"))return ready();
            assertEquals("grade",action);requests.add(payload);return failed;
        },name->{throw new AssertionError("No asset reading needed for grading");});
        JSONObject original=mission();adapter.prepare(original);original.getJSONObject("problem").put("id","changed");
        JSONObject answers=new JSONObject().put("exists",false).put("version","  actual value  ");
        assertSame(failed,adapter.grade("12",answers));
        JSONObject request=requests.get(0);assertEquals("12",request.getString("session"));
        assertEquals("protocol-only",request.getJSONObject("mission").getJSONObject("problem").getString("id"));
        assertEquals(Boolean.FALSE,request.getJSONObject("answers").get("exists"));
        assertEquals("  actual value  ",request.getJSONObject("answers").getString("version"));
    }

    @Test public void blanksDoNotBecomeFalseAndWrongInputTypesAreRejected()throws Exception{
        JSONArray fields=mission().getJSONObject("problem").getJSONArray("answer_fields");
        assertEquals(0,CondaGuest.typedAnswers(fields,new JSONObject()).length());
        assertEquals(Boolean.FALSE,CondaGuest.typedAnswers(fields,new JSONObject().put("exists",false)).get("exists"));
        for(JSONObject invalid:new JSONObject[]{new JSONObject().put("exists","false"),new JSONObject().put("version",true),new JSONObject().put("foreign","x")}){
            try{CondaGuest.typedAnswers(fields,invalid);fail("Invalid input must not be silently coerced");}catch(IOException expected){}
        }
    }

    @Test public void failedPreparationCannotGradeAnOldMission()throws Exception{
        int[] prepares={0};CondaGuest adapter=new CondaGuest((action,payload,time)->{
            assertEquals("prepare",action);if(prepares[0]++>0)throw new IOException("unit-only failed preparation");return ready();
        },name->new byte[0]);
        try{adapter.grade("1",new JSONObject());fail("No prepared mission");}catch(IOException expected){}
        adapter.prepare(mission());
        try{adapter.prepare(mission());fail("Injected failure");}catch(IOException expected){}
        try{adapter.grade("1",new JSONObject());fail("Old mission must not survive");}catch(IOException expected){}
    }

    @Test public void configOnlyWritesFixedGuestAdaptersAndViewerIsReadOnly()throws Exception{
        List<JSONObject> requests=new ArrayList<>();List<String> assets=new ArrayList<>();
        CondaGuest adapter=new CondaGuest((action,payload,time)->{
            if(action.equals("prepare"))return ready();
            assertEquals("exec",action);requests.add(payload);return output("{}");
        },name->{assets.add(name);return asset("conda-guest/"+name);});
        adapter.configure();assertEquals(Arrays.asList("conda_runtime.py","shell_snapshot.py","bashrc"),assets);
        for(JSONObject request:requests){
            assertTrue(request.getBoolean("root"));assertEquals("/tmp",request.getString("cwd"));
            assertTrue(request.getJSONArray("argv").getString(2).contains("require_guest()"));
        }
        adapter.prepare(mission());adapter.files("share/environment.yml");
        JSONObject read=requests.get(3);assertFalse(read.getBoolean("root"));assertEquals(5,read.getInt("run_timeout"));
        assertEquals(CondaGuest.WORKSPACE,read.getString("cwd"));
        assertEquals("read",read.getJSONArray("argv").getString(3));
        assertEquals("share/environment.yml",read.getJSONArray("argv").getString(4));
        assertTrue(read.getJSONArray("argv").getString(2).contains("Read-only, bounded text viewer"));
    }
}
