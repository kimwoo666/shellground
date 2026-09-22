package org.shellground.runtime;

import android.content.Context;
import android.net.LocalServerSocket;
import android.net.LocalSocket;
import android.os.Looper;
import org.json.JSONObject;
import java.io.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.util.*;
import java.util.concurrent.*;

/** Owns a real offline VM. Call start/close on a worker, never the UI thread.
 * No host filesystem mounts, shared Docker socket, external ports or shell parser.
 * Each run uses QEMU's temporary overlay; the verified base image stays immutable.
 */
public final class GuestMachine implements AutoCloseable {
    private volatile Process process;
    private volatile Thread logReader;
    private volatile GuestChannel channel;
    private final StringBuilder log = new StringBuilder();
    private File scratch;
    private volatile boolean closed;
    private boolean cleaned;

    private static void workerOnly() {
        if (Looper.myLooper() == Looper.getMainLooper())
            throw new IllegalStateException("Linux 시작/종료는 UI 스레드에서 실행할 수 없습니다.");
    }

    public static GuestMachine start(Context context, File pack, GuestChannel.Events events) throws Exception {
        workerOnly();
        GuestMachine machine = new GuestMachine();
        try { machine.boot(context, pack, events); return machine; }
        catch (Exception failure) {
            try { machine.close(); } catch (Exception cleanup) { failure.addSuppressed(cleanup); }
            throw failure;
        }
    }

    public void boot(Context context, File pack, GuestChannel.Events events) throws Exception {
        boot(context,pack,events,message->{});
    }

    public void boot(Context context, File pack, GuestChannel.Events events, java.util.function.Consumer<String> stage) throws Exception {
        workerOnly();
        if(closed)throw new IOException("Linux 시작이 취소되었습니다.");
        String allowed = context.getFilesDir().getCanonicalPath() + File.separator;
        if (!pack.getCanonicalPath().startsWith(allowed) || pack.getPath().contains(","))
            throw new IOException("앱 전용 실습 이미지 폴더만 사용할 수 있습니다.");
        File manifestFile = new File(pack, "manifest.json");
        if (manifestFile.length() > 256 * 1024) throw new IOException("실습 이미지 정보가 너무 큽니다.");
        JSONObject manifest = new JSONObject(new String(Files.readAllBytes(manifestFile.toPath()), StandardCharsets.UTF_8));
        if (manifest.optInt("schema") != 1 || !"aarch64".equals(manifest.optString("guest_arch")))
            throw new IOException("지원하지 않는 실습 이미지 형식입니다.");
        JSONObject files = manifest.getJSONObject("files");
        PackVerifier.verify(context,pack,files,stage);
        stage.accept("Linux 부팅 중 · 설명을 계속 읽을 수 있습니다.");
        File executable = new File(context.getApplicationInfo().nativeLibraryDir, "libshellground_qemu.so");
        if (!executable.canExecute()) throw new IOException("Android Linux 실행기가 포함되지 않았습니다.");
        synchronized(this){
            if(closed||Thread.currentThread().isInterrupted())throw new InterruptedException("Linux 시작 취소");
            scratch = Files.createTempDirectory(context.getCacheDir().toPath(), "sg-guest-").toFile();
        }
        String endpoint = "sg-guest-" + UUID.randomUUID();
        ExecutorService acceptor = Executors.newSingleThreadExecutor();
        try (LocalServerSocket server = new LocalServerSocket(endpoint)) {
            Future<LocalSocket> accepted = acceptor.submit(server::accept);
            List<String> args = Arrays.asList(executable.getAbsolutePath(),
                "-name", "shellground-training", "-machine", "virt", "-cpu", "cortex-a72",
                "-accel", "tcg,thread=multi,tb-size=64", "-smp", "2", "-m", "2048",
                "-display", "none", "-monitor", "none", "-no-reboot", "-nic", "none",
                "-kernel", new File(pack,"kernel").getAbsolutePath(),
                "-initrd", new File(pack,"initrd").getAbsolutePath(),
                "-append", "root=LABEL=cloudimg-rootfs rw console=ttyAMA0",
                "-serial", "stdio", "-drive", "file=" + new File(pack,"base.qcow2").getAbsolutePath() + ",format=qcow2,if=virtio,snapshot=on",
                "-device", "virtio-serial-pci", "-chardev", "socket,id=sg,path=" + endpoint + ",abstract=on",
                "-device", "virtserialport,chardev=sg,name=org.shellground.agent");
            ProcessBuilder builder = new ProcessBuilder(args).directory(scratch).redirectErrorStream(true);
            builder.environment().put("TMPDIR", scratch.getAbsolutePath());
            synchronized(this) {
                if(closed||Thread.currentThread().isInterrupted())throw new InterruptedException("Linux 시작 취소");
                process = builder.start();
                logReader = new Thread(() -> {
                try (InputStream input = process.getInputStream()) {
                    byte[] buffer = new byte[4096]; int count;
                    while ((count = input.read(buffer)) != -1) synchronized (log) {
                        log.append(new String(buffer,0,count,StandardCharsets.UTF_8));
                        if (log.length() > 65536) log.delete(0,log.length()-65536);
                    }
                } catch (IOException ignored) { }
            }, "shellground-guest-log");
                logReader.start();
            }
            GuestChannel connected = new GuestChannel(accepted.get(20, TimeUnit.SECONDS), events);
            synchronized(this) {
                if(closed){connected.close();throw new IOException("Linux 시작이 취소되었습니다.");}
                channel = connected;
            }
            JSONObject state = (JSONObject)channel.request("status",new JSONObject(),360000);
            if (!"shellground".equals(state.optString("guest")) || state.optInt("protocol") != 1
                    || !state.optBoolean("provisioned")) throw new IOException("실습 환경 준비가 완료되지 않았습니다: " + state);
        } catch (Exception error) {
            PackVerifier.invalidate(context);
            throw new IOException("Linux 실습 환경을 시작하지 못했습니다.\n" + diagnosticLog(), error);
        } finally {
            acceptor.shutdownNow();
            if (!acceptor.awaitTermination(3000, TimeUnit.MILLISECONDS))
                throw new IOException("Linux 연결 대기 작업이 종료되지 않았습니다.");
        }
    }

    public GuestChannel channel() { return channel; }
    public String diagnosticLog() { synchronized(log) { return log.toString(); } }
    public boolean isAlive() { return process != null && process.isAlive(); }
    public boolean readerAlive() { return logReader != null && logReader.isAlive(); }

    @Override public synchronized void close() throws Exception {
        workerOnly();
        if (cleaned) return;
        closed = true;
        // A cancelled startup worker may already be interrupted. That must
        // prevent future boot, not skip reaping its child. Preserve the caller's
        // interrupt after this bounded cleanup. If a new interrupt/error occurs,
        // cleaned stays false so the independent stop owner can finish cleanup.
        boolean interrupted = Thread.interrupted();
        try {
            if (channel != null) {
                try { channel.request("exec",new JSONObject().put("root",true)
                    .put("argv",new org.json.JSONArray().put("systemctl").put("poweroff")),3000); }
                catch (InterruptedException cancelled) { interrupted = true; }
                catch (Exception ignored) { }
                channel.close();
            }
            if (process != null && !process.waitFor(10,TimeUnit.SECONDS)) {
                process.destroy();
                if (!process.waitFor(2,TimeUnit.SECONDS)) process.destroyForcibly();
                if (!process.waitFor(3,TimeUnit.SECONDS)) throw new IOException("Linux 작업 종료 시간 초과");
            }
            if (logReader != null) {
                logReader.join(3000);
                if (logReader.isAlive()) throw new IOException("Linux 출력 작업이 종료되지 않았습니다.");
            }
            // Only this run's known temporary directory, never the installed pack.
            if (scratch != null) {
                File[] children = scratch.listFiles();
                if (children != null) for (File child : children) if (child.isFile()) Files.deleteIfExists(child.toPath());
                Files.deleteIfExists(scratch.toPath());
            }
            cleaned = true;
        } finally {
            if (interrupted) Thread.currentThread().interrupt();
        }
    }
}
