"""Exported ROS environment at a real Bash prompt, not /proc startup values."""
import json
import os
import re
from pathlib import Path

sid = os.environ.get('SG_SESSION', '')
if sid.isdigit():
    destination = Path('/tmp/shellground-env-' + sid + '.json')
    data = {key: os.environ[key] for key in (
        'ROS_DISTRO', 'ROS_VERSION', 'ROS_DOMAIN_ID', 'AMENT_PREFIX_PATH', 'COLCON_PREFIX_PATH',
        'TEAM', 'OLD_TEAM', 'HANDOFF', 'AUTH_TEAM', 'LAB_PROJECT', 'CONDA_PREFIX', 'CONDA_SHLVL', 'PATH') if key in os.environ}
    data['cwd'] = os.getcwd()
    try:
        previous = json.loads(destination.read_text())
    except (OSError, ValueError):
        previous = {}
    jobs = previous.get('seen_jobs', {})
    try:
        for line in Path('/tmp/shellground-jobs-' + sid + '.json').read_text().splitlines():
            match = re.match(r'\[(\d+)\][+\- ]*\s+(\d+)\s+', line)
            if match:
                number, pid = match.groups()
                try:
                    stat = Path('/proc/' + pid + '/stat').read_text().rsplit(')', 1)[1].split()
                    jobs[number] = {'pid': int(pid), 'start_ticks': stat[19]}
                except OSError:
                    pass
    except OSError:
        pass
    data['seen_jobs'] = jobs
    if os.environ.get('SG_PRESEEDED') == '1':
        data['initial_jobs'] = previous.get('initial_jobs', dict(jobs))
    temporary = destination.with_suffix('.tmp')
    temporary.write_text(json.dumps(data))
    temporary.replace(destination)
