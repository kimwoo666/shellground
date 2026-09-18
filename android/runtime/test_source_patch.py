"""Check the stored Android patch against pristine, pinned upstream members."""
import hashlib
import json
from pathlib import Path
import subprocess
import tarfile
import tempfile
import unittest

RUNTIME = Path(__file__).resolve().parent
NATIVE = RUNTIME.parent / '.native-runtime'
SPEC = json.loads((RUNTIME / 'native-sources.json').read_text())['qemu']
ARCHIVE = NATIVE / 'downloads' / SPEC['archive']


@unittest.skipUnless(ARCHIVE.is_file(), 'Requires locally downloaded official QEMU source')
class SourcePatchTests(unittest.TestCase):
    def test_exact_patch_on_original_source_matches_build_input(self):
        with ARCHIVE.open('rb') as stream:
            self.assertEqual(hashlib.file_digest(stream, 'sha256').hexdigest(), SPEC['sha256'])
        prefix = 'qemu-' + SPEC['version']
        members = ('meson.build', 'util/oslib-posix.c')
        with tempfile.TemporaryDirectory(prefix='shellground-patch-test-') as folder:
            root = Path(folder)
            with tarfile.open(ARCHIVE) as archive:
                for member in members:
                    target = root / member
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(archive.extractfile(prefix + '/' + member).read())
            patch = RUNTIME / 'patches/0001-android-shared-memory.patch'
            result = subprocess.run(['patch', '-p1', '--fuzz=0', '--batch', '--forward', '-i', str(patch)],
                                    cwd=root, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            for member in members:
                self.assertEqual((root / member).read_bytes(), (NATIVE / prefix / member).read_bytes(), member)


if __name__ == '__main__':
    unittest.main()
