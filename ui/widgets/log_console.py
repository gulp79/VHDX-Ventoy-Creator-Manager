"""
Colorized real-time log console widget for system command monitoring.
"""

import time
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPlainTextEdit,
    QPushButton, QLabel, QCheckBox, QFileDialog, QApplication
)
from PySide6.QtGui import QTextCursor, QColor, QTextCharFormat, QFont
from PySide6.QtCore import Qt, Slot


class LogConsoleWidget(QWidget):
    """
    Expandable and rich log console for displaying command execution details in real time.
    """
    def __init__(self, parent=None):
        super().__init__(parent)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 4, 0, 0)
        layout.setSpacing(6)

        # Header Bar
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)

        self.title_label = QLabel("SYSTEM CONSOLE & REAL-TIME LOGS")
        self.title_label.setStyleSheet("font-weight: bold; color: #94a3b8; font-size: 11px;")
        header_layout.addWidget(self.title_label)

        header_layout.addStretch()

        self.autoscroll_cb = QCheckBox("Auto-scroll")
        self.autoscroll_cb.setChecked(True)
        self.autoscroll_cb.setStyleSheet("color: #94a3b8; font-size: 11px;")
        header_layout.addWidget(self.autoscroll_cb)

        self.copy_btn = QPushButton("Copy All")
        self.copy_btn.setStyleSheet("padding: 3px 10px; font-size: 11px;")
        self.copy_btn.clicked.connect(self.copy_all)
        header_layout.addWidget(self.copy_btn)

        self.save_btn = QPushButton("Save Log...")
        self.save_btn.setStyleSheet("padding: 3px 10px; font-size: 11px;")
        self.save_btn.clicked.connect(self.save_to_file)
        header_layout.addWidget(self.save_btn)

        self.clear_btn = QPushButton("Clear")
        self.clear_btn.setStyleSheet("padding: 3px 10px; font-size: 11px;")
        self.clear_btn.clicked.connect(self.clear_log)
        header_layout.addWidget(self.clear_btn)

        layout.addLayout(header_layout)

        # Plain Text Edit Console
        self.text_edit = QPlainTextEdit()
        self.text_edit.setObjectName("logConsole")
        self.text_edit.setReadOnly(True)
        self.text_edit.setMaximumBlockCount(5000)
        layout.addWidget(self.text_edit)

        # Color Formats
        self.formats = {
            "INFO": self._make_format("#94a3b8"),
            "SUCCESS": self._make_format("#34d399", bold=True),
            "WARNING": self._make_format("#fbbf24", bold=True),
            "ERROR": self._make_format("#f87171", bold=True),
            "CMD": self._make_format("#38bdf8", bold=True),
            "RAW": self._make_format("#a7f3d0")
        }

    def _make_format(self, hex_color: str, bold: bool = False) -> QTextCharFormat:
        fmt = QTextCharFormat()
        fmt.setForeground(QColor(hex_color))
        if bold:
            fmt.setFontWeight(QFont.Bold)
        return fmt

    @Slot(str, str)
    def append_log(self, text: str, level: str = "INFO"):
        """
        Append a log line with optional timestamp and styling.
        Levels: INFO, SUCCESS, WARNING, ERROR, CMD, RAW
        """
        if not text:
            return

        level_upper = level.upper()
        fmt = self.formats.get(level_upper, self.formats["RAW"])

        cursor = self.text_edit.textCursor()
        cursor.movePosition(QTextCursor.End)

        if level_upper != "RAW":
            t_str = time.strftime("[%H:%M:%S] ")
            tag = f"[{level_upper}] "
            
            # Write timestamp
            cursor.insertText(t_str, self.formats["INFO"])
            # Write level tag
            cursor.insertText(tag, fmt)

        cursor.insertText(text + "\n", fmt)

        if self.autoscroll_cb.isChecked():
            self.text_edit.moveCursor(QTextCursor.End)

    @Slot()
    def clear_log(self):
        self.text_edit.clear()

    @Slot()
    def copy_all(self):
        QApplication.clipboard().setText(self.text_edit.toPlainText())

    @Slot()
    def save_to_file(self):
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Log Output", "vhdx_log.txt", "Text Files (*.txt);;All Files (*.*)"
        )
        if file_path:
            try:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(self.text_edit.toPlainText())
            except Exception as e:
                self.append_log(f"Failed to save log: {e}", "ERROR")
