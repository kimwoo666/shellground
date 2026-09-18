import unittest
import tempfile
from python_teaching.coverage_course import lessons,validation_cases
from python_teaching.values import grade_snapshot


class CoverageAnswers(unittest.TestCase):
    def test_wrong_and_equivalent_real_library_answers(self):
        from python_teaching.worker import Kernel
        units={u.key:u for u in lessons()}
        with tempfile.TemporaryDirectory() as directory:
            kernel=Kernel(directory)
            try:
                for case in validation_cases():
                    task=units[case['lesson']].problems[case['problem']]
                    for kind,expected in [('wrong',False),('equivalent',True)]:
                        with self.subTest(unit=case['lesson'],variant=case['problem'],kind=kind):
                            kernel.plt.close('all');kernel.namespace={'__name__':'__main__'}
                            self.assertTrue(kernel.execute(task.initial)['ok'])
                            response=kernel.execute(case[kind]);self.assertTrue(response['ok'],response)
                            values,_=kernel.inspect_values(task.targets,task.probes)
                            grade=grade_snapshot(values,task.checks);self.assertEqual(grade['passed'],expected,grade)
            finally:kernel.plt.close('all')


if __name__=='__main__':unittest.main()
