"""Build the real ARM64 training guest on a Linux developer machine.

No host apt install, root, Docker socket or shared home. The original x86 VM
and learner APK are never changed. Runtime Android tests are a separate gate.
"""
import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import platform
import socket
import subprocess
import sys
import time

WORKSPACE = Path(__file__).resolve().parents[2]
DESKTOP = WORKSPACE / 'desktop'
BUILD = WORKSPACE / 'android/.native-runtime/ubuntu-arm64'
RUNTIME = DESKTOP / '.vm-runtime/linux-x86_64'
SOURCES = json.loads(Path(__file__).with_name('guest-sources.json').read_text())
sys.path.insert(0, str(DESKTOP))
from build_vm_image import build_seed
from real_vm import GuestChannel
from vm_resources import lower_priority


def sha256(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def source_path(key):
    return BUILD / 'downloads' / SOURCES['files'][key]['name']


def verify_sources():
    for key, spec in SOURCES['files'].items():
        path = source_path(key)
        if path.is_symlink() or not path.is_file() or sha256(path) != spec['sha256']:
            raise ValueError('Missing or incorrect pinned source: ' + str(path))


def download():
    (BUILD / 'downloads').mkdir(parents=True, exist_ok=True)
    for key, spec in SOURCES['files'].items():
        path = source_path(key)
        if path.exists():
            if path.is_symlink() or sha256(path) != spec['sha256']:
                raise ValueError('Existing source differs; preserve and inspect: ' + str(path))
            continue
        partial = path.with_name(path.name + '.part')
        if partial.is_symlink():
            raise ValueError('Download path must not be a symlink')
        print('Downloading official source: ' + spec['name'], flush=True)
        subprocess.run(['curl', '--fail', '--location', '--show-error', '--silent',
                        '--retry', '3', '--connect-timeout', '20', '--max-time', '1800',
                        '--continue-at', '-', '--output', str(partial), spec['url']], check=True)
        if sha256(partial) != spec['sha256']:
            raise ValueError('Downloaded checksum mismatch: ' + spec['name'])
        partial.replace(path)
        print('Verified SHA256: ' + spec['name'], flush=True)


def build_environment():
    return dict(os.environ, LD_LIBRARY_PATH=str(RUNTIME / 'usr/lib/x86_64-linux-gnu'),
                QEMU_MODULE_DIR=str(RUNTIME / 'usr/lib/x86_64-linux-gnu/qemu'))


def prepare():
    if platform.system() != 'Linux' or platform.machine() != 'x86_64':
        raise RuntimeError('This developer builder currently requires Linux x86_64')
    BUILD.mkdir(parents=True, exist_ok=True)
    verify_sources()
    host = BUILD / 'host-qemu'
    if host.is_symlink():
        raise ValueError('Unexpected host QEMU directory')
    subprocess.run(['dpkg-deb', '-x', str(source_path('host_qemu')), str(host)], check=True)
    subprocess.run([str(host / 'usr/bin/qemu-system-aarch64'), '--version'],
                   env=build_environment(), check=True)
    image = BUILD / 'provisioning.qcow2'
    marker = BUILD / 'image-owner.json'
    ownership = {'schema': 1, 'kind': 'shellground-arm64-training-builder',
                 'workspace': str(WORKSPACE), 'source': SOURCES['files']['image']['sha256']}
    if image.exists():
        if image.is_symlink() or not marker.is_file() or json.loads(marker.read_text()) != ownership:
            raise ValueError('Unrecognized build image; refusing to modify it')
    else:
        subprocess.run([str(RUNTIME / 'usr/bin/qemu-img'), 'create', '-f', 'qcow2', '-F', 'qcow2',
                        '-b', str(source_path('image')), str(image), '16G'], env=build_environment(), check=True)
        marker.write_text(json.dumps(ownership, indent=2) + '\n')
    seed = build_seed(BUILD, RUNTIME, auto_provision=False)
    return image, seed, host / 'usr/bin/qemu-system-aarch64'


def command_for(image, seed, qemu, port, online):
    command = [str(qemu), '-name', 'shellground-arm64-training-builder',
               '-machine', 'virt', '-cpu', 'cortex-a72', '-accel', 'tcg,thread=multi,tb-size=64',
               '-smp', '2', '-m', '2048', '-display', 'none', '-monitor', 'none', '-no-reboot',
               '-kernel', str(source_path('kernel')), '-initrd', str(source_path('initrd')),
               '-append', 'root=LABEL=cloudimg-rootfs rw console=ttyAMA0',
               '-serial', 'file:' + str(BUILD / 'console.log'),
               '-drive', f'file={image},format=qcow2,if=virtio',
               '-drive', f'file={seed},format=raw,if=virtio,readonly=on',
               '-device', 'virtio-serial-pci',
               '-chardev', f'socket,id=sg,host=127.0.0.1,port={port},reconnect=1',
               '-device', 'virtserialport,chardev=sg,name=org.shellground.agent']
    command += (['-netdev', 'user,id=net0', '-device',
                 'virtio-net-pci,netdev=net0,romfile=,mac=52:54:00:12:34:56'] if online else ['-nic', 'none'])
    return command


def guest_exec(channel, argv, *, root=False, timeout=30):
    reply = channel.request('exec', timeout=timeout + 5, run_timeout=timeout, root=root, argv=argv)
    out, err = (base64.b64decode(reply[k]).decode(errors='replace') for k in ('out', 'err'))
    if reply['code']:
        raise RuntimeError(f'Guest command failed ({reply["code"]}): {argv!r}\n{out}\n{err}')
    return out


def ros_command(script):
    # ROS-generated setup scripts read optional environment variables. `-u`
    # would reject a normal clean learner shell before ROS itself can run.
    # Keep `-e`: failed setup or a failed ROS command must still fail the probe.
    return ['bash', '-ec', 'source /opt/ros/humble/setup.bash; ' + script]


def provision(channel):
    if channel.request('status')['provisioned']:
        print('Guest already provisioned; validating actual tools', flush=True)
        return
    # Stop no unrelated job. Reuse this VM's running provisioning unit if present.
    started = guest_exec(channel, ['bash', '-c',
        'if systemctl is-active --quiet shellground-provision.service; then echo running; '
        'else systemctl reset-failed shellground-provision.service 2>/dev/null || true; '
        'rm -f /opt/shellground/provision-exit; '
        'systemd-run --unit=shellground-provision /bin/bash -c '
        "'bash /opt/shellground/provision.sh > /opt/shellground/provision.log 2>&1; "
        "rc=$?; printf \"%s\\n\" \"$rc\" > /opt/shellground/provision-exit; exit \"$rc\"'; fi"], root=True)
    print(started.strip(), flush=True)
    deadline = time.monotonic() + 2700
    previous_tail = None
    while time.monotonic() < deadline:
        result = json.loads(guest_exec(channel, ['python3', '-c',
            'import json,pathlib; p=pathlib.Path("/opt/shellground/provision-exit"); '
            'l=pathlib.Path("/opt/shellground/provision.log"); '
            'print(json.dumps({"exit":p.read_text().strip() if p.exists() else None,'
            '"tail":l.read_text(errors="replace")[-1500:] if l.exists() else "starting"}))'], root=True))
        if result['tail'] != previous_tail:
            print(result['tail'], flush=True)
            previous_tail = result['tail']
        if result['exit'] is not None:
            if result['exit'] != '0':
                raise RuntimeError('Guest provisioning failed; retained image/log for repair')
            return
        time.sleep(20)
    raise TimeoutError('Provisioning exceeded 45 minutes; image retained')


def smoke(channel):
    status = channel.request('status')
    if not all(status.get(key) for key in ('provisioned', 'nano', 'docker', 'ros')):
        raise RuntimeError('Full guest not ready: ' + repr(status))
    results = {'status': status}
    results['platform'] = guest_exec(channel, ['bash', '-euc',
        'test "$(uname -m)" = aarch64; uname -a; dpkg --print-architecture; '
        'bash --version | head -1; nano --version | head -1'])
    results['docker'] = guest_exec(channel, ['docker', 'run', '--rm', '--network=none',
        'localhost:5000/training/alpine:latest', 'sh', '-c', 'test "$(uname -m)" = aarch64; printf SG_REAL_ARM_DOCKER'])
    results['ros'] = guest_exec(channel, ros_command(
        'ros2 pkg prefix demo_nodes_cpp; ros2 pkg prefix turtlesim'), timeout=60)
    from guest_smoke import check_pty
    results['pty'] = check_pty(channel)
    report = {'schema': 1, 'passed': True, 'execution': 'Linux developer host TCG / ARM64 guest, NOT Android runtime',
              'sources': SOURCES, 'results': results}
    (BUILD / 'validation.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(report['results'], ensure_ascii=False, indent=2), flush=True)
    print('ARM64_TRAINING_GUEST_PASS (not Android device validation)', flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--download', action='store_true')
    parser.add_argument('--build', action='store_true', help='Boot and install inside the isolated guest (network enabled)')
    parser.add_argument('--probe', action='store_true', help='Validate existing guest, with no external network')
    args = parser.parse_args()
    if args.build and args.probe:
        parser.error('Choose --build or --probe')
    if args.download:
        download()
    if not (args.build or args.probe):
        return
    image, seed, qemu = prepare()
    listener = socket.socket(); listener.bind(('127.0.0.1', 0)); listener.listen(1); listener.settimeout(1)
    command = command_for(image, seed, qemu, listener.getsockname()[1], args.build)
    channel = None
    with (BUILD / 'qemu.log').open('wb') as log:
        process = subprocess.Popen(command, env=build_environment(), stdout=log, stderr=subprocess.STDOUT)
        lower_priority(process)
        print(f'Owned ARM64 builder PID {process.pid}: 2 vCPUs / 2GiB, no host mounts', flush=True)
        try:
            deadline = time.monotonic() + 360
            while time.monotonic() < deadline:
                if process.poll() is not None:
                    raise RuntimeError('QEMU exited; see ' + str(BUILD / 'qemu.log'))
                try:
                    connection, _ = listener.accept(); connection.settimeout(None)
                    channel = GuestChannel(connection); break
                except socket.timeout:
                    pass
            if channel is None:
                raise TimeoutError('Guest control connection')
            status = channel.request('status', timeout=360)
            if status.get('guest') != 'shellground':
                raise RuntimeError('Unexpected guest identity')
            print('Real guest agent connected', flush=True)
            if args.build:
                provision(channel)
            smoke(channel)
        finally:
            listener.close()
            if channel:
                try:
                    channel.request('exec', timeout=8, root=True, argv=['systemctl', 'poweroff'])
                except Exception:
                    pass
                channel.close()
            try:
                process.wait(timeout=30)
            except subprocess.TimeoutExpired:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill(); process.wait(timeout=5)
            print('Owned ARM64 builder stopped: ' + str(process.returncode), flush=True)


if __name__ == '__main__':
    main()
