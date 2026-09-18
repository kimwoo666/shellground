"""Explicit full reruns versus small checks of a newly built artifact."""
import sys


def guest_pip_wheel_required(host_system, conda=False):
    """The pinned wheel runs in the Linux guest, even on a Windows host."""
    return conda or host_system == 'linux'


def verification_commands(binary, destination, runtime, python, *, conda=False, notebook=False, full=False, system=None, build_only=False):
    if build_only:
        if full: raise ValueError('build-only and full verification are mutually exclusive')
        return []
    binary, destination, runtime = str(binary), str(destination), str(runtime)
    commands = [[binary, '--self-test-release', '--report', destination + '/verification/bundle-smoke.json'],
                [binary, '--self-test-study-ui', '--capture-dir', destination + '/verification']]
    if (system or sys.platform) == 'win32':
        commands.insert(0, [binary, '--self-test-windows-pipes', '--report', destination + '/verification/windows-pipes.json'])
    if conda: commands.append([binary, '--self-test-conda'])  # One activation/export/package transport check.
    if notebook:
        commands.append([binary, '--self-test-notebook-package', '--runtime', runtime,
                         '--report', destination + '/verification/notebook-package.json'])
    if full:
        commands += [[binary, '--self-test'], [binary, '--self-test-python'],
                     [python, '-m', 'unittest', 'test_python_packaged', '-v']]
        if conda:
            commands += [[binary, '--self-test-real'], [binary, '--self-test-conda-setup', '--capture-dir', destination + '/verification'],
                         [binary, '--self-test-pip', '--capture-dir', destination + '/verification']]
        if notebook:
            commands += [[binary, '--self-test-ros-course', '--runtime', runtime, '--report', destination + '/verification/ros-grading.json',
                          '--keys', 'ros_params', 'ros_rate', 'ros_play', 'ros_service'],
                         [binary, '--self-test-notebook', '--runtime', runtime, '--report', destination + '/verification/notebook-course.json'],
                         [binary, '--self-test-notebook-ui', '--runtime', runtime, '--report', destination + '/verification/notebook-ui.json',
                          '--capture-dir', destination + '/verification']]
    return commands
