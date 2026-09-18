"""Native, single-window Jupyter UI acceptance; uses an actual owned VM."""
import argparse
import json
from pathlib import Path
import tempfile
import time
from unittest.mock import patch
from PySide6.QtCore import Qt, QTimer
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QMessageBox
from native_app import create_application
from study_window import StudyWindow
from python_quiz_dialog import QuizDialog
from .proof import fingerprint


def check(runtime,capture_dir=None):
    app,ui,mono=create_application();passed=[]
    def wait(predicate,timeout=90):
        deadline=time.monotonic()+timeout
        # time.sleep releases the GIL while the real setup/transport worker
        # runs. Repeated QtTest.qWait calls can starve Python worker threads.
        while not predicate() and time.monotonic()<deadline:app.processEvents();time.sleep(.01)
        app.processEvents()
        if not predicate():raise AssertionError('UI timeout: '+page.status.text())
    def record(label):passed.append(label);print('NOTEBOOK_UI_PASS '+label,flush=True)
    with tempfile.TemporaryDirectory(prefix='shellground-notebook-ui-') as temporary:
        window=StudyWindow(ui,mono,Path(temporary)/'progress.json',mode='python');window.show();app.processEvents()
        python=window.pages['python'];python.python_sections.setCurrentIndex(1);app.processEvents()
        page=python.notebook;page.engine.root=runtime
        try:
            assert page.window() is window and python.window() is window
            assert not page.engine.process and not page.prepared
            quiz=QuizDialog(python.progress,python,practice_handler=window.open_related_practice)
            quiz.index=next(i for i,q in enumerate(quiz.questions) if q['id']=='notebook-execution-order')
            quiz.render();quiz.tabs.setCurrentIndex(2)
            choice=next(i for i in range(quiz.practice_picker.count()) if quiz.practice_picker.itemData(i)['course']=='notebook')
            quiz.practice_picker.setCurrentIndex(choice)
            # The application uses a modal exec(), not a modeless show().
            # Exercise the same focus restoration after the dialog accepts.
            QTimer.singleShot(0,quiz.practice_open.click);quiz.exec();app.processEvents()
            assert not quiz.isVisible() and page.unit['key']=='jupyter_order'
            # Offscreen Qt has no window manager to activate the main window
            # after a modal dialog hides. Restore the test's keyboard target
            # explicitly; otherwise widget-local keys work but F5 shortcuts
            # are still routed to the now-hidden dialog.
            window.activateWindow();wait(lambda:app.activeWindow() is window)
            assert page.window() is window and page.engine.process is None and not page.prepared
            assert not page.progress.data['completed'] and not python.progress.data['quiz']
            page.index=0;page.phase='learn';page.variant=0;page.step=0
            page.load_document(page.problem['cells']);page.render()
            record('same_window_lazy_notebook')
            page.advance();page.advance();assert page.step==2
            page.save();saved=json.loads(page.progress.path.read_text());assert saved['resume']['step']==2
            assert not saved['completed'] and not saved['passed']
            record('microstep_saved_without_completion')
            page.phase='practice1';page.variant=1;page.load_document(page.problem['cells']);page.render()
            assert all('내용 숨김' in page.course.item(i).text() for i in range(page.course.count()))
            page.start();wait(lambda:not page.busy and page.prepared)
            record('actual_vm_and_bash_ready')
            page.grade();wait(lambda:not page.busy);assert not page.solved
            generation=page.identity['generation'];page.task_tabs.setCurrentIndex(0)
            with patch.object(QMessageBox,'question',return_value=QMessageBox.StandardButton.Yes):
                index=page.kernels.findData('sg-basic');page.kernels.setCurrentIndex(index);page.select_kernel(index)
            wait(lambda:not page.busy)
            assert page.identity['generation']!=generation
            cell=next(c for c in page.cells if c.kind=='code');before=cell.editor.toPlainText()
            cell.editor.setFocus();QTest.keyClick(cell.editor,Qt.Key.Key_Return,Qt.KeyboardModifier.ShiftModifier)
            wait(lambda:not page.busy and cell.last is not None)
            assert cell.editor.toPlainText()==before and cell.label.text().startswith('In [')
            record('shift_enter_executes_actual_selected_kernel')
            actual=page.identity['generation'];QTest.keyClick(cell.editor,Qt.Key.Key_F5)
            wait(lambda:not page.busy)
            assert page.solved and page.task_tabs.currentIndex()==1,(page.status.text(),page.feedback.toPlainText(),
                str(app.focusWidget()),str(app.activeWindow()))
            assert page.identity['generation']==actual
            assert 'jupyter_select:1' in page.progress.data['passed']
            record('failed_grade_same_document_repair')
            if capture_dir:
                capture_dir.mkdir(parents=True,exist_ok=True);window.grab().save(str(capture_dir/'notebook-grade.png'))
            page.task_tabs.setCurrentIndex(0);page.restart_kernel(confirmed=True);wait(lambda:not page.busy)
            assert cell.editor.toPlainText()==before and '이전 커널' in cell.label.text()
            page.grade();wait(lambda:not page.busy);assert not page.solved
            record('restart_keeps_code_not_namespace_or_old_output_pass')
            page.task_tabs.setCurrentIndex(0);page.run_all();wait(lambda:not page.busy);page.grade();wait(lambda:not page.busy);assert page.solved
            page.task_tabs.setCurrentIndex(0)
            if capture_dir:window.grab().save(str(capture_dir/'notebook-cells.png'))
            page.index=3;page.phase='example';page.variant=0;page.step=0;page.prepared=False
            page.load_document(page.problem['cells']);page.render();page.start();wait(lambda:not page.busy and page.prepared)
            page.work_tabs.setCurrentIndex(1)
            source=page.problem['commands'][0]
            page.terminal.input_bytes.emit((source+'\n').encode())
            # Wait on actual registered state through the existing serialized
            # worker, without shell stdout string matching as the assertion.
            deadline=time.monotonic()+15
            while time.monotonic()<deadline:
                page.refresh_kernels();wait(lambda:not page.busy)
                if page.kernels.findData('analysis-project')>=0:break
                QTest.qWait(100)
            assert page.kernels.findData('analysis-project')>=0
            record('typed_bash_registration_refreshes_real_list')
            if capture_dir:window.grab().save(str(capture_dir/'notebook-bash.png'))
            process,session=page.engine.process,page.engine.session_dir
            python.python_sections.setCurrentIndex(0);app.processEvents();assert page.isHidden()
            assert process.poll() is None and python.python_stack.currentIndex()==0
            window.close();wait(lambda:window._shutdown_ready,30)
            assert process.poll() is not None and not session.exists()
            record('hidden_notebook_vm_and_readers_close')
        finally:
            if not window._shutdown_ready:
                window.close();wait(lambda:window._shutdown_ready,30)
    return passed


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--runtime',type=Path,required=True)
    parser.add_argument('--report',type=Path,required=True);parser.add_argument('--capture-dir',type=Path)
    args=parser.parse_args();started=time.monotonic();report={'state':'failed','fingerprint':fingerprint(ui=True)}
    try:report.update(state='complete',passed=check(args.runtime,args.capture_dir))
    except BaseException as error:report['error']=str(error);raise
    finally:
        report['seconds']=round(time.monotonic()-started,2);args.report.parent.mkdir(parents=True,exist_ok=True)
        args.report.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)


if __name__=='__main__':main()
