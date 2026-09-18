import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

from conda_teaching.logged_command import read_tail, run_logged


@unittest.skipUnless(sys.platform.startswith('linux'), 'Real POSIX guest process lifecycle')
class LoggedCommandTests(unittest.TestCase):
    def assert_not_running(self, pid):
        status=Path('/proc')/str(pid)/'stat'
        # An orphan reaped asynchronously by PID1 can briefly remain a zombie.
        # It must not be executing or retain a live descendant after cleanup.
        if status.exists():self.assertIn(status.read_text().split(') ',1)[1].split()[0],('Z','X'))

    def test_real_success_has_complete_output_and_observation(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'output.log'
            result=run_logged([sys.executable,'-c','import sys;print("out");print("err",file=sys.stderr)'],path,timeout=5)
            self.assertEqual(result['status'],'passed');self.assertEqual(result['returncode'],0)
            self.assertIn('out',result['tail']);self.assertIn('err',result['tail'])
            record=json.loads(path.with_suffix('.log.json').read_text())
            self.assertEqual(record['status'],'passed');self.assertGreater(record['elapsed_seconds'],0)
            self.assert_not_running(record['pid'])

    def test_nonzero_exit_is_not_success(self):
        with tempfile.TemporaryDirectory() as folder:
            result=run_logged([sys.executable,'-c','print("actual failure",flush=True);raise SystemExit(7)'],Path(folder)/'output.log',timeout=5)
            self.assertEqual(result['status'],'failed');self.assertEqual(result['returncode'],7)
            self.assertIn('actual failure',result['tail'])

    def test_partial_output_is_readable_before_completion(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'output.log';completed=[]
            worker=threading.Thread(target=lambda:completed.append(run_logged(
                [sys.executable,'-c','import time;print("SG_STEP_START create",flush=True);time.sleep(1)'],path,timeout=5)))
            worker.start()
            try:
                end=time.monotonic()+3
                while time.monotonic()<end:
                    if path.exists() and 'SG_STEP_START create' in read_tail(path):break
                    time.sleep(.02)
                self.assertTrue(worker.is_alive());self.assertIn('SG_STEP_START create',read_tail(path))
            finally:worker.join(7)
            self.assertFalse(worker.is_alive());self.assertEqual(completed[0]['status'],'passed')

    def test_timeout_kills_real_ignoring_child_and_grandchild(self):
        child='import signal,time;signal.signal(signal.SIGTERM,signal.SIG_IGN);time.sleep(60)'
        parent=('import os,signal,subprocess,sys,time;signal.signal(signal.SIGTERM,signal.SIG_IGN);'
                'p=subprocess.Popen([sys.executable,"-c",'+repr(child)+']);'
                'print("CHILD",p.pid,flush=True);time.sleep(60)')
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'output.log'
            result=run_logged([sys.executable,'-c',parent],path,timeout=.5,grace=.05)
            self.assertEqual(result['status'],'timeout');self.assertEqual(result['returncode'],-signal.SIGKILL)
            child_pid=int(result['tail'].split('CHILD ')[1].split()[0])
            self.assert_not_running(result['pid']);self.assert_not_running(child_pid)
            self.assertEqual(json.loads(path.with_suffix('.log.json').read_text())['status'],'timeout')

    def test_interruption_reaps_actual_child_and_records_failure(self):
        original=subprocess.Popen.wait;calls=[]
        def interrupt_once(process,*args,**kwargs):
            if not calls:calls.append(process.pid);raise KeyboardInterrupt()
            return original(process,*args,**kwargs)
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'output.log'
            with patch.object(subprocess.Popen,'wait',interrupt_once),self.assertRaises(KeyboardInterrupt):
                run_logged([sys.executable,'-c','import time;time.sleep(60)'],path,timeout=5,grace=.05)
            self.assert_not_running(calls[0])
            self.assertEqual(json.loads(path.with_suffix('.log.json').read_text())['status'],'interrupted')

    def test_existing_output_and_symlink_are_not_overwritten(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);original=root/'existing';original.write_text('preserved')
            for target in (original,root/'link'):
                if target!=original:target.symlink_to(original)
                with self.assertRaises(FileExistsError):
                    run_logged([sys.executable,'-c','raise SystemExit(0)'],target,timeout=5)
                self.assertEqual(original.read_text(),'preserved')

    def test_start_error_is_recorded_without_false_success(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'output.log'
            with self.assertRaises(FileNotFoundError):run_logged(['/nonexistent-shellground-test-executable'],path,timeout=5)
            self.assertEqual(json.loads(path.with_suffix('.log.json').read_text())['status'],'start-failed')

    def test_tail_read_is_bounded(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'output.log';path.write_bytes(b'x'*50000+b'end')
            self.assertEqual(read_tail(path,10),'x'*7+'end')


if __name__=='__main__':unittest.main()
