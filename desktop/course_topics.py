"""Presentation numbering; saved unit/checkpoint identities never change."""
TOPICS = ('리눅스', 'Docker', 'ROS 2')
DOCKER_KEYS = frozenset('sim_' + k for k in (
    'images', 'run', 'lifecycle', 'exec', 'cleanup', 'update', 'tag', 'commit', 'save', 'limits'))


def topic_of(unit):
    if unit.key.startswith('ros_'): return 'ROS 2'
    return 'Docker' if unit.key in DOCKER_KEYS or unit.key.startswith('docker_') else '리눅스'


def topic_indices(units, topic):
    return [i for i, u in enumerate(units) if topic_of(u) == topic]


def unit_number(units, index):
    return topic_indices(units, topic_of(units[index])).index(index) + 1


def checkpoint_label(units, checkpoint):
    end = unit_number(units, checkpoint.end - 1)
    return f'{topic_of(units[checkpoint.end - 1])} {end - 4:02d}–{end:02d} 종합 복습 · {checkpoint.title}'


def next_in_topic(units, index):
    indices = topic_indices(units, topic_of(units[index]))
    position = indices.index(index) + 1
    return indices[position] if position < len(indices) else None
