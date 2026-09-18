"""Only the new mobile export boundary; no existing lesson is executed again."""
import ast
import json
from pathlib import Path
import unittest
from export_port_assets import ROOT, DESKTOP, conda_data
from conda_teaching.engine import course
from notebook_teaching.course import lessons


class PortDeltaTests(unittest.TestCase):
    def test_conda_adapter_is_synced_before_lazy_guest_import(self):
        service=(ROOT/'android/app/src/main/java/org/shellground/learn/LinuxService.java').read_text()
        block=service.split('private void configureGraders(',1)[1].split('private byte[] readAsset(',1)[0]
        adapter='if(requested.equals("conda"))files.put("/opt/shellground/conda_lab.py",readAsset("real-guest/conda_lab.py"));'
        self.assertIn(adapter,block)
        self.assertLess(block.index(adapter),block.index('GuestAssets.sync('))

    def test_mobile_conda_changes_only_outer_guest_budget(self):
        original=(DESKTOP/'guest/conda_lab.py').read_text()
        exported=(ROOT/'android/app/build/generated/portAssets/real-guest/conda_lab.py').read_text()
        self.assertEqual(original.replace('timeout=115)','timeout=300)'),exported)
        original=(DESKTOP/'conda_teaching/guest_runtime.py').read_text()
        for old,new in [('def run(argv,timeout=45,input=None):','def run(argv,timeout=120,input=None):'),
            ('def conda(*args,timeout=45):','def conda(*args,timeout=120):'),
            ('timeout=8,input=json.dumps(request)','timeout=30,input=json.dumps(request)')]:
            original=original.replace(old,new)
        exported=(ROOT/'android/app/build/generated/portAssets/conda-guest/conda_runtime.py').read_text()
        self.assertEqual(original,exported)

    def test_mobile_notebook_changes_only_execution_budgets(self):
        expected={
            'guest_setup.py': [],
            'guest_service.py': [('self.client.wait_for_ready(timeout=20)',
                'self.client.wait_for_ready(timeout=120)'),
                ("def exchange(self, code='', expressions=None, timeout=10, history=True):",
                 "def exchange(self, code='', expressions=None, timeout=30, history=True):")],
            'guest_lessons.py': [('text=True, timeout=25)', 'text=True, timeout=120)'),
                ('time.monotonic()+20','time.monotonic()+60'),
                ('timeout=min(10,remaining)','timeout=min(30,remaining)')],
        }
        for name,changes in expected.items():
            original=(DESKTOP/'notebook_teaching'/name).read_text()
            for before,after in changes:original=original.replace(before,after)
            exported=(ROOT/'android/app/build/generated/portAssets/notebook-guest'/name).read_text()
            self.assertEqual(original,exported,name)

    def test_all_conda_problems_keep_the_same_grading_payload(self):
        original=course();mobile=conda_data()
        self.assertEqual(len(mobile['units']),20)
        self.assertEqual(sum(len(u['problems']) for u in mobile['units']),60)
        for a,b in zip(original['units'],mobile['units'],strict=True):
            self.assertEqual(a['key'],b['key'])
            for source,display in zip(a['problems'],b['problems'],strict=True):
                self.assertEqual(source,display['mission']['problem'])
                self.assertEqual(original['observer_contract']['module_probes'],display['mission']['probes'])
                self.assertFalse(any('expected' in field for field in display['answer_fields']))
                if source['role']!='example':self.assertEqual(display['example_commands'],[])

    def test_new_pip_and_notebook_steps_are_not_dropped(self):
        units=conda_data()['units']
        self.assertEqual([u['key'] for u in units[-2:]],['pip_install','pip_remove_repair'])
        for unit in units:self.assertTrue(unit['learning_steps'])
        notebook=lessons()
        self.assertEqual(sum(len(u['problems']) for u in notebook),18)
        self.assertTrue(all(u['steps'] for u in notebook))

    def test_arm_adapter_changes_only_official_wheel_identity(self):
        generated=ROOT/'android/app/build/generated/portAssets/conda-guest/pip_wheel.py'
        before=ast.parse((DESKTOP/'conda_teaching/pip_wheel.py').read_text())
        after=ast.parse(generated.read_text())
        def extract(tree):
            node=next(n for n in tree.body if isinstance(n,ast.Assign) and
                any(isinstance(t,ast.Name) and t.id=='NUMPY_WHEEL' for t in n.targets))
            value=ast.literal_eval(node.value);tree.body.remove(node);return value
        a,b=extract(before),extract(after)
        self.assertEqual(ast.dump(before),ast.dump(after))
        self.assertEqual(a['version'],b['version'])
        self.assertIn('aarch64',b['filename']);self.assertNotIn('x86_64',b['filename'])


if __name__=='__main__':unittest.main()
