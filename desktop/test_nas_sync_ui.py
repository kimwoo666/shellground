import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch
from PySide6.QtCore import QTimer
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QMainWindow
from nas_sync import atomic_json, read_json, Synchronizer, MARKER
from nas_sync_ui import NasController, SyncDialog


class NasUiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.app=QApplication.instance() or QApplication([])
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.nas=self.root/'nas';self.nas.mkdir()
        self.local=self.root/'local';self.local.mkdir()
        self.peer=self.root/'peer';self.peer.mkdir()
        self.config=dict(enabled=True,transport='folder',folder=str(self.nas),profile='ui-test')
        atomic_json(self.nas/MARKER,dict(schema=1,profile='ui-test'))
        atomic_json(self.local/'nas-sync-config-v1.json',self.config)
        self.window=QMainWindow();self.controller=NasController(self.window,self.local)
        self.addCleanup(self.window.deleteLater);self.addCleanup(self.controller.stop)
    def wait(self,predicate,seconds=6):
        deadline=time.monotonic()+seconds
        while not predicate() and time.monotonic()<deadline:
            self.app.processEvents();QTest.qWait(10)
        self.assertTrue(predicate())
    def test_startup_applies_received_progress_before_opening_pages(self):
        atomic_json(self.peer/'progress-v3-real.json',dict(schema=3,completed=['navigate','pwdpaths']))
        Synchronizer(self.peer,self.config).synchronize()
        observed=[]
        self.controller.startup(lambda:observed.append(read_json(self.local/'progress-v3-real.json')))
        self.assertEqual(observed,[])
        self.wait(lambda:bool(observed))
        self.assertEqual(set(observed[0]['completed']),{'navigate','pwdpaths'})
        self.assertEqual(self.controller.status.text(),'NAS 저장 완료')
    def test_missing_nas_opens_local_progress_without_hanging(self):
        self.config['folder']=str(self.root/'missing')
        self.controller.config=self.config
        ready=[];self.controller.startup(lambda:ready.append(True))
        self.wait(lambda:bool(ready))
        self.assertIn('로컬 저장 유지',self.controller.status.text())
    def test_final_step_is_flushed_when_closing(self):
        atomic_json(self.local/'progress-v3-real.json',dict(schema=3,completed=['navigate']))
        finished=[];self.controller.finish_close(lambda:finished.append(True))
        self.wait(lambda:bool(finished))
        Synchronizer(self.peer,self.config).synchronize(apply=True)
        self.assertEqual(read_json(self.peer/'progress-v3-real.json')['completed'],['navigate'])
    def test_offline_close_has_a_fixed_time_limit(self):
        class Slow:
            def __init__(self,*args,**kwargs):self.cancelled=kwargs['cancelled']
            def synchronize(self,**kwargs):
                self.cancelled.wait(10);raise OSError('offline')
        with patch('nas_sync_ui.Synchronizer',Slow):
            start=time.monotonic();finished=[]
            self.controller.request()
            self.controller.finish_close(lambda:finished.append(True))
            self.wait(lambda:bool(finished),4)
            self.assertLess(time.monotonic()-start,3.8)
            self.controller._worker_thread.join(timeout=1)
    def test_disabled_sync_closes_without_shadowing_qobject_thread(self):
        self.controller.config={}
        finished=[];self.controller.finish_close(lambda:finished.append(True))
        self.assertEqual(finished,[True])
        self.assertTrue(callable(self.controller.thread))
    def test_windows_unc_path_is_preserved_without_moving_user_data(self):
        folder=r'\\nas\data\Shellground\progress-v1'
        dialog=SyncDialog(dict(enabled=True,transport='folder',folder=folder))
        self.assertEqual(dialog.values()['folder'],folder)
        dialog.deleteLater()


if __name__=='__main__':unittest.main()
