"""Actual environment provisioning ONLY inside the app-owned Linux VM."""
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

ASSETS = Path('/opt/shellground/notebook-assets')
BASE = Path('/opt/shellground/miniconda')
ROOT = Path('/opt/shellground/notebook')
ENVROOT = Path('/home/learner/notebook-envs')
WORK = Path('/home/learner/notebook-work')
JDATA = Path('/home/learner/notebook-jupyter')
SOCKET = '/home/learner/.shellground-notebook.sock'


def environment():
    return dict(PATH='/usr/bin:/bin', HOME='/home/learner', USER='learner', LOGNAME='learner',
        LANG='C.UTF-8', LC_ALL='C.UTF-8', CONDARC='/opt/shellground/condarc', CONDA_OFFLINE='true',
        CONDA_NO_PLUGINS='true', CONDA_SOLVER='classic', CONDA_REPORT_ERRORS='false',
        PYTHONNOUSERSITE='1', PIP_NO_INDEX='1', PIP_CONFIG_FILE='/dev/null',
        PIP_DISABLE_PIP_VERSION_CHECK='1', OPENBLAS_NUM_THREADS='1', OMP_NUM_THREADS='1',
        JUPYTER_DATA_DIR=str(JDATA / 'share/jupyter'), JUPYTER_CONFIG_DIR=str(WORK / '.config'),
        JUPYTER_RUNTIME_DIR=str(WORK / '.runtime'), IPYTHONDIR=str(WORK / '.ipython'))


def run(argv, root=False, timeout=110):
    options = {} if root else dict(user=1100, group=1100, extra_groups=[])
    result = subprocess.run(argv, env=environment(), cwd=WORK, capture_output=True,
                            text=True, timeout=timeout, **options)
    if result.returncode:
        raise RuntimeError((result.stderr or result.stdout)[-3000:])
    return result.stdout


def stop_service():
    owner = ROOT / 'service.json'
    if not owner.is_file():
        return
    pid = json.loads(owner.read_text())['pid']
    proc = Path(f'/proc/{pid}/cmdline')
    if not proc.exists():
        return
    if str(ASSETS / 'guest_service.py').encode() not in proc.read_bytes().split(b'\0'):
        raise RuntimeError('Notebook service process ownership mismatch')
    os.killpg(pid, signal.SIGTERM)
    deadline = time.monotonic() + 4
    while proc.exists() and time.monotonic() < deadline:
        time.sleep(.05)
    if proc.exists():
        os.killpg(pid, signal.SIGKILL)


def main():
    sys.path.insert(0, '/opt/shellground')
    from agent import require_guest
    require_guest()
    if os.getuid() != 0:
        raise RuntimeError('Only the owned VM control channel can provision notebooks')
    for path in (ROOT, ENVROOT, WORK, JDATA):
        if path.is_symlink(): raise RuntimeError('Unexpected notebook path link')
        path.mkdir(mode=0o755, parents=True, exist_ok=True)
        if path != ROOT: os.chown(path, 1100, 1100)
    manifest = json.loads((ASSETS / 'manifest.json').read_text())
    for wheel in manifest['wheels']:
        path = ASSETS / wheel['filename']
        if path.parent != ASSETS or path.is_symlink() or path.stat().st_uid != 0:
            raise RuntimeError('Unexpected wheel ownership')
        if hashlib.sha256(path.read_bytes()).hexdigest() != wheel['sha256']:
            raise RuntimeError('Jupyter asset digest mismatch')
    stop_service()
    pip = ['-m', 'pip', 'install', '--no-index', '--no-cache-dir', '--find-links', str(ASSETS)]
    marker = ROOT / 'ready.json'
    stamp = hashlib.sha256((ASSETS / 'manifest.json').read_bytes()).hexdigest()
    if not marker.is_file():
        run([str(BASE / 'bin/python'), *pip, '--target', str(ROOT / 'lib'), *manifest['requirements']], root=True)
        for name in ('basic', 'data'):
            prefix = ENVROOT / name
            if prefix.exists(): raise RuntimeError('Unowned or partial notebook environment: ' + str(prefix))
            run([str(BASE / 'bin/conda'), 'create', '--offline', '--prefix', str(prefix),
                 'python=3.12', 'pip', '--yes'])
            python = str(prefix / 'bin/python')
            run([python, *pip, *manifest['requirements']])
            if name == 'data':
                run([python, '-m', 'pip', 'install', '--no-index', '--no-cache-dir',
                     '--find-links', '/opt/shellground/wheels', 'numpy==2.3.5'])
            run([python, '-m', 'ipykernel', 'install', '--prefix', str(JDATA),
                 '--name', 'sg-' + name, '--display-name', 'Python (' + name + ')'])
        marker.write_text(json.dumps(dict(assets_sha256=stamp)))
    elif json.loads(marker.read_text()).get('assets_sha256') != stamp:
        raise RuntimeError('Notebook assets changed; create a new disposable VM')
    env = dict(environment(), PYTHONPATH=str(ROOT / 'lib'))
    log = (ROOT / 'service.log').open('ab')
    process = subprocess.Popen([str(BASE / 'bin/python'), str(ASSETS / 'guest_service.py'), 'serve'],
        stdin=subprocess.DEVNULL, stdout=log, stderr=log, cwd=WORK, env=env,
        user=1100, group=1100, extra_groups=[], start_new_session=True)
    log.close()
    (ROOT / 'service.json').write_text(json.dumps(dict(pid=process.pid)))
    print(json.dumps(dict(pid=process.pid, work=str(WORK), environments=str(ENVROOT),
                          kernels=str(JDATA / 'share/jupyter/kernels'))))


if __name__ == '__main__':
    main()
