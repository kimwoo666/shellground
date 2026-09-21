"""Build the Windows application and setup; reuse only verified offline assets.

The shared 7.8 GB guest is downloaded by setup, not embedded in the app ZIP.
Use --assets-from for local QA and --link-disk to attach the immutable guest
without keeping a second copy. The ZIP always excludes that disk.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parent
CONFIG = json.loads((ROOT / 'windows_release.json').read_text(encoding='utf-8'))


def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def download(spec, target):
    target.parent.mkdir(parents=True, exist_ok=True)
    if not target.exists() or digest(target) != spec['sha256']:
        pending = target.with_suffix('.partial')
        request = urllib.request.Request(spec['url'], headers={'User-Agent': 'Shellground-Windows-Build'})
        with urllib.request.urlopen(request, timeout=45) as response, pending.open('wb') as output:
            shutil.copyfileobj(response, output)
        if digest(pending) != spec['sha256']:
            pending.unlink()
            raise ValueError('Downloaded build asset checksum mismatch')
        pending.replace(target)
    return target


def extract(archive, target):
    target.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive) as source:
        for item in source.infolist():
            path = (target / item.filename).resolve()
            if not path.is_relative_to(target.resolve()) or ':' in item.filename:
                raise ValueError('Unsafe ZIP member')
        source.extractall(target)


def asset_paths(folder):
    if (folder / 'windows-x86_64').is_dir():
        return folder/'windows-x86_64', folder/'notebook-assets', folder/'conda-wheels', folder/'licenses'
    return (folder/'runtime/windows-x86_64', folder/'_internal/notebook_teaching',
            folder/'_internal/conda_teaching/wheels', folder/'licenses')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--assets-from', type=Path)
    parser.add_argument('--makensis', type=Path)
    parser.add_argument('--output', type=Path, default=ROOT/'dist-windows-release')
    parser.add_argument('--link-disk', action='store_true')
    parser.add_argument('--prebuilt', type=Path, help='Package an existing Windows bundle without building or claiming native verification')
    parser.add_argument('--host-license-root', type=Path, help='Site-packages of the prebuilt Windows dependencies')
    args = parser.parse_args()
    if sys.platform != 'win32' and args.prebuilt is None:
        raise RuntimeError('Build this release on native Windows')
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    cache = ROOT / '.windows-build/release-assets'
    assets = args.assets_from
    if assets is None:
        baseline = download(CONFIG['asset_source'], cache/'baseline.zip')
        extract(baseline, cache/'baseline')
        assets = cache/'baseline/Shellground-Windows'
    runtime, notebook, wheels, licenses = asset_paths(assets.resolve())
    # Check offline wheels against the published manifest before repackaging.
    expected = json.loads((ROOT/'notebook_teaching/assets-linux-x86_64.json').read_text())
    for wheel in expected['wheels']:
        path = notebook/'wheels-linux-x86_64'/wheel['filename']
        if path.stat().st_size != wheel['size'] or digest(path) != wheel['sha256']:
            raise ValueError('Unverified notebook wheel: ' + wheel['filename'])
    if args.prebuilt is None:
        subprocess.run([sys.executable, str(ROOT/'build.py'), '--skip-vm-pack',
            '--dist-dir', str(output/'build'), '--verification', 'incremental'], cwd=ROOT, check=True)
    bundle = args.prebuilt.resolve() if args.prebuilt else output/'build/Shellground'
    if not (bundle/'Shellground.exe').is_file():
        raise ValueError('Windows application executable is missing')
    shutil.copytree(runtime, bundle/'runtime/windows-x86_64', dirs_exist_ok=True,
        ignore=shutil.ignore_patterns('base.qcow2'))
    if args.link_disk:
        image = runtime/'base.qcow2'
        spec = json.loads((runtime/'runtime.json').read_text())
        if digest(image) != spec['image_sha256']:
            raise ValueError('Local guest disk checksum mismatch')
        os.link(image, bundle/'runtime/windows-x86_64/base.qcow2')
    destination = bundle/'_internal/notebook_teaching'
    shutil.copytree(notebook/'wheels-linux-x86_64', destination/'wheels-linux-x86_64', dirs_exist_ok=True)
    for name in ('assets-linux-x86_64.json', 'guest_setup.py', 'guest_service.py', 'guest_lessons.py'):
        shutil.copy2(ROOT/'notebook_teaching'/name, destination/name)
    from notebook_teaching.proof import source_hashes
    (destination/'source-hashes.json').write_text(json.dumps(source_hashes(), indent=2), encoding='utf-8')
    shutil.copytree(wheels, bundle/'_internal/conda_teaching/wheels', dirs_exist_ok=True)
    shutil.copytree(licenses, bundle/'licenses', dirs_exist_ok=True)
    shutil.copy2(ROOT.parent/'THIRD_PARTY_NOTICES.md', bundle/'THIRD_PARTY_NOTICES.md')
    # Ship notices for the newly installed host dependencies as well.
    import importlib.metadata
    distributions = importlib.metadata.distributions(path=[str(args.host_license_root.resolve())]) if args.host_license_root else importlib.metadata.distributions()
    for distribution in distributions:
        for item in distribution.files or ():
            if '.dist-info/' in str(item).replace('\\', '/') and any(
                    marker in Path(str(item)).name.upper() for marker in ('LICENSE', 'COPYING', 'NOTICE')):
                source = Path(distribution.locate_file(item))
                target = bundle/'licenses/host-build'/str(item)
                target.parent.mkdir(parents=True, exist_ok=True)
                if source.is_file():shutil.copy2(source, target)
    archive = output/CONFIG['archive']
    with zipfile.ZipFile(archive, 'x', compression=zipfile.ZIP_DEFLATED, compresslevel=6) as target:
        for path in sorted(bundle.rglob('*')):
            if path.is_file() and path.name != 'base.qcow2':
                target.write(path, 'Shellground-Windows/' + path.relative_to(bundle).as_posix())
    manifest = json.loads((ROOT/'installer/manifest.json').read_text())
    manifest['windows'] = dict(name=archive.name, bytes=archive.stat().st_size, sha256=digest(archive))
    stage = output/'setup-source'
    stage.mkdir()
    for name in ('windows_setup.ps1', 'windows_download.cs', 'windows_setup.nsi'):
        (stage/name).write_text((ROOT/'installer'/name).read_text(encoding='utf-8-sig'), encoding='utf-8-sig')
    (stage/'manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8-sig')
    shutil.copy2(ROOT/'installer/licenses/nsis.txt', stage/'Installer-Licenses.txt')
    compiler = args.makensis
    if compiler is None:
        package = download(CONFIG['nsis'], cache/'nsis.zip')
        extract(package, cache/'nsis')
        compiler = cache/'nsis/nsis-3.11/makensis.exe'
    setup = output/CONFIG['setup']
    option = '/' if sys.platform == 'win32' else '-'
    subprocess.run([str(compiler.resolve()), option+'V2', option+'DOUTPUT='+str(setup), option+'DAPP_ARCHIVE='+str(archive.resolve()), 'windows_setup.nsi'],
        cwd=stage, check=True)
    receipt = dict(tag=CONFIG['tag'], version=CONFIG['version'], platform='windows-x86_64',
        packaging_host=sys.platform, prebuilt=bool(args.prebuilt),
        files={p.name:dict(bytes=p.stat().st_size,sha256=digest(p)) for p in (archive,setup)})
    (output/'windows-build.json').write_text(json.dumps(receipt, indent=2)+'\n', encoding='utf-8')
    (output/'SHA256SUMS.txt').write_text(''.join(v['sha256']+'  '+k+'\n' for k,v in receipt['files'].items()),encoding='utf-8')
    print(json.dumps(receipt,indent=2),flush=True)


if __name__ == '__main__':
    main()
