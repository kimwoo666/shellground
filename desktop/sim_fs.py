"""In-memory POSIX filesystem. No user path ever reaches the host filesystem."""
from dataclasses import dataclass
import copy
import errno
import fnmatch
import posixpath as p
import stat
from types import SimpleNamespace


@dataclass
class Node:
    kind: str = 'file'
    data: bytes = b''
    mode: int = 0o644
    uid: int = 1100
    gid: int = 1100
    target: str = ''
    mtime: int = 1700000000


class FS:
    def __init__(self):
        self.nodes = {'/': Node('dir', mode=0o755, uid=0, gid=0)}
        self.uid = 1100

    def norm(self, path, cwd='/'):
        return p.normpath(p.join(cwd, str(path)))

    def resolve(self, path, follow=True, depth=0):
        if depth > 40: raise OSError(errno.ELOOP, 'Too many levels of symbolic links', path)
        parts = str(path).split('/')
        here = '/'
        for i, part in enumerate(parts):
            if not part or part == '.': continue
            if part == '..': here = p.dirname(here); continue
            parent = self.nodes.get(here)
            if parent is None: raise FileNotFoundError(errno.ENOENT, 'No such file or directory', here)
            if parent.kind != 'dir': raise NotADirectoryError(errno.ENOTDIR, 'Not a directory', here)
            if not self.allowed(parent, 1): raise PermissionError(errno.EACCES, 'Permission denied', here)
            here = p.join(here, part)
            node = self.nodes.get(here)
            if node and node.kind == 'link' and (follow or i < len(parts) - 1):
                return self.resolve(p.join(p.dirname(here), node.target, *parts[i + 1:]), True, depth + 1)
        return here

    def allowed(self, node, bit):
        return self.uid == 0 or ((node.mode >> (6 if node.uid == self.uid else 3 if node.gid == 1100 else 0)) & bit) == bit

    def get(self, path, follow=True):
        key = self.resolve(path, follow)
        if key not in self.nodes: raise FileNotFoundError(errno.ENOENT, 'No such file or directory', str(path))
        return self.nodes[key]

    def exists(self, path, follow=True):
        try: self.get(path, follow); return True
        except OSError: return False

    def writable_parent(self, path):
        parent = self.get(p.dirname(path))
        if parent.kind != 'dir': raise NotADirectoryError(errno.ENOTDIR, 'Not a directory', path)
        if not self.allowed(parent, 3): raise PermissionError(errno.EACCES, 'Permission denied', path)

    def mkdir(self, path, parents=False, exist_ok=False):
        if parents:
            parent = p.dirname(self.norm(path))
            if not self.exists(parent): self.mkdir(parent, True, True)
        key = self.resolve(path)
        if key in self.nodes:
            if exist_ok and self.nodes[key].kind == 'dir': return
            raise FileExistsError(errno.EEXIST, 'File exists', path)
        self.writable_parent(key)
        self.put(key, Node('dir', mode=0o755, uid=self.uid))

    def put(self, path, node):
        if len(self.nodes) >= 10000 and path not in self.nodes: raise OSError('Simulator filesystem limit: 10000 entries')
        if len(node.data) > 2_000_000: raise OSError('Simulator file limit: 2 MB')
        if sum(len(n.data) for k, n in self.nodes.items() if k != path) + len(node.data) > 8_000_000:
            raise OSError('Simulator filesystem data limit: 8 MB')
        self.nodes[path] = node

    def write(self, path, data, append=False):
        key = self.resolve(path)
        node = self.nodes.get(key)
        if node:
            if node.kind == 'dir': raise IsADirectoryError(errno.EISDIR, 'Is a directory', path)
            if not self.allowed(node, 2): raise PermissionError(errno.EACCES, 'Permission denied', path)
            updated = copy.copy(node)
            updated.data = (node.data if append else b'') + data
        else:
            self.writable_parent(key)
            updated = Node(data=data, uid=self.uid)
        self.put(key, updated)

    def read(self, path):
        node = self.get(path)
        if node.kind == 'dir': raise IsADirectoryError(errno.EISDIR, 'Is a directory', path)
        if not self.allowed(node, 4): raise PermissionError(errno.EACCES, 'Permission denied', path)
        return node.data

    def children(self, path):
        key = self.resolve(path)
        node = self.get(key)
        if node.kind != 'dir': raise NotADirectoryError(errno.ENOTDIR, 'Not a directory', path)
        if not self.allowed(node, 4): raise PermissionError(errno.EACCES, 'Permission denied', path)
        return sorted(p.basename(k) for k in self.nodes if k != key and p.dirname(k) == key)

    def remove(self, path, recursive=False):
        key = self.resolve(path, False)
        node = self.get(key, False)
        if key == '/': raise PermissionError('refusing to remove root')
        self.writable_parent(key)
        if node.kind == 'dir' and not recursive: raise IsADirectoryError(errno.EISDIR, 'Is a directory', path)
        for k in list(self.nodes):
            if k == key or (node.kind == 'dir' and k.startswith(key + '/')): del self.nodes[k]

    def copy(self, source, target, recursive=False, move=False):
        src = self.resolve(source, not move)
        node = self.get(src, not move)
        if self.exists(target) and self.get(target).kind == 'dir': target = p.join(target, p.basename(source.rstrip('/')))
        dst = self.resolve(target, False)
        if src == dst: raise OSError('source and destination are the same file')
        if node.kind == 'dir' and dst.startswith(src + '/'): raise OSError('cannot copy a directory into itself')
        if node.kind == 'dir' and not recursive and not move: raise OSError('omitting directory (use -r)')
        self.writable_parent(dst)
        if self.exists(dst) and self.get(dst).kind == 'dir' and self.children(dst): raise OSError('Directory not empty')
        if self.exists(dst) and (self.get(dst).kind == 'dir') != (node.kind == 'dir'): raise OSError('cannot overwrite file with directory or directory with file')
        if not move and node.kind == 'file' and self.exists(dst):
            self.write(dst, self.read(src))
            return
        additions = {dst + k[len(src):]: copy.deepcopy(v) for k, v in self.nodes.items() if k == src or (node.kind == 'dir' and k.startswith(src + '/'))}
        if node.kind == 'file': self.read(src)
        for k, v in additions.items(): self.put(k, v)
        if move: self.remove(src, True)

    def glob(self, pattern):
        parts = pattern.split('/')
        candidates = ['/']
        for part in parts:
            if not part: continue
            new = []
            for base in candidates:
                if any(c in part for c in '*?['):
                    try: names = self.children(base)
                    except OSError: continue
                    new += [p.join(base, n) for n in names if (not n.startswith('.') or part.startswith('.')) and fnmatch.fnmatchcase(n, part)]
                else: new.append(p.join(base, part))
            candidates = new
        return sorted(k for k in candidates if self.exists(k, False))


class VPath:
    """Path-shaped adapter for the existing result-based mission grader."""
    def __init__(self, fs, path): self.fs, self.path = fs, str(path)
    def __str__(self): return self.path
    def __fspath__(self): return self.path
    def __truediv__(self, other): return VPath(self.fs, p.join(self.path, str(other)))
    @property
    def parent(self): return VPath(self.fs, p.dirname(self.path))
    @property
    def name(self): return p.basename(self.path)
    def exists(self): return self.fs.exists(self.path)
    def is_dir(self): return self.exists() and self.fs.get(self.path).kind == 'dir'
    def is_file(self): return self.exists() and self.fs.get(self.path).kind == 'file'
    def mkdir(self, parents=False, exist_ok=False): self.fs.mkdir(self.path, parents, exist_ok)
    def read_bytes(self): return self.fs.read(self.path)
    def read_text(self): return self.read_bytes().decode()
    def write_bytes(self, data): self.fs.write(self.path, data)
    def write_text(self, text): self.write_bytes(text.encode())
    def symlink_to(self, target, target_is_directory=False): self.fs.put(self.path, Node('link', mode=0o777, target=str(target)))
    def rglob(self, pattern):
        return [VPath(self.fs, k) for k in list(self.fs.nodes) if k.startswith(self.path + '/')]
    def lstat(self): return self.stat(False)
    def stat(self, follow=True):
        n = self.fs.get(self.path, follow)
        mode = {'dir': stat.S_IFDIR, 'file': stat.S_IFREG, 'link': stat.S_IFLNK}[n.kind]
        return SimpleNamespace(st_mode=mode | n.mode, st_size=len(n.data))
