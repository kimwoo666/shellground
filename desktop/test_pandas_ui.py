"""Only the changed pandas learning flow; user profile and VM stay untouched."""
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


class PandasUITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app,cls.ui,cls.mono = create_application()

    def setUp(self):
        self.folder = tempfile.TemporaryDirectory(prefix='shellground-pandas-ui-')
        self.path = Path(self.folder.name)/'python-progress-v1.json'
        self.window = PythonWindow(self.ui,self.mono,self.path)
        self.window.show()
        self.choose('pd_series')
        self.app.processEvents()

    def tearDown(self):
        self.idle()
        self.window.close()
        self.app.processEvents()
        self.folder.cleanup()

    def choose(self,key):
        w=self.window
        w.editor.clear()
        w.select_lesson(next(i for i,u in enumerate(w.units) if u.key == key))

    def idle(self):
        deadline=time.monotonic()+20
        while self.window.busy and time.monotonic() < deadline:
            self.app.processEvents();QTest.qWait(10)
        self.app.processEvents()
        self.assertFalse(self.window.busy)

    def run_current_example(self):
        w=self.window
        w.load_learning_example()
        w.editor.setFocus()
        QTest.keyClick(w.editor, Qt.Key.Key_Return, Qt.KeyboardModifier.ShiftModifier)
        self.idle()
        self.assertNotIn('Traceback',w.output.toPlainText())
        w.grade();self.idle()
        self.assertTrue(w.solved,w.feedback.text())

    def test_five_steps_resume_and_keep_completed_records(self):
        w=self.window
        w.progress.passed('py_values',1);w.progress.passed('py_values',2)
        for expected in range(1,5):
            w.advance()
            self.assertEqual(w.step,expected)
            self.assertEqual(w.phase,'learn')
        self.assertIn('5/5',w.heading.text())
        w.editor.setPlainText('private_typed_code = 123')
        w.close();self.app.processEvents()
        self.assertNotIn('private_typed_code',self.path.read_text())
        self.window=PythonWindow(self.ui,self.mono,self.path)
        self.assertEqual(self.window.unit.key,'pd_series')
        self.assertEqual(self.window.step,4)
        self.assertEqual(self.window.editor.toPlainText(),'')
        self.assertIn('py_values',self.window.progress.data['completed'])
        self.window.previous_step()
        self.assertEqual(self.window.step,3)
        self.choose('pd_frame');self.choose('pd_series')
        self.assertEqual(self.window.step,3)

    def test_guided_grading_is_not_practice_completion_and_correction_is_live(self):
        w=self.window
        w.advance();w.advance()  # loc/iloc bridge with its own checked variables.
        w.editor.setPlainText('selected = 0\nsecond = 0')
        w.run_code();self.idle();w.grade();self.idle()
        self.assertFalse(w.solved)
        process=w.engine.process
        w.editor.clear();self.run_current_example()
        self.assertIs(w.engine.process,process)
        self.assertEqual(w.progress.data['passed'],[])
        self.assertEqual(w.progress.data['completed'],[])
        w.advance()
        self.assertIsNone(w.engine.process)
        self.assertFalse(w.solved)
        self.assertEqual(w.editor.toPlainText(),'')
        self.assertNotIn('통과',w.feedback.text())

    def test_independent_csv_step_prepares_its_own_file(self):
        self.choose('pd_csv')
        w=self.window
        w.advance();w.advance();w.advance()
        self.assertIn('mini-ko.csv',w.instructions.toPlainText())
        self.run_current_example()
        self.assertIn('서울,종로',w.output.toPlainText())
        w.advance();self.idle()
        self.assertEqual((w.phase,w.variant),('example',0))
        self.assertIn('scores.csv',w.instructions.toPlainText())
        self.assertFalse(w.load_example_button.isVisible())

    def test_practice_can_revisit_teaching_without_losing_completion(self):
        w=self.window
        w.progress.passed(w.unit.key,1);w.progress.passed(w.unit.key,2)
        before=json.loads(json.dumps(w.progress.data))
        w.phase,w.variant='practice2',2
        w.render()
        self.assertTrue(w.relearn_button.isVisible())
        self.assertNotIn('직접 해볼 코드',w.instructions.toPlainText())
        w.editor.setFocus()
        QTest.keyClick(w.editor,Qt.Key.Key_F3)
        self.app.processEvents()
        self.assertEqual((w.phase,w.step,w.variant),('learn',0,0))
        self.assertEqual(w.progress.data['completed'],before['completed'])
        self.assertEqual(w.progress.data['passed'],before['passed'])
        self.assertIn('import pandas as pd',w.instructions.toPlainText())


if __name__=='__main__': unittest.main()
