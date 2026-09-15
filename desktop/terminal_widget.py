"""Native VT screen; all keystrokes are handled by the Linux PTY."""
import base64
import json
import threading
import pyte
from PySide6.QtCore import Qt, Signal, QThread, QRect
from PySide6.QtGui import QColor, QFont, QFontMetrics, QPainter, QGuiApplication
from PySide6.QtWidgets import QWidget, QMenu


class TerminalReader(QThread):
    output = Signal(bytes)
    ended = Signal(str)

    def __init__(self, process):
        super().__init__()
        self.process = process
        self.pending = threading.BoundedSemaphore(8)
        self.stop_requested = threading.Event()

    def run(self):
        try:
            for line in self.process.stdout:
                if self.stop_requested.is_set(): return
                message = json.loads(line)
                if 'output' in message:
                    while not self.pending.acquire(timeout=.1):
                        if self.stop_requested.is_set(): return
                    self.output.emit(base64.b64decode(message['output']))
            error = self.process.stderr.read().decode('utf-8', errors='replace')
            self.ended.emit(error or '셸이 종료되었습니다. 문제 다시 시작으로 실습을 다시 열 수 있습니다.')
        except (ValueError, OSError, json.JSONDecodeError):
            pass


class Screen(pyte.HistoryScreen):
    def __init__(self, *args, sender, **kwargs):
        self.sender = sender
        self.history_serial = 0
        self.history_epoch = 0
        super().__init__(*args, **kwargs)

    def _reset_history(self):
        super()._reset_history()
        self.history_serial = 0
        self.history_epoch += 1

    def index(self):
        bottom = self.margins.bottom if self.margins else self.lines - 1
        if self.cursor.y == bottom:
            self.history_serial += 1
        super().index()

    def write_process_input(self, data):
        self.sender(data.encode('utf-8'))


COLORS = dict(black='#18201e', red='#f08080', green='#8acf98', brown='#dcc58b',
              blue='#82aaff', magenta='#c9a0dc', cyan='#82d8d8', white='#e4e9e5',
              brightblack='#778580', brightred='#ff9797', brightgreen='#a6efb4',
              brightbrown='#ffdf9f', brightblue='#a8c8ff', brightmagenta='#e5bcfa',
              brightcyan='#a9ffff', brightwhite='#ffffff')


class TerminalWidget(QWidget):
    input_bytes = Signal(bytes)
    resized = Signal(int, int)

    def __init__(self, family='monospace'):
        super().__init__()
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setAttribute(Qt.WidgetAttribute.WA_InputMethodEnabled)
        self.setMinimumSize(420, 220)
        self.font_ = QFont(family, 12)
        self.font_.setStyleHint(QFont.StyleHint.Monospace)
        metrics = QFontMetrics(self.font_)
        self.cell_w = max(1, metrics.horizontalAdvance('M'))
        self.cell_h, self.ascent = metrics.height() + 2, metrics.ascent()
        self.screen = Screen(100, 24, history=3000, sender=self.input_bytes.emit)
        self.stream = pyte.ByteStream(self.screen)
        # Browse history without paging the live parser screen. HistoryScreen
        # pagination otherwise jumps to the bottom on every incoming VT event.
        self.view_top = None
        self.selection_start = self.selection_end = None
        self.connected = False
        self.setAccessibleName('Linux·Docker 학습 터미널')

    def reset(self):
        self.screen.reset()
        self.stream = pyte.ByteStream(self.screen)
        self.view_top = None
        self.selection_start = self.selection_end = None
        self.update()

    def feed(self, data):
        epoch = self.screen.history_epoch
        self.stream.feed(data)
        if epoch != self.screen.history_epoch:
            self.show_live()
        self.clamp_view()
        self.update()

    def show_live(self):
        self.view_top = None
        self.selection_start = self.selection_end = None
        self.update()

    def clamp_view(self):
        if self.view_top is None:
            return
        oldest = self.screen.history_serial - len(self.screen.history.top)
        top = max(oldest, min(self.view_top, self.screen.history_serial))
        if top != self.view_top:
            self.selection_start = self.selection_end = None
        self.view_top = top if top < self.screen.history_serial else None

    def scroll_history(self, lines):
        top = self.screen.history_serial if self.view_top is None else self.view_top
        self.view_top = top - lines
        self.clamp_view()
        self.selection_start = self.selection_end = None
        self.update()

    def visible_lines(self):
        self.clamp_view()
        if self.view_top is None:
            return [self.screen.buffer[row] for row in range(self.screen.lines)]
        history = list(self.screen.history.top)
        oldest = self.screen.history_serial - len(history)
        rows = history + [self.screen.buffer[row] for row in range(self.screen.lines)]
        start = self.view_top - oldest
        return rows[start:start + self.screen.lines]

    def resizeEvent(self, event):
        rows, cols = max(2, (self.height() - 16) // self.cell_h), max(10, (self.width() - 16) // self.cell_w)
        self.screen.resize(lines=rows, columns=cols)
        self.clamp_view()
        self.resized.emit(rows, cols)
        super().resizeEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor('#111815'))
        selected = sorted((self.selection_start, self.selection_end)) if self.selection_start is not None and self.selection_end is not None else None
        for row, line in enumerate(self.visible_lines()):
            for col in range(self.screen.columns):
                char = line.get(col, self.screen.default_char)
                if not char.data: continue
                fg = QColor(COLORS.get(char.fg, '#' + char.fg if len(char.fg) == 6 else '#dce6de'))
                bg = QColor(COLORS.get(char.bg, '#' + char.bg if len(char.bg) == 6 else '#111815'))
                if char.reverse: fg, bg = bg, fg
                if selected and selected[0] <= (row, col) <= selected[1]: bg = QColor('#3e6254')
                x, y = 8 + col * self.cell_w, 8 + row * self.cell_h
                wide = col + 1 < self.screen.columns and line.get(col + 1, self.screen.default_char).data == ''
                painter.fillRect(x, y, self.cell_w * (2 if wide else 1), self.cell_h, bg)
                font = QFont(self.font_)
                font.setBold(char.bold)
                font.setUnderline(char.underscore)
                font.setItalic(char.italics)
                painter.setFont(font)
                painter.setPen(fg)
                painter.drawText(x, y + self.ascent + 1, char.data)
        if self.view_top is None and self.hasFocus() and self.connected and not self.screen.cursor.hidden:
            painter.setPen(QColor('#e7cd8a'))
            painter.drawRect(8 + self.screen.cursor.x * self.cell_w, 8 + self.screen.cursor.y * self.cell_h, self.cell_w - 1, self.cell_h - 1)

    def focusInEvent(self, event):
        self.update()
        super().focusInEvent(event)

    def focusOutEvent(self, event):
        self.update()
        super().focusOutEvent(event)

    def focusNextPrevChild(self, next):
        return False

    def keyPressEvent(self, event):
        key, mods = event.key(), event.modifiers()
        ctrl, shift = bool(mods & Qt.KeyboardModifier.ControlModifier), bool(mods & Qt.KeyboardModifier.ShiftModifier)
        if ctrl and shift and key == Qt.Key.Key_C: self.copy_selection(); return
        if ctrl and shift and key == Qt.Key.Key_V: self.paste(); return
        if shift and key in (Qt.Key.Key_PageUp, Qt.Key.Key_PageDown):
            page = max(1, self.screen.lines // 2)
            self.scroll_history(page if key == Qt.Key.Key_PageUp else -page)
            event.accept(); return
        if shift and key == Qt.Key.Key_End:
            self.show_live()
            event.accept(); return
        if not self.connected: return
        mapping = {
            Qt.Key.Key_Return: b'\r', Qt.Key.Key_Enter: b'\r', Qt.Key.Key_Backspace: b'\x7f',
            Qt.Key.Key_Tab: b'\t', Qt.Key.Key_Backtab: b'\x1b[Z', Qt.Key.Key_Escape: b'\x1b',
            Qt.Key.Key_Up: b'\x1b[A', Qt.Key.Key_Down: b'\x1b[B', Qt.Key.Key_Right: b'\x1b[C',
            Qt.Key.Key_Left: b'\x1b[D', Qt.Key.Key_Home: b'\x1b[H', Qt.Key.Key_End: b'\x1b[F',
            Qt.Key.Key_Delete: b'\x1b[3~', Qt.Key.Key_Insert: b'\x1b[2~',
            Qt.Key.Key_PageUp: b'\x1b[5~', Qt.Key.Key_PageDown: b'\x1b[6~',
        }
        if ctrl and Qt.Key.Key_A <= key <= Qt.Key.Key_Z: data = bytes([key - Qt.Key.Key_A + 1])
        elif ctrl and key == Qt.Key.Key_Space: data = b'\x00'
        else: data = mapping.get(key, event.text().encode('utf-8'))
        if mods & Qt.KeyboardModifier.AltModifier and data and not data.startswith(b'\x1b'): data = b'\x1b' + data
        if data:
            self.show_live()
            self.input_bytes.emit(data)
        event.accept()

    def inputMethodEvent(self, event):
        if self.connected and event.commitString():
            self.show_live()
            self.input_bytes.emit(event.commitString().encode('utf-8'))
        event.accept()

    def inputMethodQuery(self, query):
        if query == Qt.InputMethodQuery.ImCursorRectangle:
            return QRect(8 + self.screen.cursor.x * self.cell_w, 8 + self.screen.cursor.y * self.cell_h, self.cell_w, self.cell_h)
        return super().inputMethodQuery(query)

    def cell_at(self, event):
        return (max(0, min(self.screen.lines - 1, int(event.position().y() - 8) // self.cell_h)),
                max(0, min(self.screen.columns - 1, int(event.position().x() - 8) // self.cell_w)))

    def mousePressEvent(self, event):
        self.setFocus()
        if event.button() == Qt.MouseButton.LeftButton:
            self.selection_start = self.selection_end = self.cell_at(event)
            self.update()

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.MouseButton.LeftButton:
            self.selection_end = self.cell_at(event)
            self.update()

    def copy_selection(self):
        if self.selection_start is None or self.selection_end is None: return
        start, end = sorted((self.selection_start, self.selection_end))
        visible = self.visible_lines()
        lines = []
        for row in range(start[0], end[0] + 1):
            left, right = start[1] if row == start[0] else 0, end[1] if row == end[0] else self.screen.columns - 1
            if row >= len(visible): break
            lines.append(''.join(visible[row].get(col, self.screen.default_char).data for col in range(left, right + 1)).rstrip())
        QGuiApplication.clipboard().setText('\n'.join(lines))

    def paste(self):
        if self.connected:
            data = QGuiApplication.clipboard().text().replace('\r\n', '\n').encode('utf-8')
            if not data: return
            if 2004 << 5 in self.screen.mode: data = b'\x1b[200~' + data + b'\x1b[201~'
            self.show_live()
            self.input_bytes.emit(data)

    def contextMenuEvent(self, event):
        menu = QMenu(self)
        menu.addAction('복사 (Ctrl+Shift+C)', self.copy_selection)
        menu.addAction('붙여넣기 (Ctrl+Shift+V)', self.paste)
        menu.addAction('최신 출력으로 (Shift+End)', self.show_live)
        menu.exec(event.globalPos())

    def wheelEvent(self, event):
        delta = event.angleDelta().y() or event.pixelDelta().y()
        if delta:
            self.scroll_history(3 if delta > 0 else -3)
        event.accept()
