"""Real Linux/package/Docker outcome checks inside the guarded guest agent."""
import base64
import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import tarfile
import time
import urllib.request
from docker_reports import same_snapshot


class ExtensionLab:
    def __init__(self, agent):
        self.agent = agent
        self.mission = None
        self.initial_ids = {}
        self.initial_images = {}
        self.fixtures = {}
        self.started = time.time()

    def command(self, argv, root=False, timeout=30):
        result = self.agent.run(argv, root=root, cwd=self.mission['start'] if self.mission else '/', timeout=timeout)
        return result['code'], base64.b64decode(result['out']).decode(errors='replace')

    def docker(self, *args, required=False):
        code, output = self.command(['docker', *args], timeout=45)
        if required and code:
            raise RuntimeError('Docker fixture operation failed: ' + ' '.join(args))
        return output if code == 0 else ''

    def inspect(self, noun, reference):
        try:
            return json.loads(self.docker(noun, 'inspect', reference))[0]
        except (ValueError, IndexError):
            return {}

    def containers(self):
        return {c['Name'].lstrip('/'): c for c in (
            self.inspect('container', identity) for identity in self.docker('ps', '-aq').split()) if c}

    def close(self):
        if self.mission and self.key not in ('env', 'author', 'jobs', 'apt', 'review30'):
            identities = self.docker('ps', '-aq').split()
            if identities:
                self.docker('rm', '-f', *identities, required=True)

    def activate_registry(self, version):
        fixture = self.fixtures['ubuntu_' + version]
        request = urllib.request.Request('http://127.0.0.1:5000/v2/training/ubuntu/manifests/24.04',
            method='PUT', data=fixture['raw'].encode(), headers={'Content-Type': fixture['type']})
        with urllib.request.urlopen(request, timeout=10) as response:
            if response.status != 201:
                raise RuntimeError('Training registry tag update failed')

    def prepare(self, mission):
        self.mission = mission
        self.key = mission['review']['extension']
        self.ubuntu = mission['review']['registry']['ubuntu']
        self.alpine = mission['review']['registry']['alpine']
        start = Path(mission['start'])
        start.mkdir(parents=True)
        for path in (start, start.parent):
            os.chown(path, 1100, 1100)
        if self.key in ('apt', 'review30'):
            self.command(['apt-get', 'remove', '-y', 'tree'], root=True)
            # Remove only the local exercise index, not arbitrary system files.
            for path in Path('/var/lib/apt/lists').glob('*shellground*'):
                if path.is_file():
                    path.unlink()
        if self.key not in ('env', 'author', 'jobs', 'apt', 'review30'):
            self.fixtures = json.loads(Path('/opt/shellground/registry-fixtures.json').read_text())
            self.close()
            self.docker('image', 'prune', '-af', required=True)
            self.activate_registry('v1')
            name, other = 'box' + str(mission['seed']), 'keep' + str(mission['seed'])
            if self.key not in ('images', 'run', 'limits', 'review35'):
                self.docker('pull', self.ubuntu, required=True)
            if self.key in ('exec', 'lifecycle', 'cleanup', 'update', 'commit'):
                self.docker('run', '--name', name, '-d', self.ubuntu, 'sleep', '300', required=True)
            if self.key == 'lifecycle':
                self.docker('stop', '-t', '1', name, required=True)
            if self.key in ('lifecycle', 'cleanup', 'review35'):
                self.docker('run', '--name', other, '-d', self.alpine, 'sleep', '300', required=True)
            if self.key in ('update', 'review40'):
                self.activate_registry('v2')
            self.initial_ids = {name: c['Id'] for name, c in self.containers().items()}
            self.initial_images = {ref: self.inspect('image', ref).get('Id') for ref in (self.ubuntu, self.alpine)}
        self.started = time.time()
        return {'ready': True, 'reference': {}}

    def grade(self, mission, sid):
        key = self.key
        start = Path(mission['start'])
        name, other = 'box' + str(mission['seed']), 'keep' + str(mission['seed'])
        checks = []
        def check(label, passed):
            checks.append({'label': label, 'passed': bool(passed)})
        def read(filename):
            try:
                path = start / filename
                info = path.lstat()
                if not stat.S_ISREG(info.st_mode) or info.st_size > 2_000_000: return None
                return path.read_bytes()
            except OSError:
                return None
        try:
            environment = json.loads(Path('/tmp/shellground-env-' + str(sid) + '.json').read_text())
        except (OSError, ValueError):
            environment = {}
        if key in ('env', 'review30'):
            expected = 'review' if key == 'review30' else 'team' + str(mission['seed'])
            check('현재 셸에서 실제 환경변수 export', environment.get('TEAM') == expected)
            check('자식 셸 결과 파일', read('result.txt') == (expected + '\n').encode())
            if key == 'env':
                check('OLD_TEAM 제거', 'OLD_TEAM' not in environment)
        if key == 'author':
            check('스크립트 작성', bool(read('write.sh')))
            check('공백 인자 경로에 결과 저장', read('result file.txt') == b'ready\n')
            # Execute the script with a second path, so a hardcoded filename
            # cannot pass as a working $1-based script.
            probe = start / '.script-check.txt'
            probe.unlink(missing_ok=True)
            code, _ = self.command(['bash', 'write.sh', str(probe)])
            check('다른 인자 경로에도 동작하는 스크립트', code == 0 and read(probe.name) == b'ready\n')
            probe.unlink(missing_ok=True)
        if key in ('apt', 'review30'):
            indices = list(Path('/var/lib/apt/lists').glob('*shellground*Packages'))
            check('실제 패키지 목록 갱신', bool(indices))
            code, text = self.command(['dpkg-query', '-W', '-f=${db:Status-Status}', 'tree'])
            check('실제 tree 패키지 설치', code == 0 and text == 'installed')
        if key in ('jobs', 'review30'):
            jobs = environment.get('seen_jobs', {})
            states = {}
            for number, job in jobs.items():
                try:
                    stat = Path('/proc/' + str(job['pid']) + '/stat').read_text().rsplit(')', 1)[1].split()
                    state = stat[0] if stat[19] == job.get('start_ticks') else 'gone'
                except OSError:
                    state = 'gone'
                states[number] = 'Stopped' if state in ('T', 't') else 'Terminated' if state in ('gone', 'Z') else 'Running'
            target = {'1': 'Stopped'} if key == 'review30' else (
                {'1': 'Running', '2': 'Terminated'} if mission.get('practice') == 2 else {'1': 'Terminated', '2': 'Stopped'})
            check('실제 PID의 실행·중지·종료 상태', states == target)
            if mission.get('practice') == 2:
                check('처음 준비된 작업의 PID 유지', environment.get('initial_jobs') == jobs and len(jobs) == 2)
        if key not in ('env', 'author', 'jobs', 'apt', 'review30'):
            containers = self.containers()
            ubuntu, alpine = self.inspect('image', self.ubuntu), self.inspect('image', self.alpine)
            def running(n):
                return containers.get(n, {}).get('State', {}).get('Running', False)
            def ready(n):
                return self.docker('exec', n, 'cat', '/tmp/note.txt') == 'ready\n'
            if key == 'images':
                check('Ubuntu 이미지 수신', ubuntu.get('Id') == self.fixtures['ubuntu_v1']['id'])
                check('Alpine 이미지 수신', alpine.get('Id') == self.fixtures['alpine']['id'])
                check('컨테이너를 만들지 않음', not containers)
            if key in ('run', 'exec', 'lifecycle', 'update', 'limits', 'review35', 'review40'):
                check('목표 컨테이너 실행 중', running(name))
            if key in ('run', 'limits', 'review35'):
                check('지정 Ubuntu 기반 이미지 사용', containers.get(name, {}).get('Image') == self.fixtures['ubuntu_v1']['id'])
            if key == 'lifecycle':
                check('나머지 컨테이너 종료 상태', containers.get(other, {}).get('State', {}).get('Status') == 'exited')
                check('기존 ID 보존', {n: c['Id'] for n, c in containers.items()} == self.initial_ids)
            if key in ('exec', 'commit', 'review35'):
                check('컨테이너 내부 파일 내용', ready(name))
            if key == 'cleanup':
                check('대상 컨테이너와 이미지 삭제', name not in containers and not ubuntu)
                check('나머지 컨테이너 보존', running(other) and containers[other]['Id'] == self.initial_ids.get(other))
            if key in ('cleanup', 'review35'):
                check('Alpine 이미지 보존', alpine.get('Id') == self.fixtures['alpine']['id'])
            if key == 'review35':
                check('이전 컨테이너 정리', other not in containers)
            if key in ('update', 'review40'):
                check('교육 저장소의 실제 새 이미지 수신', ubuntu.get('Id') == self.fixtures['ubuntu_v2']['id'])
                check('컨테이너가 새 이미지 사용', containers.get(name, {}).get('Image') == self.fixtures['ubuntu_v2']['id'])
            if key == 'tag':
                check('원래 태그와 새 태그가 같은 이미지', bool(ubuntu) and self.inspect('image', 'training:v1').get('Id') == ubuntu.get('Id'))
            if key == 'commit':
                saved = self.inspect('image', 'training:v1')
                verify = 'verify' + str(mission['seed'])
                check('보관한 이미지로 새 컨테이너 실행', bool(saved) and containers.get(verify, {}).get('Image') == saved.get('Id'))
                check('새 컨테이너에 파일 복원', running(verify) and ready(verify))
            if key in ('save', 'review40'):
                expected = self.initial_images.get(self.ubuntu) if key == 'save' else self.fixtures['ubuntu_v2']['id']
                expected_config = self.fixtures['ubuntu_v1' if key == 'save' else 'ubuntu_v2']['config_id']
                valid = False
                try:
                    with tarfile.open(start / 'images.tar', 'r:*') as archive:
                        manifests = json.load(archive.extractfile('manifest.json'))
                        for item in manifests:
                            config = archive.extractfile(item['Config']).read()
                            if ('sha256:' + hashlib.sha256(config).hexdigest() == expected_config and
                                    all(archive.getmember(layer).isfile() for layer in item['Layers'])):
                                valid = True
                except (OSError, tarfile.TarError, KeyError, TypeError, ValueError):
                    pass
                check('실제 Docker 아카이브에 목표 이미지 보관', valid)
                check('목표 이미지가 로컬에 존재', ubuntu.get('Id') == expected)
                if key == 'save':
                    until = datetime.datetime.now(datetime.timezone.utc).isoformat()
                    events = self.docker('events', '--since', str(int(self.started)), '--until', until, '--format', '{{json .}}')
                    loaded = False
                    for line in events.splitlines():
                        try:
                            event = json.loads(line)
                            loaded |= event.get('Action') == 'load' and event.get('Actor', {}).get('ID') == expected
                        except ValueError:
                            pass
                    check('아카이브 복원으로 이미지 로드됨', loaded)
            if key in ('limits', 'review40'):
                container = containers.get(name, {})
                config = container.get('HostConfig', {})
                check('실제 컨테이너 환경변수', 'APP_MODE=training' in container.get('Config', {}).get('Env', []))
                ports = config.get('PortBindings') or {}
                check('포트 8080:80 매핑', any(p.get('HostPort') == '8080' for p in ports.get('80/tcp', [])))
                check('메모리 128 MiB / CPU 1 제한', config.get('Memory') == 128 * 1024 * 1024 and config.get('NanoCpus') == 1000000000)
            if mission.get('practice') == 2:
                for filename, kind, args, label in (
                    ('containers.txt', 'container', ('ps', '-a'), '현재 컨테이너 목록·이름·실행 상태'),
                    ('images.txt', 'image', ('image', 'ls'), '현재 이미지 목록·태그')):
                    content = read(filename)
                    report = content.decode(errors='replace') if content is not None else None
                    current = self.docker(*args, '--no-trunc', '--format', '{{json .}}', required=True)
                    check(label, same_snapshot(report, current, kind))
        if mission.get('practice') == 2 and key in ('env', 'author', 'apt'):
            check('현재 위치 인계', read('location.txt') == (mission['start'] + '\n').encode())
            if key == 'env':
                check('결과 파일 백업', read('backup.txt') == read('result.txt') and read('result.txt') is not None)
        return {'passed': bool(checks) and all(c['passed'] for c in checks), 'checks': checks}
