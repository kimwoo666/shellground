package org.shellground.runtimeprobe;

import android.net.LocalServerSocket;
import android.net.LocalSocket;
import android.net.LocalSocketAddress;
import org.shellground.runtime.GuestChannel;
import org.json.JSONObject;
import org.junit.Test;
import org.junit.runner.RunWith;
import androidx.test.ext.junit.runners.AndroidJUnit4;
import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.util.UUID;
import java.util.concurrent.ArrayBlockingQueue;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicReference;
import static org.junit.Assert.*;

/** Protocol-only transport tests. These do NOT claim actual Linux execution. */
@RunWith(AndroidJUnit4.class)
public class GuestChannelTest {
    @Test public void responsesAndTerminalEventsSurviveSplitUtf8() throws Exception {
        String name = "sg-channel-" + UUID.randomUUID();
        ArrayBlockingQueue<JSONObject> events = new ArrayBlockingQueue<>(4);
        try (LocalServerSocket server = new LocalServerSocket(name); LocalSocket peer = new LocalSocket()) {
            peer.connect(new LocalSocketAddress(name));
            try (GuestChannel channel = new GuestChannel(server.accept(), events::offer)) {
                AtomicReference<Throwable> error = new AtomicReference<>();
                Thread responder = new Thread(() -> {
                    try {
                        BufferedReader input = new BufferedReader(new InputStreamReader(peer.getInputStream(), StandardCharsets.UTF_8));
                        JSONObject request = new JSONObject(input.readLine());
                        String replies = new JSONObject().put("session", "1").put("output", "eA==").toString() + "\n"
                            + new JSONObject().put("id", request.getInt("id")).put("result", new JSONObject().put("label", "실제 연결")).toString() + "\n";
                        // Deliberately split inside multibyte characters and across JSON frames.
                        for (byte b : replies.getBytes(StandardCharsets.UTF_8)) peer.getOutputStream().write(b);
                        peer.getOutputStream().flush();
                        JSONObject close = new JSONObject(input.readLine());
                        peer.getOutputStream().write((new JSONObject().put("id", close.getInt("id")).put("result", true).toString() + "\n").getBytes(StandardCharsets.UTF_8));
                        peer.getOutputStream().flush();
                    } catch (Throwable failure) { error.set(failure); }
                });
                responder.start();
                assertEquals("실제 연결", ((JSONObject)channel.request("status", new JSONObject(), 3000)).getString("label"));
                assertEquals("1", events.poll(1, TimeUnit.SECONDS).getString("session"));
                assertEquals(Boolean.TRUE, channel.request("close", new JSONObject().put("session", "1"), 3000));
                responder.join(3000); assertFalse(responder.isAlive()); assertNull(error.get());
            }
        }
    }

    @Test public void closedAndTimedOutChannelsDoNotHang() throws Exception {
        String name = "sg-channel-" + UUID.randomUUID();
        try (LocalServerSocket server = new LocalServerSocket(name); LocalSocket peer = new LocalSocket()) {
            peer.connect(new LocalSocketAddress(name));
            try (GuestChannel channel = new GuestChannel(server.accept(), null)) {
                try { channel.request("status", new JSONObject(), 50); fail("Expected bounded timeout"); }
                catch (IOException expected) { assertTrue(expected.getMessage().contains("시간 초과")); }
                channel.close(); assertTrue(channel.isClosed());
                long start = System.nanoTime();
                try { channel.request("status", new JSONObject(), 3000); fail("Expected closed channel"); }
                catch (IOException expected) { assertTrue(TimeUnit.NANOSECONDS.toMillis(System.nanoTime() - start) < 1000); }
            }
        }
    }

    @Test public void closingWakesAnOutstandingRequest() throws Exception {
        String name = "sg-channel-" + UUID.randomUUID();
        try (LocalServerSocket server = new LocalServerSocket(name); LocalSocket peer = new LocalSocket()) {
            peer.connect(new LocalSocketAddress(name));
            try (GuestChannel channel = new GuestChannel(server.accept(), null)) {
                AtomicReference<Throwable> result = new AtomicReference<>();
                Thread caller = new Thread(() -> {
                    try { channel.request("status", new JSONObject(), 10000); result.set(new AssertionError("Expected close failure")); }
                    catch (Throwable error) { result.set(error); }
                });
                caller.start(); peer.setSoTimeout(3000);
                assertNotNull(new BufferedReader(new InputStreamReader(peer.getInputStream(), StandardCharsets.UTF_8)).readLine());
                channel.close(); caller.join(1000);
                assertFalse("Close must wake pending requests, not await their original timeout", caller.isAlive());
                assertTrue(result.get() instanceof IOException);
            }
        }
    }
}
