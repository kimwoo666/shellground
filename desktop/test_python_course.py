"""Execute every authored practical task against the actual libraries."""
import importlib.util
import os
from pathlib import Path
import tempfile
import unittest
from python_teaching.course import lessons
from python_teaching.values import grade_snapshot


class CourseStructureTests(unittest.TestCase):
    def test_reviews_follow_exactly_five_original_units(self):
        from python_teaching.review_course import insert_reviews
        expanded=lessons()
        original=tuple(u for u in expanded if not u.key.startswith('review_'))
        reviews=[u for u in expanded if u.key.startswith('review_')]
        self.assertEqual(len(reviews),13)
        self.assertEqual(insert_reviews(expanded),expanded)
        self.assertEqual(tuple(u for u in insert_reviews(original) if not u.key.startswith('review_')),original)
        for unit in reviews:
            before=[u.key for u in expanded[:expanded.index(unit)] if u.topic==unit.topic and not u.key.startswith('review_')]
            self.assertEqual(unit.prerequisites,tuple(before[-5:]))

    def test_keys_prerequisites_and_sources(self):
        keys = set()
        counts = {'Week 1_1.pdf':15,'week_1_2_handout.pdf':34,
                  'week_2_1_handout.pdf':41,'week_2_2_handout.pdf':42,'week_3_1_handout.pdf':46}
        for unit in lessons():
            self.assertNotIn(unit.key, keys)
            self.assertTrue(set(unit.prerequisites) <= keys, unit.key)
            keys.add(unit.key)
            self.assertEqual(len(unit.problems), 3, unit.key)
            self.assertTrue(unit.explanation and unit.pitfall and unit.syntax)
            if unit.source=='supplement': self.assertEqual(unit.pages,())
            else: self.assertTrue(all(0 < p <= counts[unit.source] for p in unit.pages))
            for problem in unit.problems:
                self.assertTrue(problem.goal and problem.solution and problem.checks)
                compile(problem.initial, '<fixture>', 'exec')
                compile(problem.solution, '<solution>', 'exec')


@unittest.skipUnless(all(importlib.util.find_spec(p) for p in ('numpy','pandas','matplotlib')), 'scientific Python dependencies unavailable')
class CourseExecutionTests(unittest.TestCase):
    def test_all_solutions_and_unsolved_fixtures(self):
        from python_teaching.worker import Kernel
        from python_teaching.values import snapshot
        original = Path.cwd()
        try:
            with tempfile.TemporaryDirectory(prefix='shellground-course-test-') as folder:
                os.chdir(folder)
                os.environ['MPLCONFIGDIR'] = str(Path(folder)/'.mpl-cache')
                kernel = Kernel(folder)
                for unit in lessons():
                    for i, problem in enumerate(unit.problems):
                        with self.subTest(unit=unit.key, variant=i):
                            kernel.plt.close('all')
                            kernel.namespace = {'__name__':'__main__'}
                            for name,spec in problem.files.items():
                                path = Path(folder)/name
                                path.parent.mkdir(parents=True,exist_ok=True)
                                path.write_text(spec['text'],encoding=spec.get('encoding','utf-8'))
                            result = kernel.execute(problem.initial)
                            self.assertTrue(result['ok'],result['output'])
                            def state():
                                return kernel.inspect_values(problem.targets,problem.probes)[0]
                            self.assertFalse(grade_snapshot(state(),problem.checks)['passed'],'fixture already satisfies all goals')
                            result = kernel.execute(problem.solution)
                            self.assertTrue(result['ok'],result['output'])
                            grade = grade_snapshot(state(),problem.checks)
                            self.assertTrue(grade['passed'],str(grade))
                kernel.plt.close('all')
        finally: os.chdir(original)


if __name__ == '__main__': unittest.main()
