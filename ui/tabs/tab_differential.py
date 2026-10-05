"""
Tab 2: Differential (Parent / Child) VHDX Manager Tab.
"""

import os
import time
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QGroupBox, QMessageBox, QTableWidget, QTableWidgetItem,
    QHeaderView, QAbstractItemView, QFrame
)
from PySide6.QtCore import Qt, Signal
from ui.widgets.path_picker import PathPickerWidget
from ui.workers.diff_worker import DifferentialWorker
from utils.disk_info import format_size
from utils.admin import is_admin


class TabDifferentialWidget(QWidget):
    log_requested = Signal(str, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.worker: DifferentialWorker = None
        self.known_child_disks = []

        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(14)

        # 1. 1-Click Child Generation Section
        group_create = QGroupBox("1. Rapid 1-Click Child (Differential) VHDX Creation")
        g_c_layout = QVBoxLayout(group_create)
        g_c_layout.setSpacing(10)

        desc = QLabel(
            "Differential disks inherit all operating system files from the Master (Parent) VHDX "
            "and only store changes. Creating a child disk takes <b>less than 2 seconds</b>."
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #94a3b8; font-size: 12px;")
        g_c_layout.addWidget(desc)

        # Parent VHDX Picker
        parent_lbl = QLabel("Parent Master VHDX:")
        parent_lbl.setStyleSheet("font-weight: 600; color: #cbd5e1;")
        g_c_layout.addWidget(parent_lbl)

        self.parent_picker = PathPickerWidget(
            mode="open_file",
            file_filter="Virtual Hard Disk (*.vhdx)",
            placeholder="Select existing Master (Parent) .vhdx file..."
        )
        self.parent_picker.path_changed.connect(self._on_parent_changed)
        g_c_layout.addWidget(self.parent_picker)

        # Child VHDX Picker
        child_lbl = QLabel("Child (Differential) VHDX Destination:")
        child_lbl.setStyleSheet("font-weight: 600; color: #cbd5e1;")
        g_c_layout.addWidget(child_lbl)

        self.child_picker = PathPickerWidget(
            mode="save_file",
            file_filter="Virtual Hard Disk (*.vhdx)",
            placeholder="Path for newly created Child differential .vhdx...",
            default_ext=".vhdx"
        )
        g_c_layout.addWidget(self.child_picker)

        # Action Button
        btn_layout = QHBoxLayout()
        self.create_diff_btn = QPushButton("Generate Child Differential VHDX (1-Click)")
        self.create_diff_btn.setObjectName("primaryBtn")
        self.create_diff_btn.setStyleSheet("font-size: 13px; padding: 8px 20px;")
        self.create_diff_btn.clicked.connect(self.create_child_disk)
        btn_layout.addWidget(self.create_diff_btn)

        g_c_layout.addLayout(btn_layout)
        layout.addWidget(group_create)

        # 2. Managed Differential Disks & Quick Reset
        group_manage = QGroupBox("2. Managed Differential Disks & Sandbox Reset")
        g_m_layout = QVBoxLayout(group_manage)
        g_m_layout.setSpacing(8)

        m_desc = QLabel(
            "Quickly discard changes and reset test environments by deleting the differential disk."
        )
        m_desc.setStyleSheet("color: #94a3b8; font-size: 12px;")
        g_m_layout.addWidget(m_desc)

        # Table of Differential Disks
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["Child VHDX", "Parent VHDX", "Size", "Created Date", "Action"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        g_m_layout.addWidget(self.table)

        # Table buttons
        tbl_btn_layout = QHBoxLayout()
        self.add_existing_btn = QPushButton("Add Existing Child Disk to List...")
        self.add_existing_btn.clicked.connect(self._add_existing_child)
        tbl_btn_layout.addWidget(self.add_existing_btn)

        tbl_btn_layout.addStretch()

        self.refresh_tbl_btn = QPushButton("Refresh List")
        self.refresh_tbl_btn.clicked.connect(self.refresh_table)
        tbl_btn_layout.addWidget(self.refresh_tbl_btn)

        g_m_layout.addLayout(tbl_btn_layout)
        layout.addWidget(group_manage)

    def _on_parent_changed(self, path: str):
        if path and os.path.isfile(path):
            base_dir = os.path.dirname(path)
            name_no_ext = os.path.splitext(os.path.basename(path))[0]
            
            # Suggest a non-conflicting child name
            idx = 1
            while True:
                candidate = os.path.join(base_dir, f"{name_no_ext}_Child_{idx}.vhdx")
                if not os.path.exists(candidate):
                    break
                idx += 1
            self.child_picker.setText(candidate)

    def create_child_disk(self):
        if not is_admin():
            QMessageBox.critical(
                self,
                "Administrator Rights Required",
                "Administrator privileges are required to create differential VHDX disks.\n\n"
                "Please close this application and restart it using 'Run as administrator'."
            )
            return

        parent = self.parent_picker.text()
        child = self.child_picker.text()

        if not parent or not os.path.isfile(parent):
            QMessageBox.warning(self, "Validation Error", "Please select a valid Parent Master VHDX file.")
            return

        if not child:
            QMessageBox.warning(self, "Validation Error", "Please specify a destination for the Child VHDX.")
            return

        if not child.lower().endswith(".vhdx"):
            child += ".vhdx"
            self.child_picker.setText(child)

        if os.path.exists(child):
            reply = QMessageBox.question(
                self, "File Exists",
                f"The child file '{child}' already exists.\nDo you want to overwrite it?",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply != QMessageBox.Yes:
                return
            try:
                os.remove(child)
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Could not remove existing file: {e}")
                return

        self.create_diff_btn.setEnabled(False)
        self.log_requested.emit(f"Creating differential disk: '{child}' linked to '{parent}'...", "INFO")

        self.worker = DifferentialWorker(parent_vhdx=parent, child_vhdx=child)
        self.worker.log_event.connect(self.log_requested.emit)
        self.worker.task_finished.connect(self._on_child_created)
        self.worker.start()

    def _on_child_created(self, success: bool, msg: str):
        self.create_diff_btn.setEnabled(True)
        if success:
            child_path = self.child_picker.text()
            parent_path = self.parent_picker.text()
            self._register_child_disk(child_path, parent_path)
            QMessageBox.information(
                self, "Success",
                f"Differential Child VHDX generated in 1-Click!\n\nLocation: {child_path}\n"
                f"You can now boot this child disk or deploy it to Ventoy."
            )
            # Update child picker for next generation
            self._on_parent_changed(parent_path)
        else:
            QMessageBox.critical(self, "Error", f"Failed to create differential disk:\n\n{msg}")

    def _register_child_disk(self, child_path: str, parent_path: str):
        norm_child = os.path.normpath(child_path)
        for item in self.known_child_disks:
            if item["child"] == norm_child:
                item["parent"] = parent_path
                self.refresh_table()
                return

        self.known_child_disks.append({
            "child": norm_child,
            "parent": parent_path,
            "added_time": time.time()
        })
        self.refresh_table()

    def _add_existing_child(self):
        picker = PathPickerWidget(
            mode="open_file",
            file_filter="Virtual Hard Disk (*.vhdx)",
            placeholder="Select child .vhdx..."
        )
        picker.browse()
        selected = picker.text()
        if selected and os.path.isfile(selected):
            self._register_child_disk(selected, "Linked Master")

    def refresh_table(self):
        self.table.setRowCount(0)
        valid_items = []

        for idx, item in enumerate(self.known_child_disks):
            child_path = item["child"]
            parent_path = item["parent"]

            if not os.path.exists(child_path):
                continue
            valid_items.append(item)

            row = self.table.rowCount()
            self.table.insertRow(row)

            # Child path item
            c_item = QTableWidgetItem(os.path.basename(child_path))
            c_item.setToolTip(child_path)
            self.table.setItem(row, 0, c_item)

            # Parent path item
            p_item = QTableWidgetItem(os.path.basename(parent_path) if parent_path else "Unknown")
            p_item.setToolTip(parent_path)
            self.table.setItem(row, 1, p_item)

            # Size
            try:
                sz = os.path.getsize(child_path)
                sz_str = format_size(sz)
            except Exception:
                sz_str = "Unknown"
            self.table.setItem(row, 2, QTableWidgetItem(sz_str))

            # Date
            try:
                mtime = os.path.getmtime(child_path)
                d_str = time.strftime("%Y-%m-%d %H:%M", time.localtime(mtime))
            except Exception:
                d_str = "-"
            self.table.setItem(row, 3, QTableWidgetItem(d_str))

            # Action: Delete / Reset Button
            action_widget = QWidget()
            a_layout = QHBoxLayout(action_widget)
            a_layout.setContentsMargins(2, 2, 2, 2)
            a_layout.setSpacing(4)

            open_btn = QPushButton("Open Folder")
            open_btn.setStyleSheet("padding: 2px 6px; font-size: 11px;")
            open_btn.clicked.connect(lambda _, p=child_path: os.startfile(os.path.dirname(p)))
            a_layout.addWidget(open_btn)

            del_btn = QPushButton("Reset / Delete")
            del_btn.setObjectName("dangerBtn")
            del_btn.setStyleSheet("padding: 2px 8px; font-size: 11px;")
            del_btn.clicked.connect(lambda _, p=child_path: self._delete_child_disk(p))
            a_layout.addWidget(del_btn)

            self.table.setCellWidget(row, 4, action_widget)

        self.known_child_disks = valid_items

    def _delete_child_disk(self, file_path: str):
        reply = QMessageBox.question(
            self, "Confirm Sandbox Reset",
            f"Are you sure you want to delete this differential disk?\n\n{file_path}\n\n"
            "This will reset your test environment back to the clean Master state.",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
                    self.log_requested.emit(f"Deleted differential disk: {file_path}", "SUCCESS")
                self.refresh_table()
                QMessageBox.information(self, "Reset Complete", "Differential disk deleted. Environment reset!")
            except Exception as e:
                self.log_requested.emit(f"Failed to delete disk: {e}", "ERROR")
                QMessageBox.critical(self, "Error", f"Failed to delete file: {e}")
