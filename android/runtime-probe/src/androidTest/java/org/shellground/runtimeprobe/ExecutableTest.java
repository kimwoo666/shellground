package org.shellground.runtimeprobe;

import android.content.Context;
import android.os.Bundle;
import android.net.LocalServerSocket;
import android.net.LocalSocket;
import androidx.test.platform.app.InstrumentationRegistry;
import androidx.test.ext.junit.runners.AndroidJUnit4;
import org.junit.Test;
import org.junit.runner.RunWith;
import static org.junit.Assert.*;
import java.io.File;
import java.io.InputStream;
import java.io.FileOutputStream;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.Executors;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Future;
import java.util.UUID;
import java.io.ByteArrayOutputStream;

/** Executes only the packaged candidate. Does not borrow a host/Termux binary. */
@RunWith(AndroidJUnit4.class)
public class ExecutableTest {
    private static class Session implements AutoCloseable {
        final Process process;
        final StringBuilder output = new StringBuilder();
        final Thread reader;
        volatile Throwable readFailure;
        Session(String... args) throws Exception {
            Context context = InstrumentationRegistry.getInstrumentation().getTargetContext();
            File executable = new File(context.getApplicationInfo().nativeLibraryDir, "libshellground_qemu.so");
            assertTrue("Installer must extract executable: " + executable, executable.canExecute());
            assertFalse(executable.getCanonicalPath().startsWith(context.getFilesDir().getCanonicalPath()));
            ArrayList<String> argv = new ArrayList<>();
            argv.add(executable.getAbsolutePath()); argv.addAll(Arrays.asList(args));
            ProcessBuilder builder = new ProcessBuilder(argv).redirectErrorStream(true);
            builder.directory(context.getCacheDir());
            builder.environment().put("TMPDIR", context.getCacheDir().getAbsolutePath());
            process = builder.start();
            reader = new Thread(() -> {
                try (InputStream stream = process.getInputStream()) {
                    byte[] buffer = new byte[4096]; int count;
                    while ((count = stream.read(buffer)) >= 0) {
                        synchronized (output) {
                            output.append(new String(buffer, 0, count, StandardCharsets.UTF_8));
                            if (output.length() > 262144) throw new IllegalStateException("Probe output exceeded bound");
                        }
                    }
                } catch (Throwable error) { readFailure = error; }
            }, "qemu-probe-output");
            reader.start();
        }
        String text() { synchronized (output) { return output.toString(); } }
        void waitText(String needle) throws Exception {
            waitText(needle, 15);
        }
        void waitText(String needle, int timeoutSeconds) throws Exception {
            long deadline = System.nanoTime() + TimeUnit.SECONDS.toNanos(timeoutSeconds);
            while (!text().contains(needle) && !text().contains("Kernel panic") && process.isAlive() && System.nanoTime() < deadline) Thread.sleep(30);
            assertTrue("Missing " + needle + "\n" + text(), text().contains(needle));
            if (readFailure != null) throw new AssertionError(readFailure);
        }
        synchronized void send(String text) throws Exception {
            process.getOutputStream().write(text.getBytes(StandardCharsets.UTF_8));
            process.getOutputStream().flush();
        }
        @Override public void close() throws Exception {
            if (process.isAlive()) process.destroy();
            if (!process.waitFor(2, TimeUnit.SECONDS)) process.destroyForcibly();
            assertTrue("Probe child survived close", process.waitFor(3, TimeUnit.SECONDS));
            reader.join(3000);
            assertFalse("Probe output reader survived close", reader.isAlive());
        }
    }

    private Session pausedMachine() throws Exception {
        return new Session("-machine", "virt", "-cpu", "cortex-a53", "-accel", "tcg,thread=multi,tb-size=16",
            "-smp", "2", "-m", "128", "-nodefaults", "-display", "none", "-serial", "none",
            "-monitor", "stdio", "-S");
    }

    @Test public void installedExecutableReportsActualVersion() throws Exception {
        try (Session session = new Session("--version")) {
            assertTrue(session.process.waitFor(15, TimeUnit.SECONDS));
            session.reader.join(3000);
            assertEquals(session.text(), 0, session.process.exitValue());
            assertTrue(session.text(), session.text().contains("QEMU emulator version 11.0.3"));
        }
    }

    @Test public void actualArmMachineStartsAndQuits() throws Exception {
        try (Session session = pausedMachine()) {
            session.waitText("(qemu)");
            session.send("info status\n"); session.waitText("paused");
            session.send("quit\n");
            assertTrue(session.text(), session.process.waitFor(5, TimeUnit.SECONDS));
            assertEquals(session.text(), 0, session.process.exitValue());
        }
    }

    @Test public void ownedMachineCanBeForciblyStopped() throws Exception {
        try (Session session = pausedMachine()) {
            session.waitText("(qemu)");
            session.process.destroyForcibly();
            assertTrue(session.process.waitFor(3, TimeUnit.SECONDS));
            assertFalse(session.process.isAlive());
        }
    }

    @Test public void actualQemuUsesPrivateUnixSocketWithoutInternetPermission() throws Exception {
        String endpoint = "sg-qemu-" + UUID.randomUUID();
        ExecutorService acceptor = Executors.newSingleThreadExecutor();
        try (LocalServerSocket server = new LocalServerSocket(endpoint)) {
            Future<LocalSocket> connected = acceptor.submit(server::accept);
            try (Session session = new Session("-machine", "virt", "-cpu", "cortex-a53",
                    "-accel", "tcg,thread=multi,tb-size=16", "-smp", "2", "-m", "128",
                    "-nodefaults", "-display", "none", "-serial", "none", "-S",
                    "-chardev", "socket,id=control,path=" + endpoint + ",abstract=on",
                    "-monitor", "chardev:control");
                    LocalSocket socket = connected.get(5, TimeUnit.SECONDS)) {
                socket.setSoTimeout(3000);
                socket.getOutputStream().write("info status\nquit\n".getBytes(StandardCharsets.UTF_8));
                socket.getOutputStream().flush();
                ByteArrayOutputStream monitor = new ByteArrayOutputStream();
                byte[] buffer = new byte[4096]; int count;
                while ((count = socket.getInputStream().read(buffer)) != -1) {
                    monitor.write(buffer, 0, count);
                    assertTrue(monitor.size() < 32768);
                }
                String text = monitor.toString(StandardCharsets.UTF_8.name());
                assertTrue(text, text.contains("paused"));
                assertTrue(session.process.waitFor(5, TimeUnit.SECONDS));
                assertEquals(session.text(), 0, session.process.exitValue());
            }
        } finally {
            acceptor.shutdownNow(); assertTrue(acceptor.awaitTermination(3, TimeUnit.SECONDS));
        }
    }

    private File bootAsset(String name) throws Exception {
        Context context = InstrumentationRegistry.getInstrumentation().getTargetContext();
        File target = new File(context.getCacheDir(), name);
        try (InputStream source = context.getAssets().open(name); FileOutputStream output = new FileOutputStream(target)) {
            byte[] buffer = new byte[65536]; int size;
            while ((size = source.read(buffer)) >= 0) output.write(buffer, 0, size);
        }
        return target;
    }

    @Test public void actualLinuxBootShellFileAndPoweroff() throws Exception {
        File kernel = bootAsset("linux-kernel"), initrd = bootAsset("linux-initramfs");
        long started = System.nanoTime();
        try (Session session = new Session("-machine", "virt", "-cpu", "cortex-a53", "-accel", "tcg,thread=multi,tb-size=16",
                "-smp", "2", "-m", "384", "-nodefaults", "-display", "none", "-serial", "stdio", "-monitor", "none",
                "-kernel", kernel.getAbsolutePath(), "-initrd", initrd.getAbsolutePath(),
                "-append", "console=ttyAMA0 rdinit=/bin/sh loglevel=4 TERM=dumb", "-no-reboot")) {
            session.waitText("~ #", 60);
            // Reply to the real shell's initial VT cursor-position query.
            session.send("\u001b[1;1R");
            // rdinit bypasses Alpine's normal /init, which normally installs these applet links.
            session.send("export PATH=/usr/bin:/bin:/usr/sbin:/sbin; /bin/busybox --install -s /bin; mount -t proc proc /proc; printf 'SG_ARCH_%s\\n' \"$(uname -m)\"\n");
            session.waitText("SG_ARCH_aarch64");
            session.send("mkdir -p /practice; printf '%s' linux > '/practice/read me.txt'; printf '_%s' works >> '/practice/read me.txt'; printf 'SG_FILE_%s\\n' \"$(cat '/practice/read me.txt')\"\n");
            session.waitText("SG_FILE_linux_works");
            session.send("poweroff -f\n");
            assertTrue(session.text(), session.process.waitFor(15, TimeUnit.SECONDS));
            assertEquals(session.text(), 0, session.process.exitValue());
            assertTrue(session.text(), session.text().contains("Power down"));
            Bundle evidence = new Bundle();
            evidence.putString("stream", "\nREAL_LINUX_BOOT_FILE_POWEROFF_OK elapsed_ms="
                + TimeUnit.NANOSECONDS.toMillis(System.nanoTime() - started) + "\n" + session.text() + "\n");
            InstrumentationRegistry.getInstrumentation().sendStatus(0, evidence);
        } finally {
            assertTrue("Owned kernel asset cleanup", kernel.delete());
            assertTrue("Owned initramfs asset cleanup", initrd.delete());
        }
    }
}
