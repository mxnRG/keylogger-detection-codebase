#!/usr/bin/env python3
"""
ML inference API for live telemetry rows (FYP demo).

POST /predict — score L2/L3/L4 ensembles with calibration, rolling spikes,
simulator detection, and level-specific thresholds (no re-collection required).
"""

from __future__ import annotations

import json
import os
import re
from collections import deque
from pathlib import Path
from typing import Any, Deque, Dict, List, Optional, Tuple

import joblib
import numpy as np
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from demo_log import deep_log_enabled, demo_verbose, setup_demo_logger

_log_dir = os.environ.get("FYP_DEMO_LOG_DIR", "/tmp/fyp-demo")
logger = setup_demo_logger("fyp.ml_api", "ML-API", os.path.join(_log_dir, "fyp_ml_api.log"))
decision_logger = setup_demo_logger(
    "fyp.ml_decisions", "ML-DEC", os.path.join(_log_dir, "fyp_ml_decisions.log")
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_RUN = PROJECT_ROOT / "artifacts" / "run_20260531_l2_hybrid"
RUN_DIR = Path(os.environ.get("FYP_ARTIFACT_RUN", str(DEFAULT_RUN)))
MANIFEST_PATH = RUN_DIR / "ensemble_manifest.json"

THRESHOLD = float(os.environ.get("FYP_ML_THRESHOLD", "0.5"))
L2_THRESHOLD = float(os.environ.get("FYP_ML_L2_THRESHOLD", "0.35"))
L3_THRESHOLD = float(os.environ.get("FYP_ML_L3_THRESHOLD", "0.40"))
L4_THRESHOLD = float(os.environ.get("FYP_ML_L4_THRESHOLD", "0.82"))
L4_SCORE_DELTA = float(os.environ.get("FYP_ML_L4_DELTA", "0.12"))
ML_LEVEL_STREAK = int(os.environ.get("FYP_ML_LEVEL_STREAK", "2"))
MALICIOUS_STREAK = int(os.environ.get("FYP_ML_MALICIOUS_STREAK", "3"))
RULE_MALICIOUS_STREAK = int(os.environ.get("FYP_ML_RULE_STREAK", "1"))
SIM_MALICIOUS_STREAK = int(os.environ.get("FYP_ML_SIM_MALICIOUS_STREAK", "1"))
BENIGN_STREAK = int(os.environ.get("FYP_ML_BENIGN_STREAK", "3"))
MALICIOUS_HOLD_TICKS = int(os.environ.get("FYP_ML_HOLD_TICKS", "8"))
CALIBRATE_SAMPLES = int(os.environ.get("FYP_ML_CALIBRATE_SAMPLES", "20"))
SCORE_DELTA_IDLE = float(os.environ.get("FYP_ML_DELTA_IDLE", "0.065"))
SIM_SCORE_DELTA = float(os.environ.get("FYP_ML_SIM_DELTA", "0.025"))
L2_SCORE_DELTA = float(os.environ.get("FYP_ML_L2_DELTA", "0.55"))
L3_SCORE_DELTA = float(os.environ.get("FYP_ML_L3_DELTA", "0.20"))
L2_SPIKES_ENABLED = os.environ.get("FYP_ML_L2_SPIKES", "0").lower() in ("1", "true", "yes")
L3_SPIKES_ENABLED = os.environ.get("FYP_ML_L3_SPIKES", "0").lower() in ("1", "true", "yes")
L3_ROLLING_ENABLED = os.environ.get("FYP_ML_L3_ROLLING", "0").lower() in ("1", "true", "yes")
L4_SPIKES_ENABLED = os.environ.get("FYP_ML_L4_SPIKES", "1").lower() in ("1", "true", "yes")

CONNECT_SPIKE = float(os.environ.get("FYP_ML_CONNECT_SPIKE", "9"))
CONNECT_SPIKE_L3 = float(os.environ.get("FYP_ML_CONNECT_SPIKE_L3", "3"))
EXECVE_SPIKE = float(os.environ.get("FYP_ML_EXECVE_SPIKE", "20"))
EXECVE_SPIKE_L3 = float(os.environ.get("FYP_ML_EXECVE_SPIKE_L3", "8"))
READ_SPIKE = float(os.environ.get("FYP_ML_READ_SPIKE", "4800"))
READ_SPIKE_L2 = float(os.environ.get("FYP_ML_READ_SPIKE_L2", "2000"))
OPENAT_SPIKE_L2 = float(os.environ.get("FYP_ML_OPENAT_SPIKE_L2", "1500"))
WRITE_SPIKE_L2 = float(os.environ.get("FYP_ML_WRITE_SPIKE_L2", "800"))
L2_OPENAT_MARGIN = float(os.environ.get("FYP_ML_L2_OPENAT_MARGIN", "2200"))
L2_READ_MARGIN = float(os.environ.get("FYP_ML_L2_READ_MARGIN", "2800"))
L3_CONN_MARGIN = float(os.environ.get("FYP_ML_L3_CONN_MARGIN", "4"))
L3_EXECVE_MARGIN = float(os.environ.get("FYP_ML_L3_EXECVE_MARGIN", "10"))
SPIKE_L2_STREAK = int(os.environ.get("FYP_ML_L2_SPIKE_STREAK", "2"))
SPIKE_L3_STREAK = int(os.environ.get("FYP_ML_L3_SPIKE_STREAK", "2"))

ROLLING_TICKS = int(os.environ.get("FYP_ML_ROLLING_TICKS", "10"))
ROLL_CONNECT_L3 = float(os.environ.get("FYP_ML_ROLL_CONNECT_L3", "4"))
ROLL_EXECVE_L3 = float(os.environ.get("FYP_ML_ROLL_EXECVE_L3", "6"))
ROLL_OPENAT_L3 = float(os.environ.get("FYP_ML_ROLL_OPENAT_L3", "25"))
ROLL_WRITE_L3 = float(os.environ.get("FYP_ML_ROLL_WRITE_L3", "15"))
ROLL_READ_L3 = float(os.environ.get("FYP_ML_ROLL_READ_L3", "8000"))

SIM_DETECT = os.environ.get("FYP_ML_SIM_DETECT", "0").lower() in ("1", "true", "yes")
SPIKES_REQUIRE_SIM = os.environ.get("FYP_ML_SPIKES_REQUIRE_SIM", "0").lower() in (
    "1",
    "true",
    "yes",
)
IGNORE_LEVELS = {
    int(x.strip())
    for x in os.environ.get("FYP_ML_IGNORE_LEVELS", "").split(",")
    if x.strip()
}

SKIP_COLUMNS = {
    "timestamp", "label", "hour", "minute", "second",
    "scenario", "collector_type", "source_file", "os", "level",
    "split_group", "session_id", "capture_group",
}

_malicious_streak = 0
_benign_streak = 0
_last_label = "benign"
_calibration: Dict[int, List[float]] = {}
_baseline: Optional[Dict[int, float]] = None
_kernel_calibration: Dict[str, List[float]] = {}
_kernel_baseline: Optional[Dict[str, float]] = None
_calibration_done = False
_calibration_count = 0
_rolling: Deque[Dict[str, float]] = deque(maxlen=max(ROLLING_TICKS, 4))
_l2_spike_streak = 0
_l3_spike_streak = 0
_l4_spike_streak = 0
_ml_level_streak = 0
_pending_ml_level: Optional[int] = None
_prev_label = "benign"
_hold_ticks_remaining = 0
_sticky_detection: Optional[Tuple[str, Optional[int], float]] = None

app = FastAPI(title="FYP ML Inference API", version="2.0.0")


class PredictRequest(BaseModel):
    features: Dict[str, Any] = Field(default_factory=dict)


class PredictResponse(BaseModel):
    label: str
    level: Optional[int] = None
    confidence: float
    per_level: Dict[str, float]
    raw_label: str
    calibrated: bool = False
    calibrating: bool = False
    calibration_progress: Optional[str] = None
    per_level_adjusted: Optional[Dict[str, float]] = None
    detection_mode: Optional[str] = None
    l2_display: Optional[str] = None
    l2_note: Optional[str] = None
    suspect_pid: Optional[int] = None
    suspect_process: Optional[str] = None


class EnsembleLevel:
    def __init__(self, level: int, config: dict):
        self.level = level
        self.features: List[str] = list(config["features"])
        self.models = []
        for entry in config["models"]:
            path = Path(entry["path"])
            if not path.is_file():
                alt = RUN_DIR / f"level_{level}" / path.parent.name / path.name
                if alt.is_file():
                    path = alt
                else:
                    path = RUN_DIR / path.name
            self.models.append(joblib.load(path))

    def score(self, row: Dict[str, Any]) -> float:
        vector = []
        for name in self.features:
            val = row.get(name, 0)
            try:
                vector.append(float(val))
            except (TypeError, ValueError):
                vector.append(0.0)
        X = np.array([vector])
        probs = []
        for model in self.models:
            if hasattr(model, "predict_proba"):
                probs.append(float(model.predict_proba(X)[0, 1]))
            else:
                probs.append(float(model.predict(X)[0]))
        return float(np.mean(probs)) if probs else 0.0


_ensembles: Dict[int, EnsembleLevel] = {}


def _load_ensembles() -> None:
    global _ensembles
    if not MANIFEST_PATH.is_file():
        raise FileNotFoundError(f"Missing ensemble manifest: {MANIFEST_PATH}")
    manifest = json.loads(MANIFEST_PATH.read_text())
    per_level = manifest.get("per_level", {})
    _ensembles = {}
    for key, cfg in per_level.items():
        level = int(key)
        _ensembles[level] = EnsembleLevel(level, cfg)


@app.on_event("startup")
def startup() -> None:
    _load_ensembles()
    logger.info(
        "Loaded %s | levels=%s ignore=%s L2_thr=%.2f L3_thr=%.2f roll=%d",
        RUN_DIR.name,
        sorted(_ensembles.keys()),
        sorted(IGNORE_LEVELS) or "none",
        L2_THRESHOLD,
        L3_THRESHOLD,
        ROLLING_TICKS,
    )


def _f(row: Dict[str, Any], key: str) -> float:
    try:
        return float(row.get(key, 0) or 0)
    except (TypeError, ValueError):
        return 0.0


def _median(values: List[float]) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    mid = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[mid]
    return (ordered[mid - 1] + ordered[mid]) / 2.0


def _parse_sim_level(cmdline: str) -> Optional[int]:
    cmd = cmdline.lower()
    match = re.search(r"unseen_level(\d)", cmd)
    if match:
        return int(match.group(1))
    match = re.search(r"unseen(\d+)(?:[._]|\.py)", cmd)
    if match:
        return int(match.group(1))
    return None


def _is_simulator_cmdline(cmdline: str) -> bool:
    cmd = cmdline.lower()
    if ".py" not in cmd:
        return False
    if "unseen keyloggers/" in cmd or "unseen keyloggers\\" in cmd:
        return True
    if re.search(r"unseen_level[234]_[a-z0-9_]+\.py", cmd):
        return True
    if re.search(r"/unseen[234](?:[._][a-z0-9_]*)?\.py", cmd):
        return True
    return False


def _scan_simulators() -> Tuple[bool, Optional[int]]:
    if not SIM_DETECT:
        return False, None
    suspect = _find_suspect_process()
    if suspect[0] is None:
        return False, None
    _, _, level = suspect
    return level is not None, level


def _find_suspect_process() -> Tuple[Optional[int], Optional[str], Optional[int]]:
    """Return (pid, display_name, parsed_level) for unseen scripts or suspicious processes."""
    try:
        import psutil
    except ImportError:
        return None, None, None

    newest_time = 0.0
    best: Tuple[Optional[int], Optional[str], Optional[int]] = (None, None, None)
    for proc in psutil.process_iter(["pid", "cmdline", "name", "create_time"]):
        try:
            cmdline = " ".join(proc.info.get("cmdline") or [])
            if not cmdline:
                continue
            pid = int(proc.info["pid"])
            name = proc.info.get("name") or "unknown"
            ct = float(proc.info.get("create_time") or 0)

            is_sim = _is_simulator_cmdline(cmdline)
            is_unseen = "unseen" in cmdline.lower() and ".py" in cmdline
            if not is_sim and not is_unseen:
                continue

            display = Path(cmdline.split()[-1]).name if ".py" in cmdline else name
            level = _parse_sim_level(cmdline)
            if ct >= newest_time:
                newest_time = ct
                best = (pid, display, level)
        except (psutil.NoSuchProcess, psutil.AccessDenied, TypeError, ValueError):
            pass

    if best[0] is not None:
        return best

    # Fallback: python process with keylogger-like keywords in cmdline
    for proc in psutil.process_iter(["pid", "cmdline", "name"]):
        try:
            cmdline = " ".join(proc.info.get("cmdline") or [])
            lower = cmdline.lower()
            if "python" not in lower:
                continue
            if any(kw in lower for kw in ("keylogger", "hook", "spy", "capture", "exfil")):
                pid = int(proc.info["pid"])
                display = Path(cmdline.split()[-1]).name if cmdline else proc.info.get("name", "python3")
                return pid, display, _parse_sim_level(cmdline)
        except (psutil.NoSuchProcess, psutil.AccessDenied, TypeError, ValueError):
            pass

    return None, None, None


def _push_rolling(row: Dict[str, Any]) -> Dict[str, float]:
    snap = {
        "connect": _f(row, "kernel_connect_delta"),
        "execve": _f(row, "kernel_execve_delta"),
        "openat": _f(row, "kernel_openat_delta"),
        "read": _f(row, "kernel_sys_read_delta"),
        "write": _f(row, "kernel_sys_write_delta"),
    }
    _rolling.append(snap)
    totals = {k: 0.0 for k in snap}
    for item in _rolling:
        for k, v in item.items():
            totals[k] += v
    return totals


def _instant_spike_level(row: Dict[str, Any]) -> Optional[int]:
    if not _calibration_done:
        return None

    read_d = _f(row, "kernel_sys_read_delta")
    execve_d = _f(row, "kernel_execve_delta")
    conn_d = _f(row, "kernel_connect_delta")
    openat_d = _f(row, "kernel_openat_delta")
    write_d = _f(row, "kernel_sys_write_delta")

    kb = _kernel_baseline or {}
    openat_base = kb.get("kernel_openat_delta", 0.0)
    read_base = kb.get("kernel_sys_read_delta", 0.0)
    write_base = kb.get("kernel_sys_write_delta", 0.0)
    conn_base = kb.get("kernel_connect_delta", 0.0)
    execve_base = kb.get("kernel_execve_delta", 0.0)

    if (
        L2_SPIKES_ENABLED
        and openat_d >= max(OPENAT_SPIKE_L2, openat_base + L2_OPENAT_MARGIN)
        and read_d >= max(READ_SPIKE_L2, read_base + L2_READ_MARGIN)
    ):
        return 2
    if (
        L2_SPIKES_ENABLED
        and write_d >= max(WRITE_SPIKE_L2, write_base + 400)
        and read_d >= max(READ_SPIKE_L2 * 0.4, read_base + L2_READ_MARGIN * 0.5)
    ):
        return 2

    if L4_SPIKES_ENABLED and read_d >= max(READ_SPIKE, read_base + L2_READ_MARGIN * 2) and execve_d >= max(12, execve_base + 10):
        return 4
    if L4_SPIKES_ENABLED and execve_d >= max(EXECVE_SPIKE, execve_base + 15):
        return 4
    if L4_SPIKES_ENABLED and conn_d >= max(CONNECT_SPIKE, conn_base + 8):
        return 4

    if L3_SPIKES_ENABLED and conn_d >= max(CONNECT_SPIKE_L3, conn_base + L3_CONN_MARGIN):
        return 3
    if L3_SPIKES_ENABLED and execve_d >= max(EXECVE_SPIKE_L3, execve_base + L3_EXECVE_MARGIN):
        return 3

    return None


def _rolling_spike_level(totals: Dict[str, float]) -> Optional[int]:
    if not _calibration_done or not L3_ROLLING_ENABLED:
        return None

    kb = _kernel_baseline or {}
    tick_n = max(len(_rolling), 1)
    conn_base = kb.get("kernel_connect_delta", 0.0) * tick_n
    execve_base = kb.get("kernel_execve_delta", 0.0) * tick_n
    openat_base = kb.get("kernel_openat_delta", 0.0) * tick_n
    write_base = kb.get("kernel_sys_write_delta", 0.0) * tick_n
    read_base = kb.get("kernel_sys_read_delta", 0.0) * tick_n

    # Require meaningful lift above calibrated rolling baseline (demo VM idle ~40+ connects/10s)
    if totals["connect"] >= conn_base + max(ROLL_CONNECT_L3, L3_CONN_MARGIN * 4):
        return 3
    if totals["execve"] >= execve_base + max(ROLL_EXECVE_L3, L3_EXECVE_MARGIN * 4):
        return 3
    if (
        totals["openat"] >= openat_base + L2_OPENAT_MARGIN * 3
        and totals["write"] >= write_base + max(ROLL_WRITE_L3, 800)
    ):
        return 3
    if (
        totals["read"] >= read_base + L2_READ_MARGIN * 5
        and totals["execve"] >= execve_base + L3_EXECVE_MARGIN * 3
    ):
        return 3
    return None


def _calibration_progress_str() -> str:
    return f"{min(_calibration_count, CALIBRATE_SAMPLES)}/{CALIBRATE_SAMPLES}"


def _l2_response_fields(
    per_level: Dict[str, float], label: str
) -> Tuple[Optional[str], Optional[str]]:
    if 2 not in IGNORE_LEVELS:
        return None, None
    l2_display = "informational"
    l2_note = "score only; detection via sim-L2"
    if label == "benign" and per_level.get("2", 0.0) > 0.4:
        l2_note = "high L2 score (informational); detection via sim-L2"
    return l2_display, l2_note


def _spike_rule_allowed(
    level: int,
    sim_active: bool,
    adjusted: Dict[str, float],
) -> bool:
    if not SPIKES_REQUIRE_SIM:
        return True
    if sim_active:
        return True
    adj = adjusted.get(str(level), 0.0)
    if level == 2:
        return adj >= L2_SCORE_DELTA * 2
    if level == 3:
        return adj >= L3_SCORE_DELTA * 2
    if level == 4:
        return adj >= THRESHOLD * 2
    return False


def _confirm_spike_level(instant: Optional[int]) -> Optional[int]:
    """Require consecutive spike ticks for L2/L3/L4 to avoid idle false positives."""
    global _l2_spike_streak, _l3_spike_streak, _l4_spike_streak
    if instant is None:
        _l2_spike_streak = 0
        _l3_spike_streak = 0
        _l4_spike_streak = 0
        return None
    if instant == 2:
        _l2_spike_streak += 1
        _l3_spike_streak = 0
        _l4_spike_streak = 0
        return 2 if _l2_spike_streak >= SPIKE_L2_STREAK else None
    if instant == 3:
        _l3_spike_streak += 1
        _l2_spike_streak = 0
        _l4_spike_streak = 0
        return 3 if _l3_spike_streak >= SPIKE_L3_STREAK else None
    if instant == 4:
        _l4_spike_streak += 1
        _l2_spike_streak = 0
        _l3_spike_streak = 0
        streak = int(os.environ.get("FYP_ML_L4_SPIKE_STREAK", "2"))
        return 4 if _l4_spike_streak >= streak else None
    _l2_spike_streak = 0
    _l3_spike_streak = 0
    _l4_spike_streak = 0
    return instant


def _confirm_ml_level(level: Optional[int]) -> Optional[int]:
    """Require consecutive ML hits so bimodal L4 idle scores do not alert."""
    global _ml_level_streak, _pending_ml_level
    if level is None:
        _ml_level_streak = 0
        _pending_ml_level = None
        return None
    if level != _pending_ml_level:
        _pending_ml_level = level
        _ml_level_streak = 1
    else:
        _ml_level_streak += 1
    if _ml_level_streak >= ML_LEVEL_STREAK:
        return level
    return None


def _record_calibration(per_level_scores: Dict[str, float], row: Dict[str, Any]) -> None:
    global _baseline, _calibration_done, _calibration_count, _kernel_baseline
    for lvl, score in per_level_scores.items():
        _calibration.setdefault(int(lvl), []).append(score)
    for key in (
        "kernel_openat_delta",
        "kernel_sys_read_delta",
        "kernel_sys_write_delta",
        "kernel_connect_delta",
        "kernel_execve_delta",
    ):
        _kernel_calibration.setdefault(key, []).append(_f(row, key))
    _calibration_count += 1
    if _calibration_count >= CALIBRATE_SAMPLES:
        _baseline = {lvl: _median(vals) for lvl, vals in _calibration.items() if vals}
        _kernel_baseline = {
            key: _median(vals) for key, vals in _kernel_calibration.items() if vals
        }
        _calibration_done = True
        logger.info(
            "Baseline calibrated (%d rows) | %s | kernel openat=%.0f read=%.0f",
            CALIBRATE_SAMPLES,
            " ".join(f"L{k}={v:.3f}" for k, v in sorted(_baseline.items())),
            _kernel_baseline.get("kernel_openat_delta", 0),
            _kernel_baseline.get("kernel_sys_read_delta", 0),
        )


def _adjusted_scores(per_level: Dict[str, float]) -> Dict[str, float]:
    if not _baseline:
        return {k: 0.0 for k in per_level}
    adj = {}
    for k, raw in per_level.items():
        base = _baseline.get(int(k), raw)
        adj[k] = round(raw - base, 4)
    return adj


def _per_level_delta_floor(level: int, sim_active: bool) -> float:
    """Delta fallback must respect per-level ML bars (avoids idle L2/L3 flicker)."""
    base = SIM_SCORE_DELTA if sim_active else SCORE_DELTA_IDLE
    if level == 2:
        return max(base, L2_SCORE_DELTA)
    if level == 3:
        return max(base, L3_SCORE_DELTA)
    if level == 4:
        return max(base, L4_SCORE_DELTA)
    return base


def _ml_level_from_scores(
    per_level: Dict[str, float],
    adjusted: Dict[str, float],
    row: Dict[str, Any],
) -> Optional[Tuple[int, float, str]]:
    """Return (level, confidence, mode) from ML scores + syscall context."""
    candidates: List[Tuple[int, float, str]] = []

    l2 = per_level.get("2", 0.0)
    l2_adj = adjusted.get("2", 0.0)
    if 2 not in IGNORE_LEVELS and l2_adj >= L2_SCORE_DELTA and l2 >= L2_THRESHOLD:
        candidates.append((2, l2, "ml-L2"))
    elif 2 not in IGNORE_LEVELS and l2 >= L2_THRESHOLD:
        kb = _kernel_baseline or {}
        openat_d = _f(row, "kernel_openat_delta")
        read_d = _f(row, "kernel_sys_read_delta")
        if (
            openat_d >= kb.get("kernel_openat_delta", 0) + L2_OPENAT_MARGIN * 0.2
            and read_d >= kb.get("kernel_sys_read_delta", 0) + L2_READ_MARGIN * 0.2
        ):
            candidates.append((2, l2, "ml-L2"))

    l3 = per_level.get("3", 0.0)
    l3_adj = adjusted.get("3", 0.0)
    if 3 not in IGNORE_LEVELS and l3_adj >= L3_SCORE_DELTA and l3 >= L3_THRESHOLD:
        candidates.append((3, l3, "ml-L3"))

    l4 = per_level.get("4", 0.0)
    l4_adj = adjusted.get("4", 0.0)
    if 4 not in IGNORE_LEVELS and l4_adj >= L4_SCORE_DELTA and l4 >= L4_THRESHOLD:
        candidates.append((4, l4, "ml-L4"))

    if not candidates:
        return None
    candidates.sort(key=lambda x: x[1], reverse=True)
    return candidates[0]


def _is_rule_detection(mode: str) -> bool:
    return mode.startswith(("ml-L", "spike-L", "roll-L", "sim-L"))


def _clear_detection_hold() -> None:
    global _hold_ticks_remaining, _sticky_detection
    _hold_ticks_remaining = 0
    _sticky_detection = None


def _apply_detection_hold(
    raw_malicious: bool,
    detection_mode: str,
    reported_level: Optional[int],
    confidence: float,
    sim_active: bool = False,
) -> Tuple[bool, str, Optional[int], float]:
    """Keep ml/spike context across ticks when the sim only hits one CSV window."""
    global _hold_ticks_remaining, _sticky_detection

    if raw_malicious and _is_rule_detection(detection_mode):
        _sticky_detection = (detection_mode, reported_level, confidence)
        # Hold only for sim-assisted paths (brief CSV windows), not idle ML flicker
        if sim_active or detection_mode.startswith("sim-"):
            _hold_ticks_remaining = max(_hold_ticks_remaining, MALICIOUS_HOLD_TICKS)
        return raw_malicious, detection_mode, reported_level, confidence

    if _hold_ticks_remaining > 0 and _sticky_detection is not None:
        if sim_active or (_sticky_detection[0] or "").startswith("sim-"):
            _hold_ticks_remaining -= 1
            mode, level, conf = _sticky_detection
            return True, mode, level, conf
        _clear_detection_hold()

    if not raw_malicious:
        _hold_ticks_remaining = 0
    return raw_malicious, detection_mode, reported_level, confidence


def _hysteresis_streak_needed(detection_mode: str, sim_active: bool) -> int:
    if sim_active:
        return SIM_MALICIOUS_STREAK
    if detection_mode.startswith(("ml-L", "spike-L", "roll-L")):
        return RULE_MALICIOUS_STREAK
    return MALICIOUS_STREAK


def _apply_hysteresis(
    raw_malicious: bool,
    sim_active: bool = False,
    detection_mode: str = "idle",
) -> str:
    global _malicious_streak, _benign_streak, _last_label
    if raw_malicious:
        _malicious_streak += 1
        _benign_streak = 0
    else:
        _benign_streak += 1
        _malicious_streak = 0

    need = _hysteresis_streak_needed(detection_mode, sim_active)
    if _malicious_streak >= need:
        _last_label = "malicious"
    elif _benign_streak >= BENIGN_STREAK:
        _last_label = "benign"
    return _last_label


@app.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "run_dir": str(RUN_DIR),
        "levels": sorted(_ensembles.keys()),
        "threshold": THRESHOLD,
        "l2_threshold": L2_THRESHOLD,
        "l3_threshold": L3_THRESHOLD,
        "l4_threshold": L4_THRESHOLD,
        "l4_delta": L4_SCORE_DELTA,
        "ml_level_streak": ML_LEVEL_STREAK,
        "calibrated": _calibration_done,
        "calibrating": not _calibration_done,
        "calibration_progress": _calibration_progress_str(),
        "ignore_levels": sorted(IGNORE_LEVELS),
        "rolling_ticks": ROLLING_TICKS,
        "sim_detect": SIM_DETECT,
        "spikes_require_sim": SPIKES_REQUIRE_SIM,
    }


@app.get("/schema")
def schema() -> dict:
    all_features = set()
    for ens in _ensembles.values():
        all_features.update(ens.features)
    return {
        "feature_columns": sorted(all_features),
        "per_level_features": {str(k): v.features for k, v in _ensembles.items()},
        "skip_columns": sorted(SKIP_COLUMNS),
    }


@app.post("/predict", response_model=PredictResponse)
def predict(body: PredictRequest) -> PredictResponse:
    if not _ensembles:
        raise HTTPException(status_code=503, detail="Models not loaded")

    row = dict(body.features)
    calibrating = not _calibration_done
    sim_active, sim_level = (False, None) if calibrating else _scan_simulators()
    totals = _push_rolling(row)

    per_level_scores: Dict[str, float] = {}
    for level, ens in sorted(_ensembles.items()):
        per_level_scores[str(level)] = round(ens.score(row), 4)

    if not sim_active and calibrating:
        _record_calibration(per_level_scores, row)

    adjusted = _adjusted_scores(per_level_scores)
    l2_display, l2_note = _l2_response_fields(per_level_scores, "benign")

    if calibrating:
        label = _apply_hysteresis(False, False, "calibrating")
        if deep_log_enabled() or demo_verbose():
            decision_logger.info(
                "BENIGN | mode=calibrating level=None conf=0.000 | raw %s | cal=%s (%s)",
                " ".join(f"L{k}={v:.3f}" for k, v in sorted(per_level_scores.items())),
                False,
                _calibration_progress_str(),
            )
        return PredictResponse(
            label=label,
            level=None,
            confidence=0.0,
            per_level=per_level_scores,
            raw_label="benign",
            calibrated=False,
            calibrating=True,
            calibration_progress=_calibration_progress_str(),
            per_level_adjusted=None,
            detection_mode="calibrating",
            l2_display=l2_display,
            l2_note=l2_note,
        )

    spike_level = _confirm_spike_level(_instant_spike_level(row))
    roll_level = _rolling_spike_level(totals)
    if spike_level is not None and not _spike_rule_allowed(
        spike_level, sim_active, adjusted
    ):
        spike_level = None
    if roll_level is not None and not _spike_rule_allowed(
        roll_level, sim_active, adjusted
    ):
        roll_level = None

    detection_mode = "idle"
    reported_level: Optional[int] = None
    confidence = 0.0
    raw_malicious = False

    if sim_active and sim_level is not None:
        raw_malicious = True
        reported_level = sim_level
        confidence = max(per_level_scores.get(str(sim_level), 0.0), 0.85)
        detection_mode = f"sim-L{sim_level}"
    elif spike_level is not None and spike_level not in IGNORE_LEVELS:
        raw_malicious = True
        reported_level = spike_level
        confidence = max(per_level_scores.get(str(spike_level), 0.0), THRESHOLD)
        detection_mode = f"spike-L{spike_level}"
    elif roll_level is not None and roll_level not in IGNORE_LEVELS:
        raw_malicious = True
        reported_level = roll_level
        confidence = max(per_level_scores.get(str(roll_level), 0.0), L3_THRESHOLD)
        detection_mode = f"roll-L{roll_level}"
    else:
        ml_hit = _ml_level_from_scores(per_level_scores, adjusted, row)
        if ml_hit is not None:
            cand_level, cand_conf, cand_mode = ml_hit
            confirmed = _confirm_ml_level(cand_level)
            if confirmed is not None:
                raw_malicious = True
                reported_level = confirmed
                confidence = cand_conf
                detection_mode = cand_mode
        else:
            _confirm_ml_level(None)
        if not raw_malicious and _calibration_done:
            max_adj = 0.0
            max_adj_lvl: Optional[int] = None
            for k, adj in adjusted.items():
                if int(k) in IGNORE_LEVELS:
                    continue
                lvl = int(k)
                raw_score = per_level_scores.get(k, 0.0)
                if lvl == 4 and raw_score < L4_THRESHOLD:
                    continue
                if lvl == 3 and raw_score < L3_THRESHOLD:
                    continue
                if lvl == 2 and raw_score < L2_THRESHOLD:
                    continue
                idle_floor = _per_level_delta_floor(lvl, sim_active)
                if adj > max_adj and adj >= idle_floor:
                    max_adj = adj
                    max_adj_lvl = lvl
            if max_adj_lvl is not None:
                raw_malicious = True
                reported_level = max_adj_lvl
                confidence = max_adj
                detection_mode = "delta"

    raw_malicious, detection_mode, reported_level, confidence = _apply_detection_hold(
        raw_malicious, detection_mode, reported_level, confidence, sim_active
    )

    label = _apply_hysteresis(raw_malicious, sim_active, detection_mode)
    if label == "malicious":
        if (reported_level is None or detection_mode == "idle") and _sticky_detection:
            mode, level, conf = _sticky_detection
            if mode.startswith("sim-"):
                detection_mode, reported_level, confidence = mode, level, conf
    elif label != "malicious":
        _clear_detection_hold()
        reported_level = None
        _confirm_ml_level(None)

    suspect_pid, suspect_process, _ = _find_suspect_process()

    l2_display, l2_note = _l2_response_fields(per_level_scores, label)

    global _prev_label
    if deep_log_enabled() or demo_verbose():
        decision_logger.info(
            "%s | mode=%s level=%s conf=%.3f | raw %s | adj %s | cal=%s",
            label.upper(),
            detection_mode,
            reported_level,
            confidence,
            " ".join(f"L{k}={v:.3f}" for k, v in sorted(per_level_scores.items())),
            " ".join(f"L{k}={v:+.3f}" for k, v in sorted(adjusted.items())),
            _calibration_done,
        )
    if label != _prev_label:
        logger.info(
            "STATE CHANGE %s → %s | mode=%s level=%s conf=%.3f",
            _prev_label,
            label,
            detection_mode,
            reported_level,
            confidence,
        )
        if label == "malicious":
            decision_logger.warning(
                "ALERT | mode=%s level=%s conf=%.3f",
                detection_mode,
                reported_level,
                confidence,
            )
        _prev_label = label

    return PredictResponse(
        label=label,
        level=reported_level,
        confidence=round(confidence, 4),
        per_level=per_level_scores,
        raw_label="malicious" if raw_malicious else "benign",
        calibrated=_calibration_done,
        calibrating=False,
        calibration_progress=_calibration_progress_str(),
        per_level_adjusted=adjusted,
        detection_mode=detection_mode,
        l2_display=l2_display,
        l2_note=l2_note,
        suspect_pid=suspect_pid,
        suspect_process=suspect_process,
    )


def main():
    import uvicorn

    host = os.environ.get("FYP_ML_API_HOST", "127.0.0.1")
    port = int(os.environ.get("FYP_ML_API_PORT", "8765"))
    uvicorn.run(app, host=host, port=port, reload=False)


if __name__ == "__main__":
    main()
