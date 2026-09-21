"""Cross-platform native learning UI; never executes user input on the host."""
import argparse
import json
from pathlib import Path
import sys
import threading
from PySide6.QtCore import Qt, QStandardPaths, Signal, QThread, QTimer
from PySide6.QtGui import QFont, QFontDatabase, QAction
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                              QSplitter, QListWidget, QLabel, QPushButton, QPlainTextEdit,
                              QMessageBox, QProgressBar, QDialog, QTabWidget, QTabBar)
from engine import resource_path
from execution_modes import SIMULATION, MODES, create_engine, mode_progress_path, mode_available
from mode_dialog import ModeDialog
from missions import UNITS, make_mission, random_mission, lesson_text
from terminal_widget import TerminalWidget, TerminalReader
from memory_notes import NoteStore, MemoryDialog, suggest_note
from checkpoints import CHECKPOINTS, checkpoint_at, make_checkpoint
from mode_curriculum import curriculum
from guest_display import GuestDisplay
from real_lessons import adapt_real_mission
from course_topics import TOPICS, topic_of, topic_indices, unit_number, checkpoint_label, next_in_topic
from layout_presets import PRESETS, DEFAULT_LAYOUT
from feedback_panel import FeedbackPanel
from learning_steps import learning_steps
from learning_progress import read_records, cursor_for, remember, confirmed_count
from app_settings import SettingsDialog, load_settings, save_settings, theme_palette
from study_page import StudyPage

APP_VERSION = '4.7.6'


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


class Window(StudyPage):
    def __init__(self, ui_family, mono_family, progress_path=None, mode='simulation', layout=DEFAULT_LAYOUT, engine=None):
        super().__init__()
        self.mono_family = mono_family
        self.engine = create_engine(mode) if engine is None else engine
        self.mode = mode
        self.layout_key = layout
        self.topic = '리눅스'
        self.random_all_topics = False
        self.random_return = None
        self.units, self.checkpoints = curriculum(mode)
        self.simulation_timer = QTimer(self)
        self.simulation_timer.timeout.connect(lambda: self.engine.tick() if not self.busy else None)
        self.simulation_timer.start(100)
        self.worker = None
        self.guest_display = None
        self.reader = None
        self.readers = []
        self.generation = 0
        self.index = 0
        self.phase = 'learn'
        self.learning_step = 0
        self.learning_sequence = ()
        self.learning_resume_from = 0
        self.practice_number = 0
        self.mission = None
        self.passed = False
        self.busy = False
        self._closing = False
        self._shutdown_ready = False
        self._shutdown_requested = False
        self.random_count = 0
        self.completed = []
        self.completed_checkpoints = []
        self.checkpoint_end = None
        base_progress_path = progress_path or Path(QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppDataLocation)) / 'progress-v3.json'
        self.base_progress_path = Path(base_progress_path)
        self.settings_path = self.base_progress_path.with_name('settings-v1.json')
        self.settings = load_settings(self.settings_path)
        self.progress_path = mode_progress_path(base_progress_path, mode)
        self.note_store = NoteStore(Path(base_progress_path).with_name('memory-v1.json'))
        self.load_progress()
        self.setWindowTitle(f'Shellground {APP_VERSION} — {MODES[mode].title}')
        self.resize(1220, 880)
        root = QWidget()
        self.setCentralWidget(root)
        outer = QVBoxLayout(root)
        compact = layout != 'current'
        preset = PRESETS[layout]
        if compact:
            outer.setContentsMargins(6, 4, 6, 4)
            outer.setSpacing(4)
        top = QHBoxLayout()
        title = QLabel('SHELLGROUND')
        title.setFont(QFont(ui_family, 13 if compact else 16, QFont.Weight.Bold))
        top.addWidget(title)
        top.addStretch()
        self.progress = QProgressBar()
        self.progress.setRange(0, len(self.units))
        self.progress.setFormat('%v / %m 단계 숙달')
        self.progress.setFixedWidth(210)
        top.addWidget(self.progress)
        outer.addLayout(top)
        mode_line = QHBoxLayout()
        self.mode_label = QLabel()
        self.mode_label.setWordWrap(True)
        mode_line.addWidget(self.mode_label, 1)
        self.mode_button = QPushButton('모드 선택')
        self.mode_button.clicked.connect(self.choose_mode)
        mode_line.addWidget(self.mode_button)
        self.settings_button = QPushButton('설정')
        self.settings_button.setToolTip('테마·터미널 색상·글자 크기 (Ctrl+,)')
        self.settings_button.clicked.connect(self.open_settings)
        mode_line.addWidget(self.settings_button)
        outer.addLayout(mode_line)
        self.progress_note = QLabel('완료·소단계 진도 자동 저장 · 입력 내용과 실습 파일은 저장하지 않음')
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
        self.view_guest = QPushButton('실제 Linux 화면')
        self.view_guest.clicked.connect(self.show_guest_display)
        setup_line.addWidget(self.view_guest)
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
        if compact:
            self.progress_note.hide()
            self.environment.hide()
        splitter = QSplitter()
        self.main_splitter = splitter
        splitter.setChildrenCollapsible(False)
        outer.addWidget(splitter, 1)
        sidebar = QWidget()
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(0, 0, 6, 0)
        self.topic_tabs = QTabBar()
        self.topic_tabs.setExpanding(True)
        self.topic_tabs.setAccessibleName('학습 분야 선택')
        for topic in TOPICS: self.topic_tabs.addTab(topic)
        self.topic_tabs.currentChanged.connect(self.change_topic)
        sidebar_layout.addWidget(self.topic_tabs)
        sidebar_layout.addWidget(QLabel('난이도별 단계'))
        self.course = QListWidget()
        self.course.itemClicked.connect(self.select_course_item)
        sidebar_layout.addWidget(self.course)
        self.random_button = QPushButton('이 분야 배운 범위 랜덤')
        self.random_button.clicked.connect(lambda: self.start_random())
        sidebar_layout.addWidget(self.random_button)
        self.exit_random_button = QPushButton('올랜덤 종료 · 이전 학습으로')
        self.exit_random_button.setToolTip('완료 진도를 유지하고 이전 단원의 설명 또는 종합 복습 대기로 돌아갑니다.')
        self.exit_random_button.clicked.connect(self.exit_random)
        self.exit_random_button.hide()
        sidebar_layout.addWidget(self.exit_random_button)
        splitter.addWidget(sidebar)
        body = QWidget()
        body_layout = QVBoxLayout(body)
        body_layout.setContentsMargins(6, 0, 0, 0)
        if compact: body_layout.setSpacing(4)
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
        self.feedback = FeedbackPanel()
        self.task_tabs = QTabWidget()
        self.task_tabs.setAccessibleName('문제와 채점 결과')
        self.task_tabs.addTab(self.instructions, '문제')
        self.task_tabs.addTab(self.feedback, '채점 결과')
        self.previous_learning = QPushButton('← 이전 소단계')
        self.previous_learning.clicked.connect(self.previous_learning_step)
        self.resume_preparation = QPushButton('재개 준비 명령')
        self.resume_preparation.clicked.connect(self.show_resume_preparation)
        learning_navigation = QWidget()
        navigation_layout = QHBoxLayout(learning_navigation)
        navigation_layout.setContentsMargins(0, 0, 0, 0)
        navigation_layout.addWidget(self.resume_preparation)
        navigation_layout.addWidget(self.previous_learning)
        self.task_tabs.setCornerWidget(learning_navigation)
        self.resume_preparation.hide()
        self.previous_learning.hide()
        self.task_tabs.currentChanged.connect(self.focus_task_terminal)
        self.feedback.textChanged.connect(lambda: self.statusBar().showMessage(self.feedback.text().replace('\n', ' ')) if self.feedback._checks is None else None)
        self.practice_splitter = None
        if compact:
            self.instructions.setMinimumHeight(150)
            self.instructions.setMaximumHeight(16777215)
            self.practice_splitter = QSplitter(Qt.Orientation.Vertical)
            self.practice_splitter.setChildrenCollapsible(False)
            self.practice_splitter.setHandleWidth(7)
            self.practice_splitter.setAccessibleName('문제·터미널 크기 조절')
            self.practice_splitter.addWidget(self.task_tabs)
            body_layout.addWidget(self.practice_splitter, 1)
        else:
            self.task_tabs.setMaximumHeight(265)
            body_layout.addWidget(self.task_tabs)
        self.terminal = TerminalWidget(mono_family)
        self.terminals = [self.terminal]
        self.connect_terminal(self.terminal)
        terminal_line = QHBoxLayout()
        self.more_terminal = QPushButton('새 터미널 (Ctrl+Shift+T)')
        self.more_terminal.clicked.connect(self.new_terminal)
        terminal_line.addWidget(self.more_terminal)
        terminal_line.addStretch()
        if not compact: body_layout.addLayout(terminal_line)
        self.terminal_tabs = QTabWidget()
        self.terminal_tabs.addTab(self.terminal, '터미널 1')
        self.terminal_tabs.setTabsClosable(True)
        self.terminal_tabs.currentChanged.connect(self.activate_terminal)
        self.terminal_tabs.tabCloseRequested.connect(self.close_terminal_tab)
        if compact:
            terminal_line.removeWidget(self.more_terminal)
            self.terminal_tabs.setCornerWidget(self.more_terminal)
            self.practice_splitter.addWidget(self.terminal_tabs)
            self.practice_splitter.setSizes([preset.question, preset.terminal])
        else:
            body_layout.addWidget(self.terminal_tabs, 1)
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
        if compact: splitter.setSizes([preset.sidebar, 1200 - preset.sidebar])
        self.statusBar().showMessage('명령은 가상 파일·프로세스·Docker 상태에 적용됩니다. 정답 문자열 비교가 아닙니다.')
        self.shortcut_actions = []
        for key, button in [('F1', self.hint), ('F2', self.restart), ('F3', self.options_button), ('F4', self.try_button),
                            ('F5', self.grade_button), ('F6', self.next_button), ('F7', self.remember_button), ('F8', self.notes_button),
                            ('Ctrl+Shift+T', self.more_terminal), ('Ctrl+,', self.settings_button)]:
            action = QAction(self)
            action.setShortcut(key)
            action.setShortcutContext(Qt.ShortcutContext.WindowShortcut)
            action.setAutoRepeat(False)
            action.triggered.connect(button.click)
            self.addAction(action)
            self.shortcut_actions.append((action, button))
        help_action = self.menuBar().addAction('실행 환경 / 제한 안내')
        python_action = self.menuBar().addAction('Python·데이터 학습')
        python_action.triggered.connect(self.open_python)
        help_action.triggered.connect(self.about_environment)
        self.concept_action = self.menuBar().addAction('Linux·Docker 개념 배우기·퀴즈')
        self.concept_action.triggered.connect(self.open_system_concepts)
        self.all_random_action = self.menuBar().addAction('전체 분야 올랜덤')
        self.all_random_action.triggered.connect(lambda: self.start_random(all_topics=True))
        details = self.menuBar().addAction('상태·저장 안내 표시')
        details.setCheckable(True)
        details.setChecked(not compact)
        details.toggled.connect(self.progress_note.setVisible)
        details.toggled.connect(self.environment.setVisible)
        self.apply_settings(self.settings)
        self.refresh_mode_labels()
        self.refresh_course()
        self.select_initial()
        if self.mode == 'real' and hasattr(self.engine, 'prewarm'):
            QTimer.singleShot(0, self.engine.prewarm)

    def apply_settings(self, settings):
        self.settings = settings
        self.setPalette(theme_palette(settings.theme))
        font = QFont(self.font())
        font.setPointSize(settings.text_font_size)
        self.instructions.setFont(font)
        self.feedback.set_dark_theme(settings.theme == 'dark')
        for terminal in self.terminals: terminal.apply_settings(settings)

    def open_settings(self):
        dialog = SettingsDialog(self.settings, self.mono_family, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            settings = dialog.values()
            try:
                save_settings(self.settings_path, settings)
            except OSError as exc:
                QMessageBox.warning(self, '설정 저장 실패', '기존 설정은 변경하지 않았습니다.\n' + str(exc))
            else:
                self.apply_settings(settings)
                self.statusBar().showMessage('설정을 저장했습니다. 다음 실행에도 유지됩니다.')
        if self.terminal.connected: self.terminal.setFocus()

    def focus_task_terminal(self, index):
        if hasattr(self, 'terminal') and self.terminal.connected:
            self.terminal.setFocus(Qt.FocusReason.OtherFocusReason)

    def load_progress(self):
        self.archived_completed = []
        self.archived_checkpoints = []
        self.learning_progress = {}
        self.last_learning = ''
        try:
            data = json.loads(self.progress_path.read_text(encoding='utf-8'))
            self.learning_progress = read_records(data.get('learning'))
            last = data.get('last_learning', '')
            if isinstance(last, str): self.last_learning = last
            known_units = {u.key for u in self.units}
            known_checks = {c.key for c in self.checkpoints}
            self.archived_completed = [key for key in data.get('completed', []) if isinstance(key, str) and key not in known_units]
            self.archived_checkpoints = [key for key in data.get('checkpoints', []) if isinstance(key, str) and key not in known_checks]
            for unit in self.units:
                if unit.key in data.get('completed', []): self.completed.append(unit.key)
            for checkpoint in self.checkpoints:
                if checkpoint.key in data.get('checkpoints', []):
                    self.completed_checkpoints.append(checkpoint.key)
        except (OSError, ValueError, AttributeError, TypeError):
            pass

    def save_progress(self):
        try:
            self.progress_path.parent.mkdir(parents=True, exist_ok=True)
            temporary = self.progress_path.with_suffix('.tmp')
            data = {'schema': 3, 'completed': list(dict.fromkeys(self.completed + self.archived_completed))}
            if self.learning_progress: data['learning'] = self.learning_progress
            if self.last_learning: data['last_learning'] = self.last_learning
            if self.completed_checkpoints or self.archived_checkpoints:
                data['checkpoints'] = list(dict.fromkeys(self.completed_checkpoints + self.archived_checkpoints))
            temporary.write_text(json.dumps(data, ensure_ascii=False), encoding='utf-8')
            temporary.replace(self.progress_path)
            self.progress_note.setText(f'완료·소단계 진도 자동 저장됨 · 완료 {len(self.completed)} / 미완료 {len(self.units) - len(self.completed)} · 종합 복습 {len(self.completed_checkpoints)}/{len(self.checkpoints)} · 입력·실습 파일은 저장하지 않음')
            return True
        except OSError as exc:
            self.progress_note.setText('진도 저장 실패 · 이번 완료 기록이 재실행 후 유지되지 않을 수 있습니다.')
            QMessageBox.warning(self, '진도 저장 실패', str(exc))
            return False

    def refresh_course(self):
        self.course.clear()
        testing = self.phase in ('practice', 'random', 'checkpoint')
        self.unit_rows, self.checkpoint_rows = {}, {}
        for index, unit in enumerate(self.units):
            self.unit_rows[index] = self.course.count()
            mark = '완료' if unit.key in self.completed else '미완료 · 학습 가능'
            if unit.key not in self.completed and unit.key in self.learning_progress:
                count = len(self.learning_progress[unit.key]['confirmed'])
                mark = f'미완료 · 소단계 {count}개 확인'
            detail = '평가 중 학습 내용 숨김' if testing else f'{unit.title}\n{unit.commands}'
            self.course.addItem(f'{unit_number(self.units, index):02d}. [{mark}] 난이도 {unit.level}\n{detail}')
            self.course.item(self.course.count() - 1).setData(Qt.ItemDataRole.UserRole, ('unit', index))
            self.course.item(self.course.count() - 1).setHidden(topic_of(unit) != self.topic)
            if (index + 1) % 5 == 0:
                checkpoint = checkpoint_at(index + 1, self.mode)
                self.checkpoint_rows[checkpoint.end] = self.course.count()
                mark = '완료 · 다시 복습 가능' if checkpoint.key in self.completed_checkpoints else '미완료 · 응시 가능'
                detail = '평가 중 학습 내용 숨김' if testing else checkpoint.title
                number = unit_number(self.units, index)
                self.course.addItem(f'◆ {number - 4:02d}–{number:02d} 종합 복습\n[{mark}]\n{detail}')
                self.course.item(self.course.count() - 1).setData(Qt.ItemDataRole.UserRole, ('checkpoint', checkpoint.end))
                self.course.item(self.course.count() - 1).setHidden(topic_of(unit) != self.topic)
        self.restore_course_selection()
        indices = topic_indices(self.units, self.topic)
        self.progress.setMaximum(len(indices))
        self.progress.setFormat(self.topic + ' %v / %m 단계 숙달')
        self.progress.setValue(sum(self.units[i].key in self.completed for i in indices))
        self.topic_tabs.blockSignals(True)
        self.topic_tabs.setTabEnabled(2, self.mode == 'real')
        self.topic_tabs.setTabToolTip(2, 'ROS 2는 실제 모드에서 학습합니다.' if self.mode != 'real' else 'ROS 2 01부터 시작')
        self.topic_tabs.setCurrentIndex(TOPICS.index(self.topic))
        self.topic_tabs.blockSignals(False)
        self.update_controls()

    def change_topic(self, tab_index):
        topic = TOPICS[tab_index]
        indices = topic_indices(self.units, topic)
        if self.busy or not indices or topic == self.topic: return
        if self.mission and not self.passed:
            if QMessageBox.question(self, '학습 분야 전환', '완료 진도는 유지됩니다. 현재 문제의 임시 실습 상태는 버리고 분야를 바꿀까요?') != QMessageBox.StandardButton.Yes:
                self.topic_tabs.blockSignals(True)
                self.topic_tabs.setCurrentIndex(TOPICS.index(self.topic))
                self.topic_tabs.blockSignals(False)
                return
        self.topic = topic
        # Reviews are optional entry points, not prerequisites for later lessons.
        for index in indices:
            if self.units[index].key not in self.completed:
                self.select_lesson(index, initial=True)
                return
        self.select_lesson(indices[-1], initial=True)

    def update_controls(self):
        self.concept_action.setEnabled(not self.busy and self.mode == 'real')
        for widget in [self.course, self.topic_tabs, self.check_env, self.setup, self.mode_button, self.settings_button]: widget.setEnabled(not self.busy)
        self.random_button.setEnabled(not self.busy and any(u.key in self.completed and topic_of(u) == self.topic for u in self.units))
        self.all_random_action.setEnabled(not self.busy and bool(self.completed))
        self.exit_random_button.setVisible(self.phase == 'random')
        self.exit_random_button.setEnabled(not self.busy and self.phase == 'random')
        self.grade_button.setEnabled(not self.busy and self.phase != 'learn' and self.mission is not None and not self.passed and self.terminal.connected)
        self.restart.setEnabled(not self.busy and self.mission is not None)
        self.hint.setEnabled(not self.busy and self.mission is not None)
        self.next_button.setEnabled(not self.busy and (self.phase in ('learn', 'checkpoint_ready') or self.passed))
        self.options_button.setEnabled(not self.busy)
        self.try_button.setEnabled(not self.busy and self.phase == 'learn')
        self.remember_button.setEnabled(not self.busy)
        self.notes_button.setEnabled(not self.busy)
        self.more_terminal.setEnabled(not self.busy and self.mode == 'real' and self.mission is not None and bool(self.engine.name) and len(self.terminals) < 8)
        self.view_guest.setEnabled(not self.busy and self.mode == 'real' and bool(self.engine.name))
        guided = self.phase == 'learn' and bool(self.learning_sequence)
        self.previous_learning.setVisible(guided)
        self.previous_learning.setEnabled(guided and not self.busy and self.learning_step > 0)
        self.resume_preparation.setVisible(guided and self.learning_resume_from > 0)
        self.resume_preparation.setEnabled(not self.busy)
        for action, button in self.shortcut_actions: action.setEnabled(button.isEnabled())

    def lesson_unlocked(self, index):
        return 0 <= index < len(self.units)

    def checkpoint_unlocked(self, end):
        return any(c.end == end for c in self.checkpoints)

    def restore_course_selection(self):
        row = self.checkpoint_rows[self.checkpoint_end] if self.checkpoint_end else self.unit_rows[self.index]
        self.course.setCurrentRow(row)

    def select_course_item(self, item):
        kind, number = item.data(Qt.ItemDataRole.UserRole)
        if kind == 'checkpoint': self.select_checkpoint(number)
        else: self.select_lesson(number)

    def select_initial(self):
        for index, unit in enumerate(self.units):
            if unit.key == self.last_learning and unit.key in self.learning_progress:
                self.select_lesson(index, initial=True)
                return
        for index, unit in enumerate(self.units):
            if unit.key not in self.completed:
                self.select_lesson(index, initial=True)
                return
        for checkpoint in self.checkpoints:
            if checkpoint.key not in self.completed_checkpoints:
                self.select_checkpoint(checkpoint.end, initial=True)
                return
        self.select_lesson(len(self.units) - 1, initial=True)

    def select_checkpoint(self, end, initial=False):
        if self.busy: return
        if not self.checkpoint_unlocked(end):
            self.feedback.setText('현재 과정에 없는 종합 복습입니다.')
            self.restore_course_selection()
            return
        if self.mission and not self.passed and not initial:
            if QMessageBox.question(self, '종합 복습 전환', '현재 문제의 임시 파일은 버려집니다. 종합 복습으로 전환할까요?') != QMessageBox.StandardButton.Yes:
                self.restore_course_selection()
                return
        self.clear_random()
        self.index, self.checkpoint_end = end - 1, end
        self.topic = topic_of(self.units[self.index])
        self.phase, self.mission, self.passed = 'checkpoint_ready', None, False
        self.task_tabs.setCurrentIndex(0)
        self.refresh_course()
        for reader in self.readers: reader.stop_requested.set()
        self.generation += 1
        self.reset_extra_terminals()
        self.terminal.connected = False
        self.terminal.reset()
        checkpoint = checkpoint_at(end, self.mode)
        self.heading.setText(checkpoint_label(self.units, checkpoint))
        self.steps.setText('이전 5개 단원 조합 → 종합 테스트 → 통과 기록 저장 → 다음 단원')
        self.instructions.setPlainText('이번 구간에서 배운 기능을 하나의 작업으로 조합합니다.\n\n' +
            '\n'.join(f'{unit_number(self.units, end - 5 + i):02d}. {u.commands}' for i, u in enumerate(checkpoint.units)))
        self.feedback.setText('완료한 종합 복습도 목록에서 다시 선택해 새 문제로 연습할 수 있습니다.')
        self.next_button.setText('종합 테스트 시작 (F6)')
        self.restore_course_selection()
        if self.engine.name: self.run_job(lambda log: self.release_practice(), lambda value: None)
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
            if self._shutdown_requested:
                self._shutdown_requested = False
                self.update_controls()
                QTimer.singleShot(0, self.close)
                return  # Never start a new terminal after the user asked to exit.
            try:
                if 'error' in result_holder:
                    self.feedback.setText('작업 실패: ' + result_holder['error'])
                    self.task_tabs.setCurrentIndex(1)
                    if on_error is not None: on_error(result_holder['error'])
                elif 'value' in result_holder: callback(result_holder['value'])
            except Exception as exc:
                self.feedback.setText('작업 실패: ' + str(exc))
                self.task_tabs.setCurrentIndex(1)
                if on_error is not None: on_error(str(exc))
            self.update_controls()
        self.worker.finished.connect(finished)
        self.worker.start()

    def release_practice(self):
        if self.mode == 'real' and hasattr(self.engine, 'release_practice'):
            self.engine.release_practice()
        else:
            self.engine.close()

    def prepare_environment(self):
        self.about_environment()

    def choose_mode(self):
        if self.busy: return
        dialog = ModeDialog(self, progress_path=self.base_progress_path)
        if dialog.exec() == QDialog.DialogCode.Accepted and dialog.selected_mode != self.mode:
            if dialog.selected_mode == 'python':
                self.open_python()
                return
            if dialog.selected_mode == 'conda':
                self.open_conda()
                return
            if self.mission and QMessageBox.question(self, '실습 모드 변경',
                    '완료 진도와 기억노트는 보존됩니다. 현재 문제의 임시 실습 상태는 버리고 모드를 바꿀까요?') != QMessageBox.StandardButton.Yes:
                return
            self.switch_mode(dialog.selected_mode)
        if self.terminal.connected:
            self.terminal.setFocus()

    def open_python(self):
        self.mode_requested.emit('python')

    def open_conda(self):
        self.mode_requested.emit('conda')

    def refresh_mode_labels(self):
        real = self.mode == 'real'
        self.setWindowTitle(f'Shellground {APP_VERSION} — {MODES[self.mode].title}')
        self.mode_label.setText('현재 모드: ' + MODES[self.mode].title + (' · 앱 전용 Linux에서 실제 프로그램 실행' if real else ' · 실제 Linux 도구를 실행하는 모드가 아닙니다.'))
        self.environment.setText('전용 Linux·Docker 미리 준비 · 단원 이동 시 유지 · ROS는 실습 선택 시 시작' if real else
                                 '오프라인 시뮬레이터 · 지원 범위 안의 모의 동작 · 실제 Bash/nano/Docker가 아님')
        self.check_env.setText('실제 Linux 상태' if real else '시뮬레이터 상태')
        self.setup.setText('실행 환경 안내')
        self.more_terminal.setVisible(real)
        self.view_guest.setVisible(real)
        self.terminal_tabs.tabBar().setVisible(real)
        self.statusBar().showMessage('실제 Linux 상태로 채점합니다.' if real else '가상 상태로 채점합니다. 실제 도구의 전체 동작을 구현한 것은 아닙니다.')

    def switch_mode(self, mode):
        if self.busy or mode == self.mode:
            return
        # Validate before releasing the current session. No simulated fallback.
        try:
            next_engine = create_engine(mode)
        except Exception as exc:
            self.feedback.setText(str(exc))
            return
        old_engine = self.engine
        for reader in self.readers: reader.stop_requested.set()
        self.generation += 1
        self.reset_extra_terminals()
        self.terminal.connected = False
        def switched(value):
            if self.guest_display:
                self.guest_display.stop()
                self.guest_display = None
            self.engine = next_engine
            self.mode = mode
            self.units, self.checkpoints = curriculum(mode)
            self.progress.setMaximum(len(self.units))
            self.progress_path = mode_progress_path(self.base_progress_path, mode)
            self.completed, self.completed_checkpoints = [], []
            self.load_progress()
            self.index, self.checkpoint_end = 0, None
            self.phase, self.mission, self.passed = 'learn', None, False
            self.progress_note.setText(MODES[mode].title + ' 완료 진도 · 다른 모드의 완료 기록과 별도로 저장')
            self.refresh_mode_labels()
            self.refresh_course()
            self.select_initial()
            if mode == 'real' and hasattr(self.engine, 'prewarm'):
                self.engine.prewarm()
        self.run_job(lambda log: old_engine.close(), switched)

    def show_guest_display(self):
        if self.mode != 'real' or not self.engine.name:
            return
        if self.guest_display is None:
            self.guest_display = GuestDisplay(self.engine, self)
        self.guest_display.show()
        self.guest_display.raise_()

    def connect_terminal(self, terminal):
        def send(data):
            if self.mode == 'real':
                process = getattr(terminal, 'real_process', None)
                if process is not None:
                    import base64
                    if self.engine.channel:
                        self.engine.channel.send({'action': 'input', 'session': process.sid, 'data': base64.b64encode(data).decode()})
            else:
                self.engine.send(data)
        def resize(rows, cols):
            process = getattr(terminal, 'real_process', None)
            if self.mode == 'real' and process is not None and self.engine.channel:
                self.engine.channel.send({'action': 'resize', 'session': process.sid, 'size': [rows, cols]})
            elif self.mode != 'real':
                self.engine.resize(rows, cols)
        terminal.input_bytes.connect(send)
        terminal.resized.connect(resize)

    def activate_terminal(self, index):
        terminal = self.terminal_tabs.widget(index)
        if terminal is None:
            return
        self.terminal = terminal
        if self.mode == 'real' and getattr(terminal, 'real_process', None):
            self.engine.bridge = terminal.real_process
        if hasattr(self, 'shortcut_actions'):
            self.update_controls()
        terminal.setFocus()

    def reset_extra_terminals(self):
        self.terminal_tabs.blockSignals(True)
        for terminal in self.terminals[1:]:
            terminal.connected = False
            self.terminal_tabs.removeTab(self.terminal_tabs.indexOf(terminal))
            terminal.deleteLater()
        self.terminals = self.terminals[:1]
        self.terminal = self.terminals[0]
        self.terminal.real_process = None
        self.terminal_tabs.setCurrentIndex(0)
        self.terminal_tabs.blockSignals(False)

    def attach_reader(self, terminal, process, generation):
        if self.mode == 'real':
            terminal.real_process = process
        reader = TerminalReader(process)
        self.reader = reader
        self.readers.append(reader)
        def consume(data):
            try:
                if generation == self.generation and terminal in self.terminals:
                    self.engine.observe_output(data)
                    terminal.feed(data)
            finally:
                reader.pending.release()
        reader.output.connect(consume)
        reader.ended.connect(lambda message: self.shell_ended(generation, message, terminal))
        reader.finished.connect(self.release_readers)
        reader.start()
        terminal.connected = True
        if self.mode == 'real':
            self.engine.channel.send({'action': 'resize', 'session': process.sid,
                                      'size': [terminal.screen.lines, terminal.screen.columns]})
        else:
            self.engine.resize(terminal.screen.lines, terminal.screen.columns)

    def new_terminal(self):
        if self.busy or self.mode != 'real' or not self.mission or not self.engine.channel or len(self.terminals) >= 8:
            return
        generation = self.generation
        def ready(process):
            terminal = TerminalWidget(self.mono_family)
            terminal.apply_settings(self.settings)
            self.connect_terminal(terminal)
            self.terminals.append(terminal)
            index = self.terminal_tabs.addTab(terminal, '터미널 ' + str(process.sid))
            self.attach_reader(terminal, process, generation)
            self.terminal_tabs.setCurrentIndex(index)
            self.engine.bridge = process
            terminal.setFocus()
        self.run_job(lambda log: self.engine.channel.open_terminal(self.mission.start), ready)

    def close_terminal_tab(self, index):
        if self.busy or index <= 0 or self.mode != 'real':
            return
        terminal = self.terminal_tabs.widget(index)
        if QMessageBox.question(self, '터미널 종료', '이 터미널의 셸과 연결된 작업을 종료할까요? 다른 터미널과 파일은 유지합니다.') != QMessageBox.StandardButton.Yes:
            return
        process = getattr(terminal, 'real_process', None)
        if process and self.engine.channel:
            self.engine.channel.send({'action': 'close', 'id': 0, 'session': process.sid})
        terminal.connected = False
        self.terminals.remove(terminal)
        self.terminal_tabs.removeTab(index)
        terminal.deleteLater()

    def about_environment(self):
        if self.mode == 'real':
            QMessageBox.information(self, '실제 Linux 모드', MODES['real'].description +
                '\n\n불변 기본 이미지와 실행마다 새로 만드는 실습 디스크를 사용합니다. 실습 파일은 임시 상태이며 완료 진도와 기억노트만 보존합니다.\n'
                '파일 다운로드·APT·Docker pull은 게스트 내부 교육용 서버와 저장소를 사용합니다. 호스트의 파일·장치·Docker 소켓을 공유하지 않습니다.\n'
                'GPU 등 별도 하드웨어 동작과 Windows 실기기 검증은 지원 범위 안내를 확인하세요.')
            return
        QMessageBox.information(self, '시뮬레이터 범위', 'Windows/Linux 네이티브 Qt 프로그램입니다.\n명령은 메모리 안의 가상 Linux·Docker 상태에 적용됩니다.\nDocker·WSL·VM 설치나 인터넷 연결은 필요하지 않습니다.\n\n경로·파일 내용·권한·파이프·리다이렉션·종료 코드와 이미지·컨테이너 상태를 관리합니다. 지원하지 않는 명령/옵션은 명시적으로 실패합니다. 모든 bash/GNU/Docker 동작이 구현된 것은 아닙니다.\n\n다운로드는 준비된 가상 URL만, Docker pull은 가상 저장소만 사용합니다. GPU·실제 네트워크·성능 측정·호스트 마운트는 실행하지 않습니다. nano는 학습용 편집기 구현입니다.\n\n완료 진도와 기억노트만 사용자 설정 폴더에 저장합니다. 실습 파일·이미지는 호스트 파일이 아니며 재시작/종료 시 사라집니다.')

    def select_lesson(self, index, initial=False):
        if self.busy: return
        if not self.lesson_unlocked(index):
            self.feedback.setText('현재 과정에 없는 단원입니다.')
            self.restore_course_selection()
            return
        if self.mission and not self.passed and not initial:
            if QMessageBox.question(self, '실습 전환', '현재 문제의 임시 파일은 버려집니다. 단계를 바꿀까요?') != QMessageBox.StandardButton.Yes:
                self.restore_course_selection(); return
        self.clear_random()
        self.index, self.phase, self.mission, self.passed = index, 'learn', None, False
        self.learning_sequence = learning_steps(self.units[index], self.mode)
        self.learning_step = cursor_for(self.learning_progress, self.units[index].key, self.learning_sequence)
        self.learning_resume_from = self.learning_step
        if not initial:
            if self.learning_sequence: self.remember_learning()
            elif self.last_learning:
                self.last_learning = ''
                self.save_progress()
        self.task_tabs.setCurrentIndex(0)
        self.topic = topic_of(self.units[index])
        self.checkpoint_end = None
        self.refresh_course()
        for reader in self.readers: reader.stop_requested.set()
        self.generation += 1
        self.reset_extra_terminals()
        self.terminal.connected = False
        self.terminal.reset()
        unit = self.units[index]
        self.heading.setText(f'{self.topic} {unit_number(self.units, index):02d}. {unit.title} — {unit.commands}')
        self.steps.setText('① 새 명령 배우기 → ② 예시 직접 실습 → ③ 활용 문제 2개 → ④ 배운 범위 올랜덤')
        self.instructions.setPlainText(unit.explanation)
        self.feedback.setText('F4로 설명을 보면서 직접 해볼 수 있습니다. 자유 연습은 완료 진도에 반영하지 않습니다.')
        self.next_button.setText('예시 실습 시작 (F6)')
        if self.learning_sequence: self.render_learning_step()
        self.restore_course_selection()
        if self.engine.name: self.run_job(lambda log: self.release_practice(), lambda value: None)
        self.update_controls()

    def try_lesson(self):
        if self.busy or self.phase != 'learn': return
        if self.mission and self.terminal.connected:
            self.terminal.setFocus()
            return
        if self.learning_sequence: self.remember_learning()
        self.launch(make_mission(self.units[self.index].key))

    def remember_learning(self, confirmed=None, leaving=False):
        if not self.learning_sequence: return
        key = self.units[self.index].key
        remember(self.learning_progress, key, self.learning_sequence, self.learning_step, confirmed)
        self.last_learning = '' if leaving else key
        self.save_progress()
        if hasattr(self, 'unit_rows') and self.index in self.unit_rows:
            self.refresh_course()

    def show_resume_preparation(self):
        if self.phase != 'learn' or not self.learning_resume_from: return
        dialog = QDialog(self)
        dialog.setWindowTitle('이어서 학습하기 · 이전 실습 상태 준비')
        dialog.resize(760, 540)
        layout = QVBoxLayout(dialog)
        note = QLabel('학습 진도는 복원했지만 실습 파일·실행 중 프로그램은 새로 준비됩니다.\n'
                      '연습 시작 후 필요한 앞 단계만 직접 실행하세요. 명령은 자동 실행하지 않습니다.')
        note.setWordWrap(True)
        layout.addWidget(note)
        text = QPlainTextEdit()
        text.setReadOnly(True)
        text.setPlainText('\n\n'.join(f'{i + 1}. {step.title}\n{step.text}'
                                     for i, step in enumerate(self.learning_sequence[:self.learning_resume_from])))
        layout.addWidget(text)
        close = QPushButton('닫기')
        close.clicked.connect(dialog.accept)
        layout.addWidget(close)
        dialog.exec()

    def render_learning_step(self):
        if self.phase != 'learn' or not self.learning_sequence: return
        step = self.learning_sequence[self.learning_step]
        unit = self.units[self.index]
        count = len(self.learning_sequence)
        self.heading.setText(f'{self.topic} {unit_number(self.units, self.index):02d}. {unit.title} — {step.title}')
        done = confirmed_count(self.learning_progress, unit.key, self.learning_sequence)
        self.steps.setText(f'소단계 {self.learning_step + 1}/{count} · 확인 {done}/{count} 저장 · 전체 조합 예시 → 활용 1·2')
        location = self.mission.start if self.mission else '실습 시작 시 준비됩니다. 아래 이름/경로도 실제 문제에 맞춰 바뀝니다.'
        self.instructions.setPlainText('실습 위치: ' + location + '\n' + step.text)
        self.task_tabs.setCurrentIndex(0)
        if not self.mission:
            label = '이 소단계 연습 시작'
        elif self.learning_step + 1 < count:
            label = '다음 소단계'
        else:
            label = '전체 조합 예시 시작'
        self.next_button.setText(label + ' (F6)')
        resume = ('저장된 소단계부터 이어갑니다. 종료 전 실습 파일은 복원되지 않습니다. '
                  '필요하면 ‘재개 준비 명령’을 확인하세요. ' if self.learning_resume_from else '')
        self.feedback.setText(resume + '소단계 위치와 다음으로 넘긴 확인 기록은 자동 저장합니다. '
                              '이 기록은 채점 통과가 아니며 단원 완료는 활용 문제 통과로 결정합니다. '
                              '소단계 이동 중에는 현재 실습 상태를 유지합니다.')

    def previous_learning_step(self):
        if self.busy or self.phase != 'learn' or not self.learning_sequence or self.learning_step == 0: return
        self.learning_step -= 1
        self.remember_learning()
        self.render_learning_step()
        self.update_controls()
        if self.terminal.connected: self.terminal.setFocus()

    def launch(self, mission):
        if self.mode == 'real':
            mission = adapt_real_mission(mission)
        for reader in self.readers: reader.stop_requested.set()
        self.mission, self.passed = mission, False
        self.task_tabs.setCurrentIndex(0)
        self.refresh_course()
        self.generation += 1
        self.reset_extra_terminals()
        generation = self.generation
        self.terminal.connected = False
        self.terminal.reset()
        random_scope = '전체 분야' if self.random_all_topics else self.topic
        self.steps.setText({'learn': '① 새 명령 배우기 · 설명 보며 자유 연습', 'example': '② 예시 직접 실습', 'practice': f'③ 활용 {self.practice_number}/2 · ' + ('핵심 기능 확인' if self.practice_number == 1 else '조합·문제 해결'), 'random': f'④ {random_scope} · 배운 범위 올랜덤', 'checkpoint': '종합 테스트 · 앞 5개 단원 조합'}[self.phase])
        self.heading.setText(checkpoint_label(self.units, checkpoint_at(self.checkpoint_end, self.mode)) if self.phase == 'checkpoint' else next(u.title for u in self.units if u.key == mission.kind))
        text = f'시작 위치: {mission.start}\n\n목표: {mission.prompt}'
        if self.phase == 'learn':
            text = self.units[self.index].explanation + '\n\n지금 직접 해볼 명령:\n' + mission.solution
        if self.phase == 'example': text += '\n\n따라 입력할 예시 (한 줄씩 Enter):\n' + mission.solution
        if self.phase in ('learn', 'example') and mission.interaction:
            text += '\n\n' + mission.interaction
        self.instructions.setPlainText(text)
        self.feedback.setText('실제 Linux를 시작하고 실습을 준비하는 중…' if self.mode == 'real' else '새 가상 실습 상태를 준비하는 중…')
        self.next_button.setText('예시 실습 시작 (F6)' if self.phase == 'learn' else '다음 문제 (F6)')
        if self.phase == 'learn' and self.learning_sequence:
            self.learning_sequence = learning_steps(self.units[self.index], self.mode, mission)
            self.render_learning_step()
        def ready(value):
            process = self.engine.open_terminal(mission)
            self.attach_reader(self.terminal, process, generation)
            self.terminal.setFocus()
            self.feedback.setText('설명을 보며 자유롭게 실행하세요. F6은 새 환경에서 예시를 시작하며 자유 연습 파일은 초기화됩니다.' if self.phase == 'learn' else '준비되었습니다. 명령을 자유롭게 실행한 뒤 결과 채점을 누르세요.')
            if self.phase == 'learn' and self.learning_sequence: self.render_learning_step()
            self.refresh_mode_labels()
        self.run_job(lambda log: self.engine.start(mission), ready)

    def release_readers(self):
        self.readers = [reader for reader in self.readers if reader.isRunning()]

    def shell_ended(self, generation, message, terminal=None):
        terminal = terminal or self.terminal
        if generation == self.generation and terminal in self.terminals:
            terminal.connected = False
            if terminal is self.terminal:
                self.feedback.setText(message)
            self.update_controls()

    def restart_mission(self):
        if self.mission and QMessageBox.question(self, '문제 다시 시작', '이 문제에서 만든 파일을 지우고 처음 상태로 다시 시작할까요?') == QMessageBox.StandardButton.Yes:
            if self.phase == 'learn':
                self.learning_step = 0
                self.learning_resume_from = 0
                self.remember_learning()
            self.launch(self.mission)

    def advance(self):
        if self.busy: return
        if self.phase == 'checkpoint_ready':
            self.phase = 'checkpoint'
            self.launch(make_checkpoint(self.checkpoint_end, mode=self.mode))
        elif self.phase == 'learn':
            if self.learning_sequence:
                if not self.mission or not self.terminal.connected:
                    self.try_lesson()
                    return
                if self.learning_step + 1 < len(self.learning_sequence):
                    confirmed = self.learning_step
                    self.learning_step += 1
                    self.remember_learning(confirmed)
                    self.render_learning_step()
                    self.update_controls()
                    if self.terminal.connected: self.terminal.setFocus()
                    return
                self.remember_learning(self.learning_step, leaving=True)
            self.phase = 'example'
            self.launch(make_mission(self.units[self.index].key))
        elif not self.passed: return
        elif self.phase == 'example':
            self.phase, self.practice_number = 'practice', 1
            self.launch(make_mission(self.units[self.index].key, practice=1))
        elif self.phase == 'practice' and self.practice_number < 2:
            self.practice_number += 1
            self.launch(make_mission(self.units[self.index].key, practice=2))
        elif self.phase == 'practice':
            if (self.index + 1) % 5 == 0: self.select_checkpoint(self.index + 1)
            else: self.advance_in_topic()
        elif self.phase == 'checkpoint':
            self.advance_in_topic()
        elif self.phase == 'random': self.launch(random_mission(self.random_keys(), self.mission.kind, self.units))

    def advance_in_topic(self):
        index = next_in_topic(self.units, self.index)
        if index is None: self.start_random()
        else: self.select_lesson(index)

    def random_keys(self):
        return [u.key for u in self.units if u.key in self.completed and (self.random_all_topics or topic_of(u) == self.topic)]

    def start_random(self, all_topics=False):
        if not self.completed or self.busy: return
        keys = [u.key for u in self.units if u.key in self.completed and (all_topics or topic_of(u) == self.topic)]
        if not keys: return
        if self.mission and not self.passed:
            if QMessageBox.question(self, '올랜덤 시작', '현재 문제의 임시 파일은 버려집니다. 올랜덤으로 전환할까요?') != QMessageBox.StandardButton.Yes: return
        if self.phase != 'random':
            self.random_return = (self.index, self.checkpoint_end, self.learning_step if self.phase == 'learn' else 0)
        self.phase, self.random_count = 'random', 0
        self.random_all_topics = all_topics
        self.checkpoint_end = None
        self.launch(random_mission(keys, units=self.units))

    def clear_random(self):
        self.random_return = None
        self.random_all_topics = False
        self.random_count = 0

    def exit_random(self):
        if self.busy or self.phase != 'random': return
        if self.mission and not self.passed:
            if QMessageBox.question(self, '올랜덤 종료',
                    '완료 진도는 유지됩니다. 현재 랜덤 문제의 임시 실습 상태는 버리고 이전 학습 화면으로 돌아갈까요?\n'
                    '올랜덤 시작 전의 실습 파일은 복원되지 않습니다.') != QMessageBox.StandardButton.Yes:
                return
        index, checkpoint, step = self.random_return or (self.index, None, 0)
        if checkpoint:
            self.select_checkpoint(checkpoint, initial=True)
        else:
            self.select_lesson(index, initial=True)
            if self.learning_sequence:
                self.learning_step = min(step, len(self.learning_sequence) - 1)
                self.render_learning_step()
                self.update_controls()

    def grade(self):
        if self.busy or self.phase == 'learn' or not self.mission or self.passed or not self.terminal.connected: return
        def result(value):
            self.passed = value['passed']
            count = sum(bool(item['passed']) for item in value['checks'])
            summary = ('목표 달성' if self.passed else '미완료 항목 있음') + f' · {count}/{len(value["checks"])} 통과'
            self.feedback.set_results(summary, value['checks'])
            self.task_tabs.setCurrentIndex(1)
            # Grading is read-only: keep the same PTY, files and scrollback.
            # A mouse click on F5 otherwise leaves keyboard input on the button.
            if self.terminal.connected:
                self.terminal.setFocus(Qt.FocusReason.OtherFocusReason)
            if self.passed:
                if self.phase == 'practice' and self.practice_number == 2:
                    key = self.units[self.index].key
                    if key not in self.completed:
                        self.completed.append(key)
                        self.save_progress()
                    self.refresh_course()
                    next_label = '종합 복습으로' if (self.index + 1) % 5 == 0 else ('다음 단계 배우기' if self.index + 1 < len(self.units) else '올랜덤 시작')
                    self.next_button.setText(next_label + ' (F6)')
                elif self.phase == 'checkpoint':
                    key = checkpoint_at(self.checkpoint_end, self.mode).key
                    if key not in self.completed_checkpoints:
                        self.completed_checkpoints.append(key)
                        self.save_progress()
                    self.refresh_course()
                    self.next_button.setText('다음 단계 배우기 (F6)')
                elif self.phase == 'random':
                    self.random_count += 1
                    self.next_button.setText(f'다음 랜덤 문제 (통과 {self.random_count}) (F6)')
                self.statusBar().showMessage('목표 달성! ' + ('실제 Linux' if self.mode == 'real' else '가상') + ' 파일·현재 위치·내용·권한·상태로 채점했습니다.')
            else:
                self.statusBar().showMessage('미완료 항목을 이어서 해결하고 F5로 다시 채점하세요. F2는 파일 초기화입니다.')
        def grading_error(message):
            self.feedback.setText('채점 실패: ' + message + '\n실습은 초기화하지 않았습니다. 연결이 유지되어 있다면 계속 조작하고 F5로 다시 시도하세요.')
            self.task_tabs.setCurrentIndex(1)
            if self.terminal.connected:
                self.terminal.setFocus(Qt.FocusReason.OtherFocusReason)
        self.run_job(lambda log: self.engine.rpc('grade', self.mission), result, on_error=grading_error)

    def show_hint(self):
        if self.mission:
            if self.phase == 'learn' and self.learning_sequence:
                QMessageBox.information(self, '현재 소단계', self.learning_sequence[self.learning_step].text)
                return
            hint = ('이번 조합 문제의 한 가지 풀이:\n' + self.mission.solution + '\n' + self.mission.interaction
                    if self.mission.review else next(u.hint for u in self.units if u.key == self.mission.kind))
            QMessageBox.information(self, '힌트', hint)

    def open_system_concepts(self):
        if self.busy or self.mode != 'real': return
        from system_concept_dialog import SystemConceptDialog
        try:
            dialog = SystemConceptDialog(self.base_progress_path.with_name('system-concepts-v1.json'), self,
                                         'docker' if self.topic == 'Docker' else 'linux', self.open_concept_lesson)
        except (OSError, ValueError, KeyError) as error:
            QMessageBox.warning(self, '개념 학습을 열 수 없습니다', str(error))
            return
        try:
            dialog.exec()
        finally:
            dialog.deleteLater()

    def open_concept_lesson(self, key):
        if self.busy or self.mode != 'real': return False
        index = next((i for i, unit in enumerate(self.units) if unit.key == key), None)
        if index is None: return False
        self.select_lesson(index)
        return self.index == index and self.phase == 'learn' and self.mission is None

    def remember(self):
        unit = next((u for u in self.units if self.mission and u.key == self.mission.kind), self.units[self.index])
        selected = self.instructions.textCursor().selectedText()
        self.open_notes(suggest_note(unit, self.mission, selected))

    def open_notes(self, draft=None):
        dialog = MemoryDialog(self.note_store, self, draft if isinstance(draft, dict) else None)
        dialog.exec()
        self.terminal.setFocus()

    def show_options(self):
        unit = next((u for u in self.units if self.mission and u.key == self.mission.kind), self.units[self.index])
        checkpoint = checkpoint_at(self.checkpoint_end, self.mode) if self.checkpoint_end else None
        dialog = QDialog(self)
        dialog.setWindowTitle('옵션 설명 — ' + (checkpoint_label(self.units, checkpoint) if checkpoint else unit.title))
        dialog.resize(720, 580)
        layout = QVBoxLayout(dialog)
        text = QPlainTextEdit()
        text.setReadOnly(True)
        text.setPlainText('\n\n────────\n\n'.join(u.title + '\n' + lesson_text(u, self.mode) for u in checkpoint.units) if checkpoint else lesson_text(unit, self.mode))
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
            self.finish_shutdown(event)
            return
        if self._closing:
            event.ignore()
            return
        if self.busy:
            self._shutdown_requested = True
            if hasattr(self.engine, 'cancel_pending'):
                self.engine.cancel_pending()
            self.statusBar().showMessage('진행 중인 작업 취소 후 종료하는 중…')
            event.ignore(); return
        event.ignore()
        self._closing = True
        if hasattr(self.engine, 'cancel_pending'):
            self.engine.cancel_pending()
        for reader in self.readers: reader.stop_requested.set()
        self.generation += 1
        for terminal in self.terminals:
            terminal.connected = False
        def closed(value):
            if self.guest_display and not self.guest_display.stop():
                raise RuntimeError('게스트 화면 요청 종료를 기다리는 중입니다.')
            for reader in self.readers:
                if not reader.wait(3000):
                    raise RuntimeError('터미널 종료를 기다리는 중입니다. 잠시 후 종료를 다시 눌러 주세요.')
            self._shutdown_ready = True
            self.close()
        def failed(message):
            self._closing = False
            self.statusBar().showMessage('정리가 완료되지 않았습니다. 위 오류를 확인한 뒤 종료를 다시 시도하세요.')
            self.shutdown_failed.emit(message)
        self.feedback.setText('앱 전용 Linux 종료 중…' if self.mode == 'real' else '가상 실습 상태를 정리하는 중…')
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
    parser.add_argument('--self-test-real', action='store_true', help='실제 런타임·ROS·APT·Docker 갱신/복원/배포·화면·종료 검사 (진도 저장 안 함)')
    parser.add_argument('--self-test-real-crash', action='store_true', help='Linux 전용: 임시 앱의 비정상 종료 후 VM 정리 검사 (진도 저장 안 함)')
    parser.add_argument('--mode', choices=tuple(MODES)+('python','conda'), help='실습 모드 (실제 모드는 내장 런타임 필요)')
    parser.add_argument('--layout', choices=tuple(PRESETS), default=DEFAULT_LAYOUT, help='이번 실행의 배치; 기본값은 채택된 A 균형형')
    parser.add_argument('--layout-preview', action='store_true', help='같은 문제·출력으로 배치 시안 비교 (명령 실행·진도 저장 없음)')
    args = parser.parse_args()
    if args.version: print(APP_VERSION); return 0
    if args.self_test_real_crash:
        from vm_crash_diagnostics import verify_crash_cleanup
        verify_crash_cleanup()
        return 0
    if args.self_test_real:
        from runtime_diagnostics import verify_real_runtime
        return verify_real_runtime()
    if args.self_test:
        if not resource_path('guest/bashrc').is_file():
            raise RuntimeError('Bundled terminal configuration is missing')
        simulation_units, simulation_checkpoints = curriculum('simulation')
        for unit in simulation_units: assert make_mission(unit.key, 1234).solution
        for checkpoint in simulation_checkpoints: assert make_checkpoint(checkpoint.end, 1234, mode='simulation').solution
        engine = create_engine(SIMULATION.key)
        for key in ('mkdir', 'sim_commit', 'admin_review'):
            mission = make_mission(key, 4242)
            engine.start(mission)
            for command in mission.solution.splitlines():
                result = engine.shell.execute(command)
                assert result.code == 0, result.err
            assert engine.rpc('grade', mission)['passed']
        engine.close()
        print(f'Shellground {APP_VERSION}: {len(simulation_units)} simulator units + {len(simulation_checkpoints)} checkpoints; resources OK; no Docker/WSL/VM required')
        return 0
    if args.layout_preview:
        from ui_layout_preview import run_preview
        return run_preview(args.layout)
    if args.mode and args.mode not in ('python','conda') and not mode_available(args.mode):
        print('내장 실제 Linux 런타임이 준비되지 않았습니다. 시뮬레이션으로 대신 실행하지 않습니다.', file=sys.stderr)
        return 2
    app, ui, mono = create_application()
    settings_path = Path(QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppDataLocation)) / 'settings-v1.json'
    app.setPalette(theme_palette(load_settings(settings_path).theme))
    warm = create_engine('real') if args.mode in (None, 'real') and mode_available('real') else None
    if warm:
        warm.prewarm()
    try:
        mode = args.mode
        if mode is None:
            dialog = ModeDialog()
            if dialog.exec() != QDialog.DialogCode.Accepted:
                return 0
            mode = dialog.selected_mode
        if warm and mode != 'real':
            warm.cancel_pending()
            threading.Thread(target=warm.close, name='shellground-unused-warmup', daemon=True).start()
        from study_window import StudyWindow
        window = StudyWindow(ui, mono, mode=mode, layout=args.layout,
                             linux_engine=warm if mode == 'real' else None)
        window.show()
        return app.exec()
    finally:
        if warm:
            warm.cancel_pending()
            warm.close()
