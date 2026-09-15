"""Exercise real Qt close events in separate processes, with a timeout guard."""
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest


SCENARIO = r'''
import json
from pathlib import Path
import sys
import tempfile
import time
from PySide6.QtCore import QTimer
from native_app import create_application, Window

mode = sys.argv[1]
app, ui, mono = create_application()
with tempfile.TemporaryDirectory(prefix='shellground-shutdown-test-') as temporary:
    window = Window(ui, mono, Path(temporary) / 'progress.json')
    state = {'cleanup_calls': 0, 'timed_out': False}
    real_close = window.engine.close
    def cleanup():
        state['cleanup_calls'] += 1
        if mode == 'error':
            raise RuntimeError('Test Docker cleanup failure')
        if mode == 'double':
            time.sleep(.15)
        return real_close() if mode == 'docker' else None
    window.engine.close = cleanup
    window.show()
    if mode == 'progress':
        window.completed = ['navigate']
        window.save_progress()
        window.terminal.feed(b'echo unsaved-terminal-input')
    def guard():
        state['timed_out'] = True
        app.exit(0)
    QTimer.singleShot(12000 if mode == 'docker' else 1200, guard)
    if mode == 'docker':
        window.advance()
        poll = QTimer()
        def check_ready():
            if window.terminal.connected and not window.busy:
                state['container'] = window.engine.name
                # start() invokes close() to reset a previous lab; count only shutdown.
                state['cleanup_calls'] = 0
                poll.stop()
                window.close()
        poll.timeout.connect(check_ready)
        poll.start(20)
    else:
        QTimer.singleShot(10, window.close)
        if mode == 'double':
            QTimer.singleShot(30, window.close)
    app.exec()
    if window.worker:
        window.worker.wait(5000)
    state.update(visible=window.isVisible(), closing=window._closing,
                 ready=window._shutdown_ready, error=window.feedback.text(),
                 remaining_container=window.engine.name)
    if mode == 'progress':
        state['saved_data'] = json.loads(window.progress_path.read_text())
        restored = Window(ui, mono, window.progress_path)
        state['restored_completed'] = restored.completed
        state['restored_index'] = restored.index
        state['restored_terminal'] = '\n'.join(restored.terminal.screen.display).strip()
        state['restored_rows'] = [restored.course.item(i).text() for i in range(2)]
    print(json.dumps(state))
'''


class ShutdownTests(unittest.TestCase):
    def run_scenario(self, mode):
        root = Path(__file__).resolve().parent
        env = dict(os.environ, QT_QPA_PLATFORM='offscreen')
        env['PYTHONPATH'] = os.pathsep.join([str(root), *map(str, sys.path)])
        result = subprocess.run([sys.executable, '-c', SCENARIO, mode], cwd=root, env=env,
                                capture_output=True, text=True, encoding='utf-8', timeout=20)
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout.splitlines()[-1])

    def test_exit_after_cleanup_happens_once(self):
        state = self.run_scenario('normal')
        self.assertEqual(state['cleanup_calls'], 1, state)
        self.assertFalse(state['timed_out'], state)
        self.assertFalse(state['visible'], state)
        self.assertTrue(state['ready'], state)

    def test_repeated_close_does_not_start_another_cleanup(self):
        state = self.run_scenario('double')
        self.assertEqual(state['cleanup_calls'], 1, state)
        self.assertFalse(state['timed_out'], state)
        self.assertFalse(state['visible'], state)

    def test_close_preserves_only_completion_not_terminal_input(self):
        state = self.run_scenario('progress')
        self.assertFalse(state['timed_out'], state)
        self.assertFalse(state['visible'], state)
        self.assertEqual(state['saved_data'], {'schema': 3, 'completed': ['navigate']})
        self.assertEqual(state['restored_completed'], ['navigate'])
        self.assertEqual(state['restored_index'], 1)
        self.assertEqual(state['restored_terminal'], '')
        self.assertIn('[완료]', state['restored_rows'][0])
        self.assertIn('미완료', state['restored_rows'][1])

    def test_cleanup_failure_shows_error_without_retry_loop(self):
        state = self.run_scenario('error')
        self.assertEqual(state['cleanup_calls'], 1, state)
        self.assertTrue(state['visible'], state)
        self.assertFalse(state['closing'], state)
        self.assertFalse(state['ready'], state)
        self.assertIn('Test Docker cleanup failure', state['error'])

    def test_active_simulator_cleanup_then_application_exit(self):
        state = self.run_scenario('docker')
        self.assertIn('container', state, state)
        self.assertEqual(state['cleanup_calls'], 1, state)
        self.assertFalse(state['timed_out'], state)
        self.assertFalse(state['visible'], state)
        self.assertIsNone(state['remaining_container'], state)
        self.assertEqual(state['container'], 'simulation')


if __name__ == '__main__':
    unittest.main()
