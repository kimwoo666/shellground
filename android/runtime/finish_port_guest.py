"""Resume the owned ARM Conda image, finish assets, export ONE final pack."""
import argparse
import json
from pathlib import Path
import socket
import subprocess
import sys
import time
from build_guest import WORKSPACE, DESKTOP, RUNTIME, build_environment, guest_exec, sha256
from build_conda_guest import BUILD, PACK
sys.path.insert(0,str(DESKTOP))
from real_vm import GuestChannel
from vm_resources import lower_priority


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--assemble',action='store_true');parser.add_argument('--export',action='store_true')
    args=parser.parse_args()
    image=BUILD/'provisioning.qcow2'
    owner=json.loads((BUILD/'image-owner.json').read_text())
    if owner.get('kind')!='shellground-arm64-conda-builder' or owner.get('base')!=str(PACK/'base.qcow2'):
        raise ValueError('Refuse an unrecognized working image')
    assets=WORKSPACE/'android/app/build/generated/portAssets'
    iso=BUILD/'port-assets.iso'
    if args.assemble:
        entries={name:assets/name for name in ('real-guest','conda-guest','notebook-guest','port-source-manifest.json')}
        entries['wheels']=WORKSPACE/'android/.native-runtime/port-assets/wheels'
        entries['guest_port_setup.py']=Path(__file__).with_name('guest_port_setup.py')
        subprocess.run([str(RUNTIME/'usr/bin/genisoimage'),'-quiet','-output',str(iso),'-volid','SGPORT',
            '-joliet','-rock','-graft-points',*[k+'='+str(v) for k,v in entries.items()]],check=True)
        listener=socket.socket();listener.bind(('127.0.0.1',0));listener.listen(1);listener.settimeout(1)
        qemu=WORKSPACE/'android/.native-runtime/ubuntu-arm64/host-qemu/usr/bin/qemu-system-aarch64'
        command=[str(qemu),'-name','shellground-arm64-port-builder','-machine','virt','-cpu','cortex-a72',
            '-accel','tcg,thread=multi,tb-size=64','-smp','2','-m','2048','-display','none','-monitor','none','-nic','none','-no-reboot',
            '-kernel',str(PACK/'kernel'),'-initrd',str(PACK/'initrd'),'-append','root=LABEL=cloudimg-rootfs rw console=ttyAMA0',
            '-serial','file:'+str(BUILD/'port-console.log'),'-drive',f'file={image},format=qcow2,if=virtio,discard=unmap',
            '-drive',f'file={iso},format=raw,if=virtio,readonly=on','-device','virtio-serial-pci',
            '-chardev',f'socket,id=sg,host=127.0.0.1,port={listener.getsockname()[1]},reconnect=1',
            '-device','virtserialport,chardev=sg,name=org.shellground.agent']
        channel=None
        with (BUILD/'port-qemu.log').open('wb') as log:
            process=subprocess.Popen(command,env=build_environment(),stdout=log,stderr=subprocess.STDOUT);lower_priority(process)
            try:
                print('ARM port builder started: existing image, no reinstall/full course replay',flush=True)
                deadline=time.monotonic()+480
                while time.monotonic()<deadline:
                    if process.poll() is not None:raise RuntimeError('ARM builder exited; see port-qemu.log')
                    try:connection,_=listener.accept();connection.settimeout(None);channel=GuestChannel(connection);break
                    except socket.timeout:pass
                if channel is None:raise TimeoutError('ARM guest connection')
                if channel.request('status',timeout=480).get('guest')!='shellground':raise ValueError('Wrong guest')
                command=('mkdir -p /mnt/sg-port; mount -o ro /dev/disk/by-label/SGPORT /mnt/sg-port; '
                    'systemd-run --unit=shellground-port-assembly /bin/bash -c '
                    "'python3 -u /mnt/sg-port/guest_port_setup.py > /opt/shellground/port-assembly.log 2>&1; "
                    "rc=$?; echo $rc > /opt/shellground/port-assembly-exit; exit $rc'")
                guest_exec(channel,['bash','-euc',command],root=True)
                deadline=time.monotonic()+2400;last=''
                while time.monotonic()<deadline:
                    script="from pathlib import Path;import json;p=Path('/opt/shellground/port-assembly-exit');l=Path('/opt/shellground/port-assembly.log');print(json.dumps(dict(exit=p.read_text().strip() if p.exists() else None,tail=l.read_text()[-2500:] if l.exists() else 'starting')))"
                    state=json.loads(guest_exec(channel,['python3','-c',script],root=True,timeout=30))
                    if state['tail']!=last:print(state['tail'],flush=True);last=state['tail']
                    if state['exit'] is not None:
                        if state['exit']!='0':raise RuntimeError('ARM assembly failed; see owned guest log')
                        receipt=json.loads(guest_exec(channel,['cat','/opt/shellground/android-port-assembly.json'],root=True))
                        (BUILD/'port-assembly.json').write_text(json.dumps(receipt,indent=2)+'\n');break
                    time.sleep(10)
                else:raise TimeoutError('ARM assembly exceeded 40 minutes')
            finally:
                listener.close()
                if channel:
                    try:channel.request('exec',timeout=8,root=True,argv=['systemctl','poweroff'])
                    except Exception:pass
                    channel.close()
                try:process.wait(timeout=40)
                except subprocess.TimeoutExpired:
                    process.terminate()
                    try:process.wait(timeout=5)
                    except subprocess.TimeoutExpired:process.kill();process.wait(timeout=5)
                print('Owned ARM builder stopped',flush=True)
    if args.export:
        receipt=json.loads((BUILD/'port-assembly.json').read_text())
        if receipt.get('conda_subdir')!='linux-aarch64':raise ValueError('ARM assembly receipt missing')
        target=WORKSPACE/'android/.native-runtime/android-pack-4.7.4';target.mkdir(exist_ok=True)
        temporary=target/'base.pending.qcow2';output=target/'base.qcow2'
        if output.exists():raise FileExistsError('Preserve finished pack')
        subprocess.run([str(RUNTIME/'usr/bin/qemu-img'),'convert','-m','2','-O','qcow2','-c',str(image),str(temporary)],env=build_environment(),check=True)
        temporary.replace(output)
        import shutil
        for name in ('kernel','initrd'):shutil.copy2(PACK/name,target/name)
        files={name:dict(size=(target/name).stat().st_size,sha256=sha256(target/name)) for name in ('base.qcow2','kernel','initrd')}
        manifest=dict(schema=1,version='4.7.4',guest_arch='aarch64',files=files,
            conda_course=True,notebook_course=True,assembly=receipt,android_device_executed=False)
        (target/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
        print('Final ARM pack exported: '+str(output.stat().st_size)+' bytes',flush=True)


if __name__=='__main__':main()
