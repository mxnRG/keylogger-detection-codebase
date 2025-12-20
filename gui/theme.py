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
    color: #c9d1d9;
}

/* Sidebar Navigation */
#sidebar {
    background-color: #161b22;
    border-right: 1px solid #30363d;
}

#sidebarButton {
    background-color: transparent;
    color: #6e7681;
    border: none;
    border-radius: 6px;
    padding: 12px 16px;
    text-align: left;
    font-weight: 500;
    font-size: 13px;
}

#sidebarButton:hover {
    background-color: #1c2128;
    color: #8b949e;
}

#sidebarButton[selected="true"] {
    background-color: #0d419d;
    color: #ffffff;
}

/* Status Header */
#statusHeader {
    background-color: #161b22;
    border-bottom: 1px solid #30363d;
    padding: 16px;
}

#statusLabel {
    color: #8b949e;
    font-size: 12px;
    font-weight: 500;
}

#statusValue {
    color: #c9d1d9;
    font-size: 14px;
    font-weight: 600;
}

/* Content Area */
#contentArea {
    background-color: #0d1117;
    padding: 20px;
}

#sectionTitle {
    color: #f0f6fc;
    font-size: 24px;
    font-weight: 700;
    margin-bottom: 8px;
}

#sectionSubtitle {
    color: #8b949e;
    font-size: 14px;
    margin-bottom: 20px;
}

/* Group Boxes */
QGroupBox {
    background-color: #161b22;
    border: 1px solid #30363d;
    border-radius: 8px;
    padding-top: 20px;
    margin-top: 16px;
    font-weight: 600;
    font-size: 14px;
}

QGroupBox::title {
    color: #f0f6fc;
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 0 8px;
}

/* Buttons */
QPushButton {
    background-color: #238636;
    color: #ffffff;
    border: none;
    border-radius: 6px;
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
    gridline-color: #30363d;
    border: 1px solid #30363d;
    border-radius: 8px;
    selection-background-color: #1f6feb;
}

QTableWidget::item {
    padding: 8px;
    border: none;
}

QTableWidget::item:selected {
    background-color: #1f6feb;
    color: #ffffff;
}

QHeaderView::section {
    background-color: #161b22;
    color: #8b949e;
    padding: 10px;
    border: none;
    border-bottom: 2px solid #30363d;
    font-weight: 600;
    font-size: 12px;
    text-transform: uppercase;
}

/* Text Edit / Line Edit */
QTextEdit, QLineEdit {
    background-color: #0d1117;
    color: #c9d1d9;
    border: 1px solid #30363d;
    border-radius: 6px;
    padding: 8px;
    selection-background-color: #1f6feb;
}

QTextEdit:focus, QLineEdit:focus {
    border-color: #1f6feb;
}

/* ComboBox */
QComboBox {
    background-color: #0d1117;
    color: #c9d1d9;
    border: 1px solid #30363d;
    border-radius: 6px;
    padding: 8px 12px;
    font-size: 13px;
}

QComboBox:hover {
    border-color: #8b949e;
}

QComboBox::drop-down {
    border: none;
    width: 20px;
}

QComboBox::down-arrow {
    image: none;
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-top: 5px solid #8b949e;
    margin-right: 8px;
}

QComboBox QAbstractItemView {
    background-color: #161b22;
    color: #c9d1d9;
    selection-background-color: #1f6feb;
    border: 1px solid #30363d;
    border-radius: 6px;
}

/* Progress Bar */
QProgressBar {
    background-color: #161b22;
    border: 1px solid #30363d;
    border-radius: 6px;
    text-align: center;
    color: #c9d1d9;
    height: 8px;
}

QProgressBar::chunk {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #2ea043, stop:1 #1f6feb);
    border-radius: 6px;
}

/* Status Bar */
QStatusBar {
    background-color: #161b22;
    color: #8b949e;
    border-top: 1px solid #30363d;
    font-size: 12px;
}

/* Scroll Bar */
QScrollBar:vertical {
    background-color: transparent;
    width: 10px;
    border-radius: 5px;
}

QScrollBar::handle:vertical {
    background-color: #30363d;
    border-radius: 5px;
    min-height: 30px;
}

QScrollBar::handle:vertical:hover {
    background-color: #484f58;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}

/* CheckBox */
QCheckBox {
    color: #c9d1d9;
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
    border-color: #8b949e;
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
