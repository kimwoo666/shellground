"""Developer-only image builder. No package installation on the host.

Official cloud image and extracted QEMU packages must already be downloaded.
The shipped application uses the resulting provisioned image without cloud-init.
"""
import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import subprocess

from vm_resources import accelerator_args, lower_priority, vcpu_count

ROOT = Path(__file__).resolve().parent
BASE_SHA256 = '1fe8d46c9c31a89d92400d75d73e188404e3bbf282d0540189c8f4fb3c42fbc6'


def build_seed(build, runtime, *, auto_provision=True):
    def entry(path, content, permissions='0644'):
        return {'path': path, 'encoding': 'b64', 'content': base64.b64encode(content).decode(), 'permissions': permissions}
    files = [entry('/opt/shellground/guest-owned', b'shellground-disposable-guest-v1\n'),
             entry('/opt/shellground/agent.py', (ROOT / 'guest/agent.py').read_bytes()),
             entry('/opt/shellground/lab.py', (ROOT / 'lab/lab.py').read_bytes()),
             entry('/opt/shellground/provision.sh', (ROOT / 'guest/provision.sh').read_bytes(), '0755')]
    for name in ('ros_lab.py', 'ros_observer.py', 'ros_fixture.py', 'bashrc', 'shell_snapshot.py', 'screen.py', 'extension_lab.py', 'offline_repositories.py', 'admin_lab.py', 'docker_lab.py', 'docker_reports.py'):
        files.append(entry('/opt/shellground/' + name, (ROOT / 'guest' / name).read_bytes()))
    files.append(entry('/opt/shellground/admin_lessons.py', (ROOT / 'admin_lessons.py').read_bytes()))
    services = {
        'agent': (ROOT / 'guest/shellground-agent.service').read_text(),
        'files': '[Unit]\nAfter=network.target\n[Service]\nExecStart=/usr/bin/python3 -u /opt/shellground/lab.py serve\nRestart=always\n[Install]\nWantedBy=multi-user.target\n',
        'display': '[Unit]\nDescription=Training virtual display\n[Service]\nExecStart=/usr/bin/Xvfb :0 -screen 0 800x600x24 -nolisten tcp\nRestart=always\n[Install]\nWantedBy=multi-user.target\n',
    }
    for name, service in services.items():
        files.append(entry('/etc/systemd/system/shellground-' + name + '.service', service.encode()))
    config = {'hostname': 'lab', 'users': [{'name': 'learner', 'uid': 1100, 'groups': ['sudo'],
              'shell': '/bin/bash', 'sudo': 'ALL=(ALL) NOPASSWD:ALL', 'lock_passwd': True}],
              'write_files': files, 'runcmd': [['systemctl', 'daemon-reload'],
              ['systemctl', 'enable', '--now', 'shellground-agent'],
              ['bash', '/opt/shellground/provision.sh']]}
    if not auto_provision:
        config['runcmd'] = config['runcmd'][:2]
    # JSON is a YAML subset and avoids an extra build dependency.
    (build / 'user-data').write_text('#cloud-config\n' + json.dumps(config))
    (build / 'meta-data').write_text('instance-id: shellground-build-v1\nlocal-hostname: lab\n')
    (build / 'network-config').write_text(json.dumps({'version': 2, 'ethernets': {
        'training': {'match': {'macaddress': '52:54:00:12:34:56'}, 'set-name': 'eth0',
                     'dhcp4': True, 'optional': True}}}))
    seed = build / 'seed.iso'
    subprocess.run([str(runtime / 'usr/bin/genisoimage'), '-quiet', '-output', str(seed), '-volid', 'cidata',
                    '-joliet', '-rock', 'user-data', 'meta-data', 'network-config'], cwd=build, check=True)
    return seed


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=19473)
    parser.add_argument('--offline', action='store_true', help='No virtual network; use for code-only image updates after provisioning.')
    parser.add_argument('--allow-software', action='store_true',
                        help='Explicitly allow slower, higher-load multi-thread CPU emulation (developer only).')
    args = parser.parse_args()
    acceleration = accelerator_args(args.allow_software)
    build = ROOT / '.vm-build'
    runtime = ROOT / '.vm-runtime/linux-x86_64'
    base = build / 'ubuntu-22.04-minimal-cloudimg-amd64.img'
    if hashlib.file_digest(base.open('rb'), 'sha256').hexdigest() != BASE_SHA256:
        raise RuntimeError('Official cloud image checksum mismatch')
    env = dict(os.environ, LD_LIBRARY_PATH=str(runtime / 'usr/lib/x86_64-linux-gnu'),
               QEMU_MODULE_DIR=str(runtime / 'usr/lib/x86_64-linux-gnu/qemu'))
    target = build / 'provisioning.qcow2'
    if not target.exists():
        subprocess.run([str(runtime / 'usr/bin/qemu-img'), 'create', '-f', 'qcow2', '-F', 'qcow2',
                        '-b', str(base), str(target), '16G'], env=env, check=True)
    seed = build_seed(build, runtime)
    command = [str(runtime / 'usr/bin/qemu-system-x86_64'), '-name', 'shellground-image-builder',
        '-machine', 'q35', *acceleration, '-smp', str(vcpu_count()), '-m', '2048',
        '-L', str(runtime / 'usr/share/qemu'), '-bios', str(runtime / 'usr/share/seabios/bios-256k.bin'),
        '-display', 'none', '-vga', 'none', '-monitor', 'none', '-serial', 'file:' + str(build / 'console.log'),
        '-drive', f'file={target},format=qcow2,if=virtio', '-drive', f'file={seed},format=raw,if=virtio,readonly=on',
        '-device', 'virtio-serial-pci', '-chardev', f'socket,id=sg,host=127.0.0.1,port={args.port},server=on,wait=off',
        '-device', 'virtserialport,chardev=sg,name=org.shellground.agent', '-no-reboot']
    command += ['-nic', 'none'] if args.offline else ['-netdev', 'user,id=net0', '-device', 'virtio-net-pci,netdev=net0,romfile=,mac=52:54:00:12:34:56']
    print(f'Starting isolated image builder: {acceleration[1]}, {vcpu_count()} vCPUs; only the guest installs packages.', flush=True)
    process = subprocess.Popen(command, env=env)
    lower_priority(process)
    try:
        return process.wait()
    except KeyboardInterrupt:
        process.terminate()
        try:
            return process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            return process.wait()


if __name__ == '__main__':
    raise SystemExit(main())
