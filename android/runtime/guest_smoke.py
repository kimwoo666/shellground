"""Exercise actual guest PTYs, Bash job control and GNU nano, not emulators of commands."""
import base64
import json
import queue
import time


def check_pty(channel):
    def command(argv):
        reply = channel.request('exec', timeout=35, argv=argv)
        if reply['code']:
            raise RuntimeError(base64.b64decode(reply['err']).decode(errors='replace'))
        return base64.b64decode(reply['out']).decode()

    folder = command(['mktemp', '-d', '/home/learner/sg-pty.XXXXXX']).strip()
    terminal = channel.open_terminal(folder)
    channel.send({'action': 'resize', 'session': terminal.sid, 'size': [24, 80]})

    def send(data):
        channel.send({'action': 'input', 'session': terminal.sid,
                      'data': base64.b64encode(data).decode()})

    def until(marker, timeout=30):
        seen = bytearray()
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            try:
                line = terminal.queue.get(timeout=min(1, max(.01, deadline - time.monotonic())))
            except queue.Empty:
                continue
            if line is None:
                raise RuntimeError('Guest PTY ended before ' + repr(marker))
            seen.extend(base64.b64decode(json.loads(line)['output']))
            if marker in seen:
                return seen.decode(errors='replace')[-16000:]
            if len(seen) > 1024 * 1024:
                del seen[:-65536]
        raise TimeoutError('Guest PTY did not show ' + repr(marker) + ': ' + repr(seen[-1500:]))

    try:
        send(b"printf '\nSG_%s\n' READY\r")
        until(b'SG_READY')
        send(b"printf 'status=draft\n' > 'edit me.txt'; cp 'edit me.txt' backup.txt; printf '\nSG_%s\n' FILES\r")
        until(b'SG_FILES')
        send(b"nano 'edit me.txt'\r")
        opened = until(b'GNU nano')
        # Same keystrokes the learner must use, sent to a real kernel PTY.
        send(b'\x0bstatus=ready\x0f')
        until(b'File Name to Write')
        send(b'\r')
        saved = until(b'Wrote')
        send(b'\x18')
        send(b"printf '\nSG_%s\n' EDITED\r")
        until(b'SG_EDITED')
        actual = command(['cat', folder + '/edit me.txt'])
        backup = command(['cat', folder + '/backup.txt'])
        if actual != 'status=ready\n' or backup != 'status=draft\n':
            raise AssertionError('GNU nano save or original preservation failed: ' + repr((actual, backup)))
        send(b"sleep 40\r")
        time.sleep(.5)
        send(b'\x03')
        send(b"printf '\nSG_%s\n' INTERRUPTED\r")
        interrupted = until(b'SG_INTERRUPTED', timeout=8)
        return {'actual_nano': True, 'quoted_relative_paths': True, 'original_preserved': True,
                'ctrl_c_returns_to_bash': True, 'file': actual, 'backup': backup,
                'nano_screen_excerpt': opened[-1500:], 'save_excerpt': saved[-1000:],
                'interrupt_excerpt': interrupted[-700:]}
    finally:
        channel.request('close', session=terminal.sid)
