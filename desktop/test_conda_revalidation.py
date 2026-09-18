import unittest
from unittest.mock import patch
from conda_teaching.revalidate_export import validate_identity


class RevalidationTests(unittest.TestCase):
    def test_exact_base_sources_full_scope_and_cleanup_required(self):
        value=dict(state='complete',units=None,setup_verified=True,vm_stopped=True,overlay_removed=True,image_sha256='base',
                   course_fingerprint='course',learning_fingerprint='steps',setup_fingerprint='setup')
        with patch('conda_teaching.revalidate_export.source_fingerprint',return_value='course'),\
             patch('conda_teaching.revalidate_export.learning_fingerprint',return_value='steps'),\
             patch('conda_teaching.revalidate_export.setup_fingerprint',return_value='setup'):
            validate_identity(value,'base')
            for changes in ({'state':'failed'},{'state':'in_progress'},{'units':['pip_install']},
                            {'vm_stopped':False},{'overlay_removed':False},{'image_sha256':'other'},{'setup_verified':False},
                            {'course_fingerprint':'old'},{'learning_fingerprint':'old'},{'setup_fingerprint':'old'}):
                with self.subTest(changes=changes),self.assertRaises(RuntimeError):
                    validate_identity(dict(value,**changes),'base')


if __name__=='__main__':unittest.main()
