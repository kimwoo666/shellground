"""Flatten a powered-off development image into the application's runtime pack.

QEMU's image locking refuses conversion while a writer still has the source
open. No --force-share is used. The manifest is published only after success.
"""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import argparse
import re


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--replace', action='store_true', help='Preserve the previous generated base in .vm-build/pack-backups, then replace it atomically')
    args = parser.parse_args()
    root = Path(__file__).resolve().parent
    runtime = root / '.vm-runtime/linux-x86_64'
    env = dict(os.environ, LD_LIBRARY_PATH=str(runtime / 'usr/lib/x86_64-linux-gnu'),
               QEMU_MODULE_DIR=str(runtime / 'usr/lib/x86_64-linux-gnu/qemu'))
    destination = runtime / 'base.qcow2'
    if destination.exists() and not args.replace:
        raise RuntimeError('Existing base image is preserved. Choose a new pack before replacing it.')
    if destination.exists():
        previous = json.loads((runtime / 'runtime.json').read_text())
        digest = previous.get('image_sha256', '')
        if previous.get('image') != 'base.qcow2' or not re.fullmatch('[0-9a-f]{64}', digest):
            raise RuntimeError('Previous generated pack identity could not be verified')
        backups = root / '.vm-build/pack-backups'
        backups.mkdir(exist_ok=True)
        backup = backups / ('base-' + digest + '.qcow2')
        if not backup.exists():
            os.link(destination, backup)
    temporary = runtime / 'base.qcow2.partial'
    if temporary.exists():
        raise RuntimeError('Previous partial conversion exists; inspect it before retrying.')
    if hasattr(os, 'nice'):
        os.nice(10)
    subprocess.run([str(runtime / 'usr/bin/qemu-img'), 'convert', '-p', '-O', 'qcow2',
                    str(root / '.vm-build/provisioning.qcow2'), str(temporary)], env=env, check=True)
    subprocess.run([str(runtime / 'usr/bin/qemu-img'), 'check', str(temporary)], env=env, check=True)
    with temporary.open('rb') as stream:
        digest = hashlib.file_digest(stream, 'sha256').hexdigest()
    temporary.replace(destination)
    spec = {'protocol': 1, 'provisioned': True, 'qemu': 'usr/bin/qemu-system-x86_64',
            'qemu_img': 'usr/bin/qemu-img', 'image': 'base.qcow2', 'image_sha256': digest,
            'guest': 'Ubuntu 22.04 / ROS 2 Humble', 'development_pack': True}
    pending = runtime / 'runtime.json.partial'
    pending.write_text(json.dumps(spec, indent=2) + '\n')
    pending.replace(runtime / 'runtime.json')
    print('Development runtime pack ready:', destination, destination.stat().st_size, 'bytes')


if __name__ == '__main__':
    main()
