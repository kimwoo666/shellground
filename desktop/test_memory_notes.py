"""Persistence and native UI tests for explicitly saved learning notes."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QMessageBox
from memory_notes import NoteStore, MemoryDialog, suggest_note
from missions import UNITS, make_mission
from native_app import Window, create_application


class NoteStoreTests(unittest.TestCase):
    def test_suggestions_and_selected_text(self):
        unit = next(u for u in UNITS if u.key == 'read')
        m = make_mission('read', 9853, 2)
        draft = suggest_note(unit, m)
        self.assertIn('따옴표', draft['title'])
        self.assertIn('cat "docs/read me.txt"', draft['body'])
        selected = suggest_note(unit, m, '직접 고른 규칙\u2029내 예시')
        self.assertEqual(selected['body'], '직접 고른 규칙\n내 예시')
        self.assertEqual(selected['title'], '직접 고른 규칙')

    def test_save_reload_edit_deduplicate_and_delete(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / 'memory-v1.json'
            store = NoteStore(path)
            self.assertEqual(store.load(), [])
            self.assertFalse(path.exists())
            a = store.save('공백 경로', 'cat "read me.txt"', 'read')
            self.assertEqual(NoteStore(path).load(), [a])
            duplicate = store.save('공백 경로', 'cat "read me.txt"', 'read')
            self.assertEqual(duplicate['id'], a['id'])
            self.assertEqual(len(store.load()), 1)
            store.save('따옴표 기억', '내 예시', 'read', a['id'])
            store.save('ls 옵션', '-a는 숨김 포함', 'list')
            store.delete(a['id'])
            self.assertEqual([n['title'] for n in store.load()], ['ls 옵션'])
            self.assertEqual(set(json.loads(path.read_text())), {'schema', 'notes'})

    def test_corrupt_file_and_write_failure_preserve_saved_data(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / 'memory-v1.json'
            path.write_text('{broken', encoding='utf-8')
            store = NoteStore(path)
            with self.assertRaises(ValueError): store.save('규칙', '예시')
            self.assertEqual(path.read_text(), '{broken')
            path.write_text('{"schema":1,"notes":[]}', encoding='utf-8')
            store.save('규칙', '예시')
            original = path.read_bytes()
            with patch.object(Path, 'replace', side_effect=OSError('disk full')):
                with self.assertRaises(OSError): store.save('두 번째', '예시')
            self.assertEqual(path.read_bytes(), original)
            self.assertEqual(list(Path(temporary).glob('*.tmp')), [])


class MemoryUITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app, cls.ui, cls.mono = create_application()

    def test_draft_requires_save_and_search_finds_body(self):
        with tempfile.TemporaryDirectory() as temporary:
            store = NoteStore(Path(temporary) / 'memory-v1.json')
            dialog = MemoryDialog(store, draft={'title': '규칙', 'body': '공백 경로는 따옴표로', 'unit': 'read'})
            dialog.show(); dialog.activateWindow(); dialog.body.setFocus()
            self.app.processEvents()
            self.assertFalse(store.path.exists())
            QTest.keyClick(dialog.body, Qt.Key.Key_S, Qt.KeyboardModifier.ControlModifier)
            self.app.processEvents()
            self.assertFalse(dialog.dirty)
            self.assertEqual(store.load()[0]['title'], '규칙')
            self.assertIn('저장됨', dialog.status.text())
            dialog.search.setText('따옴표')
            self.assertEqual(dialog.list.count(), 1)
            dialog.search.setText('없는단어')
            self.assertEqual(dialog.list.count(), 0)
            dialog.close()
            restored = MemoryDialog(NoteStore(store.path))
            self.assertEqual(restored.body.toPlainText(), '공백 경로는 따옴표로')
            dialog.deleteLater(); restored.deleteLater(); self.app.processEvents()

    def test_unsaved_cancel_then_save_on_close(self):
        with tempfile.TemporaryDirectory() as temporary:
            store = NoteStore(Path(temporary) / 'memory-v1.json')
            dialog = MemoryDialog(store, draft={'title': '규칙', 'body': '예시', 'unit': ''})
            dialog.show(); self.app.processEvents()
            with patch.object(QMessageBox, 'question', return_value=QMessageBox.StandardButton.Cancel):
                dialog.close()
            self.assertTrue(dialog.isVisible())
            self.assertFalse(store.path.exists())
            with patch.object(QMessageBox, 'question', return_value=QMessageBox.StandardButton.Save):
                dialog.close()
            self.assertFalse(dialog.isVisible())
            self.assertEqual(store.load()[0]['body'], '예시')
            dialog.deleteLater(); self.app.processEvents()

    def test_save_failure_keeps_dirty_note_and_corrupt_file_is_read_only(self):
        with tempfile.TemporaryDirectory() as temporary:
            store = NoteStore(Path(temporary) / 'memory-v1.json')
            dialog = MemoryDialog(store, draft={'title': '규칙', 'body': '예시', 'unit': ''})
            with patch.object(store, 'save', side_effect=OSError('disk full')), patch.object(QMessageBox, 'warning'):
                self.assertFalse(dialog.save_note())
                self.assertTrue(dialog.dirty)
                self.assertIn('저장 실패', dialog.status.text())
            store.path.write_text('broken', encoding='utf-8')
            broken = MemoryDialog(store, draft={'title': '초안', 'body': '내용', 'unit': ''})
            self.assertFalse(broken.save_button.isEnabled())
            self.assertIn('읽기 실패', broken.status.text())
            self.assertEqual(store.path.read_text(), 'broken')
            dialog.deleteLater(); broken.deleteLater(); self.app.processEvents()

    def test_switching_notes_and_deletion_require_confirmation(self):
        with tempfile.TemporaryDirectory() as temporary:
            store = NoteStore(Path(temporary) / 'memory-v1.json')
            first = store.save('첫 노트', '첫 내용')
            second = store.save('둘째 노트', '둘째 내용')
            dialog = MemoryDialog(store)
            dialog.body.setPlainText('수정한 둘째 내용')
            with patch.object(QMessageBox, 'question', return_value=QMessageBox.StandardButton.Cancel):
                dialog.list.setCurrentRow(1)
            self.assertEqual(dialog.current_id, second['id'])
            self.assertTrue(dialog.dirty)
            with patch.object(QMessageBox, 'question', return_value=QMessageBox.StandardButton.Save):
                dialog.list.setCurrentRow(1)
            self.assertEqual(dialog.current_id, first['id'])
            self.assertEqual(next(n for n in store.load() if n['id'] == second['id'])['body'], '수정한 둘째 내용')
            with patch.object(QMessageBox, 'question', return_value=QMessageBox.StandardButton.No):
                dialog.delete_note()
            self.assertEqual(len(store.load()), 2)
            with patch.object(QMessageBox, 'question', return_value=QMessageBox.StandardButton.Yes):
                dialog.delete_note()
            self.assertEqual([n['id'] for n in store.load()], [second['id']])
            dialog.deleteLater(); self.app.processEvents()

    def test_f7_f8_from_terminal_and_progress_separation(self):
        with tempfile.TemporaryDirectory() as temporary:
            progress = Path(temporary) / 'progress-v3.json'
            window = Window(self.ui, self.mono, progress)
            window.mission = make_mission('read', 9853, 2)
            window.show(); window.activateWindow(); window.terminal.setFocus()
            self.app.processEvents()
            with patch('native_app.MemoryDialog') as dialog:
                QTest.keyClick(window.terminal, Qt.Key.Key_F7)
                self.app.processEvents()
                draft = dialog.call_args.args[2]
                self.assertIn('따옴표', draft['title'])
                QTest.keyClick(window.terminal, Qt.Key.Key_F8)
                self.app.processEvents()
                self.assertIsNone(dialog.call_args.args[2])
                self.assertEqual(dialog.call_count, 2)
                window.busy = True; window.update_controls()
                QTest.keyClick(window.terminal, Qt.Key.Key_F7)
                QTest.keyClick(window.terminal, Qt.Key.Key_F8)
                self.app.processEvents()
                self.assertEqual(dialog.call_count, 2)
            window.busy = False
            window.note_store.save('규칙', '내가 저장한 예시', 'read')
            window.save_progress()
            self.assertEqual(json.loads(progress.read_text()), {'schema': 3, 'completed': []})
            self.assertEqual(window.note_store.load()[0]['body'], '내가 저장한 예시')
            window.hide(); window.deleteLater(); self.app.processEvents()


if __name__ == '__main__': unittest.main()
