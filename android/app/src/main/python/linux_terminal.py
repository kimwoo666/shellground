"""Bounded VT display adapter for native Android; never executes shell code.

The existing pyte parser consumes bytes from the real Linux PTY. History browsing
uses a separate viewport, so background output cannot pull the reader downward.
"""
import base64
import codecs
import json
import pyte


class Screen(pyte.HistoryScreen):
    def __init__(self, columns, lines, replies):
        self.replies = replies
        self.serial = 0
        self.epoch = 0
        super().__init__(columns, lines, history=1000)

    def _reset_history(self):
        super()._reset_history()
        self.serial = 0
        self.epoch += 1

    def index(self):
        bottom = self.margins.bottom if self.margins else self.lines - 1
        if self.cursor.y == bottom: self.serial += 1
        super().index()

    def write_process_input(self, data):
        if sum(len(item) for item in self.replies) < 4096:
            self.replies.append(data)


class Terminal:
    def __init__(self, columns=80, lines=24):
        self.replies = []
        self.screen = Screen(80, 24, self.replies)
        self.stream = pyte.ByteStream(self.screen)
        self.view_top = None
        self.transcript = ''
        self.decoder = codecs.getincrementaldecoder('utf-8')('replace')
        self.resize(columns, lines)

    def resize(self, columns, lines):
        columns, lines = int(columns), int(lines)
        if not 10 <= columns <= 240 or not 4 <= lines <= 80:
            raise ValueError('터미널 크기가 지원 범위를 벗어났습니다.')
        self.screen.resize(lines=lines, columns=columns)

    def feed(self, encoded):
        if len(encoded) > 350000: raise ValueError('터미널 출력 묶음이 너무 큽니다.')
        data = base64.b64decode(encoded, validate=True)
        self.transcript = (self.transcript + self.decoder.decode(data))[-262144:]
        epoch = self.screen.epoch
        self.stream.feed(data)
        if epoch != self.screen.epoch: self.view_top = None

    def scroll(self, delta):
        first, live = self.bounds()
        current = live if self.view_top is None else self.view_top
        position = max(first, min(live, current + int(delta)))
        self.view_top = None if position == live else position

    def live(self):
        self.view_top = None

    def bounds(self):
        live = self.screen.serial
        return max(0, live-len(self.screen.history.top)), live

    def _rows(self):
        return list(self.screen.history.top) + [self.screen.buffer[y] for y in range(self.screen.lines)]

    def text(self):
        return '\n'.join(''.join(row[x].data for x in range(self.screen.columns)).rstrip()
                         for row in self._rows())

    def output(self):
        """Actual PTY output for grading, independent of display/history clears."""
        return self.transcript

    def frame(self):
        first, live = self.bounds()
        top = live if self.view_top is None else max(first, min(live, self.view_top))
        if self.view_top is not None: self.view_top = top
        rows = self._rows()[top-first:top-first+self.screen.lines]
        rendered = []
        for row in rows:
            spans = []
            # Keep explicit columns for wide glyph continuation cells.
            for x in range(self.screen.columns):
                cell = row[x]
                if cell.data:
                    spans.append([x, cell.data, cell.fg, cell.bg,
                                  cell.bold, cell.reverse, cell.underscore])
            rendered.append(spans)
        response = {'columns': self.screen.columns, 'lines': self.screen.lines,
            'rows': rendered, 'top': top, 'first': first, 'live': live,
            'cursor': [self.screen.cursor.x, self.screen.cursor.y,
                       not self.screen.cursor.hidden and top == live],
            'reply': base64.b64encode(''.join(self.replies).encode()).decode()}
        self.replies.clear()
        return json.dumps(response, ensure_ascii=False)
