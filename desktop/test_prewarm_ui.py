"""The mode picker owns speculative startup; Linux adopts that same engine."""
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
import tempfile
from pathlib import Path
import unittest
from unittest.mock import Mock, patch

from native_app import create_application, main, QDialog
from sim_engine import SimEngine
from study_window import StudyWindow


class PrewarmUITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app, cls.ui, cls.mono = create_application()

    def test_cancelled_mode_picker_closes_its_background_vm(self):
        engine = Mock()
        dialog = Mock(); dialog.exec.return_value = QDialog.DialogCode.Rejected
        with patch('sys.argv', ['Shellground']), patch('native_app.mode_available', return_value=True), \
             patch('native_app.create_engine', return_value=engine), patch('native_app.ModeDialog', return_value=dialog):
            self.assertEqual(main(), 0)
        engine.prewarm.assert_called_once()
        engine.cancel_pending.assert_called_once()
        engine.close.assert_called_once()

    def test_linux_room_adopts_warm_engine_without_disabling_reading(self):
        from PySide6.QtTest import QTest
        import time
        with tempfile.TemporaryDirectory() as folder:
            engine = SimEngine()
            engine.prewarm = Mock()
            engine.release_practice = Mock()
            engine.cancel_pending = Mock()
            window = StudyWindow(self.ui, self.mono, Path(folder)/'progress.json',
                                 mode='real', linux_engine=engine)
            window.show(); self.app.processEvents()
            page = window.pages['linux']
            self.assertIs(page.engine, engine)
            engine.prewarm.assert_called_once()
            self.assertFalse(page.busy)
            self.assertTrue(page.course.isEnabled())
            self.assertIsNone(page.mission)
            self.assertFalse(list(Path(folder).glob('*progress*')))
            window.close()
            deadline = time.monotonic() + 5
            while window.isVisible() and time.monotonic() < deadline:
                self.app.processEvents(); QTest.qWait(10)
            self.assertFalse(window.isVisible())
            engine.cancel_pending.assert_called_once()
            window.deleteLater(); self.app.processEvents()


if __name__ == '__main__': unittest.main()
