# Live Demo Guide — Examiner Presentation

**Goal:** Demonstrate a **clean idle system** that reliably shows **Keylogger Detected** when an **unseen** script runs, using **ML telemetry** (not pre-scripted GUI states).

**Last updated:** June 2026 (includes L4 idle false-positive fix)

---

## 1. Prerequisites

### 1.1 System

- Ubuntu 22.04/24.04 LTS VM (tested: Linux 5.15+)  
- **Root/sudo** for kernel module + eBPF collector  
- Desktop session (GUI display — not SSH-only for full LKM demo)  
- ~4 GB RAM recommended  

### 1.2 One-time setup

```bash
cd /home/fyp/project

# Python dependencies
pip3 install -r requirements.txt

# System packages
sudo apt install build-essential linux-headers-$(uname -r) \
    python3-bcc libxcb-cursor0

# Build kernel module
cd kernel && make && cd ..
```

### 1.3 Verify artifact bundle

```bash
ls artifacts/run_20260531_l2_hybrid/ensemble_manifest.json
```

---

## 2. Start the Demo Stack

### 2.1 Always restart after code changes

```bash
cd /home/fyp/project
sudo scripts/stop_demo_stack.sh
sudo scripts/run_demo_verbose.sh
```

`run_demo_verbose.sh`:

- Starts all 6 services (LKM, watchdog, daemon, ML API, collector, GUI)  
- Tails logs from `/tmp/fyp-demo/`  
- Runs smoke test after ~12 s  

**Leave this terminal open** during presentation (logs prove detection to jury).

### 2.2 Background start (alternative)

```bash
sudo scripts/start_demo_stack.sh
# tail logs manually:
tail -f /tmp/fyp-demo/fyp_ml_decisions.log
```

---

## 3. Calibration & Idle Behavior

### 3.1 Wait period

After start, wait **15–20 seconds** without running any unseen scripts.

Watch log for:

```
Baseline calibrated (20 rows) | L2=... L3=... L4=...
```

### 3.2 Expected idle GUI state

| Element | Expected |
|---------|----------|
| ML panel title | **System Clean** (green) |
| Detail line | Model scores e.g. `L2:0.05, L3:0.27, L4:0.24` |
| Daemon alerts | None (unless typing rapidly from unknown process) |
| Kernel indicator | Active |

### 3.3 If idle shows "Keylogger Detected"

**Do not proceed with demo — fix first.**

1. Confirm demo profile:

```bash
curl -s http://127.0.0.1:8765/health | python3 -m json.tool
```

Expect (ML-first profile):

```json
"sim_detect": false,
"ignore_levels": [],
"l4_threshold": 0.82,
"ml_level_streak": 2
```

2. Restart stack:

```bash
sudo scripts/stop_demo_stack.sh && sudo scripts/run_demo_verbose.sh
```

3. Check decisions log for spurious `ml-L4`:

```bash
grep MALICIOUS /tmp/fyp-demo/fyp_ml_decisions.log | tail -5
```

If `mode=ml-L4` with `adj L4=+0.00x` at idle → outdated API; ensure latest `scripts/ml_api.py` and `demo_ml.env`.

**Root cause (documented):** L4 ensemble bimodal idle scores; fixed via L4 threshold 0.82 + delta 0.12 + 2-tick streak.

---

## 4. Unseen Keylogger Scripts

**Location:**

```
/home/fyp/project/dataset/3-natasha-mamoon-20260529T122553Z-3-001/3-natasha-mamoon/unseen keyloggers/
```

These scripts are **safe simulators** — they mimic behavioral patterns without exfiltrating real keystrokes.

### 4.1 Recommended demo scripts

| Script | Level | Behavior | Expected detection |
|--------|-------|----------|-------------------|
| `unseen2.py` | L2 | Scans `/dev/input/*`, procfs | `spike-L2` or `ml-L2` |
| `unseen2.1.py` | L2 | Variant device scanner | Same |
| `unseen_level3_agent_collector_queue.py` | L3 | Agent/queue pattern | `ml-L3` (may need longer run) |
| `unseen_level4_syscall_pressure_simulator.py` | L4 | Syscall read/write/exec pressure | `spike-L2` / elevated ML scores |

### 4.2 Primary demo command (L2 — most reliable)

Open a **second terminal** (normal user, not root):

```bash
cd "/home/fyp/project/dataset/3-natasha-mamoon-20260529T122553Z-3-001/3-natasha-mamoon/unseen keyloggers"
python3 unseen2.py
```

### 4.3 L4 demo command (optional)

```bash
python3 unseen_level4_syscall_pressure_simulator.py
```

Runs ~30–60 s for stable telemetry elevation.

---

## 5. Expected Detection Response

### 5.1 GUI (within 1–5 seconds)

| Element | Expected |
|---------|----------|
| ML panel title | **Keylogger Detected** (red) — **no level in title** |
| Mode/detail | `Detection: spike-L2 \| Level 2` (or similar) |
| Scores | Elevated L2/L3/L4 probabilities |
| Alerts tab | New row: **`unseen2.py` (PID)** + ML message |
| Tray icon | Error/red state |

### 5.2 Logs

`fyp_ml_decisions.log`:

```
MALICIOUS | mode=spike-L2 level=2 conf=...
ALERT | mode=spike-L2 level=2 conf=...
```

`fyp_gui.log`:

```
ML alert: [MEDIUM] unseen2.py (PID xxxxx) - ML telemetry detection: Level 2 ...
```

### 5.3 Stop script → return to clean

1. `Ctrl+C` the unseen script  
2. Wait **~10–15 s** (benign hysteresis: 3 ticks × 0.5 s polling)  
3. GUI returns to **System Clean**

---

## 6. Demo Profiles

### 6.1 ML-first (default — recommended for thesis)

Uses `scripts/demo_ml.env`:

- Detection from **eBPF telemetry + ML ensembles**  
- L2 syscall spikes **on**  
- L4 spikes **off**  
- Sim process scan **off** (attribution still via `_find_suspect_process`)  

```bash
sudo scripts/run_demo_verbose.sh
```

### 6.2 Sim-assist fallback

If ML path fails on jury laptop:

```bash
FYP_DEMO_PROFILE=safe sudo scripts/run_demo_verbose.sh
```

Uses `demo_safe.env`: process scan for unseen scripts, L2 ignored for ML alerts, L4 spikes gated by sim.

---

## 7. Smoke Test (pre-presentation)

Run with stack up:

```bash
bash scripts/demo_smoke_test.sh
```

Validates:

- API reachable  
- Correct artifact run  
- 10 benign CSV rows → all `label=benign`  
- High openat/read injection → still benign (when spikes configured correctly)  

---

## 8. Export Evidence

After successful demo:

```bash
bash scripts/export_demo_logs.sh
```

Produces timestamped bundle under `logs/demo_sessions/` for thesis appendix.

---

## 9. Troubleshooting

| Symptom | Fix |
|---------|-----|
| GUI not visible | Check `DISPLAY`, run from desktop session |
| ML Offline | `pgrep -f ml_api.py`; restart stack |
| Telemetry CSV missing | `pgrep -f collector_live.py`; needs sudo |
| Collector BCC error | `sudo apt install python3-bcc` |
| Kernel not loaded | `cd kernel && sudo insmod fyp_kbd.ko` |
| L4 idle false positive | Restart with latest code; verify `/health` l4_threshold=0.82 |
| No detection on script | Wait longer; try `unseen2.py`; check collector log for deltas |
| Alert PID shows `unknown` | Script may have exited; run script during detection window |

---

## 10. Presentation Script (talk track)

> "I'll start the full detection stack — kernel module, daemon, live eBPF collector, ML API, and GUI."

> "The system calibrates on the first twenty telemetry samples. While idle, you should see **System Clean**. Notice we do not capture keystroke content — only behavioral metadata and syscall rates."

> "I'll run an **unseen** Level 2 keylogger simulator that was **not used in training**. It scans input devices like a real hook-based logger."

> "Within a few seconds, ML telemetry detects syscall spikes. The dashboard shows **Keylogger Detected**. The Alerts tab names the **process and PID**, same as heuristic alerts."

> "When I stop the script, hysteresis clears the alert and the system returns to clean."

---

## 11. Environment Variables (quick reference)

| Variable | Default (demo_ml) | Purpose |
|----------|-------------------|---------|
| `FYP_ARTIFACT_RUN` | `run_20260531_l2_hybrid` | Models |
| `FYP_ML_CALIBRATE_SAMPLES` | 20 | Idle baseline rows |
| `FYP_ML_L2_SPIKES` | 1 | L2 openat+read detection |
| `FYP_ML_L4_SPIKES` | 0 | Prevent idle L4 spikes |
| `FYP_ML_L4_THRESHOLD` | 0.82 | L4 ML raw bar |
| `FYP_ML_L4_DELTA` | 0.12 | L4 calibrated lift |
| `FYP_ML_LEVEL_STREAK` | 2 | Consecutive ML hits |
| `FYP_DEMO_PROFILE` | `ml` | Set `safe` for sim-assist |

---

## 12. Related Documents

- [`ARCHITECTURE_AND_DETECTION.md`](ARCHITECTURE_AND_DETECTION.md) — full technical depth  
- [`FYP_JURY_EVALUATION_GUIDE.md`](FYP_JURY_EVALUATION_GUIDE.md) — examiner Q&A  
- [`SESSION_RESUME.md`](SESSION_RESUME.md) — command cheat sheet  
- [`ML_API.md`](ML_API.md) — API fields  

---

**End of live demo guide**
