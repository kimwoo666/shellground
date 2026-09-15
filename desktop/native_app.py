"""Cross-platform native learning UI; never executes user input on the host."""
import argparse
import json
from pathlib import Path
import sys
from PySide6.QtCore import Qt, QStandardPaths, Signal, QThread, QTimer
from PySide6.QtGui import QFont, QFontDatabase, QAction
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                              QSplitter, QListWidget, QLabel, QPushButton, QPlainTextEdit,
                              QMessageBox, QProgressBar, QDialog)
from engine import resource_path
from sim_engine import SimEngine as LabEngine
from missions import UNITS, make_mission, random_mission, lesson_text
from terminal_widget import TerminalWidget, TerminalReader
from memory_notes import NoteStore, MemoryDialog, suggest_note
from checkpoints import CHECKPOINTS, checkpoint_at, make_checkpoint

APP_VERSION = '4.0.0'


class FeedbackPanel(QPlainTextEdit):
    """Scrollable results must not displace the interactive terminal."""
    def __init__(self):
        super().__init__()
        self.setReadOnly(True)
        self.setMinimumHeight(65)
        self.setMaximumHeight(130)
        self.setAccessibleName('채점 결과와 안내')

    def setText(self, text):
        self.setPlainText(text)

    def text(self):
        return self.toPlainText()


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
        self.simulation_timer = QTimer(self)
        self.simulation_timer.timeout.connect(lambda: self.engine.tick() if not self.busy else None)
        self.simulation_timer.start(100)
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
        self._closing = False
        self._shutdown_ready = False
        self.random_count = 0
        self.completed = []
        self.completed_checkpoints = []
        self.checkpoint_end = None
        self.progress_path = progress_path or Path(QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppDataLocation)) / 'progress-v3.json'
        self.note_store = NoteStore(self.progress_path.with_name('memory-v1.json'))
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
        self.progress_note = QLabel('완료 진도 자동 저장 · 종료 후에도 유지 · 입력 내용과 실습 파일은 저장하지 않음')
        self.progress_note.setWordWrap(True)
        outer.addWidget(self.progress_note)
        self.environment = QLabel('오프라인 Linux·Docker 시뮬레이터 · VM·WSL·Docker 설치 불필요 · 개인 파일에 접근하지 않음')
        self.environment.setWordWrap(True)
        outer.addWidget(self.environment)
        setup_line = QHBoxLayout()
        self.check_env = QPushButton('시뮬레이터 상태')
        self.check_env.clicked.connect(lambda: self.run_job(lambda log: self.engine.status(), self.environment.setText))
        self.setup = QPushButton('시뮬레이터 사용 안내')
        self.setup.clicked.connect(self.about_environment)
        setup_line.addWidget(self.check_env)
        setup_line.addWidget(self.setup)
        self.try_button = QPushButton('설명 보며 연습 (F4)')
        self.try_button.clicked.connect(self.try_lesson)
        setup_line.addWidget(self.try_button)
        setup_line.addStretch()
        self.remember_button = QPushButton('기억해두기 (F7)')
        self.remember_button.clicked.connect(self.remember)
        self.notes_button = QPushButton('내 기억노트 (F8)')
        self.notes_button.clicked.connect(self.open_notes)
        setup_line.addWidget(self.remember_button)
        setup_line.addWidget(self.notes_button)
        outer.addLayout(setup_line)
        splitter = QSplitter()
        outer.addWidget(splitter, 1)
        sidebar = QWidget()
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(0, 0, 6, 0)
        sidebar_layout.addWidget(QLabel('난이도별 단계'))
        self.course = QListWidget()
        self.course.itemClicked.connect(self.select_course_item)
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
        self.feedback = FeedbackPanel()
        body_layout.addWidget(self.feedback)
        controls = QHBoxLayout()
        self.hint = QPushButton('힌트 (F1)')
        self.hint.clicked.connect(self.show_hint)
        self.restart = QPushButton('문제 다시 시작 (F2)')
        self.restart.clicked.connect(self.restart_mission)
        self.grade_button = QPushButton('결과 채점 (F5)')
        self.grade_button.clicked.connect(self.grade)
        self.options_button = QPushButton('옵션 설명 (F3)')
        self.options_button.clicked.connect(self.show_options)
        self.next_button = QPushButton('예시 실습 시작 (F6)')
        self.next_button.clicked.connect(self.advance)
        for button in [self.hint, self.restart, self.options_button, self.grade_button, self.next_button]: controls.addWidget(button)
        body_layout.addLayout(controls)
        shortcuts = QLabel('Tab 자동 완성 · ↑↓ 기록 · Ctrl+C 중단 · Ctrl+L 화면 정리 · Ctrl+Shift+C/V 복사/붙여넣기')
        shortcuts.setWordWrap(True)
        body_layout.addWidget(shortcuts)
        splitter.addWidget(body)
        splitter.setSizes([270, 930])
        self.statusBar().showMessage('명령은 가상 파일·프로세스·Docker 상태에 적용됩니다. 정답 문자열 비교가 아닙니다.')
        self.shortcut_actions = []
        for key, button in [('F1', self.hint), ('F2', self.restart), ('F3', self.options_button), ('F4', self.try_button),
                            ('F5', self.grade_button), ('F6', self.next_button), ('F7', self.remember_button), ('F8', self.notes_button)]:
            action = QAction(self)
            action.setShortcut(key)
            action.setShortcutContext(Qt.ShortcutContext.WindowShortcut)
            action.setAutoRepeat(False)
            action.triggered.connect(button.click)
            self.addAction(action)
            self.shortcut_actions.append((action, button))
        help_action = self.menuBar().addAction('실행 환경 / 제한 안내')
        help_action.triggered.connect(self.about_environment)
        self.refresh_course()
        self.select_initial()

    def load_progress(self):
        try:
            data = json.loads(self.progress_path.read_text(encoding='utf-8'))
            for unit in UNITS:
                if unit.key in data.get('completed', []): self.completed.append(unit.key)
            for checkpoint in CHECKPOINTS:
                if checkpoint.key in data.get('checkpoints', []) and all(u.key in self.completed for u in UNITS[:checkpoint.end]):
                    self.completed_checkpoints.append(checkpoint.key)
        except (OSError, ValueError, AttributeError, TypeError):
            pass

    def save_progress(self):
        try:
            self.progress_path.parent.mkdir(parents=True, exist_ok=True)
            temporary = self.progress_path.with_suffix('.tmp')
            data = {'schema': 3, 'completed': self.completed}
            if self.completed_checkpoints:
                data['checkpoints'] = self.completed_checkpoints
            temporary.write_text(json.dumps(data, ensure_ascii=False), encoding='utf-8')
            temporary.replace(self.progress_path)
            self.progress_note.setText(f'진도 자동 저장됨 · 완료 {len(self.completed)} / 미완료 {len(UNITS) - len(self.completed)} · 종합 복습 {len(self.completed_checkpoints)}/{len(CHECKPOINTS)} · 입력 내용은 저장하지 않음')
            return True
        except OSError as exc:
            self.progress_note.setText('진도 저장 실패 · 이번 완료 기록이 재실행 후 유지되지 않을 수 있습니다.')
            QMessageBox.warning(self, '진도 저장 실패', str(exc))
            return False

    def refresh_course(self):
        self.course.clear()
        testing = self.phase in ('practice', 'random', 'checkpoint')
        self.unit_rows, self.checkpoint_rows = {}, {}
        for index, unit in enumerate(UNITS):
            self.unit_rows[index] = self.course.count()
            mark = '완료' if unit.key in self.completed else ('미완료 · 학습 가능' if self.lesson_unlocked(index) else '미완료 · 잠김')
            detail = '평가 중 학습 내용 숨김' if testing else f'{unit.title}\n{unit.commands}'
            self.course.addItem(f'{index + 1:02d}. [{mark}] 난이도 {unit.level}\n{detail}')
            self.course.item(self.course.count() - 1).setData(Qt.ItemDataRole.UserRole, ('unit', index))
            if (index + 1) % 5 == 0:
                checkpoint = checkpoint_at(index + 1)
                self.checkpoint_rows[checkpoint.end] = self.course.count()
                mark = '완료 · 다시 복습 가능' if checkpoint.key in self.completed_checkpoints else ('미완료 · 응시 가능' if self.checkpoint_unlocked(checkpoint.end) else '미완료 · 잠김')
                detail = '평가 중 학습 내용 숨김' if testing else checkpoint.title
                self.course.addItem(f'◆ {checkpoint.end - 4:02d}–{checkpoint.end:02d} 종합 복습\n[{mark}]\n{detail}')
                self.course.item(self.course.count() - 1).setData(Qt.ItemDataRole.UserRole, ('checkpoint', checkpoint.end))
        self.restore_course_selection()
        self.progress.setValue(len(self.completed))
        self.update_controls()

    def update_controls(self):
        for widget in [self.course, self.check_env, self.setup]: widget.setEnabled(not self.busy)
        self.random_button.setEnabled(not self.busy and bool(self.completed))
        self.grade_button.setEnabled(not self.busy and self.phase != 'learn' and self.mission is not None and not self.passed and self.terminal.connected)
        self.restart.setEnabled(not self.busy and self.mission is not None)
        self.hint.setEnabled(not self.busy and self.mission is not None)
        self.next_button.setEnabled(not self.busy and (self.phase in ('learn', 'checkpoint_ready') or self.passed))
        self.options_button.setEnabled(not self.busy)
        self.try_button.setEnabled(not self.busy and self.phase == 'learn')
        self.remember_button.setEnabled(not self.busy)
        self.notes_button.setEnabled(not self.busy)
        for action, button in self.shortcut_actions: action.setEnabled(button.isEnabled())

    def lesson_unlocked(self, index):
        if not 0 <= index < len(UNITS): return False
        return UNITS[index].key in self.completed or (
            all(u.key in self.completed for u in UNITS[:index]) and
            all(c.key in self.completed_checkpoints for c in CHECKPOINTS if c.end <= index))

    def checkpoint_unlocked(self, end):
        return (all(u.key in self.completed for u in UNITS[:end]) and
                all(c.key in self.completed_checkpoints for c in CHECKPOINTS if c.end < end))

    def restore_course_selection(self):
        row = self.checkpoint_rows[self.checkpoint_end] if self.checkpoint_end else self.unit_rows[self.index]
        self.course.setCurrentRow(row)

    def select_course_item(self, item):
        kind, number = item.data(Qt.ItemDataRole.UserRole)
        if kind == 'checkpoint': self.select_checkpoint(number)
        else: self.select_lesson(number)

    def select_initial(self):
        for index, unit in enumerate(UNITS):
            if unit.key not in self.completed:
                self.select_lesson(index, initial=True)
                return
            if (index + 1) % 5 == 0 and checkpoint_at(index + 1).key not in self.completed_checkpoints:
                self.select_checkpoint(index + 1, initial=True)
                return
        self.select_lesson(len(UNITS) - 1, initial=True)

    def select_checkpoint(self, end, initial=False):
        if self.busy: return
        if not self.checkpoint_unlocked(end):
            self.feedback.setText('해당 구간의 단원과 앞 종합 복습을 완료하면 열립니다.')
            self.restore_course_selection()
            return
        if self.mission and not self.passed and not initial:
            if QMessageBox.question(self, '종합 복습 전환', '현재 문제의 임시 파일은 버려집니다. 종합 복습으로 전환할까요?') != QMessageBox.StandardButton.Yes:
                self.restore_course_selection()
                return
        self.index, self.checkpoint_end = end - 1, end
        self.phase, self.mission, self.passed = 'checkpoint_ready', None, False
        self.refresh_course()
        for reader in self.readers: reader.stop_requested.set()
        self.generation += 1
        self.terminal.connected = False
        self.terminal.reset()
        checkpoint = checkpoint_at(end)
        self.heading.setText(checkpoint.label)
        self.steps.setText('5개 단원 완료 → 종합 테스트 → 통과 기록 저장 → 다음 단원')
        self.instructions.setPlainText('이번 구간에서 배운 기능을 하나의 작업으로 조합합니다.\n\n' +
            '\n'.join(f'{end - 4 + i:02d}. {u.commands}' for i, u in enumerate(checkpoint.units)) +
            '\n\nF6: 종합 테스트 시작 · F3: 이 구간 설명 복습\n테스트에는 목표만 표시합니다. 필요할 때 F1로 힌트를 보세요.')
        self.feedback.setText('완료한 종합 복습도 목록에서 다시 선택해 새 문제로 연습할 수 있습니다.')
        self.next_button.setText('종합 테스트 시작 (F6)')
        self.restore_course_selection()
        if self.engine.name: self.run_job(lambda log: self.engine.close(), lambda value: None)
        self.update_controls()

    def run_job(self, function, callback, on_error=None):
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
                if 'error' in result_holder:
                    self.feedback.setText('작업 실패: ' + result_holder['error'])
                    if on_error is not None: on_error(result_holder['error'])
                elif 'value' in result_holder: callback(result_holder['value'])
            except Exception as exc:
                self.feedback.setText('작업 실패: ' + str(exc))
                if on_error is not None: on_error(str(exc))
            self.update_controls()
        self.worker.finished.connect(finished)
        self.worker.start()

    def prepare_environment(self):
        self.about_environment()

    def about_environment(self):
        QMessageBox.information(self, '시뮬레이터 범위', 'Windows/Linux 네이티브 Qt 프로그램입니다.\n명령은 메모리 안의 가상 Linux·Docker 상태에 적용됩니다.\nDocker·WSL·VM 설치나 인터넷 연결은 필요하지 않습니다.\n\n경로·파일 내용·권한·파이프·리다이렉션·종료 코드와 이미지·컨테이너 상태를 관리합니다. 지원하지 않는 명령/옵션은 명시적으로 실패합니다. 모든 bash/GNU/Docker 동작이 구현된 것은 아닙니다.\n\n다운로드는 준비된 가상 URL만, Docker pull은 가상 저장소만 사용합니다. GPU·실제 네트워크·성능 측정·호스트 마운트는 실행하지 않습니다. nano는 학습용 편집기 구현입니다.\n\n완료 진도와 기억노트만 사용자 설정 폴더에 저장합니다. 실습 파일·이미지는 호스트 파일이 아니며 재시작/종료 시 사라집니다.')

    def select_lesson(self, index, initial=False):
        if self.busy: return
        if not self.lesson_unlocked(index):
            self.feedback.setText('앞 단원과 종합 복습을 완료하면 열립니다.')
            self.restore_course_selection()
            return
        if self.mission and not self.passed and not initial:
            if QMessageBox.question(self, '실습 전환', '현재 문제의 임시 파일은 버려집니다. 단계를 바꿀까요?') != QMessageBox.StandardButton.Yes:
                self.restore_course_selection(); return
        self.index, self.phase, self.mission, self.passed = index, 'learn', None, False
        self.checkpoint_end = None
        self.refresh_course()
        for reader in self.readers: reader.stop_requested.set()
        self.generation += 1
        self.terminal.connected = False
        self.terminal.reset()
        unit = UNITS[index]
        self.heading.setText(f'{index + 1}. {unit.title} — {unit.commands}')
        self.steps.setText('① 새 명령 배우기 → ② 예시 직접 실습 → ③ 활용 문제 2개 → ④ 배운 범위 올랜덤')
        self.instructions.setPlainText(unit.explanation + '\n\nF4: 설명을 보며 자유 연습 · F6: 예시 과제 시작 · F3: 전체 옵션')
        self.feedback.setText('F4로 설명을 보면서 직접 해볼 수 있습니다. 자유 연습은 완료 진도에 반영하지 않습니다.')
        self.next_button.setText('예시 실습 시작 (F6)')
        self.restore_course_selection()
        if self.engine.name: self.run_job(lambda log: self.engine.close(), lambda value: None)
        self.update_controls()

    def try_lesson(self):
        if self.busy or self.phase != 'learn': return
        if self.mission and self.terminal.connected:
            self.terminal.setFocus()
            return
        self.launch(make_mission(UNITS[self.index].key))

    def launch(self, mission):
        for reader in self.readers: reader.stop_requested.set()
        self.mission, self.passed = mission, False
        self.refresh_course()
        self.generation += 1
        generation = self.generation
        self.terminal.connected = False
        self.terminal.reset()
        self.steps.setText({'learn': '① 새 명령 배우기 · 설명 보며 자유 연습', 'example': '② 예시 직접 실습', 'practice': f'③ 활용 {self.practice_number}/2 · ' + ('핵심 기능 확인' if self.practice_number == 1 else '조합·문제 해결'), 'random': '④ 배운 범위 올랜덤', 'checkpoint': '종합 테스트 · 앞 5개 단원 조합'}[self.phase])
        self.heading.setText(checkpoint_at(self.checkpoint_end).label if self.phase == 'checkpoint' else next(u.title for u in UNITS if u.key == mission.kind))
        text = f'시작 위치: {mission.start}\n\n목표: {mission.prompt}'
        if self.phase == 'learn':
            text = UNITS[self.index].explanation + '\n\n지금 직접 해볼 명령:\n' + mission.solution
        if self.phase == 'example': text += '\n\n따라 입력할 예시 (한 줄씩 Enter):\n' + mission.solution
        if self.phase in ('learn', 'example') and mission.interaction:
            text += '\n\n' + mission.interaction
        self.instructions.setPlainText(text)
        self.feedback.setText('새 가상 실습 상태를 준비하는 중…')
        self.next_button.setText('예시 실습 시작 (F6)' if self.phase == 'learn' else '다음 문제 (F6)')
        def ready(value):
            process = self.engine.open_terminal(mission)
            self.reader = TerminalReader(process)
            self.readers.append(self.reader)
            reader = self.reader
            def consume(data):
                try:
                    if generation == self.generation:
                        self.engine.observe_output(data)
                        self.terminal.feed(data)
                finally:
                    reader.pending.release()
            self.reader.output.connect(consume)
            self.reader.ended.connect(lambda message: self.shell_ended(generation, message))
            self.reader.finished.connect(self.release_readers)
            self.reader.start()
            self.terminal.connected = True
            self.engine.resize(self.terminal.screen.lines, self.terminal.screen.columns)
            self.terminal.setFocus()
            self.feedback.setText('설명을 보며 자유롭게 실행하세요. F6은 새 환경에서 예시를 시작하며 자유 연습 파일은 초기화됩니다.' if self.phase == 'learn' else '준비되었습니다. 명령을 자유롭게 실행한 뒤 결과 채점을 누르세요.')
            self.environment.setText('Linux·Docker 오프라인 시뮬레이터 · 가상 상태 기반 채점 · 실제 호스트 명령 실행 없음')
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
        if self.phase == 'checkpoint_ready':
            self.phase = 'checkpoint'
            self.launch(make_checkpoint(self.checkpoint_end))
        elif self.phase == 'learn':
            self.phase = 'example'
            self.launch(make_mission(UNITS[self.index].key))
        elif not self.passed: return
        elif self.phase == 'example':
            self.phase, self.practice_number = 'practice', 1
            self.launch(make_mission(UNITS[self.index].key, practice=1))
        elif self.phase == 'practice' and self.practice_number < 2:
            self.practice_number += 1
            self.launch(make_mission(UNITS[self.index].key, practice=2))
        elif self.phase == 'practice':
            if (self.index + 1) % 5 == 0: self.select_checkpoint(self.index + 1)
            elif self.index + 1 < len(UNITS): self.select_lesson(self.index + 1)
            else: self.start_random()
        elif self.phase == 'checkpoint':
            if self.checkpoint_end < len(UNITS): self.select_lesson(self.checkpoint_end)
            else: self.start_random()
        elif self.phase == 'random': self.launch(random_mission(self.completed, self.mission.kind))

    def start_random(self):
        if not self.completed or self.busy: return
        if self.mission and not self.passed:
            if QMessageBox.question(self, '올랜덤 시작', '현재 문제의 임시 파일은 버려집니다. 올랜덤으로 전환할까요?') != QMessageBox.StandardButton.Yes: return
        self.phase, self.random_count = 'random', 0
        self.checkpoint_end = None
        self.launch(random_mission(self.completed))

    def grade(self):
        if self.busy or self.phase == 'learn' or not self.mission or self.passed or not self.terminal.connected: return
        def result(value):
            self.passed = value['passed']
            summary = ('목표 달성! F6으로 다음 문제로 이동하세요.' if self.passed else
                       '계속 수정 후 F5로 재채점하세요. 파일과 현재 위치는 유지됩니다. 다시 시작할 필요가 없습니다.')
            self.feedback.setText(summary + '\n' + '\n'.join(('통과: ' if item['passed'] else '미완료: ') + item['label'] for item in value['checks']))
            # Grading is read-only: keep the same PTY, files and scrollback.
            # A mouse click on F5 otherwise leaves keyboard input on the button.
            if self.terminal.connected:
                self.terminal.setFocus(Qt.FocusReason.OtherFocusReason)
            if self.passed:
                if self.phase == 'practice' and self.practice_number == 2:
                    key = UNITS[self.index].key
                    if key not in self.completed:
                        self.completed.append(key)
                        self.save_progress()
                    self.refresh_course()
                    next_label = '종합 복습으로' if (self.index + 1) % 5 == 0 else ('다음 단계 배우기' if self.index + 1 < len(UNITS) else '올랜덤 시작')
                    self.next_button.setText(next_label + ' (F6)')
                elif self.phase == 'checkpoint':
                    key = checkpoint_at(self.checkpoint_end).key
                    if key not in self.completed_checkpoints:
                        self.completed_checkpoints.append(key)
                        self.save_progress()
                    self.refresh_course()
                    self.next_button.setText('다음 단계 배우기 (F6)')
                elif self.phase == 'random':
                    self.random_count += 1
                    self.next_button.setText(f'다음 랜덤 문제 (통과 {self.random_count}) (F6)')
                self.statusBar().showMessage('목표 달성! 가상 파일·현재 위치·내용·권한·Docker 상태로 채점했습니다.')
            else:
                self.statusBar().showMessage('미완료 항목을 이어서 해결하고 F5로 다시 채점하세요. F2는 파일 초기화입니다.')
        def grading_error(message):
            self.feedback.setText('채점 실패: ' + message + '\n실습은 초기화하지 않았습니다. 연결이 유지되어 있다면 계속 조작하고 F5로 다시 시도하세요.')
            if self.terminal.connected:
                self.terminal.setFocus(Qt.FocusReason.OtherFocusReason)
        self.run_job(lambda log: self.engine.rpc('grade', self.mission), result, on_error=grading_error)

    def show_hint(self):
        if self.mission:
            hint = ('이번 조합 문제의 한 가지 풀이:\n' + self.mission.solution + '\n' + self.mission.interaction
                    if self.mission.review else next(u.hint for u in UNITS if u.key == self.mission.kind))
            QMessageBox.information(self, '힌트', hint)

    def remember(self):
        unit = next((u for u in UNITS if self.mission and u.key == self.mission.kind), UNITS[self.index])
        selected = self.instructions.textCursor().selectedText()
        self.open_notes(suggest_note(unit, self.mission, selected))

    def open_notes(self, draft=None):
        dialog = MemoryDialog(self.note_store, self, draft if isinstance(draft, dict) else None)
        dialog.exec()
        self.terminal.setFocus()

    def show_options(self):
        unit = next((u for u in UNITS if self.mission and u.key == self.mission.kind), UNITS[self.index])
        checkpoint = checkpoint_at(self.checkpoint_end) if self.checkpoint_end else None
        dialog = QDialog(self)
        dialog.setWindowTitle('옵션 설명 — ' + (checkpoint.label if checkpoint else unit.title))
        dialog.resize(720, 580)
        layout = QVBoxLayout(dialog)
        text = QPlainTextEdit()
        text.setReadOnly(True)
        text.setPlainText('\n\n────────\n\n'.join(u.title + '\n' + lesson_text(u) for u in checkpoint.units) if checkpoint else lesson_text(unit))
        layout.addWidget(text)
        close = QPushButton('닫기 (Esc)')
        close.clicked.connect(dialog.accept)
        layout.addWidget(close)
        dialog.exec()
        self.terminal.setFocus()

    def closeEvent(self, event):
        # Closing the final window sends another close event. Accept that event
        # after cleanup instead of recursively starting cleanup again.
        if self._shutdown_ready:
            event.accept()
            return
        if self._closing:
            event.ignore()
            return
        if self.busy:
            self.statusBar().showMessage('진행 중인 환경 준비/채점을 마친 뒤 닫아 주세요.')
            event.ignore(); return
        event.ignore()
        self._closing = True
        for reader in self.readers: reader.stop_requested.set()
        self.generation += 1
        self.terminal.connected = False
        def closed(value):
            for reader in self.readers:
                if not reader.wait(3000):
                    raise RuntimeError('터미널 종료를 기다리는 중입니다. 잠시 후 종료를 다시 눌러 주세요.')
            self._shutdown_ready = True
            self.close()
        def failed(message):
            self._closing = False
            self.statusBar().showMessage('정리가 완료되지 않았습니다. 위 오류를 확인한 뒤 종료를 다시 시도하세요.')
        self.feedback.setText('가상 실습 상태를 정리하는 중…')
        self.run_job(lambda log: self.engine.close(), closed, on_error=failed)


def create_application():
    app = QApplication.instance() or QApplication(sys.argv)
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
        for checkpoint in CHECKPOINTS: assert make_checkpoint(checkpoint.end, 1234).solution
        engine = LabEngine()
        for key in ('mkdir', 'sim_commit'):
            mission = make_mission(key, 4242)
            engine.start(mission)
            for command in mission.solution.splitlines():
                result = engine.shell.execute(command)
                assert result.code == 0, result.err
            assert engine.rpc('grade', mission)['passed']
        engine.close()
        print(f'Shellground {APP_VERSION}: {len(UNITS)} simulator units + {len(CHECKPOINTS)} checkpoints; resources OK; no Docker/WSL/VM required')
        return 0
    app, ui, mono = create_application()
    window = Window(ui, mono)
    window.show()
    return app.exec()
