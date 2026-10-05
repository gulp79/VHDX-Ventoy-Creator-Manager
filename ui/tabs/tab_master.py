"""
Tab 1: Master VHDX Creation Tab.
"""

import os
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel,
    QPushButton, QComboBox, QSlider, QSpinBox, QProgressBar,
    QGroupBox, QMessageBox, QRadioButton, QButtonGroup, QScrollArea, QFrame
)
from PySide6.QtCore import Qt, Signal, QThread
from ui.widgets.path_picker import PathPickerWidget
from ui.workers.master_worker import MasterCreationWorker
from utils.constants import (
    DEFAULT_VHDX_SIZE_GB, MIN_VHDX_SIZE_GB, MAX_VHDX_SIZE_GB,
    DEFAULT_VOLUME_LABEL
)
from utils.disk_info import get_disk_space_info, format_size, validate_space_headroom
from core.dism_engine import get_wim_info
from core.vhd_engine import mount_iso, unmount_iso, find_wim_or_esd_in_drive
from utils.admin import is_admin


class WimInspectionWorker(QThread):
    """Background inspection of ISO/WIM/ESD to avoid freezing the UI when reading image index."""
    inspection_finished = Signal(list, str)  # (editions_list, error_msg)

    def __init__(self, file_path: str, parent=None):
        super().__init__(parent)
        self.file_path = file_path

    def run(self):
        ext = os.path.splitext(self.file_path)[1].lower()
        if ext == ".iso":
            mounted_drive, msg = mount_iso(self.file_path)
            if not mounted_drive:
                self.inspection_finished.emit([], f"Could not mount ISO: {msg}")
                return
            try:
                wim_file = find_wim_or_esd_in_drive(mounted_drive)
                if not wim_file:
                    self.inspection_finished.emit([], f"No install.wim/esd found inside ISO ({mounted_drive}:\\)")
                    return
                editions, msg = get_wim_info(wim_file)
                self.inspection_finished.emit(editions, "" if editions else msg)
            finally:
                unmount_iso(self.file_path)
        elif ext in [".wim", ".esd"]:
            editions, msg = get_wim_info(self.file_path)
            self.inspection_finished.emit(editions, "" if editions else msg)
        else:
            self.inspection_finished.emit([], "Unsupported file format. Please select an ISO, WIM, or ESD file.")


class TabMasterWidget(QWidget):
    log_requested = Signal(str, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.worker: MasterCreationWorker = None
        self.inspect_worker: WimInspectionWorker = None
        self.editions_data = []

        self._build_ui()

    def _build_ui(self):
        # Outer layout with scroll area to support smaller screens
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(4, 4, 4, 4)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(14)

        # 1. Source Image Group
        group_source = QGroupBox("1. Windows Source Image (ISO / WIM / ESD)")
        g_src_layout = QVBoxLayout(group_source)
        g_src_layout.setSpacing(8)

        self.source_picker = PathPickerWidget(
            mode="open_file",
            file_filter="Windows Images (*.iso *.wim *.esd);;ISO Image (*.iso);;WIM Image (*.wim);;ESD Image (*.esd)",
            placeholder="Select Windows Installation ISO, install.wim, or install.esd..."
        )
        self.source_picker.path_changed.connect(self._on_source_path_changed)
        g_src_layout.addWidget(self.source_picker)

        # Edition selector
        ed_layout = QHBoxLayout()
        ed_label = QLabel("Windows Edition Index:")
        ed_label.setStyleSheet("font-weight: 600; color: #cbd5e1;")
        ed_layout.addWidget(ed_label)

        self.edition_combo = QComboBox()
        self.edition_combo.addItem("Select source image first...")
        self.edition_combo.setEnabled(False)
        self.edition_combo.currentIndexChanged.connect(self._on_edition_changed)
        ed_layout.addWidget(self.edition_combo, stretch=1)

        self.refresh_ed_btn = QPushButton("Scan Editions")
        self.refresh_ed_btn.clicked.connect(self._scan_source_editions)
        self.refresh_ed_btn.setEnabled(False)
        ed_layout.addWidget(self.refresh_ed_btn)

        g_src_layout.addLayout(ed_layout)
        layout.addWidget(group_source)

        # 2. Target VHDX & Configuration Group
        group_target = QGroupBox("2. Target VHDX Configuration")
        g_tgt_layout = QVBoxLayout(group_target)
        g_tgt_layout.setSpacing(10)

        # Target Path Picker
        tgt_path_label = QLabel("Destination VHDX Path:")
        tgt_path_label.setStyleSheet("font-weight: 600; color: #cbd5e1;")
        g_tgt_layout.addWidget(tgt_path_label)

        self.target_picker = PathPickerWidget(
            mode="save_file",
            file_filter="Virtual Hard Disk (*.vhdx)",
            placeholder="Choose destination path for the Master .vhdx file...",
            default_ext=".vhdx"
        )
        self.target_picker.path_changed.connect(self._on_target_path_changed)
        g_tgt_layout.addWidget(self.target_picker)

        # Free space display
        self.space_info_label = QLabel("Free space: Select destination drive")
        self.space_info_label.setStyleSheet("color: #94a3b8; font-size: 12px;")
        g_tgt_layout.addWidget(self.space_info_label)

        # Size slider & spinbox
        size_layout = QHBoxLayout()
        size_label = QLabel("Max Virtual Size (GB):")
        size_label.setStyleSheet("font-weight: 600; color: #cbd5e1;")
        size_layout.addWidget(size_label)

        self.size_slider = QSlider(Qt.Horizontal)
        self.size_slider.setRange(MIN_VHDX_SIZE_GB, MAX_VHDX_SIZE_GB)
        self.size_slider.setValue(DEFAULT_VHDX_SIZE_GB)
        self.size_slider.valueChanged.connect(self._on_slider_changed)
        size_layout.addWidget(self.size_slider, stretch=1)

        self.size_spinbox = QSpinBox()
        self.size_spinbox.setRange(MIN_VHDX_SIZE_GB, MAX_VHDX_SIZE_GB)
        self.size_spinbox.setValue(DEFAULT_VHDX_SIZE_GB)
        self.size_spinbox.setSuffix(" GB")
        self.size_spinbox.valueChanged.connect(self._on_spinbox_changed)
        size_layout.addWidget(self.size_spinbox)

        g_tgt_layout.addLayout(size_layout)

        # VHDX Type (Expandable vs Fixed)
        type_layout = QHBoxLayout()
        type_label = QLabel("Disk Allocation Type:")
        type_label.setStyleSheet("font-weight: 600; color: #cbd5e1;")
        type_layout.addWidget(type_label)

        self.radio_dynamic = QRadioButton("Dynamic / Expandable (Recommended - grows as used)")
        self.radio_dynamic.setChecked(True)
        self.radio_fixed = QRadioButton("Fixed Size (Pre-allocates full space)")

        self.type_group = QButtonGroup(self)
        self.type_group.addButton(self.radio_dynamic)
        self.type_group.addButton(self.radio_fixed)

        type_layout.addWidget(self.radio_dynamic)
        type_layout.addWidget(self.radio_fixed)
        type_layout.addStretch()

        g_tgt_layout.addLayout(type_layout)
        layout.addWidget(group_target)

        # 3. Driver Injection (Optional)
        group_drivers = QGroupBox("3. Optional Drivers Injection")
        g_drv_layout = QVBoxLayout(group_drivers)
        g_drv_layout.setSpacing(6)

        drv_desc = QLabel("Inject custom network, storage, or chipset drivers (.inf) offline via DISM:")
        drv_desc.setStyleSheet("color: #94a3b8; font-size: 12px;")
        g_drv_layout.addWidget(drv_desc)

        self.driver_picker = PathPickerWidget(
            mode="directory",
            placeholder="Select folder containing driver files (.inf)... (Optional)"
        )
        g_drv_layout.addWidget(self.driver_picker)
        layout.addWidget(group_drivers)

        # 4. Action & Progress Panel
        group_action = QGroupBox("4. Creation Progress & Pipeline")
        g_act_layout = QVBoxLayout(group_action)
        g_act_layout.setSpacing(10)

        self.status_label = QLabel("Ready to create Master VHDX.")
        self.status_label.setStyleSheet("font-weight: bold; color: #38bdf8; font-size: 13px;")
        g_act_layout.addWidget(self.status_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        g_act_layout.addWidget(self.progress_bar)

        btn_layout = QHBoxLayout()
        self.create_btn = QPushButton("Create Master VHDX")
        self.create_btn.setObjectName("primaryBtn")
        self.create_btn.setStyleSheet("font-size: 14px; padding: 10px 24px;")
        self.create_btn.clicked.connect(self.start_creation)
        btn_layout.addWidget(self.create_btn, stretch=1)

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setObjectName("dangerBtn")
        self.cancel_btn.setEnabled(False)
        self.cancel_btn.clicked.connect(self.cancel_creation)
        btn_layout.addWidget(self.cancel_btn)

        g_act_layout.addLayout(btn_layout)
        layout.addWidget(group_action)

        layout.addStretch()
        scroll.setWidget(container)
        outer_layout.addWidget(scroll)

    def _on_source_path_changed(self, path: str):
        if path and os.path.isfile(path):
            self.refresh_ed_btn.setEnabled(True)
            self._scan_source_editions()
            
            # Suggest target path if empty
            if not self.target_picker.text():
                base_dir = os.path.dirname(path)
                default_target = os.path.join(base_dir, "Windows_Master.vhdx")
                self.target_picker.setText(default_target)
        else:
            self.refresh_ed_btn.setEnabled(False)
            self.edition_combo.clear()
            self.edition_combo.addItem("Select valid source image...")
            self.edition_combo.setEnabled(False)

    def _scan_source_editions(self):
        path = self.source_picker.text()
        if not path or not os.path.isfile(path):
            return

        self.edition_combo.clear()
        self.edition_combo.addItem("Scanning editions from image... Please wait")
        self.edition_combo.setEnabled(False)
        self.refresh_ed_btn.setEnabled(False)
        self.log_requested.emit(f"Inspecting Windows Image editions in '{path}'...", "INFO")

        self.inspect_worker = WimInspectionWorker(path)
        self.inspect_worker.inspection_finished.connect(self._on_editions_scanned)
        self.inspect_worker.start()

    def _on_editions_scanned(self, editions: list, error_msg: str):
        self.refresh_ed_btn.setEnabled(True)
        self.edition_combo.clear()
        self.editions_data = editions

        if error_msg or not editions:
            msg = error_msg or "No valid editions found in image."
            self.edition_combo.addItem("Failed to read editions")
            self.edition_combo.setEnabled(False)
            self.log_requested.emit(msg, "ERROR")
            QMessageBox.warning(self, "Image Inspection Notice", msg)
            return

        self.edition_combo.setEnabled(True)
        for ed in editions:
            self.edition_combo.addItem(ed["display_str"], ed["index"])

        self.log_requested.emit(f"Found {len(editions)} Windows edition(s) in source image.", "SUCCESS")

        # Update default suggested target name
        first_ed = editions[0]["name"]
        clean_name = "".join(c if c.isalnum() or c in " _-" else "" for c in first_ed).replace(" ", "_")
        if self.source_picker.text():
            src_dir = os.path.dirname(self.source_picker.text())
            suggested = os.path.join(src_dir, f"{clean_name}_Master.vhdx")
            self.target_picker.setText(suggested)

    def _on_edition_changed(self, idx: int):
        if idx >= 0 and idx < len(self.editions_data):
            ed = self.editions_data[idx]
            ed_name = ed.get("name", "")
            clean_name = "".join(c if c.isalnum() or c in " _-" else "" for c in ed_name).replace(" ", "_")
            if clean_name and self.target_picker.text():
                current_target = self.target_picker.text()
                tgt_dir = os.path.dirname(current_target)
                self.target_picker.setText(os.path.join(tgt_dir, f"{clean_name}_Master.vhdx"))

    def _on_target_path_changed(self, path: str):
        if path:
            dest_dir = os.path.dirname(os.path.abspath(path))
            info = get_disk_space_info(dest_dir)
            free_str = info.get("free_str", "Unknown")
            total_str = info.get("total_str", "Unknown")
            drive = info.get("drive", "")
            self.space_info_label.setText(
                f"Drive {drive} - Free Space: <b>{free_str}</b> (Total: {total_str})"
            )
        else:
            self.space_info_label.setText("Free space: Select destination drive")

    def _on_slider_changed(self, val: int):
        if self.size_spinbox.value() != val:
            self.size_spinbox.setValue(val)

    def _on_spinbox_changed(self, val: int):
        if self.size_slider.value() != val:
            self.size_slider.setValue(val)

    def start_creation(self):
        if not is_admin():
            QMessageBox.critical(
                self,
                "Administrator Rights Required",
                "Administrator privileges are required to create, partition, and format VHDX virtual disks.\n\n"
                "Please close this application and restart it using 'Run as administrator'."
            )
            return

        source = self.source_picker.text()
        if not source or not os.path.isfile(source):
            QMessageBox.warning(self, "Validation Error", "Please select a valid Windows source file (.iso, .wim, .esd).")
            return

        if self.edition_combo.currentIndex() < 0 or not self.editions_data:
            QMessageBox.warning(self, "Validation Error", "Please select a valid Windows Edition index.")
            return

        edition_idx = self.edition_combo.currentData()
        target_vhdx = self.target_picker.text()
        if not target_vhdx:
            QMessageBox.warning(self, "Validation Error", "Please specify a target path for the Master VHDX.")
            return

        if not target_vhdx.lower().endswith(".vhdx"):
            target_vhdx += ".vhdx"
            self.target_picker.setText(target_vhdx)

        if os.path.exists(target_vhdx):
            reply = QMessageBox.question(
                self, "File Exists",
                f"The file '{target_vhdx}' already exists.\nDo you want to overwrite it?",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply != QMessageBox.Yes:
                return

        size_gb = self.size_spinbox.value()
        vhdx_type = "expandable" if self.radio_dynamic.isChecked() else "fixed"
        driver_dir = self.driver_picker.text()

        # Confirmation Dialog with Summary
        summary = (
            f"<b>Source:</b> {os.path.basename(source)}<br>"
            f"<b>Edition:</b> {self.edition_combo.currentText()}<br>"
            f"<b>Target:</b> {target_vhdx}<br>"
            f"<b>Size:</b> {size_gb} GB ({vhdx_type.capitalize()})<br>"
            f"<b>Drivers:</b> {'None' if not driver_dir else driver_dir}<br><br>"
            f"<i>This process will create the VHDX, apply the Windows image, and configure native BCD boot files.</i>"
        )
        conf = QMessageBox.question(
            self, "Confirm VHDX Master Creation",
            f"Proceed with the following configuration?<br><br>{summary}",
            QMessageBox.Yes | QMessageBox.No
        )
        if conf != QMessageBox.Yes:
            return

        # Disable controls during execution
        self.create_btn.setEnabled(False)
        self.cancel_btn.setEnabled(True)
        self.source_picker.setEnabled(False)
        self.target_picker.setEnabled(False)
        self.edition_combo.setEnabled(False)
        self.progress_bar.setValue(0)
        self.status_label.setText("Starting Master VHDX creation pipeline...")

        self.worker = MasterCreationWorker(
            source_path=source,
            edition_index=edition_idx,
            target_vhdx_path=target_vhdx,
            size_gb=size_gb,
            vhdx_type=vhdx_type,
            driver_dir=driver_dir,
            volume_label=DEFAULT_VOLUME_LABEL
        )
        self.worker.progress_changed.connect(self.progress_bar.setValue)
        self.worker.status_changed.connect(self.status_label.setText)
        self.worker.log_event.connect(self.log_requested.emit)
        self.worker.task_finished.connect(self._on_creation_finished)
        self.worker.start()

    def cancel_creation(self):
        if self.worker and self.worker.isRunning():
            reply = QMessageBox.question(
                self, "Cancel Task", "Are you sure you want to cancel the creation process?",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                self.worker.cancel()
                self.status_label.setText("Cancelling operation...")
                self.cancel_btn.setEnabled(False)

    def _on_creation_finished(self, success: bool, message: str):
        self.create_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)
        self.source_picker.setEnabled(True)
        self.target_picker.setEnabled(True)
        self.edition_combo.setEnabled(True)

        if success:
            self.status_label.setText("Master VHDX Created Successfully!")
            QMessageBox.information(self, "Success", f"Master VHDX has been created successfully!\n\n{message}")
        else:
            self.status_label.setText("Creation Failed!")
            QMessageBox.critical(self, "Error", f"Failed to create Master VHDX:\n\n{message}")
