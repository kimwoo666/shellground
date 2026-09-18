"""Cross-compile a headless full-system QEMU candidate, not a fake shell.

Requires build_dependencies.py for the same ABI. No download, root, host
installation or application deployment is performed by this developer tool.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess

from build_dependencies import ANDROID,NATIVE,SOURCES,WORKSPACE,run
from verify_candidate import inspect
from candidate_cache import preserve


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--abi',choices=('arm64-v8a','x86_64'),required=True)
    args=parser.parse_args();report=json.loads((NATIVE/('dependencies-'+args.abi+'.json')).read_text())
    root=Path(report['build_root']);owner=json.loads((root/'owner.json').read_text())
    if owner!={'workspace':str(WORKSPACE),'kind':'shellground-android-native'}:raise ValueError('Unknown native build directory')
    for name,spec in report['sources'].items():
        if spec!=SOURCES[name]:raise ValueError('Dependency metadata changed; rebuild dependencies: '+name)
    spec=SOURCES['qemu'];archive=NATIVE/'downloads'/spec['archive']
    with archive.open('rb') as stream:
        if hashlib.file_digest(stream,'sha256').hexdigest()!=spec['sha256']:raise ValueError('QEMU checksum mismatch')
    source=root/'sources'/('qemu-'+spec['version']);prefix=Path(report['prefix']);build=root/args.abi/'qemu';build.mkdir(exist_ok=True)
    patches=sorted(Path(__file__).with_name('patches').glob('*.patch'))
    for patch in patches:
        applied=subprocess.run(['patch','-p1','--fuzz=0','--batch','--dry-run','--reverse','-i',str(patch)],cwd=source,capture_output=True)
        if applied.returncode:subprocess.run(['patch','-p1','--fuzz=0','--batch','--forward','-i',str(patch)],cwd=source,check=True)
    tools=root/'ndk/toolchains/llvm/prebuilt/linux-x86_64/bin'
    triple,cpu=('aarch64-linux-android','aarch64') if args.abi=='arm64-v8a' else ('x86_64-linux-android','x86_64')
    env=dict(os.environ,PKG_CONFIG='/usr/bin/pkg-config',PKG_CONFIG_LIBDIR=str(prefix/'lib/pkgconfig'),PKG_CONFIG_PATH='',
             AR=str(tools/'llvm-ar'),NM=str(tools/'llvm-nm'),RANLIB=str(tools/'llvm-ranlib'),STRIP=str(tools/'llvm-strip'),LC_ALL='C.UTF-8')
    try:os.nice(15)
    except OSError:pass
    run([source/'configure','--target-list=aarch64-softmmu','--with-devices-aarch64=minimal',
         '--cpu='+cpu,'--cc='+str(tools/(triple+'28-clang')),'--cxx='+str(tools/(triple+'28-clang++')),
         '--host-cc=/usr/bin/cc','--python='+str(root/'sources/build-tools/bin/python'),
         '--cross-prefix='+str(tools/'llvm-'),'--without-default-features',
         '--enable-system','--enable-tcg','--enable-fdt=system','--disable-download',
         '--with-coroutine=sigaltstack','--prefix='+str(prefix),
         '--extra-cflags=-O2 -fPIC -I'+str(prefix/'include'),
         '--extra-ldflags=-L'+str(prefix/'lib')+' -Wl,-z,max-page-size=16384 -llog -landroid',
         '-Dprefer_static=true'],build,env)
    run(['ninja','-j2','qemu-system-aarch64'],build,env)
    binary=build/'qemu-system-aarch64'
    validation,elf=inspect(binary,tools/'llvm-readelf',args.abi)
    cached=preserve(binary,NATIVE/'candidates'/args.abi/validation['sha256']/'qemu-system-aarch64',validation['sha256'])
    (NATIVE/('qemu-'+args.abi+'-elf.txt')).write_text(elf)
    artifact={'host_abi':args.abi,'guest_arch':'aarch64','api':28,'binary':str(binary),'cached_binary':str(cached),
              'source':spec,'patches':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in patches},
              'sha256':hashlib.sha256(binary.read_bytes()).hexdigest(),
              'elf_validation':validation,
              'evidence':'cross-build only; Android execution and real Linux boot not yet verified'}
    (NATIVE/('qemu-'+args.abi+'.json')).write_text(json.dumps(artifact,indent=2)+'\n')
    print('ANDROID_QEMU_CANDIDATE_BUILT '+args.abi,flush=True)


if __name__=='__main__':main()
