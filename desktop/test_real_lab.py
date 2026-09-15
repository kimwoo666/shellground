"""Opt-in integration tests: SHELLGROUND_INTEGRATION=1 python -m unittest test_real_lab -v."""
import base64
import json
import os
import queue
import shlex
import threading
import time
import unittest
from engine import LabEngine
from missions import UNITS, make_mission, random_mission, lesson_text

# Archived real-container backend covers the original curriculum only.
# Version 4 simulator extensions are verified in test_simulator.py.
UNITS = tuple(u for u in UNITS if not u.key.startswith('sim_'))


class CurriculumTests(unittest.TestCase):
    def test_generated_scenarios(self):
        for unit in UNITS:
            for seed in range(30):
                mission = make_mission(unit.key, seed)
                self.assertNotEqual(mission.start, mission.source)
                self.assertTrue(mission.solution)
                self.assertTrue(mission.prompt)
                self.assertEqual(mission, make_mission(unit.key, seed))
                self.assertIn('옵션별 의미', lesson_text(unit))

    def test_second_practice_changes_the_task_not_only_paths(self):
        for unit in UNITS:
            first = make_mission(unit.key, 4242, practice=1)
            second = make_mission(unit.key, 4242, practice=2)
            self.assertEqual(first.source, second.source)
            self.assertEqual(first.target, second.target)
            if unit.key != 'edit': self.assertNotEqual(first.solution, second.solution, unit.key)
            self.assertNotEqual(first.prompt, second.prompt, unit.key)
            self.assertTrue(second.review['goals'], unit.key)

    def test_screen_tasks_do_not_add_unnecessary_no_save_instructions(self):
        for key in ['navigate', 'lsintro', 'pwdpaths']:
            unit = next(u for u in UNITS if u.key == key)
            texts = [unit.explanation, unit.hint, lesson_text(unit)]
            texts.extend(make_mission(key, 4242, practice=p).prompt for p in [0, 1, 2])
            for text in texts:
                with self.subTest(key=key, text=text):
                    self.assertNotRegex(text, r'저장하지|저장할 필요|저장은 필요|만들지 않아도|파일 저장')
        self.assertIn('수정하고 저장', make_mission('edit', 4242).prompt)
        self.assertIn('수정하지 마세요', make_mission('read', 4242).prompt)

    def test_ls_is_taught_early(self):
        self.assertEqual([u.key for u in UNITS[:10]], ['navigate', 'lsintro', 'mkdir', 'touch', 'read', 'edit', 'duplicate', 'rename', 'remove', 'report'])

    def test_prerequisites_and_short_lessons(self):
        for key in ['navigate', 'pwdpaths', 'lsintro']:
            m = make_mission(key, 4242)
            self.assertNotIn('cat ', m.solution)
            self.assertNotIn('>', m.solution)
        self.assertEqual([line.split()[0] for line in make_mission('pwdpaths').solution.splitlines()], ['cd', 'pwd', 'pwd'])
        for unit in UNITS[:7]:
            self.assertLess(len(unit.explanation), 400)
        self.assertNotIn('ls ', make_mission('navigate').solution)

    def test_old_topics_preserved_and_commands_introduced_before_use(self):
        old = {'navigate', 'workspace', 'copy', 'list', 'long', 'recursive', 'grep', 'find',
               'curl', 'wget', 'archive', 'script', 'deb', 'pwdpaths', 'lsoptions'}
        self.assertTrue(old.issubset({u.key for u in UNITS}))
        introduces = {'navigate': {'pwd', 'cd'}, 'lsintro': {'ls'}, 'mkdir': {'mkdir'},
                      'touch': {'touch'}, 'read': {'cat'}, 'edit': {'nano'}, 'duplicate': {'cp'},
                      'rename': {'mv'}, 'remove': {'rm'}, 'grep': {'grep', 'wc'}, 'find': {'find'},
                      'permissions': {'chmod'}, 'curl': {'curl'}, 'wget': {'wget'},
                      'archive': {'tar', 'unzip'}, 'deb': {'dpkg-deb'}}
        known = set()
        for unit in UNITS:
            known.update(introduces.get(unit.key, set()))
            for seed in range(10):
                for practice in [0, 1, 2]:
                    for line in make_mission(unit.key, seed, practice).solution.splitlines():
                        for command in line.split('|'):
                            name = shlex.split(command)[0]
                            if unit.key == 'script' and name.startswith(('/home/learner/', './', '../')): continue
                            self.assertIn(name, known, (unit.key, name))
            if unit.key in {'navigate', 'lsintro', 'mkdir', 'touch', 'read', 'edit', 'duplicate', 'rename', 'remove'}:
                self.assertNotIn('>', make_mission(unit.key).solution)

    def test_random_only_learned(self):
        with self.assertRaises(ValueError): random_mission([])
        for _ in range(50):
            self.assertEqual(random_mission(['navigate']).kind, 'navigate')
            self.assertEqual(random_mission(['navigate', 'workspace'], 'navigate').kind, 'workspace')


@unittest.skipUnless(os.environ.get('SHELLGROUND_INTEGRATION') == '1', 'Set SHELLGROUND_INTEGRATION=1 for Docker tests')
class RealLabTests(unittest.TestCase):
    def setUp(self):
        self.engine = LabEngine()
        self.engine.status()
        self.addCleanup(self.engine.close)

    def shell(self, command):
        return self.engine.command('exec', '-w', self.mission.start, self.engine.name, 'bash', '-c', command)

    def start(self, kind, seed=4242, practice=0):
        self.mission = make_mission(kind, seed, practice)
        self.engine.start(self.mission)
        return self.mission

    def interactive(self):
        process = self.engine.open_terminal(self.mission)
        outputs = queue.Queue()
        def read():
            try:
                for line in process.stdout:
                    data = base64.b64decode(json.loads(line)['output'])
                    self.engine.observe_output(data)
                    outputs.put(data)
            except (OSError, ValueError):
                pass
        threading.Thread(target=read, daemon=True).start()
        def until(token):
            output = b''
            end = time.monotonic() + 8
            while token not in output and time.monotonic() < end:
                try: output += outputs.get(timeout=.1)
                except queue.Empty: pass
            self.assertIn(token, output)
        until(b'learner@lab:')
        self.wait_output = until
        def run(command):
            self.engine.send((command + "\nprintf '\\n__SG_DONE__\\n'\n").encode())
            until(b'\r\n__SG_DONE__\r\n')
        return run

    def test_every_goal_rejects_untouched_and_accepts_real_results(self):
        for unit in UNITS:
            if unit.key in ('navigate', 'pwdpaths', 'lsintro', 'mixed', 'read', 'edit'): continue
            with self.subTest(kind=unit.key):
                mission = self.start(unit.key)
                self.assertFalse(self.engine.rpc('grade', mission)['passed'])
                self.shell(mission.solution)
                result = self.engine.rpc('grade', mission)
                self.assertTrue(result['passed'], result)

    def test_all_second_practices_require_and_accept_their_own_results(self):
        for unit in UNITS:
            with self.subTest(kind=unit.key):
                m = self.start(unit.key, practice=2)
                self.assertFalse(self.engine.rpc('grade', m)['passed'])
                if unit.key == 'edit':
                    self.interactive()
                    self.engine.send((m.solution + '\n').encode())
                    self.wait_output(b'GNU nano')
                    self.engine.send(b'\x0b\x0bstatus=ready\rowner=learner\rreviewed=yes\x0f')
                    self.wait_output(b'File Name to Write')
                    self.engine.send(b'\r')
                    self.wait_output(b'Wrote 3 lines')
                    self.engine.send(b'\x18')
                    self.wait_output(b'learner@lab:')
                elif unit.key in ('navigate', 'pwdpaths', 'lsintro', 'read', 'mixed', 'long', 'report', 'mkdir'):
                    self.interactive()(m.solution)
                else:
                    self.shell(m.solution)
                result = self.engine.rpc('grade', m)
                self.assertTrue(result['passed'], (unit.key, result))

    def test_repeating_basic_solution_is_not_enough_for_review(self):
        for kind in ['touch', 'duplicate', 'copy', 'list', 'grep', 'permissions', 'deb']:
            with self.subTest(kind=kind):
                m = self.start(kind, practice=2)
                self.shell(make_mission(kind, m.seed, practice=1).solution)
                self.assertFalse(self.engine.rpc('grade', m)['passed'], kind)

    def test_adjacent_and_distant_workflows(self):
        for kind in ['touch', 'copy', 'recursive', 'lsoptions', 'archive', 'script', 'deb']:
            for seed in [4243, 4244]:
                for practice in [0, 2]:
                    with self.subTest(kind=kind, seed=seed, practice=practice):
                        m = self.start(kind, seed, practice)
                        self.shell(m.solution)
                        result = self.engine.rpc('grade', m)
                        self.assertTrue(result['passed'], result)

    def test_absolute_and_relative_answers_both_work(self):
        for relative in [False, True]:
            m = self.start('touch')
            self.shell('touch /tmp/notes.txt')
            self.assertFalse(self.engine.rpc('grade', m)['passed'])
            path = 'notes.txt' if relative else m.target + '/notes.txt'
            self.shell('touch ' + shlex.quote(path))
            self.assertTrue(self.engine.rpc('grade', m)['passed'])

    def test_five_unit_checkpoints_accept_complete_work_not_partial_work(self):
        from checkpoints import CHECKPOINTS as ALL_CHECKPOINTS, make_checkpoint
        CHECKPOINTS = tuple(c for c in ALL_CHECKPOINTS if c.end <= 25)
        for checkpoint in CHECKPOINTS:
            for seed in [4242, 4243, 4244]:
                with self.subTest(end=checkpoint.end, seed=seed):
                    self.mission = m = make_checkpoint(checkpoint.end, seed)
                    self.engine.start(m)
                    self.assertFalse(self.engine.rpc('grade', m)['passed'])
                    run = self.interactive()
                    if checkpoint.end == 10:
                        commands = m.solution.splitlines()
                        nano = next(i for i, command in enumerate(commands) if command.startswith('nano '))
                        run('\n'.join(commands[:nano]))
                        self.assertFalse(self.engine.rpc('grade', m)['passed'])
                        self.engine.send((commands[nano] + '\n').encode())
                        self.wait_output(b'GNU nano')
                        self.engine.send(b'\x0bstatus=ready\x0f')
                        self.wait_output(b'File Name to Write')
                        self.engine.send(b'\r')
                        self.wait_output(b'Wrote 1 line')
                        self.engine.send(b'\x18')
                        self.wait_output(b'learner@lab:')
                        run('\n'.join(commands[nano + 1:]))
                    else:
                        run(m.solution)
                    result = self.engine.rpc('grade', m)
                    self.assertTrue(result['passed'], result)
                    required = next(goal['path'] for goal in m.review['goals'] if goal['type'] in ('file', 'copy'))
                    self.shell('rm -- ' + shlex.quote(required))
                    self.assertFalse(self.engine.rpc('grade', m)['passed'])

    def test_list_option_order_relative_paths_and_missing_hidden_files(self):
        m = self.start('recursive')
        self.shell(f'ls -lR {m.source} > {m.report}')
        self.assertFalse(self.engine.rpc('grade', m)['passed'])
        self.shell(f'ls -al {m.source} > {m.report}')
        self.assertFalse(self.engine.rpc('grade', m)['passed'])
        for command in [f'ls -Ral {m.source} > {m.report}',
                        f'cd {m.source} && ls -laR > {m.report}',
                        f'cd {m.source} && ls --all -l --recursive . > {m.report}',
                        f'cd /home/learner && ls -l -R -a {m.source.removeprefix("/home/learner/")} > {m.report}']:
            self.shell(command)
            result = self.engine.rpc('grade', m)
            self.assertTrue(result['passed'], (command, result))
        self.shell(f'rm {m.source}/.env && ls -alR {m.source} > {m.report}')
        self.assertFalse(self.engine.rpc('grade', m)['passed'], 'Deleting source data must not change the grading oracle')

    def test_wrong_name_corrupt_download_and_fifo_fail(self):
        m = self.start('curl')
        self.shell(f'curl -fsS {m.url} -o {m.target}/wrong-name')
        self.assertFalse(self.engine.rpc('grade', m)['passed'])
        self.shell(f'echo corrupted > {m.target}/received-{m.artifact}')
        self.assertFalse(self.engine.rpc('grade', m)['passed'])
        m = self.start('list')
        self.shell(f'mkfifo {m.report}')
        self.assertFalse(self.engine.rpc('grade', m)['passed'])

    def test_option_reports_reject_wrong_meanings(self):
        for seed in [4242, 4243, 4244]:
            m = self.start('lsoptions', seed)
            self.shell(m.solution)
            self.assertTrue(self.engine.rpc('grade', m)['passed'])
            for wrong, correct, suffix in [('-1a', '-1A', 'names'), ('-al', '-alh', 'sizes'), ('-1Sr', '-1S', 'largest')]:
                self.shell(f'ls {wrong} {m.source} > {m.report}.{suffix}')
                self.assertFalse(self.engine.rpc('grade', m)['passed'], (seed, wrong))
                self.shell(f'ls {correct} {m.source} > {m.report}.{suffix}')

    def test_pwd_and_ls_screen_practice_without_files(self):
        m = self.start('pwdpaths')
        run = self.interactive()
        self.assertFalse(self.engine.rpc('grade', m)['passed'])
        run(f'cd {m.start}/shortcut\npwd -L')
        self.assertFalse(self.engine.rpc('grade', m)['passed'], 'One path alone is insufficient')
        run('pwd -P')
        self.assertTrue(self.engine.rpc('grade', m)['passed'])
        self.assertEqual(self.shell('find /home/learner/reports -type f').strip(), '')
        m = self.start('lsintro')
        run = self.interactive()
        self.assertFalse(self.engine.rpc('grade', m)['passed'])
        run(f'ls {m.source}')
        self.assertFalse(self.engine.rpc('grade', m)['passed'], 'Hidden entries missing')
        run(f'ls -a {m.source}')
        self.assertTrue(self.engine.rpc('grade', m)['passed'])
        self.assertEqual(self.shell('find /home/learner/reports -type f').strip(), '')

    def test_mixed_requires_both_location_and_report(self):
        m = self.start('mixed')
        run = self.interactive()
        self.assertFalse(self.engine.rpc('grade', m)['passed'])
        run(f'ls -al {m.source} > {m.report}')
        self.assertFalse(self.engine.rpc('grade', m)['passed'], 'Correct report but wrong current location')
        run(f'cd {m.source}')
        self.assertTrue(self.engine.rpc('grade', m)['passed'])
        run(f'ls -l > {m.report}')
        self.assertFalse(self.engine.rpc('grade', m)['passed'], 'Correct location but missing hidden entries')
        run(m.solution)
        self.assertTrue(self.engine.rpc('grade', m)['passed'])

    def test_read_then_edit_with_real_nano(self):
        m = self.start('read')
        run = self.interactive()
        self.assertFalse(self.engine.rpc('grade', m)['passed'])
        run(m.solution)
        self.assertTrue(self.engine.rpc('grade', m)['passed'])
        m = self.start('edit')
        self.interactive()
        self.assertFalse(self.engine.rpc('grade', m)['passed'])
        self.engine.send((m.solution + '\n').encode())
        self.wait_output(b'GNU nano')
        self.engine.send(b'\x0bstatus=ready')
        self.assertFalse(self.engine.rpc('grade', m)['passed'], 'Unsaved edits must not pass')
        self.engine.send(b'\x0f')
        self.wait_output(b'File Name to Write')
        self.engine.send(b'\r')
        self.wait_output(b'Wrote 1 line')
        self.engine.send(b'\x18')
        self.wait_output(b'learner@lab:')
        self.assertTrue(self.engine.rpc('grade', m)['passed'])

    def test_download_all_formats_both_tools(self):
        for artifact in ['toolkit.deb', 'setup.sh', 'bundle.tar.gz', 'bundle.zip']:
            seed = next(i for i in range(100) if make_mission('curl', i).artifact == artifact)
            m = self.start('curl', seed)
            self.shell(f'wget -q -O {m.target}/received-{artifact} {m.url}')
            self.assertTrue(self.engine.rpc('grade', m)['passed'])

    def test_isolation(self):
        self.start('workspace')
        info = json.loads(self.engine.command('inspect', self.engine.name))[0]
        self.assertTrue(info['HostConfig']['ReadonlyRootfs'])
        self.assertEqual(info['HostConfig']['NetworkMode'], 'none')
        self.assertFalse(info['HostConfig']['Binds'])
        self.assertEqual(info['Config']['User'], '1100:1100')
        self.assertEqual(self.shell('test ! -e /var/run/docker.sock && test ! -w /etc && echo isolated').strip(), 'isolated')

    def test_real_pty_cwd_tab_history_errors_interrupt_and_resize(self):
        m = self.start('navigate')
        process = self.engine.open_terminal(m)
        outputs = queue.Queue()
        def read():
            for line in process.stdout:
                outputs.put(base64.b64decode(json.loads(line)['output']))
        reader = threading.Thread(target=read, daemon=True)
        reader.start()
        def until(token, timeout=8):
            collected = b''
            end = time.monotonic() + timeout
            while token not in collected and time.monotonic() < end:
                try: collected += outputs.get(timeout=.2)
                except queue.Empty: pass
            self.assertIn(token, collected)
            return collected
        until(b'learner@lab:')
        self.engine.resize(31, 95)
        self.engine.send(f'cd {m.source}/do'.encode() + b'\t\r')
        until(b'/docs$')
        self.assertTrue(self.engine.rpc('grade', m)['passed'])
        self.engine.send(b"stty size; printf '\\n__DONE1__\\n'\r")
        self.assertIn(b'31 95', until(b'\r\n__DONE1__\r\n'))
        self.engine.send(b'echo persistent-history\r')
        until(b'\rpersistent-history\r\n')
        self.engine.send(b'\x1b[A\r')
        until(b'\rpersistent-history\r\n')
        self.engine.send(b'not_a_real_command\r')
        until(b'command not found')
        self.engine.send(b'sleep 30\r')
        time.sleep(.2)
        self.engine.send(b'\x03')
        until(b'^C')
        self.engine.send(b"printf '\\n__ALIVE__\\n'\r")
        until(b'\r\n__ALIVE__\r\n')
        self.engine.send(b'exit\r')
        process.wait(timeout=5)
        reader.join(timeout=3)


if __name__ == '__main__': unittest.main()
