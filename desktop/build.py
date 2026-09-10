"""Run on the target operating system: python build.py."""
from pathlib import Path
import subprocess
import sys

root = Path(__file__).resolve().parent
extra = []
if sys.platform == 'linux':
    cursor_library = root / '.native-libs/usr/lib/x86_64-linux-gnu/libxcb-cursor.so.0'
    if cursor_library.exists():
        extra = ['--add-binary', f'{cursor_library}:.']
subprocess.run([
    sys.executable, '-m', 'PyInstaller', '--noconfirm', '--clean', '--onefile', '--windowed',
    '--name', 'Shellground', '--distpath', str(root / 'dist'), '--workpath', str(root / 'build'),
    '--specpath', str(root), '--paths', str(root), '--add-data', f'{root / "lab"}:lab',
    '--add-data', f'{root / "assets"}:assets', '--collect-all', 'pyte', '--collect-all', 'wcwidth',
    *extra, str(root / 'shellground.py'),
], check=True)
binary = root / 'dist' / ('Shellground.exe' if sys.platform == 'win32' else 'Shellground')
subprocess.run([str(binary), '--self-test'], check=True)
print(f'Built: {binary}')
