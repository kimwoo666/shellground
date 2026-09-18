"""Native Python study room. No browser/web view and no simulated Python."""
import base64
import json
from pathlib import Path
import random
from PySide6.QtCore import Qt, QStandardPaths, QThread, Signal, QTimer
from PySide6.QtGui import QFont, QAction, QPixmap
from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QComboBox,
                              QListWidget, QPlainTextEdit, QPushButton, QLabel, QSplitter,
                              QTabWidget, QMessageBox, QScrollArea, QTabBar, QStackedWidget)
from feedback_panel import FeedbackPanel
from python_teaching.course import lessons
from python_teaching.engine import PythonEngine
from python_teaching.values import grade_snapshot
from python_teaching.progress import PythonProgress
from app_settings import load_settings, theme_palette
from python_editor import PythonEditor
from study_page import StudyPage


class PythonJob(QThread):
    finished_value = Signal(object)
    failed = Signal(str)
    def __init__(self, function):
        super().__init__()
        self.function = function
    def run(self):
        try: self.finished_value.emit(self.function())
        except Exception as exc: self.failed.emit(str(exc))


class PythonWindow(StudyPage):
    def __init__(self, ui_family, mono_family, progress_path=None):
        super().__init__()
        self.setWindowTitle('Shellground — Python·데이터 학습')
        self.resize(1220, 880)
        self.units = lessons()
        self.engine = PythonEngine()
        self.worker = None
        self.notebook = None
        self._notebook_close_started = False
        self.busy = False
        self._close_pending = False
        self.index, self.step, self.variant = 0, 0, 0
        self.phase = 'learn'
        self.solved = False
        self.random_return = None
        path = progress_path or Path(QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppDataLocation)) / 'python-progress-v1.json'
        self.progress = PythonProgress(path)
        settings = load_settings(Path(path).with_name('settings-v1.json'))
        self.setPalette(theme_palette(settings.theme))
        self.ui_family, self.mono_family = ui_family, mono_family
        container = QWidget()
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(0,0,0,0)
        self.python_sections = QTabBar()
        self.python_sections.setExpanding(False)
        self.python_sections.addTab('Python · 라이브러리')
        self.python_sections.addTab('노트북 · Jupyter')
        container_layout.addWidget(self.python_sections)
        self.python_stack = QStackedWidget()
        container_layout.addWidget(self.python_stack,1)
        self.setCentralWidget(container)
        root = QWidget()
        self.python_stack.addWidget(root)
        outer = QVBoxLayout(root)
        top = QHBoxLayout()
        title = QLabel('SHELLGROUND · Python')
        title.setFont(QFont(ui_family, 14, QFont.Weight.Bold))
        top.addWidget(title)
        top.addStretch()
        self.status = QLabel()
        top.addWidget(self.status)
        outer.addLayout(top)
        self.menuBar().addAction('사용 안내').triggered.connect(self.show_usage)
        splitter = QSplitter(Qt.Orientation.Horizontal)
        outer.addWidget(splitter, 1)
        left = QWidget()
        navigation = QVBoxLayout(left)
        self.topics = QComboBox()
        self.topics.addItems(list(dict.fromkeys(u.topic for u in self.units)))
        self.topics.currentTextChanged.connect(self.change_topic)
        navigation.addWidget(self.topics)
        self.course = QListWidget()
        self.course.setWordWrap(True)
        self.course.itemClicked.connect(lambda item: self.select_lesson(item.data(Qt.ItemDataRole.UserRole)))
        navigation.addWidget(self.course, 1)
        self.random_button = QPushButton('배운 범위 올랜덤')
        self.random_button.clicked.connect(self.start_random)
        navigation.addWidget(self.random_button)
        self.exit_random = QPushButton('올랜덤 종료 · 이전 학습')
        self.exit_random.clicked.connect(self.stop_random)
        navigation.addWidget(self.exit_random)
        self.quiz_button = QPushButton('개념 퀴즈')
        self.quiz_button.clicked.connect(self.show_quiz)
        navigation.addWidget(self.quiz_button)
        splitter.addWidget(left)
        right = QWidget()
        body = QVBoxLayout(right)
        self.heading = QLabel()
        self.heading.setFont(QFont(ui_family, 13, QFont.Weight.Bold))
        self.heading.setWordWrap(True)
        body.addWidget(self.heading)
        self.task_tabs = QTabWidget()
        self.instructions = QPlainTextEdit()
        self.instructions.setReadOnly(True)
        self.feedback = FeedbackPanel()
        self.feedback.set_dark_theme(settings.theme == 'dark')
        self.task_tabs.addTab(self.instructions, '문제·설명')
        self.task_tabs.addTab(self.feedback, '채점 결과')
        body.addWidget(self.task_tabs, 2)
        tools = QHBoxLayout()
        self.previous = QPushButton('← 이전 소단계')
        self.previous.clicked.connect(self.previous_step)
        tools.addWidget(self.previous)
        self.run_button = QPushButton('코드 실행 (Shift+Enter)')
        self.run_button.clicked.connect(self.run_code)
        tools.addWidget(self.run_button)
        self.stop_button = QPushButton('실행 중단')
        self.stop_button.clicked.connect(self.engine.cancel)
        tools.addWidget(self.stop_button)
        body.addLayout(tools)
        work = QSplitter(Qt.Orientation.Horizontal)
        self.editor = PythonEditor()
        self.editor.execute_requested.connect(self.run_code)
        self.editor.setFont(QFont(mono_family, settings.terminal_font_size))
        self.editor.setPlaceholderText('Python 코드를 입력하세요. 셸 명령(pip/conda)은 이 칸에서 실행하지 않습니다.')
        self.editor.setStyleSheet('QPlainTextEdit { background:#101714; color:#dbe9df; }')
        work.addWidget(self.editor)
        self.output_tabs = QTabWidget()
        self.output = QPlainTextEdit()
        self.output.setReadOnly(True)
        self.output.setFont(QFont(mono_family, settings.terminal_font_size))
        self.output_tabs.addTab(self.output, '실행 출력')
        self.figure = QLabel('그림을 만들면 여기에 표시됩니다.')
        self.figure.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.figure_area = QScrollArea()
        self.figure_area.setWidget(self.figure)
        self.figure_area.setWidgetResizable(True)
        self.output_tabs.addTab(self.figure_area, '그래프')
        work.addWidget(self.output_tabs)
        work.setSizes([500,450])
        body.addWidget(work, 3)
        buttons = QHBoxLayout()
        self.hint = QPushButton('힌트 (F1)')
        self.hint.clicked.connect(self.show_hint)
        self.restart = QPushButton('실습 다시 시작 (F2)')
        self.restart.clicked.connect(self.restart_problem)
        self.grade_button = QPushButton('결과 채점 (F5)')
        self.grade_button.clicked.connect(self.grade)
        self.next_button = QPushButton()
        self.next_button.clicked.connect(self.advance)
        for button in (self.hint,self.restart,self.grade_button,self.next_button): buttons.addWidget(button)
        body.addLayout(buttons)
        splitter.addWidget(right)
        splitter.setSizes([235,970])
        for shortcut, callback in [('Shift+Return',self.run_code),('F1',self.show_hint),('F2',self.restart_problem),('F4',self.start_lab),('F5',self.grade),('F6',self.advance)]:
            action = QAction(self)
            action.setShortcut(shortcut)
            action.setAutoRepeat(False)
            action.triggered.connect(callback)
            self.addAction(action)
        resume = self.progress.data.get('resume', {})
        key = resume.get('unit')
        index = next((i for i,u in enumerate(self.units) if u.key == key), 0)
        self.select_lesson(index, initial=True)
        if key == self.units[index].key:
            self.phase = resume.get('phase') if resume.get('phase') in ('learn','example','practice1','practice2') else 'learn'
            self.variant = {'learn':0,'example':0,'practice1':1,'practice2':2}[self.phase]
            self.step = min(max(resume.get('step',0),0),1) if isinstance(resume.get('step',0),int) else 0
            self.render()
        self.python_sections.currentChanged.connect(self.change_python_section)

    @property
    def busy(self):
        return self._busy or bool(self.notebook and self.notebook.busy)

    @busy.setter
    def busy(self,value):
        self._busy = value

    def change_python_section(self,index):
        previous=self.python_stack.currentIndex()
        if self.busy or self._close_pending:
            self.python_sections.blockSignals(True);self.python_sections.setCurrentIndex(previous);self.python_sections.blockSignals(False)
            return
        if index==1 and self.notebook is None:
            from notebook_app import NotebookWindow
            self.notebook=NotebookWindow(self.ui_family,self.mono_family,self.progress.path.with_name('notebook-progress-v1.json'))
            self.notebook.setParent(self.python_stack,Qt.WindowType.Widget)
            self.python_stack.addWidget(self.notebook)
            self.notebook.shutdown_finished.connect(lambda:QTimer.singleShot(0,self.close) if self._close_pending else None)
            self.notebook.shutdown_failed.connect(self.notebook_close_failed)
        self.save();self.python_stack.setCurrentIndex(index)
        for action in self.actions():action.setEnabled(index==0)
        self.setWindowTitle('Shellground — Python 노트북' if index else 'Shellground — Python·데이터 학습')

    def notebook_close_failed(self,message):
        self._notebook_close_started=False;self._close_pending=False
        self.shutdown_failed.emit(message)

    @property
    def unit(self): return self.units[self.index]

    def open_conda(self):
        self.mode_requested.emit('conda')

    def show_usage(self):
        QMessageBox.information(self, 'Python 사용 안내',
            '상단 모드 탭으로 Linux·Python·Conda를 같은 창에서 전환합니다.\n'
            'Shift+Enter는 코드 실행, Enter는 줄바꿈입니다.\n'
            '완료·소단계 진도는 자동 저장됩니다. 입력 코드와 임시 실습 파일은 종료 후 저장하지 않습니다.\n\n'
            'Python 코드는 별도 프로세스에서 실행되지만 보안 VM은 아닙니다. '
            '신뢰할 수 없는 외부 코드는 실행하지 마세요.')
    @property
    def problem(self): return self.unit.problems[self.variant]

    def save(self):
        if self.notebook:self.notebook.save()
        try:
            if self.phase == 'random' and self.random_return:
                index,phase,step,variant=self.random_return
                self.progress.resume(self.units[index].key,phase,step)
            else: self.progress.resume(self.unit.key, self.phase, self.step)
        except OSError as exc: QMessageBox.warning(self, '진도 저장 실패', str(exc))

    def refresh_course(self):
        self.course.clear()
        testing = self.phase.startswith('practice') or self.phase == 'random'
        number = 0
        for i, unit in enumerate(self.units):
            if unit.topic != self.unit.topic: continue
            review=unit.key.startswith('review_')
            if not review:number += 1
            mark = '완료' if unit.key in self.progress.data['completed'] else '미완료'
            title = '평가 중 학습 내용 숨김' if testing else unit.title
            label='◆ 복습' if review else f'{number:02d}.'
            self.course.addItem(f'{label} [{mark}] {title}')
            item = self.course.item(self.course.count()-1)
            item.setData(Qt.ItemDataRole.UserRole, i)
            if i == self.index: self.course.setCurrentItem(item)
        self.topics.blockSignals(True)
        self.topics.setCurrentText(self.unit.topic)
        self.topics.blockSignals(False)
        self.status.setText(f"단원 완료 {len(self.progress.data['completed'])}/{len(self.units)}")

    def render(self):
        phase = {'learn':f'소단계 {self.step+1}/2', 'example':'예시 실습', 'practice1':'활용 1', 'practice2':'활용 2', 'random':'올랜덤'}[self.phase]
        self.heading.setText(f'{self.unit.topic} · {phase}' + (f' — {self.unit.title}' if not self.phase.startswith('practice') and self.phase != 'random' else ''))
        text = '목표: ' + self.problem.goal
        if self.phase == 'learn':
            title, description = self.unit.learning_steps[self.step]
            text = title + '\n\n' + description
            reference='선수·실사용 보충' if self.unit.source=='supplement' else self.unit.source+' · PDF 실제 '+', '.join(map(str,self.unit.pages))+'쪽'
            text+='\n\n범위: '+reference+'\n'+self.unit.provenance_note
        if self.problem.prepared_code:
            text += '\n\n미리 준비된 데이터·이름\n' + self.problem.prepared_code
        if self.phase == 'example': text += '\n\n직접 입력할 예시\n' + self.problem.solution
        if self.problem.files: text += '\n\n실습 폴더의 파일: ' + ', '.join(self.problem.files)
        self.instructions.setPlainText(text)
        self.task_tabs.setCurrentIndex(0)
        self.next_button.setText(('다음 소단계' if self.step == 0 else '전체 예시 시작') + ' (F6)' if self.phase == 'learn' else '다음 문제 (F6)')
        self.previous.setVisible(self.phase == 'learn')
        self.previous.setEnabled(not self.busy and self.step > 0)
        self.exit_random.setVisible(self.phase == 'random')
        self.refresh_course()
        self.controls()

    def controls(self):
        for widget in (self.course,self.topics,self.run_button,self.restart,self.hint,self.quiz_button,self.exit_random,self.previous): widget.setEnabled(not self.busy)
        self.previous.setEnabled(not self.busy and self.step>0)
        self.stop_button.setEnabled(self.busy)
        self.random_button.setEnabled(not self.busy and bool(self.progress.data['completed']))
        self.grade_button.setEnabled(not self.busy and self.phase != 'learn' and self.engine.process is not None)
        self.next_button.setEnabled(not self.busy and (self.phase == 'learn' or self.solved))

    def job(self, function, callback):
        if self.busy: return
        self.busy = True
        self.controls()
        self.worker = PythonJob(function)
        self.worker.finished_value.connect(lambda value: callback(value) if not self._close_pending else None)
        self.worker.failed.connect(lambda error: self.output.appendPlainText(error) if not self._close_pending else None)
        def finished():
            self.busy = False
            self.controls()
            if self._close_pending:
                QTimer.singleShot(0, self.close)
        self.worker.finished.connect(finished)
        self.worker.start()

    def start_lab(self):
        if self.busy: return
        if self.engine.process and self.engine.process.poll() is None: return
        problem = self.problem
        self.job(lambda: self.engine.start(problem.initial, problem.files),
                 lambda result: self.output.appendPlainText('새 Python 실습 환경이 준비되었습니다.'))

    def run_code(self):
        if self.busy: return
        code, problem = self.editor.toPlainText(), self.problem
        if not code.strip():
            self.start_lab(); return
        def run():
            if not self.engine.process or self.engine.process.poll() is not None:
                self.engine.start(problem.initial, problem.files)
            result = self.engine.execute(code)
            result['inspection'] = self.engine.inspect(problem.targets, problem.probes)
            return result
        def show(result):
            self.solved = False
            self.output.appendPlainText(f"In [{result['execution']}]\n" + result['output'])
            inspection = result.get('inspection', {})
            if inspection.get('figures'):
                pixmap = QPixmap()
                pixmap.loadFromData(base64.b64decode(inspection['figures'][0]))
                self.figure.setPixmap(pixmap)
                self.output_tabs.setCurrentIndex(1)
            else:
                self.clear_figure()
                self.output_tabs.setCurrentIndex(0)
            self.save()
        self.job(run, show)

    def grade(self):
        if self.busy or self.phase == 'learn': return
        problem = self.problem
        def show(state):
            result = grade_snapshot(state.get('values', {}), problem.checks)
            self.solved = result['passed']
            details = [dict(c, label=c['label'] + ('' if c['passed'] else '\n'+c['detail'])) for c in result['checks']]
            self.feedback.set_results('목표 달성' if self.solved else '미완료 항목을 수정하고 다시 채점하세요.', details)
            self.task_tabs.setCurrentIndex(1)
            if self.solved and self.phase != 'random':
                try: self.progress.passed(self.unit.key, self.variant)
                except OSError as exc: QMessageBox.warning(self, '진도 저장 실패', str(exc))
                self.refresh_course()
        self.job(lambda: self.engine.inspect(problem.targets, problem.probes), show)

    def select_lesson(self, index, initial=False):
        if self.busy: return
        if not initial and self.editor.toPlainText().strip():
            if QMessageBox.question(self, '단원 전환', '학습 진도는 유지합니다. 입력 코드와 임시 실습을 버리고 이동할까요?') != QMessageBox.StandardButton.Yes: return
        self.engine.close()
        self.index, self.variant, self.phase, self.solved = index, 0, 'learn', False
        step = self.progress.data['learning'].get(self.unit.key,0)
        self.step = step if isinstance(step,int) and step in (0,1) else 0
        saved=self.progress.data['positions'].get(self.unit.key,{})
        if isinstance(saved,dict) and saved.get('phase') in ('learn','example','practice1','practice2'):
            self.phase=saved['phase']
            self.variant={'learn':0,'example':0,'practice1':1,'practice2':2}[self.phase]
        self.editor.clear(); self.output.clear()
        self.clear_figure()
        self.random_return = None
        self.render()
        if not initial: self.save()

    def change_topic(self, topic):
        if topic != self.unit.topic: self.select_lesson(next(i for i,u in enumerate(self.units) if u.topic == topic))
        self.refresh_course()

    def clear_figure(self):
        self.figure.clear()
        self.figure.setText('그림을 만들면 여기에 표시됩니다.')

    def previous_step(self):
        if self.busy or self.phase != 'learn' or self.step == 0: return
        self.step -= 1
        self.save(); self.render()

    def advance(self):
        if self.busy: return
        if self.phase == 'learn' and self.step == 0:
            self.step = 1
            self.save(); self.render(); return
        if self.phase != 'learn' and not self.solved: return
        if self.phase in ('practice2','random'):
            if self.phase == 'random': self.pick_random(); return
            if self.index + 1 < len(self.units):
                self.editor.clear()
                self.select_lesson(self.index + 1)
            return
        self.engine.close()
        self.phase = {'learn':'example','example':'practice1','practice1':'practice2'}[self.phase]
        self.variant = {'example':0,'practice1':1,'practice2':2}[self.phase]
        self.solved = False
        self.editor.setPlainText(self.problem.starter)
        self.output.clear()
        self.clear_figure()
        self.save(); self.render(); self.start_lab()

    def restart_problem(self):
        if self.busy: return
        if QMessageBox.question(self,'실습 초기화','입력 코드는 남기고 Python 변수·파일만 처음 상태로 돌릴까요?') != QMessageBox.StandardButton.Yes: return
        self.engine.close()
        self.solved = False
        self.start_lab()

    def show_hint(self):
        if not self.busy: QMessageBox.information(self,'힌트',self.unit.pitfall + '\n\n' + self.unit.syntax)

    def start_random(self):
        if self.busy or not self.progress.data['completed']: return
        if self.phase != 'random': self.random_return = (self.index,self.phase,self.step,self.variant)
        self.pick_random()

    def pick_random(self):
        available = [i for i,u in enumerate(self.units) if u.key in self.progress.data['completed']]
        if not available: return
        self.engine.close()
        self.index = random.choice(available)
        self.phase, self.variant, self.solved = 'random', random.choice((1,2)), False
        self.editor.clear(); self.output.clear()
        self.clear_figure()
        self.render(); self.start_lab()

    def stop_random(self):
        if self.busy or self.phase != 'random': return
        self.engine.close()
        self.index,self.phase,self.step,self.variant = self.random_return or (0,'learn',0,0)
        self.random_return = None
        self.solved = False
        self.editor.clear(); self.output.clear()
        self.clear_figure()
        self.save(); self.render()

    def show_quiz(self):
        from python_quiz_dialog import QuizDialog
        host=self.window()
        handler=getattr(host,'open_related_practice',None)
        if handler is None:
            handler=lambda target: ({'python':self.open_practice,'notebook':self.open_notebook_practice}[target['course']](
                target['unit_key'],target['problem_index']) if target['course'] in ('python','notebook') else False)
        try:dialog = QuizDialog(self.progress, self, practice_handler=handler)
        except (OSError,ValueError,KeyError,TypeError) as error:
            QMessageBox.warning(self,'퀴즈 자료를 열 수 없습니다',str(error));return
        dialog.exec()

    def open_notebook_practice(self,key,variant):
        if self.busy or self._close_pending:return False
        from notebook_teaching.course import lessons as notebook_lessons
        if key not in {u['key'] for u in notebook_lessons()} or type(variant) is not int or variant not in (0,1,2):return False
        previous=self.python_stack.currentIndex()
        self.python_sections.setCurrentIndex(1)
        opened=self.notebook.open_practice(key,variant)
        if not opened:self.python_sections.setCurrentIndex(previous)
        return opened

    def open_practice(self,key,variant):
        if self.busy:return False
        if self.python_stack.currentIndex()!=0:
            self.python_sections.setCurrentIndex(0)
        index=next((i for i,u in enumerate(self.units) if u.key==key),None)
        if index is None or type(variant) is not int or variant not in (0,1,2):return False
        phase=('example','practice1','practice2')[variant]
        if (self.index,self.phase,self.variant)==(index,phase,variant):return True
        if self.editor.toPlainText().strip() or self.output.toPlainText() or self.engine.process is not None:
            if QMessageBox.question(self,'관련 실습으로 이동',
                    '현재 Python 입력 코드와 임시 실행 상태를 초기화하고 관련 실습으로 이동할까요? 학습 완료 기록은 유지됩니다.',
                    QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No,QMessageBox.StandardButton.No)!=QMessageBox.StandardButton.Yes:
                return False
        self.save();self.select_lesson(index,initial=True)
        self.phase,self.variant,self.step=phase,variant,0
        self.solved=False;self.save();self.render()
        return True

    def closeEvent(self, event):
        if self.study_closed:
            event.accept()
            return
        self._close_pending = True
        self.engine.cancel()
        if self.notebook and not self.notebook.study_closed:
            if not self._notebook_close_started:
                self._notebook_close_started=True
                self.notebook.close()
            event.ignore()
            return
        # A QThread can already have stopped while its queued finished signal
        # has not reached the GUI. Keep the page alive until that callback has
        # cleared busy; otherwise it may touch a deleted editor/status widget.
        if self.busy or (self.worker and self.worker.isRunning()):
            event.ignore()
            self.statusBar().showMessage('Python 작업을 중단한 뒤 종료합니다…')
            return
        try:
            self.engine.close()
        except Exception as error:
            event.ignore()
            self._close_pending = False
            self.shutdown_failed.emit(str(error))
            return
        self.save()
        self.finish_shutdown(event)
