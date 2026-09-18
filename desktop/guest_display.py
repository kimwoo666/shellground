"""Low-rate native view of the actual guest display, no web view or mock scene."""
from PySide6.QtCore import Qt, QThread, QTimer, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QDialog, QLabel, QPushButton, QVBoxLayout


class FrameReader(QThread):
    frame = Signal(bytes)
    error = Signal(str)

    def __init__(self, engine, parent):
        super().__init__(parent)
        self.engine = engine

    def run(self):
        try:
            self.frame.emit(self.engine.screen())
        except Exception as exc:
            self.error.emit(str(exc))


class GuestDisplay(QDialog):
    def __init__(self, engine, parent=None):
        super().__init__(parent)
        self.engine = engine
        self.worker = None
        self.setWindowTitle('실제 Linux 화면 · TurtleSim / ROS 도구')
        self.resize(830, 690)
        layout = QVBoxLayout(self)
        self.picture = QLabel('실제 게스트 화면을 읽는 중…')
        self.picture.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.picture.setMinimumSize(800, 600)
        layout.addWidget(self.picture)
        self.status = QLabel('관찰용 화면 · 조작은 실습 터미널에서 합니다. 닫으면 화면 조회도 중단됩니다.')
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        refresh = QPushButton('지금 새로고침')
        refresh.clicked.connect(self.refresh)
        layout.addWidget(refresh)
        self.timer = QTimer(self)
        self.timer.setInterval(1000)  # At most 1 frame/s, only while visible.
        self.timer.timeout.connect(self.refresh)

    def showEvent(self, event):
        super().showEvent(event)
        self.timer.start()
        self.refresh()

    def hideEvent(self, event):
        self.timer.stop()
        super().hideEvent(event)

    def refresh(self):
        if not self.isVisible() or (self.worker and self.worker.isRunning()):
            return
        if self.worker:
            self.worker.deleteLater()
        self.worker = FrameReader(self.engine, self)
        self.worker.frame.connect(self.display)
        self.worker.error.connect(self.status.setText)
        self.worker.start()

    def display(self, data):
        pixmap = QPixmap()
        if pixmap.loadFromData(data, 'PNG'):
            self.picture.setPixmap(pixmap)
        else:
            self.status.setText('게스트에서 받은 화면을 읽을 수 없습니다.')

    def stop(self):
        self.timer.stop()
        self.hide()
        # Called after engine.close() has disconnected the request transport.
        return not self.worker or self.worker.wait(1500)
