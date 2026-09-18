import json
from pathlib import Path
import tempfile
import unittest
from conda_teaching.archive_smoke import EXPECTED, archive_failed_smoke


class SmokeArchiveTests(unittest.TestCase):
    def fixture(self, root):
        state=root/'state';state.mkdir();envs=root/'envs';envs.mkdir()
        (state/'conda-provision-exit').write_text('1\n')
        (state/'conda-provision.log').write_text('TimeoutExpired: /mnt/sg-conda/runtime_smoke.sh')
        for name, command in EXPECTED.items():
            meta=envs/name/'conda-meta';meta.mkdir(parents=True)
            (meta/'history').write_text(command+'\n')
            (envs/name/'keep.txt').write_text('original '+name)
        return state,envs,root/'archives'

    def test_moves_only_verified_fixtures_and_keeps_their_files(self):
        with tempfile.TemporaryDirectory() as folder:
            state,envs,archives=self.fixture(Path(folder))
            other=envs/'unrelated';other.mkdir();(other/'keep').write_text('untouched')
            result=archive_failed_smoke(state,envs,archives)
            self.assertEqual(result['kind'],'preserved-smoke-fixtures-not-validation')
            destination=Path(result['destination'])
            self.assertEqual(json.loads((destination/'archive.json').read_text()),result)
            for item in result['items']:
                self.assertTrue(item['moved']);self.assertFalse(Path(item['source']).exists())
                self.assertEqual((destination/item['name']/'keep.txt').read_text(),'original '+item['name'])
            self.assertEqual((other/'keep').read_text(),'untouched')

    def test_validates_both_histories_before_moving_either(self):
        with tempfile.TemporaryDirectory() as folder:
            state,envs,archives=self.fixture(Path(folder))
            (envs/'sg-copy/conda-meta/history').write_text('a different experiment')
            with self.assertRaises(ValueError):archive_failed_smoke(state,envs,archives)
            self.assertFalse(archives.exists());self.assertTrue((envs/'sg-proof/keep.txt').exists())

    def test_success_or_unrelated_failure_is_not_archived(self):
        for code,log in [('0','TimeoutExpired: /mnt/sg-conda/runtime_smoke.sh'),('1','unrelated error')]:
            with self.subTest(code=code,log=log),tempfile.TemporaryDirectory() as folder:
                state,envs,archives=self.fixture(Path(folder))
                (state/'conda-provision-exit').write_text(code);(state/'conda-provision.log').write_text(log)
                with self.assertRaises(ValueError):archive_failed_smoke(state,envs,archives)
                self.assertFalse(archives.exists());self.assertTrue((envs/'sg-proof/keep.txt').exists())

    def test_links_are_rejected_without_touching_target(self):
        with tempfile.TemporaryDirectory() as folder:
            state,envs,archives=self.fixture(Path(folder))
            original=envs/'sg-proof';original.rename(envs/'outside')
            original.symlink_to(envs/'outside',target_is_directory=True)
            with self.assertRaises(ValueError):archive_failed_smoke(state,envs,archives)
            self.assertFalse(archives.exists());self.assertTrue((envs/'outside/keep.txt').exists())


if __name__=='__main__':unittest.main()
