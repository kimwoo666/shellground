import json
import os
from pathlib import Path
import tempfile
import time
import unittest

os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from native_app import create_application
from python_app import PythonWindow
from python_teaching.progress import PythonProgress
from python_quiz_dialog import QuizDialog


class PythonUITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.app,cls.ui,cls.mono=create_application()

    def setUp(self):
        self.folder=tempfile.TemporaryDirectory()
        self.path=Path(self.folder.name)/'python-progress-v1.json'
        self.window=PythonWindow(self.ui,self.mono,self.path)
        self.window.show(); self.app.processEvents()

    def tearDown(self):
        self.window.close(); self.app.processEvents(); self.folder.cleanup()

    def idle(self):
        deadline=time.monotonic()+15
        while self.window.busy and time.monotonic()<deadline:
            self.app.processEvents(); QTest.qWait(10)
        self.app.processEvents()
        self.assertFalse(self.window.busy,'Python UI job did not finish')

    def test_microstep_survives_close_without_source(self):
        w=self.window
        w.advance(); w.editor.setPlainText('sensitive_text = 123'); w.close()
        data=json.loads(self.path.read_text())
        self.assertEqual(data['resume']['step'],1)
        self.assertNotIn('sensitive_text',self.path.read_text())
        self.window=PythonWindow(self.ui,self.mono,self.path)
        self.assertEqual(self.window.step,1)
        self.assertEqual(self.window.editor.toPlainText(),'')

    def test_partial_grade_keeps_same_process_for_correction(self):
        w=self.window; w.phase='practice1'; w.variant=1; w.render()
        w.editor.setPlainText('profit=0'); w.run_code(); self.idle()
        process=w.engine.process
        w.grade(); self.idle()
        self.assertFalse(w.solved); self.assertEqual(w.task_tabs.currentIndex(),1)
        w.task_tabs.setCurrentIndex(0)
        w.editor.setPlainText('profit=revenue-cost'); w.run_code(); self.idle()
        w.grade(); self.idle()
        self.assertTrue(w.solved); self.assertIs(w.engine.process,process)
        self.assertIn('py_values:1',w.progress.data['passed'])
        self.assertNotIn('py_values',w.progress.data['completed'])

    def test_testing_hides_names_but_not_learning(self):
        w=self.window; w.phase='practice1'; w.render()
        self.assertNotIn(w.unit.title,w.heading.text())
        self.assertTrue(all('내용 숨김' in w.course.item(i).text() for i in range(w.course.count())))
        w.phase='learn'; w.render(); self.assertIn(w.unit.title,w.heading.text())

    def test_random_cancel_and_close_preserve_return_position(self):
        w=self.window; w.progress.passed('py_values',1); w.progress.passed('py_values',2)
        w.select_lesson(1); w.advance(); w.save()
        before=(w.index,w.phase,w.step,w.variant)
        w.start_random(); self.idle(); self.assertEqual(w.phase,'random')
        w.save(); self.assertEqual(w.progress.data['resume']['unit'],'py_sequences')
        w.stop_random(); self.assertEqual((w.index,w.phase,w.step,w.variant),before)
        self.assertFalse(w.exit_random.isVisible())

    def test_each_lesson_keeps_its_phase(self):
        w=self.window; w.phase='practice2'; w.variant=2; w.save()
        w.select_lesson(1); w.select_lesson(0)
        self.assertEqual(w.phase,'practice2'); self.assertEqual(w.variant,2)

    def test_quiz_progress_does_not_grant_practical_mastery(self):
        dialog=QuizDialog(self.window.progress)
        question=dialog.questions[dialog.index]
        dialog.options[(question['answer']+1)%4].setChecked(True); dialog.grade()
        self.assertFalse(dialog.next.isEnabled())
        dialog.options[question['answer']].setChecked(True); dialog.grade()
        self.assertTrue(dialog.next.isEnabled())
        self.assertTrue(self.window.progress.data['quiz'][question['id']]['passed'])
        self.assertEqual(self.window.progress.data['completed'],[])
        dialog.close()

    def test_concept_card_position_is_saved_without_granting_completion(self):
        dialog=QuizDialog(self.window.progress)
        dialog.index=next(i for i,q in enumerate(dialog.questions) if q['id']=='cloud-session-storage')
        dialog.render(); self.assertEqual(dialog.tabs.currentIndex(),0)
        self.assertGreater(len(dialog.related_cards),1)
        dialog.move_card(1)
        saved=dialog.related_cards[dialog.card_index]['id']
        dialog.close()
        fresh=QuizDialog(PythonProgress(self.path))
        fresh.index=next(i for i,q in enumerate(fresh.questions) if q['id']=='cloud-session-storage')
        fresh.render()
        self.assertEqual(fresh.related_cards[fresh.card_index]['id'],saved)
        self.assertEqual(self.window.progress.data['completed'],[])
        self.assertFalse(self.window.progress.data['quiz'])
        fresh.close()

    def test_editor_indent_and_undo(self):
        editor=self.window.editor
        editor.setPlainText('def example():'); editor.moveCursor(editor.textCursor().MoveOperation.End)
        QTest.keyClick(editor,Qt.Key.Key_Return)
        self.assertEqual(editor.toPlainText(),'def example():\n    ')
        QTest.keyClick(editor,Qt.Key.Key_Tab)
        self.assertTrue(editor.toPlainText().endswith('        '))

    def test_progress_corruption_is_not_overwritten(self):
        bad=Path(self.folder.name)/'bad.json'; bad.write_text('{broken')
        store=PythonProgress(bad)
        with self.assertRaises(OSError): store.resume('py_values','learn',0)
        self.assertEqual(bad.read_text(),'{broken')


if __name__=='__main__': unittest.main()
