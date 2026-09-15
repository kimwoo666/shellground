"""Offscreen Qt tests; no desktop screen capture or host UI control."""
import tempfile
import json
import os
import time
import unittest
from pathlib import Path
from unittest.mock import patch
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QRawFont
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QMessageBox, QDialog
from native_app import create_application, Window
from missions import UNITS, make_mission
from terminal_widget import TerminalWidget


class NativeUITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app, cls.ui, cls.mono = create_application()

    def wait_job(self, window):
        end = time.monotonic() + 5
        while window.busy and time.monotonic() < end:
            self.app.processEvents()
            time.sleep(.005)
        self.assertFalse(window.busy)

    def test_korean_glyphs_and_terminal_cells(self):
        font = QRawFont.fromFont(QFont(self.ui, 12))
        for char in '리눅스명령어연습단계활용문제':
            self.assertTrue(font.supportsCharacter(ord(char)), char)
        terminal = TerminalWidget(self.mono)
        terminal.feed('한글 abc\r\n'.encode())
        self.assertEqual(terminal.screen.buffer[0][0].data, '한')
        self.assertEqual(terminal.screen.buffer[0][1].data, '')
        terminal.feed(b'\x1b[31mERROR\x1b[0m')
        self.assertEqual(terminal.screen.buffer[1][0].fg, 'red')

    def test_raw_keys_and_bracketed_paste(self):
        terminal = TerminalWidget(self.mono)
        terminal.connected = True
        events = []
        terminal.input_bytes.connect(events.append)
        QTest.keyClick(terminal, Qt.Key.Key_Tab)
        QTest.keyClick(terminal, Qt.Key.Key_C, Qt.KeyboardModifier.ControlModifier)
        QTest.keyClick(terminal, Qt.Key.Key_Up)
        self.assertEqual(events, [b'\t', b'\x03', b'\x1b[A'])
        terminal.feed(b'\x1b[?2004h')
        self.app.clipboard().setText('echo first\necho second')
        terminal.paste()
        self.assertEqual(events[-1], b'\x1b[200~echo first\necho second\x1b[201~')

    def test_progression_requires_two_practices_and_persists(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / 'progress.json'
            window = Window(self.ui, self.mono, path)
            self.assertEqual(window.phase, 'learn')
            self.assertFalse(window.random_button.isEnabled())
            window.select_lesson(5)
            self.assertEqual(window.index, 0)
            def launch(mission):
                window.mission, window.passed = mission, False
                window.terminal.connected = True
                window.update_controls()
            window.launch = launch
            window.engine.rpc = lambda action, mission: {'passed': True, 'checks': [{'label': 'result', 'passed': True}]}
            window.advance()
            self.assertEqual(window.phase, 'example')
            window.grade(); self.wait_job(window)
            self.assertEqual(window.completed, [])
            partial = Window(self.ui, self.mono, path)
            self.assertEqual(partial.completed, [])
            self.assertIn('미완료', partial.course.item(0).text())
            partial.deleteLater()
            window.advance()
            self.assertEqual((window.phase, window.practice_number), ('practice', 1))
            window.grade(); self.wait_job(window)
            self.assertEqual(window.completed, [])
            partial = Window(self.ui, self.mono, path)
            self.assertEqual(partial.completed, [])
            self.assertIn('미완료', partial.course.item(0).text())
            partial.deleteLater()
            window.advance()
            window.grade(); self.wait_job(window)
            self.assertEqual(window.completed, [UNITS[0].key])
            self.assertTrue(path.is_file())
            self.assertEqual(json.loads(path.read_text()), {'schema': 3, 'completed': [UNITS[0].key]})
            self.assertIn('자동 저장됨', window.progress_note.text())
            window.start_random()
            self.assertEqual(window.mission.kind, UNITS[0].key)
            restored = Window(self.ui, self.mono, path)
            self.assertEqual(restored.completed, window.completed)
            self.assertIn('[완료]', restored.course.item(0).text())
            self.assertIn('미완료', restored.course.item(1).text())
            self.assertEqual(restored.index, 1)
            self.assertIsNone(restored.mission)
            window.deleteLater(); restored.deleteLater()
            self.app.processEvents()

    def test_save_failure_does_not_claim_saved(self):
        with tempfile.TemporaryDirectory() as temporary:
            window = Window(self.ui, self.mono, Path(temporary) / 'progress.json')
            with patch.object(Path, 'replace', side_effect=OSError('disk full')), patch.object(QMessageBox, 'warning') as warning:
                self.assertFalse(window.save_progress())
                warning.assert_called_once()
                self.assertIn('저장 실패', window.progress_note.text())
            self.assertTrue(window.save_progress())
            self.assertIn('자동 저장됨', window.progress_note.text())
            window.deleteLater(); self.app.processEvents()

    def test_incomplete_grade_restores_typing_without_reset(self):
        for phase in ('example', 'practice', 'random', 'checkpoint'):
            with self.subTest(phase=phase), tempfile.TemporaryDirectory() as temporary:
                window = Window(self.ui, self.mono, Path(temporary) / 'progress.json')
                window.show(); window.activateWindow()
                window.phase = phase
                window.mission = make_mission('mkdir', 4242)
                window.terminal.connected = True
                window.terminal.feed(b'previous work\r\n')
                window.update_controls()
                mission = window.mission
                events = []
                window.terminal.input_bytes.connect(events.append)
                incomplete = {'passed': False, 'checks': [
                    {'label': '/a/long/path/' + str(i), 'passed': i % 2 == 0}
                    for i in range(40)]}
                with patch.object(window.engine, 'rpc', return_value=incomplete), patch.object(window, 'launch') as launch:
                    window.grade_button.setFocus()
                    QTest.mouseClick(window.grade_button, Qt.MouseButton.LeftButton)
                    self.wait_job(window); self.app.processEvents()
                    self.assertIs(self.app.focusWidget(), window.terminal)
                    self.assertTrue(window.grade_button.isEnabled())
                    self.assertFalse(window.next_button.isEnabled())
                    self.assertFalse(window.passed)
                    self.assertIs(window.mission, mission)
                    self.assertEqual(window.completed, [])
                    self.assertTrue(window.terminal.connected)
                    self.assertIn('previous work', '\n'.join(window.terminal.screen.display))
                    self.assertLessEqual(window.feedback.height(), 130)
                    self.assertGreater(window.feedback.verticalScrollBar().maximum(), 0)
                    QTest.keyClicks(self.app.focusWidget(), 'pwd')
                    QTest.keyClick(self.app.focusWidget(), Qt.Key.Key_Return)
                    self.assertEqual(b''.join(events), b'pwd\r')
                    launch.assert_not_called()
                window.hide(); window.deleteLater(); self.app.processEvents()

    def test_grade_error_keeps_terminal_available(self):
        with tempfile.TemporaryDirectory() as temporary:
            window = Window(self.ui, self.mono, Path(temporary) / 'progress.json')
            window.show(); window.activateWindow()
            window.phase = 'example'
            window.mission = make_mission('mkdir', 4242)
            window.terminal.connected = True
            window.update_controls()
            with patch.object(window.engine, 'rpc', side_effect=RuntimeError('temporary failure')):
                window.grade_button.setFocus()
                window.grade_button.click(); self.wait_job(window)
            self.assertIs(self.app.focusWidget(), window.terminal)
            self.assertTrue(window.grade_button.isEnabled())
            self.assertTrue(window.terminal.connected)
            self.assertIn('초기화하지 않았습니다', window.feedback.text())
            window.hide(); window.deleteLater(); self.app.processEvents()

    def test_sidebar_hides_hints_only_during_tests(self):
        with tempfile.TemporaryDirectory() as temporary:
            window = Window(self.ui, self.mono, Path(temporary) / 'progress.json')
            for phase in ('learn', 'example', 'practice', 'random', 'checkpoint'):
                window.phase = phase
                with patch.object(window, 'run_job'):
                    if phase == 'checkpoint': window.checkpoint_end = 5
                    else: window.checkpoint_end = None
                    window.launch(make_mission('mkdir', 4242))
                rows = [window.course.item(i).text() for i in range(window.course.count())]
                visible = '\n'.join(rows)
                if phase in ('practice', 'random', 'checkpoint'):
                    for command in ('pwd', 'nano', 'docker', 'mkdir', 'ls', 'cat'):
                        self.assertNotIn(command, visible)
                    self.assertIn('난이도', visible)
                    self.assertIn('미완료', visible)
                    self.assertIn('평가 중 학습 내용 숨김', visible)
                    for index in range(window.course.count()):
                        self.assertFalse(window.course.item(index).toolTip())
                else:
                    self.assertIn('pwd', visible)
                    self.assertIn('docker', visible)
            window.select_lesson(0, initial=True)
            self.assertIn('pwd', window.course.item(0).text())
            window.deleteLater(); self.app.processEvents()

    def test_corrupt_progress_and_worker_error(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / 'progress.json'
            path.write_text('{bad', encoding='utf-8')
            window = Window(self.ui, self.mono, path)
            self.assertEqual(window.completed, [])
            def fail(log): raise RuntimeError('Docker unavailable')
            window.run_job(fail, lambda value: None)
            self.wait_job(window)
            self.assertIn('Docker unavailable', window.feedback.text())
            self.assertTrue(window.next_button.isEnabled())
            window.deleteLater(); self.app.processEvents()

    def test_shortcuts_from_terminal_and_disabled_controls(self):
        with tempfile.TemporaryDirectory() as temporary:
            window = Window(self.ui, self.mono, Path(temporary) / 'progress.json')
            window.show(); window.activateWindow(); window.terminal.setFocus()
            self.app.processEvents()
            def press(key):
                QTest.keyClick(window.terminal, key)
                self.app.processEvents()
            def launch(mission):
                window.mission, window.passed = mission, False
                window.terminal.connected = True
                window.update_controls()
            with patch.object(window, 'launch', side_effect=launch) as launched, patch.object(QMessageBox, 'information') as hint, patch.object(QMessageBox, 'question', return_value=QMessageBox.StandardButton.No) as question, patch.object(QDialog, 'exec', return_value=0) as options:
                press(Qt.Key.Key_F1); press(Qt.Key.Key_F2)
                hint.assert_not_called(); question.assert_not_called()
                press(Qt.Key.Key_F3); options.assert_called_once()
                press(Qt.Key.Key_F6)
                self.assertEqual(window.phase, 'example')
                self.assertEqual(launched.call_count, 1)
                press(Qt.Key.Key_F6)  # Cannot skip an unsolved goal.
                self.assertEqual(launched.call_count, 1)
                press(Qt.Key.Key_F1); hint.assert_called_once()
                press(Qt.Key.Key_F2); question.assert_called_once()
                self.assertEqual(launched.call_count, 1)  # Cancel keeps files.
                question.return_value = QMessageBox.StandardButton.Yes
                press(Qt.Key.Key_F2)
                self.assertEqual(launched.call_count, 2)
                window.busy = True; window.update_controls()
                for key in [Qt.Key.Key_F1, Qt.Key.Key_F2, Qt.Key.Key_F3, Qt.Key.Key_F5, Qt.Key.Key_F6]: press(key)
                self.assertEqual(launched.call_count, 2)
                self.assertEqual(hint.call_count, 1)
                self.assertEqual(question.call_count, 2)
                self.assertEqual(options.call_count, 1)
                window.busy = False; window.update_controls()
                with patch.object(window.engine, 'rpc', return_value={'passed': True, 'checks': []}):
                    press(Qt.Key.Key_F5); self.wait_job(window)
                self.assertTrue(window.passed)
                press(Qt.Key.Key_F6)
                self.assertEqual((window.phase, window.practice_number), ('practice', 1))
            window.hide(); window.deleteLater(); self.app.processEvents()

    def test_reordered_curriculum_preserves_old_completions(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / 'progress.json'
            path.write_text(json.dumps({'schema': 3, 'completed': ['navigate', 'workspace', 'copy', 'list']}))
            window = Window(self.ui, self.mono, path)
            self.assertEqual(set(window.completed), {'navigate', 'workspace', 'copy', 'list'})
            self.assertEqual(UNITS[window.index].key, 'lsintro')
            self.assertTrue(window.lesson_unlocked(next(i for i, u in enumerate(UNITS) if u.key == 'copy')))
            self.assertFalse(window.lesson_unlocked(next(i for i, u in enumerate(UNITS) if u.key == 'long')))
            window.save_progress()
            self.assertEqual(set(json.loads(path.read_text())['completed']), set(window.completed))
            window.deleteLater(); self.app.processEvents()

    def test_lesson_screen_shows_only_current_topic(self):
        with tempfile.TemporaryDirectory() as temporary:
            window = Window(self.ui, self.mono, Path(temporary) / 'progress.json')
            window.completed = [u.key for u in UNITS]
            for index in [*range(7), next(i for i, u in enumerate(UNITS) if u.key == 'pwdpaths')]:
                window.select_lesson(index)
                text = window.instructions.toPlainText()
                self.assertNotIn('옵션별 의미와 비교 예시', text)
                self.assertLess(len(text), 500)
                if UNITS[index].key == 'pwdpaths':
                    self.assertIn('-L', text)
                    self.assertIn('-P', text)
                    self.assertNotIn('cat', text)
                    self.assertNotIn('>', text)
                    self.assertNotIn('ls ', text)
            window.deleteLater(); self.app.processEvents()

    def test_editor_walkthrough_only_appears_in_teaching_phases(self):
        with tempfile.TemporaryDirectory() as temporary:
            window = Window(self.ui, self.mono, Path(temporary) / 'progress.json')
            window.index = next(i for i, u in enumerate(UNITS) if u.key == 'edit')
            with patch.object(window, 'run_job'):
                for phase in ['learn', 'example', 'practice', 'random']:
                    for variant in [1, 2]:
                        with self.subTest(phase=phase, variant=variant):
                            mission = make_mission('edit', 4277, practice=variant)
                            window.phase, window.practice_number = phase, variant
                            window.launch(mission)
                            text = window.instructions.toPlainText()
                            if phase in ('learn', 'example'):
                                self.assertIn(mission.interaction, text)
                                self.assertIn(mission.solution, text)
                            else:
                                self.assertIn(mission.prompt, text)
                                self.assertIn(mission.start, text)
                                self.assertNotIn('편집기 조작:', text)
                                for key in ['Ctrl+K', 'Ctrl+O', 'Ctrl+X']:
                                    self.assertNotIn(key, text)
                                self.assertNotIn(mission.solution, text)
                                with patch.object(QMessageBox, 'information') as hint:
                                    window.show_hint()
                                    hint.assert_called_once()
                                    self.assertIn('Ctrl+O', hint.call_args.args[2])
            window.deleteLater(); self.app.processEvents()

    def test_f4_free_practice_keeps_explanation_and_cannot_complete_lesson(self):
        with tempfile.TemporaryDirectory() as temporary:
            window = Window(self.ui, self.mono, Path(temporary) / 'progress.json')
            window.show(); window.activateWindow(); window.terminal.setFocus()
            self.app.processEvents()
            def launch(mission):
                window.mission = mission
                window.terminal.connected = True
                window.update_controls()
            with patch.object(window, 'launch', side_effect=launch) as launched, patch.object(window.engine, 'rpc') as rpc:
                QTest.keyClick(window.terminal, Qt.Key.Key_F4)
                self.app.processEvents()
                self.assertEqual(window.phase, 'learn')
                self.assertEqual(launched.call_count, 1)
                self.assertFalse(window.grade_button.isEnabled())
                window.grade(); rpc.assert_not_called()
                window.try_lesson()
                self.assertEqual(launched.call_count, 1, 'F4 does not reset an active practice')
                window.advance()
                self.assertEqual(window.phase, 'example')
                self.assertEqual(launched.call_count, 2)
                self.assertEqual(window.completed, [])
            window.hide(); window.deleteLater(); self.app.processEvents()

    def test_simulated_terminal_through_native_learning_flow(self):
        with tempfile.TemporaryDirectory() as temporary:
            window = Window(self.ui, self.mono, Path(temporary) / 'progress.json')
            window.show()
            self.app.processEvents()
            def wait_for(predicate):
                end = time.monotonic() + 15
                while not predicate() and time.monotonic() < end:
                    self.app.processEvents()
                    time.sleep(.01)
                self.assertTrue(predicate(), window.feedback.text())
            try:
                window.try_lesson()
                wait_for(lambda: not window.busy and window.terminal.connected)
                self.assertEqual(window.phase, 'learn')
                self.assertIn(UNITS[0].explanation, window.instructions.toPlainText())
                self.assertFalse(window.grade_button.isEnabled())
                for stage in range(3):
                    window.advance()
                    wait_for(lambda: not window.busy and window.terminal.connected)
                    wait_for(lambda: 'learner@lab:' in '\n'.join(window.terminal.screen.display))
                    if stage == 0:
                        container = window.engine.name
                        bridge = window.engine.bridge
                        QTest.keyClicks(window.terminal, "cd /tmp; export CONTINUE_MARK=preserved; touch /tmp/keep-after-grade; printf '\\n__BEFORE_GRADE__\\n'")
                        QTest.keyClick(window.terminal, Qt.Key.Key_Return)
                        wait_for(lambda: '__BEFORE_GRADE__' in [line.strip() for line in window.terminal.screen.display])
                        for attempt in range(2):
                            QTest.mouseClick(window.grade_button, Qt.MouseButton.LeftButton)
                            wait_for(lambda: not window.busy)
                            self.assertFalse(window.passed)
                            self.assertIs(self.app.focusWidget(), window.terminal)
                            self.assertEqual(window.engine.name, container)
                            self.assertIs(window.engine.bridge, bridge)
                        QTest.keyClicks(self.app.focusWidget(), "test -f keep-after-grade && test \"$CONTINUE_MARK\" = preserved && printf '\\n__STATE_KEPT__\\n'")
                        QTest.keyClick(self.app.focusWidget(), Qt.Key.Key_Return)
                        wait_for(lambda: '__STATE_KEPT__' in [line.strip() for line in window.terminal.screen.display])
                        # Restore the authored starting location without restarting the lab.
                        QTest.keyClicks(self.app.focusWidget(), 'cd ' + window.mission.start)
                        QTest.keyClick(self.app.focusWidget(), Qt.Key.Key_Return)
                    for line in window.mission.solution.splitlines():
                        QTest.keyClicks(window.terminal, line)
                        QTest.keyClick(window.terminal, Qt.Key.Key_Return)
                    QTest.keyClicks(window.terminal, "printf '\\n__FLOW_DONE__\\n'")
                    QTest.keyClick(window.terminal, Qt.Key.Key_Return)
                    wait_for(lambda: '__FLOW_DONE__' in [line.strip() for line in window.terminal.screen.display])
                    window.grade()
                    wait_for(lambda: not window.busy)
                    self.assertTrue(window.passed, window.feedback.text())
                self.assertEqual(window.completed, ['navigate'])
            finally:
                window.generation += 1
                window.run_job(lambda log: window.engine.close(), lambda value: None)
                wait_for(lambda: not window.busy)
                for reader in window.readers: reader.wait(3000)
                window.hide(); window.deleteLater(); self.app.processEvents()


if __name__ == '__main__': unittest.main()
