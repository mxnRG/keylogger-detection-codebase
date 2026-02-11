"""
FYP GUI Theme - GitHub-inspired dark theme
"""

DARK_THEME = """
* {
    font-family: 'Inter', 'Segoe UI', 'SF Pro Display', -apple-system, system-ui, sans-serif;
    font-size: 11pt;
}

QMainWindow, QWidget {
    background-color: #0d1117;
    color: #e6edf3;
}

/* Sidebar Navigation */
#sidebar {
    background-color: #010409;
    border-right: 1px solid #21262d;
}

#sidebarButton {
    background-color: transparent;
    color: #7d8590;
    border: none;
    border-radius: 8px;
    padding: 10px 14px;
    text-align: left;
    font-weight: 500;
    font-size: 13px;
}

#sidebarButton:hover {
    background-color: #161b22;
    color: #e6edf3;
}

#sidebarButton[selected="true"] {
    background-color: #1f6feb;
    color: #ffffff;
    font-weight: 600;
}

/* Status Header */
#statusHeader {
    background-color: #161b22;
    border-bottom: 1px solid #21262d;
    padding: 16px;
}

#statusLabel {
    color: #7d8590;
    font-size: 12px;
    font-weight: 500;
}

#statusValue {
    color: #e6edf3;
    font-size: 14px;
    font-weight: 600;
}

/* Content Area */
#contentArea {
    background-color: #0d1117;
}

#sectionTitle {
    color: #f0f6fc;
    font-size: 22px;
    font-weight: 700;
    margin-bottom: 2px;
}

#sectionSubtitle {
    color: #7d8590;
    font-size: 13px;
    margin-bottom: 12px;
}

/* Dashboard Cards */
#dashCard {
    background-color: #161b22;
    border: 1px solid #21262d;
    border-radius: 10px;
    padding: 0px;
    margin-top: 0px;
}

/* Group Boxes */
QGroupBox {
    background-color: #161b22;
    border: 1px solid #21262d;
    border-radius: 10px;
    padding-top: 18px;
    margin-top: 14px;
    font-weight: 600;
    font-size: 13px;
}

QGroupBox::title {
    color: #e6edf3;
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 0 10px;
}

/* Buttons */
QPushButton {
    background-color: #238636;
    color: #ffffff;
    border: none;
    border-radius: 8px;
    padding: 8px 16px;
    font-weight: 600;
    font-size: 13px;
}

QPushButton:hover {
    background-color: #2ea043;
}

QPushButton:pressed {
    background-color: #1a7f37;
}

QPushButton#secondaryButton {
    background-color: #21262d;
    color: #c9d1d9;
    border: 1px solid #30363d;
}

QPushButton#secondaryButton:hover {
    background-color: #30363d;
    border-color: #8b949e;
}

QPushButton#dangerButton {
    background-color: #da3633;
}

QPushButton#dangerButton:hover {
    background-color: #e5534b;
}

QPushButton#primaryButton {
    background-color: #1f6feb;
}

QPushButton#primaryButton:hover {
    background-color: #388bfd;
}

/* Tables */
QTableWidget {
    background-color: #0d1117;
    alternate-background-color: #161b22;
    gridline-color: #21262d;
    border: 1px solid #21262d;
    border-radius: 10px;
    selection-background-color: #1f6feb;
}

QTableWidget::item {
    padding: 8px;
    border: none;
    border-bottom: 1px solid #21262d;
}

QTableWidget::item:selected {
    background-color: #1f6feb;
    color: #ffffff;
}

QHeaderView::section {
    background-color: #161b22;
    color: #7d8590;
    padding: 10px;
    border: none;
    border-bottom: 1px solid #21262d;
    font-weight: 600;
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}

/* Text Edit / Line Edit */
QTextEdit, QLineEdit {
    background-color: #0d1117;
    color: #e6edf3;
    border: 1px solid #30363d;
    border-radius: 8px;
    padding: 8px 12px;
    selection-background-color: #1f6feb;
}

QTextEdit:focus, QLineEdit:focus {
    border-color: #1f6feb;
    outline: none;
}

/* ComboBox */
QComboBox {
    background-color: #21262d;
    color: #e6edf3;
    border: 1px solid #30363d;
    border-radius: 8px;
    padding: 8px 12px;
    font-size: 13px;
}

QComboBox:hover {
    border-color: #484f58;
}

QComboBox::drop-down {
    border: none;
    width: 24px;
}

QComboBox::down-arrow {
    image: none;
    border-left: 5px solid transparent;
    border-right: 5px solid transparent;
    border-top: 5px solid #7d8590;
    margin-right: 8px;
}

QComboBox QAbstractItemView {
    background-color: #161b22;
    color: #e6edf3;
    selection-background-color: #1f6feb;
    border: 1px solid #30363d;
    border-radius: 8px;
    padding: 4px;
}

/* Progress Bar */
QProgressBar {
    background-color: #21262d;
    border: none;
    border-radius: 4px;
    text-align: center;
    color: #e6edf3;
    height: 6px;
}

QProgressBar::chunk {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #2ea043, stop:1 #1f6feb);
    border-radius: 4px;
}

/* Status Bar */
QStatusBar {
    background-color: #010409;
    color: #7d8590;
    border-top: 1px solid #21262d;
    font-size: 12px;
    padding: 4px 12px;
}

/* Scroll Bar */
QScrollBar:vertical {
    background-color: transparent;
    width: 8px;
    border-radius: 4px;
    margin: 2px;
}

QScrollBar::handle:vertical {
    background-color: #30363d;
    border-radius: 4px;
    min-height: 40px;
}

QScrollBar::handle:vertical:hover {
    background-color: #484f58;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}

QScrollBar:horizontal {
    background-color: transparent;
    height: 8px;
    border-radius: 4px;
    margin: 2px;
}

QScrollBar::handle:horizontal {
    background-color: #30363d;
    border-radius: 4px;
    min-width: 40px;
}

QScrollBar::handle:horizontal:hover {
    background-color: #484f58;
}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0px;
}

/* CheckBox */
QCheckBox {
    color: #e6edf3;
    spacing: 8px;
}

QCheckBox::indicator {
    width: 16px;
    height: 16px;
    border: 1px solid #30363d;
    border-radius: 4px;
    background-color: #0d1117;
}

QCheckBox::indicator:checked {
    background-color: #1f6feb;
    border-color: #1f6feb;
}

QCheckBox::indicator:hover {
    border-color: #484f58;
}

/* Slider */
QSlider::groove:horizontal {
    background: #30363d;
    height: 6px;
    border-radius: 3px;
}

QSlider::handle:horizontal {
    background: #1f6feb;
    width: 16px;
    height: 16px;
    margin: -5px 0;
    border-radius: 8px;
}

QSlider::handle:horizontal:hover {
    background: #388bfd;
}

/* Form */
QFormLayout QLabel {
    color: #8b949e;
    font-size: 13px;
}
"""
