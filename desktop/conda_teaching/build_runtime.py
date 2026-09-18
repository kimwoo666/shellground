"""Developer-only, offline Conda image builder; never installs on the host.

Creates its own persistent overlay of the existing immutable Linux image.
The only host data exposed to the guest is a read-only ISO containing the
hash-verified official installer and this project's provisioning code.
"""
import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import socket
import subprocess
import time

from real_vm import GuestChannel, runtime_info
from vm_resources import accelerator_args, lower_priority

ROOT=Path(__file__).resolve().parents[1]
NAME='Miniconda3-py312_26.7.1-1-Linux-x86_64.sh'
SHA256='b27f60ab63e77eeab50a5417c989120f767e863df32400190d4c7262369f8695'


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--probe-only',action='store_true',help='Boot existing Conda build and print its runtime metadata')
    parser.add_argument('--course-test',action='store_true',help='Verify actual course fixtures and solutions in the owned guest')
    parser.add_argument('--learning-test',action='store_true',help='Replay authored learning microsteps in persistent guest Bash')
    parser.add_argument('--setup-test',action='store_true',help='Provision installer assets then verify actual new installation and negative repairs')
    parser.add_argument('--setup-test-only',action='store_true',help='Test installation against existing verified setup assets without repeating image provisioning')
    parser.add_argument('--setup-inspect',action='store_true',help='Inspect the retained setup attempt without reinstalling or deleting it')
    parser.add_argument('--setup-ui-test',action='store_true',help='Verify native installation UI against the existing developer guest')
    parser.add_argument('--units',nargs='+',help='Optional course-test unit keys')
    args=parser.parse_args()
    build=ROOT/'.conda-build';build.mkdir(exist_ok=True)
    installer=build/NAME
    if hashlib.file_digest(installer.open('rb'),'sha256').hexdigest()!=SHA256:
        raise RuntimeError('Official Miniconda installer checksum mismatch')
    runtime,spec=runtime_info(ROOT/'.vm-runtime/linux-x86_64')
    base=(runtime/spec['image']).resolve();image=build/'provisioning.qcow2'
    marker=build/'image-owner.json'
    ownership={'schema':1,'kind':'shellground-conda-builder','base':str(base),'installer_sha256':SHA256}
    env=dict(os.environ,LD_LIBRARY_PATH=str(runtime/'usr/lib/x86_64-linux-gnu'),QEMU_MODULE_DIR=str(runtime/'usr/lib/x86_64-linux-gnu/qemu'))
    if image.exists():
        if not marker.is_file() or json.loads(marker.read_text())!=ownership or image.is_symlink():
            raise RuntimeError('Refusing to reuse an unrecognized build image')
    else:
        subprocess.run([str(runtime/spec['qemu_img']),'create','-f','qcow2','-F','qcow2','-b',str(base),str(image)],env=env,check=True)
        marker.write_text(json.dumps(ownership,indent=2)+'\n')
    iso=build/'bootstrap.iso'
    subprocess.run([str(runtime/'usr/bin/genisoimage'),'-quiet','-output',str(iso),'-volid','SGCONDA','-joliet','-rock','-graft-points',
                    'miniconda.sh='+str(installer),'provision.py='+str(ROOT/'conda_teaching/provision.py'),
                    'channel.py='+str(ROOT/'conda_teaching/channel.py'),
                    'logged_command.py='+str(ROOT/'conda_teaching/logged_command.py'),
                    'installer_sources.py='+str(ROOT/'conda_teaching/installer_sources.py'),
                    'diagnose.py='+str(ROOT/'conda_teaching/diagnose.py'),
                    'conda_runtime.py='+str(ROOT/'conda_teaching/guest_runtime.py'),
                    'conda_setup.py='+str(ROOT/'conda_teaching/setup_runtime.py'),
                    'conda_lab.py='+str(ROOT/'guest/conda_lab.py'),
                    'agent.py='+str(ROOT/'guest/agent.py'),
                    'shell_snapshot.py='+str(ROOT/'guest/shell_snapshot.py'),
                    'runtime_smoke.sh='+str(ROOT/'conda_teaching/runtime_smoke.sh')],check=True)
    listener=socket.socket();listener.bind(('127.0.0.1',0));listener.listen(1);listener.settimeout(1)
    port=listener.getsockname()[1]
    command=[str(runtime/spec['qemu']),'-name','shellground-conda-builder','-machine','q35',*accelerator_args(),
             '-smp','2','-m','2048','-display','none','-vga','none','-monitor','none','-nic','none','-no-reboot',
             '-L',str(runtime/'usr/share/qemu'),'-bios',str(runtime/'usr/share/seabios/bios-256k.bin'),
             '-serial','file:'+str(build/'console.log'),'-drive',f'file={image},format=qcow2,if=virtio',
             '-drive',f'file={iso},format=raw,if=virtio,readonly=on','-device','virtio-serial-pci',
             '-chardev',f'socket,id=sg,host=127.0.0.1,port={port},reconnect=1',
             '-device','virtserialport,chardev=sg,name=org.shellground.agent']
    channel=None
    with (build/'qemu.log').open('wb') as log:
        process=subprocess.Popen(command,env=env,stdout=log,stderr=subprocess.STDOUT);lower_priority(process)
        try:
            deadline=time.monotonic()+90
            while time.monotonic()<deadline:
                if process.poll() is not None:raise RuntimeError('Builder QEMU exited; see .conda-build/qemu.log')
                try:connection,_=listener.accept();connection.settimeout(None);channel=GuestChannel(connection);break
                except socket.timeout:pass
            if channel is None:raise TimeoutError('Guest control connection')
            status=channel.request('status',timeout=30)
            if status.get('guest')!='shellground' or not status.get('provisioned'):raise RuntimeError(status)
            print('Verified private guest; 2 vCPUs, 2GiB, no network or host mounts',flush=True)
            if args.setup_ui_test:
                from conda_teaching.setup_ui_smoke import check_setup_ui
                check_setup_ui(channel)
                return
            if args.setup_inspect:
                from conda_teaching.setup_smoke import inspect_setup
                inspect_setup(channel)
                return
            if args.setup_test_only:
                from conda_teaching.setup_smoke import check_setup
                check_setup(channel)
                return
            if args.course_test or args.learning_test:
                if args.course_test:
                    from conda_teaching.course_smoke import check_course
                    check_course(channel,args.units)
                if args.learning_test:
                    from conda_teaching.learning_smoke import check_learning
                    check_learning(channel,args.units)
                return
            if args.probe_only:
                argv=['bash','-euc','mkdir -p /mnt/sg-conda; mountpoint -q /mnt/sg-conda || mount -o ro /dev/disk/by-label/SGCONDA /mnt/sg-conda; '
                      'runuser -u learner -- env CONDARC=/opt/shellground/condarc CONDA_NO_PLUGINS=true '
                      '/opt/shellground/miniconda/bin/python /mnt/sg-conda/diagnose.py']
            else:
                argv=['bash','-euc','mkdir -p /mnt/sg-conda; mountpoint -q /mnt/sg-conda || mount -o ro /dev/disk/by-label/SGCONDA /mnt/sg-conda; python3 -u /mnt/sg-conda/provision.py']
            result=channel.request('exec',timeout=125,run_timeout=120,root=True,cwd='/tmp',argv=argv)
            text=base64.b64decode(result['out']).decode(errors='replace');error=base64.b64decode(result['err']).decode(errors='replace')
            print(text,flush=True)
            (build/'last-provision.log').write_text(text+'\n'+error)
            if result['code']:raise RuntimeError(error)
            print('Conda guest preparation succeeded; original runtime pack was not changed',flush=True)
            if args.setup_test:
                from conda_teaching.setup_smoke import check_setup
                check_setup(channel)
        finally:
            listener.close()
            if channel:
                try:channel.request('exec',timeout=8,root=True,argv=['systemctl','poweroff'])
                except Exception:pass
                channel.close()
            try:process.wait(timeout=15)
            except subprocess.TimeoutExpired:
                process.terminate()
                try:process.wait(timeout=5)
                except subprocess.TimeoutExpired:process.kill();process.wait(timeout=5)


if __name__=='__main__':main()
