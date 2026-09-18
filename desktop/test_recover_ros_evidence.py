import json
from pathlib import Path
import tempfile
import unittest
from recover_ros_evidence import recover


class RecoverRosEvidenceTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(); self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name); self.transcript = self.root / 'event.jsonl'; self.target = self.root / 'recovered.json'
        self.summary = dict(state='failed', source_fingerprint='a' * 64, failures={'ros_play:1': 'fewer messages'},
                            vm_stopped=True, overlay_removed=True)

    def write(self, pass_lines='ROS_COURSE_PASS ros_play:0', count=1, duplicate=False):
        record = dict(type='event_msg', timestamp='2026-09-18', ordinal=1, payload=dict(item=dict(
            type='CommandExecution', process_id='77', status='failed', aggregated_output=pass_lines + '\n' + json.dumps(self.summary) + f' passed={count}/3\n')))
        self.transcript.write_text(json.dumps(record) + '\n' + (json.dumps(record) + '\n' if duplicate else ''))

    def test_recovery_retains_old_failure_and_source_stamp_without_rerunning_or_overwriting(self):
        self.write(); recover(self.transcript, '77', self.target)
        result = json.loads(self.target.read_text())
        self.assertEqual(result['state'], 'failed')
        self.assertEqual(result['source_fingerprint'], 'a' * 64)
        self.assertEqual(result['passed'], ['ros_play:0'])
        self.assertEqual(result['original_expected_count'], 3)
        self.assertIn('ros_play:1', result['failures'])
        self.assertIn('not-a-new-run', result['scope'])
        with self.assertRaises(FileExistsError): recover(self.transcript, '77', self.target)

    def test_count_mismatch_duplicate_pass_or_ambiguous_event_is_rejected(self):
        for kwargs in ({'count': 2}, {'pass_lines': 'ROS_COURSE_PASS ros_play:0\nROS_COURSE_PASS ros_play:0', 'count': 2}, {'duplicate': True}):
            self.write(**kwargs)
            with self.subTest(kwargs=kwargs), self.assertRaises(RuntimeError): recover(self.transcript, '77', self.target)
            self.assertFalse(self.target.exists())

    def test_missing_cleanup_or_wrong_event_is_not_evidence(self):
        self.summary['vm_stopped'] = False; self.write()
        for process in ('77', 'other'):
            with self.assertRaises(RuntimeError): recover(self.transcript, process, self.target)


if __name__ == '__main__': unittest.main()
