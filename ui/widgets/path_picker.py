"""
Reusable file/directory picker widget with Drag & Drop support.
"""

import os
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QLineEdit, QPushButton, QFileDialog
)
from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QDragEnterEvent, QDropEvent


class PathPickerWidget(QWidget):
    """
    Path selector widget with browse dialog and drag-and-drop capability.
    """
    path_changed = Signal(str)

    def __init__(
        self,
        mode: str = "open_file",  # "open_file", "save_file", "directory"
        file_filter: str = "All Files (*.*)",
        placeholder: str = "Select path...",
        default_ext: str = "",
        parent=None
    ):
        super().__init__(parent)
        self.mode = mode
        self.file_filter = file_filter
        self.default_ext = default_ext
        self.setAcceptDrops(True)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        self.line_edit = QLineEdit()
        self.line_edit.setPlaceholderText(placeholder)
        self.line_edit.textChanged.connect(self._on_text_changed)
        layout.addWidget(self.line_edit, stretch=1)

        self.browse_btn = QPushButton("Browse...")
        self.browse_btn.clicked.connect(self.browse)
        layout.addWidget(self.browse_btn)

    def text(self) -> str:
        return self.line_edit.text().strip()

    def setText(self, text: str):
        self.line_edit.setText(text)

    def _on_text_changed(self, text: str):
        self.path_changed.emit(text.strip())

    def browse(self):
        start_dir = os.path.dirname(self.text()) if self.text() else ""

        if self.mode == "open_file":
            path, _ = QFileDialog.getOpenFileName(
                self, "Select File", start_dir, self.file_filter
            )
        elif self.mode == "save_file":
            path, _ = QFileDialog.getSaveFileName(
                self, "Save File", start_dir, self.file_filter
            )
        elif self.mode == "directory":
            path = QFileDialog.getExistingDirectory(
                self, "Select Directory", start_dir
            )
        else:
            path = ""

        if path:
            # Fix slashes on Windows
            norm_path = os.path.normpath(path)
            self.setText(norm_path)

    # Drag and Drop handlers
    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            if urls and urls[0].isLocalFile():
                event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent):
        urls = event.mimeData().urls()
        if urls:
            local_path = urls[0].toLocalFile()
            if os.name == "nt":
                local_path = os.path.normpath(local_path)
            self.setText(local_path)
            event.acceptProposedAction()
