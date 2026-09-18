"""Opt-in real installation acceptance through the native application UI.

Uses a temporary progress profile and the engine's disposable guest overlay.
The same flow runs from source or the distributed executable. It never uses
the user's host Conda installation or writes their learning progress.
"""
import argparse
import json
import os
from pathlib import Path
import sys
import tempfile
import time

from conda_teaching.engine import CondaEngine


def check_setup_ui(engine, capture_dir=None):
    os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
    from native_app import create_application
    from conda_app import CondaWindow
    from python_app import PythonWindow
    from study_window import StudyWindow
    from PySide6.QtCore import Qt
    from PySide6.QtTest import QTest
    from shiboken6 import isValid

    app, ui, mono = create_application()
    started = time.monotonic()
    process = session = None
    capture_dir = Path(capture_dir) if capture_dir is not None else None
    if capture_dir is not None:
        capture_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='shellground-setup-ui-') as directory:
        path = Path(directory) / 'conda-progress-v1.json'

        def factory(mode):
            if mode == 'conda':
                return CondaWindow(ui, mono, path, engine)
            if mode == 'python':
                return PythonWindow(ui, mono, Path(directory) / 'python-progress-v1.json')
            raise AssertionError('Unexpected UI test mode')

        host = StudyWindow(ui, mono, Path(directory) / 'progress-v3.json',
                           mode='conda', page_factory=factory)
        window = host.pages['conda']
        host.show()

        def wait(predicate, seconds=100):
            deadline = time.monotonic() + seconds
            while not predicate() and time.monotonic() < deadline:
                app.processEvents()
                QTest.qWait(15)
            if not predicate():
                detail = window.feedback.toPlainText() if isValid(window) else 'Study page closed'
                raise AssertionError('Installation UI timed out: ' + detail)

        def screen():
            return '\n'.join(window.terminal.screen.display)

        def capture(name):
            if capture_dir is not None:
                app.processEvents()
                if not host.grab().save(str(capture_dir / name)):
                    raise AssertionError('Cannot save installation UI capture: ' + name)

        try:
            window.setup_button.click()
            window.try_button.click()
            wait(lambda: not window.busy)
            assert window.terminal.connected, window.feedback.toPlainText()
            assert window.window() is host and not window.isWindow()
            assert [w for w in app.topLevelWidgets() if w.isVisible()] == [host]
            process, session = engine.process, engine.session_dir
            prefix = window.setup_ready['prefix']
            sid = engine.bridge.sid
            wait(lambda: screen().rstrip().endswith('$'), 20)

            window.step = 3
            window.render()
            window.next_button.click()
            QTest.keyClick(window.terminal, Qt.Key.Key_F5)
            wait(lambda: not window.busy)
            assert not window.solved and window.tabs.currentIndex() == 1
            assert window.terminal.connected and engine.bridge.sid == sid

            window.setup_button.click()
            assert window.phase == 'learn' and window.setup_ready['prefix'] == prefix
            window.step = 2
            window.save()
            window.render()
            assert prefix in window.instructions.toPlainText()
            capture('conda-setup-learning.png')
            command = window.learning_steps[2]['commands'][0]
            window.terminal.input_bytes.emit(
                (command + "; printf '\\n__SG_SETUP_DONE_%s__\\n' \"$?\"\r").encode())
            wait(lambda: '__SG_SETUP_DONE_0__' in screen(), 120)
            window.next_button.click()
            window.next_button.click()
            assert engine.bridge.sid == sid
            QTest.keyClick(window.terminal, Qt.Key.Key_F5)
            wait(lambda: not window.busy)
            assert window.solved, window.feedback.toPlainText()
            assert window.tabs.currentIndex() == 1
            saved = json.loads(path.read_text())
            assert 'conda_install_once' in saved['setup_completed']
            assert 'conda_install_once' not in saved['completed']
            capture('conda-setup-grade.png')

            window.setup_button.click()
            window.step = 1
            window.save()
            host.switch_mode('python')
            host.switch_mode('conda')
            assert host.pages['conda'] is window and engine.bridge.sid == sid
            # Close with Conda hidden: every room still belongs to one app.
            host.switch_mode('python')
        finally:
            readers = list(window.readers) if isValid(window) else []
            host.close()
            wait(lambda: not host.isVisible(), 30)
            for reader in readers:
                assert reader.wait(3000), 'Installation terminal reader survived close'
            if process is not None:
                assert process.poll() is not None, 'Owned VM survived application close'
            if session is not None:
                assert not session.exists(), 'Owned temporary overlay survived application close'

        saved = json.loads(path.read_text())
        assert saved['resume'] == dict(unit='conda_install_once', phase='learn', step=1)
        assert command not in path.read_text(), 'Progress must not save typed installer commands'
        restored = StudyWindow(ui, mono, Path(directory) / 'progress-v3.json', mode='conda')
        other = restored.pages['conda']
        try:
            assert other.setup_mode and other.step == 1 and other.setup_ready is None
            assert 'conda_install_once' in other.progress.data['setup_completed']
            assert other.engine.process is None, 'Restoring progress must not boot a VM'
        finally:
            restored.close()
            wait(lambda: not restored.pages, 10)

    return dict(seconds=round(time.monotonic() - started, 2),
                frozen_application=bool(getattr(sys, 'frozen', False)),
                passed=['single_window', 'actual_install', 'F5_grade', 'failed_same_PTY_retry',
                        'return_to_explanation', 'mode_roundtrip_keeps_session',
                        'setup_completion_saved', 'microstep_resume', 'reader_close',
                        'hidden_room_cleanup'],
                scope='Native Qt + actual installation in a disposable guest; not all platforms')


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('--capture-dir', type=Path)
    args = parser.parse_args(argv)
    result = check_setup_ui(CondaEngine(), args.capture_dir)
    print('REAL_CONDA_SETUP_UI_OK ' + json.dumps(result, ensure_ascii=False), flush=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
