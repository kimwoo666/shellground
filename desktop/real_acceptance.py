"""Build gate for all currently registered real Linux/Docker/ROS problems.

This certifies the registered course, not every command mentioned in a PDF.
"""
import json
from pathlib import Path
from course_topics import topic_of
from mode_curriculum import curriculum
from verify_real_course import fingerprint


def expected_cases(ros=False):
    units,reviews=curriculum('real')
    selected=[u for u in units if (topic_of(u)=='ROS 2')==ros]
    expected={u.key+':'+str(v) for u in selected for v in range(3)}
    expected.update(r.key for r in reviews if all((topic_of(u)=='ROS 2')==ros for u in r.units))
    return expected


def validate(report,ros=False):
    expected=expected_cases(ros)
    if (report.get('state')!='complete' or report.get('source_fingerprint')!=fingerprint() or
        set(report.get('expected',[]))!=expected or set(report.get('passed',{}))!=expected or
        report.get('failures') or report.get('vm_stopped') is not True or report.get('overlay_removed') is not True):
        raise RuntimeError('현재 등록된 '+('ROS 2' if ros else 'Linux/Docker')+' 전체 과정 검증이 필요합니다.')
    if ros and not {'unfiltered_bag_playback_rejected','wrong_service_orientation_repaired',
                    'stale_parameter_report_repaired'}.issubset(report.get('negative',[])):
        raise RuntimeError('ROS 2 오답·복구 검증이 필요합니다.')


def validate_directory(directory):
    directory = Path(directory)
    incremental = directory / 'incremental-course-manifest.json'
    if incremental.exists():
        from incremental_acceptance import validate_file
        return validate_file(incremental)
    for name,ros in (('linux-docker-final.json',False),('ros-final.json',True)):
        validate(json.loads((directory/name).read_text()),ros)
