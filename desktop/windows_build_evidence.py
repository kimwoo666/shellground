"""Carry immutable Linux guest teaching proof into a Windows build candidate.

This does not certify Windows execution. Original Conda proofs are validated
at their original paths, then bound byte-for-byte to the transported guest.
"""
import json
from pathlib import Path

from conda_teaching.shared_shell_carry import bound, digest, validate as validate_linux_carry
from real_vm import runtime_info
from windows_runtime_pack import INSTALLER_SHA512, assert_pe_x64


def validate_guest_carry(review_path, runtime, root):
    root, runtime = Path(root).resolve(), Path(runtime).resolve()
    review = json.loads(Path(review_path).read_text(encoding='utf-8'))
    original_metadata = bound(root, review['runtime_metadata'])
    # No change to the original narrow two-file carry gate.
    teaching = validate_linux_carry(review_path, original_metadata.parent, root)
    _, spec = runtime_info(runtime)
    if spec.get('host_platform') != 'windows-x86_64':
        raise RuntimeError('A Windows x64 runtime candidate is required')
    reference = spec.get('guest_evidence', {})
    if reference.get('platform') != 'linux-x86_64':
        raise RuntimeError('Guest proof must retain its original Linux platform')
    copied_metadata = bound(runtime, reference)
    if copied_metadata.read_bytes() != original_metadata.read_bytes():
        raise RuntimeError('Guest proof differs from the original Linux runtime')
    original = json.loads(original_metadata.read_text(encoding='utf-8'))
    # Host paths differ. Provisioning and all inherited teaching proof must not.
    host_fields = {'qemu', 'qemu_img', 'image', 'development_pack'}
    for field, value in original.items():
        if field not in host_fields and spec.get(field) != value:
            raise RuntimeError('Inherited guest field changed: ' + field)
    assembly = json.loads((runtime / 'assembly.json').read_text(encoding='utf-8'))
    if (assembly.get('schema') != 1 or assembly.get('kind') != 'windows-runtime-assembly' or
            assembly.get('qemu_sha512') != INSTALLER_SHA512 or
            assembly.get('image_sha256') != original.get('image_sha256') or
            assembly.get('guest_metadata_sha256') != digest(original_metadata)):
        raise RuntimeError('Runtime assembly identity differs from carried guest proof')
    assets = assembly.get('files')
    if not isinstance(assets, dict) or not assets: raise RuntimeError('Missing Windows QEMU asset inventory')
    qemu_root = runtime / 'qemu'
    for name, checksum in assets.items():
        bound(qemu_root, {'file': name, 'sha256': checksum})
    for field in ('qemu', 'qemu_img', 'bios'):
        actual = (runtime / spec[field]).resolve()
        if not actual.is_relative_to(qemu_root.resolve()): raise RuntimeError('QEMU asset outside inventory: ' + field)
        if actual.relative_to(qemu_root.resolve()).as_posix() not in assets:
            raise RuntimeError('QEMU entry point is not in the assembly inventory: ' + field)
        if field != 'bios': assert_pe_x64(actual)
    # This checks transport/storage integrity; it doesn't repeat any lesson.
    if digest(runtime / spec['image']) != original['image_sha256']:
        raise RuntimeError('Transported guest disk differs from the verified immutable base')
    return dict(teaching, basis='linux-guest-teaching-carry', windows_executed=False,
                windows_release_ready=False, transported_image_sha256=original['image_sha256'],
                windows_assets_checked=len(assets))
