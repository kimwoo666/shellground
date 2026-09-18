"""Display preferences, independent of completion records and lab state."""
from dataclasses import asdict, dataclass
import json
from pathlib import Path

from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import (QCheckBox, QComboBox, QDialog, QDialogButtonBox,
                              QFormLayout, QGridLayout, QGroupBox, QLabel,
                              QSpinBox, QVBoxLayout)


COLOR_GROUPS = {
    'green': '초록 계열', 'blue': '파랑 계열', 'red': '빨강 계열',
    'yellow': '노랑 계열', 'magenta': '보라 계열', 'cyan': '청록 계열',
    'gray': '흑백·회색 계열', 'extended': '256색·RGB 확장색',
}


@dataclass(frozen=True)
class Settings:
    theme: str = 'light'
    terminal_theme: str = 'dark'
    terminal_colors: bool = True
    color_groups: tuple = tuple(COLOR_GROUPS)
    terminal_font_size: int = 12
    text_font_size: int = 11
    drag_autoscroll: bool = True

    @classmethod
    def from_dict(cls, data):
        defaults = cls()
        if not isinstance(data, dict): return defaults
        values = {}
        for key in ('theme', 'terminal_theme'):
            if data.get(key) in ('light', 'dark'): values[key] = data[key]
        for key in ('terminal_colors', 'drag_autoscroll'):
            if type(data.get(key)) is bool: values[key] = data[key]
        for key, low, high in (('terminal_font_size', 9, 24), ('text_font_size', 9, 20)):
            value = data.get(key)
            if type(value) is int: values[key] = max(low, min(high, value))
        groups = data.get('color_groups')
        if isinstance(groups, (list, tuple)) and all(isinstance(g, str) for g in groups):
            values['color_groups'] = tuple(g for g in COLOR_GROUPS if g in groups)
        return cls(**values)


def load_settings(path):
    try:
        return Settings.from_dict(json.loads(Path(path).read_text(encoding='utf-8')))
    except (OSError, ValueError, TypeError):
        return Settings()


def save_settings(path, settings):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps({'schema': 1, **asdict(settings)}, ensure_ascii=False, indent=2), encoding='utf-8')
    temporary.replace(path)


def theme_palette(theme):
    palette = QPalette()
    dark = theme == 'dark'
    colors = {
        'Window': '#25292e' if dark else '#f3f3f3',
        'WindowText': '#e7ebef' if dark else '#202428',
        'Base': '#191d22' if dark else '#ffffff',
        'AlternateBase': '#2d3239' if dark else '#eceff1',
        'Text': '#e7ebef' if dark else '#202428',
        'Button': '#353b43' if dark else '#e8eaec',
        'ButtonText': '#e7ebef' if dark else '#202428',
        'ToolTipBase': '#353b43' if dark else '#fffde7',
        'ToolTipText': '#ffffff' if dark else '#202428',
        'Highlight': '#346e8c' if dark else '#246c8d',
        'HighlightedText': '#ffffff',
        'Link': '#81c9f0' if dark else '#166285',
        'LinkVisited': '#c2aff3' if dark else '#68429a',
        'Light': '#515963' if dark else '#ffffff',
        'Midlight': '#424a54' if dark else '#e7e9eb',
        'Mid': '#292e35' if dark else '#b5bbc0',
        'Dark': '#101317' if dark else '#8c949c',
        'Shadow': '#080a0d' if dark else '#626c76',
        'PlaceholderText': '#aab3bd' if dark else '#69727a',
    }
    for role, color in colors.items():
        palette.setColor(getattr(QPalette.ColorRole, role), QColor(color))
    for role in ('WindowText', 'Text', 'ButtonText', 'HighlightedText'):
        palette.setColor(QPalette.ColorGroup.Disabled, getattr(QPalette.ColorRole, role),
                         QColor('#8d969f' if dark else '#78818a'))
    return palette


class SettingsDialog(QDialog):
    def __init__(self, settings, mono_family, parent=None):
        super().__init__(parent)
        from terminal_widget import TerminalWidget
        self.setWindowTitle('설정')
        self.resize(610, 700)
        layout = QVBoxLayout(self)
        intro = QLabel('표시 설정만 변경합니다. 완료 진도·실습 파일·채점에는 영향을 주지 않습니다.')
        intro.setWordWrap(True)
        layout.addWidget(intro)
        form = QFormLayout()
        self.theme = QComboBox()
        self.terminal_theme = QComboBox()
        for combo in (self.theme, self.terminal_theme):
            combo.addItem('라이트', 'light')
            combo.addItem('다크', 'dark')
        self.terminal_font_size = QSpinBox()
        self.terminal_font_size.setRange(9, 24)
        self.terminal_font_size.setSuffix(' pt')
        self.text_font_size = QSpinBox()
        self.text_font_size.setRange(9, 20)
        self.text_font_size.setSuffix(' pt')
        form.addRow('프로그램 테마', self.theme)
        form.addRow('터미널 배경', self.terminal_theme)
        form.addRow('터미널 글자 크기', self.terminal_font_size)
        form.addRow('문제·설명 글자 크기', self.text_font_size)
        layout.addLayout(form)
        self.terminal_colors = QCheckBox('터미널 색상 사용 (ANSI)')
        layout.addWidget(self.terminal_colors)
        self.color_box = QGroupBox('사용할 색상 계열')
        grid = QGridLayout(self.color_box)
        self.color_checks = {}
        for i, (key, label) in enumerate(COLOR_GROUPS.items()):
            check = QCheckBox(label)
            self.color_checks[key] = check
            grid.addWidget(check, i // 2, i % 2)
        layout.addWidget(self.color_box)
        note = QLabel('끄는 색상은 기본 글자·배경색으로 표시됩니다. 색상 계열 기준이며,\n'
                      '특정 명령이나 파일 종류만 구분하는 설정은 아닙니다. 편집기의 반전 표시는 유지됩니다.')
        note.setWordWrap(True)
        layout.addWidget(note)
        self.drag_autoscroll = QCheckBox('텍스트를 드래그할 때 위·아래 가장자리에서 자동 스크롤')
        layout.addWidget(self.drag_autoscroll)
        layout.addWidget(QLabel('터미널 미리보기'))
        self.preview = TerminalWidget(mono_family)
        self.preview.setMinimumSize(420, 125)
        self.preview.setMaximumHeight(145)
        self.preview.setEnabled(False)
        layout.addWidget(self.preview)
        self.buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save |
                                       QDialogButtonBox.StandardButton.Cancel |
                                       QDialogButtonBox.StandardButton.RestoreDefaults)
        self.buttons.button(QDialogButtonBox.StandardButton.Save).setText('저장')
        self.buttons.button(QDialogButtonBox.StandardButton.Cancel).setText('취소')
        self.buttons.button(QDialogButtonBox.StandardButton.RestoreDefaults).setText('설정 기본값')
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        self.buttons.button(QDialogButtonBox.StandardButton.RestoreDefaults).clicked.connect(lambda: self.set_values(Settings()))
        layout.addWidget(self.buttons)
        self.set_values(settings)
        for combo in (self.theme, self.terminal_theme): combo.currentIndexChanged.connect(self.update_preview)
        for spin in (self.terminal_font_size, self.text_font_size): spin.valueChanged.connect(self.update_preview)
        for check in [self.terminal_colors, self.drag_autoscroll, *self.color_checks.values()]:
            check.toggled.connect(self.update_preview)

    def set_values(self, settings):
        # Loading defaults must not repeatedly resize/rerender the preview.
        widgets = [self.theme, self.terminal_theme, self.terminal_font_size,
                   self.text_font_size, self.terminal_colors, self.drag_autoscroll,
                   *self.color_checks.values()]
        for widget in widgets: widget.blockSignals(True)
        self.theme.setCurrentIndex(self.theme.findData(settings.theme))
        self.terminal_theme.setCurrentIndex(self.terminal_theme.findData(settings.terminal_theme))
        self.terminal_font_size.setValue(settings.terminal_font_size)
        self.text_font_size.setValue(settings.text_font_size)
        self.terminal_colors.setChecked(settings.terminal_colors)
        self.drag_autoscroll.setChecked(settings.drag_autoscroll)
        for key, check in self.color_checks.items(): check.setChecked(key in settings.color_groups)
        for widget in widgets: widget.blockSignals(False)
        self.update_preview()

    def values(self):
        return Settings(theme=self.theme.currentData(), terminal_theme=self.terminal_theme.currentData(),
                        terminal_colors=self.terminal_colors.isChecked(),
                        color_groups=tuple(k for k, c in self.color_checks.items() if c.isChecked()),
                        terminal_font_size=self.terminal_font_size.value(), text_font_size=self.text_font_size.value(),
                        drag_autoscroll=self.drag_autoscroll.isChecked())

    def update_preview(self):
        settings = self.values()
        self.setPalette(theme_palette(settings.theme))
        self.color_box.setEnabled(settings.terminal_colors)
        self.preview.apply_settings(settings)
        self.preview.reset()
        self.preview.feed(('\x1b[32mlearner@lab\x1b[0m:~/practice$ ls\r\n'
                           '\x1b[34mdocs/\x1b[0m  \x1b[32msetup.sh\x1b[0m  \x1b[31mbundle.tar.gz\x1b[0m\r\n'
                           '\x1b[33myellow\x1b[0m \x1b[35mmagenta\x1b[0m \x1b[36mcyan\x1b[0m 한글\r\n'
                           '\x1b[7m^O 저장   ^X 종료\x1b[0m').encode())
