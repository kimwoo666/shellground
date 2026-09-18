"""Real Docker outcomes in the disposable, guarded guest; never host Docker."""
import base64
import json
import os
from pathlib import Path
import stat
import subprocess
import uuid

IMAGE = 'localhost:5000/training/alpine:latest'


class DockerLab:
    def __init__(self, agent):
        self.agent = agent
        self.mission = None
        self.baseline = None
        self.original_containers = {}
        self.original_volumes = {}
        self.original_images = {}

    def command(self, argv, timeout=30, required=False):
        result = self.agent.run(argv, root=True, cwd='/', timeout=timeout)
        out = base64.b64decode(result['out']).decode(errors='replace')
        err = base64.b64decode(result['err']).decode(errors='replace')
        if required and result['code']:
            raise RuntimeError('Docker 실습 준비 실패: ' + err[-2000:])
        return result['code'], out, err

    def docker(self, *args, required=False, timeout=30):
        return self.command(['/usr/bin/docker', *args], timeout, required)

    def inspect(self, noun, name):
        code, out, _ = self.docker(noun, 'inspect', name)
        if code: return {}
        try: return json.loads(out)[0]
        except (ValueError, IndexError): return {}

    def inventory(self):
        commands = {'containers': ('ps', '-aq', '--no-trunc'),
                    'volumes': ('volume', 'ls', '-q'),
                    'networks': ('network', 'ls', '-q', '--no-trunc'),
                    'images': ('image', 'ls', '-aq', '--no-trunc'),
                    'tags': ('image', 'ls', '--format', '{{.Repository}}:{{.Tag}}')}
        return {key: set(self.docker(*args, required=True)[1].split())
                for key, args in commands.items()}

    def close(self):
        if getattr(self, 'runtime_lab', None):
            self.runtime_lab.close(); self.runtime_lab = None
        if getattr(self, 'session_lab', None):
            self.session_lab.close(); self.session_lab = None
        if self.baseline is None: return
        # The entire daemon is in our private VM. Preserve everything that
        # predates this exercise; no global prune or host Docker is ever used.
        current = self.inventory()
        for key, argv in (('containers', ('rm', '-f')),
                          ('volumes', ('volume', 'rm')),
                          ('networks', ('network', 'rm'))):
            for name in current[key] - self.baseline[key]:
                self.docker(*argv, name, required=True)
        for tag in current['tags'] - self.baseline['tags'] - {'<none>:<none>'}:
            self.docker('image', 'rm', tag)
        # Delete only newly built, unreferenced image IDs, not the Alpine cache.
        for identity in current['images'] - self.baseline['images']:
            self.docker('image', 'rm', identity)
        self.baseline = None

    @staticmethod
    def read(path):
        try:
            info = path.lstat()
            if not stat.S_ISREG(info.st_mode) or info.st_size > 1048576: return None
            return path.read_text()
        except (OSError, UnicodeError): return None

    def volume_path(self, name):
        info = self.inspect('volume', name)
        if not info or info.get('Driver') != 'local': return None
        path = Path(info['Mountpoint'])
        if not path.is_relative_to('/var/lib/docker/volumes'): return None
        return path

    def volume_identity(self, name):
        path = self.volume_path(name)
        try:
            info = path.stat() if path else None
            return (info.st_dev, info.st_ino, self.inspect('volume', name).get('CreatedAt')) if info else None
        except OSError: return None

    def seed_volume(self, name, files):
        self.docker('volume', 'create', name, required=True)
        path = self.volume_path(name)
        if path is None: raise RuntimeError('Docker volume mountpoint unavailable')
        os.chown(path, 1100, 1100)
        path.chmod(0o755)
        for relative, text in files.items():
            file = path / relative
            file.parent.mkdir(parents=True, exist_ok=True)
            file.write_text(text)
            os.chown(file, 1100, 1100)

    def prepare(self, mission):
        if mission['review'].get('docker_runtime'):
            from docker_runtime_lab import RuntimeLab
            self.runtime_lab = RuntimeLab(self.agent)
            self.mission = mission
            return self.runtime_lab.prepare(mission)
        if mission['review'].get('docker_sessions'):
            from docker_sessions_lab import SessionLab
            self.session_lab = SessionLab(self.agent)
            self.mission = mission
            return self.session_lab.prepare(mission)
        from agent import require_guest
        require_guest()
        self.mission = mission
        plan = mission['review']
        self.start = Path(mission['start'])
        if not self.start.is_relative_to('/home/learner/docker'):
            raise ValueError('Docker fixture is outside the training home')
        if not self.inspect('image', IMAGE):
            self.docker('pull', IMAGE, required=True, timeout=45)
        self.baseline = self.inventory()
        self.start.mkdir(parents=True, exist_ok=True)
        for relative, value in plan['files'].items():
            value = {'text': value} if isinstance(value, str) else value
            path = self.start / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(value['text'])
            os.chown(path, value.get('uid', 1100), value.get('gid', 1100))
            path.chmod(value.get('mode', 0o644))
        for path in [Path('/home/learner/docker'), self.start, *self.start.rglob('*')]:
            if path.is_dir():
                os.chown(path, 1100, 1100)
                path.chmod(0o755)
        for relative, meta in plan.get('directory_modes', {}).items():
            path = self.start / relative
            os.chown(path, meta['uid'], meta['gid'])
            path.chmod(meta['mode'])
        self.keep = f"sgd{mission['seed']}-keep"
        self.keep_volume = self.keep + '-data'
        self.keep_network = self.keep + '-net'
        self.keep_text = f"protected {mission['seed']}\n"
        self.seed_volume(self.keep_volume, {'marker.txt': self.keep_text})
        self.docker('network', 'create', self.keep_network, required=True)
        self.docker('run', '-d', '--name', self.keep, '--network', self.keep_network,
                    '-v', self.keep_volume + ':/keep:ro', IMAGE, 'sleep', '3600', required=True)
        self.keep_id = self.inspect('container', self.keep)['Id']
        self.keep_net_id = self.inspect('network', self.keep_network)['Id']
        self.keep_vol_id = self.volume_identity(self.keep_volume)
        for name, files in plan.get('initial_volumes', {}).items(): self.seed_volume(name, files)
        for name in plan.get('initial_networks', []): self.docker('network', 'create', name, required=True)
        for spec in plan.get('initial_images', []):
            if spec['tag'] in self.baseline['tags']: raise RuntimeError('Reserved exercise image already exists')
            self.docker('build', '--network=none', '-t', spec['tag'], str(self.start / spec['context']), required=True, timeout=60)
        for spec in plan.get('initial_containers', []):
            self.docker('run', '-d', '--name', spec['name'], *spec['args'], IMAGE, *spec['command'], required=True)
            if spec.get('wait_exit'):
                self.docker('wait', spec['name'], required=True, timeout=8)
        self.original_containers = {name: self.inspect('container', name).get('Id') for name in plan.get('preserve_containers', [])}
        self.original_volumes = {name: self.volume_identity(name) for name in plan.get('preserve_volumes', [])}
        self.original_images = {name: self.inspect('image', name).get('Id') for name in plan.get('preserve_images', [])}
        return {'ready': True, 'reference': {}}

    def probe_image(self, tag, command=()):
        # A fresh bounded container verifies the built image, not a student's
        # report file. Always remove this owned probe, including on timeout.
        name = 'shellground-probe-' + uuid.uuid4().hex
        try:
            code, out, _ = self.docker('run', '--name', name, '--network', 'none',
                '--memory', '64m', '--cpus', '.5', '--pids-limit', '64', tag, *command, timeout=8)
            return out if code == 0 else None
        except subprocess.TimeoutExpired:
            return None
        finally:
            self.docker('rm', '-f', name)

    def container_user_matches(self, name, info, expected):
        if info.get('Config', {}).get('User') == expected: return True
        # Also accept an equivalent named account or numeric UID with a
        # correctly resolved primary group, rather than matching CLI text.
        if not info.get('State', {}).get('Running'): return False
        values = []
        for flag in ('-u', '-g'):
            try:
                code, out, _ = self.docker('exec', name, 'id', flag, timeout=5)
            except subprocess.TimeoutExpired: return False
            if code: return False
            values.append(out.strip())
        return ':'.join(values) == expected

    def grade(self, mission):
        if getattr(self, 'runtime_lab', None): return self.runtime_lab.grade(mission)
        if getattr(self, 'session_lab', None): return self.session_lab.grade(mission)
        plan = mission['review']
        checks = []
        def check(label, passed): checks.append({'label': label, 'passed': bool(passed)})
        for relative, expected in plan.get('file_goals', {}).items():
            check(relative + ' 내용', self.read(self.start / relative) == expected)
        for relative, expected in plan.get('contains_goals', {}).items():
            check(relative + ' 장애 기록', expected in (self.read(self.start / relative) or ''))
        for field in ('metadata_goals', 'directory_goals'):
            for relative, meta in plan.get(field, {}).items():
                try:
                    s = (self.start / relative).lstat()
                    good = stat.S_ISDIR(s.st_mode) if field == 'directory_goals' else stat.S_ISREG(s.st_mode)
                    good = good and (s.st_uid, s.st_gid, stat.S_IMODE(s.st_mode)) == (meta['uid'], meta['gid'], meta['mode'])
                except OSError: good = False
                check(relative + ' 소유권·권한', good)
        cache = {spec['name']: self.inspect('container', spec['name']) for spec in plan.get('containers', [])}
        for spec in plan.get('containers', []):
            name = spec['name']
            info = cache[name]
            config = info.get('Config', {})
            check(name + ' 실행·이미지', info.get('State', {}).get('Running') == spec['running'] and
                  bool(info.get('Image')) and info.get('Image') == self.inspect('image', spec['image']).get('Id'))
            if 'user' in spec: check(name + ' UID/GID', self.container_user_matches(name, info, spec['user']))
            mounts = {m['Destination']: m for m in info.get('Mounts', [])}
            for expected in spec.get('mounts', []):
                actual = mounts.get(expected['destination'], {})
                check(name + ' ' + expected['destination'] + ' 마운트·접근 권한',
                    actual.get('Type') == expected['type'] and actual.get('RW') == expected['rw'] and
                    actual.get('Name' if expected['type'] == 'volume' else 'Source') == expected['source'])
            networks = info.get('NetworkSettings', {}).get('Networks', {})
            if 'network' in spec:
                check(name + ' 네트워크·별칭', spec['network'] in networks and
                      ('alias' not in spec or spec['alias'] in (networks[spec['network']].get('Aliases') or [])))
        for network in plan.get('networks', []):
            check(network + ' bridge', self.inspect('network', network).get('Driver') == 'bridge')
        for name, forbidden in plan.get('forbidden_networks', {}).items():
            actual = self.inspect('container', name).get('NetworkSettings', {}).get('Networks', {})
            check(name + ' 이전 연결 제거', all(n not in actual for n in forbidden))
        for item in plan.get('connections', []):
            try:
                code, _, _ = self.docker('exec', item['from'], 'ping', '-c', '1', '-W', '2', item['to'], timeout=5)
            except subprocess.TimeoutExpired: code = 1
            check(item['from'] + ' → ' + item['to'] + ' 실제 통신', code == 0)
        for volume, files in plan.get('volume_goals', {}).items():
            path = self.volume_path(volume)
            for relative, expected in files.items():
                check(volume + '/' + relative + ' 데이터', path is not None and self.read(path / relative) == expected)
        for name, text in plan.get('log_goals', {}).items():
            code, out, err = self.docker('logs', name)
            check(name + ' 정상 로그', code == 0 and text in out + err)
        for spec in plan.get('image_goals', []):
            info = self.inspect('image', spec['tag'])
            config = info.get('Config', {})
            good = bool(info)
            for key, field in (('workdir', 'WorkingDir'),):
                if key in spec: good = good and config.get(field) == spec[key]
            if 'user' in spec and config.get('User') != spec['user']:
                ids = [self.probe_image(spec['tag'], ('id', flag)) if info else None for flag in ('-u', '-g')]
                good = good and all(value is not None for value in ids) and ':'.join(value.strip() for value in ids if value is not None) == spec['user']
            if 'environment' in spec: good = good and spec['environment'] in (config.get('Env') or [])
            check(spec['tag'] + ' 이미지 설정', good)
            if 'output' in spec:
                check(spec['tag'] + ' 새 컨테이너 기본 실행', bool(info) and self.probe_image(spec['tag']) == spec['output'])
            if 'stamp' in spec:
                check(spec['tag'] + ' 빌드 결과물', bool(info) and self.probe_image(spec['tag'], ('cat', '/build-stamp')) == spec['stamp'])
        for noun, field in (('container', 'absent_containers'), ('volume', 'absent_volumes'), ('network', 'absent_networks')):
            for name in plan.get(field, []): check(name + ' 제거', not self.inspect(noun, name))
        for name, identity in self.original_containers.items():
            check(name + ' 기존 ID 보존', bool(identity) and self.inspect('container', name).get('Id') == identity)
        for name, identity in self.original_volumes.items():
            check(name + ' 기존 볼륨 유지', bool(identity) and self.volume_identity(name) == identity)
        for name, identity in self.original_images.items():
            check(name + ' 기존 이미지 보존', bool(identity) and self.inspect('image', name).get('Id') == identity)
        keep = self.inspect('container', self.keep)
        path = self.volume_path(self.keep_volume)
        check('보호용 컨테이너·볼륨·네트워크 보존',
            keep.get('Id') == self.keep_id and keep.get('State', {}).get('Running') and
            self.keep_network in keep.get('NetworkSettings', {}).get('Networks', {}) and
            any(m.get('Name') == self.keep_volume and m.get('Destination') == '/keep' and not m.get('RW') for m in keep.get('Mounts', [])) and
            self.inspect('network', self.keep_network).get('Id') == self.keep_net_id and
            self.volume_identity(self.keep_volume) == self.keep_vol_id and path is not None and
            self.read(path / 'marker.txt') == self.keep_text)
        return {'passed': bool(checks) and all(c['passed'] for c in checks), 'checks': checks}
