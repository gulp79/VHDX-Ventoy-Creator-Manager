"""
Application Entry Point for VHDX Ventoy Creator & Manager.
"""

import sys
import os

# Add project root directory to python path
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from ui.style import DARK_THEME_QSS
from ui.main_window import MainWindow
from utils.admin import is_admin, request_admin_elevation


def main():
    # 1. Administrator Elevation Check
    # Allow bypassing elevation with --no-elevation argument (e.g. for testing / UI inspection)
    if "--no-elevation" not in sys.argv:
        if not is_admin():
            elevated = request_admin_elevation()
            if elevated:
                # Successfully spawned elevated child process, exit current standard process
                sys.exit(0)
            else:
                print("Warning: Could not elevate to administrator. Proceeding in standard mode.")

    # 2. Qt Application Setup
    app = QApplication(sys.argv)
    app.setApplicationName("VHDX Ventoy Creator & Manager")
    app.setOrganizationName("VentoyVHDX")

    # Apply modern dark theme styling
    app.setStyleSheet(DARK_THEME_QSS)

    # 3. Create & Show Main Window
    window = MainWindow()
    window.show()

    # 4. Start Event Loop
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
