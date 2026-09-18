"""Compress the immutable Windows guest without changing its virtual disk.

qemu-img compare checks logical disk equality once; no course/VM test is rerun.
Only the release copy is replaced, never a shared hardlink's contents.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import zipfile

ROOT=Path(__file__).resolve().parent
BUNDLE=ROOT/'dist-windows-4.7.4-review/Shellground'


def digest(path):
    with path.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()


def atomic_json(path,value):
    temporary=path.with_name(path.name+'.new')
    if temporary.is_symlink():raise ValueError('Unexpected generated link')
    temporary.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    temporary.replace(path)


def compact():
    runtime=BUNDLE/'runtime/windows-x86_64'
    metadata=runtime/'runtime.json';spec=json.loads(metadata.read_text())
    image=runtime/spec['image'];receipt=runtime/'disk-compression.json'
    if receipt.exists():
        proof=json.loads(receipt.read_text())
        if proof.get('logical_compare_exit')!=0 or digest(image)!=proof['compressed_sha256']:
            raise RuntimeError('Compressed image identity changed')
        return
    original=digest(image)
    if original!=spec['image_sha256']:raise ValueError('Unrecognized original guest image')
    tools=ROOT/'.vm-runtime/linux-x86_64'
    qemu=tools/'usr/bin/qemu-img'
    env=dict(os.environ,LD_LIBRARY_PATH=str(tools/'usr/lib/x86_64-linux-gnu'),QEMU_MODULE_DIR=str(tools/'usr/lib/x86_64-linux-gnu/qemu'))
    pending=runtime/'base-compressed.pending.qcow2'
    if pending.exists():raise FileExistsError('Inspect incomplete compression before replacing it')
    original_size=image.stat().st_size
    print('Compressing Windows delivery disk; original remains immutable',flush=True)
    subprocess.run([str(qemu),'convert','-m','2','-O','qcow2','-c',str(image),str(pending)],env=env,check=True)
    subprocess.run([str(qemu),'compare','-q',str(image),str(pending)],env=env,check=True)
    checksum=digest(pending)
    proof=dict(schema=1,operation='qcow2-lossless-container-compression',original_sha256=original,
        compressed_sha256=checksum,original_bytes=original_size,compressed_bytes=pending.stat().st_size,
        logical_compare_exit=0,course_rerun=False,native_windows_executed=False)
    pending.replace(image)
    spec['image_sha256']=checksum;spec['disk_compression']=proof
    atomic_json(metadata,spec);atomic_json(receipt,proof)
    print('Windows disk compressed: '+str(proof['compressed_bytes'])+' bytes; logical comparison passed',flush=True)


def notices():
    source=ROOT/'.windows-build/toolchain/python/tools'
    target=BUNDLE/'licenses';target.mkdir(exist_ok=True)
    shutil.copy2(source/'LICENSE.txt',target/'CPython-LICENSE.txt')
    for info in sorted((source/'Lib/site-packages').glob('*.dist-info')):
        for path in info.rglob('*'):
            if path.is_file() and any(w in path.name.upper() for w in ('LICENSE','COPYING','NOTICE')):
                output=target/info.name/path.relative_to(info);output.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(path,output)
    for name in ('LGPL-3','GPL-3'):
        shutil.copy2(Path('/usr/share/common-licenses')/name,target/(name+'.txt'))
    shutil.copy2(ROOT/'assets/Noto-COPYRIGHT.txt',target/'Noto-COPYRIGHT.txt')
    (BUNDLE/'사용방법.txt').write_text('''Shellground 4.7.4 — Windows x64

1. 압축을 전부 풀고 Shellground 폴더의 Shellground.exe를 실행하세요.
2. _internal과 runtime 폴더를 실행파일과 함께 보관하세요.
3. Python, Linux, Docker, ROS 2, Conda, Jupyter 과정을 앱에서 선택합니다.

Windows 10/11 64비트용입니다. Python·Conda·Docker·WSL을 따로 설치하지 않습니다.
학습 완료와 소단계 위치는 자동 저장됩니다. 입력 코드와 임시 실습 파일은 저장하지 않습니다.
미완료 채점 후에는 같은 실습에서 계속 수정할 수 있습니다.
Jupyter에서는 노트북 커널 선택과 Bash의 Conda 활성화가 별개입니다.

Linux 기반 실습은 포함된 전용 가상머신에서 실행합니다. 시작에 시간이 걸릴 수 있습니다.
사용 가능한 Windows 가속 기능이 없으면 소프트웨어 방식으로 실행하므로 더 느립니다.
앱이 만든 실습 환경만 종료하며 개인 Docker·WSL 환경을 조작하지 않습니다.
실습 코드에는 신뢰할 수 있는 학습 코드만 입력하세요.

검증 범위: Linux 호스트의 Wine에서 Windows 실행파일을 제작했습니다.
실제 Windows PC에서의 기동·주변기기·가속 기능 검증은 수행하지 않았습니다.
서명 인증서를 사용하지 않은 자체 제작 실행파일입니다.

원본 라이선스: licenses 폴더 및 runtime/windows-x86_64/qemu의 COPYING 파일.
Qt/PySide 6.8.3 소스: https://code.qt.io/cgit/pyside/pyside-setup.git/?h=v6.8.3
Qt 라이브러리는 _internal/PySide6의 동적 DLL이며 교체 가능한 형태로 제공합니다.
QEMU Windows 배포·소스 안내: https://qemu.weilnetz.de/w64/
Shellground는 이 오픈소스 구성요소의 제작자가 아닙니다.
''',encoding='utf-8-sig')


def pack():
    destination=ROOT.parent/'releases';destination.mkdir(exist_ok=True)
    target=destination/'Shellground-4.7.4-Windows-x64.zip'
    if target.exists():raise FileExistsError('Preserve finished delivery')
    pending=target.with_suffix('.zip.partial')
    notices()
    with zipfile.ZipFile(pending,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=1,allowZip64=True) as archive:
        for path in sorted(BUNDLE.rglob('*')):
            if path.is_symlink():raise ValueError('Unexpected link in Windows distribution')
            if path.is_file():archive.write(path,path.relative_to(BUNDLE.parent).as_posix(),
                compress_type=zipfile.ZIP_STORED if path.suffix=='.qcow2' else zipfile.ZIP_DEFLATED,compresslevel=1)
    pending.replace(target)
    atomic_json(destination/'windows-build.json',dict(schema=1,artifact=target.name,bytes=target.stat().st_size,
        sha256=digest(target),built=True,build_host='Linux with Wine',native_windows_executed=False,
        course_rerun=False,disk_compression=json.loads((BUNDLE/'runtime/windows-x86_64/disk-compression.json').read_text())))
    print('Windows portable delivery ready: '+str(target),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--compact',action='store_true');parser.add_argument('--pack',action='store_true')
    args=parser.parse_args()
    if args.compact:compact()
    if args.pack:pack()
