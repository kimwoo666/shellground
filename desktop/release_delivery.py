"""Assemble deliveries without rebuilding or replaying existing courses."""
import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import tarfile
import zipfile

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'releases'

def digest(path):
    with path.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()

def json_file(path,value):
    path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

def sources():
    OUT.mkdir(exist_ok=True)
    target=OUT/'Shellground-4.7.4-Native-Sources.tar'
    if target.exists():raise FileExistsError(target)
    native=ROOT/'android/.native-runtime'
    specs=json.loads((ROOT/'android/runtime/native-sources.json').read_text())
    with tarfile.open(target,'x') as archive:
        for spec in specs.values():
            path=native/'downloads'/spec['archive']
            if digest(path)!=spec['sha256']:raise ValueError('Native source identity mismatch')
            archive.add(path,arcname='sources/'+path.name)
        for path in sorted((ROOT/'android/runtime').glob('*.py')):archive.add(path,arcname='build/android/runtime/'+path.name)
        for path in sorted((ROOT/'android/runtime').glob('*.json')):archive.add(path,arcname='build/android/runtime/'+path.name)
        archive.add(ROOT/'android/runtime/patches',arcname='build/android/runtime/patches')
        archive.add(ROOT/'android/runtime/README.md',arcname='build/android/runtime/README.md')
        archive.add(ROOT/'desktop/build_android_freetype.py',arcname='build/desktop/build_android_freetype.py')
        archive.add(ROOT/'desktop/.android-tools/freetype-2.14.3',arcname='sources/freetype-2.14.3',
            filter=lambda info:None if '.git' in Path(info.name).parts else info)
        for name in ('GPL-2','LGPL-2','LGPL-2.1','GPL-3','LGPL-3'):
            archive.add(Path('/usr/share/common-licenses')/name,arcname='licenses/'+name+'.txt')
        archive.add(ROOT/'THIRD_PARTY_NOTICES.md',arcname='THIRD_PARTY_NOTICES.md')
    print('Native corresponding-source companion:',target.stat().st_size,flush=True)

def linux():
    OUT.mkdir(exist_ok=True)
    root=ROOT/'desktop/dist-linux-4.7.4-review'
    runtime=root/'runtime/linux-x86_64'
    windows=ROOT/'desktop/dist-windows-4.7.4-review/Shellground/runtime/windows-x86_64'
    proof=json.loads((windows/'disk-compression.json').read_text())
    spec=json.loads((runtime/'runtime.json').read_text())
    if spec['image_sha256']!=proof['original_sha256'] or proof['logical_compare_exit']!=0:raise ValueError('Different guest disk')
    compressed=windows/'base.qcow2'
    if digest(compressed)!=proof['compressed_sha256']:raise ValueError('Compressed disk changed')
    spec['image_sha256']=proof['compressed_sha256'];spec['disk_compression']=proof
    target=OUT/'Shellground-4.7.4-Linux-x64.tar'
    if target.exists():raise FileExistsError(target)
    with tarfile.open(target,'x') as archive:
        archive.add(root/'Shellground',arcname='Shellground/Shellground')
        for path in sorted(runtime.rglob('*')):
            if path.is_dir() and not path.is_symlink():continue
            name='Shellground/runtime/linux-x86_64/'+path.relative_to(runtime).as_posix()
            if path.name=='runtime.json' and path.parent==runtime:
                data=(json.dumps(spec,ensure_ascii=False,indent=2)+'\n').encode();info=tarfile.TarInfo(name);info.size=len(data);info.mode=0o644
                archive.addfile(info,io.BytesIO(data))
            elif path==runtime/spec['image']:archive.add(compressed,arcname=name)
            else:archive.add(path,arcname=name)
        for path in (ROOT/'THIRD_PARTY_NOTICES.md',ROOT/'docs/GETTING_STARTED.md',ROOT/'docs/GETTING_STARTED.ko.md'):
            archive.add(path,arcname='Shellground/'+path.name)
    json_file(OUT/'linux-build.json',dict(schema=1,artifact=target.name,bytes=target.stat().st_size,
        sha256=digest(target),executable_sha256=digest(root/'Shellground'),
        packaged_execution_evidence='desktop/LINUX_474_REVIEW.md',disk_compression=proof,course_rerun=False))
    print('Linux delivery ready:',target.stat().st_size,flush=True)

def split():
    # Avoid giant Git blobs. GitHub release assets must each be under2GiB.
    maximum=1900000000
    for archive in (OUT/'Shellground-4.7.4-Windows-x64.zip',OUT/'Shellground-4.7.4-Linux-x64.tar'):
        if archive.stat().st_size<2**31:continue
        parts=[]
        with archive.open('rb') as input:
            index=1
            while input.tell()<archive.stat().st_size:
                part=archive.with_name(archive.name+f'.part{index:02d}')
                count=0
                with part.open('xb') as output:
                    while count<maximum:
                        block=input.read(min(4*1024*1024,maximum-count))
                        if not block:break
                        output.write(block);count+=len(block)
                parts.append(dict(name=part.name,bytes=count,sha256=digest(part)));index+=1
        json_file(OUT/(archive.name+'.parts.json'),dict(artifact=archive.name,bytes=archive.stat().st_size,sha256=digest(archive),parts=parts))
        if archive.suffix=='.zip':
            joined='+'.join('"'+p['name']+'"' for p in parts)
            command='@echo off\r\nsetlocal\r\ncd /d "%~dp0"\r\nif exist "'+archive.name+'" (echo The ZIP already exists. & exit /b 1)\r\n'
            command+='copy /b '+joined+' "'+archive.name+'"\r\nif errorlevel 1 exit /b 1\r\ncertutil -hashfile "'+archive.name+'" SHA256\r\necho Expected: '+digest(archive)+'\r\necho Extract the ZIP completely before launching Shellground.exe.\r\npause\r\n'
            (OUT/'Join-Windows.cmd').write_bytes(command.encode('ascii'))
        else:
            command='#!/bin/sh\nset -eu\ncd -- "$(dirname -- "$0")"\n[ ! -e "'+archive.name+'" ] || { echo "Archive already exists"; exit 1; }\n'
            command+='cat '+' '.join('"'+p['name']+'"' for p in parts)+' > "'+archive.name+'.partial"\n'
            command+='printf "%s  %s\\n" "'+digest(archive)+'" "'+archive.name+'.partial" | sha256sum -c -\n'
            command+='mv -- "'+archive.name+'.partial" "'+archive.name+'"\nprintf "Extract with: tar -xf %s\\n" "'+archive.name+'"\n'
            (OUT/'Join-Linux.sh').write_text(command);(OUT/'Join-Linux.sh').chmod(0o755)
        print('Release chunks ready:',archive.name,len(parts),flush=True)

def adopt_linux_compression():
    """Keep the current installed Linux bundle, remove its needless disk slack."""
    runtime=ROOT/'desktop/dist-linux-4.7.4-review/runtime/linux-x86_64'
    windows=ROOT/'desktop/dist-windows-4.7.4-review/Shellground/runtime/windows-x86_64'
    proof=json.loads((windows/'disk-compression.json').read_text());spec=json.loads((runtime/'runtime.json').read_text())
    if spec['image_sha256']==proof['compressed_sha256']:return
    if proof['logical_compare_exit']!=0 or spec['image_sha256']!=proof['original_sha256']:raise ValueError('Different Linux disk')
    image=windows/'base.qcow2'
    if digest(image)!=proof['compressed_sha256']:raise ValueError('Compressed disk changed')
    pending=runtime/'base-delivery.pending.qcow2'
    os.link(image,pending);pending.replace(runtime/spec['image'])
    spec['image_sha256']=proof['compressed_sha256'];spec['disk_compression']=proof
    temporary=runtime/'runtime.json.new';json_file(temporary,spec);temporary.replace(runtime/'runtime.json')
    json_file(runtime/'disk-compression.json',proof)
    print('Current Linux runtime now shares the losslessly compressed delivery disk',flush=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('action',choices=['sources','linux','split','adopt-linux-compression']);args=parser.parse_args()
    {'sources':sources,'linux':linux,'split':split,'adopt-linux-compression':adopt_linux_compression}[args.action]()
