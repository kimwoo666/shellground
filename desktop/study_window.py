"""One native application window with lazily created learning modes.

Switching rooms does not restart engines, discard editor text, or start a VM.
The Linux room can adopt a VM already warming in the mode picker.
Only the selected room receives its shortcuts. Closing the containing window
waits for every room's existing asynchronous cleanup, including hidden rooms.
"""
from pathlib import Path
from PySide6.QtCore import Qt, QStandardPaths, QTimer
from PySide6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QTabBar, QStackedWidget, QMessageBox
from layout_presets import DEFAULT_LAYOUT


class StudyWindow(QMainWindow):
    MODES = ('linux', 'python', 'conda')

    def __init__(self, ui_family, mono_family, progress_path=None, mode='real',
                 layout=DEFAULT_LAYOUT, page_factory=None, linux_engine=None):
        super().__init__()
        self.ui_family, self.mono_family = ui_family, mono_family
        self.base_progress_path = Path(progress_path or
            Path(QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppDataLocation)) / 'progress-v3.json')
        self.linux_mode = mode if mode in ('real', 'simulation') else 'real'
        self.layout_key = layout
        self.linux_engine = linux_engine
        self.pages = {}
        self.active_mode = None
        self._closing = self._shutdown_ready = False
        self._pending_close = set()
        self._page_factory = page_factory or self.make_page
        self.resize(1220, 920)
        root = QWidget()
        self.setCentralWidget(root)
        outer = QVBoxLayout(root)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        self.mode_tabs = QTabBar()
        self.mode_tabs.setAccessibleName('학습 모드 선택')
        self.mode_tabs.setExpanding(False)
        for title in ('Linux · Docker · ROS 2', 'Python · 데이터', 'Conda · 환경 관리'):
            self.mode_tabs.addTab(title)
        outer.addWidget(self.mode_tabs)
        self.stack = QStackedWidget()
        outer.addWidget(self.stack, 1)
        self.mode_tabs.currentChanged.connect(lambda index: self.switch_mode(self.MODES[index]))
        self.switch_mode('linux' if mode in ('real', 'simulation') else mode)

    def make_page(self, mode):
        if mode == 'linux':
            from native_app import Window
            return Window(self.ui_family, self.mono_family, self.base_progress_path,
                          mode=self.linux_mode, layout=self.layout_key, engine=self.linux_engine)
        if mode == 'python':
            from python_app import PythonWindow
            return PythonWindow(self.ui_family, self.mono_family,
                                self.base_progress_path.with_name('python-progress-v1.json'))
        if mode == 'conda':
            from conda_app import CondaWindow
            return CondaWindow(self.ui_family, self.mono_family,
                               self.base_progress_path.with_name('conda-progress-v1.json'))
        raise ValueError('알 수 없는 학습 모드: ' + mode)

    def restore_tab(self):
        if self.active_mode is not None:
            self.mode_tabs.blockSignals(True)
            self.mode_tabs.setCurrentIndex(self.MODES.index(self.active_mode))
            self.mode_tabs.blockSignals(False)

    @staticmethod
    def save_page(page):
        # Linux writes confirmed progress at each learning/grade action.
        # Merely switching views must not rewrite its loaded snapshot (which
        # may be stale, or empty after a malformed file was safely ignored).
        if hasattr(page, 'save'):
            page.save()

    def switch_mode(self, mode):
        if mode in ('real', 'simulation'):
            mode = 'linux'
        if mode not in self.MODES:
            raise ValueError('알 수 없는 학습 모드: ' + mode)
        if self._closing:
            self.restore_tab()
            return
        old = self.pages.get(self.active_mode)
        if old is not None and getattr(old, 'busy', False) and mode != self.active_mode:
            self.restore_tab()
            self.statusBar().showMessage('실행이 끝나거나 실행을 중단한 뒤 모드를 바꿀 수 있습니다.')
            return
        if mode not in self.pages:
            try:
                page = self._page_factory(mode)
            except Exception as error:
                self.restore_tab()
                QMessageBox.warning(self, '학습 모드를 열 수 없습니다', str(error))
                return
            page.setParent(self.stack, Qt.WindowType.Widget)
            for action in page.actions():
                action.setShortcutContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
            page.mode_requested.connect(self.switch_mode)
            page.shutdown_finished.connect(lambda key=mode: self.page_closed(key))
            page.shutdown_failed.connect(lambda message, key=mode: self.close_failed(key, message))
            page.windowTitleChanged.connect(lambda title, key=mode: self.setWindowTitle(title) if key == self.active_mode else None)
            self.pages[mode] = page
            self.stack.addWidget(page)
        if old is not None and mode != self.active_mode:
            self.save_page(old)
            if hasattr(old, 'simulation_timer'):
                old.simulation_timer.stop()
        page = self.pages[mode]
        self.active_mode = mode
        self.stack.setCurrentWidget(page)
        self.restore_tab()
        self.setWindowTitle(page.windowTitle())
        self.setPalette(page.palette())
        if hasattr(page, 'simulation_timer') and page.mode == 'simulation':
            page.simulation_timer.start(100)
        for name in ('editor', 'terminal', 'course', 'list'):
            target = getattr(page, name, None)
            if target is not None:
                target.setFocus(Qt.FocusReason.OtherFocusReason)
                break
        self.statusBar().clearMessage()

    def closeEvent(self, event):
        if self._shutdown_ready:
            event.accept()
            return
        event.ignore()
        if self._closing:
            return
        self._closing = True
        self.mode_tabs.setEnabled(False)
        self._pending_close = set(self.pages)
        self.statusBar().showMessage('진도를 저장하고 열었던 모든 실습 환경을 종료하는 중…')
        if not self._pending_close:
            self._shutdown_ready = True
            QTimer.singleShot(0, self.close)
        for key, page in list(self.pages.items()):
            if hasattr(page, 'simulation_timer'):
                page.simulation_timer.stop()
            self.save_page(page)
            page.close()

    def open_related_practice(self,target):
        if self._closing:return False
        from python_teaching.practice_links import resolve_target
        try:target=resolve_target(target)
        except (ValueError,KeyError,TypeError) as error:
            QMessageBox.warning(self,'관련 실습을 열 수 없습니다',str(error));return False
        mode='python' if target['course']=='notebook' else target['course'];original=self.active_mode
        if any(getattr(self.pages.get(key),'busy',False) for key in (original,mode)):
            self.statusBar().showMessage('실행이 끝나거나 중단한 뒤 관련 실습을 열 수 있습니다.');return False
        if mode not in self.pages:
            self.switch_mode(mode)
            if mode not in self.pages:return False
        page=self.pages[mode]
        try:
            opener=page.open_notebook_practice if target['course']=='notebook' else page.open_practice
            opened=opener(target['unit_key'],target['problem_index'])
        except Exception as error:
            self.switch_mode(original)
            QMessageBox.warning(self,'관련 실습을 열 수 없습니다',str(error));return False
        if not opened:
            self.switch_mode(original);return False
        self.switch_mode(mode)
        return self.active_mode==mode

    def page_closed(self, key):
        self._pending_close.discard(key)
        page = self.pages.pop(key, None)
        if page is not None:
            self.stack.removeWidget(page)
            page.deleteLater()
        if self._closing and not self._pending_close:
            self._shutdown_ready = True
            QTimer.singleShot(0, self.close)

    def close_failed(self, key, message):
        self._closing = False
        self._pending_close.discard(key)
        self.mode_tabs.setEnabled(True)
        self.active_mode = key
        self.stack.setCurrentWidget(self.pages[key])
        self.restore_tab()
        self.statusBar().showMessage('종료가 완료되지 않았습니다. 다시 종료해 주세요. ' + message)
