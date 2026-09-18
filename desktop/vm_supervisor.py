"""Own one QEMU child for exactly the lifetime of the app's stdin pipe.

This entry point deliberately does not import Qt or start threads before fork.
No PID from a file is ever signalled. Disk recovery requires an unlocked lease
and our versioned marker, and never follows links or removes unknown contents.
"""
import argparse
import ctypes
import json
import os
from pathlib import Path
import re
import signal
import stat
import subprocess
import sys
import tempfile
import threading
import uuid

FILES = {'owner.json', 'guard.json', 'guard.json.pending', 'lease', 'practice.qcow2', 'console.log', 'qemu.log'}


def process_identity(pid):
    """Read-only identity, including birth time; never signal a recorded PID."""
    if type(pid) is not int or pid <= 0:
        raise ValueError('Invalid process identity')
    if sys.platform == 'linux':
        try:
            text = (Path('/proc') / str(pid) / 'stat').read_text()
            fields = text[text.rfind(')') + 2:].split()
            if fields[0] == 'Z':
                return None
            return {'pid': pid, 'start': fields[19],
                    'boot': Path('/proc/sys/kernel/random/boot_id').read_text().strip()}
        except (FileNotFoundError, ProcessLookupError):
            return None
    if os.name == 'nt':
        from ctypes import wintypes as w
        kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        kernel.OpenProcess.argtypes = [w.DWORD, w.BOOL, w.DWORD]
        kernel.OpenProcess.restype = w.HANDLE
        kernel.GetProcessTimes.argtypes = [w.HANDLE, *([ctypes.POINTER(w.FILETIME)] * 4)]
        kernel.GetProcessTimes.restype = w.BOOL
        kernel.CloseHandle.argtypes = [w.HANDLE]
        handle = kernel.OpenProcess(0x1000, False, pid)  # QUERY_LIMITED_INFORMATION
        if not handle:
            error = ctypes.get_last_error()
            if error == 87:  # no such process; access denied is NOT proof of death
                return None
            raise ctypes.WinError(error)
        try:
            values = [w.FILETIME() for _ in range(4)]
            if not kernel.GetProcessTimes(handle, *[ctypes.byref(v) for v in values]):
                raise ctypes.WinError(ctypes.get_last_error())
            start = (values[0].dwHighDateTime << 32) | values[0].dwLowDateTime
            return {'pid': pid, 'start': str(start), 'boot': 'windows-filetime'}
        finally:
            kernel.CloseHandle(handle)
    raise OSError('Process identity unsupported on this platform')


def create_session():
    creator = process_identity(os.getpid())
    directory = Path(tempfile.mkdtemp(prefix='shellground-vm-'))
    token = uuid.uuid4().hex
    (directory / 'owner.json').write_text(json.dumps(
        {'schema': 2, 'kind': 'shellground-vm', 'token': token, 'creator': creator}), encoding='utf-8')
    return directory, token


def validate_session(directory, token=None):
    directory = Path(directory)
    info = directory.lstat()
    if not stat.S_ISDIR(info.st_mode) or directory.is_symlink():
        raise ValueError('Session is not a private directory')
    if directory.parent.resolve() != Path(tempfile.gettempdir()).resolve() or not directory.name.startswith('shellground-vm-'):
        raise ValueError('Session is outside the dedicated temporary namespace')
    if hasattr(os, 'getuid') and (info.st_uid != os.getuid() or info.st_mode & 0o077):
        raise ValueError('Session directory is not private to the current user')
    marker = directory / 'owner.json'
    if marker.is_symlink() or not stat.S_ISREG(marker.lstat().st_mode):
        raise ValueError('Invalid session marker')
    data = json.loads(marker.read_text(encoding='utf-8'))
    if data.get('schema') != 2 or data.get('kind') != 'shellground-vm' or not re.fullmatch('[0-9a-f]{32}', data.get('token', '')):
        raise ValueError('Unrecognized session owner')
    if token is not None and token != data['token']:
        raise ValueError('Session token does not match')
    for item in directory.iterdir():
        if item.name not in FILES or item.is_symlink() or not stat.S_ISREG(item.lstat().st_mode):
            raise ValueError('Session contains an unknown file or link')
    return data['token']


class Lease:
    def __init__(self, directory, create=False):
        path = Path(directory) / 'lease'
        self.stream = path.open('a+b' if create else 'r+b')
        try:
            if os.name == 'nt':
                import msvcrt
                if path.stat().st_size == 0:
                    self.stream.write(b'0')
                    self.stream.flush()
                self.stream.seek(0)
                msvcrt.locking(self.stream.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(self.stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BaseException:
            self.stream.close()
            raise

    def close(self):
        self.stream.close()


def remove_session(directory, token, lease):
    """Only known regular files in this private session; never recursive."""
    validate_session(directory, token)
    for item in directory.iterdir():
        if item.name != 'lease':
            item.unlink(missing_ok=True)
    # Windows cannot unlink an open lease. No future VM reuses this UUID/path.
    lease.close()
    (directory / 'lease').unlink(missing_ok=True)
    try:
        directory.rmdir()
    except FileNotFoundError:
        pass


def reap_abandoned_sessions():
    removed = []
    for directory in Path(tempfile.gettempdir()).glob('shellground-vm-*'):
        lease = None
        try:
            token = validate_session(directory)
            guard_file = directory / 'guard.json'
            if guard_file.exists():
                guard = json.loads(guard_file.read_text(encoding='utf-8'))
                if guard.get('schema') != 1 or guard.get('token') != token:
                    continue
                lease = Lease(directory)
            else:
                # A crash during qemu-img creation precedes the supervisor.
                # Only reclaim it if the original creator is demonstrably gone;
                # inaccessible or legacy identities are left untouched.
                owner = json.loads((directory / 'owner.json').read_text(encoding='utf-8'))
                creator = owner.get('creator')
                if not isinstance(creator, dict) or set(creator) != {'pid', 'start', 'boot'}:
                    continue
                if process_identity(creator['pid']) == creator:
                    continue
                lease = Lease(directory, create=True)
            # The guard writes its marker only AFTER acquiring this lease.
            # Thus a still-starting app is never mistaken for abandoned work.
            remove_session(directory, token, lease)
            removed.append(str(directory))
        except (OSError, ValueError, TypeError):
            # Live, legacy, incomplete, or unrecognized directories are left
            # alone. A cleanup problem must never cause broad deletion.
            pass
        finally:
            if lease:
                lease.close()
    return removed


def child_death_options():
    if sys.platform != 'linux':
        return {}
    libc = ctypes.CDLL(None, use_errno=True)
    libc.prctl.argtypes = [ctypes.c_int, ctypes.c_ulong, ctypes.c_ulong, ctypes.c_ulong, ctypes.c_ulong]
    libc.prctl.restype = ctypes.c_int
    parent = os.getpid()

    def protect_child():
        # Called in a fresh, single-threaded supervisor, never the Qt app.
        if libc.prctl(1, signal.SIGKILL, 0, 0, 0) != 0 or os.getppid() != parent:
            os._exit(125)
    return {'preexec_fn': protect_child}


def windows_kill_job():
    """Put this guard and future children in a kill-on-close Windows job.

    Keep the non-inheritable handle until OS process teardown. Failure is
    fatal before starting QEMU; Windows behavior still needs real-host QA.
    """
    if os.name != 'nt':
        return None
    from windows_vm import create_guard_job
    return create_guard_job()


def supervise(directory, token, command, env):
    from vm_resources import lower_priority, vm_process_options
    validate_session(directory, token)
    lease = Lease(directory, create=True)
    process = None
    stopped = threading.Event()
    # A parent close request must run cleanup, not interrupt it half-way.
    signal.signal(signal.SIGTERM, lambda *_: stopped.set())
    signal.signal(signal.SIGINT, lambda *_: stopped.set())
    try:
        os.fstat(0)  # fail closed if no lifetime pipe was supplied
        job = windows_kill_job()  # intentionally held until process teardown
        with (directory / 'qemu.log').open('ab') as log:
            process = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=log, stderr=log,
                                       env=env, **vm_process_options(), **child_death_options())
            lower_priority(process)
            pending = directory / 'guard.json.pending'
            pending.write_text(json.dumps({'schema': 1, 'token': token,
                'guard_pid': os.getpid(), 'child_pid': process.pid}), encoding='utf-8')
            pending.replace(directory / 'guard.json')

            def watch_parent():
                try:
                    while os.read(0, 1):
                        pass
                except OSError:
                    pass
                stopped.set()
            threading.Thread(target=watch_parent, daemon=True).start()
            while not stopped.wait(.25):
                if process.poll() is not None:
                    break
        if os.name == 'nt' and process.poll() is not None:
            from windows_vm import forward_qemu_error
            forward_qemu_error(directory / 'qemu.log')
        return 0
    finally:
        if process is not None and process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=3)
        try:
            remove_session(directory, token, lease)
        finally:
            lease.close()


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('--session', type=Path, required=True)
    parser.add_argument('--token', required=True)
    parser.add_argument('--library-dir')
    parser.add_argument('--module-dir')
    parser.add_argument('command', nargs=argparse.REMAINDER)
    args = parser.parse_args(argv)
    command = args.command[1:] if args.command[:1] == ['--'] else args.command
    if not command:
        parser.error('Missing owned VM command')
    env = dict(os.environ)
    if args.library_dir:
        env['LD_LIBRARY_PATH'] = args.library_dir
    if args.module_dir:
        env['QEMU_MODULE_DIR'] = args.module_dir
    try:
        return supervise(args.session, args.token, command, env)
    except Exception as exc:
        os.write(2, ('Shellground VM supervisor: ' + str(exc) + '\n').encode(errors='replace'))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
