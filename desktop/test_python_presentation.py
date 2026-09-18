"""Display-only fixtures never change real execution or remove learner data."""
from dataclasses import replace
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from python_teaching.course import lesson_by_key


class FixturePresentationTests(unittest.TestCase):
    def test_default_displays_all_existing_setup(self):
        problem=lesson_by_key('py_values').problems[0]
        self.assertEqual(problem.prepared_code,problem.initial)

    def test_explicit_display_does_not_change_actual_setup(self):
        unit=lesson_by_key('py_values')
        problem=replace(unit.problems[0],initial='data = [1,2]\ndef _observer(): return data',
                        display_initial='data = [1,2]')
        self.assertIn('def _observer',problem.initial)
        self.assertNotIn('def _observer',problem.prepared_code)
        from export_python_course import export
        with tempfile.TemporaryDirectory() as directory, patch('export_python_course.lessons',
                return_value=(replace(unit,problems=(problem,)),)):
            target=Path(directory)/'course.json'
            export(target)
            exported=json.loads(target.read_text())['lessons'][0]['problems'][0]
        self.assertEqual(exported['initial'],problem.initial)
        self.assertEqual(exported['display_initial'],'data = [1,2]')

    def test_empty_display_is_not_replaced_with_private_helpers(self):
        problem=replace(lesson_by_key('py_values').problems[0],display_initial='')
        self.assertEqual(problem.prepared_code,'')


if __name__=='__main__':unittest.main()
