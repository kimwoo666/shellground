import re
import subprocess
import unittest
from conda_teaching.engine import course
from conda_teaching.learning_steps import STEPS


class CondaLearningTests(unittest.TestCase):
    def test_all_units_have_small_fixture_compatible_steps(self):
        units=course()['units']
        self.assertEqual(set(STEPS),{unit['key'] for unit in units if 'learning_steps' not in unit})
        for unit in units:
            steps=unit.get('learning_steps') or STEPS[unit['key']];self.assertGreaterEqual(len(steps),2);self.assertLessEqual(len(steps),4)
            fixture=unit['problems'][0]['initial_fixture']
            allowed={e['name'] for e in fixture['environments']}|set(fixture['created_envs'])
            for step in steps:
                self.assertTrue(step['title'] and step['explanation'] and step['observe'])
                for command in step['commands']:
                    self.assertLessEqual(set(re.findall(r'\bsg-[a-z0-9-]+',command)),allowed,unit['key']+' '+command)
                    self.assertNotIn(command.strip(),('y','yes'))
                    result=subprocess.run(['bash','-n'],input=command,text=True,capture_output=True)
                    self.assertEqual(result.returncode,0,unit['key']+' '+result.stderr)


if __name__=='__main__':unittest.main()
