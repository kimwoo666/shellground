import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from missions import lesson_text, make_mission
from mode_curriculum import ROS_UNITS, ROS_CHECKPOINTS, curriculum
from ros_guides import (GUIDES, REPORT_KEYS, TERMINAL_GUIDE, FILE_GUIDE,
                        REPORT_GUIDE, NODE_REPORT_GUIDE)
from ros_lessons import SPECS


class RosGuideTests(unittest.TestCase):
    def test_all_twenty_guides_preserve_basics_and_teach_why_arguments_checks(self):
        self.assertEqual(set(GUIDES), {row[0] for row in SPECS})
        self.assertEqual(len(ROS_UNITS), 20)
        for unit, (key, _, _, original) in zip(ROS_UNITS, SPECS):
            with self.subTest(key=key):
                self.assertTrue(unit.explanation.startswith(original))
                for text in (GUIDES[key], TERMINAL_GUIDE, FILE_GUIDE,
                             '왜 필요한가', '명령을 읽는 법', '결과 확인과 흔한 실수'):
                    self.assertIn(text, unit.explanation)
                self.assertIn(unit.explanation, lesson_text(unit, 'real'))
                self.assertIn('직접 해볼 예시', lesson_text(unit, 'real'))

    def test_every_extra_objective_is_taught_before_test(self):
        for unit in ROS_UNITS:
            key = unit.key.removeprefix('ros_')
            m = make_mission(unit.key, 5131, 2)
            guide = REPORT_GUIDE if key in REPORT_KEYS else NODE_REPORT_GUIDE
            self.assertIn(guide, unit.explanation)
            self.assertEqual(m.review['handoff'], 'reports' if key in REPORT_KEYS else 'nodes')
            if key in REPORT_KEYS:
                self.assertIn(m.solution[m.solution.index('mkdir -p reports'):], guide)
            else:
                self.assertIn('ros2 node list > nodes-after.txt', guide)
                self.assertIn('export ROS_DOMAIN_ID=42', guide)

    def test_teaching_does_not_leak_into_test_goals_or_change_course_keys(self):
        self.assertEqual([u.key for u in ROS_UNITS], ['ros_' + row[0] for row in SPECS])
        self.assertEqual([c.end for c in ROS_CHECKPOINTS], [45, 50, 55, 60])
        self.assertEqual(len(curriculum('real')[0]), 95)
        self.assertEqual(len(curriculum('simulation')[0]), 45)
        for unit in ROS_UNITS:
            for variant in (0, 1, 2):
                m = make_mission(unit.key, 5131, variant)
                for phrase in ('왜 필요한가', '명령을 읽는 법', 'Ctrl+C', 'F5', 'F6', '터미널 A:'):
                    self.assertNotIn(phrase, m.prompt)

    def test_continuous_examples_explain_control_flow(self):
        echo = make_mission('ros_echo', 1234).solution
        self.assertLess(echo.index('echo /turtle1/pose'), echo.index('Ctrl+C'))
        self.assertLess(echo.index('Ctrl+C'), echo.index('hz /turtle1/pose'))
        record = make_mission('ros_record', 1234).solution
        self.assertEqual(record.count('source /opt/ros/humble/setup.bash'), 2)
        self.assertLess(record.index('터미널 B:'), record.index('ros2 topic pub'))
        self.assertLess(record.index('Ctrl+C'), record.index('ros2 bag info capture'))

    def test_record_reference_does_not_wait_for_an_absent_publisher(self):
        reference=make_mission('ros_record',1234).solution
        self.assertIn('pose 구독 로그',reference)
        self.assertNotIn('두 토픽의 구독 로그를 확인',reference)
        self.assertLess(reference.index('ros2 topic pub --rate 2'),reference.index('cmd_vel 구독 로그'))
        self.assertLess(reference.index('cmd_vel 구독 로그'),reference.index('터미널 B에서 Ctrl+C'))
        self.assertLess(reference.index('터미널 B에서 Ctrl+C'),reference.index('터미널 A로 돌아와 Ctrl+C'))
        self.assertIn('--once의 한 메시지',GUIDES['record'])

    def test_short_bag_reference_teaches_discovery_delay_and_visible_goal(self):
        for variant in (0,1,2):
            mission=make_mission('ros_play',1234,variant)
            self.assertIn('sample_bag --delay 2 --topics /turtle1/cmd_vel',mission.solution)
            self.assertIn('이동 메시지 8개',mission.prompt)
            self.assertNotIn('--delay',mission.prompt)
        self.assertIn('--delay 2',GUIDES['play'])
        self.assertIn('모든 시스템에서 전달을 보장',GUIDES['play'])

    def test_taught_handoff_copies_spaces_preserves_originals_and_stays_shallow(self):
        m = make_mission('ros_load', 1234, 2)
        command = m.solution[m.solution.index('mkdir -p reports'):]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            originals = {'restore.yaml': 'background_r: 120\n', 'read me.txt': 'report\n',
                         '.hidden.txt': 'hidden\n', 'other.log': 'skip\n'}
            for name, content in originals.items(): (root / name).write_text(content)
            (root / 'nested').mkdir()
            (root / 'nested' / 'skip.txt').write_text('nested\n')
            for _ in range(2):
                result = subprocess.run(['bash', '-c', command], cwd=root,
                                        capture_output=True, text=True, timeout=5)
                self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual({p.name for p in (root / 'reports').iterdir()},
                             {'restore.yaml', 'read me.txt', '.hidden.txt'})
            for name, content in originals.items():
                self.assertEqual((root / name).read_text(), content)
                if name.endswith(('.txt', '.yaml')):
                    self.assertEqual((root / 'reports' / name).read_text(), content)


class RosGuideUITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from native_app import create_application
        cls.app, cls.ui, cls.mono = create_application()

    def test_guides_reach_learning_options_and_not_practice_screen(self):
        from native_app import Window
        from real_vm import RealEngine
        from PySide6.QtWidgets import QDialog, QPlainTextEdit
        with tempfile.TemporaryDirectory() as directory, \
                patch('native_app.create_engine', return_value=RealEngine()):
            window = Window(self.ui, self.mono, Path(directory) / 'progress.json', mode='real')
            window.run_job = lambda *args, **kwargs: None
            for index, unit in enumerate(window.units):
                if not unit.key.startswith('ros_'): continue
                window.select_lesson(index)
                self.assertIn(window.learning_sequence[0].text, window.instructions.toPlainText())
                self.assertNotIn(REPORT_GUIDE, window.instructions.toPlainText())
                with patch.object(QDialog, 'exec', return_value=0): window.show_options()
                dialog = window.findChildren(QDialog)[-1]
                self.assertIn(unit.explanation, dialog.findChild(QPlainTextEdit).toPlainText())
                window.phase = 'practice'
                window.practice_number = 2
                window.launch(make_mission(unit.key, 5131, 2))
                self.assertNotIn('명령을 읽는 법', window.instructions.toPlainText())
                window.mission = None
            self.assertEqual(window.completed, [])
            window.deleteLater()
            self.app.processEvents()


if __name__ == '__main__': unittest.main()
