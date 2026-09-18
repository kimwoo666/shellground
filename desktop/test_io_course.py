import unittest
import tempfile
from pathlib import Path
from unittest.mock import patch
from io_course import KEYS, make_mission
from guest import io_lab
from mode_curriculum import curriculum
from learning_steps import learning_steps
from real_course_checks import make_review


class IOCourseTests(unittest.TestCase):
    def test_registration_preserves_prior_keys_and_no_simulator_addition(self):
        units, reviews = curriculum('real')
        self.assertEqual(tuple(u.key for u in units[80:85]), KEYS)
        self.assertEqual(make_review(next(c for c in reviews if c.end == 85), 7251).kind, 'io_review')
        self.assertFalse(any(u.key in KEYS for u in curriculum('simulation')[0]))

    def test_distinct_applications_and_interactive_steps(self):
        units = {u.key: u for u in curriculum('real')[0]}
        for key in KEYS:
            with self.subTest(key=key):
                missions = [make_mission(key, 7251, variant) for variant in range(3)]
                self.assertEqual(len({m.prompt for m in missions}), 3)
                self.assertEqual(len({m.solution for m in missions}), 3)
                steps = learning_steps(units[key], 'real', missions[0])
                self.assertEqual(len(steps), 3)
                self.assertTrue(all(s.explanation and s.commands and s.observation for s in steps))
                for mission in missions:
                    io_lab.validate(mission.payload())
                    self.assertNotIn('F5', mission.prompt)
        self.assertIn('# Ctrl+D', make_mission('io_input', 7251).solution)
        self.assertIn('# more:', make_mission('io_pager', 7251).solution)

    def test_guest_guard_and_exact_owned_paths(self):
        mission = make_mission('io_input', 7251).payload()
        with patch.object(io_lab, 'guard', side_effect=RuntimeError('not guest')):
            with self.assertRaises(RuntimeError): io_lab.prepare(mission)
            with self.assertRaises(RuntimeError): io_lab.grade(mission)
        mission['start'] = '/tmp'
        with self.assertRaises(ValueError): io_lab.validate(mission)
        mission = make_mission('io_input', 7251).payload()
        mission['review']['files']['../../outside'] = 'x'
        with self.assertRaises(ValueError): io_lab.validate(mission)

    def test_tree_hierarchy_accepts_charsets_order_footer_and_root_spelling(self):
        root = Path('/home/learner/io/session7251/inventory')
        outputs = ('inventory\n├── .hidden\n│   └── item\n└── file with spaces\n\n1 directory, 2 files\n',
                   './inventory\n|-- file with spaces\n`-- .hidden\n    `-- item\n',
                   str(root) + '\n|-- .hidden\n|   `-- item\n`-- file with spaces\n',
                   '.\n|-- .hidden\n|   `-- item\n`-- file with spaces\n')
        for output in outputs:
            self.assertEqual(io_lab.parse_tree(output.encode(), root), {'.hidden', '.hidden/item', 'file with spaces'})
        for output in ('inventory\n.hidden\nitem\nfile with spaces\n',
                       'inventory\n    └── child\n', 'other\n└── file\n',
                       'inventory\n├── item\n└── item\n'):
            self.assertIsNone(io_lab.parse_tree(output.encode(), root))

    def test_shebang_is_not_replaced_by_matching_stdout(self):
        for content in (None, b'printf ready\n', b'\n#!/bin/bash\n', b'#!/missing/bash\n', b'#!/bin/sh\n', b'#!/bin/bash\r\n'):
            self.assertFalse(io_lab.bash_header(content), content)
        for content in (b'#!/bin/bash\n', b'#!/usr/bin/bash\n', b'#! /usr/bin/env bash\n'):
            self.assertTrue(io_lab.bash_header(content), content)

    def test_names_order_is_free_but_line_boundaries_duplicates_and_header_are_not(self):
        expected = b'.\n..\n.hidden\nfile A\n'
        self.assertTrue(io_lab.same_names(b'file A\n.hidden\n..\n.\n', expected))
        for actual in (None, b'. .. .hidden file A\n', expected + b'.hidden\n', expected.rstrip()):
            self.assertFalse(io_lab.same_names(actual, expected))
        self.assertTrue(io_lab.script_output(b'directory=../inventory\nfile A\n.hidden\n..\n.\n', '../inventory', expected))
        self.assertFalse(io_lab.script_output(b'directory=inventory\n' + expected, '../inventory', expected))

    def test_directory_preservation_includes_permissions_and_rejects_symlinks(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); folder = root / 'folder'; folder.mkdir(mode=0o755)
            before = io_lab.directory_signature(folder)
            folder.chmod(0o700)
            self.assertNotEqual(io_lab.directory_signature(folder), before)
            link = root / 'link'; link.symlink_to(folder)
            self.assertIsNone(io_lab.directory_signature(link))

    def test_basic_meanings_do_not_repeat_lecture_errors(self):
        units = {u.key: u for u in curriculum('real')[0]}
        self.assertIn('^D 두 글자', units['io_input'].explanation)
        self.assertIn('스크롤', units['io_pager'].explanation)
        self.assertIn('.과 ..는 표시하지', units['io_tree'].explanation)
        self.assertIn('모든 상황에서 반드시 실패', units['io_shebang'].explanation)
        self.assertIn('다른 OS나 CPU', units['io_binary'].explanation)


if __name__ == '__main__': unittest.main()
