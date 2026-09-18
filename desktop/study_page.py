"""Common navigation and shutdown contract for embedded study rooms."""
from PySide6.QtCore import Signal
from PySide6.QtWidgets import QMainWindow


class StudyPage(QMainWindow):
    mode_requested = Signal(str)
    shutdown_finished = Signal()
    shutdown_failed = Signal(str)

    def __init__(self):
        super().__init__()
        self.study_closed = False

    def finish_shutdown(self, event):
        event.accept()
        if not self.study_closed:
            self.study_closed = True
            self.shutdown_finished.emit()
