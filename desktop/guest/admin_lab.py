"""Actual guest accounts and filesystem checks; never import/run on host."""
import base64
import grp
import os
from pathlib import Path
import pwd
import stat

from admin_lessons import grade_admin


class AdminLab:
    def __init__(self, agent):
        self.agent = agent
        self.mission = None
        self.owned_users = {}
        self.owned_groups = {}

    def command(self, argv):
        result = self.agent.run(argv, root=True, cwd='/', timeout=15)
        if result['code']:
            raise RuntimeError(base64.b64decode(result['err']).decode(errors='replace'))

    def close(self):
        # Names and identities are allocated only inside this disposable guest.
        # Never use userdel -r: homes are below the separate learner reset root.
        for name, uid in self.owned_users.items():
            try:
                actual = pwd.getpwnam(name)
                if actual.pw_uid == uid:
                    self.agent.run(['pkill', '-KILL', '-u', str(uid)], root=True, cwd='/')
                self.command(['userdel', name])
            except KeyError: pass
        for name, gid in self.owned_groups.items():
            try:
                grp.getgrnam(name)
                self.command(['groupdel', name])
            except KeyError: pass

    def prepare(self, mission):
        self.mission = mission
        plan = mission['review']
        # Includes accounts/groups the learner is asked to create, so reset
        # removes the exercise records even if the task is only partly done.
        self.owned_users = {name: u['uid'] for name, u in {**plan['users'], **plan['expected_users']}.items()}
        # The third group may survive an agent restart between exercises.
        # All three names belong to this seed's reserved training namespace.
        seed = mission['seed']
        self.owned_groups = {prefix + str(seed): 10000 + seed * 3 + offset
                             for offset, prefix in enumerate(('sgdev', 'sgaudit', 'sgops'))}
        self.owned_groups.update({**plan['groups'], **plan['expected_groups']})
        self.close()
        start = Path(plan['start'])
        start.mkdir(parents=True, exist_ok=True)
        os.chown(start, 1100, 1100)
        for name, gid in plan['groups'].items(): self.command(['groupadd', '-g', str(gid), name])
        for name, user in plan['users'].items():
            primary = next(g for g, gid in plan['groups'].items() if gid == user['gid'])
            self.command(['useradd', '-u', str(user['uid']), '-g', primary, '-G', ','.join(g for g in user['groups'] if g != primary),
                          '-s', user['shell'], '-d', user['home'], '-m', name])
        for relative, value in plan['files'].items():
            path = start / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            if value['type'] == 'dir': path.mkdir(exist_ok=True)
            else: path.write_text(value['text'])
            os.chown(path, value['uid'], value['gid'])
            path.chmod(value['mode'])
        return {'ready': True, 'reference': {}}

    def file_info(self, path):
        try:
            path = Path(path)
            s = path.lstat()
            kind = 'file' if stat.S_ISREG(s.st_mode) else 'dir' if stat.S_ISDIR(s.st_mode) else 'link'
            return {'type': kind, 'text': (path.read_text(errors='replace') if s.st_size <= 1048576 else None) if kind == 'file' else '',
                    'mode': stat.S_IMODE(s.st_mode), 'uid': s.st_uid, 'gid': s.st_gid}
        except OSError: return None

    def group_id(self, name):
        try: return grp.getgrnam(name).gr_gid
        except KeyError: return None

    def user_info(self, name):
        try:
            u = pwd.getpwnam(name)
            return {'uid': u.pw_uid, 'gid': u.pw_gid, 'home': u.pw_dir, 'shell': u.pw_shell,
                    'groups': [grp.getgrgid(g).gr_name for g in os.getgrouplist(name, u.pw_gid)]}
        except KeyError: return None

    def grade(self, mission):
        return grade_admin(mission['review'], self)
