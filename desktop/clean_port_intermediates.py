"""Explicit delivery cleanup. Never visits user progress, Git or active outputs."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import time

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'releases/verification'


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--windows',action='store_true');parser.add_argument('--android',action='store_true');args=parser.parse_args()
    if args.android:return android_cleanup()
    if not args.windows:raise ValueError('An explicit cleanup phase is required')
    proof=json.loads((ROOT/'releases/pc-build.json').read_text())
    current=ROOT/'desktop/dist-linux-4.7.4-review/runtime/linux-x86_64/runtime.json'
    if json.loads(current.read_text())['image_sha256']!=proof['shared_disk']['sha256']:
        raise ValueError('Current Linux disk has not adopted the verified delivery')
    if not (ROOT/'desktop/.jupyter-build/conda-baseline/runtime.json').is_file():
        raise ValueError('Compact historical evidence is missing')
    OUT.mkdir(parents=True,exist_ok=True)
    for source in (ROOT/'desktop/.windows-build').glob('*.json'):
        if source.stat().st_size<4*1024*1024:shutil.copy2(source,OUT/('windows-'+source.name))
    for source in (ROOT/'desktop/dist-linux-4.7.4-review/verification').glob('*.json'):
        shutil.copy2(source,OUT/('linux-'+source.name))
    names=[
        'desktop/.windows-build/toolchain','desktop/.windows-build/downloads',
        'desktop/.windows-build/runtime','desktop/dist-linux-review','desktop/dist-linux-pip-review',
        'desktop/.vm-runtime-conda','desktop/build','desktop/.build-tools',
        'releases/Shellground-4.7.4-Windows-x64.zip',
    ]
    before=shutil.disk_usage(ROOT).free;removed=[]
    for name in names:
        path=ROOT/name
        if not path.exists():continue
        if path.is_symlink():raise ValueError('Unexpected cleanup link: '+name)
        if path.is_dir():shutil.rmtree(path)
        else:path.unlink()
        removed.append(name);print('Removed generated intermediate:',name,flush=True)
    report=dict(time=time.strftime('%Y-%m-%dT%H:%M:%S%z'),removed=removed,
        free_before=before,free_after=shutil.disk_usage(ROOT).free,
        preserved=['current Linux/Windows bundles','current source and tests','Git history','learner progress','private signing key'])
    (OUT/'windows-cleanup.json').write_text(json.dumps(report,indent=2)+'\n')
    print('Free-space increase:',report['free_after']-before,flush=True)


def android_cleanup():
    result=json.loads((ROOT/'releases/android-build.json').read_text())
    if not result.get('new_real_port_tests_passed'):
        raise ValueError('Android new integration checks have not passed')
    apk=ROOT/'releases'/result['artifact']
    if not apk.is_file() or apk.stat().st_size!=result['bytes']:
        raise ValueError('Final APK missing')
    if not (ROOT/'releases/Shellground-4.7.4-Native-Sources.tar').is_file():
        raise ValueError('Corresponding native sources missing')
    processes=subprocess.check_output(['ps','-eo','args'],text=True)
    if any('-avd shellground-port474' in line for line in processes.splitlines()):
        raise ValueError('Stop the owned emulator before removing its tools/data')
    OUT.mkdir(parents=True,exist_ok=True)
    for name in ('real-port-final.log','conda-final.log','notebook-carry.json','package474h.log','port-instrumentation.log'):
        source=ROOT/'android/.port-checks'/name
        if source.exists():shutil.copy2(source,OUT/('android-'+name))
    for source,name in (
        (ROOT/'android/.native-runtime/android-pack-4.7.4/manifest.json','android-guest-manifest.json'),
        (ROOT/'android/app/build/generated/portAssets/port-source-manifest.json','android-shared-source-manifest.json'),
    ):shutil.copy2(source,OUT/name)
    # Keep compact historical verification, not old installers or seed disks.
    for source in (ROOT/'desktop/.conda-build').rglob('*.json'):
        if source.stat().st_size<4*1024*1024:
            name='conda-'+str(source.relative_to(ROOT/'desktop/.conda-build')).replace('/','-')
            shutil.copy2(source,OUT/name)
    names=[
        'android/app/build','android/runtime-probe/build','android/build','android/.gradle',
        'android/.gradle-user','android/.native-runtime','android/.port-checks',
        'desktop/.windows-build','desktop/.vm-runtime','desktop/.runtime','desktop/.python-runtime',
        'desktop/.vm-build','desktop/.conda-build',
    ]
    # Preserve both private historical/current signing keys. Never upload them.
    tools=ROOT/'desktop/.android-tools'
    for name in ('uv-cache','freetype-2.14.3.tar.xz','sdk','gradle-8.11.1','freetype-2.14.3',
        'gradle-home','avd','freetype-build-arm64-v8a','pytools','jdk','freetype-build-x86_64',
        'downloads','android-user','python','.knownPackages'):
        names.append('desktop/.android-tools/'+name)
    before=shutil.disk_usage(ROOT).free;removed=[]
    for name in names:
        path=ROOT/name
        if not path.exists():continue
        if path.is_symlink():raise ValueError('Unexpected cleanup link: '+name)
        if path.is_dir():shutil.rmtree(path)
        else:path.unlink()
        removed.append(name);print('Removed generated intermediate:',name,flush=True)
    after=shutil.disk_usage(ROOT).free
    report=dict(time=time.strftime('%Y-%m-%dT%H:%M:%S%z'),removed=removed,
        free_before=before,free_after=after,private_signing_keys_preserved=True,
        current_apps_and_source_preserved=True,learner_progress_modified=False)
    (OUT/'android-cleanup.json').write_text(json.dumps(report,indent=2)+'\n')
    print('Free-space increase:',after-before,flush=True)


if __name__=='__main__':main()
