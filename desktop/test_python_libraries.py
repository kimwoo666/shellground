"""Actual-library misconception/equivalence regressions for supplemental units."""
import importlib.util
import os
from pathlib import Path
import tempfile
import unittest
from python_teaching.library_course import lessons,validation_cases
from python_teaching.values import grade_snapshot


class LibraryCourseContractTests(unittest.TestCase):
    def test_supplements_and_visible_fixtures(self):
        units=lessons()
        self.assertEqual(len(units),6)
        self.assertEqual(len(validation_cases()),23)
        for unit in units:
            self.assertEqual(unit.source,'supplement')
            self.assertEqual(unit.pages,())
            self.assertIn('PDF',unit.provenance_note)
            for problem in unit.problems:
                self.assertTrue(problem.prepared_code)
                self.assertNotIn('def _',problem.prepared_code)
                self.assertTrue(problem.initial.startswith(problem.prepared_code))


@unittest.skipUnless(all(importlib.util.find_spec(name) for name in
                        ('numpy','pandas','matplotlib','seaborn','sklearn')),
                     'Requires the actual scientific Python libraries')
class LibraryExecutionTests(unittest.TestCase):
    def test_seaborn_first_learning_code_uses_prepared_data(self):
        from python_teaching.worker import Kernel
        previous=Path.cwd()
        try:
            with tempfile.TemporaryDirectory(prefix='shellground-library-syntax-') as folder:
                os.chdir(folder);kernel=Kernel(folder)
                for unit in lessons()[:3]:
                    with self.subTest(lesson=unit.key):
                        kernel.plt.close('all');kernel.namespace={'__name__':'__main__'}
                        self.assertTrue(kernel.execute(unit.problems[0].initial)['ok'])
                        result=kernel.execute(unit.syntax)
                        self.assertTrue(result['ok'],result)
                kernel.plt.close('all')
        finally:os.chdir(previous)

    def test_wrong_rejected_and_equivalent_accepted(self):
        from python_teaching.worker import Kernel
        previous=Path.cwd()
        try:
            with tempfile.TemporaryDirectory(prefix='shellground-library-test-') as folder:
                os.chdir(folder);kernel=Kernel(folder)
                units={unit.key:unit for unit in lessons()}
                for case in validation_cases():
                    problem=units[case['lesson']].problems[case['problem']]
                    for kind,expected in (('wrong',False),('equivalent',True)):
                        with self.subTest(lesson=case['lesson'],problem=case['problem'],kind=kind):
                            kernel.plt.close('all');kernel.namespace={'__name__':'__main__'}
                            setup=kernel.execute(problem.initial)
                            self.assertTrue(setup['ok'],setup)
                            result=kernel.execute(case[kind])
                            self.assertTrue(result['ok'],result)
                            values,_=kernel.inspect_values(problem.targets,problem.probes)
                            grade=grade_snapshot(values,problem.checks)
                            self.assertEqual(grade['passed'],expected,(case['reason'],grade))
                kernel.plt.close('all')
        finally:os.chdir(previous)


if __name__=='__main__':unittest.main()
