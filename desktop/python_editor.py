"""Small native code editor: indentation and actual Python token highlighting."""
import re
from PySide6.QtCore import Qt, QEvent, Signal
from PySide6.QtGui import QSyntaxHighlighter, QTextCharFormat, QColor, QTextCursor
from PySide6.QtWidgets import QPlainTextEdit


class PythonHighlighter(QSyntaxHighlighter):
    def highlightBlock(self, text):
        rules = [(r'\b(?:def|class|return|for|in|if|elif|else|while|break|continue|try|except|finally|raise|with|as|import|from|pass|and|or|not|is|lambda|True|False|None)\b','#bbacff'),
                 (r'\b\d+(?:\.\d+)?\b','#f2c78a'),
                 (r'''(?:"(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*')''','#9ad5a7'),
                 (r'#.*','#899b93')]
        for pattern,color in rules:
            style=QTextCharFormat(); style.setForeground(QColor(color))
            for match in re.finditer(pattern,text): self.setFormat(match.start(),len(match.group()),style)


class PythonEditor(QPlainTextEdit):
    execute_requested = Signal()

    def __init__(self,parent=None):
        super().__init__(parent)
        self.highlighter=PythonHighlighter(self.document())
        self.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)

    @staticmethod
    def execution_key(event):
        modifiers = event.modifiers() & ~Qt.KeyboardModifier.KeypadModifier
        return event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter) and modifiers == Qt.KeyboardModifier.ShiftModifier

    def event(self, event):
        if event.type() == QEvent.Type.ShortcutOverride and self.execution_key(event):
            event.accept()
            return True
        return super().event(event)

    def keyPressEvent(self,event):
        if self.execution_key(event):
            if not event.isAutoRepeat():
                self.execute_requested.emit()
            event.accept()
            return
        cursor=self.textCursor()
        if event.key()==Qt.Key.Key_Tab and not event.modifiers():
            cursor.insertText('    '); self.setTextCursor(cursor); return
        if event.key() in (Qt.Key.Key_Return,Qt.Key.Key_Enter) and not event.modifiers():
            line=cursor.block().text()[:cursor.positionInBlock()]
            indent=re.match(r'\s*',line).group()
            if line.rstrip().endswith(':'): indent+='    '
            cursor.insertText('\n'+indent); self.setTextCursor(cursor); return
        super().keyPressEvent(event)
