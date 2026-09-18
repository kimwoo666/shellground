import ast
import base64
import json
from pathlib import Path
import subprocess
import unittest
from unittest.mock import patch

from conda_teaching.engine import course,pip_course
from conda_teaching.guest_runtime import validate_package_roster
from conda_teaching.pip_runtime import package_file,uses_pip
from conda_teaching.pip_assets import install_assets,TRANSFER


class PipCourseTests(unittest.TestCase):
    def test_append_preserves_all_existing_units_and_counts(self):
        original=course(include_pip=False);extended=course()
        self.assertEqual(extended['units'][:18],original['units'])
        self.assertEqual([u['key'] for u in extended['units'][18:]],['pip_install','pip_remove_repair'])
        self.assertEqual(extended['counts']['problems'],sum(len(u['problems']) for u in extended['units']))

    def test_authored_commands_actions_and_expected_failures(self):
        spec=pip_course();self.assertEqual(spec['counts']['learning_steps'],8)
        for unit in spec['units']:
            for item in unit['problems']+unit['learning_steps']:
                actions=item.get('reference_actions',item.get('actions'))
                commands=item.get('reference_commands',item.get('commands'))
                self.assertEqual([a['command'] for a in actions],commands)
                for action in actions:
                    checked=subprocess.run(['bash','-n'],input=action['command'],text=True,capture_output=True)
                    self.assertEqual(checked.returncode,0,checked.stderr)
                    self.assertIn(action['exit_codes'],([0],[1]))
                    if action['exit_codes']==[1]:self.assertTrue(action['expectation_reason'])
                    for response in action['responses']:
                        self.assertEqual(response,dict(prompt='Proceed (Y/n)?',reply='y'))
            for problem in unit['problems']:
                self.assertTrue(uses_pip(problem))
                for criterion in problem['grade_criteria']:
                    self.assertIn(criterion['operation'],course()['grading_operations'])
                self.assertTrue(problem['fixture_summary']);self.assertTrue(problem['provided_diagnostics'])
                for diagnostic in problem['provided_diagnostics']:
                    self.assertNotIn(' install ',diagnostic);self.assertNotIn(' uninstall ',diagnostic)

    def test_only_declared_pypi_roster_extras_are_permitted(self):
        recorded={'python':{},'pip':{}};base={'python':{},'pip':{}}
        numpy=dict(channel='pypi',build_string='pypi_0')
        validate_package_roster(recorded,base)
        validate_package_roster(recorded,dict(base,numpy=numpy),('numpy',))
        for listed,allowed in ((dict(base,numpy=numpy),()),(dict(base,other=numpy),('numpy',)),
                               (dict(base,numpy=dict(channel='wrong',build_string='pypi_0')),('numpy',)),
                               ({'python':{}},('numpy',))):
            with self.assertRaises(ValueError):validate_package_roster(recorded,listed,allowed)

    def test_owned_package_paths_and_mixed_fixture_rejected(self):
        for value in ('','.','..','../pip','/etc/passwd','lib/../../outside','lib\\bad'):
            with self.assertRaises(ValueError):package_file(value)
        self.assertEqual(package_file('site-packages/pip/__init__.py'),'lib/python3.12/site-packages/pip/__init__.py')
        self.assertEqual(package_file('python-scripts/pip'),'bin/pip')
        with self.assertRaises(ValueError):uses_pip({'initial_fixture':{'environments':[
            {'pip_distributions':[]},{}]}})

    def test_asset_transfer_is_chunked_below_protocol_limit(self):
        from conda_teaching.pip_assets import wheel_path
        path=wheel_path();calls=[];published=False
        class Channel:
            def request(self,action,**kwargs):
                nonlocal published
                command=kwargs['argv'][3];data=base64.b64decode(kwargs['input'])
                calls.append((command,data,int(kwargs['argv'][-1])))
                self_outer.assertLess(len(json.dumps(kwargs).encode()),4*1024*1024)
                self_outer.assertTrue(kwargs['root'])
                if command=='finish':published=True
                return dict(code=0,out=base64.b64encode(b'ready' if published else b'missing').decode(),err='')
        self_outer=self
        with patch('conda_teaching.pip_assets.load_numpy_wheel') as validate:
            install_assets(Channel());validate.assert_called_once_with(path)
        chunks=[(data,offset) for op,data,offset in calls if op=='chunk']
        self.assertGreater(len(chunks),1)
        self.assertEqual(b''.join(data for data,_ in chunks),path.read_bytes())
        offset=0
        for data,position in chunks:self.assertEqual(position,offset);offset+=len(data)
        ast.parse(TRANSFER,feature_version=(3,10))


if __name__=='__main__':unittest.main()
