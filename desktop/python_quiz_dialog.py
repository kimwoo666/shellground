"""Native conceptual quizzes; mastery is independent of practical completion."""
import json
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPlainTextEdit, QRadioButton, QButtonGroup, QPushButton, QMessageBox, QWidget, QTabWidget, QComboBox)
from engine import resource_path


class QuizDialog(QDialog):
    def __init__(self, progress, parent=None, practice_handler=None):
        super().__init__(parent)
        self.setWindowTitle('Python·데이터 개념 퀴즈')
        self.resize(820, 660)
        self.progress = progress
        self.practice_handler=practice_handler
        from python_teaching.practice_links import load_links
        self.practice_links=load_links()
        self.questions = json.loads(resource_path('python_teaching/quiz_bank.json').read_text(encoding='utf-8'))['questions']
        self.cards = json.loads(resource_path('python_teaching/concept_cards.json').read_text(encoding='utf-8'))['cards']
        self.index = next((i for i,q in enumerate(self.questions)
                           if not progress.data['quiz'].get(q['id'], {}).get('passed')), 0)
        layout = QVBoxLayout(self)
        self.heading = QLabel()
        layout.addWidget(self.heading)
        self.tabs=QTabWidget(); layout.addWidget(self.tabs)
        study=QWidget(); study_layout=QVBoxLayout(study)
        self.card_text=QPlainTextEdit(); self.card_text.setReadOnly(True); study_layout.addWidget(self.card_text)
        card_buttons=QHBoxLayout(); study_layout.addLayout(card_buttons)
        self.card_previous=QPushButton('← 이전 개념'); self.card_previous.clicked.connect(lambda:self.move_card(-1))
        self.card_next=QPushButton('다음 개념 →'); self.card_next.clicked.connect(lambda:self.move_card(1))
        self.to_quiz=QPushButton('직접 풀기'); self.to_quiz.clicked.connect(lambda:self.tabs.setCurrentIndex(1))
        for b in (self.card_previous,self.card_next,self.to_quiz):card_buttons.addWidget(b)
        self.tabs.addTab(study,'개념 배우기')
        test=QWidget(); self.tabs.addTab(test,'퀴즈'); layout=QVBoxLayout(test)
        self.prompt = QPlainTextEdit()
        self.prompt.setReadOnly(True)
        layout.addWidget(self.prompt, 2)
        self.group = QButtonGroup(self)
        self.options = []
        self.option_labels=[]
        for i in range(4):
            row=QHBoxLayout()
            button = QRadioButton(chr(65+i))
            self.group.addButton(button, i)
            self.options.append(button)
            label=QLabel(); label.setTextFormat(Qt.TextFormat.PlainText); label.setWordWrap(True)
            self.option_labels.append(label)
            row.addWidget(button);row.addWidget(label,1);layout.addLayout(row)
        self.explanation = QPlainTextEdit()
        self.explanation.setReadOnly(True)
        layout.addWidget(self.explanation, 2)
        buttons = QHBoxLayout()
        self.submit = QPushButton('답 확인')
        self.submit.clicked.connect(self.grade)
        self.next = QPushButton('다음 퀴즈')
        self.next.clicked.connect(self.advance)
        close = QPushButton('닫기')
        close.clicked.connect(self.accept)
        for button in (self.submit, self.next, close): buttons.addWidget(button)
        layout.addLayout(buttons)
        practice=QWidget();practice_layout=QVBoxLayout(practice)
        self.practice_text=QPlainTextEdit();self.practice_text.setReadOnly(True);practice_layout.addWidget(self.practice_text)
        self.practice_picker=QComboBox();practice_layout.addWidget(self.practice_picker)
        self.practice_open=QPushButton('선택한 관련 실습 열기');self.practice_open.clicked.connect(self.open_practice)
        practice_layout.addWidget(self.practice_open)
        self.tabs.addTab(practice,'관련 실습')
        self.render()

    def render_practice(self):
        link=self.practice_links[self.questions[self.index]['id']]
        text=('이동만으로 명령을 실행하거나 실습을 완료 처리하지 않습니다.\n'
              '퀴즈 정답과 실습 통과는 별도로 기록합니다.\n\n')
        text+='퀴즈에서 이어갈 확장 목표\n'+self.questions[self.index]['practical_followup']['goal']+'\n\n'
        if link['targets']:
            text+='관련 실습에서 연습할 내용\n'+link['coverage']+'\n\n확장 목표와 다른 점·아직 평가하지 않는 범위\n'+link['remaining_gap']
        else:text+='이 개념과 직접 연결된 채점 실습은 아직 없습니다.\n'+link['remaining_gap']
        self.practice_text.setPlainText(text);self.practice_picker.clear()
        for target in link['targets']:
            label={'python':'Python','conda':'Conda·pip','notebook':'노트북·Jupyter'}[target['course']]+' · '+target['title']+' · '+('예시','활용 1','활용 2')[target['problem_index']]
            self.practice_picker.addItem(label,target)
        self.practice_picker.setEnabled(bool(link['targets']))
        self.practice_open.setEnabled(bool(link['targets']) and self.practice_handler is not None)

    def open_practice(self):
        target=self.practice_picker.currentData()
        if target is None or self.practice_handler is None:return
        if self.practice_handler(target):self.accept()

    def move_card(self, offset):
        self.card_index=max(0,min(len(self.related_cards)-1,self.card_index+offset))
        self.render_card()

    def render_card(self):
        if not self.related_cards:
            self.card_text.setPlainText('이 주제는 해당 실습 단원의 설명을 함께 복습하세요.')
            self.card_previous.setEnabled(False); self.card_next.setEnabled(False); return
        card=self.related_cards[self.card_index]
        source=card['source']; reference='보충 개념' if source['document']=='supplement' else source['document']+' · 실제 '+', '.join(map(str,source['pages']))+'쪽'
        self.card_text.setPlainText(f'{self.card_index+1}/{len(self.related_cards)} · '+card['title']+'\n\n왜 배우나요?\n'+card['why']+'\n\n'+card['explanation']+'\n\n예시\n'+card['example']+'\n\n헷갈리기 쉬운 점\n'+card['misconception']+'\n\n'+reference)
        self.card_previous.setEnabled(self.card_index>0)
        self.card_next.setEnabled(self.card_index+1<len(self.related_cards))
        self.progress.data.setdefault('concept_positions',{})[self.questions[self.index]['id']]=card['id']
        try:self.progress.save()
        except OSError as exc:QMessageBox.warning(self,'개념 진도 저장 실패',str(exc))

    def render(self):
        q = self.questions[self.index]
        self.heading.setText(f'개념 퀴즈 {self.index+1}/{len(self.questions)} · {q["topic"]}')
        self.related_cards=[card for card in self.cards if q['id'] in card['quiz_ids']]
        saved=self.progress.data.get('concept_positions',{}).get(q['id'])
        self.card_index=next((i for i,c in enumerate(self.related_cards) if c['id']==saved),0)
        self.render_card(); self.tabs.setCurrentIndex(0 if self.related_cards else 1)
        self.prompt.setPlainText(q['prompt'])
        self.group.setExclusive(False)
        for button, label, text in zip(self.options,self.option_labels,q['choices']):
            button.setChecked(False)
            label.setText(text);button.setAccessibleName(text)
        self.group.setExclusive(True)
        self.explanation.clear()
        self.next.setEnabled(False)
        self.render_practice()

    def grade(self):
        selected = self.group.checkedId()
        if selected < 0: return
        q = self.questions[self.index]
        passed = selected == q['answer']
        self.explanation.setPlainText(('정답입니다.\n\n' if passed else '다시 생각해 보세요.\n\n') +
            q['explanation'] + '\n\n흔한 오해: ' + q['misconception'])
        old = self.progress.data['quiz'].get(q['id'], {})
        self.progress.data['quiz'][q['id']] = {'attempts': old.get('attempts', 0)+1,
                                             'passed': passed or old.get('passed', False)}
        try: self.progress.save()
        except OSError as exc: QMessageBox.warning(self, '퀴즈 진도 저장 실패', str(exc))
        self.next.setEnabled(passed)

    def advance(self):
        if self.next.isEnabled():
            self.index = (self.index+1) % len(self.questions)
            self.render()
