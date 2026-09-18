import unittest
from unittest.mock import patch
from guest import process_lab
from process_course import KEYS, make_mission
from mode_curriculum import curriculum
from learning_steps import learning_steps
from real_course_checks import make_review


class ProcessCourseTests(unittest.TestCase):
    def test_registration_does_not_extend_simulator(self):
        units, reviews = curriculum('real')
        self.assertEqual(tuple(u.key for u in units[75:80]), KEYS)
        self.assertEqual(make_review(next(c for c in reviews if c.end == 80), 7251).kind, 'process_review')
        self.assertFalse(any(u.key in KEYS for u in curriculum('simulation')[0]))

    def test_executable_microsteps_and_distinct_applications(self):
        units = {u.key: u for u in curriculum('real')[0]}
        for key in KEYS:
            with self.subTest(key=key):
                variants = [make_mission(key, 7251, v) for v in range(3)]
                self.assertEqual(len({m.prompt for m in variants}), 3)
                self.assertEqual(len({str(m.review) for m in variants}), 3)
                steps = learning_steps(units[key], 'real', variants[0])
                self.assertGreaterEqual(len(steps), 2)
                self.assertTrue(all(s.commands and s.explanation for s in steps))
                for m in variants:
                    self.assertNotIn('F5', m.prompt)
                    self.assertNotIn('ls -alR / ', m.solution)

    def test_stopped_is_not_sleeping_and_kill_is_not_always_force(self):
        units = {u.key: u for u in curriculum('real')[0]}
        self.assertIn('S는', units['process_stop'].explanation)
        self.assertIn('TIME은 실행한 뒤 흐른 시간이 아닙니다', units['process_list'].explanation)
        self.assertIn('무시', units['process_signals'].explanation)
        self.assertIn('항상 빨라지는', units['process_threads'].explanation)

    def test_fixture_cannot_select_host_paths(self):
        m = make_mission('process_list', 7251).payload(); process_lab.validate(m)
        m['start'] = '/tmp'
        with self.assertRaises(ValueError): process_lab.validate(m)
        with patch.object(process_lab, 'guard', side_effect=RuntimeError('not guest')):
            with self.assertRaises(RuntimeError): process_lab.prepare(m)
            with self.assertRaises(RuntimeError): process_lab.cleanup()

    def test_cleanup_requires_pid_start_time_uid_and_owned_command(self):
        expected = dict(pid=123, start_ticks=42)
        base = dict(pid=123, start_ticks=42, uid=1100, cmd=process_lab.SCRIPT + ' worker')
        for replacement in ({}, {'start_ticks': 43}, {'uid': 0}, {'cmd': '/usr/bin/other'}):
            with self.subTest(replacement=replacement), patch.object(process_lab, 'inspect', return_value=dict(base, **replacement)):
                self.assertEqual(bool(process_lab.identity(expected)), not replacement)

    def test_ps_table_retains_full_command_and_header_order(self):
        header, rows = process_lab.table(b'UID PID PPID LWP NLWP CMD\nlearner 42 2 42 2 /usr/bin/python3 /a script.py\n')
        self.assertEqual(header[:3], ['UID', 'PID', 'PPID'])
        self.assertEqual(rows[0]['CMD'], '/usr/bin/python3 /a script.py')

    def test_equivalent_columns_and_invalid_cpu_times(self):
        header, rows = process_lab.table(b'PID TT TIME COMMAND\n42 ? 00:00:00 sgm42\n')
        self.assertEqual(header, ['PID', 'TTY', 'TIME', 'CMD'])
        self.assertEqual(rows[0]['CMD'], 'sgm42')
        for value in ('99:99:99', '00:00:60', '0', '1-24:00:00'):
            self.assertIsNone(process_lab.cpu_time(value))
        self.assertEqual(process_lab.cpu_time('01:02:03'), 3723)
        self.assertEqual(process_lab.cpu_time('2-01:02:03'), 176523)


if __name__ == '__main__': unittest.main()
