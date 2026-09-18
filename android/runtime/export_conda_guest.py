"""Export a STOPPED, fully verified ARM Conda guest, never overwrite a pack.

Developer proof only: Android integration and physical-device acceptance remain
separate. Reuse all desktop course gates; an x86 report is not ARM evidence.
"""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import tempfile

from build_conda_guest import BUILD, PACK, SPEC, DESKTOP, RUNTIME, build_environment, sha256
from conda_teaching.course_smoke import source_fingerprint
from conda_teaching.learning_smoke import learning_fingerprint
from conda_teaching.export_runtime import validate_report, validate_learning


def validate_proofs(provision, course, learning, spec, course_hash, steps_hash):
    if (provision.get('installer_sha256') != SPEC['sha256']
            or provision.get('subdir') != 'linux-aarch64'
            or provision.get('offline') is not True
            or provision.get('smoke') != 'CONDA_REAL_OFFLINE_CREATE_ACTIVATE_INSTALL_UPDATE_EXPORT_RECREATE_REMOVE_OK'):
        raise ValueError('Actual pinned ARM Conda provisioning proof required')
    if course.get('guest_architecture') != 'aarch64':
        raise ValueError('Actual ARM course proof required; x86 results cannot substitute')
    validate_report(course, spec, course_hash)
    validate_learning(learning, spec, course_hash, steps_hash)


def export(destination):
    if destination.exists() or destination.is_symlink():
        raise ValueError('Preserve existing pack; choose a new destination')
    provision = json.loads((BUILD / 'provision-validation.json').read_text())
    course = json.loads((BUILD / 'course-validation.json').read_text())
    learning = json.loads((BUILD / 'learning-validation.json').read_text())
    spec = json.loads((DESKTOP / 'conda_teaching/course_spec.json').read_text())
    fingerprints = (source_fingerprint(), learning_fingerprint())
    validate_proofs(provision, course, learning, spec, *fingerprints)
    manifest = json.loads((PACK / 'manifest.json').read_text())
    if manifest.get('guest_arch') != 'aarch64':
        raise ValueError('ARM backing pack required')
    for name in ('base.qcow2', 'kernel', 'initrd'):
        if (PACK / name).is_symlink() or sha256(PACK / name) != manifest['files'][name]['sha256']:
            raise ValueError('Immutable backing pack changed: ' + name)
    owner = json.loads((BUILD / 'image-owner.json').read_text())
    expected = {'schema': 1, 'kind': 'shellground-arm64-conda-builder',
                'base': str(PACK / 'base.qcow2'),
                'base_sha256': manifest['files']['base.qcow2']['sha256'],
                'installer_sha256': SPEC['sha256']}
    source = BUILD / 'provisioning.qcow2'
    if owner != expected or source.is_symlink() or not source.is_file():
        raise ValueError('Unrecognized Conda build image; preserve it')
    destination.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix='sg-arm-conda-pack-', dir=destination.parent))
    try:
        image = staging / 'base.qcow2'
        # Normal QEMU byte-range locks must reject a VM still using this source.
        subprocess.run([str(RUNTIME / 'usr/bin/qemu-img'), 'convert', '-m', '2', '-c',
                        '-O', 'qcow2', str(source), str(image)], env=build_environment(), check=True)
        info = json.loads(subprocess.check_output([str(RUNTIME / 'usr/bin/qemu-img'),
            'info', '--output=json', str(image)], env=build_environment(), text=True))
        if info.get('format') != 'qcow2' or info.get('backing-filename'):
            raise ValueError('A standalone qcow2 image is required')
        for name in ('kernel', 'initrd'):
            shutil.copyfile(PACK / name, staging / name)
        if fingerprints != (source_fingerprint(), learning_fingerprint()):
            raise ValueError('Course changed during export; rerun validation')
        result = {'schema': 1, 'id': 'shellground-ubuntu-arm64-conda-dev-v1',
                  'guest_arch': 'aarch64', 'development_only': True, 'conda_course': True,
                  'scope': 'Developer-verified Conda guest; Android app/device verification required',
                  'files': {name: {'size': (staging / name).stat().st_size,
                                   'sha256': sha256(staging / name)}
                            for name in ('base.qcow2', 'kernel', 'initrd')},
                  'conda_provision_validation': provision, 'conda_validation': course,
                  'conda_learning_validation': learning,
                  'backing_pack_sha256': manifest['files']['base.qcow2']['sha256']}
        (staging / 'manifest.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
        staging.rename(destination)
        print('Verified developer ARM Conda pack: ' + str(destination), flush=True)
    except BaseException:
        print('Unpublished staging retained: ' + str(staging), flush=True)
        raise


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--destination', type=Path, default=BUILD / 'android-pack-conda-v1')
    export(parser.parse_args().destination.absolute())
