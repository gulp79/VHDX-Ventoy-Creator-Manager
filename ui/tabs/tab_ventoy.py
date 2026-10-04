"""
Tab 3: Ventoy Tools, Plugin Manager, and VHDX Deployer Tab.
"""

import os
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QGroupBox, QMessageBox, QProgressBar, QRadioButton,
    QButtonGroup, QScrollArea, QFrame
)
from PySide6.QtCore import Qt, Signal
from ui.widgets.path_picker import PathPickerWidget
from ui.workers.ventoy_worker import VentoyPluginWorker, VentoyDeployWorker
from core.ventoy_engine import detect_ventoy_drives, check_vhdboot_plugin
from utils.disk_info import format_size


class TabVentoyWidget(QWidget):
    log_requested = Signal(str, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.plugin_worker: VentoyPluginWorker = None
        self.deploy_worker: VentoyDeployWorker = None
        self.drives_data = []

        self._build_ui()
        self.refresh_drives()

    def _build_ui(self):
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(4, 4, 4, 4)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(14)

        # 1. Ventoy USB Detection Group
        group_drive = QGroupBox("1. Ventoy USB Drive Detection")
        g_d_layout = QVBoxLayout(group_drive)
        g_d_layout.setSpacing(10)

        drive_top_layout = QHBoxLayout()
        self.drive_combo = QComboBox()
        self.drive_combo.currentIndexChanged.connect(self._on_drive_selected)
        drive_top_layout.addWidget(self.drive_combo, stretch=1)

        self.refresh_drives_btn = QPushButton("Refresh Drives")
        self.refresh_drives_btn.clicked.connect(self.refresh_drives)
        drive_top_layout.addWidget(self.refresh_drives_btn)

        g_d_layout.addLayout(drive_top_layout)

        # Drive details badge bar
        self.drive_info_layout = QHBoxLayout()
        self.fs_badge = QLabel("FS: Unknown")
        self.fs_badge.setObjectName("badgeInfo")
        self.drive_info_layout.addWidget(self.fs_badge)

        self.space_badge = QLabel("Free: -")
        self.space_badge.setObjectName("badgeInfo")
        self.drive_info_layout.addWidget(self.space_badge)

        self.plugin_badge = QLabel("Plugin: Checking...")
        self.plugin_badge.setObjectName("badgeWarning")
        self.drive_info_layout.addWidget(self.plugin_badge)

        self.drive_info_layout.addStretch()
        g_d_layout.addLayout(self.drive_info_layout)

        layout.addWidget(group_drive)

        # 2. Ventoy VHD Boot Plugin Management
        group_plugin = QGroupBox("2. Ventoy VHD Boot Plugin (ventoy_vhdboot.img)")
        g_p_layout = QVBoxLayout(group_plugin)
        g_p_layout.setSpacing(8)

        p_desc = QLabel(
            "Ventoy requires the <b>ventoy_vhdboot.img</b> plugin inside the <code>/ventoy/</code> folder "
            "of your USB drive to enable Native Booting of Windows VHD/VHDX files."
        )
        p_desc.setWordWrap(True)
        p_desc.setStyleSheet("color: #94a3b8; font-size: 12px;")
        g_p_layout.addWidget(p_desc)

        p_btn_layout = QHBoxLayout()
        self.plugin_status_label = QLabel("Status: Checking plugin...")
        self.plugin_status_label.setStyleSheet("font-weight: 600; color: #cbd5e1;")
        p_btn_layout.addWidget(self.plugin_status_label, stretch=1)

        self.install_plugin_btn = QPushButton("Install / Update Plugin (1-Click)")
        self.install_plugin_btn.setObjectName("successBtn")
        self.install_plugin_btn.clicked.connect(self.install_plugin)
        p_btn_layout.addWidget(self.install_plugin_btn)

        g_p_layout.addLayout(p_btn_layout)

        self.plugin_progress = QProgressBar()
        self.plugin_progress.setRange(0, 100)
        self.plugin_progress.setValue(0)
        self.plugin_progress.setVisible(False)
        g_p_layout.addWidget(self.plugin_progress)

        layout.addWidget(group_plugin)

        # 3. Guided VHDX Deployment Section
        group_deploy = QGroupBox("3. Guided VHDX Deployment to Ventoy USB")
        g_dp_layout = QVBoxLayout(group_deploy)
        g_dp_layout.setSpacing(10)

        # Source VHDX Picker
        vhd_src_lbl = QLabel("Select VHDX to Deploy (Master or Child):")
        vhd_src_lbl.setStyleSheet("font-weight: 600; color: #cbd5e1;")
        g_dp_layout.addWidget(vhd_src_lbl)

        self.vhdx_picker = PathPickerWidget(
            mode="open_file",
            file_filter="Virtual Hard Disk (*.vhdx *.vhd)",
            placeholder="Select .vhdx file to deploy..."
        )
        g_dp_layout.addWidget(self.vhdx_picker)

        # Copy vs Move options
        action_layout = QHBoxLayout()
        act_lbl = QLabel("Deployment Method:")
        act_lbl.setStyleSheet("font-weight: 600; color: #cbd5e1;")
        action_layout.addWidget(act_lbl)

        self.radio_copy = QRadioButton("Copy VHDX (Keep local source)")
        self.radio_copy.setChecked(True)
        self.radio_move = QRadioButton("Move VHDX (Frees local disk space)")

        self.deploy_action_group = QButtonGroup(self)
        self.deploy_action_group.addButton(self.radio_copy)
        self.deploy_action_group.addButton(self.radio_move)

        action_layout.addWidget(self.radio_copy)
        action_layout.addWidget(self.radio_move)
        action_layout.addStretch()

        g_dp_layout.addLayout(action_layout)

        # Deployment Progress
        self.deploy_status_lbl = QLabel("Ready to deploy VHDX to USB.")
        self.deploy_status_lbl.setStyleSheet("font-weight: bold; color: #38bdf8; font-size: 13px;")
        g_dp_layout.addWidget(self.deploy_status_lbl)

        self.deploy_progress_bar = QProgressBar()
        self.deploy_progress_bar.setRange(0, 100)
        self.deploy_progress_bar.setValue(0)
        g_dp_layout.addWidget(self.deploy_progress_bar)

        # Deploy action buttons
        d_btn_layout = QHBoxLayout()
        self.deploy_btn = QPushButton("Deploy VHDX to Ventoy USB")
        self.deploy_btn.setObjectName("primaryBtn")
        self.deploy_btn.setStyleSheet("font-size: 14px; padding: 10px 24px;")
        self.deploy_btn.clicked.connect(self.deploy_vhdx)
        d_btn_layout.addWidget(self.deploy_btn, stretch=1)

        self.cancel_deploy_btn = QPushButton("Cancel")
        self.cancel_deploy_btn.setObjectName("dangerBtn")
        self.cancel_deploy_btn.setEnabled(False)
        self.cancel_deploy_btn.clicked.connect(self.cancel_deployment)
        d_btn_layout.addWidget(self.cancel_deploy_btn)

        g_dp_layout.addLayout(d_btn_layout)
        layout.addWidget(group_deploy)

        layout.addStretch()
        scroll.setWidget(container)
        outer_layout.addWidget(scroll)

    def refresh_drives(self):
        self.drive_combo.clear()
        self.drives_data = detect_ventoy_drives()

        if not self.drives_data:
            self.drive_combo.addItem("No removable or Ventoy drives detected")
            self.drive_combo.setEnabled(False)
            self.install_plugin_btn.setEnabled(False)
            self.deploy_btn.setEnabled(False)
            self.fs_badge.setText("FS: None")
            self.space_badge.setText("Free: -")
            self.plugin_badge.setText("Plugin: N/A")
            return

        self.drive_combo.setEnabled(True)
        self.install_plugin_btn.setEnabled(True)
        self.deploy_btn.setEnabled(True)

        for d in self.drives_data:
            self.drive_combo.addItem(d["display_text"], d)

        self._on_drive_selected(0)

    def _on_drive_selected(self, idx: int):
        if idx < 0 or idx >= len(self.drives_data):
            return

        drive = self.drives_data[idx]
        mount = drive["mount_point"]
        fstype = drive["fstype"]
        free_bytes = drive["free_size_bytes"]

        # FS Badge
        if fstype == "NTFS":
            self.fs_badge.setText("FS: NTFS (Optimal)")
            self.fs_badge.setObjectName("badgeSuccess")
        elif fstype in ["EXFAT"]:
            self.fs_badge.setText(f"FS: {fstype} (Compatible)")
            self.fs_badge.setObjectName("badgeInfo")
        else:
            self.fs_badge.setText(f"FS: {fstype} (FAT32 NOT RECOMMENDED for large VHDX)")
            self.fs_badge.setObjectName("badgeWarning")

        self.fs_badge.style().unpolish(self.fs_badge)
        self.fs_badge.style().polish(self.fs_badge)

        # Space Badge
        self.space_badge.setText(f"Free: {format_size(free_bytes)}")

        # Check plugin
        has_plugin, plugin_file, sz = check_vhdboot_plugin(mount)
        if has_plugin:
            self.plugin_badge.setText("Plugin: Installed")
            self.plugin_badge.setObjectName("badgeSuccess")
            self.plugin_status_label.setText(f"Plugin Installed: {plugin_file} ({format_size(sz)})")
            self.install_plugin_btn.setText("Reinstall Plugin")
        else:
            self.plugin_badge.setText("Plugin: Missing!")
            self.plugin_badge.setObjectName("badgeDanger")
            self.plugin_status_label.setText("Plugin Missing! Install ventoy_vhdboot.img to enable VHD boot.")
            self.install_plugin_btn.setText("Install Plugin (1-Click)")

        self.plugin_badge.style().unpolish(self.plugin_badge)
        self.plugin_badge.style().polish(self.plugin_badge)

    def install_plugin(self):
        idx = self.drive_combo.currentIndex()
        if idx < 0 or idx >= len(self.drives_data):
            return

        drive = self.drives_data[idx]
        mount = drive["mount_point"]

        self.install_plugin_btn.setEnabled(False)
        self.plugin_progress.setVisible(True)
        self.plugin_progress.setValue(0)
        self.plugin_status_label.setText("Downloading ventoy_vhdboot.img...")

        self.plugin_worker = VentoyPluginWorker(ventoy_root=mount)
        self.plugin_worker.progress_changed.connect(self._on_plugin_progress)
        self.plugin_worker.log_event.connect(self.log_requested.emit)
        self.plugin_worker.task_finished.connect(self._on_plugin_finished)
        self.plugin_worker.start()

    def _on_plugin_progress(self, pct: int, text: str):
        self.plugin_progress.setValue(pct)
        self.plugin_status_label.setText(text)

    def _on_plugin_finished(self, success: bool, msg: str):
        self.install_plugin_btn.setEnabled(True)
        self.plugin_progress.setVisible(False)
        self.refresh_drives()

        if success:
            QMessageBox.information(self, "Plugin Installed", "ventoy_vhdboot.img plugin successfully installed on your Ventoy USB!")
        else:
            QMessageBox.critical(self, "Error", f"Failed to install plugin:\n{msg}")

    def deploy_vhdx(self):
        idx = self.drive_combo.currentIndex()
        if idx < 0 or idx >= len(self.drives_data):
            QMessageBox.warning(self, "Validation Error", "Please select a target Ventoy USB drive.")
            return

        drive = self.drives_data[idx]
        mount = drive["mount_point"]

        vhdx_file = self.vhdx_picker.text()
        if not vhdx_file or not os.path.isfile(vhdx_file):
            QMessageBox.warning(self, "Validation Error", "Please select a valid .vhdx file to deploy.")
            return

        vhdx_size = os.path.getsize(vhdx_file)
        if vhdx_size > drive["free_size_bytes"]:
            QMessageBox.critical(
                self, "Insufficient Space",
                f"The target Ventoy USB does not have enough free space!\n\n"
                f"File Size: {format_size(vhdx_size)}\nFree Space: {format_size(drive['free_size_bytes'])}"
            )
            return

        # Check FAT32 size limit
        if drive["fstype"] == "FAT32" and vhdx_size >= (4 * 1024 * 1024 * 1024):
            QMessageBox.critical(
                self, "Filesystem Limitation",
                "The target USB drive is formatted as FAT32 which does NOT support files larger than 4 GB.\n"
                "Please reformat the Ventoy data partition as NTFS or exFAT."
            )
            return

        is_move = self.radio_move.isChecked()
        action_name = "Move" if is_move else "Copy"

        reply = QMessageBox.question(
            self, f"Confirm VHDX {action_name}",
            f"{action_name} <b>{os.path.basename(vhdx_file)}</b> ({format_size(vhdx_size)}) to <b>{mount}</b>?",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply != QMessageBox.Yes:
            return

        self.deploy_btn.setEnabled(False)
        self.cancel_deploy_btn.setEnabled(True)
        self.vhdx_picker.setEnabled(False)
        self.drive_combo.setEnabled(False)
        self.deploy_progress_bar.setValue(0)
        self.deploy_status_lbl.setText("Starting file transfer...")

        self.deploy_worker = VentoyDeployWorker(
            source_vhdx=vhdx_file,
            target_dir=mount,
            move=is_move
        )
        self.deploy_worker.progress_changed.connect(self._on_deploy_progress)
        self.deploy_worker.log_event.connect(self.log_requested.emit)
        self.deploy_worker.task_finished.connect(self._on_deploy_finished)
        self.deploy_worker.start()

    def _on_deploy_progress(self, pct: int, text: str):
        self.deploy_progress_bar.setValue(pct)
        self.deploy_status_lbl.setText(text)

    def cancel_deployment(self):
        if self.deploy_worker and self.deploy_worker.isRunning():
            reply = QMessageBox.question(self, "Cancel Transfer", "Abort file deployment?", QMessageBox.Yes | QMessageBox.No)
            if reply == QMessageBox.Yes:
                self.deploy_worker.cancel()
                self.cancel_deploy_btn.setEnabled(False)

    def _on_deploy_finished(self, success: bool, msg: str):
        self.deploy_btn.setEnabled(True)
        self.cancel_deploy_btn.setEnabled(False)
        self.vhdx_picker.setEnabled(True)
        self.drive_combo.setEnabled(True)
        self.refresh_drives()

        if success:
            self.deploy_status_lbl.setText("Deployment Complete!")
            QMessageBox.information(self, "Success", f"VHDX successfully deployed to Ventoy USB!\n\n{msg}")
        else:
            self.deploy_status_lbl.setText("Deployment Failed!")
            QMessageBox.critical(self, "Error", f"Failed to deploy VHDX:\n\n{msg}")
