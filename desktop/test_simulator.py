"""Pure offline engine regressions. Requires neither Docker nor a VM."""
import unittest
import os
import subprocess
import tempfile
from unittest.mock import patch
from sim_engine import SimEngine
from missions import UNITS, make_mission
from checkpoints import CHECKPOINTS, make_checkpoint


class SimulatorTests(unittest.TestCase):
    def start(self, kind='mkdir', seed=4242, practice=0):
        self.mission = make_mission(kind, seed, practice)
        self.engine = SimEngine(); self.engine.start(self.mission)
        self.shell = self.engine.shell
        return self.mission

    def run_command(self, command):
        r = self.shell.execute(command)
        self.assertEqual(r.code, 0, (command, r.err.decode()))
        return r.out

    def solve(self, mission):
        for command in mission.solution.splitlines():
            self.run_command(command)
            if self.shell.editor:
                for key in '\x0b' + ('\x0bstatus=ready\rowner=learner\rreviewed=yes' if mission.practice == 2 else 'status=ready') + '\x0f\r\x18':
                    self.engine.editor_key(key)

    def test_every_mission_and_checkpoint(self):
        for unit in UNITS:
            for seed in (4242, 4243, 4244):
                for variant in (0, 1, 2):
                    with self.subTest(key=unit.key, seed=seed, variant=variant):
                        m = self.start(unit.key, seed, variant)
                        self.assertFalse(self.engine.rpc('grade', m)['passed'])
                        self.solve(m)
                        self.assertTrue(self.engine.rpc('grade', m)['passed'], self.engine.rpc('grade', m))
        for checkpoint in CHECKPOINTS:
            with self.subTest(checkpoint=checkpoint.end):
                m = make_checkpoint(checkpoint.end, 4242, mode='simulation')
                self.engine = SimEngine(); self.engine.start(m); self.shell = self.engine.shell
                self.assertFalse(self.engine.rpc('grade', m)['passed'])
                self.solve(m)
                self.assertTrue(self.engine.rpc('grade', m)['passed'], self.engine.rpc('grade', m))

    def test_shell_state_quotes_pipes_and_redirections(self):
        self.start()
        self.run_command("mkdir -p 'space dir/sub'; printf 'Hello\\nerror one\\nERROR two\\n' > 'space dir/a.txt'")
        out = self.run_command("cat 'space dir/a.txt' | grep -i error | wc -l")
        self.assertEqual(out.strip(), b'2')
        self.run_command("printf 'again\\n' >> 'space dir/a.txt'")
        self.assertTrue(self.shell.fs.read(self.shell.path('space dir/a.txt')).endswith(b'again\n'))
        self.assertEqual(self.run_command('export VALUE="two words"; printf "%s\\n" "$VALUE"'), b'two words\n')
        self.assertEqual(self.run_command("printf '%s\\n' '$VALUE'"), b'$VALUE\n')
        self.assertEqual(self.run_command('false && echo wrong; true || echo wrong; echo $?'), b'0\n')
        cwd = self.shell.cwd
        self.run_command('cd /tmp | cat')
        self.assertEqual(self.shell.cwd, cwd)
        self.assertNotEqual(self.shell.execute('cat missing 2> error.txt').code, 0)
        self.assertIn(b'No such file', self.shell.fs.read(self.shell.path('error.txt')))
        self.assertEqual(self.run_command('cat < error.txt'), self.shell.fs.read(self.shell.path('error.txt')))

    def test_permissions_links_and_fail_closed(self):
        self.start()
        self.run_command('mkdir actual; ln -s actual link; cd link')
        self.assertTrue(self.run_command('pwd -L').strip().endswith(b'/link'))
        self.assertTrue(self.run_command('pwd -P').strip().endswith(b'/actual'))
        self.run_command('printf protected > item; chmod 400 item')
        self.assertNotEqual(self.shell.execute('printf changed > item').code, 0)
        self.assertEqual(self.run_command('cat item'), b'protected')
        for command in ('ls --invented', 'docker run --privileged ubuntu', 'cat $(whoami)', 'nosuchcommand', 'curl https://example.com/file'):
            self.assertNotEqual(self.shell.execute(command).code, 0, command)
        self.assertFalse(self.shell.fs.exists('/etc/shadow'))

    def test_docker_failure_states_and_image_update(self):
        self.start('sim_update')
        name = f'box{self.mission.seed}'
        old = self.shell.docker.containers[name]['image']
        self.assertNotEqual(self.shell.execute(f'docker rm {name}').code, 0)
        self.assertNotEqual(self.shell.execute('docker rmi ubuntu:24.04').code, 0)
        self.run_command('docker pull ubuntu:24.04')
        self.assertEqual(self.shell.docker.containers[name]['image'], old)
        self.assertNotEqual(self.shell.docker.images['ubuntu:24.04']['id'], old)
        self.assertFalse(self.engine.rpc('grade', self.mission)['passed'])
        self.solve(self.mission)
        self.assertTrue(self.engine.rpc('grade', self.mission)['passed'])

    def test_docker_state_files_and_save_roundtrip(self):
        self.start('sim_images')
        self.run_command('docker run --name a -dit ubuntu bash')
        self.run_command('docker exec a bash -c \'printf "retained\\n" > /tmp/data\'')
        self.run_command('docker stop a; docker start a')
        self.assertEqual(self.run_command('docker exec a cat /tmp/data'), b'retained\n')
        self.run_command('docker commit a saved:v1; docker save -o backup.tar saved:v1; docker rmi saved:v1; docker load -i backup.tar')
        self.run_command('docker run --name b -dit saved:v1 bash')
        self.assertEqual(self.run_command('docker exec b cat /tmp/data'), b'retained\n')
        self.assertFalse(self.shell.fs.exists('/tmp/data'))
        self.run_command('docker run --rm --name disposable hello-world')
        self.assertNotIn('disposable', self.shell.docker.containers)
        self.assertIn('hello-world:latest', self.shell.docker.images)

    def test_no_host_execution_or_network(self):
        with patch('subprocess.Popen', side_effect=AssertionError('host process')), patch('subprocess.run', side_effect=AssertionError('host command')), patch('socket.socket', side_effect=AssertionError('network')):
            self.start('sim_cleanup')
            self.solve(self.mission)
            self.assertTrue(self.engine.rpc('grade', self.mission)['passed'])
            self.start('archive'); self.solve(self.mission)
            self.assertTrue(self.engine.rpc('grade', self.mission)['passed'])

    def test_interactive_eof_editor_job_control_and_container_shell(self):
        m = self.start()
        self.engine.open_terminal(m)
        self.engine.send(b'cat > note.txt\rfirst line\r\x04')
        self.assertEqual(self.shell.fs.read(self.shell.path('note.txt')), b'first line\n')
        self.engine.send(b'nano note.txt\r\x0bchanged\x0f\r\x18')
        self.assertIsNone(self.shell.editor)
        self.assertEqual(self.shell.fs.read(self.shell.path('note.txt')), b'changed\n')
        self.engine.send(b'sleep 300\r\x1a')
        self.assertEqual(self.shell.jobs[1]['state'], 'Stopped')
        self.engine.send(b'bg %1\rfg %1\r\x03')
        self.assertEqual(self.shell.jobs[1]['state'], 'Terminated')
        self.engine.send(b'docker run --name shellbox -it ubuntu bash\r')
        self.assertEqual(len(self.engine.sessions), 1)
        self.engine.send(b'printf inside > /tmp/inside\rexit\r')
        self.assertEqual(len(self.engine.sessions), 0)
        self.assertEqual(self.shell.docker.containers['shellbox']['state'], 'exited')
        self.assertFalse(self.shell.fs.exists('/tmp/inside'))
        self.engine.close()

    def test_printf_repeats_format_and_readonly_copy_rejected(self):
        self.start()
        self.assertEqual(self.run_command("printf '%s\\n' a b c"), b'a\nb\nc\n')
        self.run_command('printf a > a; printf b > b; chmod 400 b')
        self.assertNotEqual(self.shell.execute('cp a b').code, 0)
        self.assertEqual(self.run_command('cat b'), b'b')

    @unittest.skipUnless(os.name == 'posix', 'GNU/bash comparison uses Linux only; simulator itself is cross-platform')
    def test_known_safe_commands_match_real_bash_and_gnu(self):
        # These are fixed test literals, never learner input. Only a temporary
        # directory is used by the reference bash; the application does not run it.
        cases = [
            "printf '%s\\n' alpha 'two words' omega",
            "export VALUE='two words'; printf '%s\\n' \"$VALUE\"; printf '%s\\n' '$VALUE'",
            "printf 'INFO start\\nERROR first\\nerror second\\n' > log; grep -i error log | wc -l",
            "printf first > note; printf second >> note; cat < note",
            "mkdir -p 'some dir/inner'; touch 'some dir/.hidden' 'some dir/a'; ls -1a 'some dir'",
            "printf 'one\\ntwo\\nthree\\n' > text; head -n 2 text; tail -n 1 text",
            "false && echo incorrect; true || echo incorrect; echo $?",
            "mkdir a; touch a/x; cp a/x y; mv y z; rm z; ls -1 a",
            "printf 'tab\\there\\n' > text; cat -A text",
        ]
        for command in cases:
            with self.subTest(command=command), tempfile.TemporaryDirectory() as root:
                self.start(); self.shell.fs.mkdir('/home/learner/diff'); self.shell.cwd = '/home/learner/diff'
                simulated = self.shell.execute(command)
                actual = subprocess.run(['/bin/bash', '--noprofile', '--norc', '-c', command], cwd=root,
                                        env={'PATH': '/usr/bin:/bin', 'LC_ALL': 'C.UTF-8'}, capture_output=True, timeout=5)
                self.assertEqual(simulated.code, actual.returncode)
                self.assertEqual(simulated.out, actual.stdout)
                self.assertEqual(simulated.err, actual.stderr)


if __name__ == '__main__': unittest.main()
