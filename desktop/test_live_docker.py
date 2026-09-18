"""Opt-in against the isolated image builder. Never uses the host Docker CLI."""
import base64
import os
import shlex
import unittest
import test_live_extensions as helpers
from missions import make_mission
from checkpoints import make_checkpoint


@unittest.skipUnless(os.environ.get('SHELLGROUND_LIVE_GUEST') == '1', 'Dedicated guest required')
class LiveDockerTests(unittest.TestCase):
    setUpClass = classmethod(helpers.LiveExtensionTests.setUpClass.__func__)
    tearDownClass = classmethod(helpers.LiveExtensionTests.tearDownClass.__func__)
    command = helpers.LiveExtensionTests.command
    grade = helpers.LiveExtensionTests.grade
    assert_passes_eventually = helpers.LiveExtensionTests.assert_passes_eventually
    send = helpers.LiveExtensionTests.send
    wait_prompt = helpers.LiveExtensionTests.wait_prompt
    solve_in_terminal = helpers.LiveExtensionTests.solve_in_terminal

    def prepare(self, key, practice=0):
        self.mission = make_checkpoint(75, 6789) if key == 'review' else make_mission('docker_' + key, 6789, practice)
        self.channel.request('prepare', timeout=90, mission=self.mission.payload())
        self.terminal = self.channel.open_terminal(self.mission.start)
        return self.mission

    def test_all_fifteen_variants_actual_docker(self):
        for key in ('bind', 'volume', 'network', 'build', 'diagnose'):
            for variant in range(3):
                with self.subTest(key=key, variant=variant):
                    m = self.prepare(key, variant)
                    self.assertFalse(self.grade()['passed'])
                    self.command(m.solution)
                    self.assert_passes_eventually()
                    print(f'\nVERIFIED Docker {key}/{variant}', flush=True)

    def test_review_typed_into_pty_and_repair_after_failed_grade(self):
        m = self.prepare('review')
        self.assertFalse(self.grade()['passed'])
        self.solve_in_terminal(m.solution)
        self.assert_passes_eventually()
        self.command('printf wrong > keep.txt')
        self.assertFalse(self.grade()['passed'])
        self.command("printf 'unrelated document\\n' > keep.txt")
        self.assert_passes_eventually()

    def test_bind_alternative_v_syntax_and_wrong_rw(self):
        m = self.prepare('bind')
        name = 'sgd6789-worker'
        image = m.review['containers'][0]['image']
        cmd = f'docker run -d --name {name} -u 1100:1100 -v ' + shlex.quote(m.start + '/input data:/input:rw') + ' -v ' + shlex.quote(m.start + '/output:/output:rw') + f' {image} sleep 3600\ndocker exec {name} cp /input/message.txt /output/result.txt'
        self.command(cmd)
        self.assertFalse(self.grade()['passed'])
        self.command(f'docker rm -f {name}\n' + cmd.replace(':/input:rw', ':/input:ro'))
        self.assert_passes_eventually()
        # A fabricated output file cannot substitute for a writable mount.
        self.command(f'docker rm -f {name}\n' + cmd.splitlines()[0].replace(':/input:rw', ':/input:ro').replace(':/output:rw', ':/output:ro'))
        self.assertFalse(self.grade()['passed'])

    def test_recreated_container_is_not_network_repair(self):
        m = self.prepare('network', 1)
        self.command(m.solution)
        self.assert_passes_eventually()
        image = m.review['containers'][0]['image']
        self.command(f'docker rm -f sgd6789-worker\ndocker run -d --name sgd6789-worker --network sgd6789-net {image} sleep 3600')
        self.assertFalse(self.grade()['passed'])

    def test_preserved_resources_and_reset_cleanup(self):
        m = self.prepare('volume', 2)
        self.command(m.solution)
        self.assert_passes_eventually()
        self.command('docker exec -u 0 sgd6789-worker sh -c "echo corrupt > /data/note.txt"')
        self.assertFalse(self.grade()['passed'])
        self.command('docker exec -u 0 sgd6789-worker sh -c "printf \'preserved 6789\\n\' > /data/note.txt"')
        self.assert_passes_eventually()
        self.command('docker network disconnect sgd6789-keep-net sgd6789-keep')
        self.assertFalse(self.grade()['passed'])
        reset = make_mission('navigate', 1234)
        self.channel.request('prepare', timeout=60, mission=reset.payload())
        result = self.channel.request('exec', argv=['bash', '-c', 'docker ps -a --format "{{.Names}}"; docker volume ls -q; docker network ls --format "{{.Name}}"'])
        self.assertEqual(result['code'], 0)
        self.assertNotIn('sgd6789-', base64.b64decode(result['out']).decode())

    def test_fake_build_report_is_insufficient_and_probes_are_cleaned(self):
        m = self.prepare('build')
        self.command("printf 'build 6789\\n' > build-result.txt")
        self.assertFalse(self.grade()['passed'])
        self.command(m.solution)
        self.assert_passes_eventually()
        self.assertNotIn('shellground-probe-', self.command('docker ps -a --format "{{.Names}}"'))

    def test_equivalent_named_user_and_wrong_primary_group(self):
        m = self.prepare('build')
        self.command(m.solution)
        # Same numeric credentials, different Dockerfile USER spelling.
        self.command("sed -i '/USER 1100:1100/i RUN addgroup -g 1100 appgrp && adduser -D -u 1100 -G appgrp appuser' app/Dockerfile\n"
                     "sed -i 's/USER 1100:1100/USER appuser/' app/Dockerfile\n"
                     'docker build --network=none -t training/report6789:v1 app')
        self.assert_passes_eventually()
        self.command("sed -i 's/USER appuser/USER 1100:0/' app/Dockerfile\n"
                     'docker build --network=none -t training/report6789:v1 app')
        self.assertFalse(self.grade()['passed'])

    def test_real_shell_colors_via_app_configuration(self):
        from real_vm import RealEngine
        engine = RealEngine()
        engine.channel = self.channel
        engine.configure_shell()
        self.prepare('bind')
        output = self.wait_prompt()
        self.assertIn(b'\x1b[01;32m', output)
        self.send('ls -1; ls -1 > names.txt\r')
        output += self.wait_prompt()
        self.assertIn(b'\x1b[01;34m', output)
        self.assertNotIn('\x1b', self.command('cat names.txt'))
        from native_app import create_application
        from terminal_widget import TerminalWidget
        app, _, mono = create_application()
        terminal = TerminalWidget(mono)
        terminal.resize(1000, 340)
        terminal.show()
        app.processEvents()
        terminal.feed(output)
        terminal.grab().save('/tmp/shellground-real-terminal-colors.png')
        terminal.close()
        terminal.deleteLater()
        app.processEvents()


if __name__ == '__main__': unittest.main()
