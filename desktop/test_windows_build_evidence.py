import hashlib
import json
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import patch

import windows_build_evidence as proof
from windows_runtime_pack import INSTALLER_SHA512


class WindowsGuestCarryTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(); self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.original = self.root / 'linux'; self.original.mkdir()
        self.runtime = self.root / 'windows'; self.runtime.mkdir()
        qemu = self.runtime / 'qemu'; (qemu / 'share').mkdir(parents=True)
        (self.runtime / 'base.qcow2').write_bytes(b'immutable test fixture')
        self.spec = dict(protocol=1, provisioned=True, image='base.qcow2',
                         qemu='usr/bin/qemu-system-x86_64', qemu_img='usr/bin/qemu-img',
                         image_sha256=proof.digest(self.runtime / 'base.qcow2'),
                         conda_course=True, conda_validation={'kind': 'original-Linux-only'})
        self.write(self.original / 'runtime.json', self.spec)
        metadata = (self.original / 'runtime.json').read_bytes()
        (self.runtime / 'guest-runtime-linux.json').write_bytes(metadata)
        metadata_sha = hashlib.sha256(metadata).hexdigest()
        self.review = self.root / 'review.json'
        self.write(self.review, {'runtime_metadata': {'file': 'linux/runtime.json', 'sha256': metadata_sha}})
        image = bytearray(128); image[:2] = b'MZ'; struct.pack_into('<I', image, 60, 80)
        image[80:86] = b'PE\0\0\x64\x86'
        for name in ('qemu-system-x86_64.exe', 'qemu-img.exe'): (qemu / name).write_bytes(image)
        (qemu / 'share/bios.bin').write_bytes(b'firmware')
        self.windows = dict(self.spec, qemu='qemu/qemu-system-x86_64.exe', qemu_img='qemu/qemu-img.exe',
                            host_platform='windows-x86_64', firmware='qemu/share', bios='qemu/share/bios.bin',
                            guest_evidence={'platform': 'linux-x86_64', 'file': 'guest-runtime-linux.json', 'sha256': metadata_sha})
        self.write(self.runtime / 'runtime.json', self.windows)
        self.assembly = dict(schema=1, kind='windows-runtime-assembly', qemu_sha512=INSTALLER_SHA512,
                             image_sha256=self.spec['image_sha256'], guest_metadata_sha256=metadata_sha,
                             files={p.relative_to(qemu).as_posix(): proof.digest(p) for p in qemu.rglob('*') if p.is_file()})
        self.write(self.runtime / 'assembly.json', self.assembly)
        self.validate_linux = self.enterContext(patch('windows_build_evidence.validate_linux_carry',
                                                     return_value={'course_cases': 60}))

    def write(self, path, value): path.write_text(json.dumps(value), encoding='utf-8')
    def validate(self): return proof.validate_guest_carry(self.review, self.runtime, self.root)

    def test_original_proof_is_validated_and_does_not_become_windows_success(self):
        result = self.validate()
        self.validate_linux.assert_called_once_with(self.review, self.original, self.root)
        self.assertEqual(result['basis'], 'linux-guest-teaching-carry')
        self.assertIs(result['windows_executed'], False)
        self.assertIs(result['windows_release_ready'], False)
        self.assertEqual(result['windows_assets_checked'], 3)

    def test_original_gate_failure_cannot_be_bypassed_by_a_windows_pack(self):
        self.validate_linux.side_effect = RuntimeError('Original source changed')
        with self.assertRaisesRegex(RuntimeError, 'Original source changed'): self.validate()

    def test_changed_disk_or_qemu_asset_does_not_inherit_guest_pass(self):
        for relative in ('base.qcow2', 'qemu/qemu-img.exe'):
            path = self.runtime / relative; original = path.read_bytes(); path.write_bytes(b'changed')
            try:
                with self.assertRaises(RuntimeError): self.validate()
            finally: path.write_bytes(original)

    def test_relabelled_proof_and_changed_conda_fields_fail(self):
        for update in ({'host_platform': 'linux-x86_64'}, {'conda_course': False},
                       {'conda_validation': {'kind': 'invented-PASS'}},
                       {'guest_evidence': dict(self.windows['guest_evidence'], platform='windows-x86_64')}):
            self.write(self.runtime / 'runtime.json', dict(self.windows, **update))
            with self.assertRaises(RuntimeError): self.validate()

    def test_inventory_cannot_omit_or_escape_entrypoints(self):
        for files in ({'share/bios.bin': self.assembly['files']['share/bios.bin']},
                      {'../../linux/runtime.json': proof.digest(self.original / 'runtime.json')}):
            self.write(self.runtime / 'assembly.json', dict(self.assembly, files=files))
            with self.assertRaises(RuntimeError): self.validate()


if __name__ == '__main__': unittest.main()
