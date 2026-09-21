"""Bounded, temporary-profile acceptance for the packaged native window."""
import argparse
import os
from pathlib import Path
import tempfile
import time


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--capture-dir', type=Path)
    args = parser.parse_args(argv)
    if args.capture_dir:
        args.capture_dir.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
    from PySide6.QtCore import Qt
    from PySide6.QtTest import QTest
    from native_app import create_application
    from study_window import StudyWindow
    app, ui, mono = create_application()

    def wait(predicate):
        deadline = time.monotonic() + 30
        while not predicate() and time.monotonic() < deadline:
            app.processEvents()
            QTest.qWait(10)
        app.processEvents()
        if not predicate():
            raise RuntimeError('Packaged study UI operation did not finish')

    with tempfile.TemporaryDirectory(prefix='shellground-study-ui-') as folder:
        window = StudyWindow(ui, mono, Path(folder) / 'progress-v3.json', mode='simulation')
        process = None
        try:
            window.show()
            app.processEvents()
            linux = window.pages['linux']
            linux.open_python()
            app.processEvents()
            page = window.pages['python']
            assert page.window() is window and not page.isWindow()
            assert [w for w in app.topLevelWidgets() if w.isVisible()] == [window]
            source = 'print("SHELLGROUND_SHIFT_ENTER_OK")'
            page.editor.setPlainText(source)
            page.editor.setFocus()
            QTest.keyClick(page.editor, Qt.Key.Key_Return, Qt.KeyboardModifier.ShiftModifier)
            wait(lambda: not page.busy)
            assert page.editor.toPlainText() == source
            assert 'SHELLGROUND_SHIFT_ENTER_OK' in page.output.toPlainText(), page.output.toPlainText()
            process = page.engine.process
            assert process is not None and process.poll() is None
            window.switch_mode('linux')
            assert window.stack.currentWidget() is linux
            window.switch_mode('python')
            assert window.stack.currentWidget() is page
            assert page.editor.toPlainText() == source
            QTest.keyClick(page.editor, Qt.Key.Key_F6)
            app.processEvents()
            assert page.step == 1 and linux.phase == 'learn'
            from python_quiz_dialog import QuizDialog
            dialog=QuizDialog(page.progress,page,practice_handler=window.open_related_practice)
            dialog.index=next(i for i,q in enumerate(dialog.questions) if q['id']=='install-versus-import')
            dialog.render();dialog.tabs.setCurrentIndex(2);dialog.show();app.processEvents()
            target=next(i for i in range(dialog.practice_picker.count())
                        if dialog.practice_picker.itemData(i)['unit_key']=='pip_install')
            dialog.practice_picker.setCurrentIndex(target);dialog.practice_open.click();app.processEvents()
            assert not dialog.isVisible()
            conda=window.pages['conda']
            assert conda.unit['key']=='pip_install' and conda.engine.process is None
            assert conda.window() is window and not conda.isWindow()
            assert page.editor.toPlainText()==source and page.engine.process is process
            assert not page.progress.data['quiz'] and not conda.progress.data['passed']
            if args.capture_dir:
                assert window.grab().save(str(args.capture_dir / 'quiz-related-conda.png'))
                window.switch_mode('python')
                dialog.render();dialog.tabs.setCurrentIndex(2);dialog.show();app.processEvents()
                assert dialog.grab().save(str(args.capture_dir / 'quiz-related-practice.png'))
                dialog.close()
            # New pandas teaching is checked through the frozen UI and worker,
            # without replaying any previously verified course exercises.
            window.switch_mode('python')
            page.editor.clear()
            page.select_lesson(next(i for i,u in enumerate(page.units) if u.key=='pd_series'))
            assert len(page.unit.guided_steps)==5 and '1/5' in page.heading.text()
            page.load_example_button.click()
            page.editor.setFocus()
            QTest.keyClick(page.editor, Qt.Key.Key_Return, Qt.KeyboardModifier.ShiftModifier)
            wait(lambda: not page.busy)
            assert 'Traceback' not in page.output.toPlainText()
            process=page.engine.process
            page.grade_button.click();wait(lambda: not page.busy)
            assert page.solved and not page.progress.data['passed']
            page.task_tabs.setCurrentIndex(0)
            if args.capture_dir:
                app.processEvents()
                assert window.grab().save(str(args.capture_dir / 'pandas-guided-learning.png'))
            for _ in range(4):page.advance()
            assert page.step==4 and page.phase=='learn'
            page.load_example_button.click();page.run_code();wait(lambda:not page.busy)
            process=page.engine.process
            page.grade();wait(lambda:not page.busy)
            assert page.solved and not page.progress.data['completed']
            # Reproduce the reported stale blank preview using the exact code
            # from Matplotlib 01 / application 2, not a different demo plot.
            page.editor.clear()
            page.select_lesson(next(i for i,u in enumerate(page.units) if u.key=='plot_line'))
            page.phase,page.variant='practice2',2
            page.render()
            page.editor.setPlainText('old, old_ax = plt.subplots()')
            page.run_code();wait(lambda:not page.busy)
            blank=page.figure.pixmap().toImage()
            page.editor.setPlainText('measured_2 = measured-2\nfig, ax = plt.subplots()\nax.plot(t, measured)\nax.plot(t, measured_2)')
            page.editor.setFocus()
            QTest.keyClick(page.editor,Qt.Key.Key_Return,Qt.KeyboardModifier.ShiftModifier)
            wait(lambda:not page.busy)
            process=page.engine.process
            assert page.figure_picker.currentData()==2
            assert not page.figure.pixmap().isNull() and page.figure.pixmap().toImage()!=blank
            assert page.figure.pixmap().width() <= page.figure_area.viewport().width()
            assert page.figure.pixmap().height() <= page.figure_area.viewport().height()
            assert page.output_tabs.currentIndex()==1
            page.grade();wait(lambda:not page.busy)
            assert page.solved
            page.task_tabs.setCurrentIndex(0)
            if args.capture_dir:
                app.processEvents()
                assert window.grab().save(str(args.capture_dir / 'matplotlib-two-lines.png'))
            window.switch_mode('linux')
        finally:
            window.close()
            wait(lambda: not window.isVisible())
            if process is not None:
                assert process.poll() is not None, 'Hidden Python process survived application close'
        saved = Path(folder, 'python-progress-v1.json').read_text()
        assert 'SHELLGROUND_SHIFT_ENTER_OK' not in saved
        assert not window.pages
        print('Packaged single-window navigation, Shift+Enter, scoped F6, quiz-to-pip navigation, pandas learning, Matplotlib current-Figure display after blank preview and two-line grading, hidden-process cleanup PASS', flush=True)
    return 0
