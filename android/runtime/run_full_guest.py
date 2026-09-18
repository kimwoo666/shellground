"""Deploy/run the full real guest in a separate developer Android app.

ADB is development verification only, not a proposed user setup requirement.
No learner app data is cleared; no physical phone is selected implicitly.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import time
import uuid
import zipfile

WORKSPACE = Path(__file__).resolve().parents[2]
ANDROID = WORKSPACE / 'android'
NATIVE = ANDROID / '.native-runtime'
PACKAGE = 'org.shellground.runtimeprobe'


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--serial', required=True)
    parser.add_argument('--learner-app', action='store_true', help='Verify the actual learner app service, not the probe')
    parser.add_argument('--bundled-pack', action='store_true', help='Verify first-run installation from APK assets')
    parser.add_argument('--pack', type=Path, default=NATIVE / 'ubuntu-arm64/android-pack-v1')
    args = parser.parse_args()
    package = 'org.shellground.learn' if args.learner_app else PACKAGE
    if args.bundled_pack and not args.learner_app:
        raise ValueError('Bundled image installation belongs to the learner APK')
    if not args.serial.startswith('emulator-'):
        raise ValueError('Use an explicitly selected developer emulator')
    manifest = json.loads((args.pack / 'manifest.json').read_text())
    for name, spec in manifest['files'].items():
        if name not in ('base.qcow2', 'kernel', 'initrd'):
            raise ValueError('Unexpected pack file')
        if digest(args.pack / name) != spec['sha256']:
            raise ValueError('Developer pack checksum mismatch: ' + name)
    adb = [str(WORKSPACE / 'desktop/.android-tools/sdk/platform-tools/adb'), '-s', args.serial]
    def run(*parts, timeout=60, **options):
        return subprocess.run(adb + list(parts), timeout=timeout, check=True, **options)
    def text(*parts):
        return run(*parts, capture_output=True, text=True).stdout.strip()
    until = time.monotonic() + 120
    while text('shell', 'getprop', 'sys.boot_completed') != '1':
        if time.monotonic() > until:
            raise TimeoutError('Developer emulator boot')
        time.sleep(2)
    module = 'app' if args.learner_app else 'runtime-probe'
    apks = [ANDROID / f'{module}/build/outputs/apk/debug/{module}-debug.apk',
            ANDROID / f'{module}/build/outputs/apk/androidTest/debug/{module}-debug-androidTest.apk']
    if args.bundled_pack:
        with zipfile.ZipFile(apks[0]) as archive:
            packaged = json.loads(archive.read('assets/training-pack/manifest.json'))
            if packaged != manifest: raise ValueError('Bundled pack differs from validated developer source')
            packaging = json.loads(archive.read('assets/training-pack/packaging.json'))
            if not packaging.get('base_parts'): raise ValueError('Bundled image parts are absent')
    for apk in apks:
        run('install', '-r', str(apk))
    remote = subprocess.run(adb + ['shell', 'run-as', package, 'cat', 'files/training-pack/manifest.json'],
                            capture_output=True, text=True, timeout=20)
    if args.bundled_pack:
        if remote.returncode == 0:
            if json.loads(remote.stdout) != manifest: raise ValueError('Preserve different existing developer pack')
            backup='files/training-pack-before-bundle-'+uuid.uuid4().hex
            run('shell','run-as',package,'mv','files/training-pack',backup)
            print('Preserved previous developer pack at '+backup,flush=True)
        print('No ADB image staging: app must install its own bundled assets',flush=True)
    elif remote.returncode == 0:
        if json.loads(remote.stdout) != manifest:
            raise ValueError('Different private developer pack exists; preserve it for inspection')
        print('Reusing matching app-private pack; Android rechecks all file hashes', flush=True)
    else:
        staging = '/data/local/tmp/sg-full-' + uuid.uuid4().hex
        names = ['base.qcow2', 'kernel', 'initrd', 'manifest.json']
        run('shell', 'mkdir', staging)
        run('shell', 'run-as', package, 'mkdir', '-p', 'files/training-pack')
        try:
            for name in names:
                print('Staging developer guest: ' + name, flush=True)
                run('push', str(args.pack / name), staging + '/' + name, timeout=180)
                run('shell', 'run-as', package, 'cp', staging + '/' + name,
                    'files/training-pack/' + name, timeout=180)
        finally:
            # Exact files in this generated staging directory only; never app data.
            for name in names:
                run('shell', 'rm', '-f', staging + '/' + name)
            run('shell', 'rmdir', staging)
    started = time.monotonic()
    print('Starting real Android guest acceptance: ' + package, flush=True)
    prefix = 'learner-bundled' if args.bundled_pack else ('learner-service' if args.learner_app else 'full-guest')
    test = (package + '.LinuxRuntimeTest#testLearnerServiceRealNanoGradeMultipleTerminalsAndStop'
            if args.learner_app else package + '.FullGuestTest')
    marker = 'ANDROID_LEARNER_REAL_SERVICE_OK' if args.learner_app else 'ANDROID_FULL_GUEST_NANO_GRADE_DOCKER_ROS_OK'
    try:
        result = run('shell', 'am', 'instrument', '-w', '-e', 'class',
            test, '-e', 'fullGuest', 'true',
            package + '.test/androidx.test.runner.AndroidJUnitRunner',
            timeout=900, capture_output=True, text=True)
        transcript = result.stdout + result.stderr
        (NATIVE / (prefix + '-instrumentation.log')).write_text(transcript)
        passed = ('OK (1 test)' in transcript and 'FAILURES!!!' not in transcript
                  and marker in transcript)
        report = {'passed': passed, 'serial': args.serial,
            'bundled_image_installation':args.bundled_pack,
            'android_host_abi': text('shell', 'getprop', 'ro.product.cpu.abi'),
            'api': text('shell', 'getprop', 'ro.build.version.sdk'),
            'elapsed_seconds': round(time.monotonic()-started, 2),
            'pack_files': manifest['files'], 'apks': {path.name: digest(path) for path in apks},
            'scope': ('Developer Android learner app; actual nano/grade/multiple PTYs/stop; not ARM phone or full curriculum' if args.learner_app else
                      'Developer Android emulator; actual guest with real nano/grade/Docker/ROS; not ARM phone or full curriculum validation')}
        (NATIVE / (prefix + '-validation.json')).write_text(json.dumps(report, indent=2) + '\n')
        print(transcript, flush=True)
        print(json.dumps(report, indent=2), flush=True)
        return 0 if passed else 1
    finally:
        run('shell', 'am', 'force-stop', package)


if __name__ == '__main__':
    raise SystemExit(main())
