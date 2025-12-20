"""
FYP Daemon Monitor
Monitors daemon status file and emits signals
"""

import json
import subprocess
import logging
from pathlib import Path
from PySide6.QtCore import QObject, Signal, QTimer
from models import Alert

logger = logging.getLogger('FYP-GUI')


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
