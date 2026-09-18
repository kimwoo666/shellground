import copy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from admin_lessons import make_admin_mission
from checkpoints import make_checkpoint
from mode_curriculum import ADMIN_UNITS, curriculum
from missions import UNITS, lesson_text, random_mission
from sim_admin import accounts
from sim_engine import SimEngine


class AdminLessonsTests(unittest.TestCase):
    def solve(self, mission):
        engine = SimEngine()
        engine.start(mission)
        self.assertFalse(engine.rpc('grade', mission)['passed'], mission.kind)
        for line in mission.solution.splitlines():
            result = engine.shell.execute(line)
            self.assertEqual(result.code, 0, (mission.kind, mission.practice, line, result.err))
        self.assertTrue(engine.rpc('grade', mission)['passed'], engine.rpc('grade', mission))
        return engine

    def test_all_units_variants_and_review_without_host_execution(self):
        with patch('subprocess.Popen', side_effect=AssertionError('No host execution')), patch('socket.socket', side_effect=AssertionError('No network')):
            for seed in (1234, 5678, 9998):
                for unit in ADMIN_UNITS:
                    for variant in (0, 1, 2):
                        with self.subTest(key=unit.key, seed=seed, variant=variant):
                            self.solve(make_admin_mission(unit.key, seed, variant))
                self.solve(make_admin_mission('admin_review', seed))

    def test_nonnumeric_chmod_solution_is_accepted(self):
        m = make_admin_mission('admin_modes', 1234)
        e = SimEngine(); e.start(m)
        self.assertEqual(e.shell.execute('chmod u=rw,g=r,o= notes.txt; chmod u=rwx,g=rx,o= private').code, 0)
        self.assertTrue(e.rpc('grade', m)['passed'])
        e.shell.execute('chmod 777 private')
        self.assertFalse(e.rpc('grade', m)['passed'])
        e.shell.execute('chmod 750 private')
        self.assertTrue(e.rpc('grade', m)['passed'])

    def test_group_replacement_loses_membership_and_cannot_pass(self):
        m = make_admin_mission('admin_groups', 1234)
        e = SimEngine(); e.start(m)
        e.shell.execute('sudo groupadd -g 13704 sgops1234')
        e.shell.execute('sudo usermod -G sgops1234 sguser1234')
        e.shell.execute('id -Gn sguser1234 > groups.txt')
        self.assertFalse(e.rpc('grade', m)['passed'])
        self.assertNotIn('sgaudit1234', accounts(e.shell.fs).user_info('sguser1234')['groups'])
        e.shell.execute('sudo usermod -a -G sgaudit1234 sguser1234; id -Gn sguser1234 > groups.txt')
        self.assertTrue(e.rpc('grade', m)['passed'])

    def test_account_record_alone_does_not_replace_home_creation(self):
        m = make_admin_mission('admin_users', 1234)
        e = SimEngine(); e.start(m)
        self.assertEqual(e.shell.execute(m.solution.replace(' -m ', ' ')).code, 0)
        self.assertFalse(e.rpc('grade', m)['passed'])

    def test_group_permissions_and_sudo_target_are_stateful(self):
        m = make_admin_mission('admin_owners', 1234)
        e = self.solve(m)
        self.assertEqual(e.shell.execute('sudo -u sguser1234 cat handoff.txt').code, 0)
        e.shell.execute('chmod 600 handoff.txt')
        self.assertNotEqual(e.shell.execute('sudo -u sguser1234 cat handoff.txt').code, 0)
        self.assertEqual(e.shell.fs.uid, 1100)
        self.assertEqual(e.shell.execute('cat handoff.txt').code, 0)
        self.assertNotEqual(e.shell.execute('chown root handoff.txt').code, 0)

    def test_failed_user_creation_does_not_change_accounts(self):
        e = SimEngine(); e.start(make_admin_mission('admin_users', 1234))
        db = accounts(e.shell.fs)
        before = copy.deepcopy((db.users, db.groups))
        for script in ('sudo useradd -u 1100 duplicate', 'sudo useradd Bad!Name',
                       'sudo useradd -d relative invalidhome', 'sudo useradd -G missinggroup trainee'):
            self.assertNotEqual(e.shell.execute(script).code, 0, script)
            self.assertEqual((db.users, db.groups), before)

    def test_copy_needs_a_permission_change_and_keeps_original_private(self):
        m = make_admin_mission('admin_modes', 1234, 2)
        e = SimEngine(); e.start(m)
        e.shell.execute('cp "source note.txt" "shared copy.txt"')
        self.assertFalse(e.rpc('grade', m)['passed'])
        e.shell.execute('chmod 644 "shared copy.txt"')
        self.assertTrue(e.rpc('grade', m)['passed'])
        self.assertEqual(e.shell.fs.get(m.source).mode, 0o600)

    def test_preserves_old_keys_and_has_mode_specific_checkpoint(self):
        sim, sim_checks = curriculum('simulation')
        real, real_checks = curriculum('real')
        self.assertEqual(sim[:40], UNITS)
        self.assertTrue({u.key for u in UNITS}.issubset({u.key for u in real}))
        self.assertEqual(sim[40:], ADMIN_UNITS)
        self.assertEqual(tuple(u for u in real if u.key in {a.key for a in ADMIN_UNITS}), ADMIN_UNITS)
        for mode, end in (('simulation', 45), ('real', 60)):
            m = make_checkpoint(end, 1234, mode=mode)
            expected = ADMIN_UNITS if mode == 'simulation' else real[55:60]
            self.assertEqual(m.review['units'], [u.key for u in expected])
            self.assertEqual(m.review['checkpoint'], 'admin-checkpoint-accounts' if mode == 'simulation' else 'real-linux-v2-60')
            self.solve(m)
        self.assertEqual(make_checkpoint(80, 1234).kind, 'ros_review45')
        for unit in ADMIN_UNITS: self.assertIn('직접 해볼 예시', lesson_text(unit))
        self.assertEqual(random_mission(['admin_users'], units=sim).kind, 'admin_users')


class AdminUITests(unittest.TestCase):
    def test_section_progress_and_test_hiding_in_both_modes(self):
        from native_app import Window, create_application
        from real_vm import RealEngine
        app, ui, mono = create_application()
        for mode, first, end in (('simulation', 40, 45), ('real', 40, 60)):
            with tempfile.TemporaryDirectory() as directory, patch('native_app.create_engine', return_value=SimEngine() if mode == 'simulation' else RealEngine()):
                path = Path(directory) / 'progress.json'
                w = Window(ui, mono, path, mode=mode)
                self.assertTrue(w.lesson_unlocked(first))
                self.assertTrue(w.lesson_unlocked(first + 1))
                w.completed = [u.key for u in (*UNITS[:5], *ADMIN_UNITS)]
                self.assertTrue(w.checkpoint_unlocked(end))
                w.completed_checkpoints = ['checkpoint-05', 'admin-checkpoint-accounts'] if mode == 'simulation' else ['real-linux-v2-05', 'real-linux-v2-60']
                w.save_progress()
                w.phase = 'practice'; w.refresh_course()
                for unit in ADMIN_UNITS:
                    row = w.course.item(w.unit_rows[next(i for i, u in enumerate(w.units) if u.key == unit.key)]).text()
                    self.assertNotIn(unit.title, row)
                    self.assertNotIn(unit.commands, row)
                restored = Window(ui, mono, path, mode=mode)
                self.assertEqual(set(restored.completed), set(w.completed))
                self.assertEqual(set(restored.completed_checkpoints), set(w.completed_checkpoints))
                w.deleteLater(); restored.deleteLater(); app.processEvents()


if __name__ == '__main__': unittest.main()
