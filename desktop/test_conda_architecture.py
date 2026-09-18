import json
from pathlib import Path
import tempfile
import unittest
from conda_teaching.installer_sources import installer_for
from conda_teaching.channel import build_channel


class CondaArchitectureTests(unittest.TestCase):
    def test_guest_architecture_selects_the_pinned_installer(self):
        self.assertEqual(installer_for('arm64'),installer_for('aarch64'))
        self.assertEqual(installer_for('AMD64'),installer_for('x86_64'))
        self.assertEqual(installer_for('aarch64')['subdir'],'linux-aarch64')
        self.assertNotEqual(installer_for('aarch64')['sha256'],installer_for('x86_64')['sha256'])
        with self.assertRaises(ValueError):installer_for('riscv64')

    def cache(self,base,subdir,count=10):
        # Tiny metadata fixtures test routing, not execution of fake archives.
        for n in range(count):
            stem=f'fixture{n}-1.0-0';folder=base/'pkgs'/stem/'info';folder.mkdir(parents=True)
            (folder/'index.json').write_text(json.dumps({'name':f'fixture{n}','version':'1.0','build':'0',
                'build_number':0,'subdir':subdir}))
            (base/'pkgs'/(stem+'.conda')).write_bytes(b'metadata-routing-test-only')

    def test_both_architectures_keep_native_and_noarch_separate(self):
        for subdir in ('linux-64','linux-aarch64'):
            with self.subTest(subdir=subdir),tempfile.TemporaryDirectory() as directory:
                base=Path(directory)/'base';target=Path(directory)/'channel';self.cache(base,subdir)
                result=build_channel(base,target)
                self.assertEqual(result['subdir'],subdir)
                self.assertEqual(result['official_archives'],10)
                native=json.loads((target/subdir/'repodata.json').read_text())
                self.assertEqual(len(native['packages.conda']),10)
                self.assertEqual(len(json.loads((target/'noarch/repodata.json').read_text())['packages']),3)
                wrong='linux-64' if subdir=='linux-aarch64' else 'linux-aarch64'
                self.assertFalse((target/wrong).exists())

    def test_mixed_architecture_is_rejected_instead_of_silently_skipped(self):
        with tempfile.TemporaryDirectory() as directory:
            base=Path(directory)/'base';self.cache(base,'linux-64')
            path=base/'pkgs/fixture0-1.0-0/info/index.json';record=json.loads(path.read_text())
            record['subdir']='linux-aarch64';path.write_text(json.dumps(record))
            with self.assertRaisesRegex(RuntimeError,'mixed'):build_channel(base,Path(directory)/'channel')
