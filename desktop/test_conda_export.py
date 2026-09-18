from copy import deepcopy
import unittest
import tempfile
from pathlib import Path
from conda_teaching.engine import course
from conda_teaching.export_runtime import validate_report,validate_learning,export_destination,ANSWER_CASES
from conda_teaching.setup_smoke import validate_setup,setup_fingerprint,CASES
from conda_teaching.pip_acceptance import CASES as PIP_CASES


class CondaExportGateTests(unittest.TestCase):
    def setUp(self):
        self.spec=course()
        self.report={'count':60,'fingerprint':'current-source','answer_cases':sorted(ANSWER_CASES),
                     'state':'complete','fixture_clean':True,
                     'passed':[p['id'] for u in self.spec['units'] for p in u['problems']],
                     'negative_repair':['conda_activate_example','conda_install_example','conda_export_intent_example','conda_update_preserve']}
        self.report['answer_cases'].extend(key+'/'+case for key,cases in PIP_CASES.items() for case in cases)

    def test_current_complete_report(self):
        validate_report(self.report,self.spec,'current-source')

    def test_interrupted_or_unclean_builder_cannot_export_old_passes(self):
        for changes in ({'state':'in_progress'},{'state':'failed'},{'fixture_clean':False}):
            with self.subTest(changes=changes),self.assertRaises(RuntimeError):
                validate_report(dict(self.report,**changes),self.spec,'current-source')

    def test_count_without_each_real_problem_is_not_proof(self):
        report=deepcopy(self.report);report['passed'][-1]='unknown-problem'
        with self.assertRaises(RuntimeError):validate_report(report,self.spec,'current-source')

    def test_arbitrary_three_negatives_are_not_proof(self):
        report=deepcopy(self.report);report['negative_repair']=['one','two','three']
        with self.assertRaises(RuntimeError):validate_report(report,self.spec,'current-source')

    def test_stale_or_partial_report_is_not_proof(self):
        with self.assertRaises(RuntimeError):validate_report(self.report,self.spec,'new-source')
        report=deepcopy(self.report);report['count']=15;report['passed']=report['passed'][:15]
        with self.assertRaises(RuntimeError):validate_report(report,self.spec,'current-source')

    def test_equivalent_and_wrong_answers_must_be_verified(self):
        report=deepcopy(self.report);report['answer_cases'].pop()
        with self.assertRaises(RuntimeError):validate_report(report,self.spec,'current-source')

    def test_pip_final_state_negatives_cannot_be_replaced_by_happy_paths(self):
        report=deepcopy(self.report);report['answer_cases']=sorted(ANSWER_CASES)
        with self.assertRaises(RuntimeError):validate_report(report,self.spec,'current-source')

    def test_learning_requires_all_units_and_both_current_sources(self):
        report={'count':20,'passed':[unit['key'] for unit in self.spec['units']],
                'course_fingerprint':'course','fingerprint':'steps','state':'complete','fixture_clean':True}
        validate_learning(report,self.spec,'course','steps')
        for changes in ({'state':'in_progress'},{'state':'failed'},{'fixture_clean':False}):
            with self.assertRaises(RuntimeError):validate_learning(dict(report,**changes),self.spec,'course','steps')
        for course_hash,steps_hash in (('new','steps'),('course','new')):
            with self.assertRaises(RuntimeError):validate_learning(report,self.spec,course_hash,steps_hash)
        report['passed']=report['passed'][:-1]
        with self.assertRaises(RuntimeError):validate_learning(report,self.spec,'course','steps')

    def test_setup_requires_actual_install_and_all_negative_repairs(self):
        report=dict(fingerprint=setup_fingerprint(),count=len(CASES),passed=sorted(CASES),actual_installer_exit=0)
        validate_setup(report)
        for key,value in (('fingerprint','old'),('count',1),('passed',['actual_new_install']),('actual_installer_exit',1)):
            with self.assertRaises(RuntimeError):validate_setup(dict(report,**{key:value}))

    def test_versioned_export_preserves_existing_runtime(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);old=root/'.vm-runtime-conda/linux-x86_64';old.mkdir(parents=True)
            marker=old/'keep.txt';marker.write_text('existing verified runtime')
            with self.assertRaises(RuntimeError):export_destination(None,root)
            new=export_destination('.vm-runtime-conda/review-install/linux-x86_64',root)
            self.assertFalse(new.exists());self.assertTrue(new.is_relative_to(root))
            self.assertEqual(marker.read_text(),'existing verified runtime')

    def test_export_rejects_escape_and_symlink_alias(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);(root/'alias').symlink_to(root,target_is_directory=True)
            for name in ('../outside','alias/new','alias','.'):
                with self.subTest(name=name),self.assertRaises(RuntimeError):export_destination(name,root)


if __name__=='__main__':unittest.main()
