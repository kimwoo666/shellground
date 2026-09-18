"""Native layout presets. A was selected by the user on 2026-09-16."""
from dataclasses import dataclass

DEFAULT_LAYOUT = 'a'


@dataclass(frozen=True)
class LayoutPreset:
    title: str
    sidebar: int
    question: int
    terminal: int


PRESETS = {
    'current': LayoutPreset('기존 배치', 270, 235, 250),
    'a': LayoutPreset('A · 균형형', 225, 280, 360),
    'b': LayoutPreset('B · 터미널 우선', 225, 245, 395),
    'c': LayoutPreset('C · 문제 우선', 225, 330, 310),
}
