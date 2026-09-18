import json
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import patch

import windows_runtime_pack as pack


class WindowsPackTests(unittest.TestCase):
    def test_archive_paths_cannot_escape_or_alias_windows_names(self):
        for name in ('../outside', '/outside', 'C:/outside', 'a\\b', 'a//b', 'a/./b',
                     'share/NUL.txt', 'share/com1', 'a. /b', 'a./b', 'line\nbreak', 'a\0b'):
            with self.subTest(name=name), self.assertRaises(ValueError): pack.safe_name(name)
        self.assertEqual(pack.safe_name('share/doc/한글 파일.txt'), 'share/doc/한글 파일.txt')

    def test_only_required_x64_tools_dlls_firmware_and_docs_are_selected(self):
        files = {name: 10 for name in pack.REQUIRED}
        files.update({'other-machine.exe': 90, '$PLUGINSDIR/plugin.dll': 30,
                      'libglib-2.0-0.dll': 50, 'share/doc/license.html': 20})
        listing = 'Path = installer.exe\n\n----------\n' + '\n\n'.join(
            f'Path = {name}\nSize = {size}' for name, size in files.items())
        result = pack.selected_listing(listing)
        self.assertEqual(set(result), pack.REQUIRED | {'libglib-2.0-0.dll', 'share/doc/license.html'})
        with self.assertRaises(ValueError): pack.selected_listing(listing + '\n\nPath = COPYING\nSize = 2')
        with self.assertRaises(ValueError): pack.selected_listing('----------\nPath = qemu-img.exe\nSize = 0')

    def test_linux_elf_and_windows_32bit_are_not_labelled_windows_x64(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'qemu.exe'
            for data in (b'\x7fELF' + bytes(100), b'MZ' + bytes(100)):
                path.write_bytes(data)
                with self.assertRaises(ValueError): pack.assert_pe_x64(path)
            data = bytearray(128); data[:2] = b'MZ'; struct.pack_into('<I', data, 60, 80)
            data[80:86] = b'PE\0\0\x4c\x01'; path.write_bytes(data)
            with self.assertRaises(ValueError): pack.assert_pe_x64(path)
            data[84:86] = b'\x64\x86'; path.write_bytes(data); pack.assert_pe_x64(path)

    def test_guest_metadata_cannot_point_outside_source(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); (root / 'base.qcow2').write_bytes(b'original')
            spec = dict(protocol=1, provisioned=True, image='base.qcow2', image_sha256='a' * 64)
            self.assertEqual(pack.bound_guest(root, spec), root / 'base.qcow2')
            for changes in ({'image': '../base.qcow2'}, {'image_sha256': ''}, {'provisioned': False}):
                with self.assertRaises(ValueError): pack.bound_guest(root, dict(spec, **changes))

    def test_existing_pack_and_mismatched_installer_are_never_overwritten(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); original = root / 'keep'; original.mkdir()
            (original / 'personal.txt').write_text('keep')
            with self.assertRaises(FileExistsError): pack.assemble('missing', 'missing', root, original)
            with patch('windows_runtime_pack.digest', return_value='wrong'):
                with self.assertRaisesRegex(ValueError, 'SHA512'): pack.assemble('missing', 'missing', root, root / 'new')
            self.assertFalse((root / 'new').exists())
            self.assertEqual((original / 'personal.txt').read_text(), 'keep')

    def test_real_runtime_checks_optional_windows_firmware_and_utf8_metadata(self):
        from engine import LabError
        from real_vm import runtime_info
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); (root / 'share').mkdir()
            for name in ('qemu.exe', 'qemu-img.exe', 'base.qcow2', 'share/bios.bin'):
                (root / name).write_bytes(b'fixture')
            spec = dict(protocol=1, provisioned=True, qemu='qemu.exe', qemu_img='qemu-img.exe',
                        image='base.qcow2', firmware='share', bios='share/bios.bin', label='학습')
            metadata = root / 'runtime.json'
            metadata.write_text(json.dumps(spec, ensure_ascii=False), encoding='utf-8')
            self.assertEqual(runtime_info(root)[1]['label'], '학습')
            for changed in ({'firmware': '..'}, {'bios': '../outside'}, {'firmware': 'qemu.exe'}):
                metadata.write_text(json.dumps(dict(spec, **changed)), encoding='utf-8')
                with self.assertRaises(LabError): runtime_info(root)


if __name__ == '__main__': unittest.main()
