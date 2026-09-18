import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import tempfile
from pathlib import Path
import time
import unittest
from unittest.mock import patch
from PySide6.QtWidgets import QApplication
from conda_app import CondaWindow


class IdleEngine:
    bridge=None
    def __init__(self):self.closed=False
    def close(self):self.closed=True
    def cancel_pending(self):pass
    def send(self,data):pass
    def resize(self,*size):pass
    def grade_problem(self,answers):return {'passed':False,'checks':[{'label':'환경 수정 필요','passed':False}]}


class CondaUITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=QApplication.instance() or QApplication([])
    def setUp(self):self.directory=tempfile.TemporaryDirectory();self.path=Path(self.directory.name)/'conda-progress-v1.json';self.windows=[]
    def open(self):
        window=CondaWindow('sans','monospace',self.path,IdleEngine());self.windows.append(window);window.show();self.app.processEvents();return window
    def wait(self,predicate):
        until=time.monotonic()+4
        while not predicate() and time.monotonic()<until:self.app.processEvents();time.sleep(.01)
        self.assertTrue(predicate())
    def tearDown(self):
        for window in self.windows:window.close();self.wait(lambda w=window:w.closed)
        self.directory.cleanup()
    def test_microstep_resume_separate_progress_and_bounded_close(self):
        window=self.open();window.advance();self.assertEqual(window.step,1);window.close();self.wait(lambda:window.closed)
        self.assertTrue(window.engine.closed);other=self.open();self.assertEqual(other.step,1)
        self.assertFalse((self.path.parent/'python-progress-v1.json').exists())
    def test_failed_grade_keeps_terminal_and_answer_edits(self):
        window=self.open();window.phase='example';window.render();window.terminal.connected=True
        window.answers['manager_version'].setText('incorrect');window.grade();self.wait(lambda:not window.busy)
        self.assertEqual(window.tabs.currentIndex(),1);self.assertTrue(window.terminal.connected)
        window.tabs.setCurrentIndex(0);window.answers['manager_version'].setText('corrected')
        self.assertFalse(window.solved);self.assertTrue(window.grade_button.isEnabled())

    def test_pass_immediately_updates_navigation_without_resetting_answers_or_tab(self):
        window=self.open();window.phase='practice2';window.variant=2
        window.progress.passed(window.unit['key'],1);window.render();window.terminal.connected=True
        answers=dict(window.answers)
        for widget in answers.values():
            if hasattr(widget,'setText'):widget.setText('retained answer')
        with patch.object(window.engine,'grade_problem',return_value={'passed':True,'checks':[]}):
            window.grade();self.wait(lambda:not window.busy)
        self.assertIn('[완료]',window.list.item(window.index).text())
        self.assertIn('평가 중 학습 내용 숨김',window.list.item(window.index).text())
        self.assertEqual(window.tabs.currentIndex(),1);self.assertEqual(window.answers,answers)
        for widget in answers.values():
            if hasattr(widget,'text'):self.assertEqual(widget.text(),'retained answer')
        self.assertTrue(window.terminal.connected)
    def test_test_titles_hidden_and_random_exit_restores_position(self):
        window=self.open();window.phase='practice1';window.variant=1;window.render()
        self.assertNotIn('Conda와 실행',window.list.item(0).text())
        window.random_return=(0,'learn',1,0);window.phase='random';window.index=3;window.stop_random()
        self.assertEqual((window.index,window.phase,window.step),(0,'learn',1));self.assertIsNone(window.random_return)

    def test_learning_shows_current_fixture_command_not_generic_template(self):
        window=self.open();window.index=next(i for i,u in enumerate(window.units) if u['key']=='conda_activate')
        window.step=0;window.render();text=window.instructions.toPlainText()
        self.assertIn('conda activate sg-work',text);self.assertNotIn('sg-project',text)
        self.assertIn('소단계 1/3',text)

    def test_resume_preparation_is_read_only_and_preserves_saved_step(self):
        window=self.open();window.index=next(i for i,u in enumerate(window.units) if u['key']=='conda_create')
        window.step=2;window.save();window.close();self.wait(lambda:window.closed)
        other=self.open();self.assertEqual(other.step,2)
        self.assertTrue(other.preparation_button.isVisible())
        text=other.preparation_text();self.assertIn('conda create --name sg-analysis',text)
        self.assertIn('반복 실행하지 마세요',text);self.assertNotIn('sg-project',text)
        captured=[];other.show_reading=lambda title,body:captured.append(body)
        other.preparation_button.click();self.assertEqual(captured,[text]);self.assertEqual(other.step,2)
        # F2 opens the initial fixture but must not erase the saved learning position.
        with patch.object(other,'job'):
            other.start();self.assertEqual(other.step,2)
        self.assertTrue(other.preparation_notice.isVisible())
        other.phase='practice1';other.variant=1;other.render()
        self.assertFalse(other.preparation_button.isVisible());self.assertEqual(other.preparation_text(),'')
        other.show_preparation();self.assertEqual(len(captured),1)

    def test_install_preparation_has_four_steps_and_separate_resume(self):
        window=self.open();original=[u['key'] for u in window.units]
        window.step=1;window.save();window.open_setup()
        self.assertTrue(window.setup_mode);self.assertEqual(len(window.learning_steps),4)
        self.assertEqual([u['key'] for u in window.units],original)
        self.assertEqual(window.list.count(),20);self.assertFalse(window.tabs.isTabEnabled(2))
        self.assertIn('Anaconda',window.instructions.toPlainText())
        window.advance();window.advance();window.close();self.wait(lambda:window.closed)
        other=self.open();self.assertTrue(other.setup_mode);self.assertEqual(other.step,2)
        self.assertEqual(other.progress.data['positions'][original[0]]['step'],1)
        other.select(0);self.assertFalse(other.setup_mode);self.assertEqual(other.step,1)
        self.assertTrue(other.tabs.isTabEnabled(2))

    def test_install_assessment_keeps_existing_terminal_and_failed_retry(self):
        window=self.open();window.open_setup();window.step=3
        window.terminal.connected=True
        with patch.object(window,'start') as start:
            window.advance();start.assert_not_called()
        self.assertEqual(window.phase,'practice1');self.assertTrue(window.grade_button.isEnabled())
        self.assertNotIn(' -b ',window.instructions.toPlainText())
        with patch.object(window,'start') as start:
            window.setup_button.click();self.assertEqual(window.phase,'learn');self.assertTrue(window.terminal.connected)
            window.advance();start.assert_not_called()
        with patch.object(window.engine,'grade_setup',create=True,return_value={'passed':False,'checks':[]}):
            window.grade();self.wait(lambda:not window.busy)
        self.assertTrue(window.terminal.connected);self.assertFalse(window.solved)
        window.tabs.setCurrentIndex(0)
        with patch.object(window.engine,'grade_setup',create=True,return_value={'passed':True,'checks':[]}):
            window.grade();self.wait(lambda:not window.busy)
        self.assertIn('conda_install_once',window.progress.data['setup_completed'])
        self.assertEqual(window.progress.data['completed'],[])
        self.assertEqual(window.progress.data['passed'],[])
        self.assertIn('[완료]',window.setup_button.text())
        self.assertEqual(window.tabs.currentIndex(),1)
        window.advance();self.assertFalse(window.setup_mode)

    def test_install_license_is_read_only_and_uses_verified_guest_data(self):
        window=self.open();window.open_setup()
        self.assertFalse(window.license_button.isEnabled())
        window.setup_ready={'prefix':'/home/learner/setup-practice/miniconda-a','installer':
            dict(path='/opt/shellground/conda-setup/installer.sh',url='https://repo.anaconda.com/miniconda/installer.sh',
                 sha256='verified-test-hash',subdir='linux-64',license='Actual installer license fixture')}
        window.render();captured=[];window.show_reading=lambda title,body:captured.append(body)
        with patch.object(window,'start') as start:
            window.license_button.click();start.assert_not_called()
        self.assertIn('Actual installer license fixture',captured[0]);self.assertIn('verified-test-hash',captured[0])
        self.assertEqual(window.progress.data['completed'],[])
        window.step=2;window.render()
        self.assertIn('-p /home/learner/setup-practice/miniconda-a',window.instructions.toPlainText())

    def test_pip_microstep_resume_and_test_diagnostics_without_solution(self):
        window=self.open();index=next(i for i,u in enumerate(window.units) if u['key']=='pip_remove_repair')
        window.select(index);self.assertEqual(len(window.learning_steps),4)
        window.advance();window.advance();window.close();self.wait(lambda:window.closed)
        other=self.open();self.assertEqual((other.unit['key'],other.step),('pip_remove_repair',2))
        self.assertIn('ModuleNotFoundError',other.instructions.toPlainText())
        other.phase='practice1';other.variant=1;other.render()
        text=other.instructions.toPlainText()
        self.assertIn('sg-pip-writing',text);self.assertIn('확인용 진단식',text)
        self.assertNotIn('python -m pip uninstall',text);self.assertNotIn('--find-links',text)
        self.assertTrue(all('평가 중 학습 내용 숨김' in other.list.item(i).text() for i in range(other.list.count())))


if __name__=='__main__':unittest.main()
