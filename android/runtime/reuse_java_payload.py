"""Reuse a pinned APK's unchanged data/native payload for Java-only updates.

The source fingerprint rejects changed Python code, course inputs, guest sources,
or Python dependency configuration. App Java/resources/manifest are rebuilt by
Gradle. This is not an APK byte patch and never reuses old DEX or signatures.
"""
import argparse
import hashlib
from pathlib import Path
import shutil
import zipfile

ROOT = Path(__file__).resolve().parents[2]
APK_SHA = 'd36316845ddf1891ed335103fc63c5d7c999c83a942e10cf6e6452caf104d199'
SOURCE_SHA = 'b27834d322f801bf64bd3c9ccb90ce3197c6fc557a3a3222cff323562d608013'


def fingerprint():
    paths = set()
    for folder, pattern in [
        ('desktop', '*.py'), ('desktop/python_teaching', '*'),
        ('desktop/conda_teaching', '*'), ('desktop/notebook_teaching', '*'),
        ('desktop/guest', '*'), ('android/app/src/main/python', '*'),
        ('android/app/src/main/assets', '**/*'),
    ]:
        paths.update(p for p in (ROOT / folder).glob(pattern) if p.is_file() and p.suffix not in ('.pyc', '.pyo'))
    paths.update(ROOT / p for p in ['desktop/lab/lab.py', 'android/runtime/export_port_assets.py', 'android/build.gradle.kts'])
    digest = hashlib.sha256()
    for path in sorted(paths):
        digest.update(path.relative_to(ROOT).as_posix().encode() + b'\0')
        digest.update(path.read_bytes().replace(b'\r\n', b'\n') + b'\0')
    build = (ROOT / 'android/app/build.gradle.kts').read_text(encoding='utf-8')
    python = build.split('chaquopy {', 1)[1].split('tasks.named("preBuild")', 1)[0]
    digest.update(python.encode())
    return digest.hexdigest()


def restore(apk):
    if fingerprint() != SOURCE_SHA:
        raise ValueError('Python/course sources changed: use the normal full build instead of reuseJavaPayload')
    with apk.open('rb') as stream:
        if hashlib.file_digest(stream, 'sha256').hexdigest() != APK_SHA:
            raise ValueError('Baseline APK checksum mismatch')
    destination = ROOT / 'android/app/build/generated/javaPayload'
    with zipfile.ZipFile(apk) as archive:
        for member in archive.infolist():
            name = member.filename
            if name.startswith('assets/'):
                relative = Path(name)
                existing = ROOT / 'android/app/src/main' / relative
                if existing.is_file():
                    if existing.read_bytes() != archive.read(member):
                        raise ValueError('Bundled asset differs from source: ' + name)
                    continue
            elif name.startswith(('lib/arm64-v8a/', 'lib/x86_64/')):
                relative = Path('jniLibs') / Path(name).relative_to('lib')
            else:
                continue
            if '..' in relative.parts or member.is_dir():
                raise ValueError('Invalid payload member: ' + name)
            target = destination / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(member) as source, target.open('wb') as output:
                shutil.copyfileobj(source, output)
    print('Verified 4.7.6 payload restored; Gradle rebuilds Java, resources and APK signature')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('apk', type=Path)
    restore(parser.parse_args().apk)
