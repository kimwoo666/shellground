"""Non-blocking NAS synchronization for the shared desktop study window."""
from pathlib import Path
import threading
import time
import uuid

from PySide6.QtCore import QObject, Signal, QTimer
from PySide6.QtWidgets import (QCheckBox, QComboBox, QDialog, QDialogButtonBox,
    QFileDialog, QFormLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QVBoxLayout)
from nas_sync import (FILES, MARKER, Synchronizer, FolderStore, RcloneStore,
                      atomic_json, read_json)


class SyncDialog(QDialog):
    def __init__(self, config, parent=None):
        super().__init__(parent)
        self.setWindowTitle('NAS 학습 진도 동기화'); self.resize(630, 340)
        layout = QVBoxLayout(self)
        label = QLabel('두 컴퓨터에서 같은 NAS 진도 폴더를 선택하세요.\n'
            '완료·소단계·퀴즈·기억노트만 전송합니다. 실습 파일과 비밀번호는 전송하지 않습니다.\n'
            '받은 진도는 앱을 시작할 때 적용합니다. 공부 중 화면을 임의로 바꾸지 않습니다.')
        label.setWordWrap(True); layout.addWidget(label)
        self.enabled = QCheckBox('자동 동기화 사용'); self.enabled.setChecked(config.get('enabled', True))
        layout.addWidget(self.enabled)
        form = QFormLayout(); layout.addLayout(form)
        self.transport = QComboBox()
        self.transport.addItem('NAS 공유 폴더 (Windows SMB / 연결된 폴더)', 'folder')
        self.transport.addItem('기존 rclone NAS 연결 (고급)', 'rclone')
        self.transport.setCurrentIndex(1 if config.get('transport') == 'rclone' else 0)
        form.addRow('연결 방식', self.transport)
        self.folder = QLineEdit(config.get('folder',''))
        browse = QPushButton('폴더 선택')
        browse.clicked.connect(self.choose_folder)
        row = QHBoxLayout(); row.addWidget(self.folder); row.addWidget(browse)
        form.addRow('진도 전용 폴더', row)
        self.command = QLineEdit(config.get('command',''))
        self.remote = QLineEdit(config.get('remote',''))
        form.addRow('rclone 실행파일', self.command); form.addRow('rclone 전용 경로', self.remote)
        self.initialize = QCheckBox('빈 전용 폴더에 새 프로필 만들기 (첫 기기만)')
        layout.addWidget(self.initialize)
        note = QLabel('NAS 로그인은 Windows/운영체제의 기존 연결을 사용합니다.\n'
            '각 OS의 폴더 경로는 달라도, NAS 안에서는 같은 폴더여야 합니다.')
        note.setWordWrap(True); layout.addWidget(note)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept); buttons.rejected.connect(self.reject); layout.addWidget(buttons)
    def choose_folder(self):
        selected = QFileDialog.getExistingDirectory(self, 'NAS의 진도 전용 폴더', self.folder.text())
        if selected: self.folder.setText(selected)
    def values(self):
        return dict(enabled=self.enabled.isChecked(), transport=self.transport.currentData(),
                    folder=self.folder.text().strip(), command=self.command.text().strip(),
                    remote=self.remote.text().strip())


class NasController(QObject):
    finished = Signal(object, object)
    def __init__(self, window, directory):
        super().__init__(window)
        self.window, self.directory = window, Path(directory)
        self.path = self.directory / 'nas-sync-config-v1.json'
        try: self.config = read_json(self.path) if self.path.exists() else {}
        except (OSError, ValueError): self.config = {}
        if not isinstance(self.config, dict): self.config = {}
        self.cancelled = threading.Event()
        self.busy = False; self.closed = False; self._startup = None; self._worker_thread = None
        self.last_attempt = 0; self.fingerprint = None; self.retry = False
        self.status = QLabel('NAS 미연결'); window.statusBar().addPermanentWidget(self.status)
        menu = window.menuBar().addMenu('진도 동기화')
        self.settings_action = menu.addAction('NAS 연결 설정…'); self.settings_action.triggered.connect(self.configure)
        self.sync_action = menu.addAction('지금 저장 (F9)'); self.sync_action.setShortcut('F9')
        self.sync_action.triggered.connect(lambda: self.request())
        self.finished.connect(self.done)
        self.timer = QTimer(self); self.timer.setInterval(2000); self.timer.timeout.connect(self.tick)
        self.timer.start()
    @property
    def enabled(self): return self.config.get('enabled') is True and bool(self.config.get('profile'))
    def startup(self, callback):
        if not self.enabled: callback(); return
        self._startup = callback
        self.request(apply=True)
    def stamps(self):
        found = []
        for name in FILES:
            try:
                stat = (self.directory / name).stat(); found.append((name,stat.st_mtime_ns,stat.st_size))
            except FileNotFoundError: pass
        return tuple(found)
    def tick(self):
        if self.closed or self.busy or not self.enabled: return
        changed = self.stamps() != self.fingerprint
        if (changed and not self.retry) or time.monotonic() - self.last_attempt >= 30:
            self.request()
    def request(self, apply=False, new_config=None, initialize=False):
        if self.closed or self.busy or (new_config is None and not self.enabled): return
        self.busy = True; self.last_attempt = time.monotonic()
        before = self.stamps()
        self.status.setText('NAS 진도 불러오는 중…' if apply else 'NAS 저장 중…')
        self.settings_action.setEnabled(False); self.sync_action.setEnabled(False)
        config = dict(new_config or self.config)
        def work():
            try:
                if new_config is not None:
                    store = (RcloneStore(config['command'],config['remote'],self.cancelled)
                             if config['transport']=='rclone' else FolderStore(config['folder']))
                    if initialize:
                        if not isinstance(store, FolderStore): raise ValueError('새 프로필은 공유 폴더에서 만들어 주세요.')
                        if not store.root.is_dir(): raise ValueError('먼저 NAS에 빈 진도 전용 폴더를 만들어 선택하세요.')
                        # Exclusive creation: never replace another user's marker.
                        profile = dict(schema=1, profile=uuid.uuid4().hex)
                        with (store.root/MARKER).open('x',encoding='utf-8') as stream:
                            from nas_sync import encode
                            stream.write(encode(profile))
                    marker = store.marker()
                    if marker.get('schema') != 1 or not isinstance(marker.get('profile'),str):
                        raise ValueError('Shellground 진도 폴더가 아닙니다.')
                    config['profile'] = marker['profile']
                result = Synchronizer(self.directory,config,cancelled=self.cancelled).synchronize(apply=apply)
                if new_config is not None: atomic_json(self.path,config)
                result.update(config=config, fingerprint=self.stamps() if apply else before)
                error = None
            except Exception as exc: result = None; error = str(exc)
            try: self.finished.emit(result,error)
            except RuntimeError: pass  # The application has already closed.
        self._worker_thread = threading.Thread(target=work, name='shellground-nas', daemon=True)
        self._worker_thread.start()
    def done(self, result, error):
        self.busy = False
        if self.closed: return
        self.settings_action.setEnabled(True); self.sync_action.setEnabled(True)
        self.retry = bool(error)
        if error:
            self.status.setText('NAS 연결 대기 · 로컬 저장 유지'); self.status.setToolTip(error)
        else:
            self.config = result['config']; self.fingerprint = result['fingerprint']
            self.status.setText('NAS 저장 완료' + (' · 받은 진도는 다음 시작에 적용' if result['remote_changes'] and not result['applied'] else ''))
            self.status.setToolTip('완료·소단계·퀴즈·기억노트 동기화. 현재 실습 파일은 전송하지 않습니다.')
        if self._startup is not None:
            callback, self._startup = self._startup, None
            callback()
    def configure(self):
        if self.busy: return
        dialog = SyncDialog(self.config,self.window)
        if dialog.exec() != QDialog.DialogCode.Accepted: return
        config = dialog.values()
        if not config['enabled']:
            config['profile'] = self.config.get('profile','')
            atomic_json(self.path,config); self.config=config; self.status.setText('NAS 동기화 꺼짐'); return
        self.request(new_config=config,initialize=dialog.initialize.isChecked())
    def prepare_close(self):
        # Queue the final locally saved step while the VM/processes shut down.
        if not self.busy and self.enabled: self.request()
    def finish_close(self, callback):
        # An offline NAS must never keep the application running indefinitely.
        deadline = time.monotonic() + 2.5
        attempted = [False]
        def poll():
            if not self.enabled or time.monotonic() >= deadline:
                self.stop(); callback(); return
            if not self.busy:
                if self.stamps() == self.fingerprint or attempted[0]:
                    self.stop(); callback(); return
                attempted[0] = True; self.request()
            QTimer.singleShot(50, poll)
        poll()
    def stop(self):
        self.closed = True; self.timer.stop(); self.cancelled.set()
        thread = self._worker_thread
        if thread and thread.is_alive() and thread is not threading.current_thread():
            # Let the cancelled transport terminate its owned rclone process
            # before Python exits; a daemon thread alone cannot guarantee this.
            thread.join(timeout=1.5)
