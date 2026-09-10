"""Cross-platform native learning UI; never executes user input on the host."""
import argparse
import json
from pathlib import Path
import sys
from PySide6.QtCore import Qt, QStandardPaths, Signal, QThread
from PySide6.QtGui import QFont, QFontDatabase, QAction
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                              QSplitter, QListWidget, QLabel, QPushButton, QPlainTextEdit,
                              QMessageBox, QProgressBar)
from engine import LabEngine, resource_path
from missions import UNITS, make_mission, random_mission
from terminal_widget import TerminalWidget, TerminalReader

APP_VERSION = '3.0.0'


class Worker(QThread):
    result = Signal(object)
    error = Signal(str)
    line = Signal(str)

    def __init__(self, function):
        super().__init__()
        self.function = function

    def run(self):
        try:
            self.result.emit(self.function(self.line.emit))
        except Exception as exc:
            self.error.emit(str(exc))


class Window(QMainWindow):
    def __init__(self, ui_family, mono_family, progress_path=None):
        super().__init__()
        self.engine = LabEngine()
        self.worker = None
        self.reader = None
        self.readers = []
        self.generation = 0
        self.index = 0
        self.phase = 'learn'
        self.practice_number = 0
        self.mission = None
        self.passed = False
        self.busy = False
        self.random_count = 0
        self.completed = []
        self.progress_path = progress_path or Path(QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppDataLocation)) / 'progress-v3.json'
        self.load_progress()
        self.setWindowTitle(f'Shellground {APP_VERSION} — 리눅스 실전 연습')
        self.resize(1220, 880)
        root = QWidget()
        self.setCentralWidget(root)
        outer = QVBoxLayout(root)
        top = QHBoxLayout()
        title = QLabel('SHELLGROUND  |  리눅스 실전 연습')
        title.setFont(QFont(ui_family, 16, QFont.Weight.Bold))
        top.addWidget(title)
        top.addStretch()
        self.progress = QProgressBar()
        self.progress.setRange(0, len(UNITS))
        self.progress.setFormat('%v / %m 단계 숙달')
        self.progress.setFixedWidth(210)
        top.addWidget(self.progress)
        outer.addLayout(top)
        self.environment = QLabel('Docker 실행 환경을 확인해 주세요. 개인 폴더는 실습에 연결하지 않습니다.')
        self.environment.setWordWrap(True)
        outer.addWidget(self.environment)
        setup_line = QHBoxLayout()
        self.check_env = QPushButton('실행 환경 확인')
        self.check_env.clicked.connect(lambda: self.run_job(lambda log: self.engine.status(), self.environment.setText))
        self.setup = QPushButton('최초 실습 환경 준비 (인터넷 필요)')
        self.setup.clicked.connect(self.prepare_environment)
        setup_line.addWidget(self.check_env)
        setup_line.addWidget(self.setup)
        setup_line.addStretch()
        outer.addLayout(setup_line)
        splitter = QSplitter()
        outer.addWidget(splitter, 1)
        sidebar = QWidget()
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(0, 0, 6, 0)
        sidebar_layout.addWidget(QLabel('난이도별 단계'))
        self.course = QListWidget()
        self.course.itemClicked.connect(lambda item: self.select_lesson(self.course.row(item)))
        sidebar_layout.addWidget(self.course)
        self.random_button = QPushButton('배운 범위 올랜덤')
        self.random_button.clicked.connect(self.start_random)
        sidebar_layout.addWidget(self.random_button)
        splitter.addWidget(sidebar)
        body = QWidget()
        body_layout = QVBoxLayout(body)
        body_layout.setContentsMargins(6, 0, 0, 0)
        self.steps = QLabel()
        self.steps.setWordWrap(True)
        body_layout.addWidget(self.steps)
        self.heading = QLabel()
        self.heading.setFont(QFont(ui_family, 14, QFont.Weight.Bold))
        self.heading.setWordWrap(True)
        body_layout.addWidget(self.heading)
        self.instructions = QPlainTextEdit()
        self.instructions.setReadOnly(True)
        self.instructions.setMinimumHeight(140)
        self.instructions.setMaximumHeight(235)
        body_layout.addWidget(self.instructions)
        self.terminal = TerminalWidget(mono_family)
        self.terminal.input_bytes.connect(self.engine.send)
        self.terminal.resized.connect(self.engine.resize)
        body_layout.addWidget(self.terminal, 1)
        self.feedback = QLabel('')
        self.feedback.setWordWrap(True)
        self.feedback.setTextFormat(Qt.TextFormat.PlainText)
        body_layout.addWidget(self.feedback)
        controls = QHBoxLayout()
        self.hint = QPushButton('힌트')
        self.hint.clicked.connect(self.show_hint)
        self.restart = QPushButton('문제 다시 시작')
        self.restart.clicked.connect(self.restart_mission)
        self.grade_button = QPushButton('결과 채점 (F5)')
        self.grade_button.clicked.connect(self.grade)
        self.next_button = QPushButton('예시 실습 시작')
        self.next_button.clicked.connect(self.advance)
        for button in [self.hint, self.restart, self.grade_button, self.next_button]: controls.addWidget(button)
        body_layout.addLayout(controls)
        shortcuts = QLabel('Tab 자동 완성 · ↑↓ 기록 · Ctrl+C 중단 · Ctrl+L 화면 정리 · Ctrl+Shift+C/V 복사/붙여넣기')
        shortcuts.setWordWrap(True)
        body_layout.addWidget(shortcuts)
        splitter.addWidget(body)
        splitter.setSizes([270, 930])
        self.statusBar().showMessage('실습은 격리된 Ubuntu에서 실행됩니다. 입력은 정답 문자열로 비교하지 않습니다.')
        action = QAction(self)
        action.setShortcut('F5')
        action.triggered.connect(self.grade)
        self.addAction(action)
        help_action = self.menuBar().addAction('실행 환경 / 제한 안내')
        help_action.triggered.connect(self.about_environment)
        self.refresh_course()
        self.select_lesson(min(len(self.completed), len(UNITS) - 1), initial=True)

    def load_progress(self):
        try:
            data = json.loads(self.progress_path.read_text(encoding='utf-8'))
            for unit in UNITS:
                if unit.key not in data.get('completed', []): break
                self.completed.append(unit.key)
        except (OSError, ValueError, AttributeError, TypeError):
            pass

    def save_progress(self):
        try:
            self.progress_path.parent.mkdir(parents=True, exist_ok=True)
            temporary = self.progress_path.with_suffix('.tmp')
            temporary.write_text(json.dumps({'schema': 3, 'completed': self.completed}, ensure_ascii=False), encoding='utf-8')
            temporary.replace(self.progress_path)
        except OSError as exc:
            QMessageBox.warning(self, '진도 저장 실패', str(exc))

    def refresh_course(self):
        self.course.clear()
        for index, unit in enumerate(UNITS):
            mark = '완료' if unit.key in self.completed else ('학습' if index <= len(self.completed) else '잠김')
            self.course.addItem(f'{index + 1:02d}. [{mark}] 난이도 {unit.level}\n{unit.title}\n{unit.commands}')
        self.course.setCurrentRow(self.index)
        self.progress.setValue(len(self.completed))
        self.update_controls()

    def update_controls(self):
        for widget in [self.course, self.check_env, self.setup]: widget.setEnabled(not self.busy)
        self.random_button.setEnabled(not self.busy and bool(self.completed))
        self.grade_button.setEnabled(not self.busy and self.mission is not None and not self.passed and self.terminal.connected)
        self.restart.setEnabled(not self.busy and self.mission is not None)
        self.hint.setEnabled(not self.busy and self.mission is not None)
        self.next_button.setEnabled(not self.busy and (self.phase == 'learn' or self.passed))

    def run_job(self, function, callback):
        if self.busy: return
        self.busy = True
        self.update_controls()
        self.worker = Worker(function)
        result_holder = {}
        self.worker.result.connect(lambda value: result_holder.update(value=value))
        self.worker.error.connect(lambda error: result_holder.update(error=error))
        self.worker.line.connect(lambda line: self.statusBar().showMessage(line))
        def finished():
            self.busy = False
            try:
                if 'error' in result_holder: self.feedback.setText('작업 실패: ' + result_holder['error'])
                elif 'value' in result_holder: callback(result_holder['value'])
            except Exception as exc:
                self.feedback.setText('작업 실패: ' + str(exc))
            self.update_controls()
        self.worker.finished.connect(finished)
        self.worker.start()

    def prepare_environment(self):
        answer = QMessageBox.question(self, '실습 환경 준비', 'Ubuntu와 Linux 도구를 내려받아 Docker 이미지를 만듭니다. 수백 MB의 저장 공간과 인터넷이 필요합니다. 준비할까요?')
        if answer == QMessageBox.StandardButton.Yes:
            self.environment.setText('Linux 실습 환경 준비 중… 아래 상태 표시줄에서 진행 상황을 확인할 수 있습니다.')
            self.run_job(lambda log: self.engine.build(log), self.environment.setText)

    def about_environment(self):
        QMessageBox.information(self, '실행 환경과 지원 범위', '화면은 Windows/Linux 네이티브 Qt 프로그램입니다.\n명령은 Docker 안의 실제 Ubuntu bash/GNU 프로그램입니다.\n\nLinux: Docker Engine 실행 및 현재 사용자 접근 권한 필요\nWindows: Docker Desktop + WSL 2, Linux containers 모드 필요\n\n개인 파일이나 Docker 소켓은 실습 컨테이너에 연결하지 않습니다. 외부 네트워크는 차단하며 다운로드는 내부 HTTP 서버로 연습합니다.\n\nsudo/커널/하드웨어/호스트 관리 실습은 지원 범위가 아닙니다. 모든 Linux 배포판의 옵션이 같다는 뜻도 아닙니다. 명령 문서는 --help를 사용하세요.\n\n이전 문자열 맞추기 버전의 진도는 새 실전 숙달 진도로 자동 인정하지 않습니다.')

    def select_lesson(self, index, initial=False):
        if self.busy: return
        if index > len(self.completed):
            self.feedback.setText('앞 단계를 완료하면 열립니다.')
            self.course.setCurrentRow(self.index)
            return
        if self.mission and not self.passed and not initial:
            if QMessageBox.question(self, '실습 전환', '현재 문제의 임시 파일은 버려집니다. 단계를 바꿀까요?') != QMessageBox.StandardButton.Yes:
                self.course.setCurrentRow(self.index); return
        self.index, self.phase, self.mission, self.passed = index, 'learn', None, False
        for reader in self.readers: reader.stop_requested.set()
        self.generation += 1
        self.terminal.connected = False
        self.terminal.reset()
        unit = UNITS[index]
        self.heading.setText(f'{index + 1}. {unit.title} — {unit.commands}')
        self.steps.setText('① 새 명령 배우기 → ② 예시 직접 실습 → ③ 활용 문제 2개 → ④ 배운 범위 올랜덤')
        self.instructions.setPlainText(unit.explanation + '\n\n예시를 익힌 뒤에는 시작 위치·대상 경로·파일 이름이 바뀐 활용 문제를 직접 해결합니다. 목표 결과가 같으면 다른 명령 조합도 인정합니다.')
        self.feedback.setText('명령 설명을 읽고 예시 실습을 시작하세요.')
        self.next_button.setText('예시 실습 시작')
        self.course.setCurrentRow(index)
        if self.engine.name: self.run_job(lambda log: self.engine.close(), lambda value: None)
        self.update_controls()

    def launch(self, mission):
        for reader in self.readers: reader.stop_requested.set()
        self.mission, self.passed = mission, False
        self.generation += 1
        generation = self.generation
        self.terminal.connected = False
        self.terminal.reset()
        self.steps.setText({'example': '② 예시 직접 실습', 'practice': f'③ 활용 문제 {self.practice_number}/2', 'random': '④ 배운 범위 올랜덤'}[self.phase])
        self.heading.setText(next(u.title for u in UNITS if u.key == mission.kind))
        text = f'시작 위치: {mission.start}\n\n목표: {mission.prompt}'
        if self.phase == 'example': text += '\n\n따라 입력할 예시 (한 줄씩 Enter):\n' + mission.solution
        self.instructions.setPlainText(text)
        self.feedback.setText('새로운 격리 실습 환경을 여는 중…')
        self.next_button.setText('다음 문제')
        def ready(value):
            process = self.engine.open_terminal(mission)
            self.reader = TerminalReader(process)
            self.readers.append(self.reader)
            reader = self.reader
            def consume(data):
                try:
                    if generation == self.generation: self.terminal.feed(data)
                finally:
                    reader.pending.release()
            self.reader.output.connect(consume)
            self.reader.ended.connect(lambda message: self.shell_ended(generation, message))
            self.reader.finished.connect(self.release_readers)
            self.reader.start()
            self.terminal.connected = True
            self.engine.resize(self.terminal.screen.lines, self.terminal.screen.columns)
            self.terminal.setFocus()
            self.feedback.setText('준비되었습니다. 명령을 자유롭게 실행한 뒤 결과 채점을 누르세요.')
            self.environment.setText('Ubuntu 24.04 / bash · 외부 네트워크 차단 · 개인 폴더 연결 없음')
        self.run_job(lambda log: self.engine.start(mission), ready)

    def release_readers(self):
        self.readers = [reader for reader in self.readers if reader.isRunning()]

    def shell_ended(self, generation, message):
        if generation == self.generation:
            self.terminal.connected = False
            self.feedback.setText(message)
            self.update_controls()

    def restart_mission(self):
        if self.mission and QMessageBox.question(self, '문제 다시 시작', '이 문제에서 만든 파일을 지우고 처음 상태로 다시 시작할까요?') == QMessageBox.StandardButton.Yes:
            self.launch(self.mission)

    def advance(self):
        if self.busy: return
        if self.phase == 'learn':
            self.phase = 'example'
            self.launch(make_mission(UNITS[self.index].key))
        elif not self.passed: return
        elif self.phase == 'example':
            self.phase, self.practice_number = 'practice', 1
            self.launch(make_mission(UNITS[self.index].key))
        elif self.phase == 'practice' and self.practice_number < 2:
            self.practice_number += 1
            self.launch(make_mission(UNITS[self.index].key))
        elif self.phase == 'practice':
            if self.index + 1 < len(UNITS): self.select_lesson(self.index + 1)
            else: self.start_random()
        elif self.phase == 'random': self.launch(random_mission(self.completed, self.mission.kind))

    def start_random(self):
        if not self.completed or self.busy: return
        if self.mission and not self.passed:
            if QMessageBox.question(self, '올랜덤 시작', '현재 문제의 임시 파일은 버려집니다. 올랜덤으로 전환할까요?') != QMessageBox.StandardButton.Yes: return
        self.phase, self.random_count = 'random', 0
        self.launch(random_mission(self.completed))

    def grade(self):
        if self.busy or not self.mission or self.passed or not self.terminal.connected: return
        def result(value):
            self.passed = value['passed']
            self.feedback.setText('\n'.join(('통과: ' if item['passed'] else '미완료: ') + item['label'] for item in value['checks']))
            if self.passed:
                if self.phase == 'practice' and self.practice_number == 2:
                    key = UNITS[self.index].key
                    if key not in self.completed:
                        self.completed.append(key)
                        self.save_progress()
                    self.refresh_course()
                    self.next_button.setText('다음 단계 배우기' if self.index + 1 < len(UNITS) else '올랜덤 시작')
                elif self.phase == 'random':
                    self.random_count += 1
                    self.next_button.setText(f'다음 랜덤 문제 (통과 {self.random_count})')
                self.statusBar().showMessage('목표 달성! 실제 파일·현재 위치·내용·권한으로 채점했습니다.')
        self.run_job(lambda log: self.engine.rpc('grade', self.mission), result)

    def show_hint(self):
        if self.mission:
            QMessageBox.information(self, '힌트', next(u.hint for u in UNITS if u.key == self.mission.kind))

    def closeEvent(self, event):
        if self.busy:
            self.statusBar().showMessage('진행 중인 환경 준비/채점을 마친 뒤 닫아 주세요.')
            event.ignore(); return
        event.ignore()
        for reader in self.readers: reader.stop_requested.set()
        self.generation += 1
        self.terminal.connected = False
        def closed(value):
            for reader in self.readers: reader.wait(3000)
            QApplication.instance().quit()
        self.feedback.setText('이 프로그램이 만든 실습 컨테이너를 정리하는 중…')
        self.run_job(lambda log: self.engine.close(), closed)


def create_application():
    app = QApplication(sys.argv)
    app.setApplicationName('Shellground')
    app.setOrganizationName('Shellground')
    app.setStyle('Fusion')
    font_path = resource_path('assets/NotoSansCJK-Regular.ttc')
    if font_path.exists(): QFontDatabase.addApplicationFont(str(font_path))
    families = QFontDatabase.families()
    ui_family = next((f for f in ['Noto Sans CJK KR', 'Malgun Gothic', 'Noto Sans KR'] if f in families), app.font().family())
    mono_family = next((f for f in ['Noto Sans Mono CJK KR', 'Consolas', 'DejaVu Sans Mono'] if f in families), 'monospace')
    app.setFont(QFont(ui_family, 11))
    return app, ui_family, mono_family


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--version', action='store_true')
    parser.add_argument('--self-test', action='store_true')
    args = parser.parse_args()
    if args.version: print(APP_VERSION); return 0
    if args.self_test:
        for unit in UNITS: assert make_mission(unit.key, 1234).solution
        assert resource_path('lab/Dockerfile').is_file()
        print(f'Shellground {APP_VERSION}: {len(UNITS)} goal-based units; resources OK (not a Docker integration test)')
        return 0
    app, ui, mono = create_application()
    window = Window(ui, mono)
    window.show()
    return app.exec()
