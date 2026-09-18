"""Accepted A layout: results share the question panel, never the terminal."""
from pathlib import Path
import re
import tempfile
import unittest
from unittest.mock import patch

from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from native_app import Window, create_application
from mode_curriculum import curriculum
from missions import make_mission
from checkpoints import make_checkpoint
from ui_layout_preview import NoExecution, QUESTION

CHECKS = [
    {'label': label, 'passed': index % 2 == 0}
    for index, label in enumerate((
        '숨김 항목을 포함한 재귀 목록 보고서',
        'guide.txt 원본과 내용 보존',
        '공백이 있는 docs/read me.txt 내용 확인',
        'release inventory.txt에 상세 정보 저장',
        'notes.txt에 두 문서 내용을 순서대로 저장',
        '불필요한 draft.tmp만 삭제',
        '다른 파일과 디렉터리 보존',
    ))
]


class ResultTabTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.app, cls.ui, cls.mono = create_application()

    def test_all_generated_objectives_have_no_application_instructions(self):
        for mode in ('simulation', 'real'):
            units, checks = curriculum(mode)
            missions = [make_mission(u.key, seed, practice) for u in units for seed in (1234, 9853) for practice in (0, 1, 2)]
            missions += [make_checkpoint(c.end, 9853, mode=mode) for c in checks]
            for mission in missions:
                self.assertIsNone(re.search(r'\bF[1-8]\b|채점|힌트|버튼', mission.prompt), (mode, mission.kind, mission.prompt))
                self.assertNotIn('F5', mission.interaction)
        self.assertNotIn('F5', QUESTION)
        # These are graded state constraints, not application instructions.
        self.assertIn('위치', make_mission('navigate', 9853).prompt)
        self.assertIn('머무', make_mission('mixed', 9853).prompt)
        self.assertIn('중단', make_mission('ros_rate', 9853).prompt)

    def test_seven_results_fit_and_tab_switching_preserves_terminal(self):
        with tempfile.TemporaryDirectory() as directory:
            for size in ((1220, 880), (1100, 760)):
                with self.subTest(size=size):
                    w = Window(self.ui, self.mono, Path(directory) / 'progress.json', mode='real', engine=NoExecution())
                    self.assertEqual(w.layout_key, 'a')
                    w.show(); w.resize(*size)
                    for _ in range(3): self.app.processEvents()
                    w.phase = 'practice'; w.practice_number = 1
                    w.mission = make_mission('mkdir', 4242)
                    w.instructions.setPlainText(w.mission.prompt)
                    w.terminal.connected = True
                    w.terminal.feed(b'previous work\r\n')
                    before = (w.terminal.size(), w.terminal.screen.lines, w.terminal.screen.columns)
                    mission = w.mission
                    def run(fn, callback, **kwargs): callback({'passed': False, 'checks': CHECKS})
                    with patch.object(w, 'run_job', side_effect=run): w.grade()
                    for _ in range(3): self.app.processEvents()
                    self.assertEqual(w.task_tabs.currentIndex(), 1)
                    self.assertEqual(w.feedback.verticalScrollBar().maximum(), 0, (size, w.feedback.height(), w.feedback.document().size()))
                    self.assertEqual(w.feedback.horizontalScrollBar().maximum(), 0)
                    for item in CHECKS: self.assertIn(item['label'], w.feedback.text())
                    self.assertEqual(before, (w.terminal.size(), w.terminal.screen.lines, w.terminal.screen.columns))
                    self.assertIn('previous work', '\n'.join(w.terminal.screen.display))
                    w.task_tabs.setCurrentIndex(0)
                    self.app.processEvents()
                    self.assertIs(w.mission, mission)
                    self.assertTrue(w.terminal.connected)
                    self.assertIs(self.app.focusWidget(), w.terminal)
                    self.assertIn('previous work', '\n'.join(w.terminal.screen.display))
                    # Passing keeps F6 available from the results tab.
                    def passed(fn, callback, **kwargs): callback({'passed': True, 'checks': [dict(c, passed=True) for c in CHECKS]})
                    with patch.object(w, 'run_job', side_effect=passed): w.grade()
                    w.update_controls()
                    self.assertEqual(w.task_tabs.currentIndex(), 1)
                    self.assertTrue(w.next_button.isEnabled())
                    with patch.object(w, 'launch') as launch:
                        QTest.keyClick(w.terminal, Qt.Key.Key_F6)
                        launch.assert_called_once()
                    w._shutdown_ready = True
                    w.close(); w.deleteLater(); self.app.processEvents()
