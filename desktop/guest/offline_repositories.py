"""Build-time only: genuine registry manifests and an app-owned local APT repo."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import urllib.request

ROOT = Path('/opt/shellground')
ACCEPT = ', '.join(('application/vnd.oci.image.manifest.v1+json', 'application/vnd.oci.image.index.v1+json',
                    'application/vnd.docker.distribution.manifest.v2+json', 'application/vnd.docker.distribution.manifest.list.v2+json'))


def run(*args, cwd=None):
    return subprocess.check_output(args, cwd=cwd, text=True)


def platform_manifest_for(manifest, architecture):
    """Choose the real guest's image, never the build computer's CPU."""
    if architecture not in ('amd64', 'arm64'):
        raise ValueError('Unsupported guest image architecture: ' + architecture)
    candidates = [item for item in manifest.get('manifests', [])
                  if item.get('platform', {}).get('os') == 'linux'
                  and item.get('platform', {}).get('architecture') == architecture
                  and item.get('platform', {}).get('variant', '') in ('', 'v8')]
    if len(candidates) != 1:
        raise ValueError(f'Expected one Linux {architecture} image, found {len(candidates)}')
    return candidates[0]


def capture_fixture(repository, tag):
    reference = f'localhost:5000/{repository}:{tag}'
    # Docker's containerd store may push a platform-filtered OCI index with a
    # different ID from the original multi-platform Docker Hub index. Measure
    # the identity after pulling what this registry actually serves.
    run('docker', 'pull', reference)
    def get_manifest(reference):
        request = urllib.request.Request(f'http://127.0.0.1:5000/v2/{repository}/manifests/{reference}',
                                         headers={'Accept': ACCEPT})
        with urllib.request.urlopen(request, timeout=10) as response:
            return response.read().decode(), response.headers['Content-Type']
    raw, content_type = get_manifest(tag)
    manifest = json.loads(raw)
    platform_manifest = manifest
    if 'manifests' in manifest:
        platform = platform_manifest_for(manifest, run('dpkg', '--print-architecture').strip())
        platform_manifest = json.loads(get_manifest(platform['digest'])[0])
    return {'manifest': manifest, 'raw': raw, 'type': content_type,
            'config_id': platform_manifest['config']['digest'],
            'id': json.loads(run('docker', 'image', 'inspect', reference))[0]['Id']}


def refresh_identities():
    fixtures = {key: capture_fixture(repository, tag) for key, repository, tag in (
        ('ubuntu_v1', 'training/ubuntu', 'v1'), ('ubuntu_v2', 'training/ubuntu', 'v2'),
        ('alpine', 'training/alpine', 'latest'))}
    (ROOT / 'registry-fixtures.json').write_text(json.dumps(fixtures))


def registry():
    config = {'version': .1, 'log': {'level': 'warn'},
              'storage': {'filesystem': {'rootdirectory': '/var/lib/docker-registry'}},
              'http': {'addr': '127.0.0.1:5000'}}
    Path('/etc/docker/registry/config.yml').write_text(json.dumps(config))
    subprocess.run(['systemctl', 'enable', '--now', 'docker-registry'], check=True)
    subprocess.run(['systemctl', 'restart', 'docker-registry'], check=True)
    for image in ('ubuntu:24.04', 'alpine:latest'):
        if subprocess.run(['docker', 'image', 'inspect', image], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode:
            run('docker', 'pull', image)
    build = ROOT / 'image-build'
    build.mkdir(exist_ok=True)
    (build / 'Dockerfile').write_text('FROM ubuntu:24.04\n'
        'LABEL org.shellground.revision="v2"\n'
        'RUN printf "training update v2\\n" > /etc/shellground-release\n')
    run('docker', 'build', '--network=none', '-t', 'shellground-build:v2', str(build))
    fixtures = {}
    for key, source, repository, tag in (
            ('ubuntu_v1', 'ubuntu:24.04', 'training/ubuntu', 'v1'),
            ('ubuntu_v2', 'shellground-build:v2', 'training/ubuntu', 'v2'),
            ('alpine', 'alpine:latest', 'training/alpine', 'latest')):
        reference = f'localhost:5000/{repository}:{tag}'
        run('docker', 'tag', source, reference)
        run('docker', 'push', reference)
        fixtures[key] = capture_fixture(repository, tag)
    (ROOT / 'registry-fixtures.json').write_text(json.dumps(fixtures))


def apt_repository():
    repository = ROOT / 'apt-repo'
    repository.mkdir(exist_ok=True)
    run('apt-get', 'download', 'tree', cwd=repository)
    # These local packages support later upgrade/dependency/remove/purge tasks.
    for name, version, depends in (('shellground-helper', '1.0', ''),
                                   ('shellground-helper', '2.0', ''),
                                   ('shellground-note', '1.0', 'shellground-helper (>= 1.0)'),
                                   ('shellground-note', '2.0', 'shellground-helper (>= 2.0)')):
        folder = ROOT / ('package-build-' + name + '-' + version)
        (folder / 'DEBIAN').mkdir(parents=True, exist_ok=True)
        (folder / 'DEBIAN/control').write_text(f'Package: {name}\nVersion: {version}\n'
            'Architecture: all\nMaintainer: Shellground <training@example.invalid>\n'
            + (f'Depends: {depends}\n' if depends else '') + 'Description: Offline package management practice fixture\n')
        (folder / 'usr/share' / name).mkdir(parents=True, exist_ok=True)
        (folder / 'usr/share' / name / 'version.txt').write_text(version + '\n')
        if name == 'shellground-note':
            (folder / 'etc').mkdir(exist_ok=True)
            (folder / 'etc/shellground-note.conf').write_text('status=draft\n')
            (folder / 'DEBIAN/conffiles').write_text('/etc/shellground-note.conf\n')
        run('dpkg-deb', '--build', '--root-owner-group', str(folder), str(repository / f'{name}_{version}_all.deb'))
    (repository / 'Packages').write_text(run('dpkg-scanpackages', '--multiversion', '.', cwd=repository))
    # The only unsigned source trusted here is this root-owned in-guest fixture
    # directory; never teach this as a setting for an arbitrary internet source.
    saved = ROOT / 'original-apt-sources'
    saved.mkdir(exist_ok=True)
    for path in [Path('/etc/apt/sources.list'), *Path('/etc/apt/sources.list.d').glob('*')]:
        if path.is_file() and path.name != 'shellground.list':
            shutil.move(str(path), str(saved / path.name))
    Path('/etc/apt/sources.list.d/shellground.list').write_text('deb [trusted=yes] file:/opt/shellground/apt-repo ./\n')
    run('apt-get', 'update')


if __name__ == '__main__':
    if (ROOT / 'guest-owned').read_text().strip() != 'shellground-disposable-guest-v1' or not Path('/dev/virtio-ports/org.shellground.agent').exists():
        raise RuntimeError('Dedicated guest required')
    if os.getuid() != 0:
        raise RuntimeError('Image provisioning requires guest root')
    registry()
    apt_repository()
