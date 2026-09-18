"""Explicit full or changed-only proof through a built app's bundled worker."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from python_teaching.engine import worker_environment


@unittest.skipUnless(os.environ.get('SHELLGROUND_TEST_PACKAGED'),
                     'Requires an explicit freshly built application path')
class PackagedPythonCourseTests(unittest.TestCase):
    def test_entire_bundled_course_and_library_variants(self):
        binary=Path(os.environ['SHELLGROUND_TEST_PACKAGED']).resolve(strict=True)
        scope=os.environ.get('SHELLGROUND_PACKAGED_SCOPE', 'changed')
        self.assertIn(scope, ('changed', 'full'))
        code='''
import sys
from pathlib import Path
import numpy, pandas, matplotlib, seaborn, sklearn
assert sys.frozen
for library in (numpy,pandas,matplotlib,seaborn,sklearn):
    assert Path(library.__file__).resolve().is_relative_to(Path(sys._MEIPASS)), library.__file__
from python_teaching.course import lessons
from python_teaching.library_course import validation_cases
from python_teaching.review_validation import validation_cases as review_cases
from python_teaching.coverage_course import validation_cases as coverage_cases
from python_teaching.worker import Kernel
from python_teaching.values import grade_snapshot
kernel=Kernel(Path.cwd())
units=lessons()
scope=__SCOPE__
changed={'pd_datetime_index','pd_weather_audit','pd_series_charts','pd_concat_labels'}
selected=[u for u in units if scope=='full' or u.key in changed]
assert len(selected)==(95 if scope=='full' else 4),[u.key for u in selected]
checked=0
for unit in selected:
    for number,task in enumerate(unit.problems):
        kernel.plt.close('all')
        kernel.namespace={'__name__':'__main__'}
        for name,spec in task.files.items():
            path=Path(name)
            path.parent.mkdir(parents=True,exist_ok=True)
            path.write_text(spec['text'],encoding=spec.get('encoding','utf-8'))
        prepared=kernel.execute(task.initial)
        assert prepared['ok'],(unit.key,number,prepared)
        values,errors=kernel.inspect_values(task.targets,task.probes)
        assert not grade_snapshot(values,task.checks)['passed'],(unit.key,number,'already solved')
        result=kernel.execute(task.solution)
        assert result['ok'],(unit.key,number,result)
        values,errors=kernel.inspect_values(task.targets,task.probes)
        grade=grade_snapshot(values,task.checks)
        assert grade['passed'],(unit.key,number,grade,errors)
        checked+=1
by_key={unit.key:unit for unit in units}
variants=0
all_cases=(list(validation_cases())+list(review_cases())+list(coverage_cases())) if scope=='full' else coverage_cases()
for case in all_cases:
    task=by_key[case['lesson']].problems[case['problem']]
    for kind,expected in [('wrong',False),('equivalent',True)]:
        kernel.plt.close('all')
        kernel.namespace={'__name__':'__main__'}
        for name,spec in task.files.items():
            path=Path(name)
            path.parent.mkdir(parents=True,exist_ok=True)
            path.write_text(spec['text'],encoding=spec.get('encoding','utf-8'))
        prepared=kernel.execute(task.initial)
        assert prepared['ok'],prepared
        result=kernel.execute(case[kind])
        assert result['ok'],result
        values,errors=kernel.inspect_values(task.targets,task.probes)
        grade=grade_snapshot(values,task.checks)
        assert grade['passed']==expected,(case['lesson'],case['problem'],kind,grade,errors)
        variants+=1
kernel.plt.close('all')
assert len(units)==95 and checked==3*len(selected) and variants==2*len(all_cases),(len(units),checked,variants)
if scope=='full':assert len(validation_cases())==23 and len(review_cases())>=9
print('BUNDLED_REAL_COURSE_OK',scope,len(selected),checked,variants)
'''
        code=code.replace('__SCOPE__',repr(scope))
        with tempfile.TemporaryDirectory(prefix='shellground-packaged-test-') as folder:
            root=Path(folder);(root/'.shellground-python-session').write_text('1')
            requests=json.dumps({'action':'execute','code':code})+'\n'+json.dumps({'action':'close'})+'\n'
            result=subprocess.run([str(binary),'--internal-python-worker',str(root)],
                input=requests,capture_output=True,text=True,encoding='utf-8',cwd=root,
                env=worker_environment(Path(__file__).resolve().parent),timeout=120)
            self.assertEqual(result.returncode,0,result.stderr[-3000:])
            messages=[json.loads(line) for line in result.stdout.splitlines()]
            self.assertTrue(messages[0]['ready'])
            self.assertTrue(messages[1]['ok'],messages[1])
            self.assertIn('BUNDLED_REAL_COURSE_OK '+scope+(' 95 285 ' if scope=='full' else ' 4 12 '),messages[1]['output'])
            print(messages[1]['output'].strip())


if __name__=='__main__':unittest.main()
