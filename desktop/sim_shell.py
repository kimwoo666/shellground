"""Bounded shell interpreter for training. Never uses exec/eval/subprocess."""
from dataclasses import dataclass
import copy
import fnmatch
import io
import posixpath as p
import re
import shlex
import stat
import tarfile
import time
import zipfile
from urllib.parse import urlparse
from sim_fs import FS, Node


class Unsupported(ValueError): pass


@dataclass
class Result:
    out: bytes = b''
    err: bytes = b''
    code: int = 0


@dataclass
class Word:
    parts: list


def tokenize(text):
    """Retain quote boundaries until execution, including across && and ;."""
    tokens, parts, chunk = [], [], ''
    quote = None
    active = False
    i = 0
    def flush_part():
        nonlocal chunk
        if chunk: parts.append((chunk, quote)); chunk = ''
    def flush_word():
        nonlocal parts, active
        flush_part()
        if active: tokens.append(Word(parts)); parts = []; active = False
    while i < len(text):
        c = text[i]
        if quote != "'" and (text[i:i + 2] == '$(' or c == '`'):
            raise Unsupported('command substitution is not implemented yet')
        if c == '\\' and quote != "'":
            if i + 1 == len(text): raise ValueError('unexpected end of input')
            if quote == '"' and text[i + 1] not in '$`"\\\n':
                chunk += c; active = True; i += 1; continue
            flush_part(); parts.append((text[i + 1], "'")); active = True; i += 2; continue
        if c in "\"'" and (quote is None or quote == c):
            flush_part(); active = True
            if quote == c:
                if not parts: parts.append(('', quote))
                quote = None
            else: quote = c
            i += 1; continue
        if quote is None:
            if c == '#' and not active:
                while i < len(text) and text[i] != '\n': i += 1
                continue
            if c in ' \t\r': flush_word(); i += 1; continue
            if c in '|&;<>\n':
                # File descriptor redirects only when adjacent to the operator.
                fd = chunk if not parts and chunk in ('1', '2') and c in '<>' else ''
                if fd: chunk = ''; active = False
                flush_word()
                op = ';' if c == '\n' else c
                if i + 1 < len(text) and text[i + 1] == c and c in '|&<>': op += c; i += 1
                if op == '<<': raise Unsupported('here-documents are not implemented yet')
                tokens.append(fd + op); i += 1; continue
            if c in '()`': raise Unsupported('subshells and command substitution are not implemented yet')
        chunk += c; active = True; i += 1
    if quote: raise ValueError('unexpected EOF while looking for matching quote')
    flush_word()
    return tokens


def options(args, allowed='', values='', long=None):
    """GNU-style interspersed short options, combined flags and -- terminator."""
    flags, vals, paths = set(), {}, []
    end = False
    it = iter(args)
    for arg in it:
        if not end and arg == '--': end = True; continue
        if not end and arg.startswith('--'):
            key, eq, value = arg.partition('=')
            if not long or key not in long: raise Unsupported('unsupported option: ' + key)
            alias = long[key]
            if alias in values: vals[alias] = value if eq else next(it, None)
            else: flags.add(alias)
        elif not end and arg.startswith('-') and arg != '-':
            for i, key in enumerate(arg[1:]):
                if key in values:
                    vals[key] = arg[i + 2:] or next(it, None); break
                if key not in allowed: raise Unsupported('unsupported option: -' + key)
                flags.add(key)
        else: paths.append(arg)
    if any(v is None for v in vals.values()): raise ValueError('option requires an argument')
    return flags, vals, paths


class Shell:
    def __init__(self, fs=None):
        self.fs = fs or FS()
        self.cwd = '/home/learner'
        self.env = {'HOME': self.cwd, 'USER': 'learner', 'PATH': '/usr/local/bin:/usr/bin:/bin', 'PWD': self.cwd}
        self.exported = set(self.env)
        self.status = 0
        self.output = b''
        self.args = []
        self.jobs = {}
        self.next_job = 1
        self.history = []
        self.packages = {'bash': '5.2', 'coreutils': '9.4', 'nano': '7.2'}
        self.available = dict(self.packages, tree='2.1', curl='8.5')
        self.updated = False
        self.editor = None
        self.pager = None
        self.exited = False
        self.depth = 0
        self.docker = None
        self.interactive = False
        self.input_capture = None
        self.foreground = None
        self.errexit = False
        self.nounset = False

    def path(self, value):
        if value == '~' or value.startswith('~/'): value = self.env['HOME'] + value[1:]
        return p.join(self.cwd, value)

    def expand(self, word):
        if len(word.parts) == 1 and word.parts[0] == ('$@', '"'): return self.args.copy()
        values, current, wildcard = [], '', False
        for text, quote in word.parts:
            if quote != "'":
                text = re.sub(r'\$(?:\{([A-Za-z_][\w]*)\}|([A-Za-z_][\w]*|[0-9?#*@]))',
                    lambda m: self.variable(m[1] or m[2]), text)
            if quote is None:
                wildcard |= any(c in text for c in '*?[')
                fields = re.split(r'([ \t\n]+)', text)
                for part in fields:
                    if part.isspace():
                        if current: values.append(current); current = ''
                    else: current += part
            else: current += text
        if current or any(q is not None for _, q in word.parts): values.append(current)
        result = []
        for value in values:
            if word.parts and word.parts[0][1] is None and value.startswith('~'): value = self.path(value)
            hits = self.fs.glob(self.path(value)) if wildcard else []
            result.extend([h if value.startswith('/') else p.relpath(h, self.cwd) for h in hits] or [value])
        return result

    def variable(self, name):
        if name == '?': return str(self.status)
        if name == '#': return str(len(self.args))
        if name in ('@', '*'): return ' '.join(self.args)
        if name.isdigit(): return ('bash' if name == '0' else self.args[int(name) - 1] if int(name) <= len(self.args) else '')
        if self.nounset and name not in self.env: raise ValueError(name + ': unbound variable')
        return self.env.get(name, '')

    def execute(self, text, record=True):
        if len(text) > 32768: return Result(err=b'simulator: command length limit exceeded\n', code=2)
        try:
            tokens = tokenize(text)
            groups, group, joiner = [], [], ';'
            for token in tokens:
                if isinstance(token, str) and token in (';', '&&', '||', '&'):
                    if not group and token != ';': raise ValueError('syntax error near ' + token)
                    if group: groups.append((joiner, group, token == '&'))
                    group, joiner = [], token
                else: group.append(token)
            if group: groups.append((joiner, group, False))
            elif tokens and tokens[-1] in ('&&', '||'): raise ValueError('unexpected end of input')
            out, err, status = b'', b'', self.status
            for condition, group, background in groups:
                if condition == '&&' and status != 0 or condition == '||' and status == 0: continue
                if background:
                    argv = [v for w in group if isinstance(w, Word) for v in self.expand(w)]
                    if not argv or argv[0] != 'sleep' or len(argv) != 2: raise Unsupported('background mode currently supports sleep only')
                    seconds = float(argv[1])
                    if seconds < 0: raise ValueError('invalid time interval')
                    job = self.next_job; self.next_job += 1
                    self.jobs[job] = {'pid': 1000 + job, 'state': 'Running', 'command': ' '.join(argv), 'until': time.monotonic() + seconds}
                    r = Result(f'[{job}] {1000 + job}\n'.encode())
                else: r = self.pipeline(group)
                out += r.out; err += r.err; status = r.code; self.status = status
                if len(out) + len(err) > 2_000_000: raise Unsupported('output limit exceeded')
                if self.exited or self.errexit and status != 0: break
            r = Result(out, err, status)
        except (ValueError, OSError, KeyError, IndexError) as exc:
            prefix = 'simulator: ' if isinstance(exc, Unsupported) else 'bash: '
            r = Result(err=(prefix + str(exc) + '\n').encode(), code=2)
        self.status = r.code
        if record: self.output = (self.output + r.out)[-262144:]
        return r

    def pipeline(self, tokens):
        segments, segment = [], []
        for token in tokens:
            if token == '|':
                if not segment: raise ValueError('syntax error near |')
                segments.append(segment); segment = []
            else: segment.append(token)
        if not segment: raise ValueError('unexpected end of pipeline')
        segments.append(segment)
        data, error = b'', b''
        for i, segment in enumerate(segments):
            # Each side of a pipeline has its own shell environment, like bash.
            shell = self if len(segments) == 1 else copy.copy(self)
            if shell is not self: shell.env = self.env.copy()
            r = shell.simple(segment, data, i < len(segments) - 1)
            data = r.out; error += r.err
        return Result(data, error, r.code)

    def simple(self, tokens, stdin=b'', piped=False):
        argv, redirects = [], []
        i = 0
        while i < len(tokens):
            token = tokens[i]
            if isinstance(token, str):
                if token not in ('>', '>>', '<', '1>', '1>>', '2>', '2>>'): raise Unsupported('unsupported shell operator: ' + token)
                i += 1
                if i >= len(tokens) or not isinstance(tokens[i], Word): raise ValueError('syntax error: expected redirection target')
                targets = self.expand(tokens[i])
                if len(targets) != 1: raise ValueError('ambiguous redirect')
                redirects.append((token, self.path(targets[0])))
            else: argv.extend(self.expand(token))
            i += 1
        for op, path in redirects:
            if op == '<': stdin = self.fs.read(path)
            else: self.fs.write(path, b'', append=op.endswith('>>'))
        assignments = {}
        while argv and re.match(r'^[A-Za-z_]\w*=', argv[0]):
            k, v = argv.pop(0).split('=', 1); assignments[k] = v
        if not argv:
            self.env.update(assignments); return Result()
        if self.interactive and argv == ['cat'] and not stdin and not piped and not any(op == '<' for op, _ in redirects):
            self.input_capture = {'redirects': redirects, 'buffer': ''}
            return Result()
        old = self.env.copy()
        self.env.update(assignments)
        try: r = self.command(argv, stdin, piped or bool(redirects))
        except Unsupported as exc: r = Result(err=f'simulator: {argv[0]}: {exc}\n'.encode(), code=2)
        except (OSError, ValueError, IndexError, KeyError, re.error) as exc:
            detail = (f"'{exc.filename}': {exc.strerror}" if isinstance(exc, OSError) and exc.filename else str(exc))
            r = Result(err=f'{argv[0]}: {detail}\n'.encode(), code=1)
        finally:
            for k in assignments:
                if k in old: self.env[k] = old[k]
                else: self.env.pop(k, None)
        for op, path in redirects:
            if op == '<': continue
            if op.startswith('2'): self.fs.write(path, r.err, append=op.endswith('>>')); r.err = b''
            else: self.fs.write(path, r.out, append=op.endswith('>>')); r.out = b''
        return r

    def command(self, argv, stdin=b'', redirected=False):
        name, args = argv[0], argv[1:]
        if name.startswith('/bin/') or name.startswith('/usr/bin/'): name = p.basename(name)
        if name == 'docker': return self.docker.command(args, stdin)
        if args == ['--help'] and name in self.commands():
            supported = {'ls': '-a -A -l -h -1 -R -r -S -t -d', 'touch': '-a -m -c', 'cat': '-n -b -A',
                         'cp': '-r -R -v -n -f', 'mv': '-v -n -f', 'grep': '-i -n -v -c -l -w -E -F',
                         'find': '-type -name -iname -maxdepth', 'wc': '-l -w -c -m', 'chmod': 'numeric or u/g/o/a +/-/= rwx; -R'}
            return Result((f'Usage: {name} [options] [operands]\nShellground supported options: ' + supported.get(name, 'see F3; unsupported options return an error') + '\n').encode())
        out = ''
        if name in ('true', ':'): return Result()
        if name == 'false': return Result(code=1)
        if name in ('test', '['):
            if name == '[':
                if not args or args.pop() != ']': raise ValueError('missing ]')
            if len(args) == 2 and args[0] in ('-f', '-d', '-e', '-n', '-z'):
                flag, value = args
                if flag in ('-n', '-z'): valid = bool(value) == (flag == '-n')
                else:
                    full = self.path(value)
                    valid = self.fs.exists(full) and (flag == '-e' or self.fs.get(full).kind == ('file' if flag == '-f' else 'dir'))
            elif len(args) == 3 and args[1] in ('=', '!=', '-eq'):
                valid = args[0] == args[2] if args[1] == '=' else args[0] != args[2] if args[1] == '!=' else int(args[0]) == int(args[2])
            elif len(args) <= 1: valid = bool(args and args[0])
            else: raise Unsupported('unsupported test expression')
            return Result(code=0 if valid else 1)
        if name == 'exit': self.exited = True; return Result(code=int(args[0]) if args else 0)
        if name == 'clear': return Result(b'\x1b[2J\x1b[H')
        if name == 'pwd':
            flags, _, paths = options(args, 'LP')
            if paths: raise ValueError('too many arguments')
            out = (self.fs.resolve(self.cwd) if 'P' in flags else self.cwd) + '\n'
        elif name == 'cd':
            flags, _, paths = options(args, 'LP')
            if len(paths) > 1: raise ValueError('too many arguments')
            dest = paths[0] if paths else self.env['HOME']
            previous = dest == '-'
            if previous:
                dest = self.env.get('OLDPWD') or ''
                if not dest: raise ValueError('OLDPWD not set')
            raw = self.path(dest)
            resolved = self.fs.resolve(raw if 'P' in flags else p.normpath(raw))
            node = self.fs.get(resolved)
            if node.kind != 'dir': raise NotADirectoryError('Not a directory')
            if not self.fs.allowed(node, 1): raise PermissionError('Permission denied')
            self.env['OLDPWD'] = self.cwd
            self.cwd = resolved if 'P' in flags else p.normpath(raw)
            self.env['PWD'] = self.cwd
            out = self.cwd + '\n' if previous else ''
        elif name == 'ls': return self.ls(args, redirected)
        elif name == 'mkdir':
            flags, vals, paths = options(args, 'pv', 'm')
            if not paths: raise ValueError('missing operand')
            for path in paths:
                self.fs.mkdir(self.path(path), 'p' in flags, 'p' in flags)
                if 'm' in vals: self.fs.get(self.path(path)).mode = int(vals['m'], 8)
                if 'v' in flags: out += f"mkdir: created directory '{path}'\n"
        elif name == 'touch':
            flags, _, paths = options(args, 'amc')
            if not paths: raise ValueError('missing file operand')
            for path in paths:
                full = self.path(path)
                if not self.fs.exists(full):
                    if 'c' not in flags: self.fs.write(full, b'')
                elif 'a' not in flags or 'm' in flags: self.fs.get(full).mtime = int(time.time())
        elif name in ('cp', 'mv'):
            flags, _, paths = options(args, 'rRvnf')
            if len(paths) < 2: raise ValueError('missing destination file operand')
            dest = self.path(paths[-1])
            if len(paths) > 2 and (not self.fs.exists(dest) or self.fs.get(dest).kind != 'dir'): raise ValueError('target is not a directory')
            for source in paths[:-1]:
                actual = p.join(dest, p.basename(source)) if self.fs.exists(dest) and self.fs.get(dest).kind == 'dir' else dest
                if 'n' in flags and self.fs.exists(actual): continue
                self.fs.copy(self.path(source), dest, bool(flags & {'r', 'R'}), name == 'mv')
                if 'v' in flags: out += f"'{source}' -> '{paths[-1]}'\n"
        elif name in ('rm', 'rmdir'):
            flags, _, paths = options(args, 'rfRv')
            if not paths and 'f' not in flags: raise ValueError('missing operand')
            for path in paths:
                full = self.path(path)
                if 'f' in flags and not self.fs.exists(full, False): continue
                if name == 'rmdir' and self.fs.children(full): raise OSError('Directory not empty')
                self.fs.remove(full, name == 'rmdir' or bool(flags & {'r', 'R'}))
        elif name == 'cat':
            flags, _, paths = options(args, 'nbA')
            data = b''.join(stdin if path == '-' else self.fs.read(self.path(path)) for path in paths) if paths else stdin
            if flags & {'n', 'b'}:
                lines, count = [], 0
                for line in data.decode(errors='replace').splitlines(True):
                    if 'b' not in flags or line.strip(): count += 1; line = f'{count:6}\t' + line
                    lines.append(line)
                data = ''.join(lines).encode()
            if 'A' in flags: data = data.replace(b'\t', b'^I').replace(b'\r', b'^M').replace(b'\n', b'$\n')
            return Result(data)
        elif name in ('echo', 'printf'):
            if name == 'echo':
                flags = set()
                while args and args[0] in ('-n', '-e', '-E'): flags.add(args.pop(0))
                out = ' '.join(args) + ('' if '-n' in flags else '\n')
                if '-e' in flags: out = self.escapes(out)
            else:
                if not args: raise ValueError('usage: printf format [arguments]')
                fmt = self.escapes(args[0]); remaining = list(args[1:])
                def sub(m):
                    if m[0] == '%%': return '%'
                    value = remaining.pop(0) if remaining else ''
                    return str(int(value or 0)) if m[0] == '%d' else value
                if re.search(r'%(?![sd%])', fmt): raise Unsupported('printf supports %s, %d and %%')
                out = re.sub(r'%[sd%]', sub, fmt)
                if re.search(r'%(?:s|d)', fmt):
                    while remaining: out += re.sub(r'%[sd%]', sub, fmt)
        elif name in ('head', 'tail'):
            _, vals, paths = options(args, '', 'n')
            count = int(vals.get('n', '10'))
            data = b''.join(self.fs.read(self.path(path)) for path in paths) if paths else stdin
            lines = data.splitlines(True)
            return Result(b''.join(lines[:count] if name == 'head' else lines[-count:] if count else []))
        elif name == 'tree':
            if 'tree' not in self.packages: return Result(err=b'bash: tree: command not found\n', code=127)
            flags, _, paths = options(args, 'a')
            if len(paths) > 1: raise Unsupported('tree supports one root')
            root = paths[0] if paths else '.'
            rows = [root]
            def walk(path, prefix='', depth=0):
                if depth > 30: raise Unsupported('tree depth limit')
                names = [n for n in self.fs.children(self.path(path)) if 'a' in flags or not n.startswith('.')]
                for i, child in enumerate(names):
                    last = i == len(names) - 1
                    rows.append(prefix + ('└── ' if last else '├── ') + child)
                    sub = p.join(path, child)
                    if self.fs.get(self.path(sub), False).kind == 'dir': walk(sub, prefix + ('    ' if last else '│   '), depth + 1)
            walk(root); out = '\n'.join(rows) + '\n'
        elif name == 'wc':
            flags, _, paths = options(args, 'lwcm')
            rows = []
            for path in paths or ['']:
                data = self.fs.read(self.path(path)) if path else stdin
                counts = [data.count(b'\n'), len(data.split()), len(data), len(data.decode(errors='replace'))]
                selected = [str(counts[i]) for i, flag in enumerate('lwcm') if (not flags and flag != 'm') or flag in flags]
                rows.append(' '.join(selected) + (' ' + path if path else ''))
            out = '\n'.join(rows) + '\n'
        elif name == 'grep':
            flags, _, paths = options(args, 'invclwEF')
            if not paths: raise ValueError('missing pattern')
            pattern = paths.pop(0)
            expression = re.escape(pattern) if 'F' in flags else pattern
            if 'w' in flags: expression = r'(?<!\w)(?:' + expression + r')(?!\w)'
            regex = re.compile(expression, re.I if 'i' in flags else 0)
            results, any_match = [], False
            for path in paths or ['']:
                data = self.fs.read(self.path(path)).decode(errors='replace') if path else stdin.decode(errors='replace')
                matches = [(n, line) for n, line in enumerate(data.splitlines(), 1) if bool(regex.search(line)) != ('v' in flags)]
                any_match |= bool(matches)
                if 'l' in flags:
                    if matches: results.append(path or '(standard input)')
                elif 'c' in flags: results.append((path + ':' if len(paths) > 1 else '') + str(len(matches)))
                else:
                    results += [(path + ':' if len(paths) > 1 else '') + (str(n) + ':' if 'n' in flags else '') + line for n, line in matches]
            return Result(('\n'.join(results) + ('\n' if results else '')).encode(), code=0 if any_match else 1)
        elif name == 'find':
            root = args.pop(0) if args and not args[0].startswith('-') else '.'
            kind = pattern = None
            insensitive = False; maxdepth = None
            while args:
                key = args.pop(0)
                if key == '-type': kind = args.pop(0)
                elif key == '-name': pattern = args.pop(0)
                elif key == '-iname': pattern = args.pop(0); insensitive = True
                elif key == '-maxdepth': maxdepth = int(args.pop(0))
                else: raise Unsupported('unsupported find expression: ' + key)
            if kind not in (None, 'f', 'd', 'l'): raise ValueError('invalid argument to -type')
            absolute = self.fs.resolve(self.path(root)); self.fs.get(absolute)
            hits = []
            for path in sorted(self.fs.nodes):
                if path != absolute and not path.startswith(absolute.rstrip('/') + '/'): continue
                if maxdepth is not None and (0 if path == absolute else path[len(absolute):].count('/')) > maxdepth: continue
                node = self.fs.nodes[path]
                if kind and {'file': 'f', 'dir': 'd', 'link': 'l'}[node.kind] != kind: continue
                if pattern and not fnmatch.fnmatchcase(p.basename(path).lower() if insensitive else p.basename(path), pattern.lower() if insensitive else pattern): continue
                suffix = path[len(absolute):]
                hits.append(root.rstrip('/') + suffix)
            out = '\n'.join(hits) + ('\n' if hits else '')
        elif name == 'chmod':
            if args and re.fullmatch(r'-[rwx]+', args[0]): flags, paths = set(), args
            else: flags, _, paths = options(args, 'Rv')
            if len(paths) < 2: raise ValueError('missing operand')
            mode = paths.pop(0)
            for path in paths:
                full = self.fs.resolve(self.path(path))
                targets = [full] + ([k for k in self.fs.nodes if k.startswith(full + '/')] if 'R' in flags else [])
                for key in targets:
                    n = self.fs.get(key)
                    if self.fs.uid not in (0, n.uid): raise PermissionError('Operation not permitted')
                    if re.fullmatch('[0-7]{3,4}', mode): n.mode = int(mode, 8)
                    else:
                        for part in mode.split(','):
                            m = re.fullmatch('([ugoa]*)([+=-])([rwx]*)', part)
                            if not m: raise Unsupported('unsupported symbolic mode: ' + part)
                            who, op, perms = m.groups(); who = 'ugo' if not who or 'a' in who else who
                            bits = sum(bit for ch, bit in [('r', 4), ('w', 2), ('x', 1)] if ch in perms)
                            mask = sum(7 << shift for ch, shift in [('u', 6), ('g', 3), ('o', 0)] if ch in who)
                            value = sum(bits << shift for ch, shift in [('u', 6), ('g', 3), ('o', 0)] if ch in who)
                            n.mode = (n.mode | value) if op == '+' else (n.mode & ~value) if op == '-' else (n.mode & ~mask) | value
        elif name == 'ln':
            flags, _, paths = options(args, 's')
            if len(paths) != 2: raise ValueError('expected target and link name')
            if 's' not in flags: raise Unsupported('hard links are not implemented yet')
            target = self.fs.resolve(self.path(paths[1]), False)
            if self.fs.exists(target, False): raise FileExistsError('File exists')
            self.fs.writable_parent(target); self.fs.put(target, Node('link', mode=0o777, target=paths[0]))
        elif name in ('curl', 'wget'):
            flags, vals, paths = options(args, 'fLOsSq', 'oOP' if name == 'wget' else 'o', {'--output': 'o'})
            if len(paths) != 1: raise ValueError('expected one URL')
            url = urlparse(paths[0]); filename = p.basename(url.path)
            if url.scheme != 'http' or url.netloc != '127.0.0.1:8765': raise Unsupported('external network is disabled; use the lesson fixture URL')
            fixture = '/srv/fixtures/' + filename
            if not self.fs.exists(fixture): return Result(err=b'HTTP request failed: 404 Not Found\n', code=22 if name == 'curl' else 8)
            data = self.fs.read(fixture)
            dest = vals.get('o') if name == 'curl' else vals.get('O')
            if name == 'wget' and not dest:
                dest = p.join(vals.get('P', '.'), filename)
                suffix = 1; original = dest
                while self.fs.exists(self.path(dest)): dest = original + '.' + str(suffix); suffix += 1
            if name == 'curl' and 'O' in flags: dest = filename
            if dest: self.fs.write(self.path(dest), data)
            else: return Result(data)
        elif name in ('tar', 'unzip', 'dpkg-deb'): return self.archive(name, args)
        elif name == 'nano':
            _, _, paths = options(args)
            if len(paths) != 1 or redirected: raise Unsupported('nano requires one filename in an interactive terminal')
            path = self.path(paths[0]); data = self.fs.read(path).decode() if self.fs.exists(path) else ''
            self.editor = {'path': path, 'text': data, 'cursor': 0, 'dirty': False, 'mode': 'edit'}
        elif name in ('more', 'less'):
            _, _, paths = options(args)
            data = b''.join(self.fs.read(self.path(path)) for path in paths) if paths else stdin
            self.pager = data.decode(errors='replace').splitlines(); return Result()
        elif name in ('export', 'unset', 'env', 'printenv'):
            if name == 'export':
                for arg in args:
                    k, eq, value = arg.partition('=')
                    if not re.fullmatch(r'[A-Za-z_]\w*', k): raise ValueError('not a valid identifier')
                    if eq: self.env[k] = value
                    self.exported.add(k)
                if not args: out = ''.join(f'declare -x {k}="{self.env.get(k, "")}"\n' for k in sorted(self.exported))
            elif name == 'unset':
                for key in args: self.env.pop(key, None); self.exported.discard(key)
            else:
                if args: out = ''.join(self.env[k] + '\n' for k in args if k in self.exported and k in self.env)
                else: out = ''.join(k + '=' + self.env[k] + '\n' for k in sorted(self.exported) if k in self.env)
        elif name in ('bash', 'sh', 'source', '.') or '/' in name:
            if name in ('bash', 'sh') and args[:1] == ['-c']:
                if len(args) != 2: raise ValueError('expected -c command')
                child = copy.copy(self); child.env = {k: v for k, v in self.env.items() if k in self.exported}
                child.exited = False
                return child.execute(args[1], False)
            source = name in ('source', '.')
            if name in ('bash', 'sh', 'source', '.'):
                if not args: raise Unsupported('specify a script file or use bash -c')
                script, script_args = args[0], args[1:]
            else: script, script_args = name, args
            path = self.path(script)
            if name not in ('bash', 'sh', 'source', '.') and not self.fs.get(path).mode & 0o111: return Result(err=f'bash: {name}: Permission denied\n'.encode(), code=126)
            if self.depth >= 8: raise Unsupported('script recursion limit exceeded')
            body = self.fs.read(path).decode()
            if not body.startswith('#!') and name not in ('bash', 'sh', 'source', '.'): raise Unsupported('only text shell scripts are executable in this simulator')
            child = self if source else copy.copy(self)
            if not source: child.env = {k: v for k, v in self.env.items() if k in self.exported}; child.exited = False
            previous_args = child.args; child.args = script_args; child.depth += 1
            try: return child.execute(body, False)
            finally: child.args = previous_args; child.depth -= 1
        elif name == 'set':
            if args not in (['-eu'], ['-e'], ['-u']): raise Unsupported('only fixture script set -e/-u supported')
            self.errexit |= 'e' in args[0]; self.nounset |= 'u' in args[0]
        elif name in ('jobs', 'ps', 'kill', 'bg', 'fg', 'sleep'): return self.process_command(name, args)
        elif name == 'sudo':
            if not args: raise ValueError('usage: sudo command')
            uid = self.fs.uid; self.fs.uid = 0
            try: return self.command(args, stdin, redirected)
            finally: self.fs.uid = uid
        elif name in ('apt', 'apt-get'): return self.apt(args)
        elif name == 'whoami': out = 'root\n' if self.fs.uid == 0 else 'learner\n'
        elif name == 'id': out = 'uid=0(root) gid=0(root) groups=0(root)\n' if self.fs.uid == 0 else 'uid=1100(learner) gid=1100(learner) groups=1100(learner),27(sudo)\n'
        elif name == 'hostname':
            if args: raise Unsupported('hostname changes not implemented')
            out = 'lab\n'
        elif name == 'uname':
            flags, _, paths = options(args, 'asrm')
            if paths: raise ValueError('extra operand')
            out = 'Linux lab 6.8.0-sim #1 SMP x86_64 GNU/Linux\n' if 'a' in flags else 'x86_64\n' if 'm' in flags else '6.8.0-sim\n' if 'r' in flags else 'Linux\n'
        elif name == 'type':
            for arg in args:
                out += f'{arg} is a shell builtin\n' if arg in ('pwd', 'cd', 'echo', 'export', 'jobs', 'type') else f'{arg} is /usr/bin/{arg}\n' if arg in self.commands() else f'bash: type: {arg}: not found\n'
        elif name == 'history': out = ''.join(f'{i:5}  {line}\n' for i, line in enumerate(self.history, 1))
        elif name == 'help': out = 'Shellground simulator: ' + ' '.join(self.commands()) + '\n지원 범위와 제한은 프로그램 설명을 확인하세요.\n'
        else:
            for directory in self.env.get('PATH', '').split(':'):
                candidate = p.join(directory or self.cwd, name)
                if self.fs.exists(candidate): return self.command([candidate, *args], stdin, redirected)
            return Result(err=f'bash: {name}: command not found\n'.encode(), code=127)
        return Result(out.encode())

    @staticmethod
    def escapes(text):
        table = {'n': '\n', 't': '\t', 'r': '\r', '\\': '\\'}
        return re.sub(r'\\([ntr\\])', lambda m: table[m[1]], text)

    @staticmethod
    def commands():
        return 'pwd cd ls mkdir touch cat cp mv rm rmdir chmod ln echo printf head tail wc grep find curl wget tar unzip dpkg-deb nano more less export unset env printenv bash sh source jobs ps kill bg fg sleep sudo apt apt-get tree whoami id hostname uname type history help docker clear true false test exit'.split()

    def ls(self, args, redirected=False):
        flags, _, paths = options(args, 'alAhS1Rrtd', long={'--all': 'a', '--almost-all': 'A', '--human-readable': 'h', '--recursive': 'R', '--reverse': 'r'})
        chunks = []
        def listing(path, heading=False, seen=None):
            seen = set() if seen is None else seen
            key = self.fs.resolve(self.path(path)); node = self.fs.get(key)
            if key in seen: return
            seen.add(key)
            isdir = node.kind == 'dir' and 'd' not in flags
            names = self.fs.children(key) if isdir else [p.basename(path)]
            if isdir:
                names = [n for n in names if not n.startswith('.') or flags & {'a', 'A'}]
                if 'a' in flags: names = ['.', '..'] + names
            def item(n): return self.fs.get(p.join(key, n) if isdir else key, False)
            names.sort(key=lambda n: (-len(item(n).data), n) if 'S' in flags else (-item(n).mtime, n) if 't' in flags else (n,))
            if 'r' in flags: names.reverse()
            if heading: chunks.append(path + ':\n')
            if 'l' in flags:
                if isdir: chunks.append('total ' + str(sum(4 for n in names if item(n).data or item(n).kind == 'dir')) + '\n')
                for n in names:
                    node = item(n); size = 4096 if node.kind == 'dir' else len(node.target) if node.kind == 'link' else len(node.data)
                    size_text = (f'{size / 1024:.1f}K' if 1024 <= size < 10240 else f'{size / 1024:.0f}K' if size >= 10240 else str(size)) if 'h' in flags else str(size)
                    mode = stat.filemode({'dir': stat.S_IFDIR, 'file': stat.S_IFREG, 'link': stat.S_IFLNK}[node.kind] | node.mode)
                    owner = 'root' if node.uid == 0 else 'learner'
                    date = time.strftime('%b %d  %Y' if abs(time.time() - node.mtime) > 15552000 else '%b %d %H:%M', time.gmtime(node.mtime))
                    chunks.append(f'{mode} 1 {owner} {owner} {size_text:>6} {date} {n}' + (' -> ' + node.target if node.kind == 'link' else '') + '\n')
            elif names: chunks.append(('\n' if redirected or '1' in flags else '  ').join(names) + '\n')
            if 'R' in flags and isdir:
                for n in names:
                    if n not in ('.', '..') and item(n).kind == 'dir': chunks.append('\n'); listing(p.join(path, n), True, seen)
        for path in paths or ['.']: listing(path, 'R' in flags or len(paths) > 1)
        return Result(''.join(chunks).encode())

    def archive(self, name, args):
        if name == 'dpkg-deb':
            flags, _, paths = options(args, 'Ix', long={'--info': 'I', '--extract': 'x'})
            if not paths: raise ValueError('missing archive')
            data = self.fs.read(self.path(paths[0]))
            if data != self.fs.read('/srv/fixtures/toolkit.deb'): raise ValueError('not a supported Debian archive')
            if 'I' in flags: return Result(b' new Debian package, version 2.0.\n Package: shellground-toolkit\n Version: 1.0\n Architecture: all\n Description: Offline command training fixture\n')
            if 'x' not in flags or len(paths) != 2: raise ValueError('expected --info file or --extract file directory')
            dest = self.path(paths[1]); self.fs.mkdir(dest + '/usr/share/shellground', True, True)
            self.fs.write(dest + '/usr/share/shellground/message.txt', b'Extracted from a real Debian package.\n'); return Result()
        if name == 'tar':
            if args and not args[0].startswith('-'): args = ['-' + args[0], *args[1:]]
            flags, vals, paths = options(args, 'txczv', 'fC')
            if 'c' in flags: raise Unsupported('tar creation is not implemented yet')
            if 'f' not in vals or bool('t' in flags) == bool('x' in flags): raise ValueError('specify -t or -x and -f archive')
            data = self.fs.read(self.path(vals['f']))
            try:
                with tarfile.open(fileobj=io.BytesIO(data), mode='r:*') as arc:
                    entries = [(m.name, arc.extractfile(m).read() if m.isfile() else None, m.mode) for m in arc if m.isfile() or m.isdir()]
            except tarfile.TarError as exc: raise ValueError('This does not look like a tar archive') from exc
            dest = self.path(vals.get('C', '.')); listing = 't' in flags
        else:
            flags, vals, paths = options(args, 'lo', 'd')
            if len(paths) != 1: raise ValueError('expected one zip archive')
            try:
                with zipfile.ZipFile(io.BytesIO(self.fs.read(self.path(paths[0])))) as arc:
                    entries = [(m.filename, None if m.is_dir() else arc.read(m), 0o644) for m in arc.infolist()]
            except zipfile.BadZipFile as exc: raise ValueError('not a zip archive') from exc
            dest = self.path(vals.get('d', '.')); listing = 'l' in flags
            if not listing: self.fs.mkdir(dest, True, True)
        if listing: return Result(('\n'.join(n for n, _, _ in entries) + '\n').encode())
        if not self.fs.exists(dest): raise FileNotFoundError('destination directory does not exist')
        for name, data, mode in entries:
            if name.startswith('/') or '..' in name.split('/'): raise ValueError('unsafe archive member')
            target = p.join(dest, name)
            self.fs.mkdir(p.dirname(target), True, True)
            if data is None: self.fs.mkdir(target, True, True)
            else: self.fs.write(target, data); self.fs.get(target).mode = mode
        return Result()

    def process_command(self, name, args):
        for job in self.jobs.values():
            if job['state'] == 'Running' and time.monotonic() >= job['until']: job['state'] = 'Done'
        if name == 'sleep':
            if len(args) != 1: raise ValueError('expected one time interval')
            seconds = float(args[0])
            if seconds < 0: raise ValueError('invalid time interval')
            if not self.interactive: raise Unsupported('foreground sleep needs the interactive terminal')
            self.foreground = {'pid': 1000 + self.next_job, 'state': 'Running', 'command': 'sleep ' + args[0], 'until': time.monotonic() + seconds}
            return Result()
        if name == 'jobs':
            flags, _, paths = options(args, 'l')
            if paths: raise Unsupported('job selection not implemented for jobs')
            return Result(''.join(f'[{n}]+ {str(j["pid"]) + " " if "l" in flags else ""}{j["state"]:10} {j["command"]}\n' for n, j in self.jobs.items()).encode())
        if name == 'ps':
            if any(a not in ('-f', '-e', '-ef', '-Lf', '-U', 'learner') for a in args): raise Unsupported('unsupported ps option')
            return Result(('UID PID PPID C STIME TTY TIME CMD\nlearner 100 1 0 00:00 pts/0 00:00:00 bash\n' + ''.join(f'learner {j["pid"]} 100 0 00:00 pts/0 00:00:00 {j["command"]}\n' for j in self.jobs.values() if j['state'] not in ('Done', 'Terminated'))).encode())
        if name in ('fg', 'bg'):
            token = args[0] if args else '%' + str(max(self.jobs, default=0))
            job = self.jobs.get(int(token.lstrip('%')))
            if not job or job['state'] in ('Done', 'Terminated'): raise ValueError('no such job')
            job['state'] = 'Running'
            if name == 'fg': self.foreground = job
            return Result((job['command'] + (' &\n' if name == 'bg' else '\n')).encode())
        sig = 'TERM'
        if args and args[0].startswith('-'): sig = args.pop(0).lstrip('-').removeprefix('SIG')
        sig = {'9': 'KILL', '15': 'TERM', '19': 'STOP', '18': 'CONT', '2': 'INT'}.get(sig, sig)
        if sig not in ('KILL', 'TERM', 'STOP', 'TSTP', 'CONT', 'INT'): raise Unsupported('unsupported signal')
        if not args: raise ValueError('missing PID or job ID')
        for token in args:
            job = self.jobs.get(int(token[1:])) if token.startswith('%') else next((j for j in self.jobs.values() if j['pid'] == int(token)), None)
            if not job or job['state'] in ('Done', 'Terminated'): raise ValueError('No such process')
            job['state'] = 'Stopped' if sig in ('STOP', 'TSTP') else 'Running' if sig == 'CONT' else 'Terminated'
        return Result()

    def apt(self, args):
        flags, _, paths = options(args, 'y', long={'--installed': 'i', '--fix-broken': 'f'})
        if not paths: raise ValueError('usage: apt command')
        action, names = paths[0], paths[1:]
        if action == 'list': return Result(('Listing...\n' + ''.join(f'{k}/training {v} all [installed]\n' for k, v in sorted(self.packages.items()))).encode())
        if self.fs.uid != 0: return Result(err=b'E: Could not open lock file /var/lib/dpkg/lock-frontend - Permission denied\n', code=100)
        if action == 'update': self.updated = True; return Result(b'Hit:1 http://archive.ubuntu.com/ubuntu training InRelease\nReading package lists... Done\n')
        if action == 'install':
            if not names: raise ValueError('missing package name')
            for name in names:
                if name not in self.available: return Result(err=f'E: Unable to locate package {name}\n'.encode(), code=100)
            for name in names: self.packages[name] = self.available[name]
        elif action in ('remove', 'purge'):
            for name in names: self.packages.pop(name, None)
        elif action == 'upgrade':
            for name in self.packages: self.packages[name] = self.available.get(name, self.packages[name])
        else: raise Unsupported('unsupported apt command: ' + action)
        return Result(('Reading package lists... Done\n' + '\n'.join(names) + '\nDone\n').encode())
