"""Build setup wrappers only. Never rebuild or replay the learning application."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
BUILD = ROOT / 'desktop/.installer-build'
TOOLS = BUILD / 'tools'
OUTPUT = ROOT / 'releases'


def manifest():
    pc = json.loads((OUTPUT / 'pc-build.json').read_text())
    value = dict(version='4.7.4', base_url='https://github.com/kimwoo666/shellground/releases/download/v4.7.4-preview/',
        linux=pc['linux'], windows=pc['windows'], disk=pc['shared_disk'])
    (HERE / 'manifest.json').write_text(json.dumps(value, indent=2) + '\n')


def licenses():
    folder = HERE / 'licenses'; folder.mkdir(exist_ok=True)
    for package in ('python3-tk', 'libtk8.6', 'libtcl8.6', 'tk8.6-blt2.5', 'nsis'):
        source = TOOLS / 'usr/share/doc' / package / 'copyright'
        if source.is_file(): shutil.copyfile(source, folder / (package + '.txt'))
    shutil.copyfile('/usr/share/doc/python3.12/copyright', folder / 'CPython.txt')
    for source in (BUILD / 'python').glob('pyinstaller-*.dist-info/licenses/COPYING.txt'):
        shutil.copyfile(source, folder / 'PyInstaller.txt')


def windows():
    manifest()
    licenses()
    stage = BUILD / 'windows-source'; stage.mkdir(exist_ok=True)
    for name in ('windows_setup.ps1', 'windows_download.cs', 'windows_setup.nsi', 'manifest.json'):
        (stage / name).write_text((HERE / name).read_text(), encoding='utf-8-sig')
    shutil.copyfile(HERE / 'licenses/nsis.txt', stage / 'Installer-Licenses.txt')
    env = dict(os.environ, NSISDIR=str(TOOLS / 'usr/share/nsis'))
    output = OUTPUT / 'Shellground-Windows-Setup.exe'
    subprocess.run([str(TOOLS / 'usr/bin/makensis'), '-V2', '-DOUTPUT=' + str(output), 'windows_setup.nsi'], cwd=stage, env=env, check=True)
    print('Windows installer built:', output, flush=True)


def linux():
    manifest()
    licenses()
    environment = dict(os.environ)
    environment['PYTHONPATH'] = os.pathsep.join(map(str, [BUILD/'python', TOOLS/'usr/lib/python3.12', TOOLS/'usr/lib/python3.12/lib-dynload']))
    environment['LD_LIBRARY_PATH'] = os.pathsep.join(map(str, [TOOLS/'usr/lib/x86_64-linux-gnu', TOOLS/'usr/lib']))
    environment['TCL_LIBRARY'] = str(TOOLS/'usr/share/tcltk/tcl8.6')
    environment['TK_LIBRARY'] = str(TOOLS/'usr/share/tcltk/tk8.6')
    environment['PYINSTALLER_CONFIG_DIR'] = str(BUILD/'pyinstaller-cache')
    subprocess.run([sys.executable, '-m', 'PyInstaller', '--noconfirm', '--clean', '--onefile',
        '--name', 'Shellground-Linux-Setup.run', '--distpath', str(OUTPUT), '--workpath', str(BUILD/'linux'),
        '--specpath', str(BUILD), '--add-data', str(HERE/'manifest.json')+':.',
        '--add-data', str(HERE/'shellground.svg')+':.', '--add-data', str(HERE/'licenses')+':licenses',
        str(HERE/'linux_setup.py')], env=environment, check=True)


if __name__ == '__main__':
    if sys.argv[1:] == ['windows']: windows()
    elif sys.argv[1:] == ['linux']: linux()
    else: manifest()
