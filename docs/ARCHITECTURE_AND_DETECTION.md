# FYP Keylogger Detection System — Architecture & Detection Deep Dive

**Version:** Kernel v0.6 | Daemon v0.2 | GUI v3.3 | ML API v2.1  
**Last updated:** June 2026  
**Audience:** Developers, thesis examiners, and maintainers

---

## 1. Executive Summary

This system detects Linux keyloggers through **behavioral analysis** without capturing keystroke content. It combines four layers:

| Layer | Component | Role |
|-------|-----------|------|
| Kernel | `fyp_kbd.ko` | Observes keyboard input-stream access (timing, PID, process name) |
| Heuristics | `fyp_daemon.py` | Real-time rules on Netlink events (rapid typing, unknown process, burst) |
| Telemetry + ML | `collector_live.py` + `ml_api.py` | eBPF syscall/process features scored by per-level ensemble models |
| Presentation | PySide6 GUI | Dashboard, alerts, ML status, resource monitoring |

**Privacy-by-design:** No keycodes, scancodes, or plaintext keystrokes are ever captured or stored.

---

## 2. End-to-End Data Flow

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         KERNEL SPACE (fyp_kbd.ko)                       │
│  keyboard_notifier_list → workqueue (cmdline) → Netlink protocol 31     │
└───────────────────────────────┬─────────────────────────────────────────┘
                                │ 158-byte events (timestamp, pid, comm, …)
                                ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    USER SPACE — DAEMON (fyp_daemon.py)                  │
│  Netlink receiver → per-PID stats → 3 heuristics → /tmp/fyp_status.json │
└───────────────────────────────┬─────────────────────────────────────────┘
                                │ JSON (500 ms poll)
                                ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         GUI (main_gui.py / fyp_gui.py)                  │
│  DaemonMonitor + TelemetryMlMonitor + LkmStatusMonitor                  │
└───────────────────────────────┬─────────────────────────────────────────┘
                                │
        ┌───────────────────────┴───────────────────────┐
        ▼                                               ▼
 /tmp/fyp_status.json                    /tmp/fyp_telemetry_live.csv
 (heuristic alerts)                      (0.5 s eBPF rows)
                                                    │
                                                    ▼
                                         ml_api.py POST /predict
                                         (L2/L3/L4 ensembles)
```

### Live demo stack (6 processes)

Started via `sudo scripts/run_demo_verbose.sh`:

1. **LKM** — `fyp_kbd.ko` loaded once, kept alive by watchdog  
2. **Watchdog** — `scripts/lkm_watchdog.sh` reloads module if unloaded  
3. **Daemon** — `daemon/fyp_daemon.py`  
4. **ML API** — `scripts/ml_api.py` on `http://127.0.0.1:8765`  
5. **Collector** — `scripts/collector_live.py` (root, BCC/eBPF)  
6. **GUI** — `gui/main_gui.py`

---

## 3. Kernel Loadable Module (LKM)

**Source:** `kernel/fyp_kbd.c`  
**Binary:** `kernel/fyp_kbd.ko`

### 3.1 What it monitors

The module registers a **keyboard notifier** on `keyboard_notifier_list`. On each key press/release it records:

- `timestamp_ns` — monotonic time since boot  
- `pid` — process accessing the input stream  
- `comm` — 16-byte kernel task name  
- `cmdline` — up to 128 bytes (via deferred workqueue — safe mm_struct access)  
- `event_type` — press (0) or release (1)  
- `rapid_flag` — 1 if inter-event gap &lt; `rapid_threshold_ms` (default 50 ms)

**It does NOT record keycodes or character content.**

### 3.2 IPC: Netlink protocol 31

Events are sent as `struct fyp_netlink_event` (158 bytes) over a custom Netlink family (`NETLINK_FYP_DETECTOR = 31`). The daemon parses a 30-byte subset (cmdline omitted in current daemon for simplicity).

### 3.3 Runtime configuration (sysfs)

| Parameter | Default | Meaning |
|-----------|---------|---------|
| `rapid_threshold_ms` | 50 | Gap below which an event is "rapid" |
| `burst_threshold_eps` | 100 | Reference for burst detection (daemon-side) |

```bash
cat /sys/module/fyp_kbd/parameters/rapid_threshold_ms
echo 75 | sudo tee /sys/module/fyp_kbd/parameters/rapid_threshold_ms
```

### 3.4 Procfs interface

- `/proc/fyp_detector/stats` — event counters  
- `/proc/fyp_detector/config` — current thresholds  

### 3.5 Design constraints

- **Atomic context:** keyboard notifier cannot sleep; cmdline capture uses `schedule_work()` on `system_wq`  
- **NULL-safe mm_struct:** kernel threads return `"[kernel]"` instead of crashing  
- **Workqueue memory:** `kmalloc(GFP_ATOMIC)` in notifier, `kfree()` in handler  

---

## 4. Detection Daemon

**Source:** `daemon/fyp_daemon.py`

### 4.1 Architecture

- **Netlink thread** — blocking `recv()` loop  
- **Detection engine** — evaluates per-PID `ProcessStats` every event batch  
- **Status writer** — atomically updates `/tmp/fyp_status.json` (~500 ms)

### 4.2 Heuristic rules

| Rule | Condition | Severity | Rationale |
|------|-----------|----------|-----------|
| Rapid typing | `rapid_ratio > 50%` | HIGH | Automated key polling / hooking |
| Unknown process | `comm` not in whitelist | MEDIUM | Unexpected input reader |
| Burst pattern | `events_per_sec > 100` | HIGH | High-frequency stream access |

**Default whitelist:** `gnome-shell`, `Xorg`, `bash`, `firefox`, `code`, terminals, editors, etc.

### 4.3 Status file schema

```json
{
  "timestamp": "2026-06-01T13:32:04",
  "daemon_running": true,
  "kernel_loaded": true,
  "total_events": 5432,
  "processes": {
    "2048": {
      "comm": "suspicious",
      "total_events": 2500,
      "rapid_ratio": 80.0,
      "events_per_second": 120.0
    }
  },
  "alerts": [
    {
      "timestamp": "...",
      "severity": "HIGH",
      "message": "Rapid Input Stream Access: ...",
      "process": "suspicious",
      "pid": 2048
    }
  ]
}
```

The GUI `DaemonMonitor` polls this file and raises `Alert` objects with **PID + process name** — the format ML alerts now mirror.

---

## 5. Telemetry Collection

### 5.1 Offline dataset collection

Historical CSVs (L2–L4) were captured with eBPF tooling documented in `docs/ML_DATASET_REALISTIC_EVAL_PLAN.md`. Canonical paths live in `dataset/manifest.yaml` (~93k rows total).

### 5.2 Live collector (`scripts/collector_live.py`)

Runs as **root** using **BCC** (BPF Compiler Collection). Every **0.5 seconds** it:

1. Attaches kprobes/tracepoints for `read`, `write`, `openat`, `execve`, `connect`  
2. Aggregates per-interval **deltas** (then clears BPF hash maps)  
3. Reads `/proc/interrupts` for keyboard hardware interrupt count  
4. Samples `psutil` for CPU, memory, process counts, thread counts  
5. Appends one CSV row to `/tmp/fyp_telemetry_live.csv`

**Key feature columns:**

| Category | Examples |
|----------|----------|
| Kernel deltas | `kernel_sys_read_delta`, `kernel_openat_delta`, `kernel_execve_delta`, `kernel_connect_delta` |
| Keyboard | `keyboard_hardware_interrupts`, `cpu_to_keyboard_ratio` |
| Process context | `python_processes`, `shell_processes`, `suspicious_process_names`, `high_cpu_processes` |
| System | `cpu_usage`, `memory_usage`, `network_connections`, `process_count` |

These columns align with the ML training schema so live rows can be scored by offline-trained models without re-collection.

---

## 6. Machine Learning Pipeline

### 6.1 Threat levels (L2–L4)

| Level | Class | Typical technique |
|-------|-------|-------------------|
| **L2** | User-space hook / device scan | Reading `/dev/input/*`, procfs scanning |
| **L3** | Rootkit-style / persistence | Process hiding, exfiltration, agent queues |
| **L4** | Kernel-adjacent behavior | Syscall pressure, `/proc`/`/sys` enumeration |

Each level has a **separate ensemble** trained on benign vs malicious captures from **different VMs** (see `capture_groups` in `manifest.yaml`).

### 6.2 Training (`scripts/train_ml.py`)

**Models per level (ensemble average):**

| Model | Key hyperparameters |
|-------|---------------------|
| Random Forest | `n_estimators=300`, `class_weight="balanced"` |
| Extra Trees | `n_estimators=300`, `class_weight="balanced"` |
| XGBoost | `n_estimators=300`, `max_depth=6`, `lr=0.1`, `subsample=0.9`, `colsample_bytree=0.9` |

**Ensemble score** = mean of the three `predict_proba` positive-class probabilities.

**Artifacts** (per run under `artifacts/run_<id>/`):

- `ensemble_manifest.json` — feature lists + model paths  
- `level_N/{random_forest,extra_trees,xgboost}/*.joblib`  
- `evaluation.json` — tiered A/B/C metrics  
- `metrics.json`, confusion matrices, ROC/PR plots  

**Live demo run:** `artifacts/run_20260531_l2_hybrid` (tuned L2 + baseline L3/L4).

### 6.3 Evaluation tiers (thesis methodology)

| Tier | Split | Interpretation |
|------|-------|----------------|
| **A** | Stratified row split within each level | Optimistic upper bound (~1.0 AUC) |
| **B** | Cross-level holdout | Generalization across sophistication levels |
| **C** | Cross-level + behavioral feature subset | **Primary realistic metric** (macro AUC ~0.75–0.99) |

Tier C avoids label-leaking features (constants, filename-derived flags) documented in `docs/DATASET_QUALITY_REPORT.md`.

### 6.4 Live inference API (`scripts/ml_api.py` v2)

**Endpoint:** `POST http://127.0.0.1:8765/predict`

**Detection pipeline (priority order):**

1. **Calibration** — first 20 rows establish per-level and kernel-delta baselines (no alerts)  
2. **Sim scan** (optional, `FYP_ML_SIM_DETECT=1`) — unseen keylogger script in process list  
3. **Syscall spikes** — L2 openat+read, L4 read+execve, etc. (configurable)  
4. **Rolling L3** (optional, off by default) — summed deltas over 10 ticks  
5. **ML ensembles** — `ml-L2`, `ml-L3`, `ml-L4` when score exceeds level threshold **and** calibrated delta  
6. **Delta fallback** — max adjusted score above idle floor  
7. **Hysteresis** — consecutive malicious/benign ticks before UI state change  
8. **Hold** (sim-only) — brief alert persistence for one-shot CSV windows  

**Idle stability (L4 fix, June 2026):**

The L4 ensemble exhibits **bimodal idle scores** (~0.24 vs ~0.76) on the demo VM. Raw scores above 0.5 previously triggered false `ml-L4` alerts. Mitigations:

- `FYP_ML_L4_THRESHOLD=0.82` — raw score bar  
- `FYP_ML_L4_DELTA=0.12` — must exceed calibrated baseline by meaningful margin  
- `FYP_ML_LEVEL_STREAK=2` — two consecutive ML hits required  
- Detection **hold** disabled for non-sim paths  
- L3 ML now also requires `raw >= L3_THRESHOLD`

**Response fields (selected):**

| Field | Meaning |
|-------|---------|
| `label` | `benign` or `malicious` (after hysteresis) |
| `level` | 2, 3, or 4 when malicious |
| `detection_mode` | `idle`, `spike-L2`, `ml-L4`, `sim-L3`, etc. |
| `per_level` | Raw ensemble probabilities |
| `per_level_adjusted` | Raw minus calibration baseline |
| `suspect_pid` / `suspect_process` | Attribution for unseen scripts |

---

## 7. Graphical User Interface

**Entry:** `gui/main_gui.py` → `gui/fyp_gui.py`

### 7.1 Pages

| Page | Purpose |
|------|---------|
| Dashboard | Status cards, event rate chart, process bar chart, **ML status panel** |
| Alerts | Unified timeline (daemon + ML alerts) |
| Processes | Per-PID keyboard activity from daemon |
| Event Stream | Recent raw events |
| ML Insights | Offline `evaluation.json` + live API scores |
| Configuration | Threshold display, risky process controls |
| AI Assistant | Placeholder |

### 7.2 ML status panel behavior

| State | Title | Details line |
|-------|-------|--------------|
| Calibrating | `Calibrating… (N/20)` | No alerts until baseline locked |
| Clean | `System Clean` | Model scores (informational) |
| Detected | **`Keylogger Detected`** | Level, mode, confidence, L2/L3/L4 scores |

Level is **not** shown in the main title (examiner request); it appears in the detail/mode line.

### 7.3 ML alerts

When ML reports `malicious`, the GUI raises an alert with:

- **Process name + PID** — from API `suspect_process` / `suspect_pid` (unseen script scan), or fallback to daemon flagged process  
- **Message** — level, confidence, detection mode, score breakdown  

### 7.4 Monitors

| Module | Poll target |
|--------|-------------|
| `daemon_monitor.py` | `/tmp/fyp_status.json` |
| `telemetry_ml_monitor.py` | `/tmp/fyp_telemetry_live.csv` → POST `/predict` |
| `lkm_status_monitor.py` | `lsmod`, module health |

---

## 8. How Detection Works Together

### Scenario A: User-space keylogger reading `/dev/input` rapidly

1. **LKM** emits high-frequency events with `rapid_flag=1`  
2. **Daemon** fires **Rapid Typing** and possibly **Unknown Process** alerts with PID/name  
3. **GUI** shows heuristic alerts; ML may also elevate L2 scores if eBPF sees read/openat spikes  

### Scenario B: Unseen L2 script (`unseen2.py` — device scanner)

1. Script scans `/dev/input/*` and procfs → high `kernel_openat_delta` + `kernel_sys_read_delta`  
2. **Collector** writes elevated deltas to CSV  
3. **ML API** triggers `spike-L2` (when `FYP_ML_L2_SPIKES=1`) or `ml-L2`  
4. **GUI** shows **Keylogger Detected**; alert lists `unseen2.py` PID  

### Scenario C: Idle desktop

1. Collector emits stable low syscall deltas  
2. After calibration, L4 raw scores may oscillate (~0.24/0.76) but **adjusted delta stays near zero**  
3. With L4 threshold/delta/streak guards → **`System Clean`**  

---

## 9. Configuration Reference

**Demo profile (default):** `scripts/demo_ml.env` — ML-first, telemetry spikes for L2, no sim scan  
**Sim-assist fallback:** `FYP_DEMO_PROFILE=safe` → `scripts/demo_safe.env`

| Variable | Demo default | Purpose |
|----------|--------------|---------|
| `FYP_ARTIFACT_RUN` | `run_20260531_l2_hybrid` | Model bundle |
| `FYP_ML_CALIBRATE_SAMPLES` | 20 | Baseline rows |
| `FYP_ML_L4_THRESHOLD` | 0.82 | L4 raw score bar |
| `FYP_ML_L4_DELTA` | 0.12 | L4 calibrated lift required |
| `FYP_ML_LEVEL_STREAK` | 2 | Consecutive ML hits |
| `FYP_ML_L2_SPIKES` | 1 | Syscall spike rules for L2 |
| `FYP_ML_L4_SPIKES` | 0 | L4 spikes off (idle stability) |
| `FYP_ML_SIM_DETECT` | 0 | Process-name scan for alerts |

---

## 10. File Map

```
kernel/fyp_kbd.c              LKM source
daemon/fyp_daemon.py          Heuristic engine
gui/fyp_gui.py                Main window + ML panel
gui/telemetry_ml_monitor.py   CSV tail → API client
scripts/collector_live.py     Live eBPF collector
scripts/ml_api.py             FastAPI inference + rules
scripts/train_ml.py           Offline training
scripts/start_demo_stack.sh   Orchestration
dataset/manifest.yaml         Training CSV registry
artifacts/run_*/              Model bundles + evaluation
docs/                         Extended documentation
```

---

## 11. Related Documents

- [`LIVE_DEMO_GUIDE.md`](LIVE_DEMO_GUIDE.md) — examiner demo script  
- [`FYP_JURY_EVALUATION_GUIDE.md`](FYP_JURY_EVALUATION_GUIDE.md) — Q&A for evaluators  
- [`ML_API.md`](ML_API.md) — API contract  
- [`SESSION_RESUME.md`](SESSION_RESUME.md) — quick command reference  
- [`ETHICS.md`](ETHICS.md) — privacy analysis  

---

**End of architecture document**
