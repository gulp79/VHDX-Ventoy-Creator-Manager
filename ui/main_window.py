"""
Main Window for VHDX Ventoy Creator & Manager.
"""

import sys
import os
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QTabWidget, QSplitter, QPushButton, QStatusBar, QFrame
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon, QFont

from ui.tabs.tab_master import TabMasterWidget
from ui.tabs.tab_differential import TabDifferentialWidget
from ui.tabs.tab_ventoy import TabVentoyWidget
from ui.widgets.log_console import LogConsoleWidget
from utils.constants import APP_NAME, APP_VERSION, APP_DESCRIPTION
from utils.admin import is_admin


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"{APP_NAME} v{APP_VERSION}")
        self.setMinimumSize(950, 720)
        self.resize(1080, 800)

        self._build_ui()
        self._check_admin_status()

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(16, 16, 16, 12)
        main_layout.setSpacing(12)

        # 1. Header Bar
        header = QFrame()
        header.setObjectName("mainCard")
        h_layout = QHBoxLayout(header)
        h_layout.setContentsMargins(16, 12, 16, 12)

        # Title & Subtitle
        title_box = QVBoxLayout()
        title_box.setSpacing(2)

        title_lbl = QLabel(APP_NAME)
        title_lbl.setStyleSheet("font-size: 18px; font-weight: 800; color: #38bdf8; letter-spacing: 0.5px;")
        title_box.addWidget(title_lbl)

        desc_lbl = QLabel(APP_DESCRIPTION)
        desc_lbl.setStyleSheet("font-size: 12px; color: #94a3b8;")
        title_box.addWidget(desc_lbl)
        h_layout.addLayout(title_box, stretch=1)

        # Admin Badge
        self.admin_badge = QLabel("ADMINISTRATOR MODE")
        self.admin_badge.setObjectName("badgeSuccess")
        self.admin_badge.setStyleSheet("font-size: 11px; padding: 5px 12px;")
        h_layout.addWidget(self.admin_badge)

        main_layout.addWidget(header)

        # 2. Main Vertical Splitter (Tabs on Top, Log Console on Bottom)
        splitter = QSplitter(Qt.Vertical)
        splitter.setHandleWidth(6)
        splitter.setStyleSheet("QSplitter::handle { background-color: #282834; border-radius: 3px; }")

        # Tabs Container
        self.tabs = QTabWidget()
        self.tab_master = TabMasterWidget()
        self.tab_diff = TabDifferentialWidget()
        self.tab_ventoy = TabVentoyWidget()

        self.tabs.addTab(self.tab_master, "  Master VHDX Creator  ")
        self.tabs.addTab(self.tab_diff, "  Differential Disks (Parent / Child)  ")
        self.tabs.addTab(self.tab_ventoy, "  Ventoy Tools & Deployer  ")

        splitter.addWidget(self.tabs)

        # Log Console Container (Bottom Panel)
        log_panel = QFrame()
        log_panel.setObjectName("mainCard")
        log_layout = QVBoxLayout(log_panel)
        log_layout.setContentsMargins(12, 8, 12, 8)

        self.console = LogConsoleWidget()
        log_layout.addWidget(self.console)

        splitter.addWidget(log_panel)

        # Set initial splitter proportions (70% top, 30% bottom)
        splitter.setStretchFactor(0, 7)
        splitter.setStretchFactor(1, 3)

        main_layout.addWidget(splitter, stretch=1)

        # 3. Connect Log Signals from all tabs
        self.tab_master.log_requested.connect(self.console.append_log)
        self.tab_diff.log_requested.connect(self.console.append_log)
        self.tab_ventoy.log_requested.connect(self.console.append_log)

        # 4. Status Bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready. Select source image or tools to begin.")

        # Welcome log message
        self.console.append_log(f"Welcome to {APP_NAME} v{APP_VERSION}", "SUCCESS")
        self.console.append_log("Ready for automated VHDX generation, differential branching, and Ventoy boot deployment.", "INFO")

    def _check_admin_status(self):
        admin = is_admin()
        if admin:
            self.admin_badge.setText("ADMINISTRATOR MODE")
            self.admin_badge.setObjectName("badgeSuccess")
            self.console.append_log("Running with Administrator privileges. System operations enabled.", "SUCCESS")
        else:
            self.admin_badge.setText("STANDARD USER (Restricted)")
            self.admin_badge.setObjectName("badgeDanger")
            self.console.append_log("Warning: Not running as Administrator. diskpart/dism operations may fail.", "WARNING")

        self.admin_badge.style().unpolish(self.admin_badge)
        self.admin_badge.style().polish(self.admin_badge)
