"""Build the Linux app and setup with verified existing offline guest assets."""
import importlib.metadata
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile

from build_windows_release import CONFIG, ROOT, digest, download, extract


def main():
    if sys.platform != 'linux':
        raise RuntimeError('Build on native Linux')
    output = ROOT / 'dist-linux-release'
    output.mkdir(parents=True, exist_ok=True)
    cache = ROOT / '.linux-build/release-assets'
    original = download(CONFIG['linux_asset_source'], cache / 'baseline.tar')
    assets = cache / 'baseline'
    with tarfile.open(original) as archive:
        archive.extractall(assets, filter='data')
    linux = assets / 'Shellground-Linux'
    windows_zip = download(CONFIG['asset_source'], cache / 'windows-assets.zip')
    extract(windows_zip, cache / 'windows-assets')
    windows = cache / 'windows-assets/Shellground-Windows'
    wheels = windows / '_internal/conda_teaching/wheels'
    from conda_teaching.pip_wheel import NUMPY_WHEEL, load_numpy_wheel
    wheel = wheels / NUMPY_WHEEL['filename']
    load_numpy_wheel(wheel)
    (ROOT / '.conda-build').mkdir(exist_ok=True)
    shutil.copy2(wheel, ROOT / '.conda-build' / wheel.name)
    subprocess.run([sys.executable, str(ROOT / 'build.py'), '--skip-vm-pack',
                    '--offline-assets-from', str(windows), '--dist-dir', str(output / 'build'),
                    '--verification', 'incremental'], cwd=ROOT, check=True)
    package = output / 'package/Shellground-Linux'
    package.mkdir(parents=True)
    shutil.copy2(output / 'build/Shellground', package / 'Shellground')
    shutil.copytree(linux / 'runtime', package / 'runtime', ignore=shutil.ignore_patterns('base.qcow2'))
    if (linux / 'licenses').is_dir():
        shutil.copytree(linux / 'licenses', package / 'licenses')
    for distribution in importlib.metadata.distributions():
        for item in distribution.files or ():
            if '.dist-info/' in str(item) and any(key in Path(str(item)).name.upper() for key in ('LICENSE', 'COPYING', 'NOTICE')):
                source = Path(distribution.locate_file(item))
                if source.is_file():
                    target = package / 'licenses/host-build' / str(item)
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(source, target)
    shutil.copy2(ROOT.parent / 'THIRD_PARTY_NOTICES.md', package / 'THIRD_PARTY_NOTICES.md')
    archive_path = output / CONFIG['linux_archive']
    with tarfile.open(archive_path, 'w') as archive:
        archive.add(package, arcname='Shellground-Linux')
    manifest = json.loads((ROOT / 'installer/manifest.json').read_text())
    manifest.update(version=CONFIG['version'], application_base_url='https://github.com/kimwoo666/shellground/releases/download/' + CONFIG['tag'] + '/')
    manifest['linux'] = dict(name=archive_path.name, bytes=archive_path.stat().st_size, sha256=digest(archive_path))
    stage = output / 'setup-source'
    stage.mkdir()
    for name in ('linux_setup.py', 'core.py', 'shellground.svg'):
        shutil.copy2(ROOT / 'installer' / name, stage / name)
    shutil.copytree(ROOT / 'installer/licenses', stage / 'licenses')
    (stage / 'manifest.json').write_text(json.dumps(manifest, indent=2))
    subprocess.run([sys.executable, '-m', 'PyInstaller', '--noconfirm', '--clean', '--onefile',
                    '--name', CONFIG['linux_setup'], '--distpath', str(output),
                    '--workpath', str(output / 'setup-build'), '--specpath', str(stage),
                    '--add-data', str(stage / 'manifest.json') + ':.',
                    '--add-data', str(stage / 'shellground.svg') + ':.',
                    '--add-data', str(stage / 'licenses') + ':licenses', str(stage / 'linux_setup.py')], check=True)
    setup = output / CONFIG['linux_setup']
    receipt = dict(tag=CONFIG['tag'], version=CONFIG['version'], platform='linux-x86_64',
                   files={p.name: dict(bytes=p.stat().st_size, sha256=digest(p)) for p in (archive_path, setup)})
    (output / 'linux-build.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps(receipt, indent=2))


if __name__ == '__main__': main()
