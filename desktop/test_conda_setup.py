"""Local negative/identity tests; actual installation has a separate VM test."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from conda_teaching import setup_runtime as runtime


class SetupGraderTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();root=Path(self.temp.name)
        self.work=root/'work';self.work.mkdir();self.target=self.work/'miniconda-test'
        self.base=root/'base';(self.base/'bin').mkdir(parents=True)
        (self.base/'bin/python').write_bytes(b'ELF real python fixture')
        (self.base/'bin/conda').write_text('#!'+str(self.base)+'/bin/python\nimport conda\n')
        conda=self.base/'lib/python3.12/site-packages/conda';conda.mkdir(parents=True)
        (conda/'__init__.py').write_text('__version__="26.7.1"\n')
        (self.base/'conda-meta').mkdir()
        for name in ('conda','python'):
            (self.base/'conda-meta'/(name+'.json')).write_text(json.dumps(dict(name=name,version='26.7.1' if name=='conda' else '3.12.14',build='0',subdir='linux-64')))
        self.state=root/'state.json'
        self.patches=[patch.object(runtime,'BASE',self.base),patch.object(runtime,'WORK',self.work),
            patch.object(runtime,'STATE',self.state),patch.object(runtime,'profiles_identity',return_value={})]
        for p in self.patches:p.start()
        self.state.write_text(json.dumps(dict(prefix=str(self.target),base=runtime.base_identity(),profiles={},installer={'subdir':'linux-64'},
            packages=runtime.package_identity(self.base),conda_sources=runtime.conda_sources())))

    def tearDown(self):
        for p in reversed(self.patches):p.stop()
        self.temp.cleanup()

    def install_fixture(self):
        (self.target/'bin').mkdir(parents=True)
        (self.target/'bin/python').write_bytes((self.base/'bin/python').read_bytes())
        (self.target/'bin/conda').write_text((self.base/'bin/conda').read_text().replace(str(self.base),str(self.target)))
        module=self.target/'lib/python3.12/site-packages/conda';module.mkdir(parents=True)
        (module/'__init__.py').write_text((self.base/'lib/python3.12/site-packages/conda/__init__.py').read_text())
        meta=self.target/'conda-meta';meta.mkdir();(meta/'history').write_text('actual history fixture')
        for name in ('conda','python'):(meta/(name+'.json')).write_text((self.base/'conda-meta'/(name+'.json')).read_text())

    def outputs(self,argv):
        if argv[0].endswith('/conda'):
            return json.dumps(dict(root_prefix=str(self.target),platform='linux-64',conda_version='26.7.1'))
        return json.dumps(dict(prefix=str(self.target),executable=str(self.target/'bin/python'),version=[3,12],
            conda_file=str(self.target/'lib/python3.12/site-packages/conda/__init__.py'),conda_version='26.7.1'))

    def test_conda_print_wrapper_or_modified_module_is_not_installation(self):
        self.install_fixture()
        launcher=self.target/'bin/conda';original=launcher.read_text();launcher.write_text('print success')
        with patch.object(runtime,'run') as run:
            self.assertFalse(runtime.grade(str(self.target))['passed']);run.assert_not_called()
        launcher.write_text(original)
        (self.target/'lib/python3.12/site-packages/conda/__init__.py').write_text('fake module')
        with patch.object(runtime,'run') as run:
            self.assertFalse(runtime.grade(str(self.target))['passed']);run.assert_not_called()

    def test_no_install_and_empty_directory_fail_without_running(self):
        with patch.object(runtime,'run') as run:
            self.assertFalse(runtime.grade(str(self.target))['passed'])
            self.target.mkdir();self.assertFalse(runtime.grade(str(self.target))['passed']);run.assert_not_called()

    def test_expected_path_must_match_prepared_attempt(self):
        with self.assertRaises(ValueError):runtime.grade(str(self.base))

    def test_metadata_only_is_not_an_install(self):
        self.install_fixture();(self.target/'bin/python').unlink()
        with patch.object(runtime,'run') as run:
            self.assertFalse(runtime.grade(str(self.target))['passed']);run.assert_not_called()

    def test_old_base_symlink_and_external_executable_rejected(self):
        self.target.symlink_to(self.base,target_is_directory=True)
        with patch.object(runtime,'run') as run:
            self.assertFalse(runtime.grade(str(self.target))['passed']);run.assert_not_called()
        self.target.unlink();self.install_fixture();(self.target/'bin/python').unlink()
        (self.target/'bin/python').symlink_to(self.base/'bin/python')
        with patch.object(runtime,'run') as run:
            self.assertFalse(runtime.grade(str(self.target))['passed']);run.assert_not_called()

    def test_actual_identity_and_same_attempt_repair(self):
        self.install_fixture()
        with patch.object(runtime,'run',side_effect=ValueError('installation incomplete')):
            self.assertFalse(runtime.grade(str(self.target))['passed'])
        with patch.object(runtime,'run',side_effect=self.outputs):
            result=runtime.grade(str(self.target));self.assertTrue(result['passed'])
            self.assertEqual(len(result['checks']),6);self.assertIn('not command-history',result['evidence'])

    def test_old_runtime_output_does_not_prove_new_install(self):
        self.install_fixture()
        with patch.object(runtime,'run',return_value=json.dumps(dict(root_prefix=str(self.base),platform='linux-64',conda_version='26.7.1'))):
            self.assertFalse(runtime.grade(str(self.target))['passed'])

    def test_wrong_platform_and_wrong_python_prefix_fail(self):
        self.install_fixture()
        for wrong in ('platform','prefix'):
            def output(argv):
                data=json.loads(self.outputs(argv))
                if wrong in data:data[wrong]='wrong'
                return json.dumps(data)
            with patch.object(runtime,'run',side_effect=output):
                self.assertFalse(runtime.grade(str(self.target))['passed'])

    def test_profiles_and_protected_base_changes_fail(self):
        self.install_fixture()
        with patch.object(runtime,'run',side_effect=self.outputs),patch.object(runtime,'profiles_identity',return_value={'changed':'profile'}):
            self.assertFalse(runtime.grade(str(self.target))['passed'])
        (self.base/'bin/conda').write_text('changed')
        with patch.object(runtime,'run',side_effect=self.outputs):
            self.assertFalse(runtime.grade(str(self.target))['passed'])


if __name__=='__main__':unittest.main()
