"""Native mode picker, separate from terminal input and lesson hints."""
from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton, QGroupBox
from PySide6.QtCore import QStandardPaths
from pathlib import Path
import json
from execution_modes import SIMULATION, REAL, mode_available, mode_progress_path


def saved_progress_summary(base_path, mode):
    from mode_curriculum import curriculum
    try:
        data = json.loads(mode_progress_path(base_path, mode).read_text(encoding='utf-8'))
        if not isinstance(data, dict) or not isinstance(data.get('completed'), list):
            raise ValueError('Invalid progress')
        units, checkpoints = curriculum(mode)
        lessons = sum(u.key in data['completed'] for u in units)
        reviews = sum(c.key in data.get('checkpoints', []) for c in checkpoints)
        from learning_progress import read_records
        learning = read_records(data.get('learning'))
        partial = sum(u.key in learning for u in units)
        archived = len(set(data.get('checkpoints', [])) - {c.key for c in checkpoints})
        text = f'저장된 완료 기록: 단원 {lessons}개 · 종합 복습 {reviews}개'
        if partial: text += f' · 소단계 위치 {partial}단원'
        if archived: text += f'\n이전 구성 복습 {archived}개도 보존됨 · 새 조합 복습과 별도'
        return text
    except FileNotFoundError:
        return '이 모드에는 저장된 완료 기록이 없습니다. 다른 모드의 기록은 그대로 유지됩니다.'
    except (OSError, ValueError, TypeError):
        return '저장된 진도를 읽을 수 없습니다. 기존 파일은 변경하지 않았습니다.'


class ModeDialog(QDialog):
    def __init__(self, parent=None, progress_path=None):
        super().__init__(parent)
        self.selected_mode = None
        self.setWindowTitle('Shellground — 실습 모드 선택')
        self.resize(680, 500)
        layout = QVBoxLayout(self)
        heading = QLabel('실습 방식을 선택하세요. 시뮬레이션과 실제 환경은 서로 다릅니다.')
        heading.setWordWrap(True)
        layout.addWidget(heading)
        self.buttons = {}
        self.progress_labels = {}
        base_path = progress_path or Path(QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppDataLocation)) / 'progress-v3.json'
        for mode in (REAL, SIMULATION):
            ready = mode_available(mode.key)
            group = QGroupBox(mode.title + (' · 주력 학습 모드' if mode.key == 'real' else ' · 기존 보조 모드'))
            content = QVBoxLayout(group)
            text = mode.description + ('\n준비 중: 검증된 내장 런타임이 이 배포본에 없습니다.' if not ready else '')
            description = QLabel(text)
            description.setWordWrap(True)
            description.setMinimumHeight(description.fontMetrics().lineSpacing() * (text.count('\n') + 3))
            content.addWidget(description)
            progress = QLabel(saved_progress_summary(base_path, mode.key))
            progress.setWordWrap(True)
            progress.setToolTip(str(mode_progress_path(base_path, mode.key)))
            content.addWidget(progress)
            self.progress_labels[mode.key] = progress
            button = QPushButton(mode.title + ' 시작' if ready else '준비 중 · 내장 런타임 필요')
            button.setEnabled(ready)
            button.clicked.connect(lambda checked=False, key=mode.key: self.select_mode(key))
            self.buttons[mode.key] = button
            content.addWidget(button)
            layout.addWidget(group)
        note = QLabel('기존 완료 기록은 시뮬레이션 진도로 유지합니다. 실제 모드 진도는 별도로 관리합니다. 기억노트는 공유합니다.')
        note.setWordWrap(True)
        layout.addWidget(note)
        python_button = QPushButton('Python·데이터 학습 시작 · 실제 CPython')
        python_button.clicked.connect(lambda: self.select_mode('python'))
        layout.addWidget(python_button)
        from conda_teaching.engine import available as conda_available
        conda_button=QPushButton('Conda 환경 관리 · 실제 Linux guest' if conda_available() else 'Conda 환경 관리 · 검증된 런타임 준비 필요')
        conda_button.setEnabled(conda_available())
        conda_button.clicked.connect(lambda:self.select_mode('conda'))
        layout.addWidget(conda_button)
        close = QPushButton('닫기')
        close.clicked.connect(self.reject)
        layout.addWidget(close)

    def select_mode(self, mode):
        if mode=='conda':
            from conda_teaching.engine import available as conda_available
            if not conda_available():return
        elif mode != 'python' and not mode_available(mode):
            return
        self.selected_mode = mode
        self.accept()
