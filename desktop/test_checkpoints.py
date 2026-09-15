import json
from pathlib import Path
import shlex
import tempfile
import unittest
from unittest.mock import patch

from PySide6.QtWidgets import QDialog, QMessageBox
from checkpoints import CHECKPOINTS, checkpoint_at, make_checkpoint
from missions import UNITS
from native_app import Window, create_application


class CheckpointContentTests(unittest.TestCase):
    def test_five_blocks_preserve_regular_units(self):
        self.assertEqual([c.end for c in CHECKPOINTS], list(range(5, 41, 5)))
        self.assertEqual(len(UNITS), 40)
        self.assertEqual([u for c in CHECKPOINTS for u in c.units], list(UNITS))

    def test_generated_tasks_only_use_learned_commands(self):
        introduced = {'navigate': {'pwd', 'cd'}, 'lsintro': {'ls'}, 'mkdir': {'mkdir'},
                      'touch': {'touch'}, 'read': {'cat'}, 'edit': {'nano'}, 'duplicate': {'cp'},
                      'rename': {'mv'}, 'remove': {'rm'}, 'grep': {'grep', 'wc'}, 'find': {'find'},
                      'permissions': {'chmod'}, 'curl': {'curl'}, 'wget': {'wget'},
                      'archive': {'tar', 'unzip'}, 'deb': {'dpkg-deb'}}
        introduced.update({'sim_env': {'export', 'unset', 'bash', 'printenv'},
                           'sim_author': {'printf'}, 'sim_jobs': {'sleep', 'kill', 'jobs'},
                           'sim_apt': {'apt', 'sudo'}, 'sim_images': {'docker'}})
        for checkpoint in CHECKPOINTS:
            known = set().union(*(introduced.get(u.key, set()) for u in UNITS[:checkpoint.end]))
            for seed in range(12):
                m = make_checkpoint(checkpoint.end, seed)
                self.assertEqual(m, make_checkpoint(checkpoint.end, seed))
                self.assertEqual(m.review['units'], [u.key for u in checkpoint.units])
                if checkpoint.end <= 25: self.assertGreaterEqual(len(m.review['goals']), 3)
                else: self.assertIn('extension', m.review)
                self.assertNotIn('편집기 조작:', m.prompt)
                self.assertNotIn('cd .\n', m.solution)
                for line in m.solution.splitlines():
                    for command in line.split('|'):
                        name = shlex.split(command)[0]
                        if name.startswith('./'):
                            self.assertGreaterEqual(checkpoint.end, 25)
                        else:
                            self.assertIn(name, known)
        with self.assertRaises(StopIteration):
            make_checkpoint(6)


class CheckpointUITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app, cls.ui, cls.mono = create_application()

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / 'progress.json'
        self.window = Window(self.ui, self.mono, self.path)

    def tearDown(self):
        self.window.deleteLater()
        self.app.processEvents()
        self.temp.cleanup()

    def fake_jobs(self, value):
        return patch.object(self.window, 'run_job', side_effect=lambda fn, cb, **kwargs: cb(value))

    def test_sidebar_interleaves_checkpoints_without_renumbering(self):
        w = self.window
        self.assertEqual(w.course.count(), 48)
        for c in CHECKPOINTS:
            row = w.checkpoint_rows[c.end]
            self.assertEqual(w.course.item(row).data(256), ('checkpoint', c.end))
            self.assertTrue(w.course.item(row - 1).text().startswith(f'{c.end:02d}.'))
            if c.end < len(UNITS): self.assertTrue(w.course.item(row + 1).text().startswith(f'{c.end + 1:02d}.'))
        w.select_checkpoint(5)
        self.assertEqual(w.phase, 'learn')
        self.assertIn('완료하면', w.feedback.text())

    def test_boundary_routes_to_checkpoint_and_requires_passing_it(self):
        w = self.window
        w.completed = [u.key for u in UNITS[:4]]
        w.index, w.phase, w.practice_number = 4, 'practice', 2
        from missions import make_mission
        w.mission = make_mission('read', 4242, 2)
        w.terminal.connected = True
        with self.fake_jobs({'passed': True, 'checks': []}):
            w.grade()
        self.assertEqual(len(w.completed), 5)
        self.assertFalse(w.lesson_unlocked(5))
        self.assertIn('종합 복습', w.next_button.text())
        w.advance()
        self.assertEqual(w.phase, 'checkpoint_ready')
        self.assertEqual(w.checkpoint_end, 5)
        with patch.object(w, 'run_job'):
            w.advance()
        self.assertEqual(w.phase, 'checkpoint')
        self.assertNotIn(w.mission.solution, w.instructions.toPlainText())
        w.terminal.connected = True
        with self.fake_jobs({'passed': False, 'checks': []}):
            w.grade()
        self.assertEqual(w.completed_checkpoints, [])
        w.advance()
        self.assertEqual(w.phase, 'checkpoint')
        with self.fake_jobs({'passed': True, 'checks': []}):
            w.grade()
        self.assertEqual(w.completed_checkpoints, ['checkpoint-05'])
        self.assertEqual(json.loads(self.path.read_text())['checkpoints'], ['checkpoint-05'])
        self.assertTrue(w.lesson_unlocked(5))
        w.advance()
        self.assertEqual((w.index, w.phase, w.checkpoint_end), (5, 'learn', None))

    def test_resume_pending_checkpoint_and_preserve_legacy_completions(self):
        w = self.window
        w.completed = [u.key for u in UNITS]
        w.save_progress()
        restored = Window(self.ui, self.mono, self.path)
        self.assertEqual(restored.completed, w.completed)
        self.assertEqual((restored.phase, restored.checkpoint_end), ('checkpoint_ready', 5))
        self.assertTrue(restored.lesson_unlocked(25), 'Previously completed units stay available')
        restored.completed_checkpoints = ['checkpoint-05']
        restored.save_progress()
        again = Window(self.ui, self.mono, self.path)
        self.assertEqual(again.checkpoint_end, 10)
        self.assertIsNone(again.mission)
        restored.deleteLater(); again.deleteLater()

    def test_checkpoint_options_scope_hints_and_repeat(self):
        w = self.window
        w.completed = [u.key for u in UNITS]
        w.completed_checkpoints = [c.key for c in CHECKPOINTS]
        w.refresh_course()
        w.select_checkpoint(10)
        with patch('native_app.lesson_text', return_value='reference') as lesson, patch.object(QDialog, 'exec', return_value=0):
            w.show_options()
            self.assertEqual([call.args[0] for call in lesson.call_args_list], list(UNITS[5:10]))
        with patch.object(w, 'run_job'), patch('native_app.make_checkpoint', wraps=make_checkpoint) as factory:
            w.advance()
            self.assertNotIn('Ctrl+O', w.instructions.toPlainText())
            with patch.object(QMessageBox, 'information') as hint:
                w.show_hint()
                self.assertIn('nano ', hint.call_args.args[2])
                self.assertIn('Ctrl+O', hint.call_args.args[2])
            w.passed = True
            w.select_checkpoint(10)
            w.advance()
            self.assertEqual(factory.call_count, 2)
        self.assertEqual(len(w.completed_checkpoints), 8)

    def test_every_checkpoint_unlocks_the_next_regular_unit(self):
        w = self.window
        for c in CHECKPOINTS:
            w.completed = [u.key for u in UNITS[:c.end]]
            w.completed_checkpoints = [x.key for x in CHECKPOINTS if x.end < c.end]
            w.refresh_course()
            self.assertFalse(w.lesson_unlocked(c.end))
            w.select_checkpoint(c.end, initial=True)
            with patch.object(w, 'run_job'):
                w.advance()
            w.terminal.connected = True
            with self.fake_jobs({'passed': True, 'checks': []}):
                w.grade()
            with patch.object(w, 'launch'):
                w.advance()
            if c.end < len(UNITS):
                self.assertEqual(w.index, c.end)
                self.assertEqual(w.phase, 'learn')
            else: self.assertEqual(w.phase, 'random')
