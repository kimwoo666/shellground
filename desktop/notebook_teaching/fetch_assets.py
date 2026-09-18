"""Developer-only: download official, hash-pinned Linux CPython 3.12 wheels.

No installation, host config, credentials, or package cache is changed.
The generated manifest records every transitive dependency and PyPI digest.
"""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import urllib.request
from packaging.utils import parse_wheel_filename

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / '.jupyter-build' / 'wheels-linux-x86_64'
REQUIREMENTS = ('ipykernel==7.3.0', 'jupyter-client==8.10.0', 'nbformat==5.11.1')


def digest(path):
    value = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            value.update(block)
    return value.hexdigest()


def main():
    if DEST.exists():
        raise RuntimeError('Asset directory already exists; inspect it instead of overwriting')
    DEST.mkdir(parents=True)
    command = [sys.executable, '-m', 'pip', '--isolated', '--disable-pip-version-check',
               'download', '--no-cache-dir', '--index-url', 'https://pypi.org/simple',
               '--only-binary=:all:', '--python-version', '312', '--implementation', 'cp',
               '--abi', 'cp312', '--abi', 'abi3', '--dest', str(DEST)]
    for platform in ('manylinux_2_35_x86_64', 'manylinux_2_34_x86_64', 'manylinux_2_28_x86_64',
                     'manylinux_2_17_x86_64', 'manylinux2014_x86_64', 'manylinux2010_x86_64'):
        command += ['--platform', platform]
    subprocess.run(command + list(REQUIREMENTS), check=True, timeout=240)
    records = []
    for path in sorted(DEST.glob('*.whl')):
        name, version, _, tags = parse_wheel_filename(path.name)
        with urllib.request.urlopen(f'https://pypi.org/pypi/{name}/{version}/json', timeout=25) as response:
            release = json.load(response)
        entry = next(record for record in release['urls'] if record['filename'] == path.name)
        sha = digest(path)
        if sha != entry['digests']['sha256'] or path.stat().st_size != entry['size']:
            raise RuntimeError('Official PyPI digest mismatch: ' + path.name)
        records.append(dict(name=name, version=str(version), filename=path.name, sha256=sha,
                            size=path.stat().st_size, url=entry['url'], tags=sorted(map(str, tags))))
        print('VERIFIED ' + path.name, flush=True)
    manifest = dict(schema=1, platform='linux-x86_64', python='3.12',
                    requirements=list(REQUIREMENTS), wheels=records)
    (DEST / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print(f'Official offline Jupyter assets: {len(records)} wheels, {sum(r["size"] for r in records)} bytes', flush=True)


if __name__ == '__main__':
    main()
