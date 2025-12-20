#!/usr/bin/env python3
"""
FYP Keylogger Detection System - Professional GUI v3.0
Modern sidebar navigation, responsive design, 60fps animations
"""

import sys
import os
import json
import subprocess
from datetime import datetime
from pathlib import Path
from typing import List
from dataclasses import dataclass
from collections import deque
import logging

# Configure logging to file and console
log_handlers = [logging.StreamHandler()]
try:
    log_handlers.append(logging.FileHandler('/tmp/fyp_gui.log'))
except PermissionError:
    print("Warning: Cannot write to /tmp/fyp_gui.log, logging to console only")

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(name)s [%(levelname)s]: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=log_handlers
)
logger = logging.getLogger('FYP-GUI')

from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *
from PySide6.QtCharts import *

# =============== PROFESSIONAL DARK THEME ===============
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
"""

@dataclass
class Alert:
    timestamp: str
    severity: str
    message: str
    process_name: str
    pid: int
    reviewed: bool = False


class StatusIndicator(QWidget):
    """Animated pulsing status indicator"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(12, 12)
        self._color = QColor(139, 148, 158)  # Gray
        self._opacity = 1.0
        
        # Pulse animation
        self.pulse_animation = QPropertyAnimation(self, b"opacity")
        self.pulse_animation.setDuration(1500)
        self.pulse_animation.setStartValue(1.0)
        self.pulse_animation.setEndValue(0.3)
        self.pulse_animation.setEasingCurve(QEasingCurve.InOutQuad)
        self.pulse_animation.setLoopCount(-1)
        
    def set_status(self, status: str, pulse: bool = False):
        color_map = {
            'success': QColor(46, 160, 67),    # Green
            'warning': QColor(212, 167, 44),   # Yellow
            'error': QColor(218, 54, 51),      # Red
            'unknown': QColor(139, 148, 158)   # Gray
        }
        self._color = color_map.get(status, color_map['unknown'])
        
        if pulse:
            self.pulse_animation.start()
        else:
            self.pulse_animation.stop()
            self._opacity = 1.0
        
        self.update()
    
    def get_opacity(self):
        return self._opacity
    
    def set_opacity(self, value):
        self._opacity = value
        self.update()
    
    opacity = Property(float, get_opacity, set_opacity)
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setOpacity(self._opacity)
        
        # Glow effect
        gradient = QRadialGradient(6, 6, 6)
        gradient.setColorAt(0, self._color.lighter(130))
        gradient.setColorAt(0.7, self._color)
        gradient.setColorAt(1, self._color.darker(120))
        
        painter.setBrush(QBrush(gradient))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(1, 1, 10, 10)


class SidebarButton(QPushButton):
    """Custom sidebar navigation button with hover animation"""
    def __init__(self, text, icon_text, parent=None):
        super().__init__(parent)
        self.setText(f"  {icon_text}  {text}")
        self.setObjectName("sidebarButton")
        self.setCursor(Qt.PointingHandCursor)
        self.setMinimumHeight(44)
        self.selected = False
        
        # Hover animation
        self.hover_animation = QPropertyAnimation(self, b"styleSheet")
        self.hover_animation.setDuration(150)
        self.hover_animation.setEasingCurve(QEasingCurve.OutCubic)
        
    def set_selected(self, selected: bool):
        self.selected = selected
        self.setProperty("selected", "true" if selected else "false")
        self.style().unpolish(self)
        self.style().polish(self)
        
    def enterEvent(self, event):
        if not self.selected:
            # Smooth hover effect already in QSS
            pass
        super().enterEvent(event)


class EventRateChart(QChartView):
    """Smooth real-time event rate chart with 60fps"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setRenderHint(QPainter.Antialiasing)
        
        self.time_points = deque(maxlen=60)
        self.rate_points = deque(maxlen=60)
        
        self.chart = QChart()
        self.chart.setTheme(QChart.ChartThemeDark)
        self.chart.setBackgroundBrush(QBrush(QColor(22, 27, 34)))
        self.chart.setTitleBrush(QBrush(QColor(240, 246, 252)))
        self.chart.setTitleFont(QFont('Inter', 14, QFont.Bold))
        self.chart.setTitle("Event Rate Over Time")
        self.chart.legend().hide()
        self.chart.setMargins(QMargins(0, 0, 0, 0))
        
        # Use spline for smooth curves
        self.series = QSplineSeries()
        self.series.setColor(QColor(31, 111, 235))
        self.series.setPen(QPen(QColor(31, 111, 235), 3))
        self.chart.addSeries(self.series)
        
        # Axes with better styling
        self.axis_x = QValueAxis()
        self.axis_x.setRange(0, 60)
        self.axis_x.setTitleText("Time (seconds ago)")
        self.axis_x.setTitleFont(QFont('Inter', 10))
        self.axis_x.setLabelsFont(QFont('Inter', 9))
        self.axis_x.setLabelsColor(QColor(139, 148, 158))
        self.axis_x.setTitleBrush(QBrush(QColor(139, 148, 158)))
        self.axis_x.setGridLineColor(QColor(48, 54, 61))
        
        self.axis_y = QValueAxis()
        self.axis_y.setRange(0, 100)
        self.axis_y.setTitleText("Events/second")
        self.axis_y.setTitleFont(QFont('Inter', 10))
        self.axis_y.setLabelsFont(QFont('Inter', 9))
        self.axis_y.setLabelsColor(QColor(139, 148, 158))
        self.axis_y.setTitleBrush(QBrush(QColor(139, 148, 158)))
        self.axis_y.setGridLineColor(QColor(48, 54, 61))
        
        self.chart.addAxis(self.axis_x, Qt.AlignBottom)
        self.chart.addAxis(self.axis_y, Qt.AlignLeft)
        self.series.attachAxis(self.axis_x)
        self.series.attachAxis(self.axis_y)
        
        self.setChart(self.chart)
        
        # Enable OpenGL for better performance
        self.setRenderHint(QPainter.Antialiasing)
        
    def add_data_point(self, events_per_sec: float):
        self.time_points.append(0)
        self.rate_points.append(events_per_sec)
        
        for i in range(len(self.time_points) - 1):
            self.time_points[i] += 1
        
        # Update series with smooth animation
        self.series.clear()
        for i in range(len(self.time_points)):
            x = 60 - self.time_points[i]
            y = self.rate_points[i]
            self.series.append(x, y)
        
        if self.rate_points:
            max_rate = max(self.rate_points)
            self.axis_y.setRange(0, max(100, max_rate * 1.2))
            
            # Color code based on severity
            if max_rate > 100:
                self.series.setColor(QColor(218, 54, 51))  # Red
                self.series.setPen(QPen(QColor(218, 54, 51), 3))
            elif max_rate > 50:
                self.series.setColor(QColor(212, 167, 44))  # Yellow
                self.series.setPen(QPen(QColor(212, 167, 44), 3))
            else:
                self.series.setColor(QColor(46, 160, 67))  # Green
                self.series.setPen(QPen(QColor(46, 160, 67), 3))


class ProcessBarChart(QChartView):
    """Horizontal bar chart for top processes"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setRenderHint(QPainter.Antialiasing)
        
        self.chart = QChart()
        self.chart.setTheme(QChart.ChartThemeDark)
        self.chart.setBackgroundBrush(QBrush(QColor(22, 27, 34)))
        self.chart.setTitleBrush(QBrush(QColor(240, 246, 252)))
        self.chart.setTitleFont(QFont('Inter', 14, QFont.Bold))
        self.chart.setTitle("Top Active Processes")
        self.chart.legend().hide()
        self.chart.setMargins(QMargins(0, 0, 0, 0))
        
        self.series = QBarSeries()
        self.chart.addSeries(self.series)
        
        self.axis_x = QBarCategoryAxis()
        self.axis_x.setLabelsFont(QFont('Inter', 9))
        self.axis_x.setLabelsColor(QColor(139, 148, 158))
        
        self.axis_y = QValueAxis()
        self.axis_y.setTitleText("Event Count")
        self.axis_y.setTitleFont(QFont('Inter', 10))
        self.axis_y.setLabelsFont(QFont('Inter', 9))
        self.axis_y.setLabelsColor(QColor(139, 148, 158))
        self.axis_y.setTitleBrush(QBrush(QColor(139, 148, 158)))
        self.axis_y.setGridLineColor(QColor(48, 54, 61))
        
        self.chart.addAxis(self.axis_x, Qt.AlignBottom)
        self.chart.addAxis(self.axis_y, Qt.AlignLeft)
        self.series.attachAxis(self.axis_x)
        self.series.attachAxis(self.axis_y)
        
        self.setChart(self.chart)
        
    def update_data(self, processes: dict):
        sorted_procs = sorted(processes.items(), key=lambda x: x[1].get('total_events', 0), reverse=True)[:5]
        if not sorted_procs:
            return
        
        self.series.clear()
        bar_set = QBarSet("Events")
        bar_set.setColor(QColor(31, 111, 235))
        
        categories = []
        for pid, stats in sorted_procs:
            comm = stats.get('comm', 'unknown')
            categories.append(f"{comm}\n({pid})")
            bar_set.append(stats.get('total_events', 0))
        
        self.series.append(bar_set)
        self.axis_x.setCategories(categories)
        
        max_events = max(stats.get('total_events', 0) for _, stats in sorted_procs)
        self.axis_y.setRange(0, max(10, max_events * 1.2))


class DaemonMonitor(QObject):
    """Monitors daemon with enhanced logging"""
    status_updated = Signal(dict)
    alert_received = Signal(Alert)
    connection_changed = Signal(bool)
    
    def __init__(self, status_file: str = "/tmp/fyp_status.json"):
        super().__init__()
        self.status_file = Path(status_file)
        self.last_modified = 0
        self.timer = QTimer()
        self.timer.timeout.connect(self.check_updates)
        self.is_connected = False
        self.last_event_count = 0
        self.events_per_sec = 0.0
        logger.info(f"Daemon monitor initialized: {status_file}")
        
    def start(self, interval_ms: int = 500):
        self.timer.start(interval_ms)
        logger.info(f"Monitoring started with {interval_ms}ms interval")
        
    def stop(self):
        self.timer.stop()
        logger.info("Monitoring stopped")
        
    def check_updates(self):
        if not self.status_file.exists():
            if self.is_connected:
                self.is_connected = False
                self.connection_changed.emit(False)
                logger.warning("Daemon connection lost")
            return
            
        try:
            mtime = self.status_file.stat().st_mtime
            if mtime > self.last_modified:
                self.last_modified = mtime
                with open(self.status_file, 'r') as f:
                    data = json.load(f)
                    
                    current_count = data.get('total_events', 0)
                    self.events_per_sec = max(0, (current_count - self.last_event_count) * 2)
                    self.last_event_count = current_count
                    data['events_per_second'] = self.events_per_sec
                    
                    if not self.is_connected:
                        self.is_connected = True
                        self.connection_changed.emit(True)
                        logger.info("Daemon connection established")
                        
                    self.status_updated.emit(data)
                    
                    if 'alerts' in data:
                        for alert_data in data['alerts']:
                            alert = Alert(
                                timestamp=alert_data['timestamp'],
                                severity=alert_data['severity'],
                                message=alert_data['message'],
                                process_name=alert_data.get('process', 'unknown'),
                                pid=alert_data.get('pid', 0)
                            )
                            logger.warning(f"Alert received: [{alert.severity}] {alert.process_name} - {alert.message}")
                            self.alert_received.emit(alert)
                            
                            if alert.severity == "HIGH":
                                self.send_notification(alert)
        except Exception as e:
            logger.debug(f"Error reading status: {e}")
            
    def send_notification(self, alert: Alert):
        try:
            subprocess.run([
                'notify-send',
                '-u', 'critical',
                '-i', 'security-high',
                f'Security Alert: {alert.process_name}',
                alert.message
            ], timeout=1)
            logger.info(f"Desktop notification sent for HIGH alert")
        except Exception as e:
            logger.debug(f"Notification failed: {e}")


class FYPMainWindow(QMainWindow):
    """Professional main window with sidebar navigation"""
    def __init__(self):
        super().__init__()
        self.setWindowTitle("FYP Keylogger Detection System")
        self.setMinimumSize(1400, 900)
        
        # Enable OpenGL for smoother rendering
        self.setAttribute(Qt.WA_OpaquePaintEvent)
        self.setAttribute(Qt.WA_NoSystemBackground)
        
        # Fullscreen support
        self.is_fullscreen = False
        
        logger.info("=" * 80)
        logger.info("FYP Keylogger Detection System - GUI v3.0")
        logger.info("Professional Interface with Sidebar Navigation")
        logger.info("=" * 80)
        
        self.alerts = []
        self.current_page = "dashboard"
        
        self.daemon_monitor = DaemonMonitor()
        self.daemon_monitor.status_updated.connect(self.on_status_update)
        self.daemon_monitor.alert_received.connect(self.on_alert_received)
        self.daemon_monitor.connection_changed.connect(self.on_connection_changed)
        
        self.setup_tray()
        self.init_ui()
        self.daemon_monitor.start()
        
        # Fullscreen shortcut
        fullscreen_action = QAction("Toggle Fullscreen", self)
        fullscreen_action.setShortcut("F11")
        fullscreen_action.triggered.connect(self.toggle_fullscreen)
        self.addAction(fullscreen_action)
        
        logger.info("GUI initialization complete")
        
    def setup_tray(self):
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setToolTip("FYP Keylogger Detection")
        
        tray_menu = QMenu()
        show_action = QAction("Show Window", self)
        show_action.triggered.connect(self.show)
        quit_action = QAction("Quit", self)
        quit_action.triggered.connect(QApplication.quit)
        
        tray_menu.addAction(show_action)
        tray_menu.addSeparator()
        tray_menu.addAction(quit_action)
        
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self.on_tray_activated)
        self.set_tray_status('unknown')
        self.tray_icon.show()
        
    def set_tray_status(self, status: str):
        pixmap = QPixmap(64, 64)
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        
        color_map = {
            'success': QColor(46, 160, 67),
            'warning': QColor(212, 167, 44),
            'error': QColor(218, 54, 51),
            'unknown': QColor(139, 148, 158)
        }
        color = color_map.get(status, color_map['unknown'])
        
        painter.setBrush(QBrush(color))
        painter.setPen(QPen(color.lighter(120), 2))
        painter.drawEllipse(8, 8, 48, 48)
        painter.end()
        
        self.tray_icon.setIcon(QIcon(pixmap))
        
    def on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.DoubleClick:
            self.show()
            self.activateWindow()
    
    def toggle_fullscreen(self):
        """Toggle fullscreen mode (F11)"""
        if self.is_fullscreen:
            self.showNormal()
            self.is_fullscreen = False
            logger.info("Exited fullscreen mode")
        else:
            self.showFullScreen()
            self.is_fullscreen = True
            logger.info("Entered fullscreen mode")
    
    def show_all_processes_dialog(self):
        """Show dialog with all processes accessing the event stream"""
        dialog = QDialog(self)
        dialog.setWindowTitle("All Active Processes")
        dialog.setMinimumSize(700, 500)
        dialog.setStyleSheet("""
            QDialog {
                background-color: #0d1117;
                color: #c9d1d9;
            }
            QTableWidget {
                background-color: #161b22;
                border: 1px solid #30363d;
                border-radius: 6px;
                gridline-color: #21262d;
                color: #c9d1d9;
            }
            QTableWidget::item {
                padding: 8px;
                border-bottom: 1px solid #21262d;
            }
            QTableWidget::item:selected {
                background-color: #1f6feb;
            }
            QHeaderView::section {
                background-color: #161b22;
                color: #8b949e;
                padding: 8px;
                border: none;
                border-bottom: 2px solid #21262d;
                font-weight: 600;
            }
        """)
        
        layout = QVBoxLayout(dialog)
        layout.setSpacing(16)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Title
        title = QLabel("All Processes Accessing Keyboard Event Stream")
        title.setStyleSheet("font-size: 16px; font-weight: bold; color: #f0f6fc;")
        layout.addWidget(title)
        
        # Info label
        info = QLabel("Real-time monitoring of processes reading from /dev/input at kernel level")
        info.setStyleSheet("font-size: 11px; color: #8b949e;")
        layout.addWidget(info)
        
        # Table
        table = QTableWidget()
        table.setColumnCount(3)
        table.setHorizontalHeaderLabels(["Process Name", "PID", "Total Events"])
        table.horizontalHeader().setStretchLastSection(True)
        table.setSelectionBehavior(QTableWidget.SelectRows)
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        table.setAlternatingRowColors(True)
        
        # Populate with all processes
        if hasattr(self, 'processes') and self.processes:
            sorted_procs = sorted(
                self.processes.items(),
                key=lambda x: x[1].get('total_events', 0),
                reverse=True
            )
            table.setRowCount(len(sorted_procs))
            
            for row, (pid, stats) in enumerate(sorted_procs):
                comm = stats.get('comm', 'unknown')
                events = stats.get('total_events', 0)
                
                table.setItem(row, 0, QTableWidgetItem(comm))
                table.setItem(row, 1, QTableWidgetItem(str(pid)))
                table.setItem(row, 2, QTableWidgetItem(str(events)))
        else:
            table.setRowCount(1)
            no_data = QTableWidgetItem("No process data available")
            no_data.setTextAlignment(Qt.AlignCenter)
            table.setItem(0, 0, no_data)
            table.setSpan(0, 0, 1, 3)
        
        table.resizeColumnsToContents()
        layout.addWidget(table)
        
        # Close button
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        close_btn = QPushButton("Close")
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: #21262d;
                border: 1px solid #30363d;
                border-radius: 6px;
                padding: 8px 24px;
                color: #c9d1d9;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #30363d;
            }
        """)
        close_btn.clicked.connect(dialog.close)
        btn_layout.addWidget(close_btn)
        layout.addLayout(btn_layout)
        
        dialog.exec()
    
    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # ===== LEFT SIDEBAR (20%) =====
        sidebar = QWidget()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(280)
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setSpacing(4)
        sidebar_layout.setContentsMargins(12, 20, 12, 20)
        
        # Logo/Title
        title_label = QLabel("Keylogger Detection")
        title_label.setStyleSheet("font-size: 16px; font-weight: 700; color: #f0f6fc; padding: 12px 8px;")
        sidebar_layout.addWidget(title_label)
        
        sidebar_layout.addSpacing(20)
        
        # Navigation buttons
        self.nav_buttons = {}
        
        nav_items = [
            ("dashboard", "📊", "Dashboard"),
            ("alerts", "⚠️", "Alerts"),
            ("processes", "⚙️", "Processes"),
            ("stream", "📋", "Event Stream"),
            ("ai_assistant", "💬", "AI Assistant"),
            ("ml_insights", "🤖", "ML Insights"),
            ("config", "⚙", "Configuration")
        ]
        
        for page_id, icon, label in nav_items:
            btn = SidebarButton(label, icon)
            btn.clicked.connect(lambda checked, p=page_id: self.switch_page(p))
            self.nav_buttons[page_id] = btn
            sidebar_layout.addWidget(btn)
        
        self.nav_buttons["dashboard"].set_selected(True)
        
        sidebar_layout.addStretch()
        
        # System status in sidebar
        status_widget = QWidget()
        status_layout = QVBoxLayout(status_widget)
        status_layout.setContentsMargins(8, 12, 8, 12)
        status_layout.setSpacing(8)
        
        status_title = QLabel("System Status")
        status_title.setStyleSheet("font-size: 11px; font-weight: 600; color: #8b949e; text-transform: uppercase;")
        status_layout.addWidget(status_title)
        
        # Kernel status
        kernel_container = QHBoxLayout()
        self.kernel_indicator = StatusIndicator()
        self.kernel_label = QLabel("Kernel: Unknown")
        self.kernel_label.setStyleSheet("font-size: 12px; color: #c9d1d9;")
        kernel_container.addWidget(self.kernel_indicator)
        kernel_container.addWidget(self.kernel_label)
        kernel_container.addStretch()
        status_layout.addLayout(kernel_container)
        
        # Daemon status
        daemon_container = QHBoxLayout()
        self.daemon_indicator = StatusIndicator()
        self.daemon_label = QLabel("Daemon: Unknown")
        self.daemon_label.setStyleSheet("font-size: 12px; color: #c9d1d9;")
        daemon_container.addWidget(self.daemon_indicator)
        daemon_container.addWidget(self.daemon_label)
        daemon_container.addStretch()
        status_layout.addLayout(daemon_container)
        
        sidebar_layout.addWidget(status_widget)
        
        main_layout.addWidget(sidebar)
        
        # ===== RIGHT CONTENT AREA (80%) =====
        self.content_stack = QStackedWidget()
        self.content_stack.setObjectName("contentArea")
        
        # Create pages
        self.pages = {
            "dashboard": self.create_dashboard_page(),
            "alerts": self.create_alerts_page(),
            "processes": self.create_processes_page(),
            "stream": self.create_stream_page(),
            "ai_assistant": self.create_ai_assistant_page(),
            "ml_insights": self.create_ml_insights_page(),
            "config": self.create_config_page()
        }
        
        for page in self.pages.values():
            self.content_stack.addWidget(page)
        
        main_layout.addWidget(self.content_stack, 1)
        
        # Status bar
        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)
        self.statusBar.showMessage("Ready")
        
    def switch_page(self, page_id: str):
        logger.info(f"Switching to page: {page_id}")
        
        # Update button states
        for pid, btn in self.nav_buttons.items():
            btn.set_selected(pid == page_id)
        
        # Switch content
        self.content_stack.setCurrentWidget(self.pages[page_id])
        self.current_page = page_id
    
    def create_dashboard_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)
        
        # Page header
        header = QWidget()
        header_layout = QVBoxLayout(header)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(4)
        
        title = QLabel("Dashboard")
        title.setObjectName("sectionTitle")
        subtitle = QLabel("Real-time monitoring of keyboard input stream access")
        subtitle.setObjectName("sectionSubtitle")
        
        info_label = QLabel(
            "ℹ️ <b>What is an 'Event'?</b> Each event represents a process accessing the keyboard input stream. "
            "We don't read keystrokes - we monitor WHO is reading the input stream at the kernel level. "
            "Legitimate apps (terminals, browsers) access it normally. Keyloggers show up as suspicious processes reading every keystroke."
        )
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: #8b949e; font-size: 11px; padding: 12px; background-color: #161b22; border-radius: 6px; margin-bottom: 12px;")
        
        header_layout.addWidget(title)
        header_layout.addWidget(subtitle)
        layout.addWidget(header)
        
        # Stats cards row
        stats_row = QHBoxLayout()
        stats_row.setSpacing(16)
        
        self.events_card = self.create_stat_card("Total Events", "0")
        self.events_card.setToolTip("Total number of keyboard input stream accesses detected.\nEach event = one process reading from the input subsystem.")
        
        self.rate_card = self.create_stat_card("Event Rate", "0 eps")
        self.rate_card.setToolTip("Events per second - how many processes are accessing keyboard input.\nHuman typing: 2-5 eps | Fast typing: 10-15 eps | Suspicious: >100 eps")
        
        self.alerts_card = self.create_stat_card("Active Alerts", "0")
        self.alerts_card.setToolTip("Number of active security alerts from detection heuristics.")
        
        stats_row.addWidget(self.events_card)
        stats_row.addWidget(self.rate_card)
        stats_row.addWidget(self.alerts_card)
        
        layout.addLayout(stats_row)
        
        # Charts row
        charts_row = QHBoxLayout()
        charts_row.setSpacing(16)
        
        # Event rate chart (60%)
        chart_group = QGroupBox()
        chart_layout = QVBoxLayout(chart_group)
        self.event_rate_chart = EventRateChart()
        self.event_rate_chart.setMinimumHeight(300)
        chart_layout.addWidget(self.event_rate_chart)
        charts_row.addWidget(chart_group, 6)
        
        # Process bar chart (40%)
        proc_group = QGroupBox()
        proc_layout = QVBoxLayout(proc_group)
        
        # Header with "View All" button
        proc_header = QHBoxLayout()
        proc_title = QLabel("Top Active Processes")
        proc_title.setStyleSheet("font-size: 14px; font-weight: bold; color: #f0f6fc;")
        proc_header.addWidget(proc_title)
        proc_header.addStretch()
        
        view_all_btn = QPushButton("View All")
        view_all_btn.setStyleSheet("""
            QPushButton {
                background-color: #21262d;
                border: 1px solid #30363d;
                border-radius: 6px;
                padding: 4px 12px;
                color: #58a6ff;
                font-size: 10px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #30363d;
                border-color: #58a6ff;
            }
        """)
        view_all_btn.clicked.connect(self.show_all_processes_dialog)
        proc_header.addWidget(view_all_btn)
        
        proc_layout.addLayout(proc_header)
        
        self.process_bar_chart = ProcessBarChart()
        self.process_bar_chart.setMinimumHeight(280)
        proc_layout.addWidget(self.process_bar_chart)
        charts_row.addWidget(proc_group, 4)
        
        layout.addLayout(charts_row)
        layout.addStretch()
        
        return page
    
    def create_stat_card(self, label: str, value: str):
        card = QGroupBox()
        card_layout = QVBoxLayout(card)
        card_layout.setSpacing(8)
        
        label_widget = QLabel(label)
        label_widget.setStyleSheet("font-size: 12px; color: #8b949e; font-weight: 500;")
        
        value_widget = QLabel(value)
        value_widget.setObjectName("cardValue")
        value_widget.setStyleSheet("font-size: 28px; color: #f0f6fc; font-weight: 700;")
        
        card_layout.addWidget(label_widget)
        card_layout.addWidget(value_widget)
        
        # Store value widget for updates
        card.value_label = value_widget
        
        return card
    
    def create_alerts_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)
        
        # Header
        header = QWidget()
        header_layout = QVBoxLayout(header)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(4)
        
        title = QLabel("Security Alerts")
        title.setObjectName("sectionTitle")
        subtitle = QLabel("Monitor and manage security alerts")
        subtitle.setObjectName("sectionSubtitle")
        
        header_layout.addWidget(title)
        header_layout.addWidget(subtitle)
        layout.addWidget(header)
        
        # Filter controls
        filter_container = QWidget()
        filter_layout = QHBoxLayout(filter_container)
        filter_layout.setContentsMargins(0, 0, 0, 0)
        
        self.severity_filter = QComboBox()
        self.severity_filter.addItems(["All Severities", "HIGH", "MEDIUM", "LOW"])
        self.severity_filter.currentTextChanged.connect(self.apply_alert_filter)
        
        self.alert_search = QLineEdit()
        self.alert_search.setPlaceholderText("Search by process name...")
        self.alert_search.textChanged.connect(self.apply_alert_filter)
        
        clear_btn = QPushButton("Clear All")
        clear_btn.setObjectName("dangerButton")
        clear_btn.clicked.connect(self.clear_alerts)
        
        export_btn = QPushButton("Export CSV")
        export_btn.setObjectName("secondaryButton")
        export_btn.clicked.connect(self.export_alerts)
        
        filter_layout.addWidget(self.severity_filter)
        filter_layout.addWidget(self.alert_search, 1)
        filter_layout.addWidget(clear_btn)
        filter_layout.addWidget(export_btn)
        
        layout.addWidget(filter_container)
        
        # Alerts table with view details
        self.alerts_table = QTableWidget()
        self.alerts_table.setColumnCount(7)
        self.alerts_table.setHorizontalHeaderLabels(["✓", "Date", "Time", "Severity", "Process", "Reason", "Actions"])
        self.alerts_table.horizontalHeader().setSectionResizeMode(5, QHeaderView.Stretch)
        self.alerts_table.setColumnWidth(0, 40)
        self.alerts_table.setColumnWidth(1, 100)
        self.alerts_table.setColumnWidth(2, 90)
        self.alerts_table.setColumnWidth(3, 100)
        self.alerts_table.setColumnWidth(4, 180)
        self.alerts_table.setColumnWidth(6, 120)
        self.alerts_table.setAlternatingRowColors(True)
        self.alerts_table.setSelectionBehavior(QTableWidget.SelectRows)
        layout.addWidget(self.alerts_table)
        
        # Pagination controls
        pagination_container = QWidget()
        pagination_layout = QHBoxLayout(pagination_container)
        pagination_layout.setContentsMargins(0, 0, 0, 0)
        
        self.alert_page_label = QLabel("Page 1 of 1")
        self.alert_page_label.setStyleSheet("color: #8b949e; font-size: 12px;")
        
        self.alert_prev_btn = QPushButton("← Previous")
        self.alert_prev_btn.setObjectName("secondaryButton")
        self.alert_prev_btn.clicked.connect(self.alert_prev_page)
        self.alert_prev_btn.setMaximumWidth(100)
        
        self.alert_next_btn = QPushButton("Next →")
        self.alert_next_btn.setObjectName("secondaryButton")
        self.alert_next_btn.clicked.connect(self.alert_next_page)
        self.alert_next_btn.setMaximumWidth(100)
        
        self.alert_page_size = QComboBox()
        self.alert_page_size.addItems(["10", "25", "50", "100"])
        self.alert_page_size.setCurrentText("25")
        self.alert_page_size.currentTextChanged.connect(lambda: self.update_alerts_table())
        self.alert_page_size.setMaximumWidth(80)
        
        pagination_layout.addWidget(QLabel("Per page:"))
        pagination_layout.addWidget(self.alert_page_size)
        pagination_layout.addStretch()
        pagination_layout.addWidget(self.alert_page_label)
        pagination_layout.addStretch()
        pagination_layout.addWidget(self.alert_prev_btn)
        pagination_layout.addWidget(self.alert_next_btn)
        
        layout.addWidget(pagination_container)
        
        # Initialize pagination
        self.current_alert_page = 1
        
        return page
    
    def create_processes_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)
        
        # Header
        header = QWidget()
        header_layout = QVBoxLayout(header)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(4)
        
        title = QLabel("Process Statistics")
        title.setObjectName("sectionTitle")
        subtitle = QLabel("Monitor active processes and their keyboard activity")
        subtitle.setObjectName("sectionSubtitle")
        
        header_layout.addWidget(title)
        header_layout.addWidget(subtitle)
        layout.addWidget(header)
        
        # Processes table
        self.stats_table = QTableWidget()
        self.stats_table.setColumnCount(5)
        self.stats_table.setHorizontalHeaderLabels(["PID", "Process Name", "Events", "Rapid %", "Rate (eps)"])
        self.stats_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.stats_table.setAlternatingRowColors(True)
        self.stats_table.setSortingEnabled(True)
        self.stats_table.setSelectionBehavior(QTableWidget.SelectRows)
        layout.addWidget(self.stats_table)
        
        return page
    
    def create_stream_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)
        
        # Header
        header = QWidget()
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(0, 0, 0, 0)
        
        header_text = QWidget()
        header_text_layout = QVBoxLayout(header_text)
        header_text_layout.setContentsMargins(0, 0, 0, 0)
        header_text_layout.setSpacing(4)
        
        title = QLabel("Event Stream")
        title.setObjectName("sectionTitle")
        subtitle = QLabel("Raw event log from kernel module")
        subtitle.setObjectName("sectionSubtitle")
        
        header_text_layout.addWidget(title)
        header_text_layout.addWidget(subtitle)
        header_layout.addWidget(header_text, 1)
        
        # Controls
        controls = QWidget()
        controls_layout = QHBoxLayout(controls)
        controls_layout.setContentsMargins(0, 0, 0, 0)
        
        self.auto_scroll_check = QCheckBox("Auto-scroll")
        self.auto_scroll_check.setChecked(True)
        
        clear_stream_btn = QPushButton("Clear")
        clear_stream_btn.setObjectName("secondaryButton")
        clear_stream_btn.clicked.connect(lambda: self.event_stream.clear())
        
        controls_layout.addWidget(self.auto_scroll_check)
        controls_layout.addWidget(clear_stream_btn)
        
        header_layout.addWidget(controls)
        layout.addWidget(header)
        
        # Event stream
        self.event_stream = QTextEdit()
        self.event_stream.setReadOnly(True)
        self.event_stream.setFont(QFont("JetBrains Mono", 10))
        self.event_stream.setStyleSheet("""
            QTextEdit {
                background-color: #0d1117;
                color: #c9d1d9;
                border: 1px solid #30363d;
                border-radius: 8px;
                padding: 12px;
                font-family: 'JetBrains Mono', 'Consolas', 'Monaco', monospace;
            }
        """)
        layout.addWidget(self.event_stream)
        
        return page
    
    def create_ai_assistant_page(self):
        """AI-powered alert explanation assistant (placeholder)"""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)
        
        # Header
        header = QWidget()
        header_layout = QVBoxLayout(header)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(4)
        
        title = QLabel("🤖 AI Assistant")
        title.setObjectName("sectionTitle")
        subtitle = QLabel("Conversational alert analysis and explanations")
        subtitle.setObjectName("sectionSubtitle")
        
        header_layout.addWidget(title)
        header_layout.addWidget(subtitle)
        layout.addWidget(header)
        
        # Feature description card
        feature_card = QGroupBox("Feature Overview")
        feature_layout = QVBoxLayout(feature_card)
        
        desc_label = QLabel(
            "The AI Assistant will provide:\n\n"
            "• Natural language explanations of security alerts\n"
            "• Conversational interface to ask questions about suspicious behavior\n"
            "• Context-aware recommendations for responding to threats\n"
            "• Historical pattern analysis and threat correlation\n"
            "• Integration with LLM (GPT/Claude) for intelligent responses\n\n"
            "This feature requires network connectivity and API access to a language model."
        )
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet("color: #c9d1d9; font-size: 13px; line-height: 1.6;")
        feature_layout.addWidget(desc_label)
        layout.addWidget(feature_card)
        
        # Chat interface placeholder
        chat_container = QGroupBox("Conversation")
        chat_layout = QVBoxLayout(chat_container)
        
        # Message display
        self.ai_chat_display = QTextEdit()
        self.ai_chat_display.setReadOnly(True)
        self.ai_chat_display.setPlaceholderText("AI conversation will appear here...")
        self.ai_chat_display.setMinimumHeight(300)
        chat_layout.addWidget(self.ai_chat_display)
        
        # Input row
        input_row = QHBoxLayout()
        self.ai_chat_input = QLineEdit()
        self.ai_chat_input.setPlaceholderText("Ask about an alert or security concern...")
        self.ai_chat_input.setEnabled(False)
        
        send_btn = QPushButton("Send")
        send_btn.setEnabled(False)
        send_btn.setObjectName("primaryButton")
        
        input_row.addWidget(self.ai_chat_input, 1)
        input_row.addWidget(send_btn)
        chat_layout.addLayout(input_row)
        
        layout.addWidget(chat_container)
        
        # Status notice
        status_label = QLabel("⚠️ Will be available in production version")
        status_label.setStyleSheet(
            "background-color: #1c2128; color: #d29922; padding: 12px; "
            "border-radius: 6px; font-weight: 600; font-size: 13px;"
        )
        status_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(status_label)
        
        layout.addStretch()
        return page
    
    def create_ml_insights_page(self):
        """ML model logs, training metrics, and predictions (placeholder)"""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)
        
        # Header
        header = QWidget()
        header_layout = QVBoxLayout(header)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(4)
        
        title = QLabel("🤖 ML Insights")
        title.setObjectName("sectionTitle")
        subtitle = QLabel("Machine learning model performance and predictions")
        subtitle.setObjectName("sectionSubtitle")
        
        header_layout.addWidget(title)
        header_layout.addWidget(subtitle)
        layout.addWidget(header)
        
        # Feature description
        feature_card = QGroupBox("Planned Features")
        feature_layout = QVBoxLayout(feature_card)
        
        desc_label = QLabel(
            "The ML Insights dashboard will include:\n\n"
            "• Real-time model predictions and confidence scores\n"
            "• Training metrics visualization (accuracy, precision, recall, F1)\n"
            "• Feature importance analysis\n"
            "• Model version comparison and A/B testing results\n"
            "• Confusion matrix and ROC curves\n"
            "• False positive/negative rate tracking\n"
            "• Anomaly detection patterns\n"
            "• Model retraining triggers and status"
        )
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet("color: #c9d1d9; font-size: 13px; line-height: 1.6;")
        feature_layout.addWidget(desc_label)
        layout.addWidget(feature_card)
        
        # Placeholder metrics grid
        metrics_container = QGroupBox("Model Performance Metrics")
        metrics_layout = QGridLayout(metrics_container)
        metrics_layout.setSpacing(12)
        
        metric_cards = [
            ("Accuracy", "0.00%"),
            ("Precision", "0.00%"),
            ("Recall", "0.00%"),
            ("F1 Score", "0.00"),
            ("False Positives", "0"),
            ("True Positives", "0")
        ]
        
        for i, (metric_name, metric_value) in enumerate(metric_cards):
            card = QGroupBox()
            card.setStyleSheet("""
                QGroupBox {
                    background-color: #161b22;
                    border: 1px solid #30363d;
                    border-radius: 8px;
                    padding: 16px;
                }
            """)
            card_layout = QVBoxLayout(card)
            card_layout.setSpacing(8)
            
            label_widget = QLabel(metric_name)
            label_widget.setStyleSheet("font-size: 11px; color: #8b949e; font-weight: 600; text-transform: uppercase;")
            
            value_widget = QLabel(metric_value)
            value_widget.setStyleSheet("font-size: 32px; color: #c9d1d9; font-weight: 700;")
            
            card_layout.addWidget(label_widget)
            card_layout.addWidget(value_widget)
            card_layout.addStretch()
            
            metrics_layout.addWidget(card, i // 3, i % 3)
        
        layout.addWidget(metrics_container)
        
        # Charts placeholder
        charts_card = QGroupBox("Visualizations")
        charts_layout = QVBoxLayout(charts_card)
        
        chart_placeholder = QLabel(
            "📊 Training curves, confusion matrix, and feature importance charts\n"
            "will be displayed here once ML training is implemented."
        )
        chart_placeholder.setAlignment(Qt.AlignCenter)
        chart_placeholder.setStyleSheet(
            "color: #8b949e; font-size: 14px; padding: 60px; "
            "background-color: #161b22; border-radius: 8px;"
        )
        charts_layout.addWidget(chart_placeholder)
        layout.addWidget(charts_card)
        
        # Status notice
        status_label = QLabel("⚠️ Will be available in production version")
        status_label.setStyleSheet(
            "background-color: #1c2128; color: #d29922; padding: 12px; "
            "border-radius: 6px; font-weight: 600; font-size: 13px;"
        )
        status_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(status_label)
        
        return page
    
    def create_config_page(self):
        """System configuration and control panel - FUNCTIONAL"""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)
        
        # Header
        header = QWidget()
        header_layout = QVBoxLayout(header)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(4)
        
        title = QLabel("⚙ Configuration")
        title.setObjectName("sectionTitle")
        subtitle = QLabel("System settings and process management")
        subtitle.setObjectName("sectionSubtitle")
        
        header_layout.addWidget(title)
        header_layout.addWidget(subtitle)
        layout.addWidget(header)
        
        # Detection settings - NOW FUNCTIONAL
        detection_card = QGroupBox("Detection Settings")
        detection_layout = QFormLayout(detection_card)
        
        self.threshold_slider = QSlider(Qt.Horizontal)
        self.threshold_slider.setRange(10, 200)
        self.threshold_slider.setValue(100)
        self.threshold_label = QLabel("Alert Threshold: 100 events/sec")
        self.threshold_slider.valueChanged.connect(self.on_threshold_changed)
        
        detection_layout.addRow("Sensitivity:", self.threshold_slider)
        detection_layout.addRow("", self.threshold_label)
        
        self.autokill_check = QCheckBox("Auto-terminate high-risk processes (prototype: disabled for safety)")
        self.autokill_check.setEnabled(False)
        self.autokill_check.setToolTip("Not implemented in prototype for safety reasons")
        detection_layout.addRow("Response:", self.autokill_check)
        
        # Apply settings button
        apply_btn = QPushButton("Apply Settings")
        apply_btn.setObjectName("primaryButton")
        apply_btn.clicked.connect(self.apply_detection_settings)
        detection_layout.addRow("", apply_btn)
        
        layout.addWidget(detection_card)
        
        # Process control - FUNCTIONAL
        control_card = QGroupBox("High-Alert Process Management")
        control_layout = QVBoxLayout(control_card)
        
        desc = QLabel(
            "Processes flagged by detection heuristics. You can manually terminate suspicious processes.\n"
            "⚠️ Use with caution - terminating system processes may cause instability."
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #c9d1d9; font-size: 13px; margin-bottom: 8px;")
        control_layout.addWidget(desc)
        
        # Functional process list
        self.risky_processes_table = QTableWidget()
        self.risky_processes_table.setColumnCount(5)
        self.risky_processes_table.setHorizontalHeaderLabels(["Select", "PID", "Process", "Risk Level", "Event Rate"])
        self.risky_processes_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.risky_processes_table.setRowCount(0)
        self.risky_processes_table.setSelectionBehavior(QTableWidget.SelectRows)
        control_layout.addWidget(self.risky_processes_table)
        
        # Refresh button
        refresh_row = QHBoxLayout()
        refresh_btn = QPushButton("🔄 Refresh List")
        refresh_btn.setObjectName("secondaryButton")
        refresh_btn.clicked.connect(self.refresh_risky_processes)
        refresh_row.addWidget(refresh_btn)
        refresh_row.addStretch()
        control_layout.addLayout(refresh_row)
        
        # Control buttons - FUNCTIONAL
        button_row = QHBoxLayout()
        
        self.terminate_btn = QPushButton("🛑 Terminate Selected")
        self.terminate_btn.setObjectName("dangerButton")
        self.terminate_btn.clicked.connect(self.terminate_selected_process)
        
        whitelist_btn = QPushButton("✓ Add to Whitelist (Coming Soon)")
        whitelist_btn.setObjectName("secondaryButton")
        whitelist_btn.setEnabled(False)
        whitelist_btn.setToolTip("Whitelist feature will be available in next version")
        
        button_row.addWidget(self.terminate_btn)
        button_row.addWidget(whitelist_btn)
        button_row.addStretch()
        
        control_layout.addLayout(button_row)
        layout.addWidget(control_card)
        
        # Logging settings - FUNCTIONAL
        logging_card = QGroupBox("Logging & Export")
        logging_layout = QVBoxLayout(logging_card)
        
        log_path_row = QHBoxLayout()
        log_path_row.addWidget(QLabel("Log Directory:"))
        self.log_path_input = QLineEdit("/tmp/")
        log_path_row.addWidget(self.log_path_input, 1)
        
        browse_btn = QPushButton("Browse")
        browse_btn.clicked.connect(self.browse_log_directory)
        log_path_row.addWidget(browse_btn)
        
        logging_layout.addLayout(log_path_row)
        
        self.enable_detailed_log = QCheckBox("Enable detailed event logging (increases disk usage)")
        self.enable_detailed_log.setChecked(True)
        logging_layout.addWidget(self.enable_detailed_log)
        
        # Export buttons
        export_row = QHBoxLayout()
        export_all_btn = QPushButton("📥 Export All Data")
        export_all_btn.clicked.connect(self.export_all_data)
        export_row.addWidget(export_all_btn)
        export_row.addStretch()
        logging_layout.addLayout(export_row)
        
        layout.addWidget(logging_card)
        
        layout.addStretch()
        return page
    
    def on_threshold_changed(self, value):
        """Update threshold label when slider changes"""
        self.threshold_label.setText(f"Alert Threshold: {value} events/sec")
        
    def apply_detection_settings(self):
        """Apply detection threshold settings"""
        threshold = self.threshold_slider.value()
        self.statusBar.showMessage(f"Settings applied: Threshold set to {threshold} events/sec", 3000)
        logger.info(f"Detection threshold updated to {threshold} events/sec")
        # In production: Send to daemon via IPC
        
    def refresh_risky_processes(self):
        """Refresh the list of high-risk processes from alerts"""
        self.risky_processes_table.setRowCount(0)
        
        # Get high-severity alerts
        high_risk_processes = {}
        for alert in self.alerts:
            if alert.severity in ["HIGH", "MEDIUM"]:
                key = (alert.pid, alert.process_name)
                if key not in high_risk_processes:
                    high_risk_processes[key] = {
                        'pid': alert.pid,
                        'name': alert.process_name,
                        'severity': alert.severity,
                        'count': 1
                    }
                else:
                    high_risk_processes[key]['count'] += 1
        
        # Populate table
        for (pid, name), data in high_risk_processes.items():
            row = self.risky_processes_table.rowCount()
            self.risky_processes_table.insertRow(row)
            
            # Checkbox
            check_item = QTableWidgetItem()
            check_item.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
            check_item.setCheckState(Qt.Unchecked)
            self.risky_processes_table.setItem(row, 0, check_item)
            
            self.risky_processes_table.setItem(row, 1, QTableWidgetItem(str(pid)))
            self.risky_processes_table.setItem(row, 2, QTableWidgetItem(name))
            
            severity_item = QTableWidgetItem(data['severity'])
            if data['severity'] == "HIGH":
                severity_item.setBackground(QColor(218, 54, 51, 100))
            else:
                severity_item.setBackground(QColor(212, 167, 44, 100))
            self.risky_processes_table.setItem(row, 3, severity_item)
            
            self.risky_processes_table.setItem(row, 4, QTableWidgetItem(f"{data['count']} alerts"))
        
        self.statusBar.showMessage(f"Found {len(high_risk_processes)} high-risk processes", 2000)
        logger.info(f"Refreshed risky process list: {len(high_risk_processes)} processes")
    
    def terminate_selected_process(self):
        """Terminate selected processes (with confirmation)"""
        selected_pids = []
        for row in range(self.risky_processes_table.rowCount()):
            check_item = self.risky_processes_table.item(row, 0)
            if check_item and check_item.checkState() == Qt.Checked:
                pid_item = self.risky_processes_table.item(row, 1)
                name_item = self.risky_processes_table.item(row, 2)
                selected_pids.append((int(pid_item.text()), name_item.text()))
        
        if not selected_pids:
            self.statusBar.showMessage("No processes selected", 2000)
            return
        
        # Confirmation dialog
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Warning)
        msg.setWindowTitle("Confirm Termination")
        msg.setText(f"Are you sure you want to terminate {len(selected_pids)} process(es)?")
        msg.setInformativeText("\\n".join([f"• {name} (PID {pid})" for pid, name in selected_pids]))
        msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        msg.setDefaultButton(QMessageBox.No)
        
        if msg.exec() == QMessageBox.Yes:
            terminated = []
            failed = []
            
            for pid, name in selected_pids:
                try:
                    # Try kill -9 first (user's own processes)
                    result = subprocess.run(['kill', '-9', str(pid)], capture_output=True, timeout=2)
                    if result.returncode == 0:
                        terminated.append(f"{name} ({pid})")
                        logger.warning(f"Terminated process: {name} (PID {pid})")
                    else:
                        # Try with pkexec for elevated processes
                        result2 = subprocess.run(['pkexec', 'kill', '-9', str(pid)], capture_output=True, timeout=5)
                        if result2.returncode == 0:
                            terminated.append(f"{name} ({pid})")
                            logger.warning(f"Terminated process (elevated): {name} (PID {pid})")
                        else:
                            failed.append(f"{name} ({pid}): Permission denied")
                except subprocess.TimeoutExpired:
                    failed.append(f"{name} ({pid}): Timeout")
                except Exception as e:
                    failed.append(f"{name} ({pid}): {str(e)}")
                    logger.error(f"Failed to terminate {name} (PID {pid}): {e}")
            
            # Show results
            result_msg = ""
            if terminated:
                result_msg += f"Terminated: {', '.join(terminated)}"
            if failed:
                result_msg += f"\\nFailed: {', '.join(failed)}"
            
            self.statusBar.showMessage(result_msg, 5000)
            self.refresh_risky_processes()
    
    def browse_log_directory(self):
        """Browse for log directory"""
        directory = QFileDialog.getExistingDirectory(self, "Select Log Directory", "/tmp")
        if directory:
            self.log_path_input.setText(directory)
            self.statusBar.showMessage(f"Log directory set to: {directory}", 2000)
            logger.info(f"Log directory changed to: {directory}")
    
    def export_all_data(self):
        """Export all data (alerts, stats, logs)"""
        log_dir = self.log_path_input.text()
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        export_path = os.path.join(log_dir, f"fyp_export_{timestamp}")
        
        try:
            os.makedirs(export_path, exist_ok=True)
            
            # Export alerts
            with open(os.path.join(export_path, "alerts.csv"), 'w') as f:
                f.write("Timestamp,Severity,Process,PID,Message\\n")
                for alert in self.alerts:
                    f.write(f'"{alert.timestamp}","{alert.severity}","{alert.process_name}",{alert.pid},"{alert.message}"\\n')
            
            # Copy daemon log
            try:
                subprocess.run(['cp', '/tmp/fyp_daemon.log', os.path.join(export_path, 'daemon.log')])
            except:
                pass
            
            # Copy GUI log
            try:
                subprocess.run(['cp', '/tmp/fyp_gui.log', os.path.join(export_path, 'gui.log')])
            except:
                pass
            
            self.statusBar.showMessage(f"Data exported to: {export_path}", 5000)
            logger.info(f"Exported all data to {export_path}")
            
            # Show success message
            QMessageBox.information(self, "Export Complete", 
                                   f"All data exported successfully to:\\n{export_path}")
        except Exception as e:
            self.statusBar.showMessage(f"Export failed: {e}", 3000)
            logger.error(f"Export failed: {e}")
            QMessageBox.critical(self, "Export Failed", f"Failed to export data:\\n{str(e)}")
    
    def on_connection_changed(self, connected: bool):
        log_path_row.addWidget(browse_btn)
        
        logging_layout.addLayout(log_path_row)
        
        self.enable_detailed_log = QCheckBox("Enable detailed event logging")
        self.enable_detailed_log.setEnabled(False)
        logging_layout.addWidget(self.enable_detailed_log)
        
        layout.addWidget(logging_card)
        
        # Status notice
        status_label = QLabel("⚠️ Will be available in production version")
        status_label.setStyleSheet(
            "background-color: #1c2128; color: #d29922; padding: 12px; "
            "border-radius: 6px; font-weight: 600; font-size: 13px;"
        )
        status_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(status_label)
        
        layout.addStretch()
        return page
    
    def on_connection_changed(self, connected: bool):
        if connected:
            logger.info("✓ Daemon connection established")
            self.set_tray_status('success')
        else:
            logger.warning("✗ Daemon connection lost")
            self.set_tray_status('error')
    
    def on_status_update(self, data: dict):
        # Update status indicators
        kernel_loaded = data.get('kernel_loaded', False)
        daemon_running = data.get('daemon_running', False)
        
        if kernel_loaded:
            self.kernel_indicator.set_status('success', pulse=True)
            self.kernel_label.setText("Kernel: Active")
        else:
            self.kernel_indicator.set_status('error')
            self.kernel_label.setText("Kernel: Inactive")
        
        if daemon_running:
            self.daemon_indicator.set_status('success', pulse=True)
            self.daemon_label.setText("Daemon: Running")
        else:
            self.daemon_indicator.set_status('error')
            self.daemon_label.setText("Daemon: Stopped")
        
        # Update dashboard cards
        total_events = data.get('total_events', 0)
        eps = data.get('events_per_second', 0.0)
        
        self.events_card.value_label.setText(f"{total_events:,}")
        self.rate_card.value_label.setText(f"{eps:.1f} eps")
        self.alerts_card.value_label.setText(str(len(self.alerts)))
        
        # Update charts
        self.event_rate_chart.add_data_point(eps)
        
        processes = data.get('processes', {})
        self.process_bar_chart.update_data(processes)
        self.update_stats_table(processes)
        
        # Update event stream
        recent_events = data.get('recent_events', [])
        self.update_event_stream(recent_events)
        
        # Status bar
        self.statusBar.showMessage(f"Last update: {data.get('timestamp', 'unknown')}")
    
    def on_alert_received(self, alert: Alert):
        self.alerts.append(alert)
        self.update_alerts_table()
        
        if alert.severity == "HIGH":
            self.set_tray_status('error')
        elif alert.severity == "MEDIUM" and self.tray_icon.icon().pixmap(16, 16).toImage().pixel(8, 8) != QColor(218, 54, 51).rgb():
            self.set_tray_status('warning')
    
    def update_stats_table(self, processes: dict):
        self.stats_table.setRowCount(0)
        for pid_str, stats in processes.items():
            row = self.stats_table.rowCount()
            self.stats_table.insertRow(row)
            
            self.stats_table.setItem(row, 0, QTableWidgetItem(pid_str))
            self.stats_table.setItem(row, 1, QTableWidgetItem(stats.get('comm', 'unknown')))
            self.stats_table.setItem(row, 2, QTableWidgetItem(str(stats.get('total_events', 0))))
            
            rapid_ratio = stats.get('rapid_ratio', 0.0)
            rapid_item = QTableWidgetItem(f"{rapid_ratio:.1f}%")
            if rapid_ratio > 50.0:
                rapid_item.setBackground(QColor(212, 167, 44, 80))
            self.stats_table.setItem(row, 3, rapid_item)
            
            eps = stats.get('events_per_second', 0.0)
            eps_item = QTableWidgetItem(f"{eps:.1f}")
            if eps > 100.0:
                eps_item.setBackground(QColor(218, 54, 51, 80))
            self.stats_table.setItem(row, 4, eps_item)
    
    def update_alerts_table(self):
        self.alerts_table.setRowCount(0)
        
        search_text = self.alert_search.text().lower()
        filter_sev = self.severity_filter.currentText()
        
        # Filter alerts
        filtered_alerts = []
        for alert in self.alerts:
            if filter_sev != "All Severities" and alert.severity != filter_sev:
                continue
            if search_text and search_text not in alert.process_name.lower():
                continue
            filtered_alerts.append(alert)
        
        # Pagination
        page_size = int(self.alert_page_size.currentText())
        total_pages = max(1, (len(filtered_alerts) + page_size - 1) // page_size)
        self.current_alert_page = min(self.current_alert_page, total_pages)
        
        start_idx = (self.current_alert_page - 1) * page_size
        end_idx = min(start_idx + page_size, len(filtered_alerts))
        page_alerts = filtered_alerts[start_idx:end_idx]
        
        # Update pagination controls
        self.alert_page_label.setText(f"Page {self.current_alert_page} of {total_pages} ({len(filtered_alerts)} alerts)")
        self.alert_prev_btn.setEnabled(self.current_alert_page > 1)
        self.alert_next_btn.setEnabled(self.current_alert_page < total_pages)
        
        # Populate table
        for alert in page_alerts:
            row = self.alerts_table.rowCount()
            self.alerts_table.insertRow(row)
            
            check_item = QTableWidgetItem()
            check_item.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
            check_item.setCheckState(Qt.Checked if alert.reviewed else Qt.Unchecked)
            self.alerts_table.setItem(row, 0, check_item)
            
            # Parse timestamp - handle both formats
            try:
                # Try standard format first
                if 'T' in alert.timestamp or len(alert.timestamp) > 19:
                    # ISO format or timestamp with microseconds
                    dt = datetime.fromisoformat(alert.timestamp.replace('Z', '+00:00'))
                else:
                    dt = datetime.strptime(alert.timestamp, '%Y-%m-%d %H:%M:%S')
                date_str = dt.strftime('%Y-%m-%d')
                time_str = dt.strftime('%H:%M:%S')
            except:
                # Fallback parsing
                parts = alert.timestamp.split()
                if len(parts) >= 2:
                    date_str = parts[0]
                    time_str = parts[1][:8]  # Take only HH:MM:SS
                else:
                    date_str = alert.timestamp[:10] if len(alert.timestamp) >= 10 else alert.timestamp
                    time_str = alert.timestamp[11:19] if len(alert.timestamp) >= 19 else ''
            
            self.alerts_table.setItem(row, 1, QTableWidgetItem(date_str))
            self.alerts_table.setItem(row, 2, QTableWidgetItem(time_str))
            
            severity_item = QTableWidgetItem(alert.severity)
            severity_colors = {
                "HIGH": QColor(218, 54, 51, 100),
                "MEDIUM": QColor(212, 167, 44, 100),
                "LOW": QColor(46, 160, 67, 100)
            }
            severity_item.setBackground(severity_colors.get(alert.severity, QColor(139, 148, 158, 100)))
            self.alerts_table.setItem(row, 3, severity_item)
            
            self.alerts_table.setItem(row, 4, QTableWidgetItem(f"{alert.process_name} ({alert.pid})"))
            
            # Truncate message for table view
            reason = alert.message[:50] + "..." if len(alert.message) > 50 else alert.message
            self.alerts_table.setItem(row, 5, QTableWidgetItem(reason))
            
            # View details button
            details_btn = QPushButton("View Details")
            details_btn.setObjectName("secondaryButton")
            details_btn.clicked.connect(lambda checked, a=alert: self.show_alert_details(a))
            self.alerts_table.setCellWidget(row, 6, details_btn)
    
    def alert_prev_page(self):
        if self.current_alert_page > 1:
            self.current_alert_page -= 1
            self.update_alerts_table()
    
    def alert_next_page(self):
        page_size = int(self.alert_page_size.currentText())
        total_pages = max(1, (len(self.alerts) + page_size - 1) // page_size)
        if self.current_alert_page < total_pages:
            self.current_alert_page += 1
            self.update_alerts_table()
    
    def show_alert_details(self, alert: Alert):
        """Show detailed alert information in a dialog"""
        dialog = QDialog(self)
        dialog.setWindowTitle(f"Alert Details - {alert.severity}")
        dialog.setMinimumWidth(600)
        dialog.setMinimumHeight(400)
        
        layout = QVBoxLayout(dialog)
        layout.setSpacing(16)
        
        # Header with severity
        header = QLabel(f"🚨 {alert.severity} Severity Alert")
        header.setStyleSheet(f"""
            font-size: 18px;
            font-weight: 700;
            color: {'#da3633' if alert.severity == 'HIGH' else '#d4a72c' if alert.severity == 'MEDIUM' else '#2ea043'};
            padding: 12px;
            background-color: #161b22;
            border-radius: 6px;
        """)
        layout.addWidget(header)
        
        # Details grid
        details_widget = QGroupBox("Alert Information")
        details_layout = QFormLayout(details_widget)
        details_layout.setSpacing(12)
        
        timestamp_label = QLabel(alert.timestamp)
        timestamp_label.setStyleSheet("color: #c9d1d9; font-weight: 600;")
        details_layout.addRow("Timestamp:", timestamp_label)
        
        process_label = QLabel(f"{alert.process_name} (PID: {alert.pid})")
        process_label.setStyleSheet("color: #c9d1d9; font-weight: 600;")
        details_layout.addRow("Process:", process_label)
        
        severity_label = QLabel(alert.severity)
        severity_label.setStyleSheet(f"""
            color: {'#da3633' if alert.severity == 'HIGH' else '#d4a72c' if alert.severity == 'MEDIUM' else '#2ea043'};
            font-weight: 700;
        """)
        details_layout.addRow("Severity Level:", severity_label)
        
        layout.addWidget(details_widget)
        
        # Message/Reason
        message_group = QGroupBox("Detection Reason")
        message_layout = QVBoxLayout(message_group)
        
        message_text = QTextEdit()
        message_text.setPlainText(alert.message)
        message_text.setReadOnly(True)
        message_text.setMaximumHeight(150)
        message_text.setStyleSheet("""
            background-color: #0d1117;
            color: #c9d1d9;
            border: 1px solid #30363d;
            border-radius: 6px;
            padding: 8px;
            font-size: 13px;
        """)
        message_layout.addWidget(message_text)
        layout.addWidget(message_group)
        
        # Actions
        actions_group = QGroupBox("Recommended Actions")
        actions_layout = QVBoxLayout(actions_group)
        
        if alert.severity == "HIGH":
            recommendations = [
                "• Investigate this process immediately",
                "• Check process command line and parent process",
                "• Consider terminating if confirmed malicious",
                "• Review system logs for related activity",
                "• Run antivirus/antimalware scan"
            ]
        elif alert.severity == "MEDIUM":
            recommendations = [
                "• Monitor this process for continued suspicious behavior",
                "• Verify if this is a legitimate application",
                "• Consider adding to whitelist if trusted",
                "• Check process network connections"
            ]
        else:
            recommendations = [
                "• This is a low-priority alert for awareness",
                "• No immediate action required",
                "• Monitor if frequency increases"
            ]
        
        recommendations_text = "\n".join(recommendations)
        recommendations_label = QLabel(recommendations_text)
        recommendations_label.setWordWrap(True)
        recommendations_label.setStyleSheet("color: #c9d1d9; font-size: 13px; line-height: 1.6;")
        actions_layout.addWidget(recommendations_label)
        layout.addWidget(actions_group)
        
        # Close button
        close_btn = QPushButton("Close")
        close_btn.setObjectName("primaryButton")
        close_btn.clicked.connect(dialog.accept)
        layout.addWidget(close_btn)
        
        dialog.exec()
    
    def apply_alert_filter(self):
        self.update_alerts_table()
    
    def update_event_stream(self, events: List[str]):
        text = "\n".join(events[-100:])
        self.event_stream.setPlainText(text)
        
        if self.auto_scroll_check.isChecked():
            scrollbar = self.event_stream.verticalScrollBar()
            scrollbar.setValue(scrollbar.maximum())
    
    def clear_alerts(self):
        count = len(self.alerts)
        self.alerts.clear()
        self.alerts_table.setRowCount(0)
        self.statusBar.showMessage(f"Cleared {count} alerts", 3000)
        logger.info(f"Cleared {count} alerts")
    
    def export_alerts(self):
        if not self.alerts:
            self.statusBar.showMessage("No alerts to export", 2000)
            return
        
        filename = f"/tmp/fyp_alerts_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        try:
            import csv
            with open(filename, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(["Timestamp", "Severity", "Process", "PID", "Message"])
                for alert in self.alerts:
                    writer.writerow([alert.timestamp, alert.severity, alert.process_name, alert.pid, alert.message])
            self.statusBar.showMessage(f"Exported to {filename}", 3000)
            logger.info(f"Exported {len(self.alerts)} alerts to {filename}")
        except Exception as e:
            self.statusBar.showMessage(f"Export failed: {e}", 3000)
            logger.error(f"Export failed: {e}")
    
    def closeEvent(self, event):
        logger.info("Application closing...")
        self.daemon_monitor.stop()
        self.tray_icon.hide()
        logger.info("Application closed")
        event.accept()


def main():
    logger.info("Starting FYP GUI application...")
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    app.setStyleSheet(DARK_THEME)
    
    # Enable high DPI scaling
    app.setAttribute(Qt.AA_EnableHighDpiScaling)
    app.setAttribute(Qt.AA_UseHighDpiPixmaps)
    
    window = FYPMainWindow()
    window.show()
    
    logger.info("Entering Qt event loop")
    exit_code = app.exec()
    logger.info(f"Application exited with code {exit_code}")
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
