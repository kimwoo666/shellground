#!/usr/bin/env python3
"""Archived 2.x simulation UI; not used by Shellground 3."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import random
import sys

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")
from gi.repository import Gdk, Gio, GLib, Gtk  # noqa: E402

try:
    from curriculum import LEVELS, LESSONS, Exercise, review_pool, validate_curriculum
except ImportError:  # Allows `python -m desktop.shellground` during development.
    from .curriculum import LEVELS, LESSONS, Exercise, review_pool, validate_curriculum


APP_NAME = "Shellground"
APP_VERSION = "2.1.0"
APP_ID = "com.openai.shellground"

APP_CSS = """
* {
  font-family: "Noto Sans CJK KR", "Noto Sans KR", sans-serif;
  font-size: 14px;
}
window { background: #dedad0; color: #25231f; }
.topbar { background: #302e29; border-bottom: 1px solid #171612; padding: 12px 18px; min-height: 66px; }
.logo {
  background: #c95732; color: white; border: 2px solid #87351f;
  padding: 9px 11px; font-family: "Noto Sans Mono CJK KR", monospace;
  font-size: 19px; font-weight: 800;
}
.brand { color: white; font-size: 18px; font-weight: 800; letter-spacing: 1px; }
.brand-sub { color: #aaa69b; font-family: "Noto Sans Mono CJK KR", monospace; font-size: 10px; }
.header-level { color: #e9e4d9; font-weight: 700; }
.header-progress { color: #d8d3c9; font-family: "Noto Sans Mono CJK KR", monospace; font-size: 12px; }
progressbar trough { background: #b9b5ac; border: 1px solid #77736b; min-height: 12px; }
progressbar progress { background: #c95732; min-height: 12px; }
.sidebar { background: #ebe7de; border-right: 1px solid #8f8a80; padding: 12px 8px; }
.side-title { color: #25231f; font-size: 16px; font-weight: 800; }
.muted { color: #706d64; font-size: 11px; }
.level-row { background: #d4d0c6; color: #403d37; border-top: 1px solid #aaa59b; padding: 7px 9px; font-weight: 800; }
.lesson-row { background: #ebe7de; color: #514e47; padding: 7px 10px; border-bottom: 1px solid #dbd6cc; }
.lesson-row:hover { background: #f7f4ed; }
.lesson-row.current { background: #1d5d4e; color: white; }
.lesson-row.done { color: #1d5d4e; font-weight: 700; }
.lesson-row.locked { color: #aaa69d; }
.command-mini { font-family: "Noto Sans Mono CJK KR", monospace; font-weight: 700; }
.random-box { background: #d3cfc5; border: 1px solid #9b978d; padding: 10px; }
.workspace { background: #f7f4ed; padding: 16px 22px 0; }
.step { background: #c9c5bb; color: #5d5a54; border: 1px solid #aaa69d; padding: 7px 12px; font-size: 12px; }
.step.active { background: #1d5d4e; color: white; border-color: #113b31; font-weight: 800; }
.step-line { background: #aaa69d; min-height: 1px; }
.command-title { color: #87351f; font-family: "Noto Sans Mono CJK KR", monospace; font-size: 34px; font-weight: 900; }
.lesson-title { color: #25231f; font-size: 23px; font-weight: 800; }
.phase { color: #706d64; font-size: 12px; }
.description { color: #35322d; font-size: 15px; }
.detail-frame { background: #ebe7dc; border: 1px solid #aaa59b; padding: 11px 13px; }
.detail-head { color: #87351f; font-weight: 800; }
.detail-code { color: #1d5d4e; font-family: "Noto Sans Mono CJK KR", monospace; font-weight: 800; }
.detail-normal { color: #35322d; }
.detail-muted { color: #706d64; font-size: 12px; }
.terminal-frame { background: #0b100e; border: 2px solid #080d0b; }
.terminal-header { background: #28312d; border-bottom: 1px solid #788079; padding: 6px 10px; }
.terminal-caption { color: #b5c0ba; font-size: 11px; }
.terminal-safe { color: #77c895; font-family: "Noto Sans Mono CJK KR", monospace; font-size: 11px; font-weight: 800; }
.terminal-view { background: #111815; color: #d7dfd9; caret-color: #ffcf7d; padding: 10px; font-family: "Noto Sans Mono CJK KR", monospace; font-size: 13px; }
.prompt { background: #111815; color: #78ce98; font-family: "Noto Sans Mono CJK KR", monospace; font-weight: 800; padding-left: 12px; }
.command-entry { background: #f8f8f6; color: #151411; font-family: "Noto Sans Mono CJK KR", monospace; font-size: 14px; }
.footer { background: #e6e1d7; border-top: 1px solid #aaa59b; padding: 8px 12px; }
.score { color: #37342f; font-family: "Noto Sans Mono CJK KR", monospace; font-weight: 800; }
button { background: #efebe2; color: #27251f; border: 1px solid #969188; padding: 7px 12px; }
button:hover { background: #faf8f3; }
button.suggested-action { background: #1d5d4e; color: white; border-color: #113b31; font-weight: 800; }
button.suggested-action:hover { background: #287561; }
button:disabled { opacity: .5; }
"""


def add_css(widget: Gtk.Widget, *names: str) -> Gtk.Widget:
    for name in names:
        widget.add_css_class(name)
    return widget


def label(text: str = "", css: str | None = None, *, xalign: float = 0.0, wrap: bool = False) -> Gtk.Label:
    widget = Gtk.Label(label=text, xalign=xalign)
    if css:
        widget.add_css_class(css)
    if wrap:
        widget.set_wrap(True)
        widget.set_wrap_mode(2)
    return widget


class ShellgroundWindow(Gtk.ApplicationWindow):
    def __init__(self, application: Gtk.Application) -> None:
        super().__init__(application=application, title="Shellground — 리눅스 명령어 연습")
        self.set_default_size(1120, 760)
        self.set_size_request(920, 630)

        self.progress_path = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share")) / "shellground" / "progress.json"
        self.completed: list[str] = []
        self.lesson_index = 0
        self.phase = "learn"
        self.task_index = 0
        self.current_exercise: Exercise | None = None
        self.review_queue: list[Exercise] = []
        self.review_goal = 3
        self.review_score = 0
        self.random_session_score = 0
        self.attempts = 0
        self.command_history: list[str] = []
        self.history_index = -1
        self.answer_correct = False
        self._row_by_lesson: dict[int, Gtk.ListBoxRow] = {}
        self._load_progress()
        self._build_ui()
        self._install_shortcuts()
        self._refresh_course_list()
        self.show_lesson(min(self.lesson_index, len(LESSONS) - 1))

    @property
    def lesson(self):
        return LESSONS[self.lesson_index]

    def _build_ui(self) -> None:
        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.set_child(root)

        header = add_css(Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10), "topbar")
        root.append(header)
        header.append(label(">_", "logo"))
        brand_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        brand_box.set_hexpand(True)
        brand_box.append(label("SHELLGROUND", "brand"))
        brand_box.append(label("LINUX COMMAND TRAINER", "brand-sub"))
        header.append(brand_box)
        self.level_header = label("", "header-level", xalign=1.0)
        self.level_header.set_margin_end(24)
        header.append(self.level_header)
        progress_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        progress_box.set_size_request(200, -1)
        self.progress_text = label("", "header-progress", xalign=1.0)
        self.progress_bar = Gtk.ProgressBar()
        progress_box.append(self.progress_text)
        progress_box.append(self.progress_bar)
        header.append(progress_box)

        body = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        body.set_vexpand(True)
        root.append(body)

        sidebar = add_css(Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=7), "sidebar")
        sidebar.set_size_request(255, -1)
        body.append(sidebar)
        sidebar.append(label("학습 단계", "side-title"))
        sidebar.append(label("위에서부터 차례로 잠금이 해제됩니다.", "muted"))

        course_scroll = Gtk.ScrolledWindow()
        course_scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        course_scroll.set_vexpand(True)
        self.course_list = Gtk.ListBox()
        self.course_list.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.course_list.connect("row-activated", self._on_course_row_activated)
        course_scroll.set_child(self.course_list)
        sidebar.append(course_scroll)

        random_box = add_css(Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4), "random-box")
        random_box.append(label("누적 올랜덤", "side-title"))
        random_box.append(label("지금까지 배운 모든 명령어를\n순서 없이 다시 풉니다.", "muted"))
        self.random_button = Gtk.Button(label="올랜덤 시작")
        self.random_button.connect("clicked", lambda _button: self.start_free_random())
        random_box.append(self.random_button)
        sidebar.append(random_box)

        workspace = add_css(Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8), "workspace")
        workspace.set_hexpand(True)
        body.append(workspace)

        steps = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=7)
        workspace.append(steps)
        self.step_labels: list[Gtk.Label] = []
        for index, text in enumerate(("1  명령어 설명", "2  예시 따라 하기", "3  활용 문제", "4  누적 랜덤")):
            step = label(text, "step", xalign=0.5)
            self.step_labels.append(step)
            steps.append(step)
            if index < 3:
                line = add_css(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL), "step-line")
                line.set_hexpand(True)
                steps.append(line)

        title_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=13)
        title_row.set_margin_top(5)
        workspace.append(title_row)
        self.command_label = label("", "command-title")
        title_row.append(self.command_label)
        title_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        title_box.set_hexpand(True)
        self.title_label = label("", "lesson-title")
        self.phase_label = label("", "phase")
        title_box.append(self.title_label)
        title_box.append(self.phase_label)
        title_row.append(title_box)
        self.hint_button = Gtk.Button(label="힌트 (F1)")
        self.hint_button.connect("clicked", lambda _button: self.show_hint())
        title_row.append(self.hint_button)

        self.description_label = label("", "description", wrap=True)
        self.description_label.set_margin_top(3)
        workspace.append(self.description_label)

        self.detail_frame = add_css(Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=3), "detail-frame")
        workspace.append(self.detail_frame)

        terminal = add_css(Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0), "terminal-frame")
        terminal.set_vexpand(True)
        terminal.set_margin_top(5)
        workspace.append(terminal)
        terminal_header = add_css(Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6), "terminal-header")
        terminal_header.append(label("●", None))
        terminal_header.get_first_child().set_markup("<span foreground='#da5b45'>●</span>")
        dot_yellow = label("●")
        dot_yellow.set_markup("<span foreground='#d4a53d'>●</span>")
        terminal_header.append(dot_yellow)
        dot_green = label("●")
        dot_green.set_markup("<span foreground='#5c9b66'>●</span>")
        terminal_header.append(dot_green)
        caption = label("연습 터미널 — 실제 파일은 변경되지 않습니다", "terminal-caption")
        caption.set_hexpand(True)
        terminal_header.append(caption)
        terminal_header.append(label("SAFE MODE", "terminal-safe", xalign=1.0))
        terminal.append(terminal_header)

        terminal_scroll = Gtk.ScrolledWindow()
        terminal_scroll.set_vexpand(True)
        self.terminal_view = add_css(Gtk.TextView(), "terminal-view")
        self.terminal_view.set_editable(False)
        self.terminal_view.set_cursor_visible(False)
        self.terminal_view.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        self.terminal_buffer = self.terminal_view.get_buffer()
        self.terminal_buffer.create_tag("prompt", foreground="#78ce98", weight=700)
        self.terminal_buffer.create_tag("command", foreground="#ffe6aa")
        self.terminal_buffer.create_tag("output", foreground="#bdc9c3")
        self.terminal_buffer.create_tag("success", foreground="#b9e5c8", background="#18352b", weight=700)
        self.terminal_buffer.create_tag("error", foreground="#ff9a7e", weight=700)
        self.terminal_buffer.create_tag("info", foreground="#edc878")
        terminal_scroll.set_child(self.terminal_view)
        terminal.append(terminal_scroll)

        entry_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        entry_row.set_margin_top(7)
        entry_row.set_margin_bottom(7)
        entry_row.append(label("learner@lab:~/practice$", "prompt"))
        self.command_entry = add_css(Gtk.Entry(), "command-entry")
        self.command_entry.set_hexpand(True)
        self.command_entry.connect("activate", lambda _entry: self.execute_command())
        key_controller = Gtk.EventControllerKey()
        key_controller.connect("key-pressed", self._on_entry_key)
        self.command_entry.add_controller(key_controller)
        entry_row.append(self.command_entry)
        self.run_button = add_css(Gtk.Button(label="실행"), "suggested-action")
        self.run_button.connect("clicked", lambda _button: self.execute_command())
        entry_row.append(self.run_button)
        terminal.append(entry_row)

        footer = add_css(Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10), "footer")
        root.append(footer)
        self.status_label = label("Enter: 실행   ↑↓: 이전 명령   Ctrl+L: 터미널 지우기", "muted")
        self.status_label.set_hexpand(True)
        footer.append(self.status_label)
        self.score_label = label("", "score", xalign=1.0)
        footer.append(self.score_label)
        self.next_button = add_css(Gtk.Button(label="학습 시작"), "suggested-action")
        self.next_button.connect("clicked", lambda _button: self.advance())
        footer.append(self.next_button)

    def _install_shortcuts(self) -> None:
        controller = Gtk.ShortcutController()
        controller.add_shortcut(Gtk.Shortcut.new(Gtk.ShortcutTrigger.parse_string("<Control>l"), Gtk.CallbackAction.new(lambda *_: self._shortcut_clear())))
        controller.add_shortcut(Gtk.Shortcut.new(Gtk.ShortcutTrigger.parse_string("<Control>r"), Gtk.CallbackAction.new(lambda *_: self._shortcut_random())))
        controller.add_shortcut(Gtk.Shortcut.new(Gtk.ShortcutTrigger.parse_string("F1"), Gtk.CallbackAction.new(lambda *_: self._shortcut_hint())))
        self.add_controller(controller)

    def _shortcut_clear(self) -> bool:
        self.clear_terminal()
        return True

    def _shortcut_random(self) -> bool:
        self.start_free_random()
        return True

    def _shortcut_hint(self) -> bool:
        self.show_hint()
        return True

    def _load_progress(self) -> None:
        try:
            data = json.loads(self.progress_path.read_text(encoding="utf-8"))
            valid_keys = {lesson.key for lesson in LESSONS}
            self.completed = [key for key in data.get("completed", []) if key in valid_keys]
            self.lesson_index = min(int(data.get("lesson_index", len(self.completed))), len(LESSONS) - 1)
        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            self.completed = []
            self.lesson_index = 0

    def _save_progress(self) -> None:
        try:
            self.progress_path.parent.mkdir(parents=True, exist_ok=True)
            temporary = self.progress_path.with_suffix(".tmp")
            temporary.write_text(json.dumps({"completed": self.completed, "lesson_index": self.lesson_index}, ensure_ascii=False, indent=2), encoding="utf-8")
            temporary.replace(self.progress_path)
        except OSError:
            self.status_label.set_text("경고: 학습 기록을 저장할 수 없습니다.")

    def _clear_box(self, box: Gtk.Box) -> None:
        child = box.get_first_child()
        while child is not None:
            next_child = child.get_next_sibling()
            box.remove(child)
            child = next_child

    def _refresh_course_list(self) -> None:
        child = self.course_list.get_first_child()
        while child is not None:
            next_child = child.get_next_sibling()
            self.course_list.remove(child)
            child = next_child
        self._row_by_lesson.clear()
        completed_set = set(self.completed)
        unlocked_limit = min(len(self.completed), len(LESSONS) - 1)
        for level, (name, subtitle) in LEVELS.items():
            heading = Gtk.ListBoxRow()
            heading.set_activatable(False)
            heading.set_selectable(False)
            heading.set_child(label(f"난이도 {level}  {name} — {subtitle}", "level-row"))
            self.course_list.append(heading)
            for index, lesson in enumerate(LESSONS):
                if lesson.level != level:
                    continue
                done = lesson.key in completed_set
                locked = index > unlocked_limit
                marker = "✓" if done else "▶" if not locked else "▣"
                row = Gtk.ListBoxRow()
                row.lesson_index = index
                row.set_activatable(not locked)
                row.set_selectable(not locked)
                content = label(f" {marker}   {lesson.command:<9} {lesson.title}", "lesson-row")
                content.add_css_class("command-mini")
                if index == self.lesson_index and self.phase != "random":
                    content.add_css_class("current")
                elif done:
                    content.add_css_class("done")
                elif locked:
                    content.add_css_class("locked")
                row.set_child(content)
                self.course_list.append(row)
                self._row_by_lesson[index] = row
        current_row = self._row_by_lesson.get(self.lesson_index)
        if current_row and current_row.get_selectable():
            self.course_list.select_row(current_row)
        self.random_button.set_sensitive(bool(self.completed))
        self.progress_bar.set_fraction(len(self.completed) / len(LESSONS))
        self.progress_text.set_text(f"완료 {len(self.completed)} / {len(LESSONS)}")

    def _on_course_row_activated(self, _listbox: Gtk.ListBox, row: Gtk.ListBoxRow) -> None:
        index = getattr(row, "lesson_index", None)
        if index is not None and index <= len(self.completed) and index != self.lesson_index:
            self.show_lesson(index, force=True)

    def _set_steps(self, active: int) -> None:
        for index, step in enumerate(self.step_labels):
            if index == active:
                step.add_css_class("active")
            else:
                step.remove_css_class("active")

    def _set_detail(self, entries: list[tuple[str, str]]) -> None:
        self._clear_box(self.detail_frame)
        for text, style in entries:
            item = label(text, f"detail-{style}", wrap=True)
            self.detail_frame.append(item)

    def _update_header(self) -> None:
        level_name, level_subtitle = LEVELS[self.lesson.level]
        self.level_header.set_text(f"난이도 {self.lesson.level} · {level_name}\n{level_subtitle}")
        self.command_label.set_text(self.lesson.command)
        self.title_label.set_text(self.lesson.title)

    def show_lesson(self, index: int, force: bool = False) -> None:
        if index > len(self.completed) and not force:
            return
        self.lesson_index = index
        self.phase = "learn"
        self.task_index = 0
        self.current_exercise = None
        self.review_queue = []
        self.review_score = 0
        self.attempts = 0
        self.answer_correct = False
        self._update_header()
        self._set_steps(0)
        self.phase_label.set_text("먼저 뜻과 형식을 읽고, 준비되면 예시를 직접 입력합니다.")
        self.description_label.set_text(self.lesson.summary)
        entries: list[tuple[str, str]] = [("기본 형식", "head"), (f"$ {self.lesson.syntax}", "code"), ("자주 쓰는 옵션", "head")]
        for option, meaning in self.lesson.options:
            entries.append((f"{option:<10}  {meaning}", "normal"))
        entries.extend((("기억할 점", "head"), (self.lesson.tip, "muted")))
        self._set_detail(entries)
        self.clear_terminal()
        self.append_terminal(f"[{self.lesson.command}] 설명을 읽고 아래 '예시 시작' 버튼을 누르세요.\n", "info")
        self.command_entry.set_sensitive(False)
        self.run_button.set_sensitive(False)
        self.next_button.set_label("예시 시작  →")
        self.next_button.set_sensitive(True)
        self.score_label.set_text("설명 단계")
        self._refresh_course_list()
        self._save_progress()

    def start_examples(self) -> None:
        self.phase = "example"
        self.task_index = 0
        self._set_steps(1)
        self._load_current_task(self.lesson.examples[0])

    def start_practice(self) -> None:
        self.phase = "practice"
        self.task_index = 0
        self._set_steps(2)
        self._load_current_task(self.lesson.practice[0])

    def start_review(self) -> None:
        self.phase = "review"
        learned = [*self.completed]
        if self.lesson.key not in learned:
            learned.append(self.lesson.key)
        pool = review_pool(learned)
        self.review_goal = min(3, max(1, len(pool)))
        self.review_queue = random.sample(pool, self.review_goal) if len(pool) >= self.review_goal else random.choices(pool, k=self.review_goal)
        self.review_score = 0
        self.task_index = 0
        self._set_steps(3)
        self._load_current_task(self.review_queue[0])

    def start_free_random(self) -> None:
        if not self.completed:
            self.status_label.set_text("명령어를 하나 이상 완료하면 올랜덤 모드가 열립니다.")
            return
        self.phase = "random"
        self.random_session_score = 0
        self.review_queue = review_pool(self.completed)
        self._set_steps(3)
        self.command_label.set_text("RANDOM")
        self.title_label.set_text("누적 올랜덤 모드")
        self.level_header.set_text("복습 모드\n배운 명령어 전체")
        self._refresh_course_list()
        self._next_free_random()

    def _next_free_random(self) -> None:
        if not self.review_queue:
            return
        previous = self.current_exercise
        candidates = [item for item in self.review_queue if item is not previous] or self.review_queue
        self._load_current_task(random.choice(candidates))

    def _load_current_task(self, exercise: Exercise) -> None:
        self.current_exercise = exercise
        self.attempts = 0
        self.answer_correct = False
        phase_titles = {
            "example": "예시를 그대로 입력해 손에 익히세요.",
            "practice": "설명만 보고 알맞은 명령어를 완성하세요.",
            "review": "지금까지 배운 범위에서 무작위로 출제됩니다.",
            "random": "배운 모든 명령어가 순서 없이 계속 출제됩니다.",
        }
        self.phase_label.set_text(phase_titles[self.phase])
        self.description_label.set_text(exercise.prompt)
        entries: list[tuple[str, str]] = [("상황", "head"), (exercise.context, "normal")]
        if self.phase == "example":
            entries.extend((("따라 입력할 명령어", "head"), (f"$ {exercise.solution}", "code")))
        else:
            entries.extend((("입력 방법", "head"), ("아래 터미널 프롬프트에 명령어를 입력하고 Enter를 누르세요.", "muted")))
        self._set_detail(entries)
        self.clear_terminal()
        self.append_terminal(f"미션: {exercise.prompt}\n", "info")
        if self.phase == "example":
            self.append_terminal(f"따라 입력: {exercise.solution}\n", "output")
        self.command_entry.set_sensitive(True)
        self.run_button.set_sensitive(True)
        self.command_entry.set_text("")
        self.next_button.set_sensitive(False)
        self.next_button.set_label("정답을 입력하세요")
        self._update_score()
        GLib.idle_add(self.command_entry.grab_focus)

    def append_terminal(self, text: str, tag: str = "output") -> None:
        end = self.terminal_buffer.get_end_iter()
        self.terminal_buffer.insert_with_tags_by_name(end, text, tag)
        mark = self.terminal_buffer.create_mark(None, self.terminal_buffer.get_end_iter(), False)
        self.terminal_view.scroll_to_mark(mark, 0.0, True, 0.0, 1.0)

    def clear_terminal(self) -> None:
        self.terminal_buffer.set_text("")

    def execute_command(self) -> None:
        if self.current_exercise is None or self.answer_correct:
            return
        command = " ".join(self.command_entry.get_text().strip().split())
        if not command:
            self.command_entry.grab_focus()
            return
        self.command_history.append(command)
        self.history_index = -1
        self.append_terminal("learner@lab:~/practice$ ", "prompt")
        self.append_terminal(f"{command}\n", "command")
        self.command_entry.set_text("")
        if command == "clear":
            self.clear_terminal()
            return
        if command == "help":
            self.append_terminal("도움말: 미션에 맞는 명령어를 입력하세요. F1은 힌트, ↑↓는 입력 기록입니다.\n", "info")
            return
        if self.current_exercise.accepts(command):
            for line in self.current_exercise.output:
                self.append_terminal(f"{line}\n", "output")
            self.append_terminal("✓ 정답입니다. 명령의 형태와 결과를 함께 기억하세요.\n", "success")
            self.answer_correct = True
            self.command_entry.set_sensitive(False)
            self.run_button.set_sensitive(False)
            self.next_button.set_sensitive(True)
            self.next_button.set_label(self._next_button_text())
            if self.phase == "random":
                self.random_session_score += 1
            elif self.phase == "review":
                self.review_score += 1
            self._update_score()
        else:
            self.attempts += 1
            self.append_terminal("✗ 아직 맞지 않습니다. 명령어, 옵션, 인자 순서를 확인하세요.\n", "error")
            if self.attempts == 2:
                self.append_terminal(f"힌트: {self.current_exercise.hint}\n", "info")
            elif self.attempts >= 3:
                self.append_terminal(f"정답 예시: {self.current_exercise.solution}\n한 번 그대로 입력해 보세요.\n", "info")
            self.command_entry.grab_focus()

    def _on_entry_key(self, _controller, keyval, _keycode, _state) -> bool:
        if keyval == Gdk.KEY_Up and self.command_history:
            self.history_index = min(self.history_index + 1, len(self.command_history) - 1)
            self.command_entry.set_text(self.command_history[-1 - self.history_index])
            self.command_entry.set_position(-1)
            return True
        if keyval == Gdk.KEY_Down and self.history_index >= 0:
            self.history_index -= 1
            self.command_entry.set_text("" if self.history_index < 0 else self.command_history[-1 - self.history_index])
            self.command_entry.set_position(-1)
            return True
        return False

    def _next_button_text(self) -> str:
        if self.phase == "example":
            return "다음 예시  →" if self.task_index + 1 < len(self.lesson.examples) else "활용 문제 시작  →"
        if self.phase == "practice":
            return "다음 활용 문제  →" if self.task_index + 1 < len(self.lesson.practice) else "누적 랜덤 점검  →"
        if self.phase == "review":
            return "다음 랜덤 문제  →" if self.review_score < self.review_goal else "단계 완료 확인  →"
        if self.phase == "random":
            return "다음 랜덤 문제  →"
        if self.phase == "passed":
            return "다음 명령어  →" if self.lesson_index + 1 < len(LESSONS) else "전체 올랜덤 시작  →"
        return "계속"

    def advance(self) -> None:
        if self.phase == "learn":
            self.start_examples()
        elif self.phase == "example" and self.answer_correct:
            self.task_index += 1
            self._load_current_task(self.lesson.examples[self.task_index]) if self.task_index < len(self.lesson.examples) else self.start_practice()
        elif self.phase == "practice" and self.answer_correct:
            self.task_index += 1
            self._load_current_task(self.lesson.practice[self.task_index]) if self.task_index < len(self.lesson.practice) else self.start_review()
        elif self.phase == "review" and self.answer_correct:
            if self.review_score >= self.review_goal:
                self._finish_lesson()
            else:
                self.task_index += 1
                self._load_current_task(self.review_queue[self.task_index])
        elif self.phase == "random" and self.answer_correct:
            self._next_free_random()
        elif self.phase == "passed":
            self.show_lesson(self.lesson_index + 1) if self.lesson_index + 1 < len(LESSONS) else self.start_free_random()

    def _finish_lesson(self) -> None:
        if self.lesson.key not in self.completed:
            self.completed.append(self.lesson.key)
        self.phase = "passed"
        self.answer_correct = True
        self._save_progress()
        self._refresh_course_list()
        self._set_steps(3)
        self.phase_label.set_text("설명, 예시, 활용, 누적 랜덤 점검을 모두 통과했습니다.")
        self.description_label.set_text(f"'{self.lesson.command}' 명령어 학습 완료")
        self._set_detail([
            ("단계 통과", "head"),
            (f"{self.lesson.command} 명령어를 여러 상황에서 정확히 사용했습니다.", "normal"),
            ("다음 단계에서도 방금 배운 명령어가 누적 랜덤 문제에 다시 등장합니다.", "muted"),
        ])
        self.clear_terminal()
        self.append_terminal(f"★ {self.lesson.command} 단계 완료!\n", "success")
        self.append_terminal(f"전체 진도: {len(self.completed)} / {len(LESSONS)}\n", "output")
        self.command_entry.set_sensitive(False)
        self.run_button.set_sensitive(False)
        self.next_button.set_label(self._next_button_text())
        self.next_button.set_sensitive(True)
        self._update_score()

    def _update_score(self) -> None:
        if self.phase == "example":
            text = f"예시 {self.task_index + 1} / {len(self.lesson.examples)}"
        elif self.phase == "practice":
            text = f"활용 {self.task_index + 1} / {len(self.lesson.practice)}"
        elif self.phase == "review":
            text = f"누적 랜덤 {self.review_score} / {self.review_goal}"
        elif self.phase == "random":
            text = f"올랜덤 연속 정답 {self.random_session_score}"
        elif self.phase == "passed":
            text = "단계 완료"
        else:
            text = "설명 단계"
        self.score_label.set_text(text)

    def show_hint(self) -> None:
        text = self.current_exercise.hint if self.current_exercise else self.lesson.tip
        self.append_terminal(f"힌트: {text}\n", "info")
        if self.command_entry.get_sensitive():
            self.command_entry.grab_focus()


class ShellgroundApplication(Gtk.Application):
    def __init__(self) -> None:
        super().__init__(application_id=APP_ID, flags=Gio.ApplicationFlags.DEFAULT_FLAGS)

    def do_startup(self) -> None:
        Gtk.Application.do_startup(self)
        provider = Gtk.CssProvider()
        provider.load_from_string(APP_CSS)
        display = Gdk.Display.get_default()
        if display:
            Gtk.StyleContext.add_provider_for_display(display, provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

    def do_activate(self) -> None:
        window = self.props.active_window
        if not window:
            window = ShellgroundWindow(self)
        window.present()


def run_self_test() -> int:
    errors = validate_curriculum()
    if errors:
        for error in errors:
            print(f"FAIL: {error}")
        return 1
    total_exercises = sum(len(item.examples) + len(item.practice) for item in LESSONS)
    print(f"OK: {len(LESSONS)} lessons, {total_exercises} guided exercises, {len(review_pool(item.key for item in LESSONS))} all-random exercises")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Shellground native Linux command trainer")
    parser.add_argument("--self-test", action="store_true", help="validate curriculum without opening the GUI")
    parser.add_argument("--version", action="store_true", help="print version and exit")
    arguments = parser.parse_args()
    if arguments.version:
        print(f"{APP_NAME} {APP_VERSION}")
        return 0
    if arguments.self_test:
        return run_self_test()
    app = ShellgroundApplication()
    try:
        return app.run([sys.argv[0]])
    except KeyboardInterrupt:
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
