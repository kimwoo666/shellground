package org.shellground.learn;

import android.content.Context;
import android.os.Bundle;
import android.os.SystemClock;
import android.util.Base64;
import androidx.test.platform.app.InstrumentationRegistry;
import androidx.test.ext.junit.runners.AndroidJUnit4;
import org.junit.*;
import org.junit.runner.RunWith;
import org.json.*;
import org.shellground.runtime.GuestMachine;
import org.shellground.runtime.GuestChannel;
import java.io.*;
import java.nio.charset.StandardCharsets;
import java.util.*;
import java.util.concurrent.*;
import java.util.regex.Pattern;
import static org.junit.Assert.*;

/** Opt-in reference-answer acceptance IN Android's actual offline VM.
 * An explicit list prevents claiming untested lessons or silently skipping them.
 * This exercises the shared course/guest grader, not the visible Activity.
 */
@RunWith(AndroidJUnit4.class)
public final class LinuxCourseTest {
    private final BlockingQueue<JSONObject> events=new ArrayBlockingQueue<>(512);
    private final StringBuilder transcript=new StringBuilder();
    private GuestChannel channel;
    private String session;
    private static final Pattern PROMPT=Pattern.compile("learner@lab:[^\\r\\n]*\\$ ");
    private void log(String text){Bundle b=new Bundle();b.putString("stream","\n"+text+"\n");InstrumentationRegistry.getInstrumentation().sendStatus(0,b);}
    private void input(String text)throws Exception{
        channel.send(new JSONObject().put("action","input").put("session",session)
            .put("data",Base64.encodeToString(text.getBytes(StandardCharsets.UTF_8),Base64.NO_WRAP)));
    }
    private String await(String literal,int seconds)throws Exception{
        long end=SystemClock.uptimeMillis()+seconds*1000L;StringBuilder received=new StringBuilder();
        while(SystemClock.uptimeMillis()<end){
            JSONObject event=events.poll(200,TimeUnit.MILLISECONDS);if(event==null)continue;
            if(!session.equals(event.optString("session")))continue;
            assertFalse("Terminal ended unexpectedly",event.optBoolean("ended"));
            if(!event.has("output"))continue;
            String chunk=new String(Base64.decode(event.getString("output"),Base64.DEFAULT),StandardCharsets.UTF_8);
            transcript.append(chunk);received.append(chunk);
            if(transcript.length()>262144)transcript.delete(0,transcript.length()-262144);
            if(received.length()>262144)received.delete(0,received.length()-262144);
            String clean=received.toString().replaceAll("\\x1b\\[[0-?]*[ -/]*[@-~]","");
            if(literal==null?PROMPT.matcher(clean).find():clean.contains(literal))return clean;
        }
        throw new AssertionError("No "+(literal==null?"Bash prompt":literal)+": "+received);
    }
    private JSONObject grade(JSONObject mission)throws Exception{
        return (JSONObject)channel.request("grade",new JSONObject().put("mission",mission)
            .put("session",session).put("output",transcript.toString()),120000);
    }
    private void solve(JSONObject mission)throws Exception{
        String script=mission.getString("solution");
        for(String command:script.split("\n")){
            if(command.isBlank()||command.stripLeading().startsWith("#"))continue;
            if(command.startsWith("nano ")){
                input(command+"\r");await("GNU nano",30);
                if("edit".equals(mission.optString("kind"))&&mission.optInt("practice")==2){
                    // This distinct application preserves the owner line and
                    // appends reviewed=yes, not merely the example's edit.
                    input("\u000bstatus=ready\r\u001b[Breviewed=yes\u000f");
                }else input("\u000bstatus=ready\u000f");
                await("File Name to Write",30);
                input("\r");await("Wrote",30);input("\u0018");await(null,30);
            }else{
                // Only an automation convenience for the actual stock CLIs.
                command=command.replace("sudo apt install tree","sudo apt install -y tree")
                    .replace("docker stop ","docker stop -t 1 ");
                input(command+"\r");await(null,120);
            }
        }
    }
    @Test public void testExplicitCourseVariantsInActualAndroidGuest()throws Exception{
        String requested=InstrumentationRegistry.getArguments().getString("realCourseKeys","");
        Assume.assumeTrue("Explicit comma-separated realCourseKeys required",!requested.isEmpty());
        Set<String> keys=new LinkedHashSet<>(Arrays.asList(requested.split(",")));
        Context context=InstrumentationRegistry.getInstrumentation().getTargetContext();JSONObject course;
        try(InputStream input=context.getAssets().open("real-course.json")){
            ByteArrayOutputStream bytes=new ByteArrayOutputStream();byte[] buffer=new byte[8192];int n;
            while((n=input.read(buffer))!=-1)bytes.write(buffer,0,n);
            course=new JSONObject(bytes.toString(StandardCharsets.UTF_8.name()));
        }
        List<JSONObject> targets=new ArrayList<>();
        for(String group:new String[]{"units","reviews"}){
            JSONArray units=course.getJSONArray(group);
            for(int i=0;i<units.length();i++)if(keys.contains(units.getJSONObject(i).getString("key")))targets.add(units.getJSONObject(i));
        }
        assertEquals("Every requested key must exist",keys.size(),targets.size());
        GuestMachine machine=new GuestMachine();int passed=0;
        try{
            machine.boot(context,new File(context.getFilesDir(),"training-pack"),event->{
                if(!events.offer(event))throw new IllegalStateException("Test output queue overflow");
            });channel=machine.channel();
            for(JSONObject unit:targets){
                String key=unit.getString("key");JSONArray problems=unit.getJSONArray("problems");
                for(int variant=0;variant<problems.length();variant++){
                    JSONObject mission=problems.getJSONObject(variant);log("PREPARING "+key+":"+variant);
                    channel.request("prepare",new JSONObject().put("mission",mission),120000);
                    events.clear();transcript.setLength(0);
                    session=((JSONObject)channel.request("open",new JSONObject().put("cwd",mission.getString("start")),30000)).getString("session");
                    await(null,30);
                    assertFalse(key+":"+variant+" initially solved",grade(mission).getBoolean("passed"));
                    solve(mission);JSONObject result=grade(mission);
                    if(!result.getBoolean("passed")&&"edit".equals(key)){
                        JSONObject file=(JSONObject)channel.request("exec",new JSONObject().put("argv",new JSONArray()
                            .put("python3").put("-c").put("import pathlib,sys;print(repr(pathlib.Path(sys.argv[1]).read_text()))")
                            .put(mission.getString("target")+"/note.txt")),30000);
                        log("ACTUAL_EDIT_FILE "+new String(Base64.decode(file.getString("out"),Base64.DEFAULT),StandardCharsets.UTF_8));
                    }
                    assertTrue(key+":"+variant+" "+result+"\n"+transcript.substring(Math.max(0,transcript.length()-6000)),result.getBoolean("passed"));
                    passed++;log("ANDROID_REAL_VARIANT_OK "+key+":"+variant);
                }
            }
            assertEquals(targets.size()*3,passed);
        }finally{
            machine.close();assertFalse("VM cleanup",machine.isAlive());assertFalse("Reader cleanup",machine.readerAlive());
        }
        log("ANDROID_REAL_COURSE_OK "+targets.size()+" "+passed);
    }
}
