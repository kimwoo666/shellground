"""Export a tested, stopped Conda guest as a separate developer runtime pack."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import time
from conda_teaching.channel import hashes
from conda_teaching.course_smoke import source_fingerprint
from conda_teaching.learning_smoke import learning_fingerprint
from conda_teaching.setup_smoke import validate_setup
from real_vm import runtime_info
from conda_teaching.engine import course as load_course

ROOT=Path(__file__).resolve().parents[1]
ANSWER_CASES={'runtime_answer_with_base_active','normalized_root_path','unrelated_root_path_rejected',
              'normalized_environment_path','stale_inactive_answer_rejected','inactive_state_repaired',
              'environment_name_or_full_path','same_basename_wrong_path_rejected','stale_active_answer_rejected',
              'active_state_repaired','absent_environment_wrong_answer_rejected','boolean_type_preserved',
              'explicit_target_new_exporter'}


def validate_report(report,spec,fingerprint):
    expected={problem['id'] for unit in spec['units'] for problem in unit['problems']}
    repairs={'conda_activate_example','conda_install_example','conda_export_intent_example','conda_update_preserve'}
    from conda_teaching.pip_acceptance import CASES
    pip_cases={key+'/'+case for key,cases in CASES.items() if key in expected for case in cases}
    if (report.get('count')!=len(expected) or set(report.get('passed',[]))!=expected
            or report.get('state')!='complete' or report.get('fixture_clean') is not True
            or not repairs.issubset(report.get('negative_repair',[]))
            or not ANSWER_CASES.issubset(report.get('answer_cases',[]))
            or not pip_cases.issubset(report.get('answer_cases',[]))
            or report.get('fingerprint')!=fingerprint):
        raise RuntimeError('Current full real Conda course validation is required before export')


def validate_learning(report,spec,course_hash,steps_hash):
    expected={unit['key'] for unit in spec['units']}
    if (report.get('count')!=len(expected) or set(report.get('passed',[]))!=expected
            or report.get('state')!='complete' or report.get('fixture_clean') is not True
            or report.get('course_fingerprint')!=course_hash or report.get('fingerprint')!=steps_hash):
        raise RuntimeError('Current real Conda learning-step validation is required before export')


def export_destination(requested=None,root=ROOT):
    """A new versioned directory, never replacement of an existing pack."""
    root=Path(root).resolve()
    destination=Path(requested) if requested else root/'.vm-runtime-conda/linux-x86_64'
    if not destination.is_absolute():destination=root/destination
    if destination.is_symlink() or destination.exists():
        raise RuntimeError('Runtime destination already exists; choose a new versioned directory')
    resolved=destination.resolve()
    if not resolved.is_relative_to(root) or resolved==root:
        raise RuntimeError('Runtime export must stay inside this project')
    if destination.absolute()!=resolved:
        raise RuntimeError('Use a canonical export directory without symlinks or parent traversal')
    return resolved


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--destination',type=Path,help='New project-local versioned runtime directory; existing paths are never overwritten')
    args=parser.parse_args()
    destination=export_destination(args.destination)
    build=ROOT/'.conda-build'
    report=json.loads((build/'course-validation.json').read_text())
    course=load_course()
    validate_report(report,course,source_fingerprint())
    learning=json.loads((build/'learning-validation.json').read_text())
    validate_learning(learning,course,source_fingerprint(),learning_fingerprint())
    setup=json.loads((build/'setup-validation.json').read_text())
    validate_setup(setup)
    source,spec=runtime_info(ROOT/'.vm-runtime/linux-x86_64')
    marker=json.loads((build/'image-owner.json').read_text())
    if marker.get('kind')!='shellground-conda-builder' or marker.get('base')!=str((source/spec['image']).resolve()):
        raise RuntimeError('Unexpected developer image ownership')
    # QEMU uses byte-range locks; qemu-img refuses an in-use source. Never pass
    # --force-share to bypass that safety check, and never overwrite old packs.
    destination.mkdir(parents=True)
    for name in ('usr','etc'):
        shutil.copytree(source/name,destination/name,symlinks=True,copy_function=os.link)
    image=destination/'base.qcow2'
    env=dict(os.environ,LD_LIBRARY_PATH=str(source/'usr/lib/x86_64-linux-gnu'),QEMU_MODULE_DIR=str(source/'usr/lib/x86_64-linux-gnu/qemu'))
    subprocess.run([str(source/spec['qemu_img']),'convert','-O','qcow2',str(build/'provisioning.qcow2'),str(image)],env=env,check=True)
    result=dict(spec,image='base.qcow2',image_sha256=hashes(image)['sha256'],conda_course=True,
                conda_validation=report,conda_learning_validation=learning,conda_setup_validation=setup,exported_at=time.time())
    (destination/'runtime.json').write_text(json.dumps(result,indent=2)+'\n')
    print('Separate verified Conda runtime exported: '+str(destination),flush=True)


if __name__=='__main__':main()
