import json
import os
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch

os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from PySide6.QtWidgets import QMessageBox
from native_app import create_application
from python_teaching.practice_links import load_links,resolve_target
from python_quiz_dialog import QuizDialog
from study_window import StudyWindow


class PracticeLinkDataTests(unittest.TestCase):
    def test_all_questions_mapped_without_false_completion(self):
        links=load_links();self.assertEqual(len(links),61)
        self.assertEqual(sum(bool(link['targets']) for link in links.values()),56)
        for link in links.values():
            self.assertIs(link['completion_equivalence'],False)
            self.assertIs(link['original_followup_implemented_as_written'],False)
            self.assertTrue(link['remaining_gap'])
            for target in link['targets']:self.assertEqual(resolve_target(target),target)
        self.assertTrue(any(target['unit_key']=='pip_install' for target in links['install-versus-import']['targets']))

    def test_unknown_target_or_boolean_variant_rejected(self):
        for target in (None,dict(course='linux',unit_key='pwd',problem_index=0),
                       dict(course='python',unit_key='missing',problem_index=0),
                       dict(course='python',unit_key='py_kernel',problem_index=True),
                       dict(course='conda',unit_key='pip_install',problem_index=-1)):
            with self.subTest(target=target),self.assertRaises(ValueError):resolve_target(target)


class PracticeLinkUITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app,cls.ui,cls.mono=create_application()
    def setUp(self):
        self.folder=tempfile.TemporaryDirectory();self.path=Path(self.folder.name)/'progress-v3.json'
        self.host=StudyWindow(self.ui,self.mono,self.path,mode='python');self.host.show();self.app.processEvents()
        self.page=self.host.pages['python'];self.dialogs=[]
    def wait(self,predicate):
        end=time.monotonic()+15
        while not predicate() and time.monotonic()<end:self.app.processEvents();time.sleep(.01)
        self.assertTrue(predicate())
    def tearDown(self):
        for dialog in self.dialogs:dialog.close()
        self.host.close();self.wait(lambda:not self.host.isVisible());self.folder.cleanup()
    def dialog(self,key):
        dialog=QuizDialog(self.page.progress,self.page,practice_handler=self.host.open_related_practice)
        self.dialogs.append(dialog)
        dialog.index=next(i for i,q in enumerate(dialog.questions) if q['id']==key)
        dialog.render();dialog.tabs.setCurrentIndex(2);dialog.show();self.app.processEvents()
        return dialog

    def test_notebook_link_is_nested_and_does_not_run_or_complete(self):
        self.page.editor.setPlainText('keep_python_input = 42')
        target=dict(course='notebook',unit_key='jupyter_order',problem_index=1)
        self.assertTrue(self.host.open_related_practice(target));notebook=self.page.notebook
        self.assertIs(notebook.window(),self.host)
        self.assertEqual(self.page.python_stack.currentIndex(),1)
        self.assertEqual((notebook.unit['key'],notebook.phase),('jupyter_order','practice1'))
        self.assertIsNone(notebook.engine.process);self.assertFalse(notebook.prepared)
        self.assertFalse(notebook.progress.data['completed']);self.assertFalse(notebook.progress.data['passed'])
        self.assertEqual(self.page.editor.toPlainText(),'keep_python_input = 42')

    def test_declined_notebook_link_keeps_cells_and_selected_section(self):
        target=dict(course='notebook',unit_key='jupyter_order',problem_index=1)
        self.assertTrue(self.host.open_related_practice(target));notebook=self.page.notebook
        notebook.cells[-1].editor.setPlainText('preserved = 123')
        self.page.python_sections.setCurrentIndex(0)
        with patch('notebook_app.QMessageBox.question',return_value=QMessageBox.StandardButton.No):
            self.assertFalse(self.host.open_related_practice(dict(target,unit_key='jupyter_restart')))
        self.assertEqual(self.page.python_stack.currentIndex(),0)
        self.assertEqual(notebook.cells[-1].editor.toPlainText(),'preserved = 123')
        self.assertEqual(notebook.unit['key'],'jupyter_order')

    def test_explicit_python_navigation_no_auto_execution_or_completion(self):
        dialog=self.dialog('notebook-execution-order')
        before=dict(self.page.progress.data['quiz'])
        with patch.object(self.page.engine,'start') as reset,patch.object(self.page.engine,'execute') as execute:
            dialog.practice_open.click();self.app.processEvents()
            reset.assert_not_called();execute.assert_not_called()
        self.assertEqual((self.page.unit.key,self.page.variant,self.page.phase),('py_kernel',0,'example'))
        self.assertFalse(dialog.isVisible());self.assertIsNone(self.page.engine.process)
        self.assertEqual(self.page.progress.data['quiz'],before)
        self.assertEqual(self.page.progress.data['completed'],[]);self.assertEqual(self.page.progress.data['passed'],[])

    def test_declined_python_reset_preserves_code_process_and_dialog(self):
        self.page.editor.setPlainText('preserved_value = 42');self.page.run_code();self.wait(lambda:not self.page.busy)
        process=self.page.engine.process;position=(self.page.index,self.page.phase,self.page.variant)
        dialog=self.dialog('notebook-execution-order')
        with patch('python_app.QMessageBox.question',return_value=QMessageBox.StandardButton.No):dialog.practice_open.click()
        self.assertTrue(dialog.isVisible());self.assertEqual(self.page.editor.toPlainText(),'preserved_value = 42')
        self.assertIs(self.page.engine.process,process);self.assertIsNone(process.poll())
        self.assertEqual((self.page.index,self.page.phase,self.page.variant),position)
        with patch('python_app.QMessageBox.question',return_value=QMessageBox.StandardButton.Yes):dialog.practice_open.click()
        self.assertFalse(dialog.isVisible());self.assertIsNotNone(process.poll());self.assertEqual(self.page.editor.toPlainText(),'')

    def test_conda_link_uses_same_window_and_keeps_python_input(self):
        self.page.editor.setPlainText('keep_this = 7')
        dialog=self.dialog('install-versus-import')
        index=next(i for i in range(dialog.practice_picker.count()) if dialog.practice_picker.itemData(i)['unit_key']=='pip_install')
        dialog.practice_picker.setCurrentIndex(index)
        dialog.practice_open.click();self.app.processEvents()
        conda=self.host.pages['conda']
        self.assertIs(conda.window(),self.host);self.assertEqual(self.host.active_mode,'conda')
        self.assertEqual(conda.unit['key'],'pip_install');self.assertIsNone(conda.engine.process)
        self.assertFalse(conda.terminal.connected);self.assertEqual(self.page.editor.toPlainText(),'keep_this = 7')
        self.assertFalse(conda.progress.data['completed']);self.assertFalse(self.page.progress.data['quiz'])

    def test_cancel_existing_conda_practice_keeps_terminal_and_active_mode(self):
        self.host.switch_mode('conda');conda=self.host.pages['conda']
        conda.terminal.connected=True;before=(conda.index,conda.phase,conda.variant)
        self.host.switch_mode('python')
        target=dict(course='conda',unit_key='pip_install',problem_index=1)
        with patch('conda_app.QMessageBox.question',return_value=QMessageBox.StandardButton.No):
            self.assertFalse(self.host.open_related_practice(target))
        self.assertEqual(self.host.active_mode,'python');self.assertTrue(conda.terminal.connected)
        self.assertEqual((conda.index,conda.phase,conda.variant),before)
        with patch('conda_app.QMessageBox.question',return_value=QMessageBox.StandardButton.Yes):
            self.assertTrue(self.host.open_related_practice(target))
        self.assertEqual((conda.unit['key'],conda.phase),('pip_install','practice1'))
        self.assertFalse(conda.terminal.connected);self.assertIsNone(conda.engine.process)

    def test_unmapped_concept_is_explained_without_broken_button(self):
        dialog=self.dialog('cloud-session-storage')
        self.assertFalse(dialog.practice_open.isEnabled());self.assertEqual(dialog.practice_picker.count(),0)
        self.assertIn('아직 없습니다',dialog.practice_text.toPlainText())

    def test_same_practice_reuses_state_and_busy_navigation_is_blocked(self):
        target=dict(course='python',unit_key='py_kernel',problem_index=0)
        self.assertTrue(self.host.open_related_practice(target));self.page.editor.setPlainText('keep = 99')
        with patch('python_app.QMessageBox.question') as question:
            self.assertTrue(self.host.open_related_practice(target));question.assert_not_called()
        self.assertEqual(self.page.editor.toPlainText(),'keep = 99')
        self.page.busy=True
        try:self.assertFalse(self.host.open_related_practice(dict(course='conda',unit_key='pip_install',problem_index=0)))
        finally:self.page.busy=False
        self.assertNotIn('conda',self.host.pages)


if __name__=='__main__':unittest.main()
