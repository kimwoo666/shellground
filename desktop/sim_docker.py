"""Docker state machine. No daemon, network, VM, or host mounts."""
import copy
import hashlib
import io
import json
import shlex
import tarfile
import time
from sim_shell import Result, Shell, Unsupported


class Docker:
    def __init__(self, shell):
        self.host = shell
        self.images = {}
        self.containers = {}
        self.serial = 0
        self.remote = {'ubuntu:latest': '24.04-v1', 'ubuntu:24.04': '24.04-v1', 'alpine:latest': '3.20-v1', 'hello-world:latest': '1', 'nginx:latest': '1.27-v1'}
        self.session = None
        self.loaded_images = set()

    def identifier(self, value):
        self.serial += 1
        return hashlib.sha256((value + str(self.serial)).encode()).hexdigest()

    @staticmethod
    def tag(value): return value if ':' in value.rsplit('/', 1)[-1] else value + ':latest'

    def image(self, value):
        tag = self.tag(value)
        if tag in self.images: return self.images[tag]
        matches = {v['id']: v for v in self.images.values() if v['id'].startswith(value)}
        if len(matches) != 1: raise ValueError('No such image: ' + value)
        return next(iter(matches.values()))

    def container(self, value):
        matches = [v for k, v in self.containers.items() if k == value or v['id'].startswith(value)]
        if len(matches) != 1: raise ValueError('No such container: ' + value)
        return matches[0]

    def pull(self, value):
        tag = self.tag(value)
        if tag not in self.remote: raise Unsupported('image is not in the offline training registry: ' + tag)
        revision = self.remote[tag]
        old = self.images.get(tag)
        if old and old.get('revision') == revision: return f'Status: Image is up to date for {tag}\n'
        image = {'id': hashlib.sha256((tag + revision).encode()).hexdigest(), 'revision': revision, 'files': {}}
        self.images[tag] = image
        return f'{tag}: Pulling from training registry\nDigest: sha256:{image["id"]}\nStatus: Downloaded newer image for {tag}\n'

    def command(self, args, stdin=b''):
        try: return self.run(list(args), stdin)
        except (ValueError, KeyError, IndexError) as exc:
            if isinstance(exc, Unsupported): return Result(err=('simulator: docker: ' + str(exc) + '\n').encode(), code=125)
            return Result(err=('Error response from daemon: ' + str(exc) + '\n').encode(), code=1)

    def run(self, args, stdin):
        self.expire()
        if not args: return Result(b'Usage: docker COMMAND\nCommands: pull images run create ps start stop restart exec attach rm rmi tag commit save load inspect stats container\n')
        action = args.pop(0)
        if action == 'image' and args:
            action = {'ls': 'images', 'rm': 'rmi'}.get(args[0], args[0]); args.pop(0)
        if action == 'container' and args:
            action = {'ls': 'ps'}.get(args[0], args[0]); args.pop(0)
        if action in ('--version', 'version'): return Result(b'Docker CLI compatibility simulator (not an installed Docker Engine)\n')
        if action == 'pull':
            if len(args) != 1: raise ValueError('pull requires exactly 1 argument')
            return Result(self.pull(args[0]).encode())
        if action == 'images':
            if any(a not in ('-q', '-a') for a in args): raise Unsupported('unsupported images option')
            text = '' if '-q' in args else 'REPOSITORY          TAG       IMAGE ID       CREATED          SIZE\n'
            for tag, image in sorted(self.images.items()):
                repo, version = tag.rsplit(':', 1)
                text += image['id'][:12] + '\n' if '-q' in args else f'{repo:20} {version:9} {image["id"][:12]}   simulation       0B (virtual)\n'
            return Result(text.encode())
        if action in ('run', 'create'):
            flags, vals = set(), {'env': [], 'publish': []}
            value_options = {'--name': 'name', '-e': 'env', '--env': 'env', '-p': 'publish', '--publish': 'publish', '--memory': 'memory', '-m': 'memory', '--cpus': 'cpus', '-u': 'user', '--user': 'user'}
            while args and args[0].startswith('-'):
                arg = args.pop(0); key, eq, value = arg.partition('=')
                if key in value_options:
                    if not eq:
                        if not args: raise ValueError('flag needs an argument: ' + key)
                        value = args.pop(0)
                    field = value_options[key]
                    if field in ('env', 'publish'): vals[field].append(value)
                    else: vals[field] = value
                elif key in ('--rm', '-d', '-i', '-t', '-it', '-ti', '-dit', '-dti'):
                    flags.update([key] if key.startswith('--') else ['-' + c for c in key[1:]])
                else: raise Unsupported('unsupported run option: ' + key)
            if not args: raise ValueError('run requires at least 1 argument')
            reference = self.tag(args.pop(0)); output = ''
            if reference not in self.images: output += self.pull(reference)
            image = self.images[reference]
            name = vals.get('name', 'training_' + str(self.serial + 1))
            if not name or not all(c.isalnum() or c in '_.-' for c in name): raise ValueError('Invalid container name')
            if name in self.containers: raise ValueError(f'Conflict. The container name "/{name}" is already in use.')
            if len(self.containers) >= 16: raise Unsupported('16-container training limit reached')
            if 'cpus' in vals and (float(vals['cpus']) <= 0 or float(vals['cpus']) > 64): raise ValueError('invalid CPU limit')
            if 'memory' in vals:
                import re
                if not re.fullmatch(r'[1-9][0-9]*[kKmMgG]?', vals['memory']): raise ValueError('invalid memory limit')
            for port in vals['publish']:
                pair = port.split(':')
                if len(pair) != 2 or not all(n.isdigit() and 0 < int(n) < 65536 for n in pair): raise ValueError('invalid publish specification')
                if any(pair[0] in [x.split(':')[0] for x in c['options']['publish']] for c in self.containers.values() if c['state'] == 'running'): raise ValueError('port is already allocated')
            from sim_engine import base_filesystem
            fs = base_filesystem(); fs.uid = 0
            for path, node in image['files'].items(): fs.nodes[path] = copy.deepcopy(node)
            child = Shell(fs); child.cwd = '/'; child.env.update(HOME='/root', USER='root', PWD='/')
            if 'user' in vals:
                value = vals['user']
                if value in ('learner', '1100'): child.fs.uid = 1100; child.env.update(HOME='/home/learner', USER='learner')
                elif value in ('root', '0'): pass
                elif value.isdigit(): child.fs.uid = int(value); child.env['USER'] = value
                else: raise Unsupported('only root, learner or numeric UID supported')
            for env in vals['env']:
                k, eq, v = env.partition('=')
                if not eq: v = self.host.env.get(k, '')
                child.env[k] = v; child.exported.add(k)
            child.docker = self
            cid = self.identifier(name)
            container = {'id': cid, 'name': name, 'image': image['id'], 'reference': reference, 'state': 'created', 'command': args or (['nginx'] if reference.startswith('nginx:') else ['bash']), 'shell': child, 'options': vals, 'auto_remove': '--rm' in flags, 'interactive': '-i' in flags, 'logs': b''}
            self.containers[name] = container
            if container['command'][:1] == ['sleep']:
                if len(container['command']) != 2 or float(container['command'][1]) < 0: del self.containers[name]; raise ValueError('invalid sleep interval')
                container['deadline'] = time.monotonic() + float(container['command'][1])
            if action == 'create': return Result((output + cid + '\n').encode())
            container['state'] = 'running'
            if '-d' in flags and (container['command'][0] in ('sleep', 'nginx') or '-i' in flags): return Result((output + cid + '\n').encode())
            if '-i' in flags and container['command'][0] in ('bash', 'sh'):
                self.session = (container, False); return Result(output.encode())
            if reference.startswith('hello-world:'): result = Result(b'Hello from Docker!\nThis message shows the simulated container ran successfully.\n')
            elif container['command'] == ['bash']: result = Result()
            else: result = child.execute(shlex.join(container['command']))
            container['logs'] += result.out; self.finish(container)
            return Result(output.encode() + (cid + '\n').encode() if '-d' in flags else output.encode() + result.out, result.err, result.code)
        if action == 'ps':
            if any(a not in ('-a', '-q', '-aq', '-qa', '--all') for a in args): raise Unsupported('unsupported ps option')
            all_ = any(a in ('-a', '-aq', '-qa', '--all') for a in args); quiet = any('q' in a for a in args)
            text = '' if quiet else 'CONTAINER ID   IMAGE          COMMAND         STATUS           PORTS              NAMES\n'
            for c in self.containers.values():
                if not all_ and c['state'] != 'running': continue
                status = {'running': 'Up', 'exited': 'Exited (0)', 'created': 'Created'}[c['state']]
                text += c['id'][:12] + '\n' if quiet else f'{c["id"][:12]}   {c["reference"]:14} {shlex.join(c["command"]):15} {status:16} {",".join(c["options"]["publish"]):18} {c["name"]}\n'
            return Result(text.encode())
        if action in ('stop', 'start', 'restart', 'rm'):
            force = '-f' in args; args = [a for a in args if a != '-f']
            if not args: raise ValueError(action + ' requires a container')
            lines = []
            for value in args:
                c = self.container(value)
                if action == 'rm':
                    if c['state'] == 'running' and not force: raise ValueError('cannot remove a running container: stop the container before removing or force remove')
                    del self.containers[c['name']]
                elif action == 'stop': self.finish(c)
                else:
                    c['state'] = 'running'; c['shell'].exited = False
                    if c['command'][0] == 'sleep': c['deadline'] = time.monotonic() + float(c['command'][1])
                    if not c['interactive'] and c['command'][0] not in ('sleep', 'nginx'): self.finish(c)
                lines.append(value)
            return Result(('\n'.join(lines) + '\n').encode())
        if action in ('exec', 'attach'):
            interactive = False
            while args and args[0].startswith('-'):
                flag = args.pop(0)
                if flag not in ('-it', '-ti', '-i', '-t'): raise Unsupported('unsupported exec option')
                interactive |= 'i' in flag
            if not args: raise ValueError('missing container')
            c = self.container(args.pop(0))
            if c['state'] != 'running': raise ValueError('container is not running')
            if action == 'attach' or (interactive and args in (['bash'], ['sh'])):
                if action == 'attach' and c['command'][0] not in ('bash', 'sh'): raise Unsupported('attaching non-shell processes is not implemented')
                if action == 'exec':
                    child = copy.copy(c['shell']); child.env = c['shell'].env.copy(); child.cwd = '/'; child.exited = False
                    self.session = (dict(c, shell=child), True)
                else: self.session = (c, False)
                return Result()
            if not args: raise ValueError('exec requires a command')
            # Noninteractive exec starts a fresh process at its configured cwd.
            child = copy.copy(c['shell']); child.cwd = '/'; child.env = c['shell'].env.copy(); child.exited = False
            return child.execute(shlex.join(args))
        if action == 'rmi':
            if not args: raise ValueError('missing image')
            lines = []
            for value in args:
                image = self.image(value); tags = [k for k, v in self.images.items() if v['id'] == image['id']]
                target = self.tag(value)
                removes_last = target not in tags or len(tags) == 1
                if removes_last and any(c['image'] == image['id'] for c in self.containers.values()): raise ValueError('conflict: image is being used by a container')
                for tag in [target] if target in tags else tags: del self.images[tag]; lines.append('Untagged: ' + tag)
            return Result(('\n'.join(lines) + '\n').encode())
        if action == 'tag':
            if len(args) != 2: raise ValueError('tag requires 2 arguments')
            if len(self.images) >= 64: raise Unsupported('64-image-tag training limit reached')
            self.images[self.tag(args[1])] = self.image(args[0]); return Result()
        if action == 'commit':
            if len(args) != 2: raise ValueError('commit requires container and repository[:tag]')
            if len(self.images) >= 32: raise Unsupported('32-snapshot training limit reached')
            c = self.container(args[0]); ident = self.identifier(args[1])
            self.images[self.tag(args[1])] = {'id': ident, 'revision': 'local', 'files': copy.deepcopy(c['shell'].fs.nodes)}
            return Result(('sha256:' + ident + '\n').encode())
        if action == 'inspect':
            if len(args) != 1: raise Unsupported('inspect currently takes one name/ID without formatting options')
            try:
                c = self.container(args[0])
                value = {'Id': c['id'], 'Name': '/' + c['name'], 'Image': c['image'], 'State': {'Status': c['state'], 'Running': c['state'] == 'running'}, 'Config': {'Image': c['reference'], 'Env': [k + '=' + v for k, v in c['shell'].env.items()]}, 'HostConfig': c['options']}
            except ValueError:
                img = self.image(args[0]); value = {'Id': 'sha256:' + img['id'], 'RepoTags': [k for k, v in self.images.items() if v['id'] == img['id']]}
            return Result((json.dumps([value], indent=2) + '\n').encode())
        if action == 'logs':
            if len(args) != 1: raise ValueError('logs requires a container')
            return Result(self.container(args[0])['logs'])
        if action == 'prune':
            if args not in (['-f'], ['--force']): raise Unsupported('use container prune -f; interactive confirmation is not implemented')
            names = [k for k, c in self.containers.items() if c['state'] != 'running']
            for name in names: del self.containers[name]
            return Result(('Deleted Containers:\n' + '\n'.join(names) + '\nTotal reclaimed space: 0B (virtual)\n').encode())
        if action == 'save':
            path = None
            if args[:1] in (['-o'], ['--output']): args.pop(0); path = args.pop(0)
            if len(args) != 1: raise ValueError('save requires one image')
            tag = self.tag(args[0]); img = self.image(args[0])
            import base64
            data = {'format': 'shellground-image-v1', 'tag': tag, 'id': img['id'], 'revision': img['revision'], 'files': {k: dict(vars(n), data=base64.b64encode(n.data).decode()) for k, n in img['files'].items()}}
            payload = json.dumps(data).encode(); stream = io.BytesIO()
            with tarfile.open(fileobj=stream, mode='w') as arc:
                member = tarfile.TarInfo('shellground-image.json'); member.size = len(payload); arc.addfile(member, io.BytesIO(payload))
            if path: self.host.fs.write(self.host.path(path), stream.getvalue()); return Result()
            return Result(stream.getvalue())
        if action == 'load':
            if args:
                if len(args) != 2 or args[0] not in ('-i', '--input'): raise ValueError('expected load -i archive')
                stdin = self.host.fs.read(self.host.path(args[1]))
            try:
                with tarfile.open(fileobj=io.BytesIO(stdin), mode='r:*') as arc: data = json.load(arc.extractfile('shellground-image.json'))
                if data['format'] != 'shellground-image-v1': raise ValueError('wrong format')
                import base64
                from sim_fs import Node
                files = {k: Node(**dict(n, data=base64.b64decode(n['data']))) for k, n in data['files'].items()}
                self.images[data['tag']] = {'id': data['id'], 'revision': data['revision'], 'files': files}
                self.loaded_images.add(data['id'])
            except (KeyError, ValueError, tarfile.TarError): raise ValueError('not a Shellground simulated image archive')
            return Result(('Loaded image: ' + data['tag'] + '\n').encode())
        if action == 'stats':
            if '--no-stream' not in args: raise Unsupported('use stats --no-stream; live metrics are not real hardware measurements')
            return Result(('NAME CPU % MEM USAGE / LIMIT (SIMULATED)\n' + ''.join(f'{c["name"]} 0.00% 0B / {c["options"].get("memory", "unlimited")}\n' for c in self.containers.values() if c['state'] == 'running')).encode())
        raise Unsupported('unsupported Docker command: ' + action)

    def finish(self, container):
        container['state'] = 'exited'
        if container['auto_remove']: self.containers.pop(container['name'], None)

    def expire(self):
        for c in list(self.containers.values()):
            if c['state'] == 'running' and c.get('deadline', float('inf')) <= time.monotonic(): self.finish(c)
