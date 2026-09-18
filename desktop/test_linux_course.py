"""Teaching order and grading-contract regressions; no simulated shell changes."""
import shlex
import unittest

from checkpoints import make_checkpoint
from course_topics import topic_of
from learning_steps import learning_steps
from linux_course import LINUX_ORDER, NEW_KEYS
from missions import UNITS, make_mission
from mode_curriculum import ADMIN_UNITS, curriculum
from real_lessons import adapt_real_mission


class RealLinuxCourseTests(unittest.TestCase):
    def test_contents_are_added_not_removed_and_reviews_follow_actual_blocks(self):
        units, checks = curriculum('real')
        self.assertEqual(len(units), 135)
        self.assertEqual(len(checks), 27)
        self.assertEqual(tuple(u.key for u in units[:60]), LINUX_ORDER)
        old_linux = {u.key for u in UNITS + ADMIN_UNITS if topic_of(u) == '리눅스'}
        self.assertEqual(set(LINUX_ORDER), old_linux | NEW_KEYS)
        self.assertEqual(len(NEW_KEYS), 25)
        for c in checks:
            self.assertEqual(c.units, units[c.end - 5:c.end])
            m = make_checkpoint(c.end, 7251, mode='real')
            self.assertEqual(m.review['checkpoint'], c.key)
            self.assertEqual(m.review['units'], [u.key for u in c.units])
        self.assertEqual(len(curriculum('simulation')[0]), 45)

    def test_solutions_and_small_steps_use_only_introduced_commands(self):
        introduced = {
            'navigate': {'pwd', 'cd'}, 'lsintro': {'ls'}, 'read': {'cat'}, 'mkdir': {'mkdir'},
            'touch': {'touch'}, 'edit': {'nano'}, 'duplicate': {'cp'}, 'rename': {'mv'}, 'remove': {'rm'},
            'linux_grep_basic': {'grep'}, 'linux_head': {'head'}, 'linux_tail': {'tail'}, 'linux_line_count': {'wc'},
            'find': {'find'}, 'permissions': {'chmod'}, 'curl': {'curl'}, 'wget': {'wget'},
            'linux_tar_list': {'tar'}, 'archive': {'unzip'}, 'script': {'@script'}, 'linux_deb_info': {'dpkg-deb'},
            'sim_env': {'export', 'printenv', 'bash', 'unset'}, 'sim_author': {'printf'},
            'sim_jobs': {'sleep', 'jobs', 'kill'}, 'sim_apt': {'sudo', 'apt', 'tree'},
            'admin_uid': {'whoami', 'id'}, 'admin_group_ids': {'groups'}, 'admin_passwd': {'getent'},
            'admin_chown': {'chown'}, 'admin_chgrp': {'chgrp'}, 'admin_group_create': {'groupadd'},
            'admin_user_uid': {'useradd'}, 'admin_group_append': {'usermod'},
        }
        known = set()
        for index, unit in enumerate(curriculum('real')[0][:60]):
            known.update(introduced.get(unit.key, ()))
            for seed in (7251, 9853):
                for practice in (0, 1, 2):
                    m = adapt_real_mission(make_mission(unit.key, seed, practice))
                    scripts = [m.solution]
                    if practice == 0: scripts += [s.commands for s in learning_steps(unit, 'real', m)]
                    if practice == 0 and (index + 1) % 5 == 0:
                        scripts.append(make_checkpoint(index + 1, seed, mode='real').solution)
                    for script in scripts:
                        for line in script.splitlines():
                            parts = shlex.split(line)
                            commands = [parts[0]] if parts else []
                            commands += [parts[n + 1] for n, word in enumerate(parts[:-1]) if word in ('|', 'sudo')]
                            for command in commands:
                                if '/' in command: command = '@script'
                                self.assertIn(command, known, (index + 1, unit.key, practice, line))
                            if index < 5: self.assertNotIn('>', parts, (unit.key, line))
                            if index < 25: self.assertNotIn('|', parts, (unit.key, line))

    def test_useradd_options_accumulate_one_concept_at_a_time(self):
        allowed = set()
        for key, new in [('admin_user_uid', {'-u'}), ('admin_user_home', {'-d', '-m'}),
                         ('admin_user_shell', {'-s'}), ('admin_user_primary', {'-g'}), ('admin_user_extra', {'-G'})]:
            allowed |= new
            for practice in (0, 1, 2):
                solution = make_mission(key, 7251, practice).solution
                useradd = next(shlex.split(line) for line in solution.splitlines() if 'useradd ' in line)
                self.assertEqual({w for w in useradd if w.startswith('-')}, allowed)

    def test_errors_are_explained_before_complex_copy_practice(self):
        units = {u.key: u for u in curriculum('real')[0]}
        first = '\n'.join(s.text for s in learning_steps(units['navigate'], 'real'))
        for text in ('too many arguments', 'Not a directory', 'No such file or directory', '따옴표'):
            self.assertIn(text, first)
        self.assertIn('cp 원본 대상', units['duplicate'].explanation)
        self.assertIn('missing destination file operand', units['duplicate'].explanation)


if __name__ == '__main__': unittest.main()
