"""Compare Docker inventory meaning, not table spacing or relative clock text.

Accept standard/--no-trunc tables and JSON formatter records. Container identity,
name, image and state must match exactly; image tags must not be lost when two
names share an ID. Row order and elapsed 'Up ...' time are intentionally ignored.
"""
import json
import re

ANSI = re.compile(r'\x1b\[[0-?]*[ -/]*[@-~]')
HEX = re.compile(r'(?:sha256:)?[0-9a-f]{12,64}\Z')


def state(value):
    value = str(value).strip().lower()
    if value.startswith('up '):
        return ('paused' if '(paused)' in value else 'running', None)
    match = re.match(r'(?:exited|restarting) \((\d+)\)', value)
    if match: return (value.split()[0], int(match[1]))
    if value in ('created', 'running', 'paused', 'exited', 'restarting', 'removing', 'dead'):
        return (value, None)
    if value.startswith('removal in progress'): return ('removing', None)
    return None


def records(text, kind):
    if text is None: return None
    text = ANSI.sub('', text).strip('\r\n')
    # An empty JSON-lines stream is the legitimate output of --format json
    # when there are no containers. Missing files are distinguished by None.
    if not text.strip(): return []
    lines = text.splitlines()
    if text.lstrip().startswith(('{', '[')):
        try:
            values = json.loads(text) if text.lstrip().startswith('[') else [json.loads(line) for line in lines if line.strip()]
            return values if isinstance(values, list) and all(isinstance(v, dict) for v in values) else None
        except ValueError: return None
    header = lines[0]
    if kind == 'image':
        headers = re.split(r'\s{2,}|\t+', header.strip())
        legacy = headers[:3] == ['REPOSITORY', 'TAG', 'IMAGE ID']
        modern = headers[:2] == ['IMAGE', 'ID']
        if not legacy and not modern: return None
        result = []
        for line in lines[1:]:
            if not line.strip(): continue
            parts = line.split()
            if legacy and len(parts) >= 3:
                repository, tag, identity = parts[:3]
            elif modern and len(parts) >= 2 and ':' in parts[0]:
                repository, tag = parts[0].rsplit(':', 1)
                identity = parts[1]
            else: return None
            result.append({'Repository': repository, 'Tag': tag, 'ID': identity})
        return result
    # Docker's tabwriter left-aligns container columns. Using the header offsets
    # preserves empty PORTS and COMMAND values containing consecutive spaces.
    headings = list(re.finditer(r'\S(?:.*?\S)?(?=\s{2,}|\t|$)', header))
    names = [m.group() for m in headings]
    if not {'CONTAINER ID', 'IMAGE', 'STATUS', 'NAMES'}.issubset(names): return None
    result = []
    for line in lines[1:]:
        if not line.strip(): continue
        row = {}
        for i, match in enumerate(headings):
            end = headings[i + 1].start() if i + 1 < len(headings) else len(line)
            row[match.group()] = line[match.start():end].strip()
        result.append({'ID': row['CONTAINER ID'], 'Image': row['IMAGE'], 'Names': row['NAMES'], 'Status': row['STATUS']})
    return result


def normalized(row, kind):
    identity = str(row.get('ID', ''))
    if not HEX.fullmatch(identity): return None
    identity = identity.removeprefix('sha256:')
    if kind == 'image':
        repository, tag = row.get('Repository'), row.get('Tag')
        if not isinstance(repository, str) or not isinstance(tag, str) or not repository or not tag: return None
        return (identity, repository, tag)
    name, image = row.get('Names'), row.get('Image')
    status = state(row.get('Status', row.get('State', '')))
    if not isinstance(name, str) or not name or not isinstance(image, str) or not image or status is None: return None
    if 'State' in row and state(row['State']) != (status[0], None): return None
    return (identity, name, image, status)


def same_snapshot(report, current, kind):
    saved = records(report, kind)
    actual = records(current, kind)
    if saved is None or actual is None or len(saved) != len(actual): return False
    actual = [normalized(row, kind) for row in actual]
    if any(row is None for row in actual): return False
    used = set()
    for raw in saved:
        row = normalized(raw, kind)
        if row is None: return False
        matches = []
        for i, live in enumerate(actual):
            if not live[0].startswith(row[0]): continue
            if kind == 'image':
                matched = row[1:] == live[1:]
            else:
                # An unqualified name is not silently mapped to a new registry.
                image_match = row[2] == live[2] or (
                    HEX.fullmatch(row[2]) and HEX.fullmatch(live[2]) and
                    live[2].removeprefix('sha256:').startswith(row[2].removeprefix('sha256:')))
                matched = row[1] == live[1] and image_match and row[3][0] == live[3][0]
                if row[3][1] is not None:
                    matched = matched and row[3][1] == live[3][1]
            if matched: matches.append(i)
        if len(matches) != 1 or matches[0] in used: return False
        used.add(matches[0])
    return len(used) == len(actual)
