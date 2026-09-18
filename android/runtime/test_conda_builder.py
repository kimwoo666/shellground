from contextlib import redirect_stdout
import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import build_conda_guest as builder


class ArmCondaBuilderTests(unittest.TestCase):
    def test_existing_installer_must_match_pin_without_download(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);payload=b'unit-test-fixture-not-an-installer'
            spec={'name':'installer.sh','sha256':hashlib.sha256(payload).hexdigest(),'url':'https://example.invalid/fixture'}
            target=root/'installer.sh';target.write_bytes(payload)
            with patch.object(builder,'BUILD',root),patch.object(builder,'SPEC',spec),patch.object(builder.subprocess,'run') as run:
                self.assertEqual(builder.installer(),target);run.assert_not_called()
                target.write_bytes(b'changed')
                with self.assertRaises(ValueError):builder.installer(download=True)
                run.assert_not_called();self.assertEqual(target.read_bytes(),b'changed')

    def test_symlinked_installer_is_not_accepted(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);(root/'other').write_bytes(b'fixture');(root/'installer.sh').symlink_to('other')
            spec={'name':'installer.sh','sha256':hashlib.sha256(b'fixture').hexdigest()}
            with patch.object(builder,'BUILD',root),patch.object(builder,'SPEC',spec):
                with self.assertRaises(ValueError):builder.installer()
            self.assertEqual((root/'other').read_bytes(),b'fixture')

    def test_arm_build_and_reports_are_separate_from_existing_x86_pack(self):
        self.assertIn('conda-arm64',str(builder.BUILD))
        self.assertNotEqual(builder.BUILD,builder.DESKTOP/'.conda-build')
        self.assertEqual(builder.SPEC['architecture'],'aarch64')
        self.assertEqual(builder.SPEC['subdir'],'linux-aarch64')
        self.assertEqual(builder.PACK.name,'android-pack-v1')

    def test_diagnostic_is_separate_from_success_reports(self):
        fixture={'kind':'read-only-arm-conda-diagnostic-not-validation','installed':True,'environments':{}}
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            with redirect_stdout(io.StringIO()),patch.object(builder,'BUILD',root),patch.object(builder,'guest_exec',return_value=json.dumps(fixture)) as execute:
                builder.diagnose(object())
            self.assertEqual(json.loads((root/'diagnostic.json').read_text()),fixture)
            self.assertEqual([path.name for path in root.iterdir()],['diagnostic.json'])
            script=execute.call_args.args[1][2]
            self.assertNotIn('write_text',script);self.assertNotIn('unlink',script);self.assertNotIn('subprocess',script)

    def test_progress_script_compiles_and_reads_bounded_live_log(self):
        with tempfile.TemporaryDirectory() as folder:
            # Mocked output is not actual ARM provisioning proof. Capture it so
            # the unit-test console cannot be mistaken for a real VM result.
            with redirect_stdout(io.StringIO()),patch.object(builder,'BUILD',Path(folder)),patch.object(builder,'guest_exec',side_effect=[
                '',json.dumps({'exit':'0','tail':'unit-only observation'}),json.dumps({'subdir':'linux-aarch64'})]) as execute:
                builder.provision(object())
            script=execute.call_args_list[1].args[1][2]
            compile(script,'<guest progress>','exec')
            self.assertIn('read_tail(output,3000)',script)
            self.assertIn('Unexpected smoke progress link',script)

    def test_invalid_archive_journal_is_rejected_before_guest_mutation(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);(root/'smoke-archives.json').write_text('{}')
            with patch.object(builder,'BUILD',root),patch.object(builder,'guest_exec') as execute:
                with self.assertRaises(ValueError):builder.archive_smoke_fixtures(object())
                execute.assert_not_called()

    def test_archive_journal_preserves_previous_entries(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);prior={'destination':'/unit-test/old'};current={'destination':'/unit-test/new'}
            (root/'smoke-archives.json').write_text(json.dumps([prior]))
            with redirect_stdout(io.StringIO()),patch.object(builder,'BUILD',root),patch.object(builder,'guest_exec',side_effect=['',json.dumps(current)]):
                builder.archive_smoke_fixtures(object())
            self.assertEqual(json.loads((root/'smoke-archives.json').read_text()),[prior,current])


if __name__=='__main__':unittest.main()
