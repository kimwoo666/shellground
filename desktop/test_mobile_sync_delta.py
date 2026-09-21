"""Only changed port contracts; no replay of solved full-course examples."""
from copy import deepcopy
from dataclasses import asdict
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'android/app/src/main/python'))
from mobile_progress import SCOPES, export_preferences, import_preferences, exchange
from mobile_bridge import select_problem
from nas_sync import FolderStore, Synchronizer, atomic_json, read_json, MARKER
from python_teaching.course import lessons


class MobileDeltaTests(unittest.TestCase):
    def setUp(self):
        self.catalogs={scope:[{'key':'unit','learning_steps':[{'title':'A'},{'title':'B'},{'title':'C'}]}] for scope in SCOPES}
        self.catalogs['real-linux-progress-v1'].append({'key':'review','review':True})
        self.catalogs.update(quizzes=[{'id':'quiz'}],cards=[{'id':'card','quiz_ids':['quiz']}])

    def test_completion_is_union_and_all_scopes_convert(self):
        prefs={scope:{'unit'+(':' if scope=='python-progress-v1' else ':done:')+str(v):True for v in (1,2)} for scope in SCOPES}
        prefs['real-linux-progress-v1'].update({'review:done:1':True,'review:done:2':True})
        docs=export_preferences(prefs,self.catalogs,{'python-progress-v1.json':{'schema':1,'completed':['older'],'positions':{'older':{'step':3,'phase':'learn'}}}})
        for name in SCOPES.values():self.assertIn('unit',docs[name]['completed'])
        self.assertEqual(docs['progress-v3-real.json']['checkpoints'],['review'])
        self.assertIn('older',docs['python-progress-v1.json']['completed'])
        self.assertIn('older',docs['python-progress-v1.json']['positions'])
        self.assertEqual(import_preferences(docs,self.catalogs,{})['real-linux-progress-v1']['unit:done:2'],True)

    def test_cursor_quiz_and_private_fields(self):
        prefs={'python-progress-v1':{'last':'unit','unit.phase':0,'unit.step':2,'quiz.quiz':True,'card.quiz':0,'password':'PRIVATE','editor':'PRIVATE'},
               'real-linux-progress-v1':{'last':'unit','unit:phase':0,'unit:step':1},
               'real-conda-progress-v1':{'conda_install_once:done':True}}
        docs=export_preferences(prefs,self.catalogs,{})
        self.assertNotIn('PRIVATE',json.dumps(docs))
        self.assertEqual(docs['python-progress-v1.json']['positions']['unit'],{'phase':'learn','step':2})
        self.assertEqual(docs['progress-v3-real.json']['learning']['unit']['cursor'],'B')
        restored=import_preferences(docs,self.catalogs,{})
        for scope,values in prefs.items():
            for key,value in values.items():
                if key not in ('password','editor'):self.assertEqual(restored[scope][key],value)

    def test_pc_android_pc_roundtrip_and_offline_preserve(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);nas=root/'nas';nas.mkdir();pc=root/'pc';pc.mkdir();phone=root/'phone';phone.mkdir()
            atomic_json(nas/MARKER,{'schema':1,'profile':'test'})
            config={'transport':'folder','folder':str(nas),'profile':'test'}
            atomic_json(pc/'python-progress-v1.json',{'schema':1,'completed':['older'],'passed':['unit:1'],
                'positions':{'unit':{'phase':'learn','step':2}},'resume':{'unit':'unit','phase':'learn','step':2}})
            Synchronizer(pc,config).synchronize(True)
            class Remote:
                def read(self,name):return json.dumps(read_json(nas/name))
                def names(self):return FolderStore(nas).names()
                def write(self,name,data):atomic_json(nas/name,json.loads(data))
            received=json.loads(exchange(phone,'{}',json.dumps(self.catalogs),Remote(),True))['preferences']
            self.assertEqual(received['python-progress-v1']['unit.step'],2)
            self.assertTrue(received['python-progress-v1']['unit:1'])
            received['python-progress-v1'].update({'unit:2':True,'unit.phase':3})
            exchange(phone,json.dumps(received),json.dumps(self.catalogs),Remote(),False)
            Synchronizer(pc,config).synchronize(True)
            result=read_json(pc/'python-progress-v1.json')
            self.assertEqual(set(result['completed']),{'older','unit'})
            self.assertEqual(result['positions']['unit']['phase'],'practice2')
            exchange(phone,json.dumps(received),json.dumps(self.catalogs),None,False)
            self.assertTrue(read_json(phone/'python-progress-v1.json')['completed'])

    def test_learning_checks_do_not_create_completion(self):
        docs=export_preferences({'python-progress-v1':{'last':'unit','unit.phase':0,'unit.step':2}},self.catalogs,{})
        self.assertEqual(docs['python-progress-v1.json'].get('completed',[]),[])
        self.assertEqual(docs['python-progress-v1.json'].get('passed',[]),[])

    def test_all_pandas_guided_steps_select_exact_fixtures_and_checks(self):
        units=lessons();count=0
        for unit in units:
            for at,step in enumerate(unit.guided_steps):
                selected,identity=select_problem(dict(unit=unit.key,phase='learn',step=at,variant=0))
                self.assertEqual(asdict(selected),asdict(step.practice));self.assertEqual(identity,at);count+=1
            for variant in range(len(unit.problems)):
                selected,identity=select_problem(dict(unit=unit.key,phase='practice1',step=0,variant=variant))
                self.assertEqual(selected,unit.problems[variant]);self.assertIsNone(identity)
        self.assertEqual(count,81)
        unit=next(u for u in units if u.guided_steps)
        with self.assertRaises(ValueError):select_problem(dict(unit=unit.key,phase='learn',step=-1))


if __name__=='__main__':unittest.main()
