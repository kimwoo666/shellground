"""Stage checksum/ELF-validated executables for the isolated Android probe APK."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

from build_dependencies import NATIVE, SOURCES, WORKSPACE
from candidate_cache import select
from verify_candidate import inspect


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--destination', type=Path, required=True)
    args = parser.parse_args()
    android = Path(__file__).resolve().parents[1]
    allowed = args.destination.resolve()
    if allowed not in (android / 'runtime-probe/build/generated/jniLibs', android / 'app/build/generated/realJniLibs'):
        raise ValueError('Only the two owned Android generated native directories may be staged')
    patches = {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
               for p in Path(__file__).with_name('patches').glob('*.patch')}
    artifacts = []
    for abi in ('arm64-v8a', 'x86_64'):
        report = json.loads((NATIVE / ('qemu-' + abi + '.json')).read_text())
        dependencies = json.loads((NATIVE / ('dependencies-' + abi + '.json')).read_text())
        root = Path(dependencies['build_root'])
        binary = Path(report['binary'])
        if report['source'] != SOURCES['qemu'] or report['patches'] != patches:
            raise ValueError('Candidate metadata is stale; rebuild ' + abi)
        if binary.resolve() != (root / abi / 'qemu/qemu-system-aarch64').resolve():
            raise ValueError('Unexpected candidate path')
        if dependencies.get('ndk')!='27.2.12479018':
            raise ValueError('Unexpected verified NDK version')
        # /tmp may disappear at reboot. Exact previously recorded bytes can be
        # recovered from our own staged copies, then ELF-inspected again using
        # the durable project NDK. Never loosen the hash/source/patch gates.
        cache=NATIVE/'candidates'/abi/report['sha256']/'qemu-system-aarch64'
        binary=select(binary,cache,[
            android/'app/build/generated/realJniLibs'/abi/'libshellground_qemu.so',
            android/'runtime-probe/build/generated/jniLibs'/abi/'libshellground_qemu.so',
        ],report['sha256'])
        readelf=WORKSPACE/'desktop/.android-tools/sdk/ndk'/dependencies['ndk']/'toolchains/llvm/prebuilt/linux-x86_64/bin/llvm-readelf'
        verified, _ = inspect(binary, readelf, abi)
        if verified['sha256'] != report['sha256']:
            raise ValueError('Candidate checksum changed')
        artifacts.append((abi, binary, verified,readelf))
    for abi, binary, verified,readelf in artifacts:
        target = allowed / abi / 'libshellground_qemu.so'
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(binary, target)
        # Keep the PIE intact; remove debug sections only in the delivery copy.
        # The verified original remains immutable. AGP's generic shared-library
        # stripper is still disabled because this is an executable, not a DSO.
        subprocess.run([str(readelf.with_name('llvm-strip')),'--strip-debug',str(target)],check=True)
        compact,_=inspect(target,readelf,abi)
        for key in ('machine','interpreter','load_alignments','needed_system_libraries'):
            if compact[key]!=verified[key]:raise ValueError('Stripping changed executable contract')
        (allowed/(abi+'-delivery.json')).write_text(json.dumps(dict(original_sha256=verified['sha256'],
            delivery_sha256=compact['sha256'],bytes=target.stat().st_size,operation='strip-debug-only'),indent=2)+'\n')
        print('STAGED', abi, compact['sha256'],target.stat().st_size, flush=True)


if __name__ == '__main__':
    main()
