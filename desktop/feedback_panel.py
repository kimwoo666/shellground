"""Native grading tab with readable, compact multi-column checks."""
from html import escape
from PySide6.QtGui import QTextOption
from PySide6.QtWidgets import QTextBrowser


class FeedbackPanel(QTextBrowser):
    def __init__(self):
        super().__init__()
        self.setReadOnly(True)
        self.setOpenExternalLinks(False)
        self.setAccessibleName('채점 결과와 안내')
        option = self.document().defaultTextOption()
        option.setWrapMode(QTextOption.WrapMode.WrapAtWordBoundaryOrAnywhere)
        self.document().setDefaultTextOption(option)
        self._checks = None
        self._summary = ''
        self._columns = None
        self.dark_theme = False

    def set_dark_theme(self, dark):
        if self.dark_theme != dark:
            self.dark_theme = dark
            self._columns = None
            self._render()

    def setText(self, text):
        self._checks = None
        self.setPlainText(text)

    def text(self):
        return self.toPlainText()

    def set_results(self, summary, checks):
        self._summary = summary
        self._checks = [dict(item) for item in checks]
        self._columns = None
        self._render()

    def _render(self):
        width = max(100, self.viewport().width())
        if self._checks is not None:
            count = len(self._checks)
            columns = 3 if count > 10 and width >= 900 else 2 if count >= 5 and width >= 650 else 1
            if self._columns != columns:
                cells = []
                for index, item in enumerate(self._checks):
                    mark = '통과' if item['passed'] else '미완료'
                    color = ('#91dda8' if item['passed'] else '#ffab96') if self.dark_theme else ('#226443' if item['passed'] else '#a33520')
                    cells.append(f'<td width="{100 // columns}%"><span style="color:{color}"><b>{index + 1}. {mark}</b></span>: {escape(str(item["label"]))}</td>')
                rows = ['<tr>' + ''.join(cells[i:i + columns]) + '</tr>' for i in range(0, len(cells), columns)]
                self.setHtml('<b>' + escape(self._summary) + '</b><table width="100%" cellspacing="3" cellpadding="1">' + ''.join(rows) + '</table>')
                self._columns = columns

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._render()
