#!/usr/bin/env python3
"""
FYP Keylogger Detection - Qt GUI Application
Version: 2.0 - Modern UI with Charts & Animations
Author: FYP Project
Description: Production-grade desktop GUI for real-time keylogger detection
"""

import sys
import json
import os
import logging
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Optional, List
from dataclasses import dataclass
from collections import deque

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s [%(name)s]: %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger('FYP-GUI')

try:
    from PySide6.QtWidgets import (
        QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
        QTableWidget, QTableWidgetItem, QTextEdit, QLabel, QPushButton,
        QGroupBox, QHeaderView, QTabWidget, QStatusBar, QSystemTrayIcon,
        QMenu, QComboBox, QLineEdit, QCheckBox, QProgressBar, QFrame,
        QSplitter, QScrollArea, QGridLayout
    )
    from PySide6.QtCore import (
        QTimer, Qt, Signal, QObject, QPropertyAnimation, QEasingCurve,
        QParallelAnimationGroup, QPoint, QSize, QSettings
    )
    from PySide6.QtGui import (
        QColor, QFont, QPalette, QIcon, QAction, QPainter, QBrush, QPen,
        QLinearGradient, QRadialGradient
    )
    from PySide6.QtCharts import (
        QChart, QChartView, QLineSeries, QBarSeries, QBarSet,
        QBarCategoryAxis, QValueAxis, QDateTimeAxis, QSplineSeries
    )
except ImportError as e:
    print(f"ERROR: PySide6 not installed. Install with: pip3 install PySide6")
    print(f"Details: {e}")
    sys.exit(1)


# Dark Theme Stylesheet
DARK_THEME = """
/* Main Window */
QMainWindow, QWidget {
    background-color: #1e1e1e;
    color: #e0e0e0;
    font-family: 'Segoe UI', Arial, sans-serif;
    font-size: 10pt;
}

/* Group Boxes */
QGroupBox {
    background-color: #2d2d2d;
    border: 1px solid #404040;
    border-radius: 6px;
    margin-top: 12px;
    padding-top: 12px;
    font-weight: bold;
    color: #e0e0e0;
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 4px 8px;
    color: #007acc;
}

/* Buttons */
QPushButton {
    background-color: #0e639c;
    color: white;
    border: none;
    border-radius: 4px;
    padding: 8px 16px;
    font-weight: bold;
}

QPushButton:hover {
    background-color: #1177bb;
}

QPushButton:pressed {
    background-color: #005a9e;
}

QPushButton:disabled {
    background-color: #3c3c3c;
    color: #666666;
}

/* Tables */
QTableWidget {
    background-color: #252526;
    alternate-background-color: #2d2d30;
    gridline-color: #3e3e42;
    border: 1px solid #404040;
    border-radius: 4px;
    selection-background-color: #094771;
}

QTableWidget::item {
    padding: 6px;
    border: none;
}

QTableWidget::item:selected {
    background-color: #094771;
}

QHeaderView::section {
    background-color: #2d2d2d;
    color: #e0e0e0;
    padding: 8px;
    border: none;
    border-right: 1px solid #404040;
    border-bottom: 2px solid #007acc;
    font-weight: bold;
}

/* Tabs */
QTabWidget::pane {
    border: 1px solid #404040;
    background-color: #1e1e1e;
    border-radius: 4px;
}

QTabBar::tab {
    background-color: #2d2d2d;
    color: #a0a0a0;
    padding: 10px 20px;
    border: 1px solid #404040;
    border-bottom: none;
    border-top-left-radius: 4px;
    border-top-right-radius: 4px;
    margin-right: 2px;
}

QTabBar::tab:selected {
    background-color: #1e1e1e;
    color: #007acc;
    border-bottom: 2px solid #007acc;
}

QTabBar::tab:hover {
    background-color: #383838;
}

/* Text Edit */
QTextEdit, QLineEdit {
    background-color: #1e1e1e;
    color: #e0e0e0;
    border: 1px solid #404040;
    border-radius: 4px;
    padding: 6px;
    selection-background-color: #094771;
}

QTextEdit:focus, QLineEdit:focus {
    border: 1px solid #007acc;
}

/* ComboBox */
QComboBox {
    background-color: #2d2d2d;
    color: #e0e0e0;
    border: 1px solid #404040;
    border-radius: 4px;
    padding: 6px;
}

QComboBox:hover {
    border: 1px solid #007acc;
}

QComboBox::drop-down {
    border: none;
    width: 20px;
}

QComboBox::down-arrow {
    image: none;
    border-left: 5px solid transparent;
    border-right: 5px solid transparent;
    border-top: 5px solid #e0e0e0;
    margin-right: 5px;
}

QComboBox QAbstractItemView {
    background-color: #2d2d2d;
    color: #e0e0e0;
    selection-background-color: #094771;
    border: 1px solid #404040;
}

/* Progress Bar */
QProgressBar {
    background-color: #2d2d2d;
    border: 1px solid #404040;
    border-radius: 4px;
    text-align: center;
    color: #e0e0e0;
}

QProgressBar::chunk {
    background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #4ec9b0, stop:0.5 #007acc, stop:1 #4ec9b0);
    border-radius: 3px;
}

/* Status Bar */
QStatusBar {
    background-color: #007acc;
    color: white;
    border-top: 1px solid #005a9e;
}

/* Scroll Bar */
QScrollBar:vertical {
    background-color: #1e1e1e;
    width: 12px;
    border-radius: 6px;
}

QScrollBar::handle:vertical {
    background-color: #404040;
    border-radius: 6px;
    min-height: 20px;
}

QScrollBar::handle:vertical:hover {
    background-color: #4e4e4e;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}

/* CheckBox */
QCheckBox {
    color: #e0e0e0;
    spacing: 8px;
}

QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border: 2px solid #404040;
    border-radius: 3px;
    background-color: #2d2d2d;
}

QCheckBox::indicator:checked {
    background-color: #007acc;
    border-color: #007acc;
}

QCheckBox::indicator:hover {
    border-color: #007acc;
}

/* Labels with Status Colors */
QLabel[status="success"] {
    color: #4ec9b0;
    font-weight: bold;
}

QLabel[status="warning"] {
    color: #ce9178;
    font-weight: bold;
}

QLabel[status="error"] {
    color: #f48771;
    font-weight: bold;
}

QLabel[status="info"] {
    color: #007acc;
    font-weight: bold;
}

/* Frame Separator */
QFrame[frameShape="4"], QFrame[frameShape="5"] {
    color: #404040;
}
"""


@dataclass
class Alert:
    """Alert data structure"""
    timestamp: str
    severity: str  # LOW, MEDIUM, HIGH
    message: str
    process_name: str
    pid: int
    reviewed: bool = False


class AnimatedLabel(QLabel):
    """Label with fade-in animation"""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.animation = None
        
    def fade_in(self):
        """Animate label appearance"""
        self.animation = QPropertyAnimation(self, b"windowOpacity")
        self.animation.setDuration(300)
        self.animation.setStartValue(0.0)
        self.animation.setEndValue(1.0)
        self.animation.setEasingCurve(QEasingCurve.InOutQuad)
        self.animation.start()


class StatusIndicator(QWidget):
    """Animated status indicator dot"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(16, 16)
        self._color = QColor(100, 100, 100)
        self._pulse_animation = None
        
    def set_status(self, status: str):
        """Set indicator status: success, warning, error, unknown"""
        color_map = {
            'success': QColor(78, 201, 176),  # #4ec9b0
            'warning': QColor(206, 145, 120),  # #ce9178
            'error': QColor(244, 135, 113),    # #f48771
            'unknown': QColor(100, 100, 100)
        }
        self._color = color_map.get(status, color_map['unknown'])
        self.update()
        
    def paintEvent(self, event):
        """Draw the indicator"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Create radial gradient for glow effect
        gradient = QRadialGradient(8, 8, 8)
        gradient.setColorAt(0, self._color.lighter(150))
        gradient.setColorAt(0.5, self._color)
        gradient.setColorAt(1, self._color.darker(150))
        
        painter.setBrush(QBrush(gradient))
        painter.setPen(QPen(self._color.lighter(120), 1))
        painter.drawEllipse(2, 2, 12, 12)


class EventRateChart(QChartView):
    """Real-time event rate line chart"""
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Data storage (last 60 seconds)
        self.time_points = deque(maxlen=60)
        self.rate_points = deque(maxlen=60)
        
        # Create chart
        self.chart = QChart()
        self.chart.setTitle("Event Rate (events/second)")
        self.chart.setTheme(QChart.ChartThemeDark)
        self.chart.setBackgroundBrush(QBrush(QColor(30, 30, 30)))
        self.chart.setTitleBrush(QBrush(QColor(224, 224, 224)))
        self.chart.legend().hide()
        
        # Create series
        self.series = QSplineSeries()
        self.series.setColor(QColor(0, 122, 204))  # #007acc
        pen = QPen(QColor(0, 122, 204), 2)
        self.series.setPen(pen)
        self.chart.addSeries(self.series)
        
        # Create axes
        self.axis_x = QValueAxis()
        self.axis_x.setRange(0, 60)
        self.axis_x.setTitleText("Time (seconds ago)")
        self.axis_x.setLabelFormat("%d")
        self.axis_x.setLabelsColor(QColor(160, 160, 160))
        self.axis_x.setTitleBrush(QBrush(QColor(224, 224, 224)))
        self.axis_x.setGridLineColor(QColor(64, 64, 64))
        
        self.axis_y = QValueAxis()
        self.axis_y.setRange(0, 100)
        self.axis_y.setTitleText("Events/sec")
        self.axis_y.setLabelsColor(QColor(160, 160, 160))
        self.axis_y.setTitleBrush(QBrush(QColor(224, 224, 224)))
        self.axis_y.setGridLineColor(QColor(64, 64, 64))
        
        self.chart.addAxis(self.axis_x, Qt.AlignBottom)
        self.chart.addAxis(self.axis_y, Qt.AlignLeft)
        self.series.attachAxis(self.axis_x)
        self.series.attachAxis(self.axis_y)
        
        self.setChart(self.chart)
        self.setRenderHint(QPainter.Antialiasing)
        
    def add_data_point(self, events_per_sec: float):
        """Add new data point and update chart"""
        # Add new point at time 0 (current)
        self.time_points.append(0)
        self.rate_points.append(events_per_sec)
        
        # Age existing points
        for i in range(len(self.time_points) - 1):
            self.time_points[i] += 1
        
        # Update series
        self.series.clear()
        for i in range(len(self.time_points)):
            # Invert time (60 seconds ago to now)
            x = 60 - self.time_points[i]
            y = self.rate_points[i]
            self.series.append(x, y)
        
        # Auto-scale Y axis
        if self.rate_points:
            max_rate = max(self.rate_points)
            self.axis_y.setRange(0, max(100, max_rate * 1.2))
            
            # Change color based on rate
            if max_rate > 100:
                self.series.setColor(QColor(244, 135, 113))  # Red
            elif max_rate > 50:
                self.series.setColor(QColor(206, 145, 120))  # Yellow
            else:
                self.series.setColor(QColor(78, 201, 176))  # Green


class ProcessBarChart(QChartView):
    """Top processes bar chart"""
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.chart = QChart()
        self.chart.setTitle("Top 5 Processes by Event Count")
        self.chart.setTheme(QChart.ChartThemeDark)
        self.chart.setBackgroundBrush(QBrush(QColor(30, 30, 30)))
        self.chart.setTitleBrush(QBrush(QColor(224, 224, 224)))
        self.chart.legend().hide()
        
        self.series = QBarSeries()
        self.chart.addSeries(self.series)
        
        # Axes
        self.axis_x = QBarCategoryAxis()
        self.axis_x.setLabelsColor(QColor(160, 160, 160))
        self.axis_x.setGridLineColor(QColor(64, 64, 64))
        
        self.axis_y = QValueAxis()
        self.axis_y.setTitleText("Events")
        self.axis_y.setLabelsColor(QColor(160, 160, 160))
        self.axis_y.setTitleBrush(QBrush(QColor(224, 224, 224)))
        self.axis_y.setGridLineColor(QColor(64, 64, 64))
        
        self.chart.addAxis(self.axis_x, Qt.AlignBottom)
        self.chart.addAxis(self.axis_y, Qt.AlignLeft)
        self.series.attachAxis(self.axis_x)
        self.series.attachAxis(self.axis_y)
        
        self.setChart(self.chart)
        self.setRenderHint(QPainter.Antialiasing)
        
    def update_data(self, processes: dict):
        """Update chart with top 5 processes"""
        # Sort by event count
        sorted_procs = sorted(
            processes.items(),
            key=lambda x: x[1].get('total_events', 0),
            reverse=True
        )[:5]
        
        if not sorted_procs:
            return
        
        # Clear existing data
        self.series.clear()
        
        # Create new bar set
        bar_set = QBarSet("Events")
        bar_set.setColor(QColor(0, 122, 204))
        
        categories = []
        for pid, stats in sorted_procs:
            comm = stats.get('comm', 'unknown')[:10]  # Truncate long names
            categories.append(f"{comm}\n({pid})")
            bar_set.append(stats.get('total_events', 0))
        
        self.series.append(bar_set)
        self.axis_x.setCategories(categories)
        
        # Auto-scale Y
        max_events = max(stats.get('total_events', 0) for _, stats in sorted_procs)
        self.axis_y.setRange(0, max(10, max_events * 1.2))


class DaemonMonitor(QObject):
    """Monitors daemon status file for updates"""
    
    status_updated = Signal(dict)
    alert_received = Signal(Alert)
    connection_changed = Signal(bool)  # True if connected, False if disconnected
    
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
        """Start monitoring daemon status file"""
        self.timer.start(interval_ms)
        logger.info(f"Started monitoring with {interval_ms}ms interval")
        
    def stop(self):
        """Stop monitoring"""
        self.timer.stop()
        logger.info("Stopped monitoring")
        
    def check_updates(self):
        """Check if daemon status file has been updated"""
        if not self.status_file.exists():
            if self.is_connected:
                self.is_connected = False
                self.connection_changed.emit(False)
            logger.debug(f"Status file not found: {self.status_file}")
            return
            
        try:
            mtime = self.status_file.stat().st_mtime
            if mtime > self.last_modified:
                self.last_modified = mtime
                with open(self.status_file, 'r') as f:
                    data = json.load(f)
                    
                    # Calculate events per second
                    current_count = data.get('total_events', 0)
                    self.events_per_sec = max(0, (current_count - self.last_event_count) * 2)  # *2 because 500ms interval
                    self.last_event_count = current_count
                    
                    # Add EPS to data
                    data['events_per_second'] = self.events_per_sec
                    
                    logger.debug(f"Status update: {current_count} events, "
                               f"{len(data.get('processes', {}))} processes, "
                               f"{self.events_per_sec:.1f} eps")
                    
                    if not self.is_connected:
                        self.is_connected = True
                        self.connection_changed.emit(True)
                        
                    self.status_updated.emit(data)
                    
                    # Check for new alerts
                    if 'alerts' in data:
                        for alert_data in data['alerts']:
                            alert = Alert(
                                timestamp=alert_data['timestamp'],
                                severity=alert_data['severity'],
                                message=alert_data['message'],
                                process_name=alert_data.get('process', 'unknown'),
                                pid=alert_data.get('pid', 0)
                            )
                            logger.warning(f"New alert: [{alert.severity}] {alert.message}")
                            self.alert_received.emit(alert)
        except (json.JSONDecodeError, OSError) as e:
            # Ignore transient errors (file being written)
            logger.debug(f"Transient error reading status file: {e}")
            pass


class FYPMainWindow(QMainWindow):
    """Main application window"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("FYP Keylogger Detection System")
        self.setMinimumSize(1000, 700)
        
        logger.info("=" * 60)
        logger.info("FYP Keylogger Detection GUI v0.1")
        logger.info("=" * 60)
        
        # Alert history
        self.alerts = []
        
        # Initialize daemon monitor
        self.daemon_monitor = DaemonMonitor()
        self.daemon_monitor.status_updated.connect(self.on_status_update)
        self.daemon_monitor.alert_received.connect(self.on_alert_received)
        
        self.init_ui()
        self.daemon_monitor.start()
        
        logger.info("GUI initialized successfully")
        
    def init_ui(self):
        """Initialize user interface"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        # System status bar at top
        status_group = QGroupBox("System Status")
        status_layout = QHBoxLayout()
        
        self.kernel_status = QLabel("⚫ Kernel Module: Unknown")
        self.daemon_status = QLabel("⚫ Daemon: Unknown")
        self.events_count = QLabel("Events: 0")
        
        refresh_btn = QPushButton("🔄 Refresh")
        refresh_btn.clicked.connect(self.force_refresh)
        refresh_btn.setMaximumWidth(100)
        
        status_layout.addWidget(self.kernel_status)
        status_layout.addWidget(self.daemon_status)
        status_layout.addWidget(self.events_count)
        status_layout.addStretch()
        status_layout.addWidget(refresh_btn)
        
        status_group.setLayout(status_layout)
        main_layout.addWidget(status_group)
        
        # Tab widget for different views
        tabs = QTabWidget()
        
        # Tab 1: Real-time Alerts
        alerts_tab = QWidget()
        alerts_layout = QVBoxLayout(alerts_tab)
        
        alerts_label = QLabel("🚨 Security Alerts")
        alerts_label.setFont(QFont("Arial", 12, QFont.Bold))
        alerts_layout.addWidget(alerts_label)
        
        self.alerts_table = QTableWidget()
        self.alerts_table.setColumnCount(4)
        self.alerts_table.setHorizontalHeaderLabels(["Time", "Severity", "Process", "Message"])
        self.alerts_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.alerts_table.setAlternatingRowColors(True)
        alerts_layout.addWidget(self.alerts_table)
        
        clear_btn = QPushButton("Clear Alerts")
        clear_btn.clicked.connect(self.clear_alerts)
        alerts_layout.addWidget(clear_btn)
        
        tabs.addTab(alerts_tab, "Alerts")
        
        # Tab 2: Process Statistics
        stats_tab = QWidget()
        stats_layout = QVBoxLayout(stats_tab)
        
        stats_label = QLabel("📊 Process Statistics")
        stats_label.setFont(QFont("Arial", 12, QFont.Bold))
        stats_layout.addWidget(stats_label)
        
        self.stats_table = QTableWidget()
        self.stats_table.setColumnCount(5)
        self.stats_table.setHorizontalHeaderLabels(["PID", "Process", "Events", "Rapid %", "Events/sec"])
        self.stats_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.stats_table.setAlternatingRowColors(True)
        stats_layout.addWidget(self.stats_table)
        
        tabs.addTab(stats_tab, "Statistics")
        
        # Tab 3: Event Stream
        stream_tab = QWidget()
        stream_layout = QVBoxLayout(stream_tab)
        
        stream_label = QLabel("📋 Raw Event Stream (Last 100)")
        stream_label.setFont(QFont("Arial", 12, QFont.Bold))
        stream_layout.addWidget(stream_label)
        
        self.event_stream = QTextEdit()
        self.event_stream.setReadOnly(True)
        self.event_stream.setFont(QFont("Courier", 9))
        stream_layout.addWidget(self.event_stream)
        
        tabs.addTab(stream_tab, "Event Stream")
        
        main_layout.addWidget(tabs)
        
        # Status bar at bottom
        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)
        self.statusBar.showMessage("Ready - Waiting for daemon...")
        
    def force_refresh(self):
        """Manually trigger a status check"""
        logger.info("Manual refresh triggered")
        self.daemon_monitor.check_updates()
        self.statusBar.showMessage("Refreshed", 2000)
    
    def on_status_update(self, data: dict):
        """Handle daemon status update"""
        # Check if data is stale (older than 5 seconds)
        import time
        from datetime import datetime
        try:
            timestamp_str = data.get('timestamp', '')
            if timestamp_str:
                update_time = datetime.fromisoformat(timestamp_str)
                age_seconds = (datetime.now() - update_time).total_seconds()
                is_stale = age_seconds > 5
                if is_stale:
                    logger.warning(f"Stale daemon data detected: {age_seconds:.1f}s old")
            else:
                is_stale = True
                logger.warning("No timestamp in status data")
        except Exception as e:
            is_stale = True
            logger.error(f"Error parsing timestamp: {e}")
        
        # Update system status
        kernel_loaded = data.get('kernel_loaded', False)
        daemon_running = data.get('daemon_running', False)
        
        if kernel_loaded:
            self.kernel_status.setText("🟢 Kernel Module: Active")
            self.kernel_status.setStyleSheet("color: green; font-weight: bold;")
        else:
            self.kernel_status.setText("🔴 Kernel Module: Inactive")
            self.kernel_status.setStyleSheet("color: red; font-weight: bold;")
            logger.warning("Kernel module not loaded!")
            
        if daemon_running and not is_stale:
            self.daemon_status.setText("🟢 Daemon: Running")
            self.daemon_status.setStyleSheet("color: green; font-weight: bold;")
        elif is_stale:
            self.daemon_status.setText("🟡 Daemon: Stale (not updating)")
            self.daemon_status.setStyleSheet("color: orange; font-weight: bold;")
        else:
            self.daemon_status.setText("🔴 Daemon: Stopped")
            self.daemon_status.setStyleSheet("color: red; font-weight: bold;")
            logger.warning("Daemon not running!")
            
        # Update event count (daemon's total processed, not kernel buffer)
        total_events = data.get('total_events', 0)
        self.events_count.setText(f"Events: {total_events:,}")  # Add comma formatting
        
        # Update process statistics
        processes = data.get('processes', {})
        self.update_stats_table(processes)
        
        # Update event stream
        recent_events = data.get('recent_events', [])
        self.update_event_stream(recent_events)
        
        # Update status bar
        last_update = data.get('timestamp', 'unknown')
        self.statusBar.showMessage(f"Last update: {last_update}")
        
    def on_alert_received(self, alert: Alert):
        """Handle new alert"""
        # Add to alerts list
        self.alerts.append(alert)
        
        # Update alerts table
        row = self.alerts_table.rowCount()
        self.alerts_table.insertRow(row)
        
        # Time
        time_item = QTableWidgetItem(alert.timestamp)
        self.alerts_table.setItem(row, 0, time_item)
        
        # Severity with color coding
        severity_item = QTableWidgetItem(alert.severity)
        if alert.severity == "HIGH":
            severity_item.setBackground(QColor(255, 100, 100))
        elif alert.severity == "MEDIUM":
            severity_item.setBackground(QColor(255, 200, 100))
        else:  # LOW
            severity_item.setBackground(QColor(255, 255, 150))
        self.alerts_table.setItem(row, 1, severity_item)
        
        # Process
        process_item = QTableWidgetItem(f"{alert.process_name} (PID {alert.pid})")
        self.alerts_table.setItem(row, 2, process_item)
        
        # Message
        message_item = QTableWidgetItem(alert.message)
        self.alerts_table.setItem(row, 3, message_item)
        
        # Scroll to bottom
        self.alerts_table.scrollToBottom()
        
    def update_stats_table(self, processes: dict):
        """Update process statistics table"""
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
                rapid_item.setBackground(QColor(255, 200, 100))
            self.stats_table.setItem(row, 3, rapid_item)
            
            eps = stats.get('events_per_second', 0.0)
            eps_item = QTableWidgetItem(f"{eps:.1f}")
            if eps > 100.0:
                eps_item.setBackground(QColor(255, 200, 100))
            self.stats_table.setItem(row, 4, eps_item)
            
    def update_event_stream(self, events: list):
        """Update raw event stream display"""
        # Keep last 100 events
        text = "\n".join(events[-100:])
        self.event_stream.setPlainText(text)
        
        # Scroll to bottom
        from PySide6.QtGui import QTextCursor
        cursor = self.event_stream.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        self.event_stream.setTextCursor(cursor)
        
    def clear_alerts(self):
        """Clear all alerts"""
        alert_count = len(self.alerts)
        self.alerts.clear()
        self.alerts_table.setRowCount(0)
        self.statusBar.showMessage("Alerts cleared")
        logger.info(f"Cleared {alert_count} alerts")
        
    def closeEvent(self, event):
        """Handle window close"""
        logger.info("Shutting down GUI...")
        self.daemon_monitor.stop()
        logger.info("GUI shutdown complete")
        event.accept()


def main():
    logger.info("Starting FYP GUI application...")
    app = QApplication(sys.argv)
    
    # Set application style
    app.setStyle('Fusion')
    logger.info("Qt style set to 'Fusion'")
    
    window = FYPMainWindow()
    window.show()
    logger.info("Main window displayed")
    
    logger.info("Entering Qt event loop...")
    exit_code = app.exec()
    logger.info(f"Application exiting with code {exit_code}")
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
