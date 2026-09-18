"""Verify current course sources against an immutable exported Linux pack.

Unlike the developer builder, this uses the exact shipped base in a disposable
overlay. Reports are bound to its verified image hash; old review packs and
their acceptance reports are never overwritten.
"""
import argparse
import json
from pathlib import Path

from .engine import CondaEngine
from .course_smoke import check_course,source_fingerprint
from .learning_smoke import check_learning,learning_fingerprint
from .pip_wheel import digest
from real_vm import runtime_info
from .setup_smoke import check_setup,setup_fingerprint


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runtime',type=Path,required=True)
    parser.add_argument('--report-dir',type=Path,required=True)
    parser.add_argument('--units',nargs='+')
    parser.add_argument('--with-setup',action='store_true')
    args=parser.parse_args()
    root,spec=runtime_info(args.runtime)
    if spec.get('conda_course') is not True:raise RuntimeError('A validated Conda base is required')
    with (root/spec['image']).open('rb') as image:actual=digest(image)
    if actual!=spec['image_sha256']:raise RuntimeError('Immutable base image hash mismatch')
    args.report_dir.mkdir(parents=True,exist_ok=True)
    identity=dict(runtime=str(root.resolve()),image_sha256=actual,
                  course_fingerprint=source_fingerprint(),learning_fingerprint=learning_fingerprint(),
                  setup_fingerprint=setup_fingerprint(),
                  state='in_progress',units=args.units,setup_verified=False)
    report=args.report_dir/'runtime-validation.json'
    report.write_text(json.dumps(identity,indent=2)+'\n')
    engine=CondaEngine(root);process=None;session=None
    try:
        engine.boot();process=engine.process;session=engine.session_dir
        print('Actual exported Linux base; disposable overlay, hardware acceleration, no host mounts',flush=True)
        check_course(engine.channel,args.units,args.report_dir/'course-validation.json')
        check_learning(engine.channel,args.units,args.report_dir/'learning-validation.json')
        if args.with_setup:
            check_setup(engine.channel,args.report_dir/'setup-validation.json')
            identity['setup_verified']=True
        if (identity['course_fingerprint'],identity['learning_fingerprint'],identity['setup_fingerprint'])!=(
                source_fingerprint(),learning_fingerprint(),setup_fingerprint()):
            raise RuntimeError('Course source changed during verification')
        identity['state']='complete'
    except BaseException as error:
        identity.update(state='failed',error=str(error)[-2000:]);raise
    finally:
        engine.close()
        identity['vm_stopped']=process is None or process.poll() is not None
        identity['overlay_removed']=session is None or not session.exists()
        if not identity['vm_stopped'] or not identity['overlay_removed']:
            identity['state']='failed'
        report.write_text(json.dumps(identity,indent=2)+'\n')
    if identity['state']!='complete':raise RuntimeError('VM cleanup was not verified')
    print('Actual guest verification and owned VM cleanup complete',flush=True)


if __name__=='__main__':main()
