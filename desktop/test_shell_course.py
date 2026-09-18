import unittest
from unittest.mock import patch
from guest import shell_lab
from shell_course import KEYS, make_mission, reference_script, write_script
from mode_curriculum import curriculum
from learning_steps import learning_steps
from real_course_checks import make_review
import shlex


class ShellCourseTests(unittest.TestCase):
    def test_registration_and_old_keys_preserved(self):
        units, reviews = curriculum('real')
        self.assertEqual(tuple(u.key for u in units[70:75]), KEYS)
        self.assertEqual(make_review(next(c for c in reviews if c.end == 75), 7251).kind, 'shell_review')
        self.assertFalse(any(u.key in KEYS for u in curriculum('simulation')[0]))

    def test_microsteps_and_distinct_application_contracts(self):
        units = {u.key: u for u in curriculum('real')[0]}
        for key in KEYS:
            with self.subTest(key=key):
                missions = [make_mission(key, 7251, v) for v in range(3)]
                self.assertEqual(len({m.prompt for m in missions}), 3)
                for m in missions:
                    self.assertNotIn('F5', m.prompt)
                    self.assertIn('보존', m.prompt)
                steps = learning_steps(units[key], 'real', missions[0])
                self.assertGreaterEqual(len(steps), 2)
                self.assertTrue(all(s.commands and s.explanation for s in steps))

    def test_script_reference_is_one_input_line_with_parameters_preserved(self):
        for key in KEYS[2:]:
            lines = reference_script(key)
            command = write_script('my tool.sh', lines)
            self.assertNotIn('\n', command)
            words = shlex.split(command)
            self.assertEqual(words[2:-2], lines)
            self.assertEqual(words[-2:], ['>', 'my tool.sh'])

    def test_arguments_keep_empty_and_glob_as_values(self):
        self.assertEqual(shell_lab.argument_output('script.sh', ['', 'a b', '*']),
                         b'script=script.sh\ncount=3\narg=\narg=a b\narg=*\njoined= a b *\n')

    def test_new_helper_rejects_non_guest_before_mutating(self):
        with patch.object(shell_lab, 'guard', side_effect=RuntimeError('not guest')):
            with self.assertRaises(RuntimeError): shell_lab.prepare(make_mission('shell_path', 7251).payload())
            with self.assertRaises(RuntimeError): shell_lab.grade(make_mission('shell_path', 7251).payload())

    def test_payload_cannot_select_unrelated_script_path(self):
        payload = make_mission('shell_args', 7251).payload()
        shell_lab.validate(payload)
        payload['review']['script'] = '/etc/profile'
        with self.assertRaises(ValueError): shell_lab.validate(payload)

    def test_error_and_option_explanations_are_explicit(self):
        units = {u.key: u for u in curriculum('real')[0]}
        self.assertIn('$?', units['shell_if'].explanation)
        self.assertIn('소문자 -c', units['shell_noclobber'].explanation)
        self.assertIn('같은 실제 파일', make_mission('shell_if', 7251).prompt)

    def test_compact_preservation_row_rejects_each_changed_file(self):
        m = make_mission('shell_source', 7251).payload()
        m['_reference'] = {'preserved': {'personal.txt': ['old'], 'settings.sh': ['old']}}
        for changed in (set(), {'personal.txt'}, {'settings.sh'}, {'personal.txt', 'settings.sh'}):
            with self.subTest(changed=changed), patch.object(shell_lab, 'guard'), \
                 patch.object(shell_lab, 'parent_environment', return_value={}), patch.object(shell_lab, 'read', return_value=None), \
                 patch.object(shell_lab, 'signature', side_effect=lambda path: ['new'] if path.name in changed else ['old']):
                result = shell_lab.grade(m)
            preservation = result['checks'][-1]
            self.assertEqual(preservation['passed'], not changed)
            self.assertTrue(all(name in preservation['label'] for name in changed))
            self.assertLessEqual(len(result['checks']), 7)

    def test_backup_still_required_in_compact_row(self):
        m = make_mission('shell_source', 7251).payload()
        m['review']['backup'] = True
        m['_reference'] = {'preserved': {}}
        for correct in (False, True):
            with self.subTest(correct=correct), patch.object(shell_lab, 'guard'), \
                 patch.object(shell_lab, 'parent_environment', return_value={}), \
                 patch.object(shell_lab, 'read', side_effect=lambda path: shell_lab.BROKEN.encode()
                              if correct and path.name == 'original script.txt' else None):
                last = shell_lab.grade(m)['checks'][-1]
            self.assertEqual(last['passed'], correct)
            if not correct: self.assertIn('original script.txt', last['label'])


if __name__ == '__main__': unittest.main()
