package org.shellground.runtimeprobe;

import android.content.Context;
import android.os.Bundle;
import android.util.Base64;
import androidx.test.platform.app.InstrumentationRegistry;
import androidx.test.ext.junit.runners.AndroidJUnit4;
import org.shellground.runtime.GuestChannel;
import org.shellground.runtime.GuestMachine;
import org.json.*;
import org.junit.*;
import org.junit.runner.RunWith;
import java.io.*;
import java.nio.charset.StandardCharsets;
import java.util.concurrent.*;
import static org.junit.Assert.*;

/** Opt-in actual Ubuntu/Bash/nano/Docker/ROS acceptance inside Android.
 * The VM is an Android child, not a Linux-host process or a remote connection.
 */
@RunWith(AndroidJUnit4.class)
public class FullGuestTest {
    private final ArrayBlockingQueue<JSONObject> output = new ArrayBlockingQueue<>(512);
    private volatile boolean overflow;
    private GuestChannel channel;
    private String session;

    private String command(boolean root, String... argv) throws Exception {
        JSONObject reply = (JSONObject)channel.request("exec", new JSONObject().put("root",root)
            .put("argv",new JSONArray(argv)).put("run_timeout",110),115000);
        String out = new String(Base64.decode(reply.getString("out"),Base64.DEFAULT),StandardCharsets.UTF_8);
        String err = new String(Base64.decode(reply.getString("err"),Base64.DEFAULT),StandardCharsets.UTF_8);
        assertEquals(out + "\n" + err, 0, reply.getInt("code"));
        return out;
    }

    private void send(String keys) throws Exception {
        channel.send(new JSONObject().put("action","input").put("session",session)
            .put("data",Base64.encodeToString(keys.getBytes(StandardCharsets.UTF_8),Base64.NO_WRAP)));
    }

    private void until(String needle, int seconds) throws Exception {
        long deadline = System.nanoTime()+TimeUnit.SECONDS.toNanos(seconds);
        StringBuilder seen = new StringBuilder();
        while (System.nanoTime()<deadline) {
            JSONObject event = output.poll(1,TimeUnit.SECONDS);
            assertFalse("Bounded terminal output overflowed",overflow);
            if (event == null || !session.equals(event.optString("session"))) continue;
            assertFalse("Real PTY ended: " + seen,event.optBoolean("ended"));
            seen.append(new String(Base64.decode(event.getString("output"),Base64.DEFAULT),StandardCharsets.UTF_8));
            if (seen.indexOf(needle)>=0) return;
            if (seen.length()>65536) seen.delete(0,seen.length()-32768);
        }
        fail("Missing real terminal response " + needle + "\n" + seen);
    }

    @Test public void actualUbuntuNanoGradingDockerRosAndCleanup() throws Exception {
        Assume.assumeTrue("Explicit fullGuest=true and staged private pack required",
            "true".equals(InstrumentationRegistry.getArguments().getString("fullGuest")));
        Context context = InstrumentationRegistry.getInstrumentation().getTargetContext();
        JSONObject fixture;
        try (InputStream input=context.getAssets().open("full-guest-test.json")) {
            ByteArrayOutputStream bytes=new ByteArrayOutputStream();byte[] buffer=new byte[8192];int count;
            while((count=input.read(buffer))!=-1)bytes.write(buffer,0,count);
            fixture=new JSONObject(bytes.toString(StandardCharsets.UTF_8.name()));
        }
        long started=System.nanoTime();
        GuestMachine machine=GuestMachine.start(context,new File(context.getFilesDir(),"training-pack"),
            event->{if(!output.offer(event))overflow=true;});
        long ready=System.nanoTime();
        String platform, docker, ros;
        try {
            channel=machine.channel();
            platform=command(false,"bash","-ec","test \"$(uname -m)\" = aarch64; uname -a; nano --version | head -1");
            JSONObject mission=fixture.getJSONObject("mission");
            channel.request("prepare",new JSONObject().put("mission",mission),120000);
            JSONObject opened=(JSONObject)channel.request("open",new JSONObject().put("cwd",mission.getString("start")),60000);
            session=opened.getString("session");
            channel.send(new JSONObject().put("action","resize").put("session",session).put("size",new JSONArray(new int[]{24,80})));
            send("printf '\\nSG_%s\\n' READY\r");until("SG_READY",30);
            JSONObject gradeRequest=new JSONObject().put("mission",mission).put("session",session).put("output","");
            JSONObject initial=(JSONObject)channel.request("grade",gradeRequest,60000);
            assertFalse("Unchanged file must not pass",initial.getBoolean("passed"));
            send("nano note.txt\r");until("GNU nano",30);
            send("\u000bstatus=ready\u000f");until("File Name to Write",30);
            send("\r");until("Wrote",30);
            send("\u0018");send("printf '\\nSG_%s\\n' SAVED\r");until("SG_SAVED",30);
            assertEquals("status=ready\n",command(false,"cat",mission.getString("target")+"/note.txt"));
            JSONObject passed=(JSONObject)channel.request("grade",gradeRequest,60000);
            assertTrue("Correct real file must pass without restart: "+passed,passed.getBoolean("passed"));
            send("sleep 40\r");Thread.sleep(500);send("\u0003");
            send("printf '\\nSG_%s\\n' INTERRUPTED\r");until("SG_INTERRUPTED",10);
            docker=command(false,"docker","run","--rm","--network=none","localhost:5000/training/alpine:latest",
                "sh","-c","test \"$(uname -m)\" = aarch64; printf SG_REAL_ANDROID_DOCKER");
            assertEquals("SG_REAL_ANDROID_DOCKER",docker);
            // Shell-quote the fixture script rather than treating it as Android executable code.
            String script=fixture.getString("ros_topic_python").replace("'","'\"'\"'");
            ros=command(false,"bash","-ec","source /opt/ros/humble/setup.bash; python3 -c '"+script+"'");
            assertTrue(ros,ros.contains("SG_REAL_ROS_TOPIC_OK"));
            assertEquals(Boolean.TRUE,channel.request("close",new JSONObject().put("session",session),10000));
        } finally {machine.close();}
        assertFalse("Android VM child remains alive",machine.isAlive());
        assertFalse("Android VM output reader remains alive",machine.readerAlive());
        Bundle evidence=new Bundle();
        evidence.putString("stream","\nANDROID_FULL_GUEST_NANO_GRADE_DOCKER_ROS_OK boot_ms="
            +TimeUnit.NANOSECONDS.toMillis(ready-started)+" total_ms="+TimeUnit.NANOSECONDS.toMillis(System.nanoTime()-started)
            +"\n"+platform+docker+"\n"+ros+"\n");
        InstrumentationRegistry.getInstrumentation().sendStatus(0,evidence);
    }
}
