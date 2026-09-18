"""Android build input for the existing REAL course, never the legacy matcher.

Keep stable progress keys, topic-local numbering, full explanations, microsteps,
distinct practice variants, and every five-unit review. No commands execute here.
"""
from dataclasses import asdict
import json
from pathlib import Path
import sys

from mode_curriculum import curriculum
from course_topics import topic_of, unit_number, checkpoint_label
from missions import make_mission, lesson_text
from real_lessons import adapt_real_mission
from learning_steps import learning_steps, LearningStep
from real_course_checks import make_review


def course_data():
    units, checkpoints = curriculum('real')
    records = []
    for index, unit in enumerate(units):
        example = adapt_real_mission(make_mission(unit.key, 4242))
        sequence = learning_steps(unit, 'real', example)
        if not sequence:
            # Basic single-concept desktop units use their complete explanation
            # directly. Export that as one page, not an empty mobile lesson.
            sequence = (LearningStep(unit.title, unit.explanation, example.solution, example.prompt),)
        record = asdict(unit)
        record.update(topic=topic_of(unit), number=unit_number(units, index),
            reference=lesson_text(unit, 'real'),
            learning_steps=[asdict(step) for step in sequence],
            problems=[adapt_real_mission(make_mission(unit.key, seed, practice=practice)).payload()
                      for practice, seed in enumerate((4242, 9280, 5942))])
        records.append(record)
    reviews = [{'key': checkpoint.key, 'after': units[checkpoint.end-1].key,
        'topic': topic_of(units[checkpoint.end-1]), 'title': checkpoint_label(units, checkpoint),
        'requires': [unit.key for unit in checkpoint.units],
        'problems': [adapt_real_mission(make_review(checkpoint, seed)).payload()
                     for seed in (4242, 9280, 5942)]} for checkpoint in checkpoints]
    return {'schema': 1, 'execution': 'real-guest', 'units': records, 'reviews': reviews}


def export(path):
    data = course_data()
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(data, ensure_ascii=False), encoding='utf-8')
    print(f'Real course: {len(data["units"])} units, {len(data["reviews"])} reviews -> {target}')


if __name__ == '__main__':
    export(sys.argv[1])
