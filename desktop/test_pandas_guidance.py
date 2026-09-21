"""Focused checks for newly authored teaching, not a rerun of old exercises."""
import ast
from dataclasses import replace
import os
from pathlib import Path
import tempfile
import unittest

from python_teaching.course import lessons, lesson_by_key
from python_teaching.pandas_guidance import sequences, teach_before_practice
from python_teaching.values import grade_snapshot


def features(code):
    tree = ast.parse(code)
    return ({'attribute:' + node.attr for node in ast.walk(tree) if isinstance(node, ast.Attribute)}
            | {'keyword:' + node.arg for node in ast.walk(tree) if isinstance(node, ast.keyword) and node.arg})


class GuidanceStructureTests(unittest.TestCase):
    def test_all_pandas_units_have_independent_explained_examples(self):
        units = [u for u in lessons() if u.key.startswith('pd_')]
        self.assertEqual(set(sequences()), {u.key for u in units})
        self.assertEqual(len(units), 26)
        for unit in units:
            self.assertGreaterEqual(len(unit.guided_steps), 2)
            self.assertIn(unit.explanation, unit.learning_steps[-1][1])
            self.assertIn(unit.pitfall, unit.learning_steps[-1][1])
            for page in unit.guided_steps:
                with self.subTest(unit=unit.key, page=page.title):
                    self.assertGreater(len(page.explanation), 45)
                    self.assertGreater(len(page.observation), 25)
                    self.assertEqual(page.practice.initial, '')
                    self.assertTrue(page.practice.checks)
                    self.assertTrue(page.practice.solution.startswith('import pandas as pd\n'))
                    self.assertIn('print(', page.practice.solution)
                    compile(page.practice.solution, page.title, 'exec')

    def test_original_tasks_keys_and_prerequisites_are_unchanged(self):
        from python_teaching.pandas_course import lessons as original
        from python_teaching.integration_course import insertions
        from python_teaching.coverage_course import lessons as coverage
        originals = {u.key:u for u in (*original(), *insertions().values(), *coverage())}
        self.assertEqual(len(lessons()), 95)
        for key in sequences():
            unit, old = lesson_by_key(key), originals[key]
            self.assertEqual(unit.problems, old.problems, key)
            self.assertEqual(unit.prerequisites, old.prerequisites, key)
            self.assertEqual(unit.title, old.title, key)
            self.assertEqual(teach_before_practice(unit), unit)

    def test_practice_apis_and_keywords_appear_in_prior_teaching(self):
        # A syntax audit, not a substitute for the authored explanation review.
        seen = set()
        for unit in lessons():
            codes = ([s.practice.solution for s in unit.guided_steps] if unit.guided_steps
                     else [unit.syntax, unit.problems[0].solution])
            for code in codes:
                try: seen |= features(code)
                except SyntaxError: pass  # Older non-pandas syntax templates.
            if unit.guided_steps or (unit.topic == 'pandas' and unit.key.startswith('review_')):
                for problem in unit.problems:
                    self.assertFalse(features(problem.solution) - seen, unit.key)

    def test_entry_syntax_and_early_loc_bridges_are_explicit(self):
        first = '\n'.join(text for _,text in lesson_by_key('pd_series').learning_steps)
        for keyword in ('as pd', '변수', '문자열', '인자', 'loc', 'iloc', '.sum()', '순서'):
            self.assertIn(keyword, first)
        for key, token in [('pd_frame','tolist()'),('pd_argmax','df.loc['),('pd_computed','df.loc[')]:
            self.assertIn(token, '\n'.join(p.description for p in lesson_by_key(key).guided_steps))

    def test_step_bounds_keep_legacy_positions_and_support_later_steps(self):
        unit = lesson_by_key('pd_series')
        for value,expected in [(0,0),(1,1),(4,4),(99,4),(-1,0),('4',0),(None,0),(True,0)]:
            self.assertEqual(unit.clamp_step(value),expected)
        legacy = replace(unit,guided_steps=())
        self.assertEqual(len(legacy.learning_steps),2)
        self.assertEqual(legacy.clamp_step(4),1)


class GuidanceExecutionTests(unittest.TestCase):
    def test_each_new_example_runs_fresh_and_repeatedly(self):
        from python_teaching.worker import Kernel
        original = Path.cwd()
        try:
            with tempfile.TemporaryDirectory(prefix='shellground-pandas-new-') as folder:
                os.chdir(folder)
                os.environ.setdefault('MPLCONFIGDIR', str(Path(folder)/'.mpl-cache'))
                kernel = Kernel(folder)
                count = 0
                for unit in lessons():
                    for page in unit.guided_steps:
                        with self.subTest(unit=unit.key, page=page.title):
                            problem = page.practice
                            kernel.plt.close('all')
                            kernel.namespace = {'__name__':'__main__'}
                            self.assertFalse(grade_snapshot({}, problem.checks)['passed'])
                            for name,spec in problem.files.items():
                                path = Path(folder)/name
                                path.write_text(spec['text'], encoding=spec.get('encoding','utf-8'))
                            for _ in range(2):
                                result = kernel.execute(problem.solution)
                                self.assertTrue(result['ok'], result['output'])
                                self.assertTrue(result['output'].strip())
                                values,errors = kernel.inspect_values(problem.targets,problem.probes)
                                self.assertFalse(errors, errors)
                                grade = grade_snapshot(values,problem.checks)
                                self.assertTrue(grade['passed'],grade)
                            count += 1
                kernel.plt.close('all')
                self.assertEqual(count,81)

        finally:
            os.chdir(original)


if __name__ == '__main__': unittest.main()
