"""
Monitor LKM watchdog status written to /tmp/fyp_lkm_status.json
"""

import json
import logging
from pathlib import Path

from PySide6.QtCore import QObject, QTimer, Signal

logger = logging.getLogger("FYP-GUI")

DEFAULT_STATUS_FILE = "/tmp/fyp_lkm_status.json"


class LkmStatusMonitor(QObject):
    status_updated = Signal(dict)

    def __init__(self, status_file: str = DEFAULT_STATUS_FILE, parent=None):
        super().__init__(parent)
        self.status_file = Path(status_file)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.poll)

    def start(self, interval_ms: int = 2000):
        self.timer.start(interval_ms)
        self.poll()
        logger.info("LKM status monitor started (%sms)", interval_ms)

    def stop(self):
        self.timer.stop()

    def poll(self):
        if not self.status_file.exists():
            self.status_updated.emit(
                {
                    "loaded": False,
                    "state": "unknown",
                    "message": "Watchdog status not available",
                }
            )
            return
        try:
            with open(self.status_file, "r", encoding="utf-8") as handle:
                data = json.load(handle)
            self.status_updated.emit(data)
        except (json.JSONDecodeError, OSError) as exc:
            logger.debug("LKM status read error: %s", exc)
