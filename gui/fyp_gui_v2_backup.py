#!/usr/bin/env python3
"""
FYP Keylogger Detection - Modern Qt GUI v2.0
Production-grade UI with charts, animations, dark theme
"""

import sys
import json
import subprocess
from datetime import datetime
from pathlib import Path
from typing import List
from dataclasses import dataclass
from collections import deque
import logging

logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(levelname)s: %(message)s', datefmt='%H:%M:%S')
logger = logging.getLogger('FYP-GUI')

from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *
from PySide6.QtCharts import *

# =============== DARK THEME ===============
DARK_THEME = """
QMainWindow, QWidget { background-color: #1e1e1e; color: #e0e0e0; font-family: 'Segoe UI', Arial; font-size: 10pt; }
QGroupBox { background-color: #2d2d2d; border: 1px solid #404040; border-radius: 6px; margin-top: 12px; padding-top: 12px; font-weight: bold; }
QGroupBox::title { subcontrol-origin: margin; subcontrol-position: top left; padding: 4px 8px; color: #007acc; }
QPushButton { background-color: #0e639c; color: white; border: none; border-radius: 4px; padding: 8px 16px; font-weight: bold; }
QPushButton:hover { background-color: #1177bb; }
QPushButton:pressed { background-color: #005a9e; }
QTableWidget { background-color: #252526; alternate-background-color: #2d2d30; gridline-color: #3e3e42; border: 1px solid #404040; selection-background-color: #094771; }
QHeaderView::section { background-color: #2d2d2d; color: #e0e0e0; padding: 8px; border: none; border-right: 1px solid #404040; border-bottom: 2px solid #007acc; font-weight: bold; }
QTabWidget::pane { border: 1px solid #404040; background-color: #1e1e1e; border-radius: 4px; }
QTabBar::tab { background-color: #2d2d2d; color: #a0a0a0; padding: 10px 20px; border: 1px solid #404040; border-bottom: none; border-top-left-radius: 4px; border-top-right-radius: 4px; }
QTabBar::tab:selected { background-color: #1e1e1e; color: #007acc; border-bottom: 2px solid #007acc; }
QTabBar::tab:hover { background-color: #383838; }
QTextEdit, QLineEdit { background-color: #1e1e1e; color: #e0e0e0; border: 1px solid #404040; border-radius: 4px; padding: 6px; selection-background-color: #094771; }
QComboBox { background-color: #2d2d2d; color: #e0e0e0; border: 1px solid #404040; border-radius: 4px; padding: 6px; }
QComboBox:hover { border: 1px solid #007acc; }
QComboBox QAbstractItemView { background-color: #2d2d2d; color: #e0e0e0; selection-background-color: #094771; border: 1px solid #404040; }
QProgressBar { background-color: #2d2d2d; border: 1px solid #404040; border-radius: 4px; text-align: center; color: #e0e0e0; }
QProgressBar::chunk { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #4ec9b0, stop:1 #007acc); border-radius: 3px; }
QStatusBar { background-color: #007acc; color: white; border-top: 1px solid #005a9e; }
QScrollBar:vertical { background-color: #1e1e1e; width: 12px; border-radius: 6px; }
QScrollBar::handle:vertical { background-color: #404040; border-radius: 6px; min-height: 20px; }
QScrollBar::handle:vertical:hover { background-color: #4e4e4e; }
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
    """Animated status dot"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(16, 16)
        self._color = QColor(100, 100, 100)
        
    def set_status(self, status: str):
        color_map = {
            'success': QColor(78, 201, 176),
            'warning': QColor(206, 145, 120),
            'error': QColor(244, 135, 113),
            'unknown': QColor(100, 100, 100)
        }
        self._color = color_map.get(status, color_map['unknown'])
        self.update()
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        gradient = QRadialGradient(8, 8, 8)
        gradient.setColorAt(0, self._color.lighter(150))
        gradient.setColorAt(0.5, self._color)
        gradient.setColorAt(1, self._color.darker(150))
        painter.setBrush(QBrush(gradient))
        painter.setPen(QPen(self._color.lighter(120), 1))
        painter.drawEllipse(2, 2, 12, 12)


class EventRateChart(QChartView):
    """Real-time event rate chart"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.time_points = deque(maxlen=60)
        self.rate_points = deque(maxlen=60)
        
        self.chart = QChart()
        self.chart.setTitle("Event Rate (events/second)")
        self.chart.setTheme(QChart.ChartThemeDark)
        self.chart.setBackgroundBrush(QBrush(QColor(30, 30, 30)))
        self.chart.setTitleBrush(QBrush(QColor(224, 224, 224)))
        self.chart.legend().hide()
        
        self.series = QSplineSeries()
        self.series.setColor(QColor(0, 122, 204))
        self.series.setPen(QPen(QColor(0, 122, 204), 3))
        self.chart.addSeries(self.series)
        
        self.axis_x = QValueAxis()
        self.axis_x.setRange(0, 60)
        self.axis_x.setTitleText("Time (seconds ago)")
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
        self.time_points.append(0)
        self.rate_points.append(events_per_sec)
        
        for i in range(len(self.time_points) - 1):
            self.time_points[i] += 1
        
        self.series.clear()
        for i in range(len(self.time_points)):
            x = 60 - self.time_points[i]
            y = self.rate_points[i]
            self.series.append(x, y)
        
        if self.rate_points:
            max_rate = max(self.rate_points)
            self.axis_y.setRange(0, max(100, max_rate * 1.2))
            
            if max_rate > 100:
                self.series.setColor(QColor(244, 135, 113))  # Red
                self.series.setPen(QPen(QColor(244, 135, 113), 3))
            elif max_rate > 50:
                self.series.setColor(QColor(206, 145, 120))  # Yellow
                self.series.setPen(QPen(QColor(206, 145, 120), 3))
            else:
                self.series.setColor(QColor(78, 201, 176))  # Green
                self.series.setPen(QPen(QColor(78, 201, 176), 3))


class ProcessBarChart(QChartView):
    """Top processes bar chart"""
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.chart = QChart()
        self.chart.setTitle("Top 5 Processes")
        self.chart.setTheme(QChart.ChartThemeDark)
        self.chart.setBackgroundBrush(QBrush(QColor(30, 30, 30)))
        self.chart.setTitleBrush(QBrush(QColor(224, 224, 224)))
        self.chart.legend().hide()
        
        self.series = QBarSeries()
        self.chart.addSeries(self.series)
        
        self.axis_x = QBarCategoryAxis()
        self.axis_x.setLabelsColor(QColor(160, 160, 160))
        
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
        sorted_procs = sorted(processes.items(), key=lambda x: x[1].get('total_events', 0), reverse=True)[:5]
        if not sorted_procs:
            return
        
        self.series.clear()
        bar_set = QBarSet("Events")
        bar_set.setColor(QColor(0, 122, 204))
        
        categories = []
        for pid, stats in sorted_procs:
            comm = stats.get('comm', 'unknown')[:10]
            categories.append(f"{comm}\n({pid})")
            bar_set.append(stats.get('total_events', 0))
        
        self.series.append(bar_set)
        self.axis_x.setCategories(categories)
        
        max_events = max(stats.get('total_events', 0) for _, stats in sorted_procs)
        self.axis_y.setRange(0, max(10, max_events * 1.2))


class DaemonMonitor(QObject):
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
        
    def start(self, interval_ms: int = 500):
        self.timer.start(interval_ms)
        logger.info(f"Monitoring started ({interval_ms}ms interval)")
        
    def stop(self):
        self.timer.stop()
        
    def check_updates(self):
        if not self.status_file.exists():
            if self.is_connected:
                self.is_connected = False
                self.connection_changed.emit(False)
            return
            
        try:
            mtime = self.status_file.stat().st_mtime
            if mtime > self.last_modified:
                self.last_modified = mtime
                with open(self.status_file, 'r') as f:
                    data = json.load(f)
                    
                    # Calculate events per second
                    current_count = data.get('total_events', 0)
                    self.events_per_sec = max(0, (current_count - self.last_event_count) * 2)
                    self.last_event_count = current_count
                    data['events_per_second'] = self.events_per_sec
                    
                    if not self.is_connected:
                        self.is_connected = True
                        self.connection_changed.emit(True)
                        
                    self.status_updated.emit(data)
                    
                    # Process alerts
                    if 'alerts' in data:
                        for alert_data in data['alerts']:
                            alert = Alert(
                                timestamp=alert_data['timestamp'],
                                severity=alert_data['severity'],
                                message=alert_data['message'],
                                process_name=alert_data.get('process', 'unknown'),
                                pid=alert_data.get('pid', 0)
                            )
                            self.alert_received.emit(alert)
                            if alert.severity == "HIGH":
                                self.send_notification(alert)
        except Exception as e:
            logger.debug(f"Error reading status: {e}")
            
    def send_notification(self, alert: Alert):
        """Send desktop notification for HIGH alerts"""
        try:
            subprocess.run([
                'notify-send',
                '-u', 'critical',
                '-i', 'security-high',
                f'Security Alert: {alert.process_name}',
                alert.message
            ], timeout=1)
        except Exception as e:
            logger.debug(f"Notification failed: {e}")


class FYPMainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("FYP Keylogger Detection System - v2.0")
        self.setMinimumSize(1400, 900)
        
        logger.info("=" * 60)
        logger.info("FYP Keylogger Detection GUI v2.0 - Modern Interface")
        logger.info("=" * 60)
        
        self.alerts = []
        self.alert_filter_severity = "ALL"
        
        # Daemon monitor
        self.daemon_monitor = DaemonMonitor()
        self.daemon_monitor.status_updated.connect(self.on_status_update)
        self.daemon_monitor.alert_received.connect(self.on_alert_received)
        self.daemon_monitor.connection_changed.connect(self.on_connection_changed)
        
        # System tray
        self.setup_tray()
        
        self.init_ui()
        self.daemon_monitor.start()
        
        logger.info("GUI initialized successfully")
        
    def setup_tray(self):
        """Setup system tray icon"""
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setToolTip("FYP Keylogger Detection")
        
        # Create tray menu
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
        """Update tray icon color"""
        # Create colored icon
        pixmap = QPixmap(64, 64)
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        
        color_map = {
            'success': QColor(78, 201, 176),
            'warning': QColor(206, 145, 120),
            'error': QColor(244, 135, 113),
            'unknown': QColor(100, 100, 100)
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
    
    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(10, 10, 10, 10)
        
        # ===== STATUS HEADER =====
        status_group = QGroupBox("System Status")
        status_layout = QHBoxLayout()
        
        self.kernel_indicator = StatusIndicator()
        self.daemon_indicator = StatusIndicator()
        
        self.kernel_label = QLabel("Kernel Module: Unknown")
        self.daemon_label = QLabel("Daemon: Unknown")
        self.events_label = QLabel("Events: 0")
        self.rate_label = QLabel("Rate: 0 eps")
        
        refresh_btn = QPushButton("🔄 Refresh")
        refresh_btn.clicked.connect(self.force_refresh)
        refresh_btn.setMaximumWidth(100)
        
        status_layout.addWidget(self.kernel_indicator)
        status_layout.addWidget(self.kernel_label)
        status_layout.addSpacing(20)
        status_layout.addWidget(self.daemon_indicator)
        status_layout.addWidget(self.daemon_label)
        status_layout.addSpacing(20)
        status_layout.addWidget(self.events_label)
        status_layout.addSpacing(20)
        status_layout.addWidget(self.rate_label)
        status_layout.addStretch()
        status_layout.addWidget(refresh_btn)
        
        status_group.setLayout(status_layout)
        main_layout.addWidget(status_group)
        
        # ===== TABS =====
        tabs = QTabWidget()
        
        # TAB 1: DASHBOARD
        dashboard_tab = self.create_dashboard_tab()
        tabs.addTab(dashboard_tab, "📊 Dashboard")
        
        # TAB 2: ALERTS
        alerts_tab = self.create_alerts_tab()
        tabs.addTab(alerts_tab, "🚨 Alerts")
        
        # TAB 3: PROCESSES
        processes_tab = self.create_processes_tab()
        tabs.addTab(processes_tab, "⚙️ Processes")
        
        # TAB 4: EVENT STREAM
        stream_tab = self.create_stream_tab()
        tabs.addTab(stream_tab, "📋 Event Stream")
        
        main_layout.addWidget(tabs)
        
        # Status bar
        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)
        self.statusBar.showMessage("Ready - Waiting for daemon...")
        
    def create_dashboard_tab(self):
        """Dashboard with charts"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Top row: event rate chart
        chart_group = QGroupBox("Real-Time Monitoring")
        chart_layout = QVBoxLayout()
        
        self.event_rate_chart = EventRateChart()
        self.event_rate_chart.setMinimumHeight(250)
        chart_layout.addWidget(self.event_rate_chart)
        
        chart_group.setLayout(chart_layout)
        layout.addWidget(chart_group)
        
        # Bottom row: process bar chart
        proc_chart_group = QGroupBox("Process Activity")
        proc_chart_layout = QVBoxLayout()
        
        self.process_bar_chart = ProcessBarChart()
        self.process_bar_chart.setMinimumHeight(250)
        proc_chart_layout.addWidget(self.process_bar_chart)
        
        proc_chart_group.setLayout(proc_chart_layout)
        layout.addWidget(proc_chart_group)
        
        return widget
    
    def create_alerts_tab(self):
        """Alerts table with filters"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Filter controls
        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel("Filter by Severity:"))
        
        self.severity_filter = QComboBox()
        self.severity_filter.addItems(["ALL", "HIGH", "MEDIUM", "LOW"])
        self.severity_filter.currentTextChanged.connect(self.apply_alert_filter)
        filter_layout.addWidget(self.severity_filter)
        
        filter_layout.addWidget(QLabel("Search:"))
        self.alert_search = QLineEdit()
        self.alert_search.setPlaceholderText("Search process name...")
        self.alert_search.textChanged.connect(self.apply_alert_filter)
        filter_layout.addWidget(self.alert_search)
        
        clear_btn = QPushButton("Clear All")
        clear_btn.clicked.connect(self.clear_alerts)
        filter_layout.addWidget(clear_btn)
        
        export_btn = QPushButton("Export CSV")
        export_btn.clicked.connect(self.export_alerts)
        filter_layout.addWidget(export_btn)
        
        layout.addLayout(filter_layout)
        
        # Alerts table
        self.alerts_table = QTableWidget()
        self.alerts_table.setColumnCount(5)
        self.alerts_table.setHorizontalHeaderLabels(["✓", "Time", "Severity", "Process", "Message"])
        self.alerts_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.Stretch)
        self.alerts_table.setColumnWidth(0, 30)
        self.alerts_table.setAlternatingRowColors(True)
        layout.addWidget(self.alerts_table)
        
        return widget
    
    def create_processes_tab(self):
        """Process statistics table"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        self.stats_table = QTableWidget()
        self.stats_table.setColumnCount(5)
        self.stats_table.setHorizontalHeaderLabels(["PID", "Process", "Events", "Rapid %", "Rate (eps)"])
        self.stats_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.stats_table.setAlternatingRowColors(True)
        self.stats_table.setSortingEnabled(True)
        layout.addWidget(self.stats_table)
        
        return widget
    
    def create_stream_tab(self):
        """Raw event stream"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        controls_layout = QHBoxLayout()
        self.auto_scroll_check = QCheckBox("Auto-scroll")
        self.auto_scroll_check.setChecked(True)
        controls_layout.addWidget(self.auto_scroll_check)
        controls_layout.addStretch()
        
        clear_stream_btn = QPushButton("Clear")
        clear_stream_btn.clicked.connect(lambda: self.event_stream.clear())
        controls_layout.addWidget(clear_stream_btn)
        
        layout.addLayout(controls_layout)
        
        self.event_stream = QTextEdit()
        self.event_stream.setReadOnly(True)
        self.event_stream.setFont(QFont("Courier", 9))
        layout.addWidget(self.event_stream)
        
        return widget
    
    def force_refresh(self):
        logger.info("Manual refresh triggered")
        self.daemon_monitor.check_updates()
        self.statusBar.showMessage("Refreshed", 2000)
    
    def on_connection_changed(self, connected: bool):
        if connected:
            logger.info("Daemon connection established")
            self.set_tray_status('success')
        else:
            logger.warning("Daemon connection lost")
            self.set_tray_status('error')
    
    def on_status_update(self, data: dict):
        # Update status indicators
        kernel_loaded = data.get('kernel_loaded', False)
        daemon_running = data.get('daemon_running', False)
        
        if kernel_loaded:
            self.kernel_indicator.set_status('success')
            self.kernel_label.setText("Kernel Module: Active")
        else:
            self.kernel_indicator.set_status('error')
            self.kernel_label.setText("Kernel Module: Inactive")
        
        if daemon_running:
            self.daemon_indicator.set_status('success')
            self.daemon_label.setText("Daemon: Running")
        else:
            self.daemon_indicator.set_status('error')
            self.daemon_label.setText("Daemon: Stopped")
        
        # Update counters
        total_events = data.get('total_events', 0)
        self.events_label.setText(f"Events: {total_events:,}")
        
        eps = data.get('events_per_second', 0.0)
        self.rate_label.setText(f"Rate: {eps:.1f} eps")
        
        # Update charts
        self.event_rate_chart.add_data_point(eps)
        
        processes = data.get('processes', {})
        self.process_bar_chart.update_data(processes)
        self.update_stats_table(processes)
        
        # Update event stream
        recent_events = data.get('recent_events', [])
        self.update_event_stream(recent_events)
        
        # Status bar
        last_update = data.get('timestamp', 'unknown')
        self.statusBar.showMessage(f"Last update: {last_update}")
    
    def on_alert_received(self, alert: Alert):
        self.alerts.append(alert)
        self.update_alerts_table()
        
        # Update tray based on severity
        if alert.severity == "HIGH":
            self.set_tray_status('error')
        elif alert.severity == "MEDIUM":
            self.set_tray_status('warning')
        
        logger.warning(f"Alert: [{alert.severity}] {alert.process_name} - {alert.message}")
    
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
                rapid_item.setBackground(QColor(206, 145, 120))
            self.stats_table.setItem(row, 3, rapid_item)
            
            eps = stats.get('events_per_second', 0.0)
            eps_item = QTableWidgetItem(f"{eps:.1f}")
            if eps > 100.0:
                eps_item.setBackground(QColor(244, 135, 113))
            self.stats_table.setItem(row, 4, eps_item)
    
    def update_alerts_table(self):
        self.alerts_table.setRowCount(0)
        
        search_text = self.alert_search.text().lower()
        filter_sev = self.severity_filter.currentText()
        
        for alert in self.alerts:
            # Apply filters
            if filter_sev != "ALL" and alert.severity != filter_sev:
                continue
            if search_text and search_text not in alert.process_name.lower():
                continue
            
            row = self.alerts_table.rowCount()
            self.alerts_table.insertRow(row)
            
            # Checkbox
            check_item = QTableWidgetItem()
            check_item.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
            check_item.setCheckState(Qt.Checked if alert.reviewed else Qt.Unchecked)
            self.alerts_table.setItem(row, 0, check_item)
            
            # Time
            self.alerts_table.setItem(row, 1, QTableWidgetItem(alert.timestamp))
            
            # Severity with color
            severity_item = QTableWidgetItem(alert.severity)
            if alert.severity == "HIGH":
                severity_item.setBackground(QColor(244, 135, 113))
            elif alert.severity == "MEDIUM":
                severity_item.setBackground(QColor(206, 145, 120))
            else:
                severity_item.setBackground(QColor(200, 200, 100))
            self.alerts_table.setItem(row, 2, severity_item)
            
            # Process
            self.alerts_table.setItem(row, 3, QTableWidgetItem(f"{alert.process_name} ({alert.pid})"))
            
            # Message
            self.alerts_table.setItem(row, 4, QTableWidgetItem(alert.message))
    
    def apply_alert_filter(self):
        self.update_alerts_table()
    
    def update_event_stream(self, events: List[str]):
        text = "\n".join(events[-100:])
        self.event_stream.setPlainText(text)
        
        if self.auto_scroll_check.isChecked():
            cursor = self.event_stream.textCursor()
            cursor.movePosition(cursor.End)
            self.event_stream.setTextCursor(cursor)
    
    def clear_alerts(self):
        count = len(self.alerts)
        self.alerts.clear()
        self.alerts_table.setRowCount(0)
        self.statusBar.showMessage(f"Cleared {count} alerts", 2000)
        logger.info(f"Cleared {count} alerts")
    
    def export_alerts(self):
        if not self.alerts:
            self.statusBar.showMessage("No alerts to export", 2000)
            return
        
        filename = f"/tmp/fyp_alerts_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        try:
            with open(filename, 'w') as f:
                f.write("Timestamp,Severity,Process,PID,Message\n")
                for alert in self.alerts:
                    f.write(f'"{alert.timestamp}","{alert.severity}","{alert.process_name}",{alert.pid},"{alert.message}"\n')
            self.statusBar.showMessage(f"Exported to {filename}", 3000)
            logger.info(f"Exported {len(self.alerts)} alerts to {filename}")
        except Exception as e:
            self.statusBar.showMessage(f"Export failed: {e}", 3000)
    
    def closeEvent(self, event):
        """Minimize to tray instead of closing"""
        event.ignore()
        self.hide()
        self.tray_icon.showMessage(
            "FYP Keylogger Detection",
            "Application minimized to tray. Double-click icon to restore.",
            QSystemTrayIcon.Information,
            2000
        )
    
    def closeEvent(self, event):
        """Handle window close"""
        logger.info("Shutting down GUI...")
        self.daemon_monitor.stop()
        self.tray_icon.hide()
        logger.info("GUI shutdown complete")
        event.accept()


def main():
    logger.info("Starting FYP GUI v2.0...")
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    app.setStyleSheet(DARK_THEME)
    
    window = FYPMainWindow()
    window.show()
    
    logger.info("Entering Qt event loop...")
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
