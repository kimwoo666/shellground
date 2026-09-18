"""Publish new proof for an unchanged, freshly rechecked exported Linux base.

Read-only VM assets are hardlinked, never rewritten, avoiding another 16 GiB
copy on the developer laptop. The new runtime.json is a separate inode. Each
folder remains usable if the old folder is later removed; no external symlinks.
"""
import argparse
import json
import os
from pathlib import Path
import shutil
import time

from .engine import course
from .course_smoke import source_fingerprint
from .learning_smoke import learning_fingerprint
from .setup_smoke import validate_setup,setup_fingerprint
from .export_runtime import validate_report,validate_learning,export_destination
from .pip_wheel import digest
from real_vm import runtime_info


def validate_identity(proof,image_hash):
    if (proof.get('state')!='complete' or proof.get('units','missing') is not None
            or proof.get('setup_verified') is not True
            or proof.get('vm_stopped') is not True or proof.get('overlay_removed') is not True
            or proof.get('image_sha256')!=image_hash
            or proof.get('course_fingerprint')!=source_fingerprint()
            or proof.get('learning_fingerprint')!=learning_fingerprint()
            or proof.get('setup_fingerprint')!=setup_fingerprint()):
        raise RuntimeError('Full current source acceptance against this exact base, including cleanup, is required')


def export(source,reports,destination):
    source,spec=runtime_info(source);reports=Path(reports)
    destination=export_destination(destination)
    proof=json.loads((reports/'runtime-validation.json').read_text())
    validate_identity(proof,spec['image_sha256'])
    with (source/spec['image']).open('rb') as image:actual=digest(image)
    if actual!=spec['image_sha256']:raise RuntimeError('Previously verified base has changed')
    current=course()
    validated=json.loads((reports/'course-validation.json').read_text())
    learning=json.loads((reports/'learning-validation.json').read_text())
    setup=json.loads((reports/'setup-validation.json').read_text())
    validate_report(validated,current,source_fingerprint())
    validate_learning(learning,current,source_fingerprint(),learning_fingerprint())
    validate_setup(setup)
    destination.mkdir(parents=True)
    for item in source.iterdir():
        if item.name=='runtime.json':continue
        target=destination/item.name
        if item.is_symlink():
            if not item.resolve().is_relative_to(source.resolve()):raise ValueError('External runtime link')
            target.symlink_to(os.readlink(item))
        elif item.is_dir():shutil.copytree(item,target,symlinks=True,copy_function=os.link)
        else:os.link(item,target)
    result=dict(spec,conda_validation=validated,conda_learning_validation=learning,
                conda_setup_validation=setup,conda_runtime_revalidation=proof,
                conda_pip_course=True,revalidated_at=time.time())
    (destination/'runtime.json').write_text(json.dumps(result,indent=2)+'\n')
    print('New versioned pack; original image and review preserved: '+str(destination),flush=True)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path,required=True)
    parser.add_argument('--reports',type=Path,required=True)
    parser.add_argument('--destination',type=Path,required=True)
    args=parser.parse_args();export(args.source,args.reports,args.destination)


if __name__=='__main__':main()
