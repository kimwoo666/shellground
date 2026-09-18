"""Embedded native notebook room. Widgets are a frontend to real ipykernel."""
import html
from pathlib import Path
import re
import threading
import uuid
from PySide6.QtCore import Qt, Signal, QThread, QTimer, QEvent, QStandardPaths
from PySide6.QtGui import QAction, QFont
from PySide6.QtWidgets import (QWidget,QVBoxLayout,QHBoxLayout,QLabel,QPushButton,QComboBox,
    QListWidget,QSplitter,QTabWidget,QPlainTextEdit,QScrollArea,QFrame,QTextBrowser,QLineEdit,QMessageBox)
from app_settings import load_settings,theme_palette
from feedback_panel import FeedbackPanel
from python_editor import PythonEditor
from python_teaching.progress import PythonProgress
from notebook_teaching.course import lessons,ENV_GUIDE
from notebook_teaching.engine import NotebookEngine
from study_page import StudyPage
from terminal_widget import TerminalWidget,TerminalReader


class NotebookJob(QThread):
    value=Signal(object)
    error=Signal(str)
    status=Signal(str)
    def __init__(self, operation):
        super().__init__();self.operation=operation
    def run(self):
        try:self.value.emit(self.operation(self.status.emit))
        except Exception as error:self.error.emit(str(error))


class Cell(QFrame):
    selected=Signal(object)
    execute=Signal(object)
    changed=Signal()
    def __init__(self, data, mono):
        super().__init__();self.key=data['id'];self.kind=data['type'];self.last=None
        self.setFrameShape(QFrame.Shape.StyledPanel)
        layout=QVBoxLayout(self);layout.setContentsMargins(8,5,8,5)
        self.label=QLabel('Markdown · 설명' if self.kind=='markdown' else 'In [ ]')
        layout.addWidget(self.label)
        self.editor=PythonEditor();self.editor.setFont(QFont(mono,11));self.editor.setPlainText(data['source'])
        self.editor.installEventFilter(self);self.editor.execute_requested.connect(lambda:self.execute.emit(self))
        self.editor.setStyleSheet('QPlainTextEdit {background:#101714;color:#dbe9df;}')
        layout.addWidget(self.editor)
        self.output=QTextBrowser();self.output.setOpenExternalLinks(False);self.output.hide();layout.addWidget(self.output)
        self.preview=QTextBrowser();self.preview.hide();layout.addWidget(self.preview)
        self.editor.textChanged.connect(self.edited);self.fit()

    def eventFilter(self, watched, event):
        if event.type()==QEvent.Type.FocusIn:self.selected.emit(self)
        return super().eventFilter(watched,event)

    def data(self):return dict(id=self.key,type=self.kind,source=self.editor.toPlainText())

    def fit(self):
        self.editor.setFixedHeight(min(180,max(64,self.editor.blockCount()*21+18)))

    def edited(self):
        self.fit()
        if self.last and self.last[0]!=self.editor.toPlainText():self.label.setText('편집됨 · 아래 출력은 이전 실행 결과')
        self.changed.emit()

    def show_result(self,result):
        self.last=(self.editor.toPlainText(),result['generation'])
        self.label.setText('In ['+str(result['execution_count'])+']'+(' · 오류' if not result['ok'] else ''))
        blocks=[]
        for message in result['messages']:
            typ,data=message['type'],message['content']
            if typ=='clear_output':blocks=[]
            elif typ=='stream':blocks.append('<pre>'+html.escape(data['text'])+'</pre>')
            elif typ=='error':
                text='\n'.join(data.get('traceback',[])) or data.get('ename','')+': '+data.get('evalue','')
                text=re.sub(r'\x1b\[[0-9;]*[A-Za-z]','',text)
                blocks.append('<pre>'+html.escape(text)+'</pre>')
            elif typ in ('execute_result','display_data'):
                mime=data.get('data',{})
                if 'image/png' in mime:
                    blocks.append('<img width="520" src="data:image/png;base64,'+mime['image/png']+'">')
                elif 'text/plain' in mime:blocks.append('<pre>'+html.escape(mime['text/plain'])+'</pre>')
        if result.get('truncated'):blocks.append('<p>긴 출력은 표시 한도를 넘어서 일부 생략했습니다.</p>')
        self.output.setHtml(''.join(blocks));self.output.setVisible(bool(blocks))
        self.output.setFixedHeight(155 if len(''.join(blocks))>300 else 70)

    def stale(self):
        if self.last:self.label.setText('이전 커널의 출력 · 현재 값이 아님')


class NotebookWindow(StudyPage):
    def __init__(self,ui_family,mono_family,progress_path=None,engine=None):
        super().__init__();self.setWindowTitle('Shellground — Python 노트북')
        self.units=lessons();self.engine=engine or NotebookEngine();self.mono=mono_family
        self.busy=False;self.closing=False;self.closed=False;self.worker=None;self.interrupter=None
        self.readers=[];self.reader=None;self.cells=[];self.active_cell=None;self.identity=None
        self.prepared=False;self.solved=False;self.stop_event=threading.Event()
        path=Path(progress_path or Path(QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppDataLocation))/'notebook-progress-v1.json')
        self.progress=PythonProgress(path);settings=load_settings(path.with_name('settings-v1.json'))
        self.setPalette(theme_palette(settings.theme))
        root=QWidget();self.setCentralWidget(root);outer=QVBoxLayout(root)
        split=QSplitter(Qt.Orientation.Horizontal);outer.addWidget(split,1)
        self.course=QListWidget();self.course.setWordWrap(True);split.addWidget(self.course)
        self.course.itemClicked.connect(lambda item:self.select(item.data(Qt.ItemDataRole.UserRole)))
        right=QWidget();body=QVBoxLayout(right);split.addWidget(right);split.setSizes([215,990])
        self.heading=QLabel();self.heading.setFont(QFont(ui_family,13,QFont.Weight.Bold));body.addWidget(self.heading)
        vertical=QSplitter(Qt.Orientation.Vertical);body.addWidget(vertical,1)
        self.task_tabs=QTabWidget();self.instructions=QPlainTextEdit();self.instructions.setReadOnly(True)
        self.feedback=FeedbackPanel();self.feedback.set_dark_theme(settings.theme=='dark')
        self.task_tabs.addTab(self.instructions,'문제·설명');self.task_tabs.addTab(self.feedback,'채점 결과')
        self.grade_details=QPlainTextEdit();self.grade_details.setReadOnly(True)
        self.task_tabs.addTab(self.grade_details,'채점 상세')
        vertical.addWidget(self.task_tabs)
        workspace=QWidget();work=QVBoxLayout(workspace);work.setContentsMargins(0,0,0,0);vertical.addWidget(workspace)
        row=QHBoxLayout();work.addLayout(row);row.addWidget(QLabel('커널'))
        self.kernels=QComboBox();self.kernels.setMinimumContentsLength(18);row.addWidget(self.kernels,1)
        self.refresh_button=QPushButton('목록 새로 고침');self.refresh_button.clicked.connect(self.refresh_kernels);row.addWidget(self.refresh_button)
        self.kernel_restart=QPushButton('커널 재시작');self.kernel_restart.clicked.connect(self.restart_kernel);row.addWidget(self.kernel_restart)
        self.kernels.activated.connect(self.select_kernel)
        self.kernel_status=QLabel('아직 실습을 열지 않았습니다.');self.kernel_status.setWordWrap(True);work.addWidget(self.kernel_status)
        self.work_tabs=QTabWidget();work.addWidget(self.work_tabs,1)
        document=QWidget();document_layout=QVBoxLayout(document);document_layout.setContentsMargins(0,0,0,0)
        tools=QHBoxLayout();document_layout.addLayout(tools)
        self.cell_tools=[]
        for title,callback in [('코드 +',lambda:self.add_cell('code')),('설명 +',lambda:self.add_cell('markdown')),
                               ('↑',lambda:self.move_cell(-1)),('↓',lambda:self.move_cell(1)),('셀 삭제',self.remove_cell),
                               ('선택 실행 ⇧Enter',self.run_selected),('전체 실행',self.run_all)]:
            button=QPushButton(title);button.clicked.connect(callback);tools.addWidget(button);self.cell_tools.append(button)
        self.stop_button=QPushButton('중단');self.stop_button.clicked.connect(self.interrupt);tools.addWidget(self.stop_button)
        self.scroll=QScrollArea();self.scroll.setWidgetResizable(True);self.cell_container=QWidget()
        self.cell_layout=QVBoxLayout(self.cell_container);self.cell_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.scroll.setWidget(self.cell_container);document_layout.addWidget(self.scroll,1)
        save_row=QHBoxLayout();document_layout.addLayout(save_row)
        self.filename=QLineEdit('report.ipynb');save_row.addWidget(self.filename)
        self.save_button=QPushButton('작업 폴더에 문서 저장');self.save_button.clicked.connect(self.save_document);save_row.addWidget(self.save_button)
        self.work_tabs.addTab(document,'노트북')
        self.terminal=TerminalWidget(mono_family);self.terminal.setMinimumHeight(160);self.terminal.apply_settings(settings)
        self.terminal.input_bytes.connect(lambda data:self.engine.send(data) if not self.busy else None)
        self.terminal.resized.connect(self.engine.resize)
        self.work_tabs.addTab(self.terminal,'Bash · 환경/커널 등록')
        vertical.setSizes([225,535]);self.task_splitter=vertical
        self.status=QLabel('실습은 앱 전용 환경에서 실행합니다. 진행 위치·완료만 자동 저장합니다.');self.status.setWordWrap(True);body.addWidget(self.status)
        buttons=QHBoxLayout();body.addLayout(buttons)
        self.previous=QPushButton('이전 소단계');self.previous.clicked.connect(self.previous_step)
        self.hint=QPushButton('힌트 (F1)');self.hint.clicked.connect(self.show_hint)
        self.reset_button=QPushButton('실습 초기화 (F2)');self.reset_button.clicked.connect(self.reset_problem)
        self.start_button=QPushButton('실습 열기 (F4)');self.start_button.clicked.connect(self.start)
        self.grade_button=QPushButton('채점 (F5)');self.grade_button.clicked.connect(self.grade)
        self.next_button=QPushButton('다음 (F6)');self.next_button.clicked.connect(self.advance)
        for button in (self.previous,self.hint,self.reset_button,self.start_button,self.grade_button,self.next_button):buttons.addWidget(button)
        for key,callback in [('F1',self.show_hint),('F2',self.reset_problem),('F4',self.start),('F5',self.grade),('F6',self.advance)]:
            action=QAction(self);action.setShortcut(key);action.setShortcutContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
            action.setAutoRepeat(False);action.triggered.connect(callback);self.addAction(action)
        resume=self.progress.data.get('resume',{})
        self.index=next((i for i,u in enumerate(self.units) if u['key']==resume.get('unit')),0)
        self.restore(resume);self.load_document(self.problem['cells']);self.render()

    @property
    def unit(self):return self.units[self.index]
    @property
    def problem(self):return self.unit['problems'][self.variant]

    def restore(self,position):
        self.phase=position.get('phase','learn')
        if self.phase not in ('learn','example','practice1','practice2'):self.phase='learn'
        self.variant={'learn':0,'example':0,'practice1':1,'practice2':2}[self.phase]
        step=position.get('step',0);self.step=min(max(step if type(step)is int else 0,0),len(self.unit['steps'])-1)

    def save(self):
        try:self.progress.resume(self.unit['key'],self.phase,self.step)
        except OSError as error:self.status.setText('진도 저장 실패: '+str(error))

    def render(self):
        testing=self.phase.startswith('practice');self.course.clear()
        for index,unit in enumerate(self.units):
            mark='완료' if unit['key'] in self.progress.data['completed'] else '미완료'
            self.course.addItem(('◆ ' if unit['key'].startswith('review_') else f'{index+1:02d} ')+f'[{mark}] '+('평가 중 내용 숨김' if testing else unit['title']))
            self.course.item(index).setData(Qt.ItemDataRole.UserRole,index)
        self.course.setCurrentRow(self.index)
        phase={'learn':f'배우기 {self.step+1}/{len(self.unit["steps"])}','example':'예시','practice1':'활용 1','practice2':'활용 2'}[self.phase]
        self.heading.setText('노트북 · '+phase+('' if testing else ' · '+self.unit['title']))
        if self.phase=='learn':
            title,description=self.unit['steps'][self.step]
            text=title+'\n\n'+description+'\n\n범위: '+self.unit['source']
        else:
            text='목표: '+self.problem['goal']
            if self.phase=='example':
                text+='\n\n예시 순서\n'
                if self.problem.get('commands'):text+='Bash:\n'+'\n'.join(self.problem['commands'])+'\n'
                text+='커널 선택: '+self.problem.get('registration','sg-'+self.problem['target'])
                if self.problem.get('restart'):text+=' → 커널 재시작'
                text+='\n코드 셀:\n'+'\n\n'.join(c['source'] for c in self.problem['solution'] if c['type']=='code')
                if self.problem.get('save'):text+='\nMarkdown 설명을 작성하고 report.ipynb로 저장합니다.'
        text+='\n\n환경 안내\n'+ENV_GUIDE
        if self.problem.get('both_numpy'):text+='\n이번 문제는 예외: basic에도 NumPy 2.3.5가 준비되어 있습니다.'
        if self.phase=='learn' and self.step>0:text+='\n재개 시 코드는 저장되지 않습니다. 이전 소단계 버튼으로 준비 순서를 다시 볼 수 있습니다.'
        self.instructions.setPlainText(text);self.task_tabs.setCurrentIndex(0);self.controls()

    def controls(self):
        ready=self.prepared and not self.busy
        for widget in (self.course,self.hint,self.reset_button,self.previous):widget.setEnabled(not self.busy)
        for widget in (self.kernels,self.refresh_button,self.kernel_restart,self.save_button):widget.setEnabled(ready)
        for widget in self.cell_tools:widget.setEnabled(not self.busy)
        for cell in self.cells:cell.editor.setReadOnly(self.busy)
        self.start_button.setEnabled(not self.busy and not self.prepared)
        self.grade_button.setEnabled(ready and self.phase!='learn')
        self.next_button.setEnabled(not self.busy and (self.phase=='learn' or self.solved))
        self.previous.setVisible(self.phase=='learn');self.previous.setEnabled(not self.busy and self.step>0)
        self.stop_button.setEnabled(self.busy and self.engine.notebook_ready and not self.closing)

    def job(self,operation,callback,closing=False):
        if self.busy:return
        self.busy=True;self.controls();worker=NotebookJob(operation);self.worker=worker;outcome={}
        worker.value.connect(lambda value:outcome.update(value=value));worker.error.connect(lambda error:outcome.update(error=error))
        worker.status.connect(self.status.setText)
        def finished():
            self.busy=False
            if 'error' in outcome:
                self.status.setText('실행 환경 오류: '+outcome['error'])
                if closing:self.closing=False;self.shutdown_failed.emit(outcome['error'])
            elif not self.closing or closing:callback(outcome.get('value'))
            self.controls()
            if self.closing:QTimer.singleShot(0,self.close)
        worker.finished.connect(finished);worker.start()

    def document(self):return [cell.data() for cell in self.cells]

    def load_document(self,data):
        for cell in self.cells:
            self.cell_layout.removeWidget(cell)
            # deleteLater is deferred until the next outer event loop. Hide
            # immediately so old editors cannot paint over the new document.
            cell.hide();cell.deleteLater()
        self.cells=[];self.active_cell=None
        for entry in data:self.insert_cell(entry)
        self.choose_cell(next((c for c in self.cells if c.kind=='code'),self.cells[0]))

    def insert_cell(self,data):
        cell=Cell(data,self.mono);self.cells.append(cell);self.cell_layout.addWidget(cell)
        cell.selected.connect(self.choose_cell);cell.execute.connect(self.run_cell);cell.changed.connect(self.unsolved)
        return cell

    def unsolved(self):self.solved=False;self.controls()

    def choose_cell(self,cell):
        self.active_cell=cell
        for item in self.cells:item.setLineWidth(2 if item is cell else 1)

    def add_cell(self,kind):
        if self.busy or len(self.cells)>=16:return
        cell=self.insert_cell(dict(id=uuid.uuid4().hex,type=kind,source=''))
        self.choose_cell(cell);cell.editor.setFocus();self.unsolved()

    def move_cell(self,direction):
        if self.busy or self.active_cell not in self.cells:return
        old=self.cells.index(self.active_cell);new=old+direction
        if 0<=new<len(self.cells):
            self.cells.pop(old);self.cells.insert(new,self.active_cell)
            self.cell_layout.removeWidget(self.active_cell);self.cell_layout.insertWidget(new,self.active_cell);self.unsolved()

    def remove_cell(self):
        if self.busy or len(self.cells)<=1 or self.active_cell not in self.cells:return
        if QMessageBox.question(self,'셀 삭제','선택한 셀의 코드·설명과 출력을 삭제할까요?')!=QMessageBox.StandardButton.Yes:return
        cell=self.active_cell;self.cells.remove(cell);self.cell_layout.removeWidget(cell);cell.deleteLater()
        self.choose_cell(self.cells[0]);self.unsolved()

    def disconnect_bash(self):
        self.terminal.connected=False
        for reader in self.readers:reader.stop_requested.set()
        if self.engine.bridge:self.engine.bridge.close()
        self.reader=None;self.terminal.reset()

    def start(self,after=None):
        if self.busy:return
        if self.prepared:
            if callable(after):after()
            return
        self.disconnect_bash();problem=self.problem
        def operation(status):
            baseline=self.engine.start_problem(problem,status)
            return baseline,self.engine.open_bash()
        def ready(value):
            baseline,bridge=value;self.prepared=True;self.update_identity(baseline['identity'])
            reader=TerminalReader(bridge);self.reader=reader;self.readers.append(reader);self.terminal.connected=True
            def receive(data):
                try:
                    if reader is self.reader:self.terminal.feed(data)
                finally:reader.pending.release()
            def ended(message):
                if reader is self.reader and not self.closing:self.terminal.connected=False;self.status.setText(message)
            reader.output.connect(receive);reader.ended.connect(ended);reader.start()
            self.engine.resize(self.terminal.screen.lines,self.terminal.screen.columns)
            self.status.setText('준비 완료 · 설명을 보며 셀과 Bash를 직접 실행할 수 있습니다.')
            if callable(after):QTimer.singleShot(0,after)
        self.job(operation,ready)

    def update_identity(self,identity):
        old=self.identity;self.identity=identity
        if old and old['generation']!=identity['generation']:
            for cell in self.cells:cell.stale()
        self.kernels.blockSignals(True);self.kernels.clear()
        for item in identity['kernels']:
            self.kernels.addItem(item['display_name']+' · '+item['name'],item['name'])
            self.kernels.setItemData(self.kernels.count()-1,item['executable'],Qt.ItemDataRole.ToolTipRole)
        self.kernels.setCurrentIndex(self.kernels.findData(identity['kernel']));self.kernels.blockSignals(False)
        self.kernel_status.setText(identity['values']['executable']+' · Python '+identity['values']['version'])

    def refresh_kernels(self):
        if not self.busy and self.prepared:self.job(lambda _:self.engine.perform('identity'),self.update_identity)

    def select_kernel(self,index):
        if self.busy or not self.prepared:return
        name=self.kernels.itemData(index)
        if name==self.identity['kernel']:return
        if QMessageBox.question(self,'커널 전환','현재 커널을 닫고 선택한 Python을 시작합니다. 셀 코드는 남지만 변수는 초기화됩니다. 전환할까요?')!=QMessageBox.StandardButton.Yes:
            self.update_identity(self.identity);return
        self.solved=False;self.job(lambda _:self.engine.perform('select',name=name),self.update_identity)

    def restart_kernel(self,confirmed=False):
        if self.busy or not self.prepared:return
        if not confirmed and QMessageBox.question(self,'커널 재시작','코드·설명·파일은 남기고 현재 커널의 변수를 모두 초기화할까요?')!=QMessageBox.StandardButton.Yes:return
        self.solved=False;self.job(lambda _:self.engine.perform('restart'),self.update_identity)

    def run_selected(self):
        if self.active_cell:self.run_cell(self.active_cell)

    def run_cell(self,cell):
        if self.busy:return
        if cell.kind=='markdown':
            cell.preview.setMarkdown(cell.editor.toPlainText());cell.preview.setFixedHeight(90);cell.preview.show();return
        if not self.prepared:self.start(lambda:self.run_cell(cell));return
        code=cell.editor.toPlainText();self.solved=False
        self.job(lambda _:self.engine.perform('execute',cell_id=cell.key,code=code),cell.show_result)

    def run_all(self):
        if self.busy:return
        if not self.prepared:self.start(self.run_all);return
        document=self.document();self.stop_event.clear();self.solved=False
        def execute(status):
            results=[]
            for cell in document:
                if self.stop_event.is_set():break
                if cell['type']!='code':continue
                status('문서 실행 중 · '+cell['id'])
                result=self.engine.perform('execute',cell_id=cell['id'],code=cell['source']);results.append((cell['id'],result))
                if not result['ok']:break
            return results
        def shown(results):
            for key,result in results:
                next(c for c in self.cells if c.key==key).show_result(result)
            self.status.setText('문서 실행 완료' if results and results[-1][1]['ok'] else '실행 중단 또는 오류 · 셀을 고친 뒤 계속 실행할 수 있습니다.')
        self.job(execute,shown)

    def interrupt(self):
        if not self.busy or self.closing or (self.interrupter and self.interrupter.isRunning()):return
        self.stop_event.set();self.interrupter=NotebookJob(lambda _:self.engine.interrupt())
        self.interrupter.error.connect(lambda text:self.status.setText('중단 요청: '+text));self.interrupter.start()

    def save_document(self):
        if self.busy or not self.prepared:return
        document=self.document();filename=self.filename.text().strip()
        self.job(lambda _:self.engine.perform('save',filename=filename,cells=document),
                 lambda value:self.status.setText('임시 작업 폴더에 저장: '+value['path']))

    def grade(self):
        if self.busy or not self.prepared or self.phase=='learn':return
        self.status.setText('현재 값 확인'+(' · 별도 새 커널에서 문서 재현 검사(현재 커널 유지)' if self.problem.get('replay') else ''))
        problem,document=self.problem,self.document()
        def shown(result):
            self.solved=result['passed'];self.update_identity(result['identity'])
            self.feedback.set_results('목표 달성' if self.solved else '미완료 항목을 수정하세요. 이유는 「채점 상세」에서 확인할 수 있습니다.',result['checks'])
            self.grade_details.setPlainText('\n\n'.join(('통과: ' if c['passed'] else '미완료: ')+c['label']+'\n'+c['detail'] for c in result['checks']))
            self.task_tabs.setCurrentIndex(1)
            QTimer.singleShot(0,self.fit_feedback)
            if self.solved:
                try:self.progress.passed(self.unit['key'],self.variant)
                except OSError as error:self.status.setText('진도 저장 실패: '+str(error))
            self.save()
        self.job(lambda _:self.engine.grade_problem(problem,document),shown)

    def fit_feedback(self):
        # Keep the compact grading checklist visible at ordinary desktop
        # sizes. Very small windows still retain a usable code/terminal pane.
        sizes=self.task_splitter.sizes();total=sum(sizes)
        desired=int(self.feedback.document().size().height())+self.task_tabs.tabBar().height()+12
        upper=min(max(sizes[0],desired),max(sizes[0],total-230))
        if upper>sizes[0]:self.task_splitter.setSizes([upper,total-upper])

    def show_hint(self):
        if not self.busy:QMessageBox.information(self,'힌트',self.unit['hint'])

    def select(self,index):
        if self.busy:return
        if self.prepared and not self.solved and QMessageBox.question(self,'단원 이동','현재 임시 실습을 닫고 이동할까요? 완료 진도는 유지됩니다.')!=QMessageBox.StandardButton.Yes:
            self.course.setCurrentRow(self.index);return
        self.save();self.disconnect_bash();self.index=index;self.prepared=False;self.solved=False
        self.restore(self.progress.data['positions'].get(self.unit['key'],{}))
        self.load_document(self.problem['cells']);self.save();self.render()

    def open_practice(self,key,variant):
        if self.busy or self.closing:return False
        index=next((i for i,u in enumerate(self.units) if u['key']==key),None)
        if index is None or type(variant) is not int or variant not in (0,1,2):return False
        phase=('example','practice1','practice2')[variant]
        if (self.index,self.phase,self.variant)==(index,phase,variant):return True
        if self.prepared or self.document()!=self.problem['cells']:
            if QMessageBox.question(self,'관련 노트북 실습으로 이동',
                    '현재 노트북의 입력·임시 실행 상태를 새 실습으로 바꿀까요? 완료 기록은 유지됩니다.',
                    QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No,QMessageBox.StandardButton.No)!=QMessageBox.StandardButton.Yes:
                return False
        self.save();self.disconnect_bash();self.index=index;self.phase=phase;self.variant=variant;self.step=0
        self.prepared=False;self.solved=False;self.load_document(self.problem['cells']);self.save();self.render()
        return True

    def previous_step(self):
        if not self.busy and self.phase=='learn' and self.step>0:self.step-=1;self.save();self.render()

    def advance(self):
        if self.busy:return
        if self.phase=='learn' and self.step+1<len(self.unit['steps']):self.step+=1;self.save();self.render();return
        if self.phase!='learn' and not self.solved:return
        if self.phase=='practice2':
            if self.index+1<len(self.units):self.select(self.index+1)
            return
        self.disconnect_bash();self.phase={'learn':'example','example':'practice1','practice1':'practice2'}[self.phase]
        self.variant={'example':0,'practice1':1,'practice2':2}[self.phase]
        self.prepared=False;self.solved=False;self.load_document(self.problem['cells']);self.save();self.render();self.start()

    def reset_problem(self):
        if self.busy:return
        if QMessageBox.question(self,'실습 전체 초기화','입력 셀은 남기고 이 노트북 실습의 환경·등록·임시 파일을 초기화할까요? 커널 재시작보다 오래 걸립니다.')!=QMessageBox.StandardButton.Yes:return
        self.disconnect_bash();self.prepared=False;self.solved=False
        self.job(lambda _:self.engine.close(),lambda _:QTimer.singleShot(0,self.start))

    def closeEvent(self,event):
        if self.closed:self.finish_shutdown(event);return
        event.ignore();self.closing=True;self.save();self.stop_event.set();self.disconnect_bash()
        if self.busy:self.engine.cancel_pending();return
        def cleanup(_):
            self.engine.close()
            for reader in self.readers:
                if not reader.wait(2000):raise RuntimeError('노트북 터미널 종료 대기 실패')
            if self.interrupter and not self.interrupter.wait(6000):raise RuntimeError('커널 중단 요청 종료 대기 실패')
        def done(_):self.closed=True
        self.job(cleanup,done,closing=True)
