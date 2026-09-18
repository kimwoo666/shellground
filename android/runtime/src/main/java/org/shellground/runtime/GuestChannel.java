package org.shellground.runtime;

import android.net.LocalSocket;
import org.json.JSONObject;
import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.nio.charset.StandardCharsets;
import java.util.concurrent.ArrayBlockingQueue;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.concurrent.atomic.AtomicInteger;

/** App-private Unix-socket transport for the existing real guest agent.
 * No shell commands are interpreted on Android, and no TCP server is exposed.
 * All potentially blocking requests must run off the Android main thread.
 */
public final class GuestChannel implements AutoCloseable {
    public interface Events { void message(JSONObject event); }
    private static final int MAX_LINE = 4 * 1024 * 1024;
    private final LocalSocket socket;
    private final OutputStream output;
    private final ConcurrentHashMap<Integer, ArrayBlockingQueue<JSONObject>> pending = new ConcurrentHashMap<>();
    private final AtomicInteger serial = new AtomicInteger();
    private final AtomicBoolean closed = new AtomicBoolean();
    private final Thread reader;
    private final Events events;

    public GuestChannel(LocalSocket socket, Events events) throws IOException {
        if (socket.getPeerCredentials().getUid() != android.os.Process.myUid()) {
            socket.close();
            throw new IOException("다른 앱의 Linux 제어 연결은 허용하지 않습니다.");
        }
        this.socket = socket;
        this.output = socket.getOutputStream();
        this.events = events;
        reader = new Thread(this::read, "shellground-guest-channel");
        reader.start();
    }

    private void read() {
        String failure = "Linux 연결이 종료되었습니다.";
        try (InputStream input = socket.getInputStream()) {
            ByteArrayOutputStream line = new ByteArrayOutputStream();
            byte[] buffer = new byte[8192]; int count;
            while (!closed.get() && (count = input.read(buffer)) != -1) {
                for (int i = 0; i < count; i++) {
                    if (buffer[i] == '\n') {
                        JSONObject message = new JSONObject(new String(line.toByteArray(), StandardCharsets.UTF_8));
                        line.reset();
                        if (message.has("session")) {
                            // The consumer queues bounded terminal output; it must not block this reader.
                            if (events != null) events.message(message);
                        } else {
                            ArrayBlockingQueue<JSONObject> waiter = pending.get(message.optInt("id", -1));
                            if (waiter != null) waiter.offer(message);
                        }
                    } else {
                        if (line.size() >= MAX_LINE) throw new IOException("Linux 응답 크기가 제한을 초과했습니다.");
                        line.write(buffer[i]);
                    }
                }
            }
        } catch (Exception error) {
            if (!closed.get()) failure = error.toString();
        } finally {
            disconnect(failure);
        }
    }

    public synchronized void send(JSONObject message) throws IOException {
        if (closed.get()) throw new IOException("Linux 연결이 종료되었습니다.");
        byte[] data = (message.toString() + "\n").getBytes(StandardCharsets.UTF_8);
        if (data.length > MAX_LINE) throw new IOException("Linux 요청 크기가 제한을 초과했습니다.");
        output.write(data); output.flush();
    }

    public Object request(String action, JSONObject payload, long timeoutMs) throws Exception {
        if (timeoutMs < 1 || timeoutMs > 360000) throw new IllegalArgumentException("Request timeout out of range");
        int id = serial.incrementAndGet();
        ArrayBlockingQueue<JSONObject> waiter = new ArrayBlockingQueue<>(1);
        pending.put(id, waiter);
        try {
            JSONObject request = new JSONObject(payload.toString()).put("id", id).put("action", action);
            send(request);
            JSONObject reply = waiter.poll(timeoutMs, TimeUnit.MILLISECONDS);
            if (reply == null) throw new IOException("Linux 응답 시간 초과: " + action);
            if (reply.has("error")) throw new IOException(reply.getString("error"));
            // Existing agent actions return objects (status/open/exec) and
            // a boolean (close). Preserve the protocol's actual result type.
            return reply.get("result");
        } finally {
            pending.remove(id);
        }
    }

    private void disconnect(String reason) {
        closed.set(true);
        try { socket.shutdownInput(); } catch (Exception ignored) { }
        try { socket.shutdownOutput(); } catch (Exception ignored) { }
        try { socket.close(); } catch (Exception ignored) { }
        try {
            JSONObject failure = new JSONObject().put("error", reason);
            for (ArrayBlockingQueue<JSONObject> waiter : pending.values()) waiter.offer(failure);
        } catch (Exception ignored) { }
    }

    public boolean isClosed() { return closed.get(); }

    @Override public void close() {
        disconnect("Linux 연결을 닫았습니다.");
        if (Thread.currentThread() != reader) {
            try { reader.join(2000); } catch (InterruptedException error) { Thread.currentThread().interrupt(); }
        }
    }
}
