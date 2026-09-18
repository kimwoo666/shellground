"""The new evidence gate only; no actual course or VM is re-executed."""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import incremental_acceptance as gate


class IncrementalAcceptanceTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(); self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name); self.reports = self.root / 'proof'; self.reports.mkdir()
        (self.root / 'missions.py').write_text('version = 2\n')
        self.expected = {'unit:0', 'checkpoint-new'}
        self.patch = patch.object(gate, 'definitions', return_value=(self.expected, {'new_review:0': 'checkpoint-new'}))
        self.patch.start(); self.addCleanup(self.patch.stop)
        self.old = dict(state='complete', source_fingerprint='a' * 64, expected=['unit:0'],
                        passed={'unit:0': {'seconds': 1}}, failures={}, vm_stopped=True, overlay_removed=True,
                        negative=sorted(gate.ROS_NEGATIVE))
        self.new = dict(state='complete', source_hashes={'missions.py': gate.digest(self.root / 'missions.py')},
                        passed=['new_review:0'], failures=[], vm_stopped=True, overlay_removed=True)
        self.old_binding = self.write('old.json', self.old)
        self.new_binding = self.write('new.json', self.new)
        (self.reports / 'review.md').write_text('Reviewed unchanged legacy unit; only new review added.\n')
        self.manifest = dict(schema=1, kind='reviewed-incremental-course-evidence',
            source_snapshot=gate.source_snapshot(self.root), expected=sorted(self.expected), requires_fresh=['checkpoint-new'],
            review=dict(file='review.md', sha256=gate.digest(self.reports / 'review.md')),
            evidence=[dict(self.old_binding, cases=['unit:0'], basis='reviewed-carry',
                           reason='The old unit was reviewed and its grading behavior is unchanged.'),
                      dict(self.new_binding, cases=['new_review:0'], basis='current')])

    def write(self, name, value):
        path = self.reports / name; path.write_text(json.dumps(value))
        return dict(file=name, sha256=gate.digest(path))

    def validate(self, manifest=None):
        return gate.validate(self.manifest if manifest is None else manifest, self.reports, self.root)

    def replace_report(self, index, report):
        entry = self.manifest['evidence'][index]
        entry.update(self.write(entry['file'], report))

    def test_current_delta_and_explicit_old_baseline_combine_without_rewriting_reports(self):
        before = [(self.reports / n).read_bytes() for n in ('old.json', 'new.json')]
        result = self.validate()
        self.assertEqual((result['registered'], result['current'], result['reviewed_carry']), (2, 1, 1))
        self.assertFalse(result['reran_entire_course'])
        self.assertEqual(before, [(self.reports / n).read_bytes() for n in ('old.json', 'new.json')])

    def test_missing_duplicate_unknown_and_unpassed_cases_block(self):
        variants = []
        value = deepcopy(self.manifest); value['evidence'].pop(); variants.append(value)
        value = deepcopy(self.manifest); value['evidence'].append(value['evidence'][0]); variants.append(value)
        value = deepcopy(self.manifest); value['evidence'][0]['cases'] = ['unit:1']; variants.append(value)
        value = deepcopy(self.manifest); value['expected'].append('unit:1'); variants.append(value)
        for value in variants:
            with self.subTest(value=value), self.assertRaises(RuntimeError): self.validate(value)

    def test_changed_sources_or_evidence_or_review_require_new_review(self):
        for path in (self.root / 'missions.py', self.reports / 'old.json', self.reports / 'review.md'):
            before = path.read_bytes(); path.write_bytes(before + b'\n')
            with self.subTest(path=path), self.assertRaises(RuntimeError): self.validate()
            path.write_bytes(before)

    def test_new_source_file_also_invalidates_snapshot(self):
        (self.root / 'new_course.py').write_text('new = True\n')
        with self.assertRaises(RuntimeError): self.validate()

    def test_old_report_cannot_be_relabelled_as_current(self):
        self.manifest['evidence'][0]['basis'] = 'current'
        with patch('verify_real_course.fingerprint', return_value='b' * 64), self.assertRaises(RuntimeError): self.validate()

    def test_changed_case_cannot_be_satisfied_by_carry_forward(self):
        self.manifest['requires_fresh'].append('unit:0')
        with self.assertRaisesRegex(RuntimeError, 'Changed cases'): self.validate()

    def test_change_review_cannot_be_omitted(self):
        self.manifest.pop('requires_fresh')
        with self.assertRaisesRegex(RuntimeError, 'changed-case review'): self.validate()

    def test_carry_requires_concrete_explanation_and_original_provenance(self):
        self.manifest['evidence'][0]['reason'] = 'OK'
        with self.assertRaises(RuntimeError): self.validate()
        self.manifest['evidence'][0]['reason'] = 'The old case is unchanged after the documented review.'
        self.old.pop('source_fingerprint'); self.replace_report(0, self.old)
        with self.assertRaises(RuntimeError): self.validate()

    def test_live_or_unclean_or_inconsistent_report_blocks(self):
        for changes in ({'state': 'in_progress'}, {'vm_stopped': False}, {'overlay_removed': False},
                        {'failures': ['some failure']}):
            self.replace_report(1, dict(self.new, **changes))
            with self.subTest(changes=changes), self.assertRaises(RuntimeError): self.validate()

    def test_partial_old_success_requires_explicit_review_and_cannot_include_failed_case(self):
        self.old.update(state='cancelled', failures={'unit:1': 'interrupted'})
        self.replace_report(0, self.old)
        with self.assertRaises(RuntimeError): self.validate()
        self.manifest['evidence'][0]['partial_review'] = 'The later case was interrupted; earlier recorded success is retained.'
        self.validate()
        self.old['failures']['unit:0'] = 'also failed'; self.replace_report(0, self.old)
        with self.assertRaises(RuntimeError): self.validate()

    def test_missing_negative_recovery_proof_blocks(self):
        self.old['negative'] = []; self.replace_report(0, self.old)
        with self.assertRaisesRegex(RuntimeError, 'negative/recovery'): self.validate()

    def test_path_escape_symlink_and_review_binding_are_rejected(self):
        for name in ('../outside.json', '/tmp/proof.json'):
            value = deepcopy(self.manifest); value['evidence'][0]['file'] = name
            with self.subTest(name=name), self.assertRaises(RuntimeError): self.validate(value)
        outside = self.root / 'outside.json'; outside.write_text(json.dumps(self.old))
        (self.reports / 'link.json').symlink_to(outside)
        self.manifest['evidence'][0].update(file='link.json', sha256=gate.digest(outside))
        with self.assertRaises(RuntimeError): self.validate()

    def test_inventory_is_not_a_release_approval(self):
        result = gate.inventory([self.reports / 'old.json'])
        self.assertFalse(result['accepted'])
        self.assertEqual(result['missing'], ['checkpoint-new'])

    def test_directory_prefers_manifest_and_never_falls_back_after_a_failure(self):
        from real_acceptance import validate_directory
        path = self.reports / 'incremental-course-manifest.json'; path.write_text('{}')
        with patch.object(gate, 'validate_file', return_value={'current': 1}) as validator:
            self.assertEqual(validate_directory(self.reports), {'current': 1})
            validator.assert_called_once_with(path)
        with patch.object(gate, 'validate_file', side_effect=RuntimeError('invalid proof')):
            with self.assertRaisesRegex(RuntimeError, 'invalid proof'): validate_directory(self.reports)


if __name__ == '__main__': unittest.main()
