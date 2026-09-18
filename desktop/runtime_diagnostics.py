"""Explicit packaged-runtime diagnostic; no saved learner progress is touched."""
import base64
import json
import time
from real_vm import RealEngine
from ros_lessons import make_ros_mission
from missions import make_mission
from real_lessons import adapt_real_mission


def verify_real_runtime():
    engine = RealEngine()
    report = {}
    try:
        mission = make_ros_mission('ros_set', 7890)
        engine.start(mission)
        engine.open_terminal(mission)
        if engine.rpc('grade', mission)['passed']:
            raise RuntimeError('Unsolved diagnostic was incorrectly graded as complete')
        result = engine.channel.request('exec', cwd=mission.start,
                                        argv=['bash', '-c', mission.solution])
        if result['code']:
            raise RuntimeError(base64.b64decode(result['err']).decode(errors='replace'))
        graded = engine.rpc('grade', mission)
        if not graded['passed']:
            raise RuntimeError(json.dumps(graded, ensure_ascii=False))
        if not engine.screen().startswith(b'\x89PNG'):
            raise RuntimeError('Guest display capture failed')
        report.update(actual_ros=True, actual_guest_display=True, offline=True,
                      boot_seconds=round(engine.start_seconds, 2))
        for key in ('copy', 'sim_apt', 'sim_update', 'sim_save', 'admin_review', 'docker_review'):
            mission = adapt_real_mission(make_mission(key, 9280 if key == 'copy' else 7890, 1 if key == 'copy' else 0))
            engine.start(mission)
            engine.open_terminal(mission)
            if key == 'copy':
                import shlex
                # Reproduce the exact reported source/work-folder distinction
                # before any solution commands can rename the fixture.
                probe = engine.channel.request('exec', argv=['bash', '-c',
                    'test ! -e ' + shlex.quote(mission.source + '/draft.txt') +
                    ' && cat ' + shlex.quote(mission.target + '/draft.txt')])
                if probe['code'] or base64.b64decode(probe['out']) != b'Draft 9280\n':
                    raise RuntimeError('Reported copy 9280 fixture was not prepared correctly')
            if engine.rpc('grade', mission)['passed']:
                raise RuntimeError('Unsolved ' + key + ' diagnostic passed')
            script = mission.solution.replace('sudo apt install tree', 'sudo apt install -y tree').replace('docker stop ', 'docker stop -t 1 ')
            result = engine.channel.request('exec', timeout=65, run_timeout=60, cwd=mission.start,
                                            argv=['bash', '-c', 'set -e\n' + script])
            if result['code']:
                raise RuntimeError(base64.b64decode(result['err']).decode(errors='replace'))
            graded = engine.rpc('grade', mission)
            if not graded['passed']:
                raise RuntimeError(json.dumps(graded, ensure_ascii=False))
        report.update(actual_apt=True, actual_docker_update=True, actual_docker_archive_restore=True,
                      actual_accounts_and_permissions=True, actual_docker_deployment=True, actual_copy_9280=True)
    finally:
        started = time.monotonic()
        engine.close()
        report['close_seconds'] = round(time.monotonic() - started, 2)
    print(json.dumps(report))
    return 0
