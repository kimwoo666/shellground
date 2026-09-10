"""Linux-side PTY transport; the host needs only cross-platform subprocess pipes."""
import base64
import fcntl
import json
import os
from pathlib import Path
import pty
import select
import signal
import struct
import sys
import termios


def main():
    os.chdir(sys.argv[1])
    pid, master = pty.fork()
    if pid == 0:
        os.environ.update(TERM="xterm", LANG="C.UTF-8", LC_ALL="C.UTF-8",
                          PS1=r"\[\e[32m\]\u@lab:\w\$ \[\e[0m\]",
                          HISTFILE="/tmp/shellground_history", HOME="/home/learner")
        os.execvp("bash", ["bash", "--noprofile", "--norc", "-i"])
    Path("/tmp/shellground.pid").write_text(str(pid))
    def resize(rows, cols):
        fcntl.ioctl(master, termios.TIOCSWINSZ, struct.pack("HHHH", rows, cols, 0, 0))
    resize(24, 100)
    buffer = b""
    try:
        while True:
            ready, _, _ = select.select([master, sys.stdin.fileno()], [], [])
            if master in ready:
                try:
                    data = os.read(master, 65536)
                except OSError:
                    break
                if not data:
                    break
                print(json.dumps({"output": base64.b64encode(data).decode()}), flush=True)
            if sys.stdin.fileno() in ready:
                data = os.read(sys.stdin.fileno(), 65536)
                if not data:
                    break
                buffer += data
                while b"\n" in buffer:
                    line, buffer = buffer.split(b"\n", 1)
                    message = json.loads(line)
                    if "input" in message:
                        os.write(master, base64.b64decode(message["input"]))
                    if "resize" in message:
                        rows, cols = message["resize"]
                        resize(max(2, min(200, rows)), max(10, min(500, cols)))
    finally:
        os.close(master)
        try:
            os.kill(pid, signal.SIGHUP)
            os.waitpid(pid, 0)
        except (ProcessLookupError, ChildProcessError):
            pass


if __name__ == "__main__":
    main()
