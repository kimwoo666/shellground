"""Flatten the verified developer guest into an Android-private runtime pack.

This is a development artifact, not a release/licensing approval. Never modify
the source VM, use qemu-img's normal image locks, and publish only complete packs.
"""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import tempfile

from build_guest import BUILD, RUNTIME, SOURCES, build_environment, sha256, source_path, verify_sources


def validate_report(report):
    results = report.get('results', {})
    if report.get('passed') is not True or report.get('sources') != SOURCES:
        raise ValueError('No matching successful ARM64 guest validation')
    pty = results.get('pty', {})
    if not all(pty.get(key) is True for key in ('actual_nano', 'quoted_relative_paths',
            'original_preserved', 'ctrl_c_returns_to_bash')):
        raise ValueError('Actual PTY/nano proof is missing')
    if results.get('docker') != 'SG_REAL_ARM_DOCKER' or not results.get('ros'):
        raise ValueError('Actual Docker/ROS proof is missing')


def export(destination):
    if destination.exists() or destination.is_symlink():
        raise ValueError('Preserve existing pack; choose a new destination')
    verify_sources()
    report = json.loads((BUILD / 'validation.json').read_text())
    validate_report(report)
    destination.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix='sg-arm-pack-', dir=destination.parent))
    try:
        image = staging / 'base.qcow2'
        # No -U: a running VM holding the source disk must make export fail.
        subprocess.run([str(RUNTIME / 'usr/bin/qemu-img'), 'convert', '-m', '2', '-c',
            '-O', 'qcow2', str(BUILD / 'provisioning.qcow2'), str(image)],
            env=build_environment(), check=True)
        info = json.loads(subprocess.check_output([str(RUNTIME / 'usr/bin/qemu-img'),
            'info', '--output=json', str(image)], env=build_environment(), text=True))
        if info.get('backing-filename') or info.get('format') != 'qcow2':
            raise ValueError('Pack must be a standalone qcow2 image')
        for key, name in [('kernel', 'kernel'), ('initrd', 'initrd')]:
            shutil.copyfile(source_path(key), staging / name)
        manifest = {'schema': 1, 'id': 'shellground-ubuntu-arm64-dev-v1',
            'guest_arch': 'aarch64', 'development_only': True,
            'scope': 'Linux Docker ROS runtime; Conda not included; device verification separate',
            'files': {name: {'size': (staging / name).stat().st_size,
                             'sha256': sha256(staging / name)}
                      for name in ('base.qcow2', 'kernel', 'initrd')},
            'developer_guest_validation': report}
        (staging / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
        staging.rename(destination)
        print(json.dumps({'pack': str(destination), 'files': manifest['files']}, indent=2), flush=True)
    except BaseException:
        # Preserve partial artifacts for diagnosis, don't recursively delete a broad path.
        print('Unpublished staging directory retained: ' + str(staging), flush=True)
        raise


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--destination', type=Path, default=BUILD / 'android-pack-v1')
    export(parser.parse_args().destination.resolve())
