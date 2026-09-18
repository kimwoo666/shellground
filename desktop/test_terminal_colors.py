"""Real Bash/coreutils colour checks in a temporary PTY, without a VM."""
import os
from pathlib import Path
import select
import shlex
import shutil
import subprocess
import tempfile
import time
import unittest


@unittest.skipUnless(os.name == 'posix' and shutil.which('bash') and shutil.which('dircolors'),
                     'Linux Bash/coreutils required')
class ShellColorsTests(unittest.TestCase):
    def test_prompt_listing_search_and_plain_redirects(self):
        import pty
        with tempfile.TemporaryDirectory(prefix='shellground-color-') as directory:
            root = Path(directory)
            (root / 'folder').mkdir()
            (root / 'run.sh').write_text('#!/bin/sh\n')
            (root / 'run.sh').chmod(0o755)
            (root / 'message.txt').write_text('hello colour\n')
            master, slave = pty.openpty()
            process = subprocess.Popen(['/bin/bash', '--noprofile', '--norc', '-i'],
                stdin=slave, stdout=slave, stderr=slave, cwd=root, start_new_session=True,
                env=dict(os.environ, HOME=directory, TERM='xterm', PS1='READY> ',
                         SG_PRESEEDED='0', SG_SESSION='color-test', HISTFILE='/dev/null',
                         PROMPT_COMMAND=''))
            os.close(slave)
            def receive(marker):
                result = b''
                deadline = time.monotonic() + 5
                while marker not in result and time.monotonic() < deadline:
                    if select.select([master], [], [], .2)[0]:
                        try:
                            result += os.read(master, 65536)
                        except OSError:
                            break
                self.assertIn(marker, result)
                return result
            try:
                receive(b'READY> ')
                rc = Path(__file__).with_name('guest') / 'bashrc'
                # Disable only the VM-only grading hook, not its colour setup.
                os.write(master, f'source {shlex.quote(str(rc))}; unset PROMPT_COMMAND\n'.encode())
                prompt = receive(b'\x1b[0m')
                self.assertIn(b'\x1b[01;32m', prompt)
                os.write(master, b"ls -1; grep colour message.txt; ls -1 > listing.txt; grep colour message.txt > match.txt; printf '\\nCHECK_%s\\n' DONE\n")
                output = receive(b'CHECK_DONE')
                self.assertIn(b'\x1b[01;34mfolder', output)
                self.assertIn(b'\x1b[01;32mrun.sh', output)
                self.assertIn(b'\x1b[01;31m', output)
                self.assertNotIn(b'\x1b', (root / 'listing.txt').read_bytes())
                self.assertEqual((root / 'match.txt').read_bytes(), b'hello colour\n')
            finally:
                process.terminate()
                try:
                    process.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=3)
                os.close(master)


class TerminalColorsTests(unittest.TestCase):
    def test_vt_preserves_green_blue_red_and_normal_text(self):
        from native_app import create_application
        from terminal_widget import TerminalWidget
        app, _, mono = create_application()
        terminal = TerminalWidget(mono)
        try:
            terminal.feed(b'\x1b[01;32mG\x1b[01;34mB\x1b[01;31mR\x1b[0mN')
            cells = terminal.screen.buffer[0]
            self.assertEqual([cells[i].fg for i in range(4)], ['green', 'blue', 'red', 'default'])
            self.assertTrue(cells[0].bold)
            self.assertFalse(cells[3].bold)
        finally:
            terminal.deleteLater()
            app.processEvents()


if __name__ == '__main__':
    unittest.main()
