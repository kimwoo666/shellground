import hashlib
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from conda_teaching.shared_shell_carry import baseline_fingerprint, bound, ALLOWED


def synthetic_fingerprint():
    for name in ('guest/bashrc', 'guest/shell_snapshot.py', 'course.json'): pass
    return 'unused'


class CondaSharedShellCarryTests(unittest.TestCase):
    def test_reconstruction_substitutes_only_shell_and_detects_other_course_change(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); (root / 'guest').mkdir()
            original = {n: ('old-' + n).encode() for n in ALLOWED}
            for n in ALLOWED: (root / n).write_bytes(b'changed shell')
            (root / 'course.json').write_bytes(b'unchanged course')
            expected = hashlib.sha256()
            for name in (*ALLOWED, 'course.json'):
                expected.update(name.encode()); expected.update(original.get(name, b'unchanged course'))
            expected.update(b'rc')
            with patch('conda_teaching.shared_shell_carry.source_fingerprint', synthetic_fingerprint), patch('conda_teaching.shared_shell_carry.RC', 'rc'):
                self.assertEqual(baseline_fingerprint(root, original), expected.hexdigest())
                (root / 'course.json').write_bytes(b'new grading')
                self.assertNotEqual(baseline_fingerprint(root, original), expected.hexdigest())

    def test_no_third_file_or_incomplete_baseline_can_be_substituted(self):
        for original in ({}, {ALLOWED[0]: b'x'}, {**{n: b'x' for n in ALLOWED}, 'course.json': b'x'}):
            with self.assertRaises(RuntimeError): baseline_fingerprint(Path('/tmp'), original)

    def test_bound_evidence_fails_on_mutation_or_path_escape(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); path = root / 'proof.json'; path.write_bytes(b'proof')
            record = dict(file='proof.json', sha256=hashlib.sha256(b'proof').hexdigest())
            self.assertEqual(bound(root, record), path)
            path.write_bytes(b'edited proof')
            with self.assertRaises(RuntimeError): bound(root, record)
            for name in ('', '../proof.json', '/tmp/proof.json'):
                with self.assertRaises(RuntimeError): bound(root, dict(record, file=name))


if __name__ == '__main__': unittest.main()
