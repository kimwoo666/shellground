"""Stage Conda teaching data and the existing real-guest adapters for Android.

No VM is started and no runtime readiness is inferred from a successful export.
The learner APK uses these same sources, not a new Conda implementation.
"""
from pathlib import Path
import sys

from conda_teaching.engine import SHELL_INIT
from conda_teaching.mobile_course import export as export_course


def export(destination):
    target = Path(destination)
    root = Path(__file__).resolve().parent
    export_course(target / 'conda-course.json')
    scripts = target / 'conda-guest'
    scripts.mkdir(parents=True, exist_ok=True)
    sources = {
        'conda_runtime.py': root / 'conda_teaching/guest_runtime.py',
        'shell_snapshot.py': root / 'guest/shell_snapshot.py',
        'guest_files.py': root / 'conda_teaching/guest_files.py',
    }
    for name, source in sources.items():
        data = source.read_bytes()
        compile(data, name, 'exec')
        (scripts / name).write_bytes(data)
    (scripts / 'bashrc').write_text(
        (root / 'guest/bashrc').read_text(encoding='utf-8') + SHELL_INIT,
        encoding='utf-8')


if __name__ == '__main__':
    export(sys.argv[1])
