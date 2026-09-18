"""Native Linux/Docker concepts. Opening/answering never starts an engine."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QComboBox, QLabel,
    QTabWidget, QWidget, QPlainTextEdit, QPushButton, QButtonGroup, QRadioButton, QScrollArea)
from system_concepts import load_catalog
from system_concept_progress import ConceptProgress


class SystemConceptDialog(QDialog):
    def __init__(self, path, parent=None, topic='linux', practice_handler=None):
        super().__init__(parent)
        self.setWindowTitle('Linux · Docker 개념 배우기와 퀴즈')
        self.resize(900, 760)
        self.setMinimumSize(640, 520)
        self.progress = ConceptProgress(path)
        self.practice_handler = practice_handler
        self.catalog = {key: load_catalog(key) for key in ('linux', 'docker')}
        from mode_curriculum import curriculum
        self.practice_units = {unit.key: unit for unit in curriculum('real')[0]}
        layout = QVBoxLayout(self)
        row = QHBoxLayout()
        self.topic_picker = QComboBox()
        for title, key in (('Linux', 'linux'), ('Docker', 'docker')):
            self.topic_picker.addItem(title, key)
        self.topic_picker.setCurrentIndex(1 if topic == 'docker' else 0)
        self.topic_picker.setAccessibleName('개념 분야')
        self.question_picker = QComboBox()
        self.question_picker.setAccessibleName('개념 문제 선택')
        self.question_picker.setMinimumContentsLength(18)
        self.question_picker.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        row.addWidget(self.topic_picker); row.addWidget(self.question_picker, 1)
        layout.addLayout(row)
        self.summary = QLabel()
        self.summary.setWordWrap(True)
        layout.addWidget(self.summary)
        self.error = QLabel()
        self.error.setWordWrap(True)
        self.error.setTextFormat(Qt.TextFormat.PlainText)
        self.error.setVisible(False)
        layout.addWidget(self.error)
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs, 1)
        study = QWidget(); study_layout = QVBoxLayout(study)
        self.card_text = self.readonly()
        study_layout.addWidget(self.card_text, 1)
        card_row = QHBoxLayout()
        self.previous_card = QPushButton('← 이전 개념')
        self.next_card = QPushButton('다음 개념 →')
        self.to_quiz = QPushButton('직접 풀기')
        self.previous_card.clicked.connect(lambda: self.move_card(-1))
        self.next_card.clicked.connect(lambda: self.move_card(1))
        self.to_quiz.clicked.connect(lambda: self.tabs.setCurrentIndex(1))
        for button in (self.previous_card, self.next_card, self.to_quiz): card_row.addWidget(button)
        study_layout.addLayout(card_row)
        self.tabs.addTab(study, '개념 배우기')

        test = QWidget(); test_layout = QVBoxLayout(test)
        self.prompt = self.readonly()
        test_layout.addWidget(self.prompt, 3)
        options_scroll = QScrollArea(); options_scroll.setWidgetResizable(True)
        options_scroll.setMinimumHeight(130)
        options_widget = QWidget(); choices_layout = QVBoxLayout(options_widget)
        self.group = QButtonGroup(self); self.options = []; self.option_labels = []
        for index in range(4):
            choice_row = QHBoxLayout()
            choice = QRadioButton(chr(65 + index)); self.group.addButton(choice, index)
            choice_label = QLabel(); choice_label.setWordWrap(True)
            choice_label.setTextFormat(Qt.TextFormat.PlainText)
            choice_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            choice_row.addWidget(choice); choice_row.addWidget(choice_label, 1)
            choices_layout.addLayout(choice_row)
            self.options.append(choice); self.option_labels.append(choice_label)
        choices_layout.addStretch()
        options_scroll.setWidget(options_widget); test_layout.addWidget(options_scroll, 2)
        self.submit = QPushButton('답 확인')
        self.submit.clicked.connect(self.grade); test_layout.addWidget(self.submit)
        self.group.buttonClicked.connect(self.allow_resubmit)
        self.tabs.addTab(test, '퀴즈')
        evaluation = QWidget(); evaluation_layout = QVBoxLayout(evaluation)
        self.feedback = self.readonly(); evaluation_layout.addWidget(self.feedback, 1)
        self.try_again = QPushButton('문제로 돌아가 답 다시 고르기')
        self.try_again.clicked.connect(lambda: self.tabs.setCurrentIndex(1))
        evaluation_layout.addWidget(self.try_again)
        self.tabs.addTab(evaluation, '채점 결과')

        practice = QWidget(); practice_layout = QVBoxLayout(practice)
        self.practice_text = self.readonly(); practice_layout.addWidget(self.practice_text, 1)
        self.practice_picker = QComboBox(); self.practice_picker.setAccessibleName('관련 실습 단원')
        self.practice_open = QPushButton('관련 단원 설명 보기')
        self.practice_open.clicked.connect(self.open_practice)
        practice_layout.addWidget(self.practice_picker); practice_layout.addWidget(self.practice_open)
        self.tabs.addTab(practice, '관련 실습')
        navigation = QHBoxLayout()
        self.previous = QPushButton('← 이전 문제'); self.previous.clicked.connect(lambda: self.move_question(-1))
        self.next = QPushButton('다음 문제 →'); self.next.clicked.connect(lambda: self.move_question(1))
        close = QPushButton('닫기'); close.clicked.connect(self.accept)
        for button in (self.previous, self.next, close): navigation.addWidget(button)
        layout.addLayout(navigation)
        self.topic_picker.currentIndexChanged.connect(self.change_topic)
        self.question_picker.currentIndexChanged.connect(self.render)
        self.change_topic()

    @staticmethod
    def readonly():
        editor = QPlainTextEdit(); editor.setReadOnly(True)
        return editor

    def persist(self, operation):
        try:
            operation(); self.error.hide()
        except OSError as exc:
            self.error.setText('저장 실패 · ' + str(exc)); self.error.show()

    def change_topic(self, *_):
        self.topic = self.topic_picker.currentData()
        self.questions = self.catalog[self.topic]
        position = self.progress.data['positions'].get(self.topic, {})
        self.question_picker.blockSignals(True); self.question_picker.clear()
        for index, question in enumerate(self.questions):
            self.question_picker.addItem(f'{index + 1:02d} · {question["title"]}', question['id'])
        index = next((i for i, q in enumerate(self.questions) if q['id'] == position.get('question')),
                     next((i for i, q in enumerate(self.questions)
                           if not self.progress.data['quiz'].get(q['id'], {}).get('passed')), 0))
        self.question_picker.setCurrentIndex(index); self.question_picker.blockSignals(False)
        self.render()

    def render(self, *_):
        self.index = self.question_picker.currentIndex()
        self.question = self.questions[self.index]
        q = self.question
        self.question_picker.setToolTip(q['title'])
        saved = self.progress.data['positions'].get(self.topic, {})
        self.card_index = next((i for i, c in enumerate(q['cards'])
                                if saved.get('question') == q['id'] and c['id'] == saved.get('card')), 0)
        self.render_card(); self.tabs.setCurrentIndex(0)
        self.prompt.setPlainText(q['prompt'])
        self.group.setExclusive(False)
        for option, label, choice in zip(self.options, self.option_labels, q['choices']):
            option.setChecked(False); option.setAccessibleName(choice); label.setText(choice)
        self.group.setExclusive(True)
        self.feedback.clear(); self.tabs.setTabEnabled(2, False)
        self.submit.setEnabled(True)
        self.previous.setEnabled(self.index > 0); self.next.setEnabled(self.index + 1 < len(self.questions))
        self.update_summary()
        self.render_practice()

    def update_summary(self):
        completed = sum(bool(self.progress.data['quiz'].get(q['id'], {}).get('passed')) for q in self.questions)
        state = '완료' if self.progress.data['quiz'].get(self.question['id'], {}).get('passed') else '미완료'
        self.summary.setText(f'개념 {completed}/{len(self.questions)} 완료 · 현재 {state} · 실습 완료와 별도로 자동 저장')

    def render_card(self):
        q = self.question; card = q['cards'][self.card_index]
        references = '\n'.join(source.get('title', '') + ('\n' + source['url'] if source.get('url') else '') for source in q['sources'])
        self.card_text.setPlainText(f'{self.card_index + 1}/{len(q["cards"])} · {card["title"]}\n\n'
            + card['explanation'] + ('\n\n설명 예시\n' + card['example'] if card['example'] else '')
            + '\n\n근거\n' + references)
        self.previous_card.setEnabled(self.card_index > 0)
        self.next_card.setEnabled(self.card_index + 1 < len(q['cards']))
        self.persist(lambda: self.progress.position(self.topic, q['id'], card['id']))

    def move_card(self, offset):
        self.card_index = max(0, min(len(self.question['cards']) - 1, self.card_index + offset))
        self.render_card()

    def move_question(self, offset):
        self.question_picker.setCurrentIndex(max(0, min(len(self.questions) - 1, self.index + offset)))

    def allow_resubmit(self, *_):
        self.submit.setEnabled(True)

    def grade(self):
        selected = self.group.checkedId()
        if selected < 0: return
        q = self.question; passed = selected == q['answer']
        self.persist(lambda: self.progress.grade(q['id'], passed))
        explanations = '\n\n'.join(f'{chr(65+i)} · {value}' for i, value in enumerate(q['feedback']))
        self.feedback.setPlainText(('정답입니다.' if passed else '다시 생각해 보세요. 답을 바꾸어 재시도할 수 있습니다.')
            + f'\n\n선택한 답: {chr(65+selected)} · {q["choices"][selected]}'
            + f'\n정답: {chr(65+q["answer"])} · {q["choices"][q["answer"]]}'
            + '\n\n보기별 해설\n' + explanations)
        self.tabs.setTabEnabled(2, True); self.tabs.setCurrentIndex(2)
        self.submit.setEnabled(False); self.update_summary()

    def render_practice(self):
        q = self.question
        self.practice_text.setPlainText('개념 정답은 실습 완료가 아닙니다. 아래 버튼은 설명으로 이동할 뿐 명령을 실행하지 않습니다.\n'
            '실습 중에 이동하면 기존 문제의 임시 상태를 버릴지 먼저 확인합니다.\n\n' + q['practice_note'])
        self.practice_picker.clear()
        for key in q['practice_keys']:
            self.practice_picker.addItem(self.practice_units[key].title, key)
        available = bool(q['practice_keys'])
        self.practice_picker.setEnabled(available)
        self.practice_open.setEnabled(available and self.practice_handler is not None)

    def open_practice(self):
        key = self.practice_picker.currentData()
        if key and self.practice_handler and self.practice_handler(key): self.accept()
