# FYP Keylogger Detection System - Current Status

**Date:** May 31, 2026  
**Phase:** 3b — Live ML Demo (tuned L2 + sim assist)  
**Versions:** Kernel v0.6 | Daemon v0.2 | GUI v3.3

---

## Project Summary

Linux keylogger detection via behavioral analysis (no keystroke content). Pipeline: kernel module → daemon heuristics → Qt GUI. Phase 3 adds offline ML on eBPF CSVs; **Phase 3b** adds live ML scoring for examiner demo.

---

## Phase 3b: Live ML — CURRENT (2026-05-31)

### Flow

1. **LKM watchdog** → keeps `fyp_kbd.ko` loaded
2. **Daemon** → keyboard heuristics → `/tmp/fyp_status.json`
3. **collector_live.py** → eBPF → `/tmp/fyp_telemetry_live.csv` (0.5 s)
4. **ml_api.py v2** → calibration, sim detect, L4 spikes → `/predict`
5. **GUI** → polls CSV, calls API, Clean / **Keylogger Detected — Level N**

### Artifact runs

| Run | Use |
|-----|-----|
| `artifacts/run_20260531_l2_hybrid` | **Live demo** (tuned L2 + baseline L3/L4) |
| `artifacts/run_20260531_021332` | L2-only retrain (`l2_behavioral`) |
| `artifacts/run_20260529_193015` | Original baseline |

### Start / stop

```bash
cd /home/fyp/project
sudo scripts/stop_demo_stack.sh          # always restart after code changes
sudo scripts/run_demo_verbose.sh         # start + live logs (recommended)
# or: sudo scripts/start_demo_stack.sh   # background only
```

Full command list: [`docs/SESSION_RESUME.md`](docs/SESSION_RESUME.md)

### Idle behaviour (post-fix)

- Wait ~15 s after start for calibration.
- Dashboard should show **System Clean** at idle.
- **L4 idle FP fix (2026-06-01):** L4 threshold 0.82 + delta 0.12 + 2-tick ML streak; hold disabled for non-sim.
- GUI shows **Keylogger Detected** (level in details only); ML alerts include suspect PID/process.

### Examiner demo

1. Confirm idle clean after calibration.
2. Run unseen L4 → red + `sim-L4` / `spike-L4`.
3. Run unseen L3 → `sim-L3`.
4. Run unseen L2 (`unseen2.py`) → `sim-L2`.
5. Export logs: `bash scripts/export_demo_logs.sh`

Unseen scripts: `dataset/.../unseen keyloggers/`

### Key env vars

| Variable | Default |
|----------|---------|
| `FYP_ARTIFACT_RUN` | `artifacts/run_20260531_l2_hybrid` |
| `FYP_ML_IGNORE_LEVELS` | `2` |
| `FYP_DEMO_LOG_DIR` | `/tmp/fyp-demo` |
| `FYP_ML_L3_ROLLING` | `0` |
| `FYP_ML_SIM_DETECT` | `1` |

See [`docs/SESSION_RESUME.md`](docs/SESSION_RESUME.md) for full table.

---

## Phase 3: ML Evaluation (offline)

- **~93k rows** — `dataset/manifest.yaml`
- Tier C macro AUC 0.75–0.99 — `artifacts/run_20260529_193015/evaluation.json`
- L2 tuned run: `artifacts/run_20260531_021332`

---

## Phase 2: Detection Pipeline — COMPLETE

Kernel v0.6, Daemon v0.2, GUI v3.3

---

## Documentation map

| Doc | Content |
|-----|---------|
| [`docs/ARCHITECTURE_AND_DETECTION.md`](docs/ARCHITECTURE_AND_DETECTION.md) | Full architecture + detection pipeline |
| [`docs/FYP_JURY_EVALUATION_GUIDE.md`](docs/FYP_JURY_EVALUATION_GUIDE.md) | Examiner Q&A |
| [`docs/LIVE_DEMO_GUIDE.md`](docs/LIVE_DEMO_GUIDE.md) | Demo script + troubleshooting |

---

**Last Updated:** May 31, 2026  
**Status:** Live demo ready — use `run_demo_verbose.sh`, sim assist for L2/L3, L4 spikes + sim for L4
