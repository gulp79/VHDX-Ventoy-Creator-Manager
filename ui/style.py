"""
Modern Dark Theme QSS Stylesheet and UI styling definitions.
"""

DARK_THEME_QSS = """
/* Global Window & Widget Settings */
QWidget {
    background-color: #16161a;
    color: #fffffe;
    font-family: "Segoe UI", "Helvetica Neue", "Arial", sans-serif;
    font-size: 13px;
    selection-background-color: #3b82f6;
    selection-color: #ffffff;
}

/* Main Container Panels */
QFrame#mainCard, QGroupBox {
    background-color: #1e1e24;
    border: 1px solid #2e2e38;
    border-radius: 10px;
    margin-top: 14px;
    padding-top: 14px;
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 0 8px;
    color: #94a3b8;
    font-weight: 600;
    font-size: 12px;
    letter-spacing: 0.5px;
    text-transform: uppercase;
}

/* Sidebar / Tabs */
QTabWidget::pane {
    border: 1px solid #2e2e38;
    background: #1e1e24;
    border-radius: 8px;
    top: -1px;
}

QTabBar::tab {
    background: #16161a;
    color: #94a3b8;
    padding: 10px 20px;
    border: 1px solid #2e2e38;
    border-bottom: none;
    border-top-left-radius: 8px;
    border-top-right-radius: 8px;
    margin-right: 4px;
    font-weight: 600;
    min-width: 140px;
}

QTabBar::tab:selected {
    background: #1e1e24;
    color: #38bdf8;
    border-top: 2px solid #38bdf8;
    border-bottom: 1px solid #1e1e24;
}

QTabBar::tab:hover:!selected {
    background: #25252e;
    color: #f1f5f9;
}

/* Standard Buttons */
QPushButton {
    background-color: #272730;
    color: #f8fafc;
    border: 1px solid #3f3f4e;
    border-radius: 6px;
    padding: 7px 16px;
    font-weight: 600;
    min-height: 20px;
}

QPushButton:hover {
    background-color: #343440;
    border-color: #64748b;
}

QPushButton:pressed {
    background-color: #1e1e26;
}

QPushButton:disabled {
    background-color: #1a1a20;
    color: #555566;
    border-color: #282832;
}

/* Primary Accent Button */
QPushButton#primaryBtn {
    background-color: #2563eb;
    color: #ffffff;
    border: 1px solid #3b82f6;
    font-weight: 600;
    font-size: 13px;
    padding: 9px 20px;
}

QPushButton#primaryBtn:hover {
    background-color: #1d4ed8;
    border-color: #60a5fa;
}

QPushButton#primaryBtn:pressed {
    background-color: #1e40af;
}

/* Success Button */
QPushButton#successBtn {
    background-color: #059669;
    color: #ffffff;
    border: 1px solid #10b981;
}

QPushButton#successBtn:hover {
    background-color: #047857;
}

/* Danger Button */
QPushButton#dangerBtn {
    background-color: #b91c1c;
    color: #ffffff;
    border: 1px solid #ef4444;
}

QPushButton#dangerBtn:hover {
    background-color: #991b1b;
}

/* Inputs, LineEdits, ComboBoxes */
QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox {
    background-color: #121216;
    color: #f8fafc;
    border: 1px solid #383846;
    border-radius: 6px;
    padding: 6px 10px;
    min-height: 22px;
}

QLineEdit:focus, QComboBox:focus, QSpinBox:focus {
    border: 1px solid #38bdf8;
    background-color: #15151c;
}

QComboBox::drop-down {
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 26px;
    border-left-width: 1px;
    border-left-color: #383846;
    border-left-style: solid;
    border-top-right-radius: 6px;
    border-bottom-right-radius: 6px;
}

QComboBox QAbstractItemView {
    background-color: #1c1c24;
    border: 1px solid #3f3f50;
    selection-background-color: #2563eb;
    selection-color: #ffffff;
    padding: 4px;
    outline: none;
}

/* Radio Buttons & Checkboxes */
QRadioButton, QCheckBox {
    color: #f8fafc;
    background-color: transparent;
    spacing: 8px;
    font-size: 13px;
}

QRadioButton::indicator {
    width: 18px;
    height: 18px;
    border-radius: 9px;
    border: 2px solid #64748b;
    background-color: #121216;
}

QRadioButton::indicator:hover {
    border-color: #38bdf8;
    background-color: #181822;
}

QRadioButton::indicator:checked {
    border: 2px solid #38bdf8;
    background: qradialgradient(cx:0.5, cy:0.5, radius:0.45,
        fx:0.5, fy:0.5,
        stop:0 #38bdf8,
        stop:0.55 #38bdf8,
        stop:0.62 #121216,
        stop:1 #121216);
}

QRadioButton::indicator:checked:hover {
    border-color: #60a5fa;
    background: qradialgradient(cx:0.5, cy:0.5, radius:0.45,
        fx:0.5, fy:0.5,
        stop:0 #60a5fa,
        stop:0.55 #60a5fa,
        stop:0.62 #121216,
        stop:1 #121216);
}

QCheckBox::indicator {
    width: 16px;
    height: 16px;
    border-radius: 4px;
    border: 2px solid #64748b;
    background-color: #121216;
}

QCheckBox::indicator:hover {
    border-color: #38bdf8;
}

QCheckBox::indicator:checked {
    border: 2px solid #38bdf8;
    background-color: #2563eb;
}

/* Sliders */
QSlider::groove:horizontal {
    border: 1px solid #2e2e38;
    height: 8px;
    background: #121216;
    margin: 2px 0;
    border-radius: 4px;
}

QSlider::sub-page:horizontal {
    background: #3b82f6;
    border-radius: 4px;
}

QSlider::handle:horizontal {
    background: #60a5fa;
    border: 1px solid #93c5fd;
    width: 18px;
    margin-top: -6px;
    margin-bottom: -6px;
    border-radius: 9px;
}

QSlider::handle:horizontal:hover {
    background: #93c5fd;
}

/* Progress Bar */
QProgressBar {
    border: 1px solid #2e2e38;
    border-radius: 6px;
    text-align: center;
    background-color: #121216;
    color: #f8fafc;
    font-weight: bold;
    min-height: 20px;
}

QProgressBar::chunk {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #2563eb, stop:1 #38bdf8);
    border-radius: 5px;
}

/* Console Log View */
QPlainTextEdit#logConsole {
    background-color: #0d0d11;
    color: #a7f3d0;
    font-family: "Consolas", "Cascadia Code", "Courier New", monospace;
    font-size: 12px;
    border: 1px solid #2e2e38;
    border-radius: 6px;
    padding: 8px;
}

/* Table Widget */
QTableWidget {
    background-color: #121216;
    border: 1px solid #2e2e38;
    border-radius: 6px;
    gridline-color: #282834;
}

QTableWidget::item {
    padding: 6px;
}

QTableWidget::item:selected {
    background-color: #1e3a8a;
    color: #ffffff;
}

QHeaderView::section {
    background-color: #1a1a22;
    color: #94a3b8;
    padding: 6px;
    border: none;
    border-bottom: 1px solid #2e2e38;
    font-weight: 600;
}

/* Custom Scrollbars */
QScrollBar:vertical {
    background: #16161a;
    width: 10px;
    margin: 0px;
}

QScrollBar::handle:vertical {
    background: #333342;
    min-height: 20px;
    border-radius: 5px;
}

QScrollBar::handle:vertical:hover {
    background: #4b4b60;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}

QScrollBar:horizontal {
    background: #16161a;
    height: 10px;
    margin: 0px;
}

QScrollBar::handle:horizontal {
    background: #333342;
    min-width: 20px;
    border-radius: 5px;
}

QScrollBar::handle:horizontal:hover {
    background: #4b4b60;
}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0px;
}

/* Status Labels & Badges */
QLabel#badgeSuccess {
    background-color: #064e3b;
    color: #6ee7b7;
    border: 1px solid #059669;
    border-radius: 4px;
    padding: 2px 8px;
    font-weight: 600;
}

QLabel#badgeWarning {
    background-color: #78350f;
    color: #fde68a;
    border: 1px solid #d97706;
    border-radius: 4px;
    padding: 2px 8px;
    font-weight: 600;
}

QLabel#badgeDanger {
    background-color: #7f1d1d;
    color: #fca5a5;
    border: 1px solid #dc2626;
    border-radius: 4px;
    padding: 2px 8px;
    font-weight: 600;
}

QLabel#badgeInfo {
    background-color: #1e3a8a;
    color: #93c5fd;
    border: 1px solid #2563eb;
    border-radius: 4px;
    padding: 2px 8px;
    font-weight: 600;
}
"""
