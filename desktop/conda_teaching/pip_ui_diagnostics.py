"""Source/frozen native UI acceptance for real pip, with temporary progress."""
import argparse
import json
import os
from pathlib import Path
import sys
import tempfile
import time
from .engine import CondaEngine


def check_ui(engine,capture_dir=None):
    os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
    from native_app import create_application
    from conda_app import CondaWindow
    from python_app import PythonWindow
    from study_window import StudyWindow
    from PySide6.QtCore import Qt
    from PySide6.QtTest import QTest
    from shiboken6 import isValid

    app,ui,mono=create_application();started=time.monotonic()
    capture_dir=Path(capture_dir) if capture_dir else None
    if capture_dir:capture_dir.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='shellground-pip-ui-') as directory:
        path=Path(directory)/'conda-progress-v1.json'
        def factory(mode):
            if mode=='conda':return CondaWindow(ui,mono,path,engine)
            if mode=='python':return PythonWindow(ui,mono,Path(directory)/'python-progress-v1.json')
            raise AssertionError('Unexpected test room')
        host=StudyWindow(ui,mono,Path(directory)/'progress-v3.json',mode='conda',page_factory=factory)
        window=host.pages['conda'];host.show();process=session=None
        def screen():return '\n'.join(window.terminal.screen.display)
        def prompt():return screen().rstrip().split('\n')[-1].strip()
        def wait(predicate,seconds=125):
            deadline=time.monotonic()+seconds
            while not predicate() and time.monotonic()<deadline:app.processEvents();QTest.qWait(15)
            if not predicate():
                raise AssertionError('pip UI timed out: '+(window.feedback.toPlainText()+'\n'+screen() if isValid(window) else 'closed'))
        def capture(name):
            if capture_dir:
                app.processEvents();assert host.grab().save(str(capture_dir/name))
        def grade(expected):
            QTest.keyClick(window.terminal,Qt.Key.Key_F5);wait(lambda:not window.busy)
            assert window.solved is expected,window.feedback.toPlainText()
            assert window.tabs.currentIndex()==1
        try:
            window.index=next(i for i,u in enumerate(window.units) if u['key']=='pip_remove_repair')
            window.phase='example';window.variant=0;window.render();window.try_button.click()
            wait(lambda:not window.busy)
            assert window.terminal.connected,window.feedback.toPlainText()
            process,session=engine.process,engine.session_dir;sid=engine.bridge.sid
            wait(lambda:prompt().endswith('$'),20)
            assert window.window() is host and not window.isWindow()
            assert [w for w in app.topLevelWidgets() if w.isVisible()]==[host]
            grade(False);assert window.terminal.connected
            window.tabs.setCurrentIndex(0)
            window.terminal.input_bytes.emit(b'python -m pip uninstall numpy\r')
            wait(lambda:prompt().endswith('Proceed (Y/n)?'),25)
            capture('pip-confirmation.png')
            window.terminal.input_bytes.emit(b'n\r');wait(lambda:prompt().endswith('$'),20)
            grade(False)
            assert engine.bridge.sid==sid
            window.tabs.setCurrentIndex(0)
            window.terminal.input_bytes.emit(b'python -m pip uninstall numpy\r')
            wait(lambda:prompt().endswith('Proceed (Y/n)?'),25)
            window.terminal.input_bytes.emit(b'y\r')
            wait(lambda:prompt().endswith('$') and 'Successfully uninstalled numpy' in screen(),25)
            grade(True);assert engine.bridge.sid==sid
            capture('pip-grade.png')
            saved=json.loads(path.read_text());assert 'pip_remove_repair:0' in saved['passed']
            assert 'pip_remove_repair' not in saved['completed']
            window.phase='learn';window.step=2;window.save();window.render()
            assert 'ModuleNotFoundError' in window.instructions.toPlainText()
            capture('pip-learning.png')
            host.switch_mode('python');host.switch_mode('conda')
            assert host.pages['conda'] is window and engine.bridge.sid==sid
            host.switch_mode('python')
        finally:
            readers=list(window.readers) if isValid(window) else []
            host.close();wait(lambda:not host.isVisible(),30)
            for reader in readers:assert reader.wait(3000),'pip terminal reader survived close'
            if process:assert process.poll() is not None,'pip VM survived close'
            if session:assert not session.exists(),'pip overlay survived close'
        assert 'python -m pip uninstall' not in path.read_text()
        restored=StudyWindow(ui,mono,Path(directory)/'progress-v3.json',mode='conda')
        other=restored.pages['conda']
        try:
            assert (other.unit['key'],other.step,other.phase)==('pip_remove_repair',2,'learn')
            assert other.engine.process is None
        finally:
            restored.close();wait(lambda:not restored.pages,10)
    return dict(seconds=round(time.monotonic()-started,2),frozen_application=bool(getattr(sys,'frozen',False)),
        passed=['single_window','initial_incomplete','actual_pip_question','decline_not_passed',
                'confirm_removal','same_PTY_retry','F5_result_tab','example_not_unit_completion',
                'microstep_resume','mode_roundtrip','hidden_VM_cleanup'])


def main(argv=None):
    parser=argparse.ArgumentParser();parser.add_argument('--runtime',type=Path);parser.add_argument('--capture-dir',type=Path)
    args=parser.parse_args(argv)
    print('REAL_PIP_UI_OK '+json.dumps(check_ui(CondaEngine(args.runtime),args.capture_dir),ensure_ascii=False),flush=True)
    return 0


if __name__=='__main__':raise SystemExit(main())
