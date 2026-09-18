"""Run only in the developer's dedicated, disconnected Shellground guest."""
import hashlib
import json
import os
import shutil
from pathlib import Path
import subprocess
import sys
import tempfile

sys.path.insert(0,'/opt/shellground')
from agent import require_guest
from installer_sources import installer_for
from logged_command import run_logged

BASE=Path('/opt/shellground/miniconda')
INSTALLER=Path('/mnt/sg-conda/miniconda.sh')
SPEC=installer_for()
SHA256=SPEC['sha256']


def main():
    require_guest()
    if os.getuid()!=0:raise RuntimeError('Image provisioning requires guest root')
    digest=hashlib.sha256()
    with INSTALLER.open('rb') as source:
        for block in iter(lambda:source.read(1024*1024),b''):digest.update(block)
    if digest.hexdigest()!=SHA256:
        raise RuntimeError('Installer checksum mismatch inside guest')
    # Keep the verified original available for the learner's separate install.
    # Only this marked private builder guest is modified, never the host.
    setup_assets=Path('/opt/shellground/conda-setup')
    if setup_assets.is_symlink():raise RuntimeError('Unexpected setup assets symlink')
    setup_assets.mkdir(mode=0o755,exist_ok=True)
    copied=setup_assets/SPEC['name']
    if copied.is_symlink():raise RuntimeError('Unexpected installer destination symlink')
    shutil.copyfile(INSTALLER,copied);copied.chmod(0o444)
    # Preserve the exact license shipped in the hash-pinned installer; fail if
    # constructor changes its header layout instead of extracting binary data.
    with INSTALLER.open('rb') as stream:header=stream.read(65536).decode('utf-8',errors='replace')
    license_text=header.split('MINICONDA END USER LICENSE AGREEMENT\n',1)[1].split('\nEOF\n',1)[0]
    if 'DISCLAIMER:' not in license_text:raise RuntimeError('Installer license extraction failed')
    (setup_assets/'LICENSE.txt').write_text('MINICONDA END USER LICENSE AGREEMENT\n'+license_text+'\n')
    (setup_assets/'LICENSE.txt').chmod(0o444)
    if not (BASE/'conda-meta/history').is_file():
        if BASE.exists():raise RuntimeError('Partial installation found; inspect the owned guest before retrying')
        subprocess.run(['bash',str(INSTALLER),'-b','-m','-p',str(BASE)],env=dict(os.environ,HOME='/root'),check=True,timeout=600)
    # Root's installer must not own the learner's environment registry/cache.
    # All these paths are exclusively inside the marked image-builder guest.
    for name in ('.conda','conda-envs','conda-cache'):
        directory=Path('/home/learner')/name
        if directory.is_symlink():raise RuntimeError('Unexpected learner directory symlink: '+name)
        directory.mkdir(mode=0o755,exist_ok=True)
        os.chown(directory,1100,1100)
        if name=='.conda':
            for child in directory.iterdir():
                if child.is_file() and not child.is_symlink():os.chown(child,1100,1100)
    # No defaults repository access or hidden host conda configuration.
    config={'channels':['file:///opt/shellground/conda-channel'], 'default_channels':[],
            'offline':True,'auto_activate_base':False,'solver':'classic','notify_outdated_conda':False,
            'envs_dirs':['/home/learner/conda-envs'],'pkgs_dirs':['/home/learner/conda-cache',str(BASE/'pkgs')]}
    config_path=Path('/opt/shellground/condarc');config_path.write_text(json.dumps(config,indent=2)+'\n')
    # Conda merges list settings across configuration sources. Its installer
    # .condarc contains "defaults"; leaving that entry yields an extra channel
    # in real env export even when default_channels expands to an empty list.
    # Replace only this app-owned installation's config, never a host profile.
    (BASE/'.condarc').write_text(config_path.read_text())
    # Third-party account/ToS plugins are not part of the local file channel.
    # Do not ask for, accept, or contact external repository services.
    env=dict(os.environ,HOME='/root',CONDARC=str(config_path),CONDA_OFFLINE='true',CONDA_SOLVER='classic',
             CONDA_REPORT_ERRORS='false',CONDA_NO_PLUGINS='true')
    from channel import build_channel
    channel=build_channel(BASE,Path('/opt/shellground/conda-channel'))
    result=subprocess.run([str(BASE/'bin/conda'),'info','--json'],env=env,text=True,capture_output=True,check=True)
    info=json.loads(result.stdout)
    if info.get('subdir',info.get('platform'))!=SPEC['subdir'] or channel['subdir']!=SPEC['subdir']:
        raise RuntimeError('Installed Conda, package channel and guest architecture must agree')
    packages=[]
    for path in sorted((BASE/'pkgs').glob('*/info/index.json')):
        record=json.loads(path.read_text());packages.append({'name':record['name'],'version':record['version'],'subdir':record.get('subdir'),'extracted':path.parent.parent.name})
    report={'installer_sha256':SHA256,'conda_version':info['conda_version'],'python_version':info['python_version'],
            'subdir':info.get('subdir',info.get('platform')),'offline':info['offline'],'cache_packages':packages,'channel':channel}
    # The check uses learner credentials and a real persistent Bash environment.
    # It creates/removes only two named verification environments in this guest.
    run_dir=Path(tempfile.mkdtemp(prefix='conda-smoke-',dir='/opt/shellground'))
    output=run_dir/'output.log'
    Path('/opt/shellground/conda-smoke-current.json').write_text(json.dumps({'log':str(output)})+'\n')
    check=run_logged(['bash','/mnt/sg-conda/runtime_smoke.sh'],output,
        timeout=600 if SPEC['architecture']=='aarch64' else 90, identity=(1100,1100),
        env=dict(os.environ,HOME='/home/learner',USER='learner',LOGNAME='learner',
                 CONDARC=str(config_path),CONDA_OFFLINE='true',CONDA_SOLVER='classic',
                 CONDA_REPORT_ERRORS='false',CONDA_NO_PLUGINS='true'))
    print(check['tail'],flush=True)
    if check['status']!='passed':
        raise RuntimeError('Conda smoke '+check['status']+'; full output and timings retained in '+str(output))
    sentinel='CONDA_REAL_OFFLINE_CREATE_ACTIVATE_INSTALL_UPDATE_EXPORT_RECREATE_REMOVE_OK'
    if sentinel not in check['tail'].splitlines():raise RuntimeError('Conda smoke did not finish all checks')
    report['smoke']=sentinel
    report['smoke_observation']={key:value for key,value in check.items() if key!='tail'}
    # New adapters take effect on the next guest boot. The running control
    # channel is not restarted while it is servicing this provisioning call.
    for name in ('agent.py','conda_lab.py','conda_runtime.py','shell_snapshot.py','conda_setup.py','installer_sources.py'):
        data=(Path('/mnt/sg-conda')/name).read_bytes();compile(data,name,'exec')
        target=Path('/opt/shellground')/name;target.write_bytes(data);target.chmod(0o644)
    Path('/opt/shellground/conda-build-report.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k!='cache_packages'},indent=2),flush=True)


if __name__=='__main__':main()
