from pathlib import Path
import tempfile
import unittest
from conda_teaching.guest_files import list_files,read_file,MAX_BYTES


class CondaFileViewerTests(unittest.TestCase):
    def test_actual_relative_files_and_read_only_preview(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);(root/'share').mkdir();file=root/'share/environment.yml'
            file.write_text('name: sg-work\n');(root/'.note').write_text('hidden file')
            self.assertEqual(list_files(root)['files'],['.note','share/environment.yml'])
            self.assertEqual(read_file('share/environment.yml',root)['text'],'name: sg-work\n')
            self.assertEqual(file.read_text(),'name: sg-work\n')
            for path in ('../secret','/etc/passwd','share'):
                with self.assertRaises((ValueError,OSError)):read_file(path,root)

    def test_bounded_files_links_and_binary(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);(root/'large').write_text('x'*(MAX_BYTES+4))
            value=read_file('large',root);self.assertTrue(value['truncated']);self.assertEqual(len(value['text']),MAX_BYTES)
            (root/'binary').write_bytes(b'\0data')
            with self.assertRaises(ValueError):read_file('binary',root)
            (root/'link').symlink_to(root/'large')
            with self.assertRaises(ValueError):read_file('link',root)
            self.assertNotIn('link',list_files(root)['files'])
            for number in range(205):(root/f'item{number}').touch()
            value=list_files(root);self.assertTrue(value['truncated']);self.assertLessEqual(len(value['files']),200)


if __name__=='__main__':unittest.main()
