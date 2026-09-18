"""Separate, offline ARM64 Conda guest builder. Never install on the host.

The existing validated Android Linux pack is an immutable backing image. This
developer's owned overlay and reports are distinct from the x86 Conda build.
Success here is not proof of execution on an Android phone or in the app UI.
"""
import argparse
import json
from pathlib import Path
import socket
import subprocess
import sys
import time

from build_guest import WORKSPACE, DESKTOP, RUNTIME, build_environment, guest_exec, sha256

sys.path.insert(0,str(DESKTOP))
from real_vm import GuestChannel
from vm_resources import lower_priority
from conda_teaching.installer_sources import installer_for
from conda_teaching.course_smoke import source_fingerprint, check_course
from conda_teaching.learning_smoke import check_learning

BUILD=WORKSPACE/'android/.native-runtime/conda-arm64'
PACK=WORKSPACE/'android/.native-runtime/ubuntu-arm64/android-pack-v1'
SPEC=installer_for('aarch64')


def installer(download=False):
    path=BUILD/SPEC['name']
    if download and not path.exists():
        partial=path.with_suffix('.sh.part')
        if partial.is_symlink():raise ValueError('Unexpected installer link')
        subprocess.run(['curl','--fail','--location','--show-error','--silent','--retry','3',
            '--connect-timeout','20','--max-time','900','--continue-at','-','--output',str(partial),SPEC['url']],check=True)
        if sha256(partial)!=SPEC['sha256']:raise ValueError('Official ARM installer checksum mismatch')
        partial.replace(path)
    if path.is_symlink() or not path.is_file() or sha256(path)!=SPEC['sha256']:
        raise ValueError('Missing or incorrect pinned ARM installer; use --download')
    return path


def prepare(download):
    BUILD.mkdir(parents=True,exist_ok=True)
    setup=installer(download)
    manifest=json.loads((PACK/'manifest.json').read_text())
    if manifest.get('guest_arch')!='aarch64':raise ValueError('ARM64 backing image required')
    for name in ('base.qcow2','kernel','initrd'):
        if sha256(PACK/name)!=manifest['files'][name]['sha256']:raise ValueError('Backing pack hash mismatch: '+name)
    image=BUILD/'provisioning.qcow2';marker=BUILD/'image-owner.json'
    ownership={'schema':1,'kind':'shellground-arm64-conda-builder','base':str(PACK/'base.qcow2'),
        'base_sha256':manifest['files']['base.qcow2']['sha256'],'installer_sha256':SPEC['sha256']}
    if image.exists():
        if image.is_symlink() or not marker.is_file() or json.loads(marker.read_text())!=ownership:
            raise ValueError('Preserve unrecognized existing Conda image')
    else:
        subprocess.run([str(RUNTIME/'usr/bin/qemu-img'),'create','-f','qcow2','-F','qcow2',
            '-b',str(PACK/'base.qcow2'),str(image)],env=build_environment(),check=True)
        marker.write_text(json.dumps(ownership,indent=2)+'\n')
    files={'miniconda.sh':setup,
        **{name:DESKTOP/'conda_teaching'/name for name in ('provision.py','channel.py','installer_sources.py','runtime_smoke.sh','logged_command.py','archive_smoke.py')},
        'conda_runtime.py':DESKTOP/'conda_teaching/guest_runtime.py',
        **{name:DESKTOP/'guest'/name for name in ('agent.py','conda_lab.py','shell_snapshot.py')}}
    iso=BUILD/'bootstrap.iso'
    subprocess.run([str(RUNTIME/'usr/bin/genisoimage'),'-quiet','-output',str(iso),'-volid','SGCONDA',
        '-joliet','-rock','-graft-points',*[name+'='+str(path) for name,path in files.items()]],check=True)
    return image,iso


def provision(channel):
    # The agent caps individual execs at120s. Run an owned systemd unit and
    # poll its actual result instead of weakening the learner command limit.
    script="python3 -u /mnt/sg-conda/provision.py > /opt/shellground/conda-provision.log 2>&1; rc=$?; printf '%s\\n' \"$rc\" > /opt/shellground/conda-provision-exit; exit \"$rc\""
    import shlex
    command=('mkdir -p /mnt/sg-conda; mountpoint -q /mnt/sg-conda || mount -o ro /dev/disk/by-label/SGCONDA /mnt/sg-conda; '
        'if systemctl is-active --quiet shellground-conda-provision.service; then echo running; '
        'else systemctl reset-failed shellground-conda-provision.service 2>/dev/null || true; '
        'rm -f /opt/shellground/conda-provision-exit; '
        'systemd-run --unit=shellground-conda-provision /bin/bash -c '+shlex.quote(script)+'; fi')
    guest_exec(channel,['bash','-euc',command],root=True)
    deadline=time.monotonic()+1800;last=None
    code='''
import json,sys
from pathlib import Path
sys.path.insert(0,'/mnt/sg-conda')
from logged_command import read_tail
p=Path('/opt/shellground/conda-provision-exit')
l=Path('/opt/shellground/conda-provision.log')
pointer=Path('/opt/shellground/conda-smoke-current.json')
tail=read_tail(l,2000) if l.is_file() else 'starting'
if pointer.is_file():
    output=Path(json.loads(pointer.read_text())['log'])
    if output.name!='output.log' or output.parent.parent!=Path('/opt/shellground') or not output.parent.name.startswith('conda-smoke-'):
        raise ValueError('Unrecognized smoke progress path')
    if output.resolve()!=output or output.parent.is_symlink():raise ValueError('Unexpected smoke progress link')
    if output.is_file():tail+='\\n'+read_tail(output,3000)
print(json.dumps({'exit':p.read_text().strip() if p.exists() else None,'tail':tail}))
'''
    while time.monotonic()<deadline:
        state=json.loads(guest_exec(channel,['python3','-c',code],root=True))
        if state['tail']!=last:print(state['tail'],flush=True);last=state['tail']
        if state['exit'] is not None:
            if state['exit']!='0':
                try:diagnose(channel)
                except Exception as error:print('Read-only failure diagnostic unavailable: '+str(error),flush=True)
                raise RuntimeError('ARM Conda provisioning failed; owned image and log retained')
            report=json.loads(guest_exec(channel,['cat','/opt/shellground/conda-build-report.json'],root=True))
            if report['subdir']!='linux-aarch64':raise ValueError('Wrong actual Conda architecture')
            (BUILD/'provision-validation.json').write_text(json.dumps(report,indent=2)+'\n')
            print('ARM_CONDA_PROVISION_PASS (developer host, NOT Android proof)',flush=True);return
        time.sleep(10)
    raise TimeoutError('Conda provisioning exceeded30minutes')


def diagnose(channel):
    """Read the owned failed build; do not delete/reinstall/repair environments."""
    script='''
import json,sys
from pathlib import Path
sys.path.insert(0,'/opt/shellground')
from agent import require_guest
require_guest()
def read(path,limit=12000):
    p=Path(path)
    if not p.is_file():return None
    with p.open('rb') as stream:
        stream.seek(0,2);stream.seek(max(0,stream.tell()-limit))
        return stream.read(limit).decode(errors='replace')
smoke={}
pointer=Path('/opt/shellground/conda-smoke-current.json')
if pointer.is_file():
    output=Path(json.loads(pointer.read_text())['log'])
    if output.name!='output.log' or output.parent.parent!=Path('/opt/shellground') or not output.parent.name.startswith('conda-smoke-'):
        raise ValueError('Unrecognized smoke log path')
    if output.resolve()!=output or output.parent.is_symlink():raise ValueError('Unexpected smoke log link')
    smoke={'log':str(output),'output_tail':read(output),'observation':read(str(output)+'.json',4000)}
environments={}
for name in ('sg-proof','sg-copy'):
    root=Path('/home/learner/conda-envs')/name
    packages=[]
    for path in sorted((root/'conda-meta').glob('*.json')):
        record=json.loads(path.read_text())
        packages.append({key:record.get(key) for key in ('name','version','subdir')})
    environments[name]={'exists':root.exists(),'packages':packages,'history_tail':read(root/'conda-meta/history',4000)}
print(json.dumps({'kind':'read-only-arm-conda-diagnostic-not-validation',
    'installed':Path('/opt/shellground/miniconda/conda-meta/history').is_file(),
    'provision_exit':read('/opt/shellground/conda-provision-exit',64),
    'provision_log':read('/opt/shellground/conda-provision.log'),
    'smoke':smoke,
    'exported_yaml':read('/home/learner/conda-proof/environment.yml',8192),
    'environments':environments}))
'''
    result=json.loads(guest_exec(channel,['/usr/bin/python3','-c',script],root=True,timeout=60))
    (BUILD/'diagnostic.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(result,ensure_ascii=False,indent=2),flush=True)


def archive_smoke_fixtures(channel):
    # An explicit opt-in, not something ordinary startup/provisioning does.
    journal=BUILD/'smoke-archives.json'
    if journal.is_symlink():raise ValueError('Unexpected smoke archive journal link')
    previous=json.loads(journal.read_text()) if journal.is_file() else []
    if not isinstance(previous,list):raise ValueError('Unexpected smoke archive journal')
    mount='mkdir -p /mnt/sg-conda; mountpoint -q /mnt/sg-conda || mount -o ro /dev/disk/by-label/SGCONDA /mnt/sg-conda'
    guest_exec(channel,['bash','-euc',mount],root=True)
    result=json.loads(guest_exec(channel,['/usr/bin/python3','/mnt/sg-conda/archive_smoke.py'],root=True,timeout=60))
    previous.append(result);journal.write_text(json.dumps(previous,indent=2)+'\n')
    print('Prior smoke fixtures preserved: '+result['destination'],flush=True)


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--download',action='store_true')
    parser.add_argument('--build',action='store_true')
    parser.add_argument('--course-test',action='store_true')
    parser.add_argument('--learning-test',action='store_true')
    parser.add_argument('--diagnose',action='store_true',help='Read failed build logs and the two smoke environments, without repair')
    parser.add_argument('--archive-smoke-fixtures',action='store_true',help='Explicitly preserve the two proven failed-test environments before retrying; never delete them')
    parser.add_argument('--units',nargs='+')
    args=parser.parse_args();BUILD.mkdir(parents=True,exist_ok=True)
    if not (args.build or args.course_test or args.learning_test or args.diagnose or args.archive_smoke_fixtures):
        installer(args.download);print('Verified official ARM installer only; no VM started');return
    image,iso=prepare(args.download);fingerprint=source_fingerprint()
    listener=socket.socket();listener.bind(('127.0.0.1',0));listener.listen(1);listener.settimeout(1)
    qemu=WORKSPACE/'android/.native-runtime/ubuntu-arm64/host-qemu/usr/bin/qemu-system-aarch64'
    args_vm=[str(qemu),'-name','shellground-arm64-conda-builder','-machine','virt','-cpu','cortex-a72',
        '-accel','tcg,thread=multi,tb-size=64','-smp','2','-m','2048','-display','none','-monitor','none','-nic','none','-no-reboot',
        '-kernel',str(PACK/'kernel'),'-initrd',str(PACK/'initrd'),'-append','root=LABEL=cloudimg-rootfs rw console=ttyAMA0',
        '-serial','file:'+str(BUILD/'console.log'),'-drive',f'file={image},format=qcow2,if=virtio',
        '-drive',f'file={iso},format=raw,if=virtio,readonly=on','-device','virtio-serial-pci',
        '-chardev',f'socket,id=sg,host=127.0.0.1,port={listener.getsockname()[1]},reconnect=1',
        '-device','virtserialport,chardev=sg,name=org.shellground.agent']
    channel=None
    with (BUILD/'qemu.log').open('wb') as log:
        process=subprocess.Popen(args_vm,env=build_environment(),stdout=log,stderr=subprocess.STDOUT);lower_priority(process)
        try:
            print(f'Owned ARM Conda guest PID{process.pid}:2vCPU/2GiB/offline',flush=True)
            deadline=time.monotonic()+360
            while time.monotonic()<deadline:
                if process.poll() is not None:raise RuntimeError('ARM Conda QEMU exited; see qemu.log')
                try:connection,_=listener.accept();connection.settimeout(None);channel=GuestChannel(connection);break
                except socket.timeout:pass
            if channel is None:raise TimeoutError('ARM Conda control connection')
            status=channel.request('status',timeout=360)
            if status.get('guest')!='shellground' or not status.get('provisioned'):raise RuntimeError(status)
            if guest_exec(channel,['uname','-m']).strip()!='aarch64':raise ValueError('ARM64 guest required')
            if args.archive_smoke_fixtures:archive_smoke_fixtures(channel)
            if args.build:provision(channel)
            if args.diagnose:diagnose(channel)
            if args.course_test:check_course(channel,args.units,BUILD/'course-validation.json')
            if args.learning_test:check_learning(channel,args.units,BUILD/'learning-validation.json')
            if fingerprint!=source_fingerprint():raise RuntimeError('Conda sources changed during verification')
        finally:
            listener.close()
            if channel:
                try:channel.request('exec',timeout=8,root=True,argv=['systemctl','poweroff'])
                except Exception:pass
                channel.close()
            try:process.wait(timeout=30)
            except subprocess.TimeoutExpired:
                process.terminate()
                try:process.wait(timeout=5)
                except subprocess.TimeoutExpired:process.kill();process.wait(timeout=5)
            print('Owned ARM Conda builder stopped: '+str(process.returncode),flush=True)


if __name__=='__main__':main()
