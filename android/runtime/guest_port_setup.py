"""Offline image assembly in the explicitly owned ARM builder guest only."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

sys.path.insert(0,'/opt/shellground')
from agent import require_guest


def main():
    require_guest()
    if os.getuid()!=0 or os.uname().machine!='aarch64':raise RuntimeError('Owned ARM builder required')
    source=Path('/mnt/sg-port'); target=Path('/opt/shellground')
    receipt=target/'android-port-assembly.json'
    for name in ('real-guest','conda-guest'):
        for path in (source/name).iterdir():
            if path.is_file():shutil.copy2(path,target/path.name)
    # Ordinary Linux starts without implicitly activating Conda.
    shutil.copy2(source/'real-guest/bashrc',target/'bashrc')
    notebook=target/'notebook-assets';notebook.mkdir(exist_ok=True)
    for path in (source/'notebook-guest').iterdir():shutil.copy2(path,notebook/path.name)
    for path in (source/'wheels').glob('*.whl'):
        directory=target/'wheels' if path.name.startswith('numpy-') else notebook
        directory.mkdir(exist_ok=True);shutil.copy2(path,directory/path.name)
    shutil.copy2(source/'wheels/manifest.json',notebook/'manifest.json')
    base=target/'miniconda'
    if not (base/'conda-meta/history').is_file():raise RuntimeError('Existing ARM Miniconda installation missing')
    env=dict(os.environ,HOME='/home/learner',CONDARC=str(target/'condarc'),CONDA_OFFLINE='true',
        CONDA_NO_PLUGINS='true',CONDA_SOLVER='classic',OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1')
    info=json.loads(subprocess.check_output([str(base/'bin/conda'),'info','--json'],env=env,timeout=180))
    if info.get('subdir',info.get('platform'))!='linux-aarch64':raise RuntimeError('Conda architecture mismatch')
    # These are known, failed historical verification fixtures, not learner
    # progress. Remove them from this private build image before distribution.
    for name in ('sg-proof','sg-copy'):
        path=Path('/home/learner/conda-envs')/name
        if path.is_dir() and not path.is_symlink():shutil.rmtree(path)
    sys.path.insert(0,str(notebook))
    import guest_setup
    original_run=guest_setup.run
    # Installation under cross-architecture TCG can take longer than a normal
    # learner transaction. Only this builder call gets the larger budget.
    guest_setup.run=lambda argv,root=False,timeout=110:original_run(argv,root=root,timeout=600)
    print('Preparing Jupyter environments from offline ARM wheels',flush=True)
    guest_setup.main()
    # One platform delta check, not another replay of the existing course.
    import guest_service
    def call(payload):
        result=subprocess.run(['/usr/bin/python3',str(notebook/'guest_service.py'),'client'],
            input=json.dumps(payload),capture_output=True,text=True,user=1100,group=1100,
            cwd='/home/learner/notebook-work',timeout=15)
        if result.returncode:raise RuntimeError(result.stderr[-2000:])
        response=json.loads(result.stdout)
        if not response['ok']:raise RuntimeError(response['error'])
        return response['value']
    deadline=time.monotonic()+40
    while True:
        try:call({'action':'ping'});break
        except Exception:
            if time.monotonic()>deadline:raise
            time.sleep(1)
    job=call({'action':'begin','request':{'operation':'list'}})['job']
    while True:
        state=call({'action':'poll','job':job})
        if state['done']:break
        time.sleep(.2)
    kernels=state['result']['kernels']
    if {k['name'] for k in kernels}!={'sg-basic','sg-data'}:raise RuntimeError('ARM kernel registrations missing')
    probe=subprocess.check_output(['/home/learner/notebook-envs/data/bin/python','-I','-c',
        'import numpy as n,ipykernel,sys,json; print(json.dumps(dict(sum=int(n.arange(4).sum()),prefix=sys.prefix,numpy=n.__version__)))'],
        env=env,user=1100,group=1100,cwd='/tmp',timeout=90,text=True)
    observation=json.loads(probe)
    if observation['sum']!=6 or observation['numpy']!='2.3.5':raise RuntimeError(observation)
    guest_setup.stop_service()
    (guest_setup.ROOT/'service.json').unlink(missing_ok=True)
    # Drop download/OS logs, not Conda's offline teaching channel/package cache.
    for path in Path('/var/cache/apt/archives').glob('*.deb'):path.unlink()
    for path in Path('/var/log').rglob('*.log'):
        if path.is_file() and not path.is_symlink():path.write_bytes(b'')
    record=dict(schema=1,kind='arm-guest-assembly',android_device_executed=False,
        full_course_rerun=False,conda_subdir=info.get('subdir',info.get('platform')),
        kernel_names=[k['name'] for k in kernels],scientific_import=observation,
        source_manifest=json.loads((source/'port-source-manifest.json').read_text()))
    receipt.write_text(json.dumps(record,indent=2)+'\n')
    subprocess.run(['sync'],check=True)
    subprocess.run(['fstrim','-av'],check=False)
    print('ARM guest assembly and new runtime import delta complete',flush=True)


if __name__=='__main__':main()
