"""Virtual accounts and ownership. No host accounts, passwd files, or commands."""
import copy
import posixpath as p
import re
from sim_fs import Node


class Accounts:
    def __init__(self, fs):
        self.fs = fs
        self.groups = {'root': 0, 'learner': 1100, 'sudo': 27}
        self.users = {
            'root': {'uid': 0, 'gid': 0, 'home': '/root', 'shell': '/bin/bash', 'groups': ['root']},
            'learner': {'uid': 1100, 'gid': 1100, 'home': '/home/learner', 'shell': '/bin/bash', 'groups': ['learner', 'sudo']}}

    def username(self, uid): return next((n for n, u in self.users.items() if u['uid'] == uid), str(uid))
    def groupname(self, gid): return next((n for n, value in self.groups.items() if value == gid), str(gid))
    def group_id(self, name): return self.groups.get(name)
    def user_info(self, name): return copy.deepcopy(self.users.get(name))

    def file_info(self, path):
        try:
            n = self.fs.get(path, False)
            return {'type': n.kind, 'text': n.data.decode(errors='replace') if n.kind == 'file' else '',
                    'mode': n.mode, 'uid': n.uid, 'gid': n.gid}
        except OSError: return None

    def user(self, name):
        if name.isdigit(): name = self.username(int(name))
        if name not in self.users: raise ValueError('no such user: ' + name)
        return name, self.users[name]

    def group(self, name):
        if name.isdigit():
            number = int(name)
            if number in self.groups.values(): return self.groupname(number), number
        if name not in self.groups: raise ValueError('group does not exist: ' + name)
        return name, self.groups[name]

    def sync(self):
        passwd = ''.join(f'{n}:x:{u["uid"]}:{u["gid"]}::{u["home"]}:{u["shell"]}\n' for n, u in self.users.items())
        groups = ''.join(f'{n}:x:{gid}:' + ','.join(name for name, u in self.users.items() if n in u['groups'] and u['gid'] != gid) + '\n' for n, gid in self.groups.items())
        self.fs.put('/etc/passwd', Node(data=passwd.encode(), uid=0, gid=0))
        self.fs.put('/etc/group', Node(data=groups.encode(), uid=0, gid=0))

    def add_user(self, name, user, create_home):
        if name in self.users: raise ValueError('user already exists: ' + name)
        if any(u['uid'] == user['uid'] for u in self.users.values()): raise ValueError('UID is not unique')
        if not re.fullmatch('[a-z_][a-z0-9_-]*', name): raise ValueError('invalid user name')
        if not user['home'].startswith('/') or not user['shell'].startswith('/'): raise ValueError('home and shell must be absolute paths')
        self.users[name] = copy.deepcopy(user)
        if create_home:
            if not self.fs.exists(user['home']):
                self.fs.mkdir(user['home'], True)
                node = self.fs.get(user['home'])
                node.uid, node.gid, node.mode = user['uid'], user['gid'], 0o750
        self.sync()


def accounts(fs):
    if not hasattr(fs, 'accounts'): fs.accounts = Accounts(fs)
    return fs.accounts


COMMANDS = {'whoami', 'id', 'groups', 'getent', 'groupadd', 'useradd', 'usermod', 'chown', 'chgrp'}


def command(shell, name, args):
    from sim_shell import Result, options
    fs, db = shell.fs, accounts(shell.fs)
    if name in ('useradd', 'usermod', 'groupadd') and fs.uid != 0:
        raise PermissionError('Permission denied')
    out = ''
    if name == 'whoami':
        if args: raise ValueError('extra operand')
        out = db.username(fs.uid) + '\n'
    elif name == 'id':
        flags, _, operands = options(args, 'ugGnr')
        if len(operands) > 1: raise ValueError('extra operand')
        choices = flags & set('ugG')
        if len(choices) > 1 or (flags & set('nr') and not choices): raise ValueError('invalid option combination')
        if operands:
            username, user = db.user(operands[0])
            uid, gid = user['uid'], user['gid']
            gids = [gid] + sorted({db.groups[g] for g in user['groups']} - {gid})
        else:
            uid, gid = fs.uid, fs.gid
            username = db.username(uid)
            gids = [gid] + sorted(set(fs.groups) - {gid})
        if 'u' in flags: out = username if 'n' in flags else str(uid)
        elif 'g' in flags: out = db.groupname(gid) if 'n' in flags else str(gid)
        elif 'G' in flags: out = ' '.join(db.groupname(g) if 'n' in flags else str(g) for g in gids)
        else: out = f'uid={uid}({username}) gid={gid}({db.groupname(gid)}) groups=' + ','.join(f'{g}({db.groupname(g)})' for g in gids)
        out += '\n'
    elif name == 'groups':
        if not args:
            out = command(shell, 'id', ['-Gn']).out.decode()
        else:
            out = ''.join(n + ' : ' + command(shell, 'id', ['-Gn', n]).out.decode() for n in args)
    elif name == 'getent':
        if not args or args[0] not in ('passwd', 'group'): raise ValueError('supported databases: passwd, group')
        db.sync()
        records = fs.nodes['/etc/' + args[0]].data.decode().splitlines()
        if len(args) > 1:
            records = [line for line in records if line.split(':')[0] in args[1:] or line.split(':')[2] in args[1:]]
        return Result(('\n'.join(records) + ('\n' if records else '')).encode(), code=0 if records else 2)
    elif name == 'groupadd':
        _, vals, operands = options(args, '', 'g', {'--gid': 'g'})
        if len(operands) != 1: raise ValueError('one group name required')
        group = operands[0]
        if group in db.groups: raise ValueError('group already exists')
        gid = int(vals.get('g', max(db.groups.values()) + 1))
        if gid < 0 or gid in db.groups.values(): raise ValueError('GID is not unique or invalid')
        if not re.fullmatch('[a-z_][a-z0-9_-]*', group): raise ValueError('invalid group name')
        db.groups[group] = gid; db.sync()
    elif name in ('useradd', 'usermod'):
        aliases = {'--uid': 'u', '--gid': 'g', '--groups': 'G', '--shell': 's', '--home-dir': 'd'}
        aliases.update({'--create-home': 'm', '--no-create-home': 'M'} if name == 'useradd' else {'--append': 'a'})
        flags, vals, operands = options(args, 'mM' if name == 'useradd' else 'a', 'ugGsd', aliases)
        if len(operands) != 1: raise ValueError('one user name required')
        username = operands[0]
        if name == 'useradd':
            if 'a' in flags: raise ValueError('useradd does not support --append')
            if username in db.users: raise ValueError('user already exists')
            if not re.fullmatch('[a-z_][a-z0-9_-]*', username): raise ValueError('invalid user name')
            if any(opt in vals and not vals[opt].startswith('/') for opt in ('d', 's')): raise ValueError('path must be absolute')
            uid = int(vals.get('u', max(u['uid'] for u in db.users.values()) + 1))
            if 'g' in vals: primary, gid = db.group(vals['g'])
            else:
                if username in db.groups: raise ValueError('group exists; specify -g')
                primary, gid = username, uid
                if gid in db.groups.values(): raise ValueError('GID is not unique')
            supplemental = [db.group(g)[0] for g in vals.get('G', '').split(',') if g]
            if uid < 0 or any(u['uid'] == uid for u in db.users.values()): raise ValueError('UID is not unique or invalid')
            if 'g' not in vals: db.groups[primary] = gid
            db.add_user(username, {'uid': uid, 'gid': gid, 'home': vals.get('d', '/home/' + username),
                'shell': vals.get('s', '/bin/sh'), 'groups': list(dict.fromkeys([primary, *supplemental]))}, 'm' in flags and 'M' not in flags)
        else:
            _, old = db.user(username)
            updated = copy.deepcopy(old)
            if 'a' in flags and 'G' not in vals: raise ValueError('-a requires -G')
            primary = db.groupname(old['gid'])
            supplemental = set(old['groups']) - {primary}
            if 'G' in vals:
                requested = {db.group(g)[0] for g in vals['G'].split(',') if g}
                supplemental = supplemental | requested if 'a' in flags else requested
            if 'g' in vals: primary, updated['gid'] = db.group(vals['g'])
            if 'u' in vals:
                updated['uid'] = int(vals['u'])
                if updated['uid'] < 0 or any(u['uid'] == updated['uid'] for n, u in db.users.items() if n != username): raise ValueError('UID is not unique')
            for opt, field in [('s', 'shell'), ('d', 'home')]:
                if opt in vals:
                    if not vals[opt].startswith('/'): raise ValueError('path must be absolute')
                    updated[field] = vals[opt]
            updated['groups'] = [primary, *sorted(supplemental - {primary})]
            for path, node in fs.nodes.items():
                if path == old['home'] or path.startswith(old['home'] + '/'):
                    if 'u' in vals and node.uid == old['uid']: node.uid = updated['uid']
                    if 'g' in vals and node.gid == old['gid']: node.gid = updated['gid']
            db.users[username] = updated; db.sync()
    elif name in ('chown', 'chgrp'):
        flags, _, paths = options(args, 'Rv', long={'--recursive': 'R', '--verbose': 'v'})
        if len(paths) < 2: raise ValueError('missing operand')
        spec = paths.pop(0)
        uid = gid = None
        if name == 'chgrp': gid = int(spec) if spec.isdigit() else db.group(spec)[1]
        else:
            owner, sep, group = spec.partition(':')
            if owner: uid = int(owner) if owner.isdigit() else db.user(owner)[1]['uid']
            if sep: gid = (int(group) if group.isdigit() else db.group(group)[1]) if group else db.user(owner)[1]['gid']
        for path in paths:
            full = fs.resolve(shell.path(path))
            targets = [full] + ([n for n in fs.nodes if n.startswith(full + '/')] if 'R' in flags else [])
            for target in targets:
                node = fs.get(target)
                if fs.uid != 0 and (node.uid != fs.uid or uid not in (None, node.uid) or gid is not None and gid not in fs.groups):
                    raise PermissionError('Operation not permitted')
                if uid is not None: node.uid = uid
                if gid is not None: node.gid = gid
                node.mode &= ~0o6000
    return Result(out.encode())


def sudo(shell, args, stdin, redirected):
    from sim_shell import Result
    fs, db = shell.fs, accounts(shell.fs)
    username = db.username(fs.uid)
    if fs.uid != 0 and (username not in db.users or 'sudo' not in db.users[username]['groups']):
        return Result(err=(username + ' is not in the sudoers file.\n').encode(), code=1)
    target = 'root'
    if args[:1] == ['-u']:
        if len(args) < 3: raise ValueError('usage: sudo -u user command')
        target, args = args[1], args[2:]
    if not args: raise ValueError('usage: sudo command')
    if args[0] in ('cd', 'source', 'export', 'unset'): raise ValueError('command not found: ' + args[0])
    target, user = db.user(target)
    previous = fs.uid, fs.gid, fs.groups, shell.env.copy()
    fs.uid, fs.gid, fs.groups = user['uid'], user['gid'], {db.groups[g] for g in user['groups']}
    shell.env.update(USER=target, LOGNAME=target, HOME=user['home'])
    try: return shell.command(args, stdin, redirected)
    finally: fs.uid, fs.gid, fs.groups, shell.env = previous


def prepare_admin(shell, mission):
    plan, fs = mission.review, shell.fs
    db = accounts(fs)
    previous = fs.uid, fs.gid, fs.groups
    fs.uid, fs.gid, fs.groups = 0, 0, {0}
    try:
        fs.mkdir(mission.start, True, True)
        fs.get(mission.start).uid = fs.get(mission.start).gid = 1100
        db.groups.update(plan['groups'])
        for name, user in plan['users'].items(): db.add_user(name, user, True)
        for relative, data in plan['files'].items():
            path = p.join(mission.start, relative)
            fs.mkdir(p.dirname(path), True, True)
            fs.put(path, Node(data['type'], data=data['text'].encode(), mode=data['mode'], uid=data['uid'], gid=data['gid']))
        db.sync()
    finally: fs.uid, fs.gid, fs.groups = previous
