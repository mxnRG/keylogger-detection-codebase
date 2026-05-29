"""
Poll live telemetry CSV and POST rows to the ML inference API.
"""

from __future__ import annotations

import csv
import io
import json
import logging
import os
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional

from PySide6.QtCore import QObject, QThread, QTimer, Signal

logger = logging.getLogger("FYP-GUI")

DEFAULT_CSV = os.environ.get("FYP_TELEMETRY_CSV", "/tmp/fyp_telemetry_live.csv")
DEFAULT_API = os.environ.get("FYP_ML_API_URL", "http://127.0.0.1:8765/predict")

SKIP_FOR_API = {"timestamp", "scenario", "collector_type"}


class _PredictWorker(QThread):
    finished_ok = Signal(dict)
    finished_err = Signal(str)

    def __init__(self, api_url: str, features: Dict[str, Any], parent=None):
        super().__init__(parent)
        self.api_url = api_url
        self.features = features

    def run(self):
        try:
            payload = json.dumps({"features": self.features}).encode("utf-8")
            req = urllib.request.Request(
                self.api_url,
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=3) as resp:
                body = json.loads(resp.read().decode("utf-8"))
            self.finished_ok.emit(body)
        except urllib.error.URLError as exc:
            reason = getattr(exc, "reason", exc)
            self.finished_err.emit(f"API unreachable: {reason}")
        except Exception as exc:
            self.finished_err.emit(str(exc))


class TelemetryMlMonitor(QObject):
    prediction_received = Signal(dict)
    api_error = Signal(str)
    csv_offline = Signal(bool)

    def __init__(
        self,
        csv_path: str = DEFAULT_CSV,
        api_url: str = DEFAULT_API,
        parent=None,
    ):
        super().__init__(parent)
        self.csv_path = Path(csv_path)
        self.api_url = api_url
        self._offset = 0
        self._inode: Optional[int] = None
        self._fieldnames: List[str] = []
        self._busy = False
        self._worker: Optional[_PredictWorker] = None

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.poll)

    def start(self, interval_ms: int = 500):
        self.timer.start(interval_ms)
        logger.info("Telemetry ML monitor started → %s", self.api_url)

    def stop(self):
        self.timer.stop()
        if self._worker and self._worker.isRunning():
            self._worker.wait(2000)

    def _reset_file_state(self) -> None:
        self._offset = 0
        self._fieldnames = []
        if not self.csv_path.exists():
            return
        with open(self.csv_path, "r", encoding="utf-8", errors="replace") as handle:
            header = handle.readline()
            self._fieldnames = [c.strip() for c in header.strip().split(",") if c.strip()]
            self._offset = handle.tell()

    def poll(self):
        if self._busy:
            return
        if not self.csv_path.exists():
            self.csv_offline.emit(True)
            return

        self.csv_offline.emit(False)
        try:
            stat = self.csv_path.stat()
            if self._inode != stat.st_ino:
                self._inode = stat.st_ino
                self._reset_file_state()

            if stat.st_size <= self._offset:
                return

            with open(self.csv_path, "r", encoding="utf-8", errors="replace") as handle:
                handle.seek(self._offset)
                chunk = handle.read()
                self._offset = handle.tell()

            if not chunk or not self._fieldnames:
                return

            lines = [ln for ln in chunk.splitlines() if ln.strip()]
            if not lines:
                return

            row = self._parse_row(lines[-1])
            if row:
                self._request_prediction(row)
        except OSError as exc:
            logger.debug("CSV poll error: %s", exc)
            self.csv_offline.emit(True)

    def _parse_row(self, line: str) -> Optional[Dict[str, Any]]:
        try:
            reader = csv.DictReader(io.StringIO(line), fieldnames=self._fieldnames)
            parsed = next(reader, None)
            if not parsed:
                return None
            out: Dict[str, Any] = {}
            for key, val in parsed.items():
                if not key or key in SKIP_FOR_API:
                    continue
                try:
                    out[key] = float(val)
                except (TypeError, ValueError):
                    if val not in (None, ""):
                        out[key] = val
            return out if out else None
        except Exception as exc:
            logger.debug("Row parse error: %s", exc)
            return None

    def _request_prediction(self, row: Dict[str, Any]):
        self._busy = True
        self._worker = _PredictWorker(self.api_url, row)

        def clear_busy():
            self._busy = False

        self._worker.finished_ok.connect(self._on_ok)
        self._worker.finished_err.connect(self._on_err)
        self._worker.finished.connect(clear_busy)
        self._worker.start()

    def _on_ok(self, body: dict):
        self.prediction_received.emit(body)

    def _on_err(self, message: str):
        self.api_error.emit(message)
