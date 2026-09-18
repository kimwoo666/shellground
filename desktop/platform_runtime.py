"""Never select a Linux executable bundle merely because the host is not Windows."""
import platform
import sys


def runtime_tag(system=None,machine=None):
    system=system or sys.platform
    machine=(machine or platform.machine()).lower()
    arch={'amd64':'x86_64','aarch64':'arm64'}.get(machine,machine)
    name={'win32':'windows','darwin':'macos','linux':'linux'}.get(system,system)
    return name+'-'+arch
