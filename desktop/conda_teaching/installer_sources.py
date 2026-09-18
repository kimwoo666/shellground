"""Official, pinned installers for the app's Linux guests, not the host OS.

Checksums verified against https://repo.anaconda.com/miniconda/ on 2026-09-17.
This is provenance only; an ARM build must pass its own execution/course gate.
"""
import platform

INSTALLERS = {
    'x86_64': {
        'name': 'Miniconda3-py312_26.7.1-1-Linux-x86_64.sh',
        'sha256': 'b27f60ab63e77eeab50a5417c989120f767e863df32400190d4c7262369f8695',
        'subdir': 'linux-64',
    },
    'aarch64': {
        'name': 'Miniconda3-py312_26.7.1-1-Linux-aarch64.sh',
        'sha256': 'f6d64a1565e713429683720f59dd6661f5131c2f959a4830438eb1969cde23f7',
        'subdir': 'linux-aarch64',
    },
}


def installer_for(machine=None):
    arch = (machine or platform.machine()).lower()
    arch = {'arm64': 'aarch64', 'amd64': 'x86_64'}.get(arch, arch)
    if arch not in INSTALLERS:
        raise ValueError('No verified Conda installer for guest architecture: ' + arch)
    spec = dict(INSTALLERS[arch])
    spec.update(architecture=arch, url='https://repo.anaconda.com/miniconda/' + spec['name'])
    return spec
