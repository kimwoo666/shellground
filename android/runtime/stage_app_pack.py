"""Stream a verified development guest into bounded APK data assets.

AGP materializes each asset while packaging; a single 1.7GB qcow2 exceeds its
heap. Small uncompressed pieces bound packaging memory without changing bytes.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil

ANDROID = Path(__file__).resolve().parents[1]
CHUNK_SIZE = 32 * 1024 * 1024


def stage(source, destination):
    source, destination = Path(source), Path(destination)
    allowed = ANDROID / 'app/build/generated/realAssets/training-pack'
    if destination.resolve() != allowed:
        raise ValueError('Only the owned generated app asset directory may be staged')
    manifest = json.loads((source / 'manifest.json').read_text())
    if manifest.get('schema') != 1 or set(manifest.get('files', {})) != {'base.qcow2', 'kernel', 'initrd'}:
        raise ValueError('Unexpected guest pack manifest')
    # Validate every source before replacing any generated assets.
    for name, spec in manifest['files'].items():
        with (source / name).open('rb') as stream:
            checksum = hashlib.file_digest(stream, 'sha256').hexdigest()
        if (source/name).stat().st_size != spec['size'] or checksum != spec['sha256']:
            raise ValueError('Source pack checksum mismatch: ' + name)
    destination.mkdir(parents=True, exist_ok=True)
    pieces = []
    with (source / 'base.qcow2').open('rb') as stream:
        for index in range(1024):
            block = stream.read(CHUNK_SIZE)
            if not block: break
            name = f'base-{index:04d}.sgpart'
            target = destination / name
            target.write_bytes(block)
            pieces.append({'name':name, 'size':len(block), 'sha256':hashlib.sha256(block).hexdigest()})
        else: raise ValueError('Guest pack has too many pieces')
    for name in ('kernel', 'initrd', 'manifest.json'):
        shutil.copy2(source/name, destination/name)
    (destination/'packaging.json').write_text(json.dumps({'schema':1,'base_parts':pieces},indent=2)+'\n')
    # Remove only the previous, generated monolithic copy of this same asset.
    # Source images and app-private practice data are never touched.
    (destination/'base.qcow2').unlink(missing_ok=True)
    current = {piece['name'] for piece in pieces}
    for stale in destination.glob('base-[0-9][0-9][0-9][0-9].sgpart'):
        if stale.name not in current: stale.unlink()
    print(f'Staged verified guest in {len(pieces)} bounded parts ({CHUNK_SIZE} bytes each maximum)',flush=True)


if __name__ == '__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--source',type=Path,default=ANDROID/'.native-runtime/ubuntu-arm64/android-pack-v1')
    parser.add_argument('--destination',type=Path,required=True)
    args=parser.parse_args()
    stage(args.source,args.destination)
