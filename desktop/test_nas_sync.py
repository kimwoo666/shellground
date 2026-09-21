import json
from pathlib import Path
import tempfile
import unittest

from nas_sync import (Synchronizer, FolderStore, atomic_json, read_json, merge,
                      validate_snapshot, MARKER, flatten)


class NasSyncTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.nas = self.root / 'NAS'; self.nas.mkdir()
        self.config = dict(profile='test-profile', transport='folder', folder=str(self.nas))
        atomic_json(self.nas / MARKER, dict(schema=1, profile='test-profile'))
        self.a, self.b = self.root / 'linux', self.root / 'windows'
        self.a.mkdir(); self.b.mkdir()
    def write(self, root, completed, **extra):
        atomic_json(root / 'progress-v3-real.json', dict(schema=3, completed=completed, **extra))
    def sync(self, root, apply=True):
        return Synchronizer(root, self.config).synchronize(apply=apply)
    def data(self, root): return read_json(root / 'progress-v3-real.json')
    def note(self, root, body):
        notes = [] if body is None else [dict(id='quote',title='공백 경로',body=body,unit='navigate')]
        atomic_json(root / 'memory-v1.json', dict(schema=1, notes=notes))
    def test_existing_completion_and_substeps_merge(self):
        self.write(self.a, ['navigate'], learning={'navigate':{'confirmed':['A'], 'cursor':'B'}})
        self.write(self.b, ['pwdpaths'], learning={'navigate':{'confirmed':['B'], 'cursor':'C'}})
        self.sync(self.a); self.sync(self.b); self.sync(self.a)
        self.assertEqual(set(self.data(self.a)['completed']), {'navigate','pwdpaths'})
        self.assertEqual(set(self.data(self.a)['learning']['navigate']['confirmed']), {'A','B'})
    def test_active_session_does_not_replace_local_files(self):
        self.write(self.a, ['navigate']); self.write(self.b, ['pwdpaths'])
        self.sync(self.a); self.sync(self.b, apply=False)
        self.assertEqual(self.data(self.b)['completed'], ['pwdpaths'])
        self.sync(self.b)
        self.assertEqual(set(self.data(self.b)['completed']), {'navigate','pwdpaths'})
    def test_old_app_cannot_erase_earned_completion(self):
        self.write(self.a, ['navigate','pwdpaths']); self.sync(self.a)
        self.write(self.a, ['navigate']); self.sync(self.a)
        self.assertIn('pwdpaths', self.data(self.a)['completed'])
    def test_idle_old_cursor_is_not_republished_as_new(self):
        self.write(self.a, ['navigate'], last_learning='navigate'); self.sync(self.a); self.sync(self.b)
        self.write(self.b, ['navigate'], last_learning='pwdpaths'); self.sync(self.b)
        self.sync(self.a, apply=False); self.sync(self.a, apply=False); self.sync(self.a)
        self.assertEqual(self.data(self.a)['last_learning'], 'pwdpaths')
    def test_later_note_edit_replaces_without_conflict_copy(self):
        self.note(self.a, 'old'); self.sync(self.a); self.sync(self.b)
        self.note(self.b, 'new'); self.sync(self.b); self.sync(self.a)
        notes=read_json(self.a/'memory-v1.json')['notes']
        self.assertEqual([n['body'] for n in notes], ['new'])
    def test_concurrent_note_edits_are_both_preserved(self):
        self.note(self.a, 'old'); self.sync(self.a); self.sync(self.b)
        self.note(self.a, 'Linux edit'); self.note(self.b, 'Windows edit')
        self.sync(self.a); self.sync(self.b); self.sync(self.a); self.sync(self.b)
        for root in (self.a,self.b):
            notes=read_json(root/'memory-v1.json')['notes']
            self.assertEqual({n['body'] for n in notes}, {'Linux edit','Windows edit'})
            self.assertEqual(len(notes), 2)
    def test_note_deletion_does_not_resurrect_from_idle_computer(self):
        self.note(self.a, 'old'); self.sync(self.a); self.sync(self.b)
        self.note(self.a, None); self.sync(self.a); self.sync(self.b); self.sync(self.a)
        self.assertEqual(read_json(self.b/'memory-v1.json')['notes'], [])
    def test_absent_note_file_does_not_delete_other_devices_notes(self):
        self.note(self.a, 'old'); self.sync(self.a); self.sync(self.b)
        (self.b/'memory-v1.json').unlink(); self.sync(self.b)
        self.assertEqual(read_json(self.b/'memory-v1.json')['notes'][0]['body'], 'old')
    def test_foreign_files_and_code_not_sent(self):
        self.write(self.a, ['navigate'], private_token='not-to-upload')
        atomic_json(self.a/'settings-v1.json', {'password':'not-to-upload'})
        self.sync(self.a)
        remote=next(self.nas.glob('device-*.json')).read_text()
        self.assertNotIn('not-to-upload', remote)
    def test_wrong_profile_and_corrupt_remote_preserve_local_progress(self):
        self.write(self.a, ['navigate']); self.sync(self.a)
        original=(self.a/'progress-v3-real.json').read_bytes()
        atomic_json(self.nas/('device-'+'f'*32+'.json'), {'schema':1,'profile':'someone-else'})
        with self.assertRaises(ValueError): self.sync(self.a)
        self.assertEqual((self.a/'progress-v3-real.json').read_bytes(), original)
    def test_missing_mount_does_not_create_fallback_profile(self):
        self.config['folder']=str(self.root/'not-mounted')
        with self.assertRaises(OSError): self.sync(self.a)
        self.assertFalse((self.root/'not-mounted').exists())
    def test_failed_upload_retries_without_losing_changes(self):
        class Failing(FolderStore):
            def write(self, name, data): raise OSError('offline')
        self.write(self.a, ['navigate'])
        with self.assertRaises(OSError):
            Synchronizer(self.a,self.config,Failing(self.nas)).synchronize()
        self.sync(self.a); self.sync(self.b)
        self.assertEqual(self.data(self.b)['completed'], ['navigate'])
    def test_unknown_schema_does_not_publish(self):
        atomic_json(self.a/'progress-v3-real.json',dict(schema=999,completed=['navigate']))
        with self.assertRaises(ValueError): self.sync(self.a)
        self.assertEqual(list(self.nas.glob('device-*.json')), [])
    def test_payload_cannot_choose_arbitrary_local_file(self):
        self.write(self.a, ['navigate']); self.sync(self.a)
        remote=read_json(next(self.nas.glob('device-*.json')))
        record=next(iter(remote['records'].values()))
        remote['records'][json.dumps(['value','../outside.json','resume'])]=record
        with self.assertRaises(ValueError): validate_snapshot(remote,'test-profile')


if __name__ == '__main__': unittest.main()
