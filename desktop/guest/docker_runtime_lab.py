"""Actual private-guest Docker/HTTP/cgroup observations, without load benchmarks."""
import hashlib
import json
import math
import os
from pathlib import Path
import re
import stat
import subprocess
import tempfile
import time
import urllib.error
import urllib.request
import uuid

if __package__:
    from .docker_lab import DockerLab, IMAGE
else:
    from docker_lab import DockerLab, IMAGE


HTTP_SCRIPT = '''#!/bin/sh
IFS= read -r request || exit 0
while IFS= read -r header; do
    [ "$header" = "$(printf '\\r')" ] || [ -z "$header" ] && break
done
case "$request" in
    'GET /health.txt HTTP/'*)
        if [ -f /www/health.txt ]; then
            length=$(wc -c < /www/health.txt)
            printf 'HTTP/1.1 200 OK\\r\\nContent-Type: text/plain\\r\\nContent-Length: %s\\r\\nConnection: close\\r\\n\\r\\n' "$length"
            cat /www/health.txt
        else
            printf 'HTTP/1.1 404 Not Found\\r\\nContent-Length: 10\\r\\nConnection: close\\r\\n\\r\\nnot found\\n'
        fi ;;
    *) printf 'HTTP/1.1 404 Not Found\\r\\nContent-Length: 10\\r\\nConnection: close\\r\\n\\r\\nnot found\\n' ;;
esac
'''


def cpus(text):
    result = set()
    try:
        for item in text.strip().split(','):
            bounds = item.split('-'); low = int(bounds[0]); high = int(bounds[-1])
            if len(bounds) > 2 or low < 0 or high < low or high - low > 4096: return None
            result.update(range(low, high + 1))
        return result
    except (ValueError, AttributeError): return None


def quota_matches(text, expected):
    try:
        quota, period = text.split()
        if int(period) <= 0: return False
        return quota == 'max' if expected is None else quota != 'max' and int(quota) / int(period) == expected
    except (ValueError, AttributeError): return False


def memory_bytes(value):
    match = re.fullmatch(r'(\d+(?:\.\d+)?)\s*(B|KiB|MiB|GiB|TiB)', value.strip())
    if not match: return None
    result = float(match[1]) * 1024 ** ('B', 'KiB', 'MiB', 'GiB', 'TiB').index(match[2])
    return result if math.isfinite(result) else None


def io_quantities(value):
    pairs = value.split('/')
    return len(pairs) == 2 and all(re.fullmatch(r'\d+(?:\.\d+)?\s*(?:B|kB|MB|GB|TB|KiB|MiB|GiB|TiB)', p.strip()) and
                                  math.isfinite(float(re.match(r'[\d.]+', p.strip())[0])) for p in pairs)


def output_snapshot(folder):
    result = {}
    for path in folder.rglob('*'):
        info = path.lstat()
        if not stat.S_ISREG(info.st_mode) or info.st_size > 1048576: return None
        result[str(path.relative_to(folder))] = (hashlib.sha256(path.read_bytes()).hexdigest(), stat.S_IMODE(info.st_mode), info.st_uid, info.st_gid)
    return result


def safe_security(options):
    options = set(options or [])
    return bool(options & {'no-new-privileges', 'no-new-privileges=true'}) and not options - {
        'no-new-privileges', 'no-new-privileges=true', 'apparmor=docker-default'}


def valid_stats(text, name, identity, limit):
    """Check a submitted snapshot's structure/identity/limit, not fresh usage equality.

    Reports cannot prove historical CLI execution. Actual object settings are
    checked independently. No live value is invented or required to stay fixed.
    """
    if not text: return False
    rows = text.strip().splitlines()
    if len(rows) != 2 or 'MEM USAGE / LIMIT' not in rows[0] or 'PIDS' not in rows[0]: return False
    values = re.split(r'\s{2,}', rows[1].strip())
    if len(values) != 8 or values[1] != name or not identity.startswith(values[0]) or len(values[0]) < 12: return False
    try:
        usage, maximum = values[3].split('/')
        used = memory_bytes(usage); bound = memory_bytes(maximum)
        percentages = [float(values[i].removesuffix('%')) for i in (2, 4)]
        return (used is not None and used >= 0 and bound == limit and
                all(math.isfinite(n) and n >= 0 for n in percentages) and
                values[2].endswith('%') and values[4].endswith('%') and
                io_quantities(values[5]) and io_quantities(values[6]) and int(values[7]) >= 1)
    except (ValueError, TypeError): return False


class RuntimeLab(DockerLab):
    def seed_file(self, relative, value, protected=False, mode=0o644):
        path = self.start / relative; path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(value); path.chmod(mode); os.chown(path, 0 if protected else 1100, 0 if protected else 1100)
        for folder in path.parents:
            if folder == self.start: break
            if folder.is_relative_to(self.start): folder.chmod(0o755); os.chown(folder, 1100, 1100)
        if protected: self.protected[path] = (hashlib.sha256(path.read_bytes()).hexdigest(), mode)
        return path

    def prepare(self, mission):
        from agent import require_guest
        require_guest()
        seed = mission['seed']; p = mission['review']; key = p['docker_runtime']; v = mission['practice']
        if (type(seed) is not int or not 0 <= seed <= 9999 or type(v) is not int or v not in (0, 1, 2) or
            key not in ('http', 'stats', 'cpu', 'io_weight', 'safe_launcher', 'review') or
            mission['start'] != f'/home/learner/docker/runtime{seed}' or p['name'] != f'sgr{seed}-task' or p['port'] != 40000 + seed):
            raise ValueError('Invalid owned Docker runtime fixture')
        self.base_mission = dict(mission, review={'docker_real': 'runtime', 'files': {'keep.txt': 'keep document\n', 'output/.keep': 'keep output\n'},
                                                'file_goals': {'keep.txt': 'keep document\n', 'output/.keep': 'keep output\n'}})
        super().prepare(self.base_mission)
        self.baseline_tags = {tag: self.inspect('image', tag).get('Id') for tag in self.baseline['tags'] if tag != '<none>:<none>'}
        self.mission = mission; self.key = key; self.variant = v; self.name = p['name']; self.port = p['port']
        self.protected = {}; self.preserved = {}; self.health = f'healthy {seed}\n'; self.payload = f'input data {seed}\n'
        self.image_id = self.inspect('image', IMAGE)['Id']
        self.allowed = cpus(Path('/sys/fs/cgroup/cpuset.cpus.effective').read_text())
        info = json.loads(self.docker('info', '--format', '{{json .}}', required=True)[1])
        if info.get('CgroupVersion') != '2' or not self.allowed:
            raise RuntimeError('이 자원 과정은 확인된 cgroup v2 guest가 필요합니다. 적용 성공으로 처리하지 않습니다.')
        self.target_cpu = min(self.allowed)
        self.seed_file('available-cpus.txt', ','.join(map(str, sorted(self.allowed))) + '\n', True)
        self.seed_file('target-cpu.txt', str(self.target_cpu) + '\n', True)
        self.seed_file('source-health.txt', self.health, True)
        self.seed_file('server/http-response.sh', HTTP_SCRIPT, True, 0o755)
        self.seed_file('www/keep.txt', 'keep web document\n', True)
        if not (key == 'http' and v == 1): self.seed_file('www/health.txt', self.health, True)
        self.seed_file('input/source notes.txt', self.payload, True)
        self.seed_file('output/result.txt', 'previous result\n')
        self.seed_file('equipment.txt', self.command(['sh', '-c', 'ls -ld /dev/dri /dev/nvidia* /tmp/.X11-unix 2>&1; printf "DISPLAY=%s\\n" "$DISPLAY"; true'], required=True)[1] +
                       'CPU 파일 처리만 시험합니다. 장치 접근·GPU 계산·X11 표시는 별도로 실행하지 않았습니다.\n', True)
        self.seed_file('unsafe-draft.txt', '# 실행하지 말고 검토할 초안: 입력 검사 없음, 인자 인용 없음, 불필요한 root/privileged\ndocker run --privileged -v $1:/in.txt -v $2:/out alpine sh\n', True)
        if key == 'http' and v:
            self.start_http('0.0.0.0' if v == 2 else '127.0.0.1')
            self.initial_http = self.inspect('container', self.name)
            # A real 404 fixture, not a fabricated error transcript.
            observed = self.http_response()
            if observed != ((404, 'not found\n') if v == 1 else (200, self.health)):
                raise RuntimeError('Actual HTTP fixture not ready: ' + repr(observed))
        if key == 'stats':
            self.start_wait(self.name, memory='32m')
            if v == 1: self.start_wait(self.name + '-large', memory='96m')
            if v == 2:
                self.docker('stop', '-t', '1', self.name, required=True)
                self.seed_file('status.txt', 'running\n'); self.seed_file('memory-limit.txt', '0\n'); self.seed_file('usage.txt', '0B\n')
            for name in [self.name] + ([self.name + '-large'] if v == 1 else []): self.preserved[name] = self.identity(name)
        if key == 'cpu' and v == 2: self.start_wait(self.name, extra=('--cpuset-cpus', str(self.target_cpu)), cpulimit=False)
        if key in ('io_weight', 'review'):
            runtime_version = self.docker('version', '--format', '{{json .Server.Components}}', required=True)[1]
            if not any(row.get('Name') == 'runc' and row.get('Version', '').startswith('1.3.4') for row in json.loads(runtime_version)):
                raise RuntimeError('I/O 변환 검증 범위 밖의 runtime입니다. 적용값을 추측하지 않습니다.')
            details = self.command(['sh', '-c', 'cat /sys/fs/cgroup/cgroup.controllers; for f in /sys/block/vd*/queue/scheduler; do printf "%s: " "$f"; cat "$f"; done'], required=True)[1]
            self.seed_file('io-environment.txt', 'cgroup v2\n' + runtime_version + '\n' + details + '\n성능 효과는 미측정입니다.\n', True)
            # Bounded real interface probe, removed immediately.
            probe = 'sgr-interface-' + uuid.uuid4().hex
            try:
                self.start_wait(probe, extra=('--blkio-weight', '300'))
                if not self.io_applied(self.inspect('container', probe), 300):
                    raise RuntimeError('가중치 제어 파일 적용을 확인할 수 없습니다. 단원을 자동 통과시키지 않습니다.')
            finally: self.docker('rm', '-f', probe)
            if key == 'io_weight' and v == 2:
                self.start_wait(self.name, extra=('--blkio-weight', '600')); self.preserved[self.name] = self.identity(self.name)
                self.seed_file('effect.txt', '600MB/s guaranteed\n')
        return {'ready': True, 'reference': {}}

    def start_wait(self, name, extra=(), memory='32m', cpulimit=True):
        self.docker('run', '-d', '--name', name, '--network', 'none', '--memory', memory, '--pids-limit', '32',
                    *(['--cpus', '.25'] if cpulimit else []), *extra, IMAGE, 'sleep', '3600', required=True)

    def start_http(self, address):
        self.docker('run', '-d', '--name', self.name, '--memory', '32m', '--cpus', '.25', '--pids-limit', '32',
                    '-p', f'{address}:{self.port}:8080', '--mount', f'type=bind,src={self.start}/server,dst=/srv,readonly',
                    '--mount', f'type=bind,src={self.start}/www,dst=/www,readonly', IMAGE,
                    'nc', '-lk', '-p', '8080', '-e', '/srv/http-response.sh', required=True)

    def http_response(self):
        for attempt in range(10):
            try:
                # No proxies or host/network requests: private guest loopback only.
                opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
                with opener.open(f'http://127.0.0.1:{self.port}/health.txt', timeout=2) as response:
                    return response.status, response.read(4096).decode()
            except urllib.error.HTTPError as error: return error.code, error.read(4096).decode(errors='replace')
            except (OSError, UnicodeError):
                if attempt == 9: return None
                time.sleep(.05)

    def identity(self, name):
        info = self.inspect('container', name)
        return (info.get('Id'), info.get('State'), info.get('HostConfig'), info.get('Config'))

    def cgroup(self, info):
        pid = info.get('State', {}).get('Pid', 0)
        if type(pid) is not int or pid <= 0: return None
        try:
            relative = next(line[3:] for line in Path(f'/proc/{pid}/cgroup').read_text().splitlines() if line.startswith('0::'))
            path = (Path('/sys/fs/cgroup') / relative.lstrip('/')).resolve()
            if not path.is_relative_to('/sys/fs/cgroup'): return None
            return path
        except (OSError, StopIteration): return None

    def cpu_applied(self, info, quota, affinity):
        path = self.cgroup(info)
        try:
            host = info.get('HostConfig', {})
            configured = host.get('NanoCpus', 0) / 1e9 if host.get('NanoCpus') else (host.get('CpuQuota', 0) / (host.get('CpuPeriod', 0) or 100000) if host.get('CpuQuota', 0) > 0 else None)
            chosen = cpus(host.get('CpusetCpus', '')) if host.get('CpusetCpus') else None
            return (configured == quota and chosen == affinity and path is not None and
                    quota_matches((path / 'cpu.max').read_text(), quota) and
                    cpus((path / 'cpuset.cpus.effective').read_text()) == (affinity or self.allowed))
        except OSError: return False

    def io_applied(self, info, weight):
        if info.get('HostConfig', {}).get('BlkioWeight') != weight: return False
        path = self.cgroup(info)
        if path is None: return False
        try:
            bfq = path / 'io.bfq.weight'
            text = (bfq if bfq.is_file() else path / 'io.weight').read_text().strip()
            target = weight if bfq.is_file() else 1 + (weight - 10) * 9999 // 990
            return text in (str(target), f'default {target}')
        except OSError: return False

    def wait_config(self, info):
        host = info.get('HostConfig', {})
        return bool(info.get('State', {}).get('Running') and info.get('Image') == self.image_id and
                    host.get('NetworkMode') == 'none' and host.get('Memory') == 33554432 and host.get('PidsLimit') == 32)

    def http_good(self):
        info = self.inspect('container', self.name); host = info.get('HostConfig', {})
        maps = host.get('PortBindings') or {}; mounts = {m['Destination']: m for m in info.get('Mounts', [])}
        good = bool(info.get('State', {}).get('Running') and info.get('Image') == self.image_id and maps == {'8080/tcp': [{'HostIp': '127.0.0.1', 'HostPort': str(self.port)}]} and len(mounts) == 2)
        for destination, source in (('/srv', 'server'), ('/www', 'www')):
            m = mounts.get(destination, {}); good = good and m.get('Type') == 'bind' and m.get('Source') == str(self.start / source) and not m.get('RW', True)
        if self.key == 'http' and self.variant == 1:
            good = good and info.get('Id') == self.initial_http['Id'] and info.get('State', {}).get('StartedAt') == self.initial_http['State']['StartedAt']
        if self.key == 'http' and self.variant == 2: good = good and info.get('Id') != self.initial_http['Id']
        return good and self.http_response() == (200, self.health) and self.read(self.start / 'response.txt') == self.health and self.read(self.start / 'www/health.txt') == self.health

    def safe_result(self, name, source, output, expected):
        info = self.inspect('container', name); state = info.get('State', {}); host = info.get('HostConfig', {}); config = info.get('Config', {})
        security = set(host.get('SecurityOpt') or [])
        mounts = {m['Destination']: m for m in info.get('Mounts', [])}
        good = bool(info and info.get('Image') == self.image_id and state.get('Status') == 'exited' and
                    not state.get('Running') and state.get('ExitCode') == 0 and
                    state.get('StartedAt', '').startswith('20') and state.get('FinishedAt', '').startswith('20') and
                    config.get('User') == '1100:1100' and host.get('NetworkMode') == 'none' and host.get('ReadonlyRootfs') and
                    set(host.get('CapDrop') or []) == {'ALL'} and not host.get('CapAdd') and not host.get('Privileged') and
                    not host.get('Devices') and not host.get('DeviceRequests') and not host.get('DeviceCgroupRules') and
                    host.get('PidMode') != 'host' and host.get('IpcMode') != 'host' and not host.get('Tmpfs') and
                    safe_security(security) and
                    host.get('Memory') == 33554432 and host.get('PidsLimit') == 32 and
                    (host.get('NanoCpus') == 250000000 or (host.get('CpuQuota', 0) > 0 and host.get('CpuQuota') / (host.get('CpuPeriod') or 100000) == .25)) and len(mounts) == 2)
        for destination, path, rw in (('/in.txt', source, False), ('/out', output, True)):
            m = mounts.get(destination, {}); good = good and m.get('Type') == 'bind' and m.get('Source') == str(path) and m.get('RW') is rw
        for relative, value in (('result.txt', expected), ('uid.txt', '1100\n'), ('gid.txt', '1100\n')):
            path = output / relative
            try: good = good and self.read(path) == value and (path.lstat().st_uid, path.lstat().st_gid) == (1100, 1100)
            except OSError: good = False
        return good

    def launcher_probe(self):
        script = self.start / 'run-job.sh'
        try:
            mode = script.lstat().st_mode
            if not stat.S_ISREG(mode) or not mode & 0o100 or script.stat().st_size > 65536: return False
        except OSError: return False
        names = ['sgr-probe-' + uuid.uuid4().hex for _ in range(2)]
        with tempfile.TemporaryDirectory(prefix='new input ', dir=self.start) as folder:
            root = Path(folder); root.chmod(0o755); os.chown(root, 1100, 1100)
            source = root / 'another source.txt'; expected = uuid.uuid4().hex + '\n'; source.write_text(expected); source.chmod(0o444)
            output = root / 'another output'; output.mkdir(); os.chown(output, 1100, 1100)
            (output / 'unrelated.txt').write_text('preserve this too\n')
            try:
                result = self.agent.run([str(script), str(source), str(output), names[0]], root=False, cwd=str(self.start), timeout=12)
                good = result['code'] == 0 and self.safe_result(names[0], source, output, expected) and source.read_text() == expected
                before = output_snapshot(output)
                result = self.agent.run([str(script), str(root / 'missing input'), str(output), names[1]], root=False, cwd=str(self.start), timeout=12)
                return good and before is not None and result['code'] != 0 and not self.inspect('container', names[1]) and output_snapshot(output) == before
            except (OSError, TimeoutError, subprocess.TimeoutExpired): return False
            finally:
                for name in names: self.docker('rm', '-f', name)

    def grade(self, mission):
        key = self.key; v = self.variant; checks = []
        def check(label, value): checks.append(dict(label=label, passed=bool(value)))
        info = self.inspect('container', self.name)
        if key in ('http', 'review'): check('loopback 공개·읽기 전용 문서·실제 HTTP 200과 본문', self.http_good())
        if key == 'stats':
            same = all(self.identity(name) == original for name, original in self.preserved.items())
            if v == 2:
                good = self.read(self.start / 'status.txt') == 'exited\n' and self.read(self.start / 'memory-limit.txt') == '33554432\n' and self.read(self.start / 'usage.txt') == 'unobserved\n'
            else:
                good = valid_stats(self.read(self.start / 'stats.txt'), self.name, info.get('Id', ''), 33554432)
                good = good and self.read(self.start / ('selected.txt' if v == 1 else 'memory-limit.txt')) == (self.name if v == 1 else '33554432') + '\n'
            check('실제 대상·순간 통계와 설정 한도 구별·원래 상태 유지', same and good)
        if key in ('cpu', 'review'):
            target = self.inspect('container', self.name + '-worker') if key == 'review' else info
            quota = .25 if key == 'review' or v == 2 else None if v == 1 else .5
            affinity = None if key == 'cpu' and v == 0 else {self.target_cpu}
            check('시간 상한·유효 CPU 집합·대기 작업 설정', self.wait_config(target) and self.cpu_applied(target, quota, affinity))
        if key in ('io_weight', 'review'):
            pairs = [(self.name + '-worker', 300)] if key == 'review' else [(self.name, 600 if v == 2 else 300)] + ([(self.name + '-high', 600)] if v == 1 else [])
            good = True
            for name, weight in pairs:
                target = self.inspect('container', name)
                good = good and self.wait_config(target) and self.io_applied(target, weight)
                good = good and self.cpu_applied(target, .25, {self.target_cpu} if key == 'review' else None)
            good = good and self.read(self.start / 'effect.txt') == 'effect=unmeasured\n'
            if key == 'io_weight' and v == 2: good = good and self.identity(self.name) == self.preserved[self.name] and self.read(self.start / 'requested.txt') == '600\n'
            check('요청 가중치·실제 제어 파일·성능 미측정 구분', good)
        if key == 'review':
            worker = self.inspect('container', self.name + '-worker')
            check('worker 현재 통계와 설정 한도', valid_stats(self.read(self.start / 'stats.txt'), self.name + '-worker', worker.get('Id', ''), 33554432))
        if key in ('safe_launcher', 'review'):
            name = self.name + '-job' if key == 'review' else self.name
            good = self.safe_result(name, self.start / 'input/source notes.txt', self.start / 'output', self.payload)
            good = good and self.launcher_probe()
            if key == 'safe_launcher' and v == 1: good = good and self.read(self.start / 'previous-result.txt') == 'previous result\n'
            if key == 'safe_launcher' and v == 2: good = good and self.read(self.start / 'equipment-status.txt') == 'device=unverified\ngpu=unexecuted\nx11=unexecuted\n'
            check('최소 권한 실행·새 공백 경로·입력 부재의 비파괴 실패', good)
        base = super().grade(self.base_mission)
        protected = True
        for path, (digest, mode) in self.protected.items():
            try: protected = protected and self.read(path) is not None and hashlib.sha256(path.read_bytes()).hexdigest() == digest and stat.S_IMODE(path.lstat().st_mode) == mode
            except OSError: protected = False
        inv = self.inventory()
        protected = protected and all(self.baseline[k] <= inv[k] for k in ('tags', 'containers', 'volumes', 'networks'))
        protected = protected and all(self.inspect('image', tag).get('Id') == identity for tag, identity in self.baseline_tags.items())
        check('보호 문서·서버·입력·기존 이미지와 Docker 객체 보존', base['passed'] and protected)
        try: returned = all(os.tcgetpgrp(session['fd']) == session['pid'] for session in self.agent.sessions.values())
        except OSError: returned = False
        check('전용 Linux 셸로 복귀', returned)
        return dict(passed=all(row['passed'] for row in checks), checks=checks)
