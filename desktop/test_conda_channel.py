import io
import json
from pathlib import Path
import tarfile
import tempfile
import unittest

from conda_teaching.channel import hashes, training_package, package_record


class CondaPackageTests(unittest.TestCase):
    def test_official_installed_hotfix_is_preserved(self):
        with tempfile.TemporaryDirectory() as directory:
            base=Path(directory);meta=base/'pkgs/tk-8.6.15-0/info/index.json'
            meta.parent.mkdir(parents=True);(base/'conda-meta').mkdir()
            original={'name':'tk','version':'8.6.15','build':'0','build_number':0,'depends':['zlib <1.3']}
            meta.write_text(json.dumps(original))
            installed=base/'conda-meta/tk-8.6.15-0.json'
            installed.write_text(json.dumps(dict(original,depends=['zlib >=1.2.13,<2'],files=['lib/a'])))
            actual=package_record(base,meta)
            self.assertEqual(actual['depends'],['zlib >=1.2.13,<2'])
            self.assertNotIn('files',actual)
            installed.write_text(json.dumps(dict(original,version='9')))
            with self.assertRaises(RuntimeError):package_record(base,meta)

    def test_real_noarch_archive_metadata_paths_and_imported_code(self):
        with tempfile.TemporaryDirectory() as directory:
            package,record=training_package(Path(directory),'training-math','1.1','def total(values):\n    return sum(values)\n')
            with tarfile.open(package) as archive:
                index=json.load(archive.extractfile('info/index.json'))
                link=json.load(archive.extractfile('info/link.json'))
                paths=archive.extractfile('info/files').read().decode().splitlines()
                self.assertEqual(index,record)
                self.assertEqual(link['noarch']['type'],'python')
                self.assertEqual(paths,['site-packages/training_math/__init__.py'])
                for member in archive.getmembers():
                    self.assertFalse(member.name.startswith('/'))
                    self.assertNotIn('..',Path(member.name).parts)
                namespace={};exec(archive.extractfile(paths[0]).read(),namespace)
                self.assertEqual(namespace['__version__'],'1.1')
                self.assertEqual(namespace['total']([2,3,5]),10)
            self.assertGreater(hashes(package)['size'],0)

    def test_training_package_build_is_reproducible(self):
        with tempfile.TemporaryDirectory() as a,tempfile.TemporaryDirectory() as b:
            first,_=training_package(Path(a),'training-text','1.0','def normalize(text):\n    return text.strip().upper()\n')
            second,_=training_package(Path(b),'training-text','1.0','def normalize(text):\n    return text.strip().upper()\n')
            self.assertEqual(hashes(first),hashes(second))


if __name__=='__main__':unittest.main()
