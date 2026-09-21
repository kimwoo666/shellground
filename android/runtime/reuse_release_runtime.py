"""Recover unchanged runtime bytes from a pinned, signed previous delivery.

UI/course updates do not need another native QEMU or guest-image build. This
reads only known runtime members; it never imports old course or app code.
"""
import argparse
import hashlib
import io
import json
from pathlib import Path
import shutil
import zipfile

ROOT=Path(__file__).resolve().parents[2]
BASELINE_SHA='72a9e30b3c9b5f49e59b15565f7e6d4dfd78480ab8e0c6fe1433f56ac0ba23b4'


def restore(apk):
    with apk.open('rb') as source:
        if hashlib.file_digest(source,'sha256').hexdigest()!=BASELINE_SHA:
            raise ValueError('Previous runtime APK checksum mismatch')
    generated=ROOT/'android/app/build/generated'
    with zipfile.ZipFile(apk) as archive:
        for member in archive.infolist():
            if member.filename.startswith('assets/training-pack/'):
                relative=Path(member.filename).relative_to('assets')
                target=generated/'realAssets'/relative
            elif member.filename in ('lib/arm64-v8a/libshellground_qemu.so','lib/x86_64/libshellground_qemu.so'):
                target=generated/'realJniLibs'/Path(member.filename).relative_to('lib')
            else:continue
            if '..' in target.parts:raise ValueError('Invalid archive path')
            target.parent.mkdir(parents=True,exist_ok=True)
            with archive.open(member) as source,target.open('wb') as output:shutil.copyfileobj(source,output)
        # This identity was independently verified against PyPI in the baseline.
        manifest=json.loads(archive.read('assets/port-source-manifest.json'))
        path=ROOT/'android/.native-runtime/port-assets/wheels/numpy-official.json'
        path.parent.mkdir(parents=True,exist_ok=True)
        path.write_text(json.dumps(manifest['architecture_adapter'],indent=2)+'\n')
    print('Recovered unchanged native runtimes and guest pack; no VM rebuild')


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('apk',type=Path);args=parser.parse_args();restore(args.apk)
