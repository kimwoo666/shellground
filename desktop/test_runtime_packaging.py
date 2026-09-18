import tempfile
from pathlib import Path
import unittest
from runtime_packaging import copy_runtime_pack


class RuntimePackagingTests(unittest.TestCase):
    def test_explicit_immutable_links_save_space_and_atomic_update_preserves_old_reader(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); source = root / 'source'; target = root / 'target'
            (source / 'nested').mkdir(parents=True)
            old = source / 'nested/base.qcow2'; old.write_bytes(b'old immutable base')
            copy_runtime_pack(source, target, link_immutable=True)
            bundled = target / 'nested/base.qcow2'
            self.assertEqual(old.stat().st_ino, bundled.stat().st_ino)
            replacement = source / 'nested/replacement'; replacement.write_bytes(b'new immutable base image')
            replacement.replace(old)
            self.assertEqual(bundled.read_bytes(), b'old immutable base')
            copy_runtime_pack(source, target, link_immutable=True)
            self.assertEqual(old.stat().st_ino, bundled.stat().st_ino)
            self.assertEqual(bundled.read_bytes(), b'new immutable base image')

    def test_link_failure_does_not_fall_back_to_full_copy_or_damage_existing_file(self):
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); source = root / 'source'; target = root / 'target'
            source.mkdir(); target.mkdir()
            (source / 'base.qcow2').write_bytes(b'new source base')
            (target / 'base.qcow2').write_bytes(b'old')
            with patch('runtime_packaging.os.link', side_effect=OSError('cross device')):
                with self.assertRaises(OSError): copy_runtime_pack(source, target, link_immutable=True)
            self.assertEqual((target / 'base.qcow2').read_bytes(), b'old')
            self.assertEqual(list(target.iterdir()), [target / 'base.qcow2'])

    def test_already_exported_into_bundle_is_not_copied_or_replaced(self):
        with tempfile.TemporaryDirectory() as directory:
            pack = Path(directory) / 'runtime'
            (pack / 'usr').mkdir(parents=True)
            image = pack / 'base.qcow2'
            image.write_bytes(b'immutable image')
            (pack / 'usr/library').write_bytes(b'library')
            (pack / 'usr/library.so').symlink_to('library')
            inode = image.stat().st_ino
            copy_runtime_pack(pack, pack)
            self.assertEqual(image.stat().st_ino, inode)
            self.assertEqual(image.read_bytes(), b'immutable image')
            self.assertTrue((pack / 'usr/library.so').is_symlink())

    def test_repeated_packaging_preserves_links_and_files(self):
        with tempfile.TemporaryDirectory() as directory:
            source, target = Path(directory) / 'source', Path(directory) / 'target'
            source.mkdir()
            (source / 'library').write_bytes(b'fixture')
            (source / 'library.so').symlink_to('library')
            copy_runtime_pack(source, target)
            copy_runtime_pack(source, target)
            self.assertTrue((target / 'library.so').is_symlink())
            self.assertEqual((target / 'library.so').read_bytes(), b'fixture')

    def test_never_copies_through_a_destination_symlink(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / 'source'
            source.mkdir()
            (source / 'file').write_text('new')
            original = root / 'original'
            original.write_text('preserve')
            target = root / 'target'
            target.mkdir()
            (target / 'file').symlink_to(original)
            with self.assertRaises(ValueError):
                copy_runtime_pack(source, target)
            self.assertEqual(original.read_text(), 'preserve')
