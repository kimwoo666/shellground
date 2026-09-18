import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from conda_teaching.validation_progress import checkpoint


class ValidationProgressTests(unittest.TestCase):
    def test_failure_keeps_only_completed_case_evidence_and_blocks_export(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'course.json'
            checkpoint(path,{'fingerprint':'current'},
                       {'passed':['first'],'negative_repair':['repair']},current_problem='first')
            result=checkpoint(path,{'fingerprint':'current'},
                       {'passed':[],'negative_repair':[]},state='failed',current_problem='second',phase='prepare')
            self.assertEqual(result['passed'],['first'])
            self.assertEqual(result['negative_repair'],['repair'])
            self.assertEqual(result['count'],1)
            self.assertFalse(result['fixture_clean'])
            self.assertEqual(json.loads(path.read_text())['phase'],'prepare')

    def test_resume_merges_only_the_same_course_and_learning_sources(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'learning.json'
            identity={'fingerprint':'steps','course_fingerprint':'course'}
            checkpoint(path,identity,{'passed':['first']},state='failed')
            result=checkpoint(path,identity,{'passed':['second']},state='complete')
            self.assertEqual(result['passed'],['first','second'])
            self.assertTrue(result['fixture_clean'])
            changed=checkpoint(path,dict(identity,course_fingerprint='changed'),{'passed':['third']})
            self.assertEqual(changed['passed'],['third'])
            changed=checkpoint(path,dict(identity,fingerprint='changed'),{'passed':[]})
            self.assertEqual(changed['passed'],[])

    def test_new_run_invalidates_previous_clean_flag_until_reset_finishes(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'course.json'
            checkpoint(path,{'fingerprint':'current'},{'passed':['first']},state='complete')
            result=checkpoint(path,{'fingerprint':'current'},{'passed':[]})
            self.assertEqual(result['passed'],['first'])
            self.assertEqual(result['state'],'in_progress')
            self.assertFalse(result['fixture_clean'])

    def test_failed_recheck_does_not_reuse_its_old_pass(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'course.json'
            identity={'fingerprint':'current'}
            checkpoint(path,identity,{'passed':['first']},state='complete')
            result=checkpoint(path,identity,{'passed':[]},invalidate=['first'])
            self.assertEqual(result['passed'],[])
            checkpoint(path,identity,{'passed':[]},state='failed')
            result=checkpoint(path,identity,{'passed':['second']},state='complete')
            self.assertEqual(result['passed'],['second'])
            self.assertEqual(result['count'],1)

    def test_atomic_write_failure_preserves_original_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'course.json'
            checkpoint(path,{'fingerprint':'current'},{'passed':['first']})
            original=path.read_bytes()
            with patch('conda_teaching.validation_progress.os.replace',side_effect=OSError('test failure')):
                with self.assertRaises(OSError):
                    checkpoint(path,{'fingerprint':'current'},{'passed':['second']})
            self.assertEqual(path.read_bytes(),original)
            self.assertEqual(list(Path(directory).iterdir()),[path])


if __name__=='__main__':unittest.main()
