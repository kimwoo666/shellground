import json
from pathlib import Path
import tempfile
import unittest

from conda_teaching.learning_steps import STEPS
from conda_teaching.mobile_course import course_data, export, mobile_steps, provided_diagnostics


class CondaMobileCourseTests(unittest.TestCase):
    def setUp(self):
        self.spec = json.loads(Path('conda_teaching/course_spec.json').read_text(encoding='utf-8'))
        self.data = course_data()

    def test_all_units_problems_and_microsteps_are_preserved(self):
        self.assertEqual(len(self.data['units']), 18)
        self.assertEqual(sum(len(unit['problems']) for unit in self.data['units']), 54)
        for source, mobile in zip(self.spec['units'], self.data['units'], strict=True):
            self.assertEqual(mobile['key'], source['key'])
            self.assertEqual(mobile['explanation'], source['explanation'])
            for original, adapted in zip(STEPS[source['key']], mobile['learning_steps'], strict=True):
                self.assertEqual(original['title'], adapted['title'])
                self.assertEqual(original['commands'], adapted['commands'])
                self.assertEqual(set(original), set(adapted))
                if source['key'] not in ('conda_identity', 'conda_create'):
                    self.assertEqual(original, adapted)
            self.assertEqual(mobile['prerequisites'], source['prerequisites'])
            for problem, exported in zip(source['problems'], mobile['problems'], strict=True):
                self.assertEqual(exported['mission']['problem'], problem)
                self.assertEqual(exported['mission']['probes'], self.spec['observer_contract']['module_probes'])

    def test_review_does_not_consume_a_lesson_number(self):
        lessons = [unit for unit in self.data['units'] if unit['kind'] == 'lesson']
        reviews = [unit for unit in self.data['units'] if unit['kind'] == 'review']
        self.assertEqual([unit['number'] for unit in lessons], list(range(1, 16)))
        self.assertEqual([unit['number'] for unit in reviews], [5, 10, 15])

    def test_visible_answer_widgets_do_not_reveal_expected_values(self):
        count = 0
        for unit in self.data['units']:
            for problem in unit['problems']:
                for visible, actual in zip(problem['answer_fields'], problem['mission']['problem']['answer_fields'], strict=True):
                    self.assertEqual(set(visible), {'key', 'label', 'input'})
                    self.assertEqual(visible['input'], 'boolean' if isinstance(actual.get('expected'), bool) else 'text')
                    count += 1
        self.assertGreater(count, 10)

    def test_application_solutions_are_not_in_display_commands(self):
        examples = applications = expressions = 0
        for source, mobile in zip(self.spec['units'], self.data['units'], strict=True):
            for original, problem in zip(source['problems'], mobile['problems'], strict=True):
                self.assertNotIn('reference_commands', problem)
                self.assertEqual(problem['role'], original['role'])
                self.assertEqual(problem['goal'], original['goal'])
                if problem['role'] == 'example':
                    examples += 1
                    self.assertEqual(problem['example_commands'], original['reference_commands'])
                else:
                    applications += 1
                    self.assertEqual(problem['example_commands'], [])
                expected = [command for command in original['reference_commands'] if command.startswith('python ')]
                self.assertEqual(problem['provided_diagnostics'], expected)
                expressions += len(expected)
        self.assertEqual((examples, applications, expressions), (18, 36, 31))

    def test_diagnostics_preserve_repeat_but_never_accept_compound_commands(self):
        command = 'python -c "import sys; print(sys.executable); print(sys.prefix)"'
        self.assertEqual(provided_diagnostics([command, 'conda activate sg-other', command]), [command, command])
        for altered in (command + ' && conda activate sg-other', command + ' > answer.txt',
                        'python -c "print(42)"', 'bash -c "conda activate sg-other"'):
            with self.subTest(command=altered), self.assertRaises(ValueError):
                provided_diagnostics([altered])

    def test_export_is_json_and_not_a_runtime_success_badge(self):
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / 'assets' / 'conda-course.json'
            export(target)
            exported = json.loads(target.read_text(encoding='utf-8'))
        self.assertEqual(exported['execution'], 'real-guest')
        self.assertEqual(exported['schema'], 2)
        self.assertEqual(exported['status'], 'teaching-export-only-runtime-integration-required')
        self.assertFalse(exported['runtime_integration']['practice_enabled'])
        self.assertFalse(exported['runtime_integration']['optional_install_enabled'])
        self.assertEqual(len(exported['units']), 18)

    def test_install_guidance_and_optional_exercise_are_not_lost(self):
        self.assertEqual(self.data['bootstrap'], self.spec['bootstrap'])
        self.assertEqual(self.data['official_sources'], self.spec['official_sources'])
        bootstrap = self.data['bootstrap']
        self.assertFalse(bootstrap['counted_as_lesson'])
        self.assertEqual(bootstrap['optional_install_exercise']['key'], 'conda_install_once')
        self.assertEqual(self.data['counts']['bootstrap_optional_install_exercises'], 1)
        self.assertTrue(bootstrap['readiness_gate']['required'])
        self.data['bootstrap']['optional_install_exercise']['goal'] = 'changed'
        self.assertNotEqual(course_data()['bootstrap']['optional_install_exercise']['goal'], 'changed')

    def test_mobile_instructions_use_buttons_not_desktop_shortcuts(self):
        for unit in self.data['units']:
            for step in unit['learning_steps']:
                for field in ('title', 'explanation', 'observe'):
                    self.assertNotRegex(step[field], r'\bF(?:[1-9]|1[0-2])\b')
        self.assertIn('‘실습 시작’', mobile_steps('conda_identity')[0]['explanation'])
        self.assertIn('‘터미널’ 탭', mobile_steps('conda_identity')[0]['explanation'])
        self.assertIn('‘문제 다시 시작’', mobile_steps('conda_create')[0]['observe'])
        self.assertIn('F4', STEPS['conda_identity'][0]['explanation'])
        self.assertIn('F2', STEPS['conda_create'][0]['observe'])

    def test_mutation_does_not_change_shared_learning_sequences(self):
        self.data['units'][0]['learning_steps'][0]['title'] = 'changed'
        self.assertNotEqual(STEPS['conda_identity'][0]['title'], 'changed')
        self.assertNotEqual(course_data()['units'][0]['learning_steps'][0]['title'], 'changed')


if __name__ == '__main__':
    unittest.main()
