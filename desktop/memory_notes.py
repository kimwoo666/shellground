"""User-chosen learning notes, separate from progress and terminal history."""
import json
from pathlib import Path
import uuid
from PySide6.QtCore import Qt
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (QDialog, QHBoxLayout, QVBoxLayout, QListWidget, QListWidgetItem,
                              QLineEdit, QPlainTextEdit, QPushButton, QLabel, QMessageBox)


class NoteStore:
    def __init__(self, path):
        self.path = Path(path)

    def load(self):
        try:
            data = json.loads(self.path.read_text(encoding='utf-8'))
        except FileNotFoundError:
            return []
        if not isinstance(data, dict) or data.get('schema') != 1 or not isinstance(data.get('notes'), list):
            raise ValueError('기억노트 파일 형식을 읽을 수 없습니다. 원본은 덮어쓰지 않습니다.')
        ids = set()
        for note in data['notes']:
            if (not isinstance(note, dict) or any(not isinstance(note.get(key), str) for key in ('id', 'title', 'body', 'unit'))
                    or not note['id'] or note['id'] in ids):
                raise ValueError('기억노트 내용이 손상되었습니다. 원본은 덮어쓰지 않습니다.')
            ids.add(note['id'])
        return data['notes']

    def write(self, notes):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_name(self.path.name + '.' + uuid.uuid4().hex + '.tmp')
        try:
            temporary.write_text(json.dumps({'schema': 1, 'notes': notes}, ensure_ascii=False, indent=2), encoding='utf-8')
            temporary.replace(self.path)
        finally:
            temporary.unlink(missing_ok=True)

    def save(self, title, body, unit='', note_id=None):
        title, body = title.strip(), body.strip()
        if not title or not body:
            raise ValueError('제목과 기억할 내용을 모두 입력하세요.')
        notes = self.load()  # Never overwrite a corrupt file with an empty list.
        if note_id is None:
            same = next((n for n in notes if n['title'] == title and n['body'] == body), None)
            note_id = same['id'] if same else uuid.uuid4().hex
        note = {'id': note_id, 'title': title, 'body': body, 'unit': unit}
        notes = [note, *(n for n in notes if n['id'] != note_id)]
        self.write(notes)
        return note

    def delete(self, note_id):
        self.write([n for n in self.load() if n['id'] != note_id])


def suggest_note(unit, mission=None, selected=''):
    if selected.strip():
        body = selected.replace('\u2029', '\n').strip()
        title = body.splitlines()[0][:60]
    elif '공백' in (mission.prompt if mission else unit.explanation):
        title = '공백이 있는 경로는 따옴표로 묶기'
        body = ('규칙\n공백이 있는 파일·폴더 경로 전체를 작은따옴표 또는 큰따옴표로 묶어 한 인자로 전달한다.\n\n'
                '예시\ncat "docs/read me.txt"\nmkdir "daily notes"\n\n'
                '주의\ncat docs/read me.txt처럼 쓰면 docs/read와 me.txt라는 두 인자로 나뉜다.\n'
                '필요한 경로만 묶고 명령 전체를 따옴표로 감싸지 않는다.')
    else:
        title, body = unit.title, unit.explanation
    return {'title': title, 'body': body, 'unit': unit.key}


class MemoryDialog(QDialog):
    def __init__(self, store, parent=None, draft=None):
        super().__init__(parent)
        self.store = store
        self.current_id = None
        self.unit = ''
        self.dirty = False
        self.loading = False
        self.notes = []
        self.load_error = None
        self.setWindowTitle('내 기억노트 — 규칙과 예시 모아두기')
        self.resize(860, 580)
        layout = QVBoxLayout(self)
        label = QLabel('직접 저장한 규칙·예시만 보관합니다. 터미널 입력이나 학습 진도를 자동 복사하지 않습니다.')
        label.setWordWrap(True)
        layout.addWidget(label)
        self.search = QLineEdit()
        self.search.setPlaceholderText('찾기: 공백, 따옴표, ls … (제목·내용 검색)')
        layout.addWidget(self.search)
        row = QHBoxLayout()
        self.list = QListWidget()
        self.list.setMinimumWidth(240)
        row.addWidget(self.list, 1)
        editor = QVBoxLayout()
        self.title = QLineEdit()
        self.title.setPlaceholderText('제목')
        self.body = QPlainTextEdit()
        self.body.setPlaceholderText('기억할 규칙, 사용 예시, 내가 자주 틀리는 점을 적으세요.')
        editor.addWidget(self.title)
        editor.addWidget(self.body)
        row.addLayout(editor, 2)
        layout.addLayout(row, 1)
        self.status = QLabel('')
        self.status.setWordWrap(True)
        self.status.setTextFormat(Qt.TextFormat.PlainText)
        layout.addWidget(self.status)
        buttons = QHBoxLayout()
        self.new_button = QPushButton('새 노트')
        self.save_button = QPushButton('저장 (Ctrl+S)')
        save_action = QAction(self)
        save_action.setShortcut('Ctrl+S')
        save_action.setAutoRepeat(False)
        save_action.triggered.connect(self.save_note)
        self.addAction(save_action)
        self.delete_button = QPushButton('삭제')
        close = QPushButton('닫기 (Esc)')
        for button in (self.new_button, self.save_button, self.delete_button, close):
            button.setAutoDefault(False)
            buttons.addWidget(button)
        layout.addLayout(buttons)
        self.title.textChanged.connect(self.changed)
        self.body.textChanged.connect(self.changed)
        self.search.textChanged.connect(self.refresh)
        self.list.currentItemChanged.connect(self.select)
        self.new_button.clicked.connect(self.new_note)
        self.save_button.clicked.connect(self.save_note)
        self.delete_button.clicked.connect(self.delete_note)
        close.clicked.connect(self.reject)
        try:
            self.notes = store.load()
        except (OSError, ValueError) as exc:
            self.load_error = str(exc)
            self.status.setText('읽기 실패: ' + str(exc))
            self.save_button.setEnabled(False)
            self.delete_button.setEnabled(False)
        self.refresh()
        if draft:
            duplicate = next((n for n in self.notes if n['title'] == draft['title'] and n['body'] == draft['body']), None)
            self.fill(duplicate or draft)
            if not duplicate:
                self.dirty = True
                self.status.setText('저장할 내용의 초안입니다. 수정한 뒤 저장하세요.')
        elif self.notes:
            self.fill(self.notes[0])
        else:
            self.fill({})
        if self.load_error:
            self.status.setText('읽기 실패: ' + self.load_error + ' · 원본 보호를 위해 저장하지 않습니다.')

    def changed(self):
        if not self.loading:
            self.dirty = True
            self.status.setText('수정 중 · 아직 저장되지 않았습니다.')

    def refresh(self):
        query = self.search.text().casefold()
        self.list.blockSignals(True)
        self.list.clear()
        for note in self.notes:
            if query not in (note['title'] + '\n' + note['body']).casefold(): continue
            item = QListWidgetItem(note['title'])
            item.setData(Qt.ItemDataRole.UserRole, note['id'])
            self.list.addItem(item)
            if note['id'] == self.current_id: self.list.setCurrentItem(item)
        self.list.blockSignals(False)

    def fill(self, note):
        self.loading = True
        self.current_id, self.unit = note.get('id'), note.get('unit', '')
        self.title.setText(note.get('title', ''))
        self.body.setPlainText(note.get('body', ''))
        self.dirty = False
        self.loading = False
        self.delete_button.setEnabled(self.save_button.isEnabled() and self.current_id is not None)
        self.refresh()

    def may_leave(self):
        if not self.dirty: return True
        answer = QMessageBox.question(self, '저장하지 않은 기억노트', '수정한 노트를 저장할까요?',
                                      QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Discard | QMessageBox.StandardButton.Cancel,
                                      QMessageBox.StandardButton.Save)
        if answer == QMessageBox.StandardButton.Save: return self.save_note()
        return answer == QMessageBox.StandardButton.Discard

    def select(self, item, previous):
        if item is None: return
        note_id = item.data(Qt.ItemDataRole.UserRole)
        if note_id == self.current_id: return
        if not self.may_leave():
            self.refresh()
            return
        self.fill(next(n for n in self.notes if n['id'] == note_id))
        self.status.setText('저장된 기억노트')

    def new_note(self):
        if self.may_leave():
            self.fill({})
            self.status.setText('새 노트를 작성하세요.')
            self.title.setFocus()

    def save_note(self):
        if not self.save_button.isEnabled(): return False
        try:
            note = self.store.save(self.title.text(), self.body.toPlainText(), self.unit, self.current_id)
            self.notes = self.store.load()
        except (OSError, ValueError) as exc:
            self.status.setText('저장 실패: ' + str(exc))
            QMessageBox.warning(self, '기억노트 저장 실패', str(exc))
            return False
        self.fill(note)
        self.status.setText('기억노트 저장됨 · 프로그램을 종료해도 유지됩니다.')
        return True

    def delete_note(self):
        if self.current_id is None: return
        if QMessageBox.question(self, '기억노트 삭제', '이 노트를 삭제할까요? 삭제 후 복구할 수 없습니다.') != QMessageBox.StandardButton.Yes: return
        try:
            self.store.delete(self.current_id)
            self.notes = self.store.load()
        except (OSError, ValueError) as exc:
            QMessageBox.warning(self, '기억노트 삭제 실패', str(exc))
            return
        self.fill(self.notes[0] if self.notes else {})
        self.status.setText('노트를 삭제했습니다.')

    def reject(self):
        if self.may_leave(): super().reject()

    def closeEvent(self, event):
        if self.may_leave(): event.accept()
        else: event.ignore()
