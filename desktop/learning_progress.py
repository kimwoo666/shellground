"""Small learning bookmarks, independent of graded mastery and lab contents.

Titles identify steps across reordering; examples contain changing paths and must
never be persisted. A removed/renamed step is not silently marked as learned.
"""


def read_records(value):
    if not isinstance(value, dict): return {}
    records = {}
    for key, record in value.items():
        if not isinstance(key, str) or not isinstance(record, dict): continue
        done = record.get('confirmed', [])
        cursor = record.get('cursor', '')
        records[key] = {
            'cursor': cursor if isinstance(cursor, str) else '',
            'confirmed': list(dict.fromkeys(s for s in done if isinstance(s, str))) if isinstance(done, list) else [],
        }
    return records


def cursor_for(records, key, steps):
    if not steps: return 0
    record = records.get(key, {})
    titles = [s.title for s in steps]
    if record.get('cursor') in titles: return titles.index(record['cursor'])
    return next((i for i, title in enumerate(titles) if title not in record.get('confirmed', [])), 0)


def remember(records, key, steps, cursor, confirmed=None):
    record = records.setdefault(key, {'cursor': '', 'confirmed': []})
    record['cursor'] = steps[cursor].title
    if confirmed is not None and steps[confirmed].title not in record['confirmed']:
        record['confirmed'].append(steps[confirmed].title)


def confirmed_count(records, key, steps):
    return len({s.title for s in steps} & set(records.get(key, {}).get('confirmed', [])))
