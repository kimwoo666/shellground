"""Answer normalization is semantic and bounded to this course's known types."""
import unittest
from conda_teaching.guest_runtime import answer_matches,preserved_snapshot


class CondaAnswerTests(unittest.TestCase):
    def test_equivalent_absolute_paths(self):
        expected='/opt/shellground/miniconda'
        for value in (expected,expected+'/',expected+'/./',expected+'//'):
            self.assertTrue(answer_matches(value,expected),value)
        for value in ('miniconda','~/miniconda','/opt/else/miniconda',expected+'/../other'):
            self.assertFalse(answer_matches(value,expected),value)

    def test_registered_environment_name_or_path_only(self):
        names={'sg-draft','sg-publish'}
        for value in ('sg-draft',' /home/learner/conda-envs/sg-draft/ '):
            self.assertTrue(answer_matches(value,'sg-draft',names))
        for value in ('/tmp/sg-draft','/home/learner/conda-envs/sg-publish','draft'):
            self.assertFalse(answer_matches(value,'sg-draft',names))
        self.assertFalse(answer_matches('/home/learner/conda-envs/sg-draft','sg-draft',()))

    def test_known_labels_and_boolean_types(self):
        self.assertTrue(answer_matches('conda','Conda'))
        self.assertTrue(answer_matches('리눅스 게스트','Linux guest'))
        self.assertTrue(answer_matches('Linux VM','Linux guest'))
        for wrong in ('Windows','macOS','Android','Miniconda'):
            self.assertFalse(answer_matches(wrong,'Linux guest'))
        self.assertFalse(answer_matches('Anaconda','Conda'))
        self.assertFalse(answer_matches(0,False));self.assertFalse(answer_matches('false',False))
        self.assertTrue(answer_matches(False,False))

    def test_repaired_learner_history_but_not_base_is_ignored(self):
        original={'history':'old','packages':{'tool':'1.0'},'requested':{'tool':'tool==1.0'},'contents':{'tool.py':'good'}}
        repaired=dict(original,history='real repair transactions')
        self.assertTrue(preserved_snapshot(repaired,original))
        self.assertFalse(preserved_snapshot(repaired,original,strict=True))
        self.assertFalse(preserved_snapshot(dict(repaired,packages={'tool':'1.1'}),original))
        self.assertFalse(preserved_snapshot(dict(repaired,contents={'tool.py':'bad'}),original))
        self.assertFalse(preserved_snapshot(dict(repaired,requested={'tool':'tool>=1.0'}),original))


if __name__=='__main__':unittest.main()
