#!/usr/bin/env python3
"""
FYP Keylogger Detection - Qt GUI Application
Version: 0.1
Author: FYP Project
Description: Desktop GUI for real-time keylogger detection monitoring
"""

import sys
import json
import os
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional
from dataclasses import dataclass

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
        QGroupBox, QHeaderView, QTabWidget, QStatusBar
    )
    from PySide6.QtCore import QTimer, Qt, Signal, QObject
    from PySide6.QtGui import QColor, QFont, QPalette
except ImportError:
    print("ERROR: PySide6 not installed. Install with: pip3 install PySide6")
    sys.exit(1)


@dataclass
class Alert:
    """Alert data structure"""
    timestamp: str
    severity: str  # LOW, MEDIUM, HIGH
    message: str
    process_name: str
    pid: int


class DaemonMonitor(QObject):
    """Monitors daemon status file for updates"""
    
    status_updated = Signal(dict)
    alert_received = Signal(Alert)
    
    def __init__(self, status_file: str = "/tmp/fyp_status.json"):
        super().__init__()
        self.status_file = Path(status_file)
        self.last_modified = 0
        self.timer = QTimer()
        self.timer.timeout.connect(self.check_updates)
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
            logger.debug(f"Status file not found: {self.status_file}")
            return
            
        try:
            mtime = self.status_file.stat().st_mtime
            if mtime > self.last_modified:
                self.last_modified = mtime
                with open(self.status_file, 'r') as f:
                    data = json.load(f)
                    logger.debug(f"Status update: {data.get('total_events', 0)} events, "
                               f"{len(data.get('processes', {}))} processes")
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
