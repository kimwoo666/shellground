"""Portable review regression data plus actual-library grading integration.

Contract tests always run without scientific dependencies. Execution tests use
the existing Kernel and grader, create only temporary fixtures, and skip when
the actual NumPy/pandas/Matplotlib/SciPy libraries are unavailable.
"""
import ast
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest

from python_teaching.course import lessons
from python_teaching.review_validation import validation_cases
from python_teaching.values import grade_snapshot


class ReviewValidationContractTests(unittest.TestCase):
    def test_cases_are_serializable_complete_and_distinct(self):
        units = {unit.key: unit for unit in lessons()}
        cases = validation_cases()
        self.assertEqual(len(cases), 26)
        self.assertEqual(json.loads(json.dumps(cases, ensure_ascii=False)), list(cases))
        self.assertEqual(len({case['id'] for case in cases}), len(cases))
        self.assertEqual({case['audit'] for case in cases}, {
            'intermediate_name', 'concat_index', 'preservation', 'empty_figure',
            'axes_position', 'scatter_correspondence', 'scatter_visibility',
            'colorbar_link',
        })
        for case in cases:
            with self.subTest(case=case['id']):
                self.assertEqual(set(case), {'id', 'audit', 'lesson', 'problem',
                                            'wrong', 'equivalent', 'reason'})
                self.assertIn(case['lesson'], units)
                self.assertTrue(case['lesson'].startswith('review_'))
                self.assertIs(type(case['problem']), int)
                self.assertIn(case['problem'], range(3))
                self.assertTrue(case['reason'])
                self.assertNotEqual(case['wrong'], case['equivalent'])
                for kind in ('wrong', 'equivalent'):
                    self.assertIsInstance(case[kind], str)
                    ast.parse(case[kind], filename=f"{case['id']}:{kind}")

    def test_original_audit_alternatives_remain_explicit(self):
        self.assertEqual(tuple(case['id'] for case in validation_cases()[:9]), (
            'totals_intermediate_name', 'concat_original_index',
            'center_preserves_source', 'stock_preserves_sources',
            'scratch_zero_axes', 'vertical_axes_created_bottom_first',
            'scatter_split_collections', 'scatter_reordered_rows',
            'horizontal_axes_created_right_first',
        ))

    def test_mutation_rejection_has_a_stated_preservation_goal(self):
        units = {unit.key: unit for unit in lessons()}
        for key, number in (('review_np_03', 2), ('review_pd_03', 1)):
            with self.subTest(lesson=key):
                self.assertIn('보존', units[key].problems[number].goal)

    def test_callers_cannot_mutate_future_case_data(self):
        cases = validation_cases()
        original = cases[0]['equivalent']
        cases[0]['equivalent'] = 'changed by a consumer'
        self.assertEqual(validation_cases()[0]['equivalent'], original)


_HAS_LIBRARIES = all(importlib.util.find_spec(name) for name in
                     ('numpy', 'pandas', 'matplotlib', 'scipy'))


@unittest.skipUnless(_HAS_LIBRARIES, 'Requires actual NumPy/pandas/Matplotlib/SciPy')
class ReviewGradingExecutionTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory(prefix='shellground-review-grading-')
        self.previous_cwd = Path.cwd()
        self.previous_mplconfig = os.environ.get('MPLCONFIGDIR')
        os.environ['MPLCONFIGDIR'] = str(Path(self.folder.name) / '.mpl-cache')
        self.units = {unit.key: unit for unit in lessons()}

    def tearDown(self):
        os.chdir(self.previous_cwd)
        if self.previous_mplconfig is None:
            os.environ.pop('MPLCONFIGDIR', None)
        else:
            os.environ['MPLCONFIGDIR'] = self.previous_mplconfig
        self.folder.cleanup()

    def grade(self, problem, code=None):
        from python_teaching.worker import Kernel
        previous_path = sys.path[:]
        # File exports and imported fixture modules must not leak between cases.
        fixture_modules = [Path(name).stem for name in problem.files
                           if name.endswith('.py')]
        saved_modules = {name: sys.modules.get(name) for name in fixture_modules}
        previous_cwd = Path.cwd()
        kernel = None
        try:
            with tempfile.TemporaryDirectory(prefix='case-', dir=self.folder.name) as folder:
                os.chdir(folder)
                for name in fixture_modules:
                    sys.modules.pop(name, None)
                for name, spec in problem.files.items():
                    target = Path(folder) / name
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_text(spec['text'], encoding=spec.get('encoding', 'utf-8'))
                kernel = Kernel(folder)
                setup = kernel.execute(problem.initial)
                self.assertTrue(setup['ok'], setup)
                if code is not None:
                    executed = kernel.execute(code)
                    self.assertTrue(executed['ok'], executed)
                values, errors = kernel.inspect_values(problem.targets, problem.probes)
                if code is not None:
                    self.assertFalse(errors, errors)
                return grade_snapshot(values, problem.checks)
        finally:
            if kernel is not None:
                kernel.plt.close('all')
            os.chdir(previous_cwd)
            sys.path[:] = previous_path
            for name, module in saved_modules.items():
                if module is None:
                    sys.modules.pop(name, None)
                else:
                    sys.modules[name] = module

    def test_all_thirteen_reviews_have_incomplete_fixtures_and_passing_solutions(self):
        reviews = [unit for unit in self.units.values() if unit.key.startswith('review_')]
        self.assertEqual(len(reviews), 13)
        self.assertEqual(sum(len(unit.problems) for unit in reviews), 39)
        for unit in reviews:
            for number, problem in enumerate(unit.problems):
                with self.subTest(lesson=unit.key, problem=number, kind='initial'):
                    self.assertFalse(self.grade(problem)['passed'], 'Fixture already solved')
                with self.subTest(lesson=unit.key, problem=number, kind='reference'):
                    result = self.grade(problem, problem.solution)
                    self.assertTrue(result['passed'], result)

    def test_wrong_rejected_and_equivalent_accepted(self):
        for case in validation_cases():
            problem = self.units[case['lesson']].problems[case['problem']]
            for kind, expected in (('wrong', False), ('equivalent', True)):
                with self.subTest(case=case['id'], lesson=case['lesson'],
                                  problem=case['problem'], kind=kind):
                    result = self.grade(problem, case[kind])
                    failed = [item for item in result.get('checks', ())
                              if not item.get('passed')]
                    self.assertEqual(result['passed'], expected,
                                     (case['reason'], failed or result))


if __name__ == '__main__':
    unittest.main()
