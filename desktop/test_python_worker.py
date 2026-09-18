import os
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch

from python_teaching.engine import PythonEngine, worker_environment
from python_teaching.values import grade_snapshot


class WorkerEnvironmentTests(unittest.TestCase):
    def test_frozen_linux_reuses_only_trusted_bundle_loader_path(self):
        supplied = {'PATH': '/usr/bin', 'LD_LIBRARY_PATH': '/user/untrusted',
                    'PYTHONPATH': '/user/python', 'CONDA_PREFIX': '/personal/conda',
                    'EXAMPLE_SECRET': 'do-not-inherit', '_PYI_ARCHIVE_FILE': '/owned/Shellground',
                    '_PYI_APPLICATION_HOME_DIR': '/tmp/owned-bundle'}
        with patch.dict(os.environ, supplied, clear=True), patch('sys.frozen', True, create=True), \
             patch('sys._MEIPASS', '/tmp/owned-bundle', create=True), patch('sys.platform', 'linux'):
            env = worker_environment(Path('/tmp/owned-bundle'))
        self.assertEqual(env['LD_LIBRARY_PATH'], '/tmp/owned-bundle')
        self.assertEqual(env['_PYI_APPLICATION_HOME_DIR'], '/tmp/owned-bundle')
        self.assertNotIn('EXAMPLE_SECRET', env)
        self.assertNotIn('CONDA_PREFIX', env)
        self.assertNotIn('/user/python', env['PYTHONPATH'])
        self.assertEqual(env['OPENBLAS_NUM_THREADS'], '1')

    def test_source_worker_does_not_inherit_frozen_or_loader_state(self):
        with patch.dict(os.environ, {'LD_LIBRARY_PATH': '/user/lib', '_PYI_ARCHIVE_FILE': '/other/app'}, clear=True), \
             patch('sys.frozen', False, create=True):
            env = worker_environment(Path('/owned/source'))
        self.assertNotIn('LD_LIBRARY_PATH', env)
        self.assertNotIn('_PYI_ARCHIVE_FILE', env)


@unittest.skipUnless((Path(__file__).parent / '.python-runtime/numpy').is_dir(), 'Python teaching pack required')
class PythonWorkerTests(unittest.TestCase):
    def engine(self, **kwargs):
        engine = PythonEngine(**kwargs)
        self.addCleanup(engine.close)
        return engine

    def test_real_numpy_state_exception_and_retry(self):
        e = self.engine()
        e.start('import numpy as np\na = np.arange(6).reshape(2, 3)')
        bad = e.execute('a + np.array([1, 2])')
        self.assertFalse(bad['ok'])
        self.assertIn('ValueError', bad['error'])
        good = e.execute('result = a + np.array([[10], [20]])\nresult')
        self.assertTrue(good['ok'], good)
        self.assertIn('array', good['output'])
        state = e.inspect(['result', 'a'])['values']
        checks = [dict(label='배열 값', target='result', path=['data'], expected=[[10,11,12],[23,24,25]]),
                  dict(label='배열 형태', target='result', path=['shape'], expected=[2,3]),
                  dict(label='원본 보존', target='a', path=['data'], expected=[[0,1,2],[3,4,5]])]
        self.assertTrue(grade_snapshot(state, checks)['passed'])
        e.execute('result = result.flatten()')
        self.assertFalse(grade_snapshot(e.inspect(['result','a'])['values'], checks)['passed'])

    def test_real_pandas_labels_missing_values_and_csv_encoding(self):
        e = self.engine()
        e.start('import pandas as pd', {'weather.csv': {'text': '지역,기온\n서울,20\n부산,\n', 'encoding': 'cp949'}})
        self.assertTrue(e.execute("df = pd.read_csv('weather.csv', encoding='cp949', index_col=0)\nmissing = df.isna().sum()")['ok'])
        state = e.inspect(['df', 'missing'])['values']
        self.assertEqual(state['df']['index'], ['서울','부산'])
        self.assertEqual(state['df']['data'][1][0], {'special': 'nan'})
        self.assertEqual(state['missing']['data'], [1])

    def test_figure_grading_checks_actual_data_not_appearance_only(self):
        e = self.engine()
        e.start('import matplotlib.pyplot as plt')
        result = e.execute("fig, ax = plt.subplots()\nax.plot([0,1,2], [0,1,4], label='squared')\nax.set_xlabel('time')\nax.legend()")
        self.assertTrue(result['ok'], result)
        state = e.inspect(['fig'])
        self.assertTrue(state['figures'])
        checks = [dict(label='그래프 값', target='fig', path=['axes',0,'lines',0,'y','data'], expected=[0,1,4]),
                  dict(label='범례', target='fig', path=['axes',0,'legend'], expected=['squared'])]
        self.assertTrue(grade_snapshot(state['values'], checks)['passed'])
        e.execute('ax.lines[0].set_ydata([0,1,9])')
        self.assertFalse(grade_snapshot(e.inspect(['fig'])['values'], checks)['passed'])

    def test_bounded_output_write_guard_and_no_process_launch(self):
        e = self.engine()
        e.start()
        self.assertLessEqual(len(e.execute("print('x' * 100000)")['output']), 65536)
        with tempfile.TemporaryDirectory() as d:
            outside = Path(d) / 'not-created.txt'
            self.assertFalse(e.execute(f"open({str(outside)!r}, 'w').write('bad')")['ok'])
            self.assertFalse(outside.exists())
        self.assertFalse(e.execute("import subprocess\nsubprocess.run(['echo', 'not allowed'])")['ok'])
        self.assertTrue(e.execute("open('answer.txt', 'w').write('kept in private exercise')")['ok'])

    def test_timeout_and_owned_directory_cleanup(self):
        e = self.engine(timeout=.25)
        e.start()
        directory = Path(e.workspace.name)
        with self.assertRaises(TimeoutError): e.execute('while True: pass')
        self.assertIsNotNone(e.process.poll())
        e.close()
        self.assertFalse(directory.exists())


if __name__ == '__main__': unittest.main()
