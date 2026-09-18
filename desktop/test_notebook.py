import concurrent.futures
import json
import os
from pathlib import Path
import tempfile
import threading
import time
import unittest
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from notebook_teaching.course import lessons
from notebook_teaching.guest_service import Service


class NotebookContractTests(unittest.TestCase):
    def test_evidence_rejects_stale_incomplete_and_unclean_reports(self):
        from notebook_teaching.proof import fingerprint, validate
        report = dict(state='complete', fingerprint=fingerprint(),
            passed=[u['key']+':'+str(v) for u in lessons() for v in range(3)],
            vm_stopped=True, overlay_removed=True, negative=[
                'numpy_scalar_equivalent','package_removal_and_repair','direct_file_read_equivalent',
                'edited_and_old_kernel_outputs_not_saved','restart_in_wrong_environment_rejected',
                'repeat_mutation_with_trailing_output_rejected','order_in_both_environments_accepted',
                'target_kernel_recreation_equivalent'])
        validate(report)
        for changes in ({'fingerprint':'old'}, {'passed':report['passed'][:-1]},
                {'vm_stopped':False}, {'overlay_removed':False}, {'negative':[]}, {'state':'failed'}):
            with self.subTest(changes=changes), self.assertRaises(RuntimeError):
                validate(dict(report, **changes))

    def test_every_problem_has_different_fixture_goal_and_authored_solution(self):
        units=lessons();self.assertEqual(len(units),6)
        keys=set()
        for unit in units:
            self.assertNotIn(unit['key'],keys);keys.add(unit['key'])
            self.assertGreaterEqual(len(unit['steps']),2)
            self.assertEqual(len(unit['problems']),3)
            self.assertEqual(len({p['goal'] for p in unit['problems']}),3)
            for problem in unit['problems']:
                self.assertTrue(problem['expected'])
                self.assertEqual(len({c['id'] for c in problem['cells']}),len(problem['cells']))
                for cell in problem['solution']:
                    if cell['type']=='code':compile(cell['source'],'<reference>','exec')
                self.assertNotIn('F5',problem['goal'])

    def test_completed_task_timeout_is_an_error_not_an_endless_poll(self):
        service=Service.__new__(Service);service.lock=threading.Lock()
        future=concurrent.futures.Future();future.set_exception(TimeoutError('kernel terminated'))
        service.jobs={'job':future}
        with self.assertRaisesRegex(TimeoutError,'kernel terminated'):
            service.dispatch({'action':'poll','job':'job'})

    def test_pending_task_yields_without_busy_polling(self):
        service=Service.__new__(Service);service.lock=threading.Lock();service.jobs={'job':concurrent.futures.Future()}
        start=time.monotonic()
        self.assertEqual(service.dispatch({'action':'poll','job':'job'}),{'done':False})
        self.assertGreaterEqual(time.monotonic()-start,.45)


class NotebookWidgetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from native_app import create_application
        cls.app,cls.ui,cls.mono=create_application()

    def test_long_grade_list_expands_shared_pane_without_hiding_code(self):
        from study_window import StudyWindow
        with tempfile.TemporaryDirectory() as directory:
            host=StudyWindow(self.ui,self.mono,Path(directory)/'progress.json',mode='python')
            host.show();host.pages['python'].python_sections.setCurrentIndex(1);self.app.processEvents()
            page=host.pages['python'].notebook
            page.feedback.set_results('목표 달성',[{'label':'별도 새 커널의 문서 재현 · 마지막 셀 반복','passed':True} for _ in range(16)])
            page.task_tabs.setCurrentIndex(1);self.app.processEvents();page.fit_feedback();self.app.processEvents()
            self.assertEqual(page.feedback.verticalScrollBar().maximum(),0)
            self.assertGreaterEqual(page.task_splitter.sizes()[1],220)
            host.close();deadline=time.monotonic()+10
            while not host._shutdown_ready and time.monotonic()<deadline:self.app.processEvents();time.sleep(.01)
            self.assertTrue(host._shutdown_ready)

    def test_nested_page_is_lazy_switch_safe_and_closes(self):
        from python_app import PythonWindow
        with tempfile.TemporaryDirectory() as directory:
            parent=PythonWindow(self.ui,self.mono,Path(directory)/'python-progress-v1.json');parent.show()
            parent.python_sections.setCurrentIndex(1);self.app.processEvents();page=parent.notebook
            self.assertIs(page.window(),parent);self.assertIsNone(page.engine.process)
            old=list(page.cells);page.load_document(page.units[1]['problems'][1]['cells']);self.app.processEvents()
            self.assertTrue(all(c.isHidden() for c in old))
            self.assertEqual(len(page.cells),3)
            page.advance();page.advance();page.save()
            self.assertEqual(json.loads(page.progress.path.read_text())['resume']['step'],2)
            self.assertFalse(page.progress.data['completed'])
            page.busy=True;parent.python_sections.setCurrentIndex(0)
            self.assertEqual(parent.python_sections.currentIndex(),1)
            page.busy=False;parent.python_sections.setCurrentIndex(0)
            self.assertTrue(all(a.isEnabled() for a in parent.actions()))
            parent.close();deadline=time.monotonic()+10
            while not parent.study_closed and time.monotonic()<deadline:self.app.processEvents();time.sleep(.01)
            self.assertTrue(parent.study_closed);self.assertTrue(page.study_closed)


if __name__=='__main__':unittest.main()
