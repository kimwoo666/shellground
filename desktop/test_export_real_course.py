import json
from pathlib import Path
import tempfile
import unittest

from export_real_course import course_data, export
from mode_curriculum import curriculum
from missions import make_mission
from real_lessons import adapt_real_mission
from learning_steps import learning_steps
from dataclasses import asdict


class RealCourseExportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = course_data()

    def test_full_real_scope_stable_keys_and_topic_numbering(self):
        units, checkpoints = curriculum('real')
        self.assertEqual([u.key for u in units], [u['key'] for u in self.data['units']])
        self.assertEqual([c.key for c in checkpoints], [c['key'] for c in self.data['reviews']])
        for topic, count in [('리눅스', 60), ('Docker', 15), ('ROS 2', 20)]:
            self.assertEqual(list(range(1, count+1)), [u['number'] for u in self.data['units'] if u['topic'] == topic])
        self.assertEqual(19, len(self.data['reviews']))
        for review in self.data['reviews']:
            self.assertEqual(5, len(review['requires']))
            self.assertEqual(review['after'], review['requires'][-1])

    def test_every_practice_and_microstep_comes_from_same_real_course(self):
        units, _ = curriculum('real')
        for original, record in zip(units, self.data['units']):
            with self.subTest(unit=original.key):
                example = adapt_real_mission(make_mission(original.key, 4242))
                sequence = learning_steps(original, 'real', example)
                if sequence:
                    self.assertEqual([asdict(s) for s in sequence], record['learning_steps'])
                else:
                    self.assertEqual([{'title': original.title, 'explanation': original.explanation,
                        'commands': example.solution, 'observation': example.prompt}], record['learning_steps'])
                self.assertTrue(record['learning_steps'], 'Mobile must not silently lose microsteps')
                for practice, seed in enumerate((4242, 9280, 5942)):
                    self.assertEqual(adapt_real_mission(make_mission(original.key, seed, practice=practice)).payload(), record['problems'][practice])
                    self.assertNotIn('F5', record['problems'][practice]['prompt'])

    def test_export_roundtrip(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / 'real-course.json'
            export(target)
            self.assertEqual(self.data, json.loads(target.read_text()))


if __name__ == '__main__':
    unittest.main()
