"""Path presentation for generated lessons; canonical grading paths stay absolute."""
from dataclasses import replace
import posixpath
import shlex


def nearby_path(path, cwd):
    """Shorten local/adjacent paths, not long chains of ../../.. ."""
    relative = posixpath.relpath(path, cwd)
    # Count leading parent components explicitly (dotfiles are not parents).
    parents = 0
    for part in relative.split('/'):
        if part != '..':
            break
        parents += 1
    return relative if parents <= 1 and len(relative) < len(path) else path


def starting_location(kind, seed, start, source, target, report):
    """Rotate real work locations without removing distant-path exercises."""
    location = seed % 3
    if location == 2:
        return start
    if kind in {'mkdir', 'touch', 'edit', 'rename', 'remove', 'workspace',
                'permissions', 'duplicate', 'copy', 'curl', 'wget',
                'archive', 'script', 'deb'}:
        return target if location == 0 else posixpath.dirname(target)
    if kind in {'read', 'lsintro'}:
        return source + '/docs' if location == 0 else posixpath.dirname(source)
    if kind in {'list', 'long', 'recursive', 'lsoptions', 'grep', 'find'}:
        return posixpath.dirname(source) if location == 0 else start
    if kind == 'report' and location == 0:
        return posixpath.dirname(report)
    return start


def natural_paths(m, *, move_to_focus=True):
    """Render our simple command templates, tracking cd between lines.

    This is not a shell interpreter and never processes user input. Templates
    contain only commands, pipes and > redirection; quote every ordinary token.
    find keeps its absolute search root because its output is part of the goal.
    """
    cwd = m.start
    lines = []
    focus = None
    if m.kind in {'rename', 'remove', 'workspace', 'copy', 'permissions',
                  'archive', 'script', 'deb'}:
        focus = m.target
    elif m.kind in {'lsintro', 'read', 'long', 'lsoptions', 'grep'}:
        focus = m.source
    # For repeated work far away, move once instead of repeating long paths.
    if (move_to_focus and focus and len(m.solution.splitlines()) > 1
            and nearby_path(focus, cwd).startswith('/')):
        lines.append('cd ' + shlex.quote(focus))
        cwd = focus
    for line in m.solution.splitlines():
        lexer = shlex.shlex(line, posix=True, punctuation_chars='|>')
        lexer.whitespace_split = True
        lexer.commenters = ''
        tokens = list(lexer)
        rendered = []
        command = tokens[0]
        for index, token in enumerate(tokens):
            if token in {'|', '>'}:
                rendered.append(token)
                if token == '|':
                    command = tokens[index + 1]
                continue
            value = token
            if token.startswith('/home/learner/'):
                if not (command == 'find' and index == 1):
                    value = nearby_path(token, cwd)
                if index == 0 and not value.startswith(('/', './', '../')):
                    value = './' + value
            rendered.append(shlex.quote(value))
        lines.append(' '.join(rendered))
        if tokens[0] == 'cd':
            cwd = posixpath.normpath(posixpath.join(cwd, tokens[1]))
    prompt = m.prompt
    roots = {m.source, m.target, posixpath.dirname(m.report), m.start}
    for root in sorted(roots, key=len, reverse=True):
        short = nearby_path(root, m.start)
        if short != root:
            # All roots come from our generated templates, not arbitrary text.
            prompt = prompt.replace(root, short)
    if prompt != m.prompt:
        prompt = '아래 상대경로는 시작 위치 기준입니다. 이동했다면 현재 위치에 맞게 해석하세요.\n\n' + prompt
    if m.kind == 'copy':
        # Distinguish the source tree from the separate prepared work area.
        # Keep canonical anchors visible even after the learner changes cwd;
        # individual objectives and solutions still use nearby relative paths.
        prompt = f'원본 폴더: {m.source}\n작업 폴더: {m.target}\n\n' + prompt
    return replace(m, prompt=prompt, solution='\n'.join(lines))
