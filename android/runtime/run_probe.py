"""Run acceptance on the explicitly selected developer emulator; adb exit 0 is not success."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import time

from build_dependencies import ANDROID, NATIVE, WORKSPACE


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--serial', required=True)
    args = parser.parse_args()
    if not args.serial.startswith('emulator-'):
        raise ValueError('This developer runner requires an explicitly selected emulator')
    adb = WORKSPACE / 'desktop/.android-tools/sdk/platform-tools/adb'
    command = [str(adb), '-s', args.serial]
    artifacts = [ANDROID / 'runtime-probe/build/outputs/apk/debug/runtime-probe-debug.apk',
                 ANDROID / 'runtime-probe/build/outputs/apk/androidTest/debug/runtime-probe-debug-androidTest.apk']
    hashes = {}
    for artifact in artifacts:
        hashes[artifact.name] = hashlib.sha256(artifact.read_bytes()).hexdigest()
        subprocess.run(command + ['install', '-r', str(artifact)], check=True, timeout=45)
    abi = subprocess.check_output(command + ['shell', 'getprop', 'ro.product.cpu.abi'], text=True, timeout=10).strip()
    api = subprocess.check_output(command + ['shell', 'getprop', 'ro.build.version.sdk'], text=True, timeout=10).strip()
    started = time.monotonic()
    result = subprocess.run(command + ['shell', 'am', 'instrument', '-w', '-e', 'class',
        'org.shellground.runtimeprobe.ExecutableTest,org.shellground.runtimeprobe.GuestChannelTest',
        'org.shellground.runtimeprobe.test/androidx.test.runner.AndroidJUnitRunner'], capture_output=True, text=True, timeout=150)
    transcript = result.stdout + result.stderr
    (NATIVE / 'probe-instrumentation.log').write_text(transcript)
    passed = (result.returncode == 0 and 'OK (8 tests)' in transcript and 'FAILURES!!!' not in transcript
              and 'REAL_LINUX_BOOT_FILE_POWEROFF_OK' in transcript)
    report = {'passed': passed, 'emulator_serial': args.serial, 'android_host_abi': abi, 'api': api,
              'guest_architecture': 'aarch64', 'elapsed_seconds': round(time.monotonic() - started, 2),
              'apks': hashes, 'checks': ['installed_executable_version', 'machine_start_quit',
                                       'forced_stop', 'actual_linux_shell_file_poweroff',
                                       'actual_qemu_private_unix_socket', 'protocol_split_utf8', 'protocol_timeout_close',
                                       'protocol_close_wakes_request'],
              'scope': 'Developer probe APK on emulator; not ARM phone or full course support'}
    (NATIVE / 'probe-validation.json').write_text(json.dumps(report, indent=2) + '\n')
    print(transcript, flush=True)
    print(json.dumps(report, indent=2), flush=True)
    return 0 if passed else 1


if __name__ == '__main__':
    raise SystemExit(main())
