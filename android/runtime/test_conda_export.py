from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import export_conda_guest as exporter
from conda_teaching.export_runtime import ANSWER_CASES


class ArmCondaExportTests(unittest.TestCase):
    def setUp(self):
        self.spec = json.loads((exporter.DESKTOP / 'conda_teaching/course_spec.json').read_text())
        self.provision = {'installer_sha256': exporter.SPEC['sha256'], 'subdir': 'linux-aarch64',
                          'offline': True, 'smoke': 'CONDA_REAL_OFFLINE_CREATE_ACTIVATE_INSTALL_UPDATE_EXPORT_RECREATE_REMOVE_OK'}
        # Synthetic gate fixtures, NOT execution evidence. Never saved as reports.
        self.course = {'guest_architecture': 'aarch64', 'fingerprint': 'course', 'count': 54,
                       'passed': [p['id'] for u in self.spec['units'] for p in u['problems']],
                       'negative_repair': ['conda_activate_example', 'conda_install_example',
                                          'conda_export_intent_example', 'conda_update_preserve'],
                       'answer_cases': sorted(ANSWER_CASES)}
        self.learning = {'count': 18, 'passed': [u['key'] for u in self.spec['units']],
                         'course_fingerprint': 'course', 'fingerprint': 'steps'}

    def validate(self):
        exporter.validate_proofs(self.provision, self.course, self.learning, self.spec, 'course', 'steps')

    def test_all_current_arm_gates(self):
        self.validate()

    def test_x86_or_missing_architecture_is_not_arm_proof(self):
        for arch in ('x86_64', None):
            with self.subTest(arch=arch):
                self.course['guest_architecture'] = arch
                with self.assertRaises(ValueError): self.validate()

    def test_wrong_installer_subdir_or_smoke_is_rejected(self):
        original = deepcopy(self.provision)
        for key, value in (('installer_sha256', 'wrong'), ('subdir', 'linux-64'), ('offline', False), ('smoke', 'PASS')):
            with self.subTest(key=key):
                self.provision = dict(original, **{key: value})
                with self.assertRaises(ValueError): self.validate()

    def test_partial_and_stale_reports_do_not_unlock_export(self):
        self.course['passed'].pop()
        with self.assertRaises(RuntimeError): self.validate()
        self.setUp(); self.learning['fingerprint'] = 'old'
        with self.assertRaises(RuntimeError): self.validate()

    def test_existing_destination_is_preserved_before_reading_reports(self):
        with tempfile.TemporaryDirectory() as folder:
            destination = Path(folder) / 'existing'; destination.mkdir()
            marker = destination / 'preserve.txt'; marker.write_text('keep')
            with patch.object(exporter.subprocess, 'run') as run:
                with self.assertRaises(ValueError): exporter.export(destination)
                run.assert_not_called()
            self.assertEqual(marker.read_text(), 'keep')


if __name__ == '__main__':
    unittest.main()
