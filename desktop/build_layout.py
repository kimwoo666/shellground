"""Target-native executable and external VM resource placement.

A macOS .app must remain self-contained when moved to Applications. VM disk
images belong in Resources, not beside the outer app or in the code directory.
"""
from pathlib import Path
import sys


def executable_path(destination, system=None):
    system = system or sys.platform
    destination = Path(destination)
    if system == 'darwin':
        return destination / 'Shellground.app/Contents/MacOS/Shellground'
    if system == 'win32':
        return destination / 'Shellground/Shellground.exe'
    return destination / 'Shellground'


def runtime_directory(executable, system=None):
    system = system or sys.platform
    directory = Path(executable).parent
    if system == 'darwin' and directory.name == 'MacOS' and directory.parent.name == 'Contents':
        return directory.parent / 'Resources/runtime'
    return directory / 'runtime'


def bundle_options(system=None):
    # A Windows folder already needs the external VM disk. Avoid repeatedly
    # unpacking scientific/Qt libraries for every worker and VM supervisor.
    # Onedir also gives the parent a direct handle to the supervisor, without
    # an intermediate onefile extraction/cleanup process. Linux stays onefile.
    system = system or sys.platform
    options = ['--onedir' if system in ('darwin', 'win32') else '--onefile', '--windowed']
    if system == 'win32':
        # The frozen interpreter ignores the user's PYTHONUTF8 environment.
        # This makes UTF-8 lesson/source files independent of ANSI code page.
        options += ['--python-option', 'X utf8']
    return options
