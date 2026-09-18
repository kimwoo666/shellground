"""Native Conda lessons around the real Linux terminal and outcome grader."""
from pathlib import Path
import random
import platform
from PySide6.QtCore import Qt,QStandardPaths,QTimer
from PySide6.QtGui import QAction,QFont
from PySide6.QtWidgets import (QMainWindow,QWidget,QVBoxLayout,QHBoxLayout,QLabel,QPushButton,
    QListWidget,QSplitter,QTabWidget,QPlainTextEdit,QFormLayout,QLineEdit,QComboBox,QMessageBox,QDialog,QDialogButtonBox)
from conda_teaching.engine import CondaEngine,course
from conda_teaching.learning_steps import STEPS
from conda_teaching import setup_course
from python_teaching.progress import PythonProgress
from python_app import PythonJob
from terminal_widget import TerminalWidget,TerminalReader
from feedback_panel import FeedbackPanel
from app_settings import load_settings,theme_palette
from study_page import StudyPage


class CondaWindow(StudyPage):
    def __init__(self,ui_family,mono_family,progress_path=None,engine=None):
        super().__init__();self.setWindowTitle('Shellground — Conda 환경 관리');self.resize(1220,880)
        self.spec=course();self.units=self.spec['units'];self.engine=engine or CondaEngine()
        self.index=0;self.phase='learn';self.step=0;self.variant=0;self.solved=False;self.busy=False
        self.setup_mode=False;self.setup_ready=None
        self.worker=None;self.readers=[];self.reader=None;self.closing=False;self.closed=False;self.random_return=None
        path=progress_path or Path(QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppDataLocation))/'conda-progress-v1.json'
        self.progress=PythonProgress(path);settings=load_settings(Path(path).with_name('settings-v1.json'))
        self.setPalette(theme_palette(settings.theme))
        root=QWidget();self.setCentralWidget(root);outer=QVBoxLayout(root)
        self.heading=QLabel('SHELLGROUND · Conda');self.heading.setFont(QFont(ui_family,14,QFont.Weight.Bold));outer.addWidget(self.heading)
        self.status=QLabel('Conda 실습은 전용 Linux guest에서 실행 · 아직 실습을 열지 않았습니다.');self.status.setWordWrap(True)
        status_row=QHBoxLayout();status_row.addWidget(self.status,1)
        self.full_description=QPushButton('전체 설명 (F3)');self.full_description.clicked.connect(self.show_description);status_row.addWidget(self.full_description)
        self.preparation_button=QPushButton('이전 소단계 준비 보기');self.preparation_button.clicked.connect(self.show_preparation);status_row.addWidget(self.preparation_button)
        runtime_info=QPushButton('실행 환경');runtime_info.clicked.connect(self.show_runtime);status_row.addWidget(runtime_info);outer.addLayout(status_row)
        self.preparation_notice=QLabel('학습 위치는 저장되지만 실습 환경은 재시작 시 초기화됩니다. 중간부터 다시 열었다면 「이전 소단계 준비 보기」를 확인하세요.')
        self.preparation_notice.setWordWrap(True);outer.addWidget(self.preparation_notice)
        split=QSplitter(Qt.Orientation.Horizontal);outer.addWidget(split,1)
        left=QWidget();nav=QVBoxLayout(left);self.list=QListWidget();self.list.setWordWrap(True)
        self.setup_button=QPushButton('설치 준비·실습');self.setup_button.clicked.connect(self.open_setup);nav.addWidget(self.setup_button)
        self.license_button=QPushButton('설치 파일·라이선스');self.license_button.clicked.connect(self.show_installer);nav.addWidget(self.license_button)
        self.list.itemClicked.connect(lambda item:self.select(item.data(Qt.ItemDataRole.UserRole)))
        nav.addWidget(self.list,1);self.random_button=QPushButton('배운 범위 올랜덤');self.random_button.clicked.connect(self.start_random);nav.addWidget(self.random_button)
        self.return_button=QPushButton('올랜덤 종료 · 이전 학습');self.return_button.clicked.connect(self.stop_random);nav.addWidget(self.return_button);split.addWidget(left)
        right=QWidget();body=QVBoxLayout(right);split.addWidget(right);split.setSizes([245,965])
        work=QSplitter(Qt.Orientation.Vertical);body.addWidget(work,1)
        self.tabs=QTabWidget();self.instructions=QPlainTextEdit();self.instructions.setReadOnly(True)
        self.feedback=FeedbackPanel();self.feedback.set_dark_theme(settings.theme=='dark')
        self.tabs.addTab(self.instructions,'문제·설명');self.tabs.addTab(self.feedback,'채점 결과');work.addWidget(self.tabs)
        files=QWidget();file_layout=QVBoxLayout(files);file_row=QHBoxLayout();file_layout.addLayout(file_row)
        self.file_picker=QComboBox();self.file_picker.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self.file_picker.setMinimumContentsLength(20);file_row.addWidget(self.file_picker,1)
        self.file_refresh=QPushButton('새로 고침');self.file_refresh.clicked.connect(self.refresh_files);file_row.addWidget(self.file_refresh)
        self.file_notice=QLabel('실습 폴더의 파일을 읽기 전용으로 확인합니다.');self.file_notice.setWordWrap(True);file_layout.addWidget(self.file_notice)
        self.file_text=QPlainTextEdit();self.file_text.setReadOnly(True);self.file_text.setFont(QFont(mono_family,11));file_layout.addWidget(self.file_text,1)
        self.tabs.addTab(files,'실습 파일')
        self.file_picker.activated.connect(self.read_file)
        self.tabs.currentChanged.connect(lambda index:self.refresh_files() if index==2 else None)
        self.answer_box=QWidget();self.answer_layout=QFormLayout(self.answer_box);body.addWidget(self.answer_box);self.answers={}
        self.terminal=TerminalWidget(mono_family);self.terminal.apply_settings(settings);work.addWidget(self.terminal);work.setSizes([285,465])
        self.terminal.input_bytes.connect(lambda data:self.engine.send(data) if not self.busy else None)
        self.terminal.resized.connect(self.engine.resize)
        row=QHBoxLayout();body.addLayout(row)
        self.previous=QPushButton('이전 소단계');self.previous.clicked.connect(self.previous_step)
        self.hint=QPushButton('힌트 (F1)');self.hint.clicked.connect(lambda:self.feedback_hint())
        self.restart=QPushButton('다시 시작 (F2)');self.restart.clicked.connect(self.start)
        self.try_button=QPushButton('설명 보며 실습 (F4)');self.try_button.clicked.connect(self.try_lab)
        self.grade_button=QPushButton('채점 (F5)');self.grade_button.clicked.connect(self.grade)
        self.next_button=QPushButton('다음 (F6)');self.next_button.clicked.connect(self.advance)
        for button in (self.previous,self.hint,self.restart,self.try_button,self.grade_button,self.next_button):row.addWidget(button)
        for key,call in [('F1',self.feedback_hint),('F2',self.start),('F3',self.show_description),('F4',self.try_lab),('F5',self.grade),('F6',self.advance)]:
            action=QAction(self);action.setShortcut(key);action.setAutoRepeat(False);action.triggered.connect(call);self.addAction(action)
        resume=self.progress.data.get('resume',{});self.index=next((i for i,u in enumerate(self.units) if u['key']==resume.get('unit')),0)
        if resume.get('unit')==setup_course.KEY:
            self.setup_mode=True
            self.index=next((i for i,u in enumerate(self.units) if u['key']==self.progress.data.get('setup_return_unit')),0)
        self.restore(resume);self.render()

    @property
    def unit(self):return self.units[self.index]
    @property
    def problem(self):return self.unit['problems'][self.variant]
    @property
    def learning_steps(self):
        if self.setup_mode:return setup_course.steps(self.setup_ready)
        return self.unit.get('learning_steps') or STEPS[self.unit['key']]

    def restore(self,position):
        self.phase=position.get('phase','learn')
        if self.phase not in ('learn','example','practice1','practice2'):self.phase='learn'
        if self.setup_mode and self.phase!='learn':self.phase='practice1'
        self.variant={'learn':0,'example':0,'practice1':1,'practice2':2}[self.phase]
        step=position.get('step',0);self.step=min(max(step if isinstance(step,int) else 0,0),len(self.learning_steps)-1)

    def save(self):
        try:
            if self.setup_mode:self.progress.resume(setup_course.KEY,self.phase,self.step)
            elif self.random_return:
                index,phase,step,variant=self.random_return;self.progress.resume(self.units[index]['key'],phase,step)
            else:self.progress.resume(self.unit['key'],self.phase,self.step)
        except OSError as error:QMessageBox.warning(self,'진도 저장 실패',str(error))

    def render_navigation(self):
        testing=self.phase in ('practice1','practice2','random');self.list.clear();number=0
        for i,unit in enumerate(self.units):
            review=unit['key'].startswith('review_')
            if not review:number+=1
            mark='완료' if unit['key'] in self.progress.data['completed'] else '미완료'
            self.list.addItem(('◆ 복습' if review else f'{number:02d}')+f' [{mark}] '+('평가 중 학습 내용 숨김' if testing else unit['title']))
            self.list.item(i).setData(Qt.ItemDataRole.UserRole,i)
        self.list.setCurrentRow(self.index)
        mark='완료' if setup_course.KEY in self.progress.data.get('setup_completed',[]) else '미완료'
        self.setup_button.setText(('설치 설명으로 돌아가기' if self.setup_mode and testing else '설치 평가' if testing else '설치 준비·실습')+' ['+mark+']')
        if self.setup_mode:self.list.setCurrentRow(-1)

    def render(self):
        self.render_navigation()
        testing=self.phase in ('practice1','practice2','random')
        if self.setup_mode:
            self.heading.setText('SHELLGROUND · Conda · 설치 준비' if not testing else 'SHELLGROUND · Conda · 설치 평가')
            if self.phase=='learn':
                part=self.learning_steps[self.step]
                text=f'소단계 {self.step+1}/{len(self.learning_steps)} · '+part['title']+'\n\n'+part['explanation']
                if part['commands']:text+='\n\n직접 입력할 명령\n'+'\n'.join(part['commands'])
                text+='\n\n관찰할 내용\n'+part['observe']
            else:text='목표: '+setup_course.goal(self.setup_ready)
            if not self.setup_ready:text+='\n\n실습을 열면 검증된 설치 파일과 이번에 사용할 새 경로를 표시합니다.'
            self.instructions.setPlainText(text);self.tabs.setCurrentIndex(0)
            while self.answer_layout.rowCount():self.answer_layout.removeRow(0)
            self.answers={};self.answer_box.hide();self.controls();return
        title='활용 문제' if testing else self.unit['title'];self.heading.setText('SHELLGROUND · Conda · '+title)
        if self.phase=='learn':
            part=self.learning_steps[self.step]
            text=f'소단계 {self.step+1}/{len(self.learning_steps)} · '+part['title']+'\n\n'+part['explanation']
            if part['commands']:text+='\n\n지금 입력할 명령 (한 줄씩)\n'+'\n'.join(part['commands'])
            text+='\n\n관찰할 내용\n'+part['observe']
            if self.step==len(self.learning_steps)-1:text+='\n\n다음 예시로 넘어가면 실습 환경을 새로 준비합니다. 완료 진도는 유지됩니다.'
        else:
            text='목표: '+self.problem['goal']
            if self.phase=='example':text+='\n\n직접 입력할 예시\n'+'\n'.join(self.problem['reference_commands'])
        if self.problem.get('fixture_summary'):text+='\n\n준비 상태\n'+self.problem['fixture_summary']
        if self.phase!='learn' and self.problem.get('provided_diagnostics'):
            text+='\n\n확인용 진단식 (암기 대상 아님)\n'+'\n'.join(self.problem['provided_diagnostics'])
            text+='\n'+self.problem.get('diagnostic_note','')
        fixture=self.problem['initial_fixture']
        text+='\n\n시작 위치: /home/learner/conda-work\n준비된 환경: '+(', '.join(x['name'] for x in fixture['environments']) or '없음')+'\n시작 시 활성 환경: '+(fixture.get('active_env') or '없음')
        if fixture['files']:text+='\n준비된 파일·폴더: '+', '.join(x['path'] for x in fixture['files'])
        self.instructions.setPlainText(text);self.tabs.setCurrentIndex(0)
        while self.answer_layout.rowCount():self.answer_layout.removeRow(0)
        self.answers={}
        for field in self.problem['answer_fields']:
            if isinstance(field.get('expected'),bool):
                widget=QComboBox();widget.addItem('선택하세요',None);widget.addItem('예',True);widget.addItem('아니요',False)
            else:widget=QLineEdit()
            self.answers[field['key']]=widget;self.answer_layout.addRow(field['label'],widget)
        self.answer_box.setVisible(bool(self.answers) and self.phase!='learn');self.controls()

    def controls(self):
        for widget in (self.list,self.hint,self.restart,self.try_button,self.random_button,self.return_button,self.full_description,self.preparation_button,self.setup_button):widget.setEnabled(not self.busy)
        self.license_button.setVisible(self.setup_mode);self.license_button.setEnabled(not self.busy and self.setup_ready is not None)
        self.tabs.setTabEnabled(2,not self.setup_mode)
        show_preparation=self.phase=='learn' and self.step>0
        self.preparation_button.setVisible(show_preparation);self.preparation_notice.setVisible(show_preparation)
        self.previous.setVisible(self.phase=='learn');self.previous.setEnabled(not self.busy and self.step>0)
        self.try_button.setText('설명 보며 실습 (F4)' if self.phase=='learn' else '실습 열기 (F4)')
        self.grade_button.setEnabled(not self.busy and self.phase!='learn' and self.terminal.connected)
        self.next_button.setEnabled(not self.busy and (self.phase=='learn' or self.solved))
        self.return_button.setVisible(self.random_return is not None)
        self.random_button.setEnabled(not self.busy and not self.setup_mode and bool(self.progress.data['completed']))
        self.next_button.setText('환경 관리 단원으로 (F6)' if self.setup_mode and self.solved else '다음 (F6)')
        self.file_refresh.setEnabled(not self.busy and self.terminal.connected)
        self.file_picker.setEnabled(not self.busy and self.terminal.connected and self.file_picker.count()>0)

    def job(self,operation,callback,closing_job=False):
        if self.busy:return
        self.busy=True;self.controls();worker=PythonJob(operation);self.worker=worker;result={}
        worker.finished_value.connect(lambda value:result.update(value=value));worker.failed.connect(lambda error:result.update(error=error))
        def finish():
            self.busy=False
            if 'error' in result:
                self.feedback.setText('실행 환경 오류\n'+result['error']);self.tabs.setCurrentIndex(1)
                if closing_job:
                    self.closing=False
                    self.shutdown_failed.emit(result['error'])
            elif not self.closing or closing_job:callback(result.get('value'))
            self.controls()
            if self.closing:QTimer.singleShot(0,self.close)
        worker.finished.connect(finish);worker.start()

    def disconnect(self):
        self.terminal.connected=False
        for reader in self.readers:reader.stop_requested.set()
        if self.engine.bridge:self.engine.bridge.close()
        self.terminal.reset()

    def start(self):
        if self.busy:return
        if self.setup_mode and self.terminal.connected:
            if QMessageBox.question(self,'설치 실습 다시 시작','현재 설치를 덮어쓰지 않고 새 경로를 배정합니다. 새로 시작할까요?')!=QMessageBox.StandardButton.Yes:return
        if self.setup_mode:self.setup_ready=None
        self.file_picker.clear();self.file_text.clear();self.file_notice.setText('실습 폴더의 파일을 읽기 전용으로 확인합니다.')
        self.disconnect();self.solved=False;self.feedback.setText('실제 Conda 실습 준비 중…');self.status.setText('전용 Linux guest 준비 중 · 개인 Conda는 사용하지 않습니다.')
        def ready(process):
            self.terminal.connected=True;reader=TerminalReader(process);self.reader=reader;self.readers.append(reader)
            def receive(data):
                try:
                    if reader is self.reader:self.terminal.feed(data)
                finally:reader.pending.release()
            def ended(message):
                if reader is self.reader and not self.closing:
                    self.terminal.connected=False;self.status.setText(message);self.controls()
            reader.output.connect(receive);reader.ended.connect(ended);reader.start();self.engine.resize(self.terminal.screen.lines,self.terminal.screen.columns)
            info=self.engine.ready['runtime'];identity=self.engine.session_dir.name if self.engine.session_dir else '검증 세션'
            self.status.setText('실제 Linux guest '+identity+' · Conda '+info['conda_version']+' · '+info['platform'])
            if self.setup_mode:
                self.setup_ready=self.engine.ready;self.render()
            self.terminal.setFocus()
        self.job(self.engine.start_setup if self.setup_mode else lambda:self.engine.start_problem(self.problem,self.spec['observer_contract']['module_probes']),ready)

    def try_lab(self):
        if self.busy:return
        if self.terminal.connected:self.terminal.setFocus()
        else:self.start()

    def refresh_files(self):
        if self.busy or self.setup_mode or not self.terminal.connected:return
        def listed(result):
            previous=self.file_picker.currentText();self.file_picker.clear();self.file_picker.addItems(result['files'])
            self.file_notice.setText('실습 폴더 /home/learner/conda-work · 읽기 전용'+(' · 목록은 200항목까지만 표시합니다.' if result['truncated'] else ''))
            if previous in result['files']:self.file_picker.setCurrentText(previous)
            if result['files']:QTimer.singleShot(0,self.read_file)
            else:self.file_text.setPlainText('아직 생성된 파일이 없습니다. 터미널에서 작업한 뒤 새로 고침하세요.')
        self.job(self.engine.inspect_files,listed)

    def read_file(self,*_):
        if self.busy or not self.terminal.connected or not self.file_picker.currentText():return
        relative=self.file_picker.currentText()
        def displayed(result):
            self.file_text.setPlainText(result['text'])
            self.file_notice.setText('실습 폴더 /home/learner/conda-work · 읽기 전용'+(' · 큰 파일의 처음 128 KiB만 표시합니다.' if result['truncated'] else ''))
        self.job(lambda:self.engine.inspect_files(relative),displayed)

    def show_runtime(self):
        if not getattr(self.engine,'ready',None):
            QMessageBox.information(self,'실행 환경','아직 실습을 열지 않았습니다.\n이 과정은 앱 전용 Linux guest의 실제 Conda를 사용합니다. 개인 Conda나 시스템 Python을 사용하지 않습니다.');return
        info=self.engine.ready['runtime']
        QMessageBox.information(self,'실제 실행 환경',
            '앱을 실행한 OS: '+platform.system()+'\n명령 실행 OS: Linux guest\n'
            '전용 임시 디스크 위치: '+str(self.engine.session_dir)+'\n'
            '관리용 base: '+info['root_prefix']+'\n환경 폴더: /home/learner/conda-envs\n'
            '실습 폴더: '+self.engine.ready['start']+'\n저장소: file:///opt/shellground/conda-channel\n'
            '패키지 플랫폼: '+info['platform']+'\n외부 네트워크·호스트 폴더 공유 없음')

    def show_description(self):
        if self.busy:return
        if self.setup_mode:
            self.show_reading('Miniconda 설치 준비', '\n\n'.join(part['title']+'\n'+part['explanation'] for part in self.learning_steps));return
        self.show_reading('Conda 전체 설명 · '+self.unit['title'],
            self.unit['explanation']+'\n\n명령 형태 참고\n'+self.unit['syntax']+
            '\n\n위 이름은 명령 형태를 설명하는 예시입니다. 현재 실습에서는 소단계에 표시된 실제 환경 이름과 경로를 사용하세요.'+
            '\n\n주의\n'+self.unit['pitfall'])

    def show_reading(self,title,text):
        dialog=QDialog(self);dialog.setWindowTitle(title);dialog.resize(760,520)
        layout=QVBoxLayout(dialog);body=QPlainTextEdit();body.setReadOnly(True);body.setPlainText(text);layout.addWidget(body)
        buttons=QDialogButtonBox(QDialogButtonBox.StandardButton.Close);buttons.rejected.connect(dialog.reject);layout.addWidget(buttons)
        dialog.exec()

    def preparation_text(self):
        if self.phase!='learn' or self.step==0:return ''
        text=('소단계 '+str(self.step+1)+'에서 이어서 배우기\n\n'
              '학습 위치와 완료 기록은 저장됩니다. 이전에 입력했던 명령과 임시 환경·파일은 저장하지 않습니다.\n'
              '앱을 다시 열었거나 F2로 초기화했다면, 실습을 열고 아래의 이전 소단계를 순서대로 다시 준비하세요.\n'
              '같은 실습을 계속 사용하는 중이면 반복 실행하지 마세요. 특히 환경 생성·삭제와 activate/deactivate를 중복 실행하면 상태가 달라질 수 있습니다.\n'
              '이 안내를 여는 것만으로 명령을 실행하거나 완료 처리하지 않습니다.\n')
        for number,part in enumerate(self.learning_steps[:self.step],1):
            text+='\n'+str(number)+'. '+part['title']+'\n'+part['explanation']+'\n'
            text+='\n'.join(part['commands']) if part['commands'] else '이 단계는 파일 관찰입니다.'
            text+='\n확인: '+part['observe']+'\n'
        return text

    def show_preparation(self):
        if self.busy:return
        text=self.preparation_text()
        if text:self.show_reading('이전 소단계 준비 · '+('Miniconda 설치' if self.setup_mode else self.unit['title']),text)

    def show_installer(self):
        if self.busy or not self.setup_ready:return
        info=self.setup_ready['installer']
        self.show_reading('설치 파일·라이선스',
            '공식 출처: '+info['url']+'\n파일: '+info['path']+'\n검증된 SHA-256: '+info['sha256']+
            '\n명령 실행 플랫폼: '+info['subdir']+'\n\n'+info['license']+
            '\n\n이 창을 열거나 닫는 것으로 설치하거나 동의하지 않습니다. 약관을 확인하고 동의한 경우에만 -b 설치 명령을 직접 실행하세요.')

    def open_setup(self):
        if self.busy:return
        if self.setup_mode:
            self.phase='learn';self.variant=0;self.save();self.render();return
        if self.terminal.connected and not self.solved and QMessageBox.question(self,'설치 준비로 이동','현재 실습 터미널을 닫고 설치 준비로 이동할까요? 학습 진도는 유지됩니다.')!=QMessageBox.StandardButton.Yes:return
        self.save();self.disconnect();self.random_return=None
        self.progress.data['setup_return_unit']=self.unit['key']
        self.setup_mode=True;self.setup_ready=None;self.solved=False
        self.restore(self.progress.data['positions'].get(setup_course.KEY,{}));self.save();self.render()

    def grade(self):
        if self.busy or self.phase=='learn' or not self.terminal.connected:return
        answers={key:(widget.currentData() if isinstance(widget,QComboBox) else widget.text()) for key,widget in self.answers.items()}
        def graded(value):
            self.solved=value['passed'];self.feedback.set_results(('새 설치 결과 확인 완료' if self.setup_mode else '완료') if self.solved else '미완료 항목을 수정하고 다시 채점하세요.',value['checks']);self.tabs.setCurrentIndex(1)
            if self.solved:
                try:
                    if self.setup_mode:
                        completed=self.progress.data.setdefault('setup_completed',[])
                        if setup_course.KEY not in completed:completed.append(setup_course.KEY)
                        self.save()
                    else:self.progress.passed(self.unit['key'],self.variant)
                except OSError as error:QMessageBox.warning(self,'진도 저장 실패',str(error))
                self.render_navigation()
        self.job(self.engine.grade_setup if self.setup_mode else lambda:self.engine.grade_problem(answers),graded)

    def feedback_hint(self):
        if self.busy:return
        if self.setup_mode:
            self.feedback.setText('새 설치는 bash 설치파일 -b -p 새경로 형식입니다. -b는 라이선스 동의를 전제로 합니다.\n'
                '설치를 마쳤다면 새경로/bin/conda와 새경로/bin/python으로 확인하세요. 관리용 base의 버전만 확인하면 안 됩니다.');self.tabs.setCurrentIndex(1);return
        self.feedback.setText(self.problem['hint']);self.tabs.setCurrentIndex(1)

    def select(self,index,confirmed=False):
        if self.busy:return
        if not confirmed and self.terminal.connected and not self.solved and QMessageBox.question(self,'단원 전환','임시 실습 상태를 버리고 단원을 바꿀까요? 완료 진도는 유지됩니다.')!=QMessageBox.StandardButton.Yes:
            self.list.setCurrentRow(self.index);return
        self.save();self.disconnect();self.random_return=None;self.index=index;self.solved=False;self.setup_mode=False;self.setup_ready=None
        self.restore(self.progress.data['positions'].get(self.unit['key'],{}));self.save();self.render()

    def open_practice(self,key,variant):
        if self.busy:return False
        index=next((i for i,u in enumerate(self.units) if u['key']==key),None)
        if index is None or type(variant) is not int or variant not in (0,1,2):return False
        phase=('example','practice1','practice2')[variant]
        if not self.setup_mode and (self.index,self.phase,self.variant)==(index,phase,variant):return True
        if self.terminal.connected and QMessageBox.question(self,'관련 실습으로 이동',
                '현재 Conda 터미널과 임시 실습을 닫고 관련 실습으로 이동할까요? 학습 완료 기록은 유지됩니다.',
                QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No,QMessageBox.StandardButton.No)!=QMessageBox.StandardButton.Yes:
            return False
        self.select(index,confirmed=True)
        self.phase,self.variant,self.step=phase,variant,0
        self.save();self.render()
        return True

    def previous_step(self):
        if not self.busy and self.phase=='learn' and self.step>0:self.step-=1;self.save();self.render()

    def advance(self):
        if self.busy:return
        if self.setup_mode:
            if self.phase=='learn' and self.step+1<len(self.learning_steps):
                self.step+=1;self.save();self.render();return
            if self.phase=='learn':
                self.phase='practice1';self.variant=1;self.save();self.render()
                if not self.terminal.connected:self.start()
            elif self.solved:self.select(self.index)
            return
        if self.phase=='learn':
            if self.step+1<len(self.learning_steps):self.step+=1;self.save();self.render();return
            self.phase='example';self.variant=0
        elif not self.solved:return
        elif self.phase=='random':self.random_problem();return
        elif self.phase=='example':self.phase='practice1';self.variant=1
        elif self.phase=='practice1':self.phase='practice2';self.variant=2
        else:
            self.select(min(self.index+1,len(self.units)-1));return
        self.save();self.render();self.start()

    def start_random(self):
        if self.busy or self.setup_mode or not self.progress.data['completed']:return
        if not self.random_return:self.random_return=(self.index,self.phase,self.step,self.variant)
        self.random_problem()

    def random_problem(self):
        choices=[i for i,u in enumerate(self.units) if u['key'] in self.progress.data['completed']]
        if not choices:return
        self.index=random.choice(choices);self.phase='random';self.variant=random.choice((1,2));self.render();self.start()

    def stop_random(self):
        if self.busy or self.random_return is None:return
        self.disconnect();self.index,self.phase,self.step,self.variant=self.random_return;self.random_return=None;self.solved=False;self.save();self.render()

    def closeEvent(self,event):
        if self.closed:self.finish_shutdown(event);return
        event.ignore();self.closing=True;self.save();self.disconnect()
        if self.busy:self.engine.cancel_pending();return
        def done(_):self.closed=True
        self.job(self.engine.close,done,closing_job=True)
