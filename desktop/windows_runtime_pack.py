"""Assemble an UNVERIFIED Windows x64 runtime, without installing anything.

Run under the builder's resource limit. The source guest remains immutable.
This is packaging evidence, never Windows execution/grading evidence.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import struct
import subprocess
import tempfile

INSTALLER = 'qemu-w64-setup-20260811.exe'
INSTALLER_URL = 'https://qemu.weilnetz.de/w64/' + INSTALLER
INSTALLER_SHA512 = '5bcf9eed634e8575a37b74f445af41a2fe4106da512d0c30c368301d4c105037fdfab40a5287367a28a957624cddebbc8c07e16c88ab6634f554cdf3d16bf543'
REQUIRED = {'qemu-img.exe', 'qemu-system-x86_64.exe', 'share/bios-256k.bin', 'COPYING', 'COPYING.LIB'}


def digest(path, algorithm='sha256'):
    result = hashlib.new(algorithm)
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''): result.update(block)
    return result.hexdigest()


def safe_name(name):
    if (not name or '\\' in name or ':' in name or '\n' in name or '\r' in name or '\0' in name
            or name.startswith('/') or any(p in ('', '.', '..') for p in name.split('/'))):
        raise ValueError('Unsafe archive path: ' + repr(name))
    for part in name.split('/'):
        if part.endswith((' ', '.')) or re.fullmatch(r'(con|prn|aux|nul|com[1-9]|lpt[1-9])(?:\..*)?', part, re.I):
            raise ValueError('Unsafe Windows file name: ' + name)
    return name


def selected_listing(text):
    """Parse 7-Zip technical listing only after the actual member separator."""
    if '\n----------\n' not in text: raise ValueError('Unrecognized archive listing')
    selected = {}; seen = set()
    for block in text.split('\n----------\n', 1)[1].split('\n\n'):
        fields = dict(line.split(' = ', 1) for line in block.splitlines() if ' = ' in line)
        if 'Path' not in fields: continue
        name = safe_name(fields['Path'])
        folded = name.casefold()
        if folded in seen: raise ValueError('Case-colliding archive path: ' + name)
        seen.add(folded)
        path = PurePosixPath(name)
        choose = (name in REQUIRED or path.parts[0] == 'share' or
                  (len(path.parts) == 1 and name.lower().endswith('.dll')))
        if choose and fields.get('Folder') != '+':
            size = int(fields.get('Size', '-1'))
            if size < 0: raise ValueError('Missing archive member size: ' + name)
            selected[name] = size
    if not REQUIRED.issubset(selected): raise ValueError('Incomplete Windows QEMU installer')
    return selected


def assert_pe_x64(path):
    with Path(path).open('rb') as stream:
        header = stream.read(64)
        if len(header) != 64 or header[:2] != b'MZ': raise ValueError('Not a Windows executable: ' + str(path))
        offset = struct.unpack_from('<I', header, 60)[0]
        if not 64 <= offset <= 16 * 1024 * 1024: raise ValueError('Invalid PE offset')
        stream.seek(offset); signature = stream.read(6)
        if signature != b'PE\0\0\x64\x86': raise ValueError('Not a Windows x64 PE: ' + str(path))


def bound_guest(source, spec):
    if spec.get('protocol') != 1 or spec.get('provisioned') is not True:
        raise ValueError('A provisioned immutable Linux guest is required')
    image_name = safe_name(spec['image'])
    image = source / image_name
    if image.is_symlink() or not image.is_file() or not image.resolve().is_relative_to(source.resolve()):
        raise ValueError('Guest image escapes source runtime')
    if not re.fullmatch('[a-f0-9]{64}', spec.get('image_sha256', '')):
        raise ValueError('Guest image SHA256 is required')
    return image


def assemble(installer, extractor, guest_runtime, destination, *, link_immutable=False):
    installer, extractor = Path(installer).resolve(), Path(extractor).resolve()
    source, destination = Path(guest_runtime).resolve(), Path(destination).absolute()
    if destination.exists() or destination.is_symlink():
        raise FileExistsError('Preserve existing runtime: ' + str(destination))
    if digest(installer, 'sha512') != INSTALLER_SHA512: raise ValueError('Installer SHA512 mismatch')
    metadata = (source / 'runtime.json').read_bytes(); spec = json.loads(metadata)
    image = bound_guest(source, spec)
    listed = subprocess.run([str(extractor), 'l', '-slt', str(installer)], check=True,
                            capture_output=True, text=True, encoding='utf-8', timeout=30)
    selected = selected_listing(listed.stdout)
    destination.parent.mkdir(parents=True, exist_ok=True)
    required_space = sum(selected.values()) + (0 if link_immutable else image.stat().st_size) + 64 * 1024 * 1024
    if shutil.disk_usage(destination.parent).free < required_space:
        raise OSError('Insufficient free space; no partial base-image copy started')
    if link_immutable and image.stat().st_dev != destination.parent.stat().st_dev:
        raise OSError('Hardlink requested across filesystems; refusing a giant copy fallback')
    print('Checking immutable guest SHA256 (no course rerun)…', flush=True)
    if digest(image) != spec['image_sha256']: raise ValueError('Source guest image changed')
    destination.mkdir(); qemu = destination / 'qemu'; qemu.mkdir()
    # A UTF-8 list avoids Windows command-line length limits; safe_name rejects
    # newlines, path traversal and Windows aliases before extraction.
    with tempfile.TemporaryDirectory(prefix='shellground-pack-list-') as directory:
        names = Path(directory) / 'members.txt'
        names.write_text('\n'.join(sorted(selected)) + '\n', encoding='utf-8')
        subprocess.run([str(extractor), 'x', '-y', '-bd', '-bb0', '-mmt=2', '-scsUTF-8',
                        '-o' + str(qemu), str(installer), '@' + str(names)], check=True, timeout=300)
    actual = {p.relative_to(qemu).as_posix(): p for p in qemu.rglob('*') if p.is_file()}
    if set(actual) != set(selected): raise ValueError('Extracted member list differs from selected list')
    hashes = {}
    for name, path in actual.items():
        if path.is_symlink() or path.stat().st_size != selected[name]: raise ValueError('Invalid extracted file: ' + name)
        if name.lower().endswith(('.exe', '.dll')): assert_pe_x64(path)
        hashes[name] = digest(path)
    target_image = destination / 'base.qcow2'
    if link_immutable: os.link(image, target_image)
    else: shutil.copy2(image, target_image)
    # Preserve original proof bytes. Original Linux PASS is not a Windows PASS.
    (destination / 'guest-runtime-linux.json').write_bytes(metadata)
    windows_spec = dict(spec, qemu='qemu/qemu-system-x86_64.exe', qemu_img='qemu/qemu-img.exe',
                        image='base.qcow2', firmware='qemu/share', bios='qemu/share/bios-256k.bin',
                        host_platform='windows-x86_64', development_pack=True,
                        windows_validation={'state': 'not-run', 'release_ready': False},
                        guest_evidence={'platform': 'linux-x86_64', 'file': 'guest-runtime-linux.json',
                                        'sha256': hashlib.sha256(metadata).hexdigest()})
    report = dict(schema=1, kind='windows-runtime-assembly', state='assembled-not-host-verified',
                  qemu_url=INSTALLER_URL, qemu_sha512=INSTALLER_SHA512,
                  extractor_sha256=digest(extractor), files=hashes, image_sha256=spec['image_sha256'],
                  guest_metadata_sha256=hashlib.sha256(metadata).hexdigest(),
                  immutable_hardlink=link_immutable, windows_executed=False)
    for name, data in (('runtime.json', windows_spec), ('assembly.json', report)):
        with (destination / name).open('x', encoding='utf-8', newline='\n') as stream:
            json.dump(data, stream, ensure_ascii=False, indent=2); stream.write('\n')
    return {'runtime': str(destination), 'files': len(hashes), 'state': report['state'],
            'image_sha256': spec['image_sha256'], 'windows_executed': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--installer', type=Path, required=True)
    parser.add_argument('--extractor', type=Path, required=True)
    parser.add_argument('--guest-runtime', type=Path, required=True)
    parser.add_argument('--destination', type=Path, required=True)
    parser.add_argument('--link-immutable', action='store_true')
    args = parser.parse_args()
    print(json.dumps(assemble(args.installer, args.extractor, args.guest_runtime, args.destination,
                              link_immutable=args.link_immutable), ensure_ascii=False, indent=2))


if __name__ == '__main__': main()
