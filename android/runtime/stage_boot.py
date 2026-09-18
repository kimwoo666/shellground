"""Extract two checksum-verified official Linux boot assets, without mounting."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import subprocess

from build_dependencies import ANDROID, NATIVE, WORKSPACE


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--destination', type=Path, required=True)
    args = parser.parse_args()
    allowed = ANDROID / 'runtime-probe/build/generated/assets'
    if args.destination.resolve() != allowed:
        raise ValueError('Only the owned probe asset directory may be generated')
    spec = json.loads(Path(__file__).with_name('boot-sources.json').read_text())['alpine-virt']
    source = NATIVE / 'downloads' / spec['archive']
    with source.open('rb') as stream:
        if hashlib.file_digest(stream, 'sha256').hexdigest() != spec['sha256']:
            raise ValueError('Official boot image checksum mismatch')
    isoinfo = WORKSPACE / 'desktop/.vm-runtime/linux-x86_64/usr/bin/isoinfo'
    allowed.mkdir(parents=True, exist_ok=True)
    files = {}
    for member, name in (('/boot/vmlinuz-virt', 'linux-kernel'), ('/boot/initramfs-virt', 'linux-initramfs')):
        data = subprocess.check_output([str(isoinfo), '-R', '-i', str(source), '-x', member])
        if not data:
            raise ValueError('Missing official ISO member: ' + member)
        # QEMU need not contain a host zlib dependency to load the ARM64 Image.
        if name == 'linux-kernel' and data.startswith(b'\x1f\x8b'):
            data = gzip.decompress(data)
        (allowed / name).write_bytes(data)
        files[name] = {'iso_member': member, 'size': len(data), 'sha256': hashlib.sha256(data).hexdigest()}
    report = {'source': spec, 'files': files, 'evidence': 'Official boot assets extracted; device boot is a separate test'}
    (NATIVE / 'boot-assets.json').write_text(json.dumps(report, indent=2) + '\n')
    print('OFFICIAL_BOOT_ASSETS_STAGED', json.dumps(files), flush=True)


if __name__ == '__main__':
    main()
