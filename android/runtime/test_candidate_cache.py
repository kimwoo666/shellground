import hashlib
from pathlib import Path
import tempfile
import unittest

from candidate_cache import preserve, select


class CandidateCacheTests(unittest.TestCase):
    def test_reboot_missing_build_uses_only_byte_identical_owned_copy(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);staged=root/'staged';staged.write_bytes(b'unit-fixture-not-an-executable')
            expected=hashlib.sha256(staged.read_bytes()).hexdigest();cached=root/'cache'/expected/'qemu'
            result=select(root/'missing-build',cached,[staged],expected)
            self.assertEqual(result,cached);self.assertEqual(cached.read_bytes(),staged.read_bytes())
            staged.unlink()
            self.assertEqual(select(root/'missing-build',cached,[],expected),cached)

    def test_changed_or_missing_artifacts_never_become_a_new_build(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);staged=root/'staged';staged.write_bytes(b'changed')
            with self.assertRaises(ValueError):select(root/'missing',root/'cache',[staged],'a'*64)
            self.assertFalse((root/'cache').exists())
            # Existing incorrect original is not silently replaced by a fallback.
            original=root/'original';original.write_bytes(b'wrong')
            digest=hashlib.sha256(staged.read_bytes()).hexdigest()
            with self.assertRaises(ValueError):select(original,root/'cache',[staged],digest)

    def test_conflicting_cache_and_links_are_preserved(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);original=root/'original';original.write_bytes(b'verified')
            digest=hashlib.sha256(original.read_bytes()).hexdigest();cache=root/'cache';cache.write_bytes(b'conflict')
            with self.assertRaises(ValueError):preserve(original,cache,digest)
            self.assertEqual(cache.read_bytes(),b'conflict')
            link=root/'link';link.symlink_to(original)
            with self.assertRaises(ValueError):preserve(link,root/'new',digest)
            with self.assertRaises(ValueError):preserve(original,link,digest)


if __name__=='__main__':unittest.main()
