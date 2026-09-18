"""Native, non-executing layout review. Never opens a VM or saves progress."""
import argparse
import json
from pathlib import Path
import tempfile

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QComboBox, QWidget, QHBoxLayout, QLabel, QPushButton
from layout_presets import PRESETS, DEFAULT_LAYOUT
from native_app import Window, create_application

QUESTION = '''시작 위치: /home/learner/desk/team5

목표: 릴리스 자료를 점검하고 인계 보고서를 준비하세요.
1. ../../data/release9853 폴더의 숨김 항목을 포함한 상세 목록을 하위 폴더까지 조사하세요.
2. guide.txt와 docs/read me.txt 두 파일의 내용을 확인하세요. 원본은 유지하세요.
3. 목록은 현재 작업 폴더의 release inventory.txt에, 두 문서의 내용은 notes.txt에 순서대로 저장하세요.
4. 작업 중 만들어진 draft.tmp만 삭제하고, 다른 파일과 디렉터리는 보존하세요.'''

OUTPUT = '''\x1b[33m[배치 비교용 출력 — 명령을 실행한 결과가 아닙니다]\x1b[0m
learner@lab:~/desk/team5$ pwd
/home/learner/desk/team5
learner@lab:~/desk/team5$ ls -la
total 20
drwxr-xr-x 2 learner learner 4096 Sep 16 10:00 .
drwxr-xr-x 3 learner learner 4096 Sep 16 10:00 ..
-rw-r--r-- 1 learner learner   28 Sep 16 10:00 .session
-rw-r--r-- 1 learner learner   17 Sep 16 10:00 draft.tmp
-rw-r--r-- 1 learner learner  142 Sep 16 10:00 checklist.txt
learner@lab:~/desk/team5$ '''


class NoExecution:
    """Only permits constructing an idle window; has no command implementation."""
    name = None

    def tick(self): pass


class Preview:
    def __init__(self, initial=DEFAULT_LAYOUT):
        self.app, self.ui, self.mono = create_application()
        self.temporary = tempfile.TemporaryDirectory(prefix='shellground-layout-preview-')
        self.window = None
        self.show(initial)

    def show(self, key):
        old = self.window
        # Construct the real-mode UI, but never start an engine/terminal session.
        w = Window(self.ui, self.mono, Path(self.temporary.name) / 'unused.json', mode='real', layout=key, engine=NoExecution())
        w.simulation_timer.stop()
        w._shutdown_ready = True
        w.index, w.phase, w.practice_number = 17, 'practice', 2
        w.refresh_course()
        w.steps.setText('③ 활용 2/2 · 이전 지식 조합 — 배치 비교 전용')
        w.heading.setText('리눅스 18 · 릴리스 자료 조사와 보고서 정리')
        w.instructions.setPlainText(QUESTION)
        w.feedback.setText('미완료: 숨김 항목을 포함한 재귀 목록 보고서\n미완료: 두 문서 내용과 작업 폴더 정리')
        for button in w.findChildren(QPushButton): button.setEnabled(False)
        w.course.setEnabled(False)
        w.topic_tabs.setEnabled(False)
        for action, button in w.shortcut_actions: action.setEnabled(False)
        for action in w.menuBar().actions(): action.setEnabled(False)
        bar = QWidget()
        row = QHBoxLayout(bar)
        row.setContentsMargins(2, 0, 2, 0)
        row.addWidget(QLabel('배치 비교'))
        combo = QComboBox()
        combo.setAccessibleName('비교할 배치 시안')
        for name, preset in PRESETS.items(): combo.addItem(preset.title, name)
        combo.setCurrentIndex(tuple(PRESETS).index(key))
        row.addWidget(combo)
        w.centralWidget().layout().itemAt(0).layout().insertWidget(1, bar)
        w.setWindowTitle('Shellground 배치 확인 — ' + PRESETS[key].title + ' · 기본 A 채택')
        w.statusBar().showMessage('비교 전용 · 명령 실행/VM 기동/진도 저장 없음 · 경계선을 끌어 크기 조절 가능 · 기본 A 채택')
        if old: w.setGeometry(old.geometry())
        w.show()
        self.app.processEvents()
        w.terminal.feed(OUTPUT.replace('\n', '\r\n').encode())
        combo.currentIndexChanged.connect(lambda index: self.show(combo.itemData(index)))
        self.window = w
        if old:
            old.close()
            old.deleteLater()

    def render(self, destination):
        destination = Path(destination)
        destination.mkdir(parents=True, exist_ok=True)
        measurements = {}
        for key in PRESETS:
            self.show(key)
            w = self.window
            w.resize(1220, 880)
            for _ in range(3): self.app.processEvents()
            w.grab().save(str(destination / f'layout-{key}.png'))
            measurements[key] = {name: [widget.width(), widget.height()] for name, widget in (
                ('window', w), ('question', w.instructions), ('terminal', w.terminal), ('sidebar', w.course), ('feedback', w.feedback))}
        # Generated inspection data, not application configuration.
        (destination / 'measurements.json').write_text(json.dumps(measurements, ensure_ascii=False, indent=2), encoding='utf-8')
        return measurements


def run_preview(key=DEFAULT_LAYOUT):
    preview = Preview(key)
    result = preview.app.exec()
    preview.temporary.cleanup()
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--render', type=Path)
    args = parser.parse_args()
    if args.render:
        preview = Preview()
        print(json.dumps(preview.render(args.render), ensure_ascii=False))
        preview.window.close()
        preview.temporary.cleanup()
    else:
        raise SystemExit(run_preview())
