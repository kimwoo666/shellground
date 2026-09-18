"""Explicit Linux crash tests using owned disposable VMs, never learner progress."""
import json
import os
from pathlib import Path
import subprocess
import sys
import threading
import time


def crash_probe(during_startup=False):
    from real_vm import RealEngine, runtime_info
    engine = RealEngine()
    try:
        root, spec = runtime_info()
        base = root / spec['image']
        original = base.stat()
        if during_startup:
            errors = []
            def boot():
                try:
                    engine.boot()
                except Exception as exc:
                    errors.append(str(exc))
            threading.Thread(target=boot, daemon=True).start()
            deadline = time.monotonic() + 30
            while time.monotonic() < deadline:
                if errors:
                    raise RuntimeError(errors[0])
                directory = engine.session_dir
                if directory and (directory / 'guard.json').exists():
                    try:
                        json.loads((directory / 'guard.json').read_text())
                        break
                    except ValueError:
                        pass
                time.sleep(.02)
            else:
                raise RuntimeError('VM startup probe timed out')
        else:
            engine.boot()
        state = json.loads((engine.session_dir / 'guard.json').read_text())
        print(json.dumps(dict(state, directory=str(engine.session_dir), base=str(base),
            base_size=original.st_size, base_mtime=original.st_mtime_ns,
            during_startup=during_startup, guest_ready=bool(engine.guest_status))), flush=True)
        # Deliberately skip all Python/Qt finalizers. The supervisor must react
        # to the kernel closing the app's pipe, not RealEngine.close().
        os._exit(86)
    finally:
        # Reached on a diagnostic failure, never the intended abrupt exit.
        engine.cancel_pending()
        engine.close()


def process_running(pid):
    try:
        data = (Path('/proc') / str(pid) / 'stat').read_text()
        return data[data.rfind(')') + 2:].split()[0] != 'Z'
    except (FileNotFoundError, ProcessLookupError):
        return False


def verify_crash_cleanup():
    if sys.platform != 'linux':
        raise RuntimeError('This crash diagnostic is currently verified only on Linux')
    launcher = [sys.executable] if getattr(sys, 'frozen', False) else [sys.executable, str(Path(__file__).with_name('shellground.py'))]
    cases = []
    for during_startup in (True, False):
        result = subprocess.run(launcher + ['--internal-vm-crash-probe'] + (['--during-startup'] if during_startup else []),
            env=dict(os.environ, PYINSTALLER_RESET_ENVIRONMENT='1'), capture_output=True,
            text=True, encoding='utf-8', timeout=150)
        if result.returncode != 86:
            raise RuntimeError('Crash probe did not reach its deliberate exit: ' + result.stderr[-2000:])
        state = json.loads(result.stdout.splitlines()[-1])
        started = time.monotonic()
        deadline = started + 10
        while (process_running(state['child_pid']) or process_running(state['guard_pid']) or Path(state['directory']).exists()):
            if time.monotonic() >= deadline:
                raise RuntimeError('Owned VM or temporary disk remained after app crash: ' + json.dumps(state))
            time.sleep(.05)
        current = Path(state['base']).stat()
        if (current.st_size, current.st_mtime_ns) != (state['base_size'], state['base_mtime']):
            raise RuntimeError('Immutable base changed during crash diagnostic')
        if not during_startup and not state['guest_ready']:
            raise RuntimeError('Post-startup probe did not boot an actual guest')
        cases.append({'during_startup': during_startup, 'guest_ready': state['guest_ready'],
                      'owned_vm_stopped': True, 'temporary_disk_removed': True, 'base_unchanged': True,
                      'observed_cleanup_seconds_after_probe_exit': round(time.monotonic() - started, 2)})
    print(json.dumps({'actual_linux_crash_cleanup': cases}))
    return cases
