import ast
import json
from pathlib import Path
import subprocess
import unittest
from conda_teaching.engine import course
from conda_teaching.guest_runtime import prefix,artifact


class CondaCourseTests(unittest.TestCase):
    def test_full_scope_and_supported_actual_grades(self):
        data=course();units=data['units'];self.assertEqual(len(units),20)
        self.assertEqual(sum(len(u['problems']) for u in units),60)
        self.assertEqual(sum(u['key'].startswith('review_') for u in units),3)
        self.assertFalse(set(data['grading_operations']) & {'executed','executed_in','recreated_from','export_executed'})
        ids=[]
        for unit in units:
            self.assertTrue(unit['explanation']);self.assertGreaterEqual(len(unit['microsteps']),2)
            for problem in unit['problems']:
                ids.append(problem['id']);fixture=problem['initial_fixture']
                known={e['name'] for e in fixture['environments']};created=set(fixture['created_envs'])
                self.assertFalse(known & created);self.assertTrue(created<=set(fixture['absent_envs']))
                self.assertTrue(set(fixture['removed_envs'])<=known)
                self.assertTrue(set(fixture['mutable_envs'])<=known|created)
                for criterion in problem['grade_criteria']:self.assertIn(criterion['operation'],data['grading_operations'])
                self.assertTrue(problem['representative_wrong_answers']);self.assertTrue(problem['equivalent_solutions'])
        self.assertEqual(len(ids),len(set(ids)))

    def test_reference_shell_syntax_only_never_host_execution(self):
        for unit in course()['units']:
            for problem in unit['problems']:
                result=subprocess.run(['bash','-n'],input='\n'.join(problem['reference_commands']),text=True,capture_output=True)
                self.assertEqual(result.returncode,0,problem['id']+result.stderr)

    def test_grader_paths_cannot_point_at_host_or_other_guest_roots(self):
        for name in ('/root','../outside','sg-../../root','','base/../bad'):
            with self.assertRaises(ValueError):prefix(name)
        for path in ('/root/result.yml','../../outside'):
            with self.assertRaises(ValueError):artifact(path)
        self.assertEqual(str(prefix('sg-work')),'/home/learner/conda-envs/sg-work')

    def test_guest_entrypoints_compile_on_guest_python_syntax(self):
        for path in ('conda_teaching/guest_runtime.py','guest/conda_lab.py','guest/agent.py'):
            ast.parse(Path(path).read_text(),feature_version=(3,10))


if __name__=='__main__':unittest.main()
