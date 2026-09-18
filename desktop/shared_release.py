"""Publish the identical PC guest once; assemble ordinary offline app folders."""
import hashlib
import io
import json
from pathlib import Path
import tarfile
import zipfile

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'releases'
WIN=ROOT/'desktop/dist-windows-4.7.4-review/Shellground'
LIN=ROOT/'desktop/dist-linux-4.7.4-review'


def digest(path):
    with path.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()


def record(path):
    return dict(name=path.name,bytes=path.stat().st_size,sha256=digest(path))


def main():
    proof=json.loads((WIN/'runtime/windows-x86_64/disk-compression.json').read_text())
    spec=json.loads((LIN/'runtime/linux-x86_64/runtime.json').read_text())
    if proof['logical_compare_exit']!=0 or spec['image_sha256'] not in (proof['original_sha256'],proof['compressed_sha256']):
        raise ValueError('PC guests do not match')
    image=WIN/'runtime/windows-x86_64/base.qcow2'
    if digest(image)!=proof['compressed_sha256']:raise ValueError('Compressed image changed')
    spec['image_sha256']=proof['compressed_sha256'];spec['disk_compression']=proof
    linux=OUT/'Shellground-4.7.4-Linux-App.tar'
    windows=OUT/'Shellground-4.7.4-Windows-App.zip'
    if linux.exists() or windows.exists():raise FileExistsError('Preserve existing deliveries')
    with tarfile.open(linux,'x') as archive:
        archive.add(LIN/'Shellground',arcname='Shellground-Linux/Shellground')
        runtime=LIN/'runtime/linux-x86_64'
        for path in sorted(runtime.rglob('*')):
            if path==runtime/spec['image'] or (path.is_dir() and not path.is_symlink()):continue
            name='Shellground-Linux/runtime/linux-x86_64/'+path.relative_to(runtime).as_posix()
            if path==runtime/'runtime.json':
                data=(json.dumps(spec,ensure_ascii=False,indent=2)+'\n').encode()
                info=tarfile.TarInfo(name);info.size=len(data);info.mode=0o644;archive.addfile(info,io.BytesIO(data))
            else:archive.add(path,arcname=name)
        for path in (ROOT/'THIRD_PARTY_NOTICES.md',ROOT/'docs/GETTING_STARTED.md',ROOT/'docs/GETTING_STARTED.ko.md'):
            archive.add(path,arcname='Shellground-Linux/'+path.name)
    with zipfile.ZipFile(windows,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=1) as archive:
        for path in sorted(WIN.rglob('*')):
            if path==image:continue
            if path.is_symlink():raise ValueError('Windows app contains a link')
            if path.is_file():archive.write(path,'Shellground-Windows/'+path.relative_to(WIN).as_posix())
    print('Small platform app archives ready',flush=True)
    parts=[]
    with image.open('rb') as source:
        while source.tell()<image.stat().st_size:
            part=OUT/f'Shellground-4.7.4-PC-Guest.qcow2.part{len(parts)+1:02d}'
            used=0
            with part.open('xb') as target:
                while used<1900000000:
                    block=source.read(min(4*1024*1024,1900000000-used))
                    if not block:break
                    target.write(block);used+=len(block)
            parts.append(record(part))
    sha=proof['compressed_sha256']
    paths=' '.join('"'+p['name']+'"' for p in parts)
    sh='''#!/bin/sh
set -eu
cd -- "$(dirname -- "$0")"
[ ! -e Shellground-Linux ] || { echo "Shellground-Linux already exists; use a new empty folder."; exit 1; }
'''
    # Verify inputs before extracting or writing the final guest.
    for item in [record(linux),*parts]:sh+='printf "%s  %s\\n" "'+item['sha256']+'" "'+item['name']+'" | sha256sum -c -\n'
    sh+='tar -xf "'+linux.name+'"\n'
    sh+='cat '+paths+' > Shellground-Linux/runtime/linux-x86_64/base.qcow2.partial\n'
    sh+='printf "%s  %s\\n" "'+sha+'" "Shellground-Linux/runtime/linux-x86_64/base.qcow2.partial" | sha256sum -c -\n'
    sh+='mv Shellground-Linux/runtime/linux-x86_64/base.qcow2.partial Shellground-Linux/runtime/linux-x86_64/base.qcow2\n'
    sh+='printf "Ready: ./Shellground-Linux/Shellground\\n"\n'
    (OUT/'Join-Linux.sh').write_text(sh);(OUT/'Join-Linux.sh').chmod(0o755)
    cmd='@echo off\r\nsetlocal\r\ncd /d "%~dp0"\r\nif exist Shellground-Windows (echo Use a new empty folder. & exit /b 1)\r\n'
    for item in [record(windows),*parts]:
        cmd+='powershell -NoProfile -Command "if ((Get-FileHash -LiteralPath \''+item['name']+'\' -Algorithm SHA256).Hash -ne \''+item['sha256']+'\') { exit 1 }"\r\nif errorlevel 1 (echo File missing or damaged. & pause & exit /b 1)\r\n'
    cmd+='powershell -NoProfile -Command "Expand-Archive -LiteralPath \''+windows.name+'\' -DestinationPath \'.\'"\r\nif errorlevel 1 exit /b 1\r\n'
    cmd+='copy /b '+'+'.join('"'+p['name']+'"' for p in parts)+' "Shellground-Windows\\runtime\\windows-x86_64\\base.qcow2.partial"\r\nif errorlevel 1 exit /b 1\r\n'
    cmd+='powershell -NoProfile -Command "if ((Get-FileHash -LiteralPath \'Shellground-Windows/runtime/windows-x86_64/base.qcow2.partial\' -Algorithm SHA256).Hash -ne \''+sha+'\') { exit 1 }; Move-Item -LiteralPath \'Shellground-Windows/runtime/windows-x86_64/base.qcow2.partial\' -Destination \'Shellground-Windows/runtime/windows-x86_64/base.qcow2\'"\r\nif errorlevel 1 exit /b 1\r\n'
    cmd+='echo Ready: Shellground-Windows\\Shellground.exe\r\npause\r\n'
    (OUT/'Join-Windows.cmd').write_bytes(cmd.encode('ascii'))
    result=dict(schema=1,shared_disk=dict(bytes=image.stat().st_size,sha256=sha,parts=parts),
        linux=record(linux),windows=record(windows),logical_compare_exit=0,
        native_windows_executed=False,linux_executable_sha256=digest(LIN/'Shellground'))
    (OUT/'pc-build.json').write_text(json.dumps(result,indent=2)+'\n')
    print('Shared PC release ready: one disk, two native app archives',flush=True)


if __name__=='__main__':main()
