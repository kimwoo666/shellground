"""New authentication teaching contracts, without executing host accounts."""
import unittest
from unittest.mock import patch
from auth_course import KEYS
from guest import auth_lab
from learning_steps import learning_steps
from missions import make_mission, lesson_text
from mode_curriculum import curriculum
from real_course_checks import make_review


class AuthCourseTests(unittest.TestCase):
    def test_appended_registration_preserves_other_modes(self):
        units, reviews = curriculum('real')
        self.assertEqual(tuple(u.key for u in units[65:70]), KEYS)
        self.assertFalse(any(u.key in KEYS for u in curriculum('simulation')[0]))
        review = next(c for c in reviews if c.end == 70)
        self.assertEqual(make_review(review, 7251).kind, 'auth_review')

    def test_lessons_have_executable_microsteps_and_distinct_applications(self):
        by_key = {u.key: u for u in curriculum('real')[0]}
        for key in KEYS:
            with self.subTest(key=key):
                variants = [make_mission(key, 7251, n) for n in range(3)]
                self.assertEqual(len({m.prompt for m in variants}), 3)
                steps = learning_steps(by_key[key], 'real', variants[0])
                self.assertGreaterEqual(len(steps), 2)
                self.assertTrue(all(s.commands and s.explanation for s in steps))
                self.assertIn('직접 해볼', lesson_text(by_key[key], 'real'))
                for m in variants:
                    self.assertNotIn('F5', m.prompt)
                    self.assertIn('개인 암호', m.prompt)
                    self.assertIn('보존', m.prompt)

    def test_password_is_not_a_shell_command_or_logged_argument(self):
        for key in ('auth_password', 'auth_review'):
            m = make_mission(key, 7251)
            active = [line for line in m.solution.splitlines() if not line.startswith('#')]
            self.assertFalse(any(m.review['new_password'] in line for line in active))
            self.assertEqual(active.count('sudo passwd sgauth7251'), 1)

    def test_login_and_nonlogin_locations_differ(self):
        ordinary = make_mission('auth_switch', 7251)
        login = make_mission('auth_login', 7251)
        self.assertEqual(ordinary.review['reports']['location.txt'][1].strip(), ordinary.start)
        self.assertEqual(login.review['reports']['location.txt'][1].strip(), login.target)
        self.assertNotIn('team.txt', ordinary.review['reports'])
        self.assertIn('team.txt', login.review['reports'])

    def test_guard_runs_before_any_account_mutation(self):
        with patch.object(auth_lab, 'guard', side_effect=RuntimeError('not guest')), patch.object(auth_lab, 'run') as run:
            with self.assertRaises(RuntimeError): auth_lab.prepare(make_mission('auth_status', 1).payload())
            with self.assertRaises(RuntimeError): auth_lab.cleanup()
            run.assert_not_called()

    def test_payload_cannot_select_host_or_unrelated_user(self):
        m = make_mission('auth_status', 1).payload()
        auth_lab.validate(m)
        m['review']['user'] = 'root'
        with self.assertRaises(ValueError): auth_lab.validate(m)

    def test_permission_report_compares_every_grant_with_wrapping_allowed(self):
        header = 'User trainee may run the following commands on lab:\n'
        actual = header + '    (root) NOPASSWD: /usr/bin/cat /opt/notice.txt\n'
        wrapped = header + '    (root) NOPASSWD: /usr/bin/cat\n        /opt/notice.txt\n'
        extra = actual + '    (ALL) NOPASSWD: ALL\n'
        self.assertEqual(auth_lab.allowed_commands(actual), auth_lab.allowed_commands(wrapped))
        self.assertNotEqual(auth_lab.allowed_commands(actual), auth_lab.allowed_commands(extra))
        self.assertIsNone(auth_lab.allowed_commands('(root) NOPASSWD: /usr/bin/cat /opt/notice.txt'))


if __name__ == '__main__': unittest.main()
