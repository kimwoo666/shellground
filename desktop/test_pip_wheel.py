"""Unit evidence checks, plus opt-in real pip in disposable local venvs.

The latter does not prove guest/app-UI acceptance. It never
installs into the host's Python or changes the active Conda validation image.
"""
import csv
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import unittest
import venv

from conda_teaching.pip_wheel import (
    NUMPY_WHEEL, NUMPY_PROBE, WheelAssetError, WheelManifest,
    inspect_install, inspect_removal, load_numpy_wheel, record_hash, record_rows, wheel_path)


class WheelEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.folder=tempfile.TemporaryDirectory()
        self.root=Path(self.folder.name)
        self.prefix=self.root/'env'
        self.site=self.prefix/'lib/python3.12/site-packages'
        self.dist='numpy-2.3.5.dist-info'
        self.module=self.site/'numpy/__init__.py'
        self.record=self.site/self.dist/'RECORD'
        # A deliberately tiny unit fixture, never an actual NumPy claim.
        data=b'unit fixture, not executable NumPy\n'
        self.checksum=hashlib.sha256(data).hexdigest()
        self.manifest=WheelManifest('numpy','2.3.5',self.dist,
            {'numpy/__init__.py':(self.checksum,len(data))},'unit-fixture',('f2py',))
        self.module.parent.mkdir(parents=True)
        self.module.write_bytes(data)
        self.record.parent.mkdir()
        output=io.StringIO();writer=csv.writer(output)
        writer.writerow(['numpy/__init__.py',record_hash(self.checksum),str(len(data))])
        writer.writerow([self.dist+'/RECORD','',''])
        self.record.write_text(output.getvalue())

    def tearDown(self):self.folder.cleanup()

    def test_canonical_fixture_and_changed_file(self):
        self.assertTrue(inspect_install(self.prefix,self.manifest)['valid'])
        self.module.write_bytes(b'fake output')
        self.assertFalse(inspect_install(self.prefix,self.manifest)['valid'])

    def test_metadata_without_files_is_not_installation(self):
        self.module.unlink()
        self.assertFalse(inspect_install(self.prefix,self.manifest)['valid'])

    def test_modified_record_does_not_override_official_hash(self):
        self.module.write_bytes(b'changed')
        value=hashlib.sha256(b'changed').hexdigest()
        self.record.write_text('numpy/__init__.py,'+record_hash(value)+',7\n')
        self.assertFalse(inspect_install(self.prefix,self.manifest)['valid'])

    def test_external_links_and_alias_prefix_are_not_distinct_installation(self):
        external=self.root/'outside';external.write_bytes(self.module.read_bytes())
        self.module.unlink();self.module.symlink_to(external)
        self.assertFalse(inspect_install(self.prefix,self.manifest)['valid'])
        alias=self.root/'alias';alias.symlink_to(self.prefix,target_is_directory=True)
        self.assertFalse(inspect_install(alias,self.manifest)['valid'])

    def test_installed_script_record_may_be_inside_prefix_but_never_outside(self):
        original=self.record.read_text()
        self.record.write_text(original+'../../../bin/f2py,,\n')
        self.assertTrue(inspect_install(self.prefix,self.manifest)['valid'])
        self.record.write_text(original+'../../../../host-file,,\n')
        self.assertFalse(inspect_install(self.prefix,self.manifest)['valid'])

    def test_record_cannot_claim_other_packages_or_python_even_inside_prefix(self):
        original=self.record.read_text()
        for name in ('training_text/__init__.py', 'pip/__init__.py', '../../../bin/python',
                     '../../../bin/pip', self.dist+'/../../python3.12/os.py'):
            with self.subTest(name=name):
                self.record.write_text(original+name+',,\n')
                self.assertFalse(inspect_install(self.prefix,self.manifest)['valid'])

    def test_generated_bytecode_is_accepted_but_other_package_bytecode_is_not(self):
        original=self.record.read_text()
        self.record.write_text(original+'numpy/__pycache__/__init__.cpython-312.pyc,,\n')
        self.assertTrue(inspect_install(self.prefix,self.manifest)['valid'])
        self.record.write_text(original+'pip/__pycache__/__init__.cpython-312.pyc,,\n')
        self.assertFalse(inspect_install(self.prefix,self.manifest)['valid'])

    def test_symlink_loops_are_incorrect_state_not_checker_crashes(self):
        self.module.unlink();self.module.symlink_to(self.module.name)
        self.assertFalse(inspect_install(self.prefix,self.manifest)['valid'])
        loop=self.root/'loop';loop.symlink_to('loop')
        self.assertFalse(inspect_install(loop,self.manifest)['valid'])
        self.assertFalse(inspect_removal(loop,self.manifest)['valid'])

    def test_removal_requires_owned_files_and_scripts_absent_but_allows_empty_dirs(self):
        self.assertFalse(inspect_removal(self.prefix,self.manifest)['valid'])
        self.module.unlink();self.record.unlink()
        self.assertTrue(inspect_removal(self.prefix,self.manifest)['valid'])
        script=self.prefix/'bin/f2py';script.parent.mkdir();script.write_text('remaining script')
        self.assertFalse(inspect_removal(self.prefix,self.manifest)['valid'])
        script.unlink();script.symlink_to('missing-target')
        self.assertFalse(inspect_removal(self.prefix,self.manifest)['valid'])

    def test_record_is_required_and_duplicate_entries_are_rejected(self):
        with self.assertRaises(ValueError):record_rows('a,,\na,,\n')
        with self.assertRaises(ValueError):record_rows('a,sha256=abc\n')
        self.record.unlink()
        self.assertFalse(inspect_install(self.prefix,self.manifest)['valid'])

    def test_wheel_paths_and_unverified_asset_fail_closed(self):
        for name in ('../outside','/absolute','a/../b','a//b','a\\b'):
            with self.subTest(name=name),self.assertRaises(ValueError):wheel_path(name)
        self.assertEqual(str(wheel_path('numpy/__init__.py')),'numpy/__init__.py')
        path=self.root/NUMPY_WHEEL['filename'];path.write_bytes(b'not the official wheel')
        with self.assertRaises(WheelAssetError):load_numpy_wheel(path)


@unittest.skipUnless(os.environ.get('SHELLGROUND_TEST_PIP_WHEEL')=='1',
                     'Explicit opt-in: official local wheel and temporary Linux CPython3.12 venv')
class ActualWheelEvidenceTests(unittest.TestCase):
    def test_official_numpy_install_corruption_repair_wrong_prefix_and_uninstall(self):
        self.assertEqual(sys.version_info[:2],(3,12))
        self.assertEqual(sys.platform,'linux')
        wheel=Path(__file__).resolve().parent/'.conda-build'/NUMPY_WHEEL['filename']
        manifest=load_numpy_wheel(wheel)
        self.assertEqual(len(manifest.files),899)
        with tempfile.TemporaryDirectory(prefix='shellground-pip-proof-') as folder:
            root=Path(folder);prefix=root/'env'
            venv.EnvBuilder(with_pip=True,symlinks=False).create(prefix)
            python=prefix/'bin/python'
            site=prefix/'lib/python3.12/site-packages'
            # Preservation sentinels are not claims about the real lesson's
            # training tools. Full guest preservation grading is still pending.
            sentinel=site/'training_text/__init__.py'
            sentinel.parent.mkdir();sentinel.write_text('VALUE = "keep this package"\n')
            other=root/'other-env'
            venv.EnvBuilder(with_pip=False,symlinks=False).create(other)
            def preserved():
                paths=list((site/'pip').rglob('*'))
                for dist in site.glob('pip-*.dist-info'):
                    paths.extend(dist.rglob('*'))
                paths.extend((prefix/'bin').iterdir())
                paths.extend(other.rglob('*'))
                paths.append(sentinel)
                return {str(path.relative_to(root)):hashlib.sha256(path.read_bytes()).hexdigest()
                        for path in paths if path.is_file() and path.suffix!='.pyc'
                        and path.name not in ('f2py','numpy-config')}
            baseline=preserved()
            def pip(*args):
                result=subprocess.run([str(python),'-I','-m','pip','--isolated',
                    *args,'--disable-pip-version-check','--no-cache-dir'],cwd=root,
                    text=True,capture_output=True,timeout=45)
                self.assertEqual(result.returncode,0,result.stdout+result.stderr)
                return result
            def confirm_uninstall(reply):
                # Observe the real pip question on an actual PTY. This is a
                # local developer check, not the still-pending guest UI test.
                import errno
                import pty
                import select
                master,slave=pty.openpty()
                process=None;output=b'';answered=False
                try:
                    process=subprocess.Popen([str(python),'-I','-m','pip','--isolated',
                        'uninstall','numpy','--disable-pip-version-check'],cwd=root,
                        stdin=slave,stdout=slave,stderr=slave,start_new_session=True)
                    os.close(slave);slave=None
                    deadline=time.monotonic()+20
                    while time.monotonic()<deadline:
                        readable,_,_=select.select([master],[],[],.2)
                        if readable:
                            try:block=os.read(master,65536)
                            except OSError as error:
                                if error.errno!=errno.EIO:raise
                                block=b''
                            output+=block
                            if b'Proceed (Y/n)?' in output and not answered:
                                self.assertIn(str(prefix).encode(),output)
                                os.write(master,reply.encode()+b'\n');answered=True
                            if not block:break
                        if process.poll() is not None and not readable:break
                    self.assertTrue(answered,output.decode(errors='replace'))
                    self.assertEqual(process.wait(timeout=2),0,output.decode(errors='replace'))
                    return output.decode(errors='replace')
                finally:
                    if process is not None and process.poll() is None:
                        os.killpg(process.pid,signal.SIGKILL);process.wait(timeout=3)
                    os.close(master)
                    if slave is not None:os.close(slave)
            def probe(absent=False,expected=None):
                return subprocess.run([str(python),'-I','-c',NUMPY_PROBE],cwd=root,
                    input=json.dumps(dict(prefix=str(expected or prefix),version='2.3.5',absent=absent)),
                    text=True,capture_output=True,timeout=15,
                    env=dict(os.environ,OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1'))
            self.assertEqual(probe(absent=True).returncode,0)
            self.assertTrue(inspect_removal(prefix,manifest)['valid'])
            self.assertFalse(inspect_install(prefix,manifest)['valid'])
            pip('install','--no-index','--no-deps',str(wheel))
            evidence=inspect_install(prefix,manifest)
            self.assertTrue(evidence['valid'],evidence)
            observed=probe();self.assertEqual(observed.returncode,0,observed.stderr)
            self.assertEqual(json.loads(observed.stdout)['sums'],[7,3])
            self.assertNotEqual(probe(expected=root/'wrong-env').returncode,0)

            module=site/'numpy/__init__.py';original=module.read_bytes()
            try:
                module.write_bytes(original+b'\n# unexpected modification\n')
                self.assertFalse(inspect_install(prefix,manifest)['valid'])
            finally:module.write_bytes(original)
            self.assertTrue(inspect_install(prefix,manifest)['valid'])

            extension_name=next(name for name in manifest.files
                if '/_multiarray_umath.' in name and name.endswith('.so'))
            extension=site/extension_name;saved=root/'damaged-extension-backup.so'
            extension.rename(saved)
            self.assertFalse(inspect_install(prefix,manifest)['valid'])
            self.assertNotEqual(probe().returncode,0)
            self.assertNotEqual(probe(absent=True).returncode,0)
            # The same installed version is skipped by plain pip install;
            # success exit status must not be mistaken for successful repair.
            pip('install','--no-index','--no-deps',str(wheel))
            self.assertFalse(inspect_install(prefix,manifest)['valid'])
            self.assertNotEqual(probe().returncode,0)
            pip('uninstall','--yes','numpy')
            self.assertTrue(inspect_removal(prefix,manifest)['valid'])
            self.assertEqual(probe(absent=True).returncode,0)
            pip('install','--no-index','--no-deps',str(wheel))
            self.assertTrue(inspect_install(prefix,manifest)['valid'])
            self.assertEqual(probe().returncode,0)

            dist=site/manifest.dist_info;hidden=site/(manifest.dist_info+'.saved')
            dist.rename(hidden)
            try:
                self.assertNotEqual(probe(absent=True).returncode,0,
                                    'Missing metadata must not hide the remaining importable module')
            finally:hidden.rename(dist)
            library_name=next(name for name in manifest.files if name.startswith('numpy.libs/'))
            library=site/library_name;library_backup=root/'owned-native-library.so'
            shutil.copy2(library,library_backup)
            confirm_uninstall('n')
            self.assertTrue(inspect_install(prefix,manifest)['valid'])
            self.assertEqual(probe().returncode,0)
            confirm_uninstall('y')
            self.assertFalse(inspect_install(prefix,manifest)['valid'])
            absent=probe(absent=True);self.assertEqual(absent.returncode,0,absent.stderr)
            self.assertTrue(inspect_removal(prefix,manifest)['valid'])
            # Import and metadata absence alone miss leftover native libraries.
            library.parent.mkdir(exist_ok=True);shutil.copy2(library_backup,library)
            self.assertEqual(probe(absent=True).returncode,0)
            self.assertFalse(inspect_removal(prefix,manifest)['valid'])
            library.unlink()
            self.assertTrue(inspect_removal(prefix,manifest)['valid'])
            empty_dist=site/manifest.dist_info;empty_dist.mkdir(exist_ok=True)
            self.assertTrue(inspect_removal(prefix,manifest)['valid'])
            absent=probe(absent=True);self.assertEqual(absent.returncode,0,absent.stderr)
            self.assertTrue(json.loads(absent.stdout)['empty_metadata_only'])
            empty_dist.rmdir()
            empty=site/'numpy';empty.mkdir(exist_ok=True)
            cache=empty/'__pycache__';cache.mkdir(exist_ok=True)
            (cache/'__init__.cpython-312.pyc').write_bytes(b'harmless orphaned cache')
            self.assertTrue(inspect_removal(prefix,manifest)['valid'])
            absent=probe(absent=True);self.assertEqual(absent.returncode,0,absent.stderr)
            self.assertTrue(json.loads(absent.stdout)['empty_namespace_only'])
            (empty/'__init__.py').write_text('array = None\n')
            self.assertFalse(inspect_removal(prefix,manifest)['valid'])
            self.assertNotEqual(probe(absent=True).returncode,0)
            (empty/'__init__.py').unlink()
            self.assertEqual(preserved(),baseline)
            output=pip('--version').stdout
            self.assertIn(str(site/'pip'),output)
            print('ACTUAL_LOCAL_WHEEL_EVIDENCE_OK official_files=899 import_sums=7,3 '
                  'changed_file wrong_prefix metadata_only_loss same_version_nonrepair '
                  'actual_uninstall_reinstall real_PTY_decline_then_confirm leftover_library '
                  'empty_namespace pip_other_env_preserved; '
                  'not_guest_or_UI_acceptance',flush=True)


if __name__=='__main__':unittest.main()
