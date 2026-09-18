"""New APT teaching/grading contracts only; does not repeat the old course."""
import unittest
from pathlib import Path
from unittest.mock import patch
from types import SimpleNamespace

import apt_course as course
from guest import apt_lab
from learning_steps import learning_steps
from missions import make_mission, lesson_text
from mode_curriculum import curriculum
from real_course_checks import make_review


class AptCourseTests(unittest.TestCase):
    def test_append_preserves_existing_sixty_and_simulator(self):
        from linux_course import LINUX_ORDER
        units, reviews = curriculum('real')
        self.assertEqual(tuple(u.key for u in units[:60]), LINUX_ORDER)
        self.assertEqual(tuple(u.key for u in units[60:65]), course.KEYS)
        self.assertFalse(any(u.key in course.KEYS for u in curriculum('simulation')[0]))
        review = next(c for c in reviews if c.end == 65)
        self.assertEqual(make_review(review, 7251).kind, 'apt_review')
        self.assertEqual(tuple(u.key for u in review.units), course.KEYS)

    def test_each_unit_has_small_steps_and_distinct_application(self):
        by_key = {u.key: u for u in curriculum('real')[0]}
        for key in course.KEYS:
            with self.subTest(key=key):
                variants = [make_mission(key, 7251, v) for v in range(3)]
                self.assertEqual(len({m.prompt for m in variants}), 3)
                self.assertGreaterEqual(len(learning_steps(by_key[key], 'real', variants[0])), 2)
                self.assertIn(variants[0].solution, lesson_text(by_key[key], 'real').replace('4242', '7251'))
                for m in variants:
                    self.assertIn('personal.txt', m.prompt)
                    self.assertNotIn('F5', m.prompt)
                    self.assertNotIn('sudo apt', m.prompt)
                self.assertIn('backup', variants[2].solution)

    def test_parser_ignores_headings_not_status_version_or_arch(self):
        text = 'Desired=Unknown/Install\nii  shellground-helper 2.0 all Helper\nrc  shellground-note 1.0 all Note\n'
        self.assertEqual(apt_lab.dpkg_rows(text), {'shellground-helper': ['ii', '2.0', 'all'], 'shellground-note': ['rc', '1.0', 'all']})
        self.assertIsNone(apt_lab.dpkg_rows(text + text))
        self.assertEqual(apt_lab.apt_rows('Listing...\nshellground-note/unknown 2.0 all [upgradable from: 1.0]'),
                         [('shellground-note', '2.0', 'all', 'upgradable', ('from', '1.0'))])
        self.assertNotEqual(apt_lab.apt_rows('shellground-note/repo 2.0 all [upgradable from: 1.0]'),
                            apt_lab.apt_rows('shellground-note/repo 2.0 all [upgradable from: 2.0]'))

    def test_review_keeps_repaired_packages_and_purges_a_separate_target(self):
        m = make_mission('apt_review', 7251)
        self.assertEqual(m.review['expected_note'], 'installed')
        self.assertTrue(m.review['retired'])
        self.assertNotIn('repaired', m.review['reports'].values())
        self.assertIn('sudo apt purge shellground-retired-note', m.solution)
        self.assertNotIn('sudo apt purge shellground-note\n', m.solution)

    def test_inspection_version_matches_scenario(self):
        for v in range(3):
            plan = make_mission('apt_inspect', 1, v).review
            self.assertEqual(plan['note'], plan['expected_version'])
            self.assertEqual(plan['helper'], plan['expected_helper'])

    def test_purge_requires_database_state_not_only_deleted_config(self):
        m = make_mission('apt_purge', 7251).payload()
        m['_reference'] = {'apt_outside': {}}
        state = {course.NOTE: ['1.0', 'deinstall ok config-files'], course.HELPER: ['1.0', 'install ok installed']}
        with patch.object(apt_lab, 'require_guest'), patch.object(apt_lab, 'package_states', return_value=state), \
             patch.object(apt_lab, 'read', return_value=None), patch.object(apt_lab, 'run', return_value=SimpleNamespace(stdout='')):
            result = apt_lab.grade(m)
        self.assertFalse(result['passed'])
        self.assertFalse(result['checks'][0]['passed'])

    def test_guard_is_before_package_mutations(self):
        with patch.object(apt_lab, 'require_guest', side_effect=RuntimeError('not guest')), \
             patch.object(apt_lab, 'run') as run:
            with self.assertRaises(RuntimeError): apt_lab.prepare(make_mission('apt_remove', 1).payload())
            run.assert_not_called()


if __name__ == '__main__': unittest.main()
