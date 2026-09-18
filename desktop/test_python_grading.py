"""Wrong-answer rejection and semantically equivalent correct alternatives."""
import importlib.util
import os
from pathlib import Path
import tempfile
import unittest
from python_teaching.course import lesson_by_key
from python_teaching.values import grade_snapshot


@unittest.skipUnless(all(importlib.util.find_spec(p) for p in ('numpy','pandas','matplotlib')), 'scientific Python dependencies unavailable')
class GradingTests(unittest.TestCase):
    def setUp(self):
        self.folder=tempfile.TemporaryDirectory(prefix='shellground-grading-')
        self.previous=Path.cwd(); os.chdir(self.folder.name)
        os.environ['MPLCONFIGDIR']=str(Path(self.folder.name)/'.mpl-cache')
        from python_teaching.worker import Kernel
        self.kernel=Kernel(self.folder.name)
    def tearDown(self):
        self.kernel.plt.close('all'); os.chdir(self.previous); self.folder.cleanup()
    def grade(self,key,variant,code):
        p=lesson_by_key(key).problems[variant]
        self.kernel.namespace={'__name__':'__main__'}; self.kernel.plt.close('all')
        for name,spec in p.files.items():
            path=Path(self.folder.name)/name;path.parent.mkdir(parents=True,exist_ok=True)
            path.write_text(spec['text'],encoding=spec.get('encoding','utf-8'))
        self.assertTrue(self.kernel.execute(p.initial)['ok'])
        run=self.kernel.execute(code); self.assertTrue(run['ok'],run['output'])
        return grade_snapshot(self.kernel.inspect_values(p.targets,p.probes)[0],p.checks)['passed']

    def test_dictionary_cannot_impersonate_real_array(self):
        self.assertFalse(self.grade('np_elementwise',0,"result={'kind':'array','data':[3,8,12],'shape':[3]}"))
    def test_function_is_called_with_other_inputs(self):
        self.assertFalse(self.grade('py_functions',0,'results=[6,-4]\ndef double(x): return 6'))
    def test_saved_blank_figure_is_not_correct_export(self):
        self.assertFalse(self.grade('plot_save',0,"fig,ax=plt.subplots(figsize=(4,3))\nax.plot(x,y)\nother=plt.figure(figsize=(4,3))\nother.savefig('report.png',dpi=100)"))
    def test_invalid_svg_is_rejected(self):
        self.assertFalse(self.grade('plot_save',1,"fig,ax=plt.subplots()\nax.plot(x,y)\nopen('vector.svg','w').write('<svg')"))
    def test_different_valid_svg_is_rejected(self):
        self.assertFalse(self.grade('plot_save',1,"fig,ax=plt.subplots()\nax.plot(x,y)\nother=plt.figure()\nother.savefig('vector.svg')"))
    def test_pandas_plot_wrong_x_axis_is_rejected(self):
        self.assertFalse(self.grade('pd_plot',2,"import matplotlib.pyplot as plt\nresult=df.T\nfig,ax=plt.subplots()\nax.plot([99,100],[80,70])"))
    def test_subplot_wrong_layout_rejected(self):
        self.assertFalse(self.grade('plot_subplots',2,'fig,axs=plt.subplots(1,3)\naxs[0].plot(x,x)\naxs[1].plot(x,x*x)\naxs[2].plot(x,x+1)'))
    def test_empty_axes_not_a_colorbar(self):
        self.assertFalse(self.grade('plot_heatmap',1,'fig,axs=plt.subplots(1,2)\naxs[0].imshow(a)'))
    def test_uniform_scatter_sizes_are_equivalent(self):
        self.assertTrue(self.grade('plot_scatter',0,'fig,ax=plt.subplots()\nax.scatter(x,y,s=[40,40,40])'))
    def test_rotated_pie_has_same_proportions(self):
        self.assertTrue(self.grade('plot_pie',0,"fig,ax=plt.subplots()\nax.pie(values,labels=['A','B'],autopct='%1.1f%%',startangle=90)"))
    def test_patch_boxes_are_equivalent(self):
        self.assertTrue(self.grade('plot_box',1,'fig,ax=plt.subplots()\nax.boxplot(data,patch_artist=True)\nq1,median,q3=np.percentile(data,[25,50,75])\niqr=q3-q1'))
    def test_fake_memory_self_report_rejected(self):
        self.assertFalse(self.grade('np_memory',2,'view=a[:,1].copy()\nview[0]=50\na[0,1]=50\nshared=True'))
    def test_alias_not_two_independent_generators(self):
        self.assertFalse(self.grade('np_random_generator',2,'a=np.random.default_rng(42)\nb=a\nfirst=a.integers(1,7,size=4)\nsecond=first'))

    def test_timing_invalid_and_hardware_independent_values(self):
        from python_teaching.timing_course import timing_check
        checks=[timing_check('samples',3)]
        for invalid in ([0,0,0],[.1,-.1,.2],[True,.1,.2],[.1,.2],[float('inf')]*3):
            self.assertFalse(grade_snapshot({'samples':invalid},checks)['passed'])
        for valid in ([1e-9,2e-9,3e-9],[1.,2.,3.]):
            self.assertTrue(grade_snapshot({'samples':valid},checks)['passed'])

    def test_group_threshold_is_after_aggregation(self):
        self.assertFalse(self.grade('pd_group_filter',0,"result=df.loc[df['visits']>=10].groupby('team')['visits'].sum()"))

    def test_scatter_needs_numeric_color_and_attached_scale(self):
        self.assertFalse(self.grade('plot_scatter_color',0,"fig,ax=plt.subplots()\nax.scatter(x,y,color='red')"))

    def test_review_wrong_answers_and_equivalent_solutions(self):
        cases=[
            ('review_py_01',0,False,lambda s:s+"\norder['total']=0"),
            ('review_py_02',2,False,lambda s:s+"\ndef remaining(required,done):\n    return ['array','table']"),
            ('review_np_01',0,False,lambda s:s+'\nresult=result.tolist()'),
            ('review_np_02',1,False,lambda s:s.replace('flat=column.flatten()','flat=column[:,0]')),
            ('review_np_03',1,False,lambda s:s.replace('std(ddof=1)','std(ddof=0)')),
            ('review_np_04',1,False,lambda s:s+'\nview=matrix[:,0].copy()'),
            ('review_plot_01',0,False,lambda s:s+"\nother,other_ax=plt.subplots(figsize=(4,3))\nother.savefig('review_sensor.png',dpi=100)"),
            ('review_plot_02',2,False,lambda s:s+'\npoints.colorbar.remove()\nfig.add_subplot(1,2,2)'),
            ('review_plot_03',1,False,lambda s:s.replace('density=True','density=False')),
            ('review_pd_01',0,False,lambda s:s+"\nresult=result['rain']"),
            ('review_pd_02',0,False,lambda s:s+"\ndf['mean']=df[['math','english','total']].mean(axis=1)"),
            ('review_pd_03',1,False,lambda s:s.replace("how='outer'","how='inner'")),
            ('review_pd_04',2,False,lambda s:s+'\nwide.index=[str(x) for x in wide.index]'),
            ('review_py_01',0,True,lambda s:s.replace('ordered=sorted(prices)','ordered=prices[:]\nordered.sort()')),
            ('review_np_01',0,True,lambda s:s.replace('result=raw-bias+offset','result=offset+(raw-bias)')),
            ('review_plot_01',1,True,lambda s:s.replace("ax.plot(x,change,color='blue',marker='s',linestyle='-')","ax.plot(x,change,'bs-')")),
            ('review_plot_02',0,True,lambda s:s.replace("autopct='%1.1f%%'","autopct='%1.1f%%',startangle=90")),
            ('review_pd_02',2,True,lambda s:s.replace('eligible.tail(1)','eligible.iloc[-1:]')),
            ('review_pd_04',1,True,lambda s:s.replace("df.pivot(index='day',columns='sensor',values='reading')","df.pivot_table(index='day',columns='sensor',values='reading',aggfunc='mean')")),
        ]
        for key,variant,expected,transform in cases:
            with self.subTest(key=key,variant=variant,equivalent=expected):
                self.assertEqual(self.grade(key,variant,transform(lesson_by_key(key).problems[variant].solution)),expected)


if __name__=='__main__': unittest.main()
