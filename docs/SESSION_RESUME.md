# Session Resume — FYP Keylogger Detection

**Last updated:** 2026-05-29  
**Project path:** `/home/fyp/project`  
**Phase:** 3b — Live ML demo integration

Use this file when Cursor chat history is lost after SSH reconnects.

---

## What was done (2026-05-29)

### Offline ML (Phase 3)

- Tiered ML evaluation (A/B/C) in `scripts/train_ml.py`
- `scripts/analyze_dataset.py`, `docs/DATASET_ANALYSIS_LATEST.md`
- `dataset/manifest.yaml` with `capture_groups` and `evaluation_policy`
- Latest training run: **`artifacts/run_20260529_193015`**

### Live demo integration (Phase 3b)

- `scripts/collector_live.py` → `/tmp/fyp_telemetry_live.csv` (0.5s, full L3 eBPF schema)
- `scripts/ml_api.py` — `POST /predict`, per-level ensembles, hysteresis
- `scripts/lkm_watchdog.sh` — auto-reload `fyp_kbd.ko` if detached
- `scripts/start_demo_stack.sh` — one-shot demo startup
- `gui/telemetry_ml_monitor.py` + Dashboard ML status panel in `fyp_gui.py`
- `docs/ML_API.md` — request/response contract

## Key finding (offline)

Perfect AUC on row splits is **structural** (different VMs per class).  
**Report Tier C** (`evaluation.json` → `tiers.C.macro_avg`) for thesis:

| Model | Tier C test_auc |
|-------|-----------------|
| random_forest | 0.927 |
| extra_trees | 0.754 |
| xgboost | 0.990 |

Live demo uses **unseen keylogger simulators** (not in training CSVs) — see `dataset/.../unseen keyloggers/`.

## Quick commands

```bash
cd /home/fyp/project

# Full demo stack (sudo)
sudo scripts/start_demo_stack.sh

# Resume context
cat docs/SESSION_RESUME.md
cat docs/ML_API.md

# ML API only
export FYP_ARTIFACT_RUN=artifacts/run_20260529_193015
python3 scripts/ml_api.py
curl -s http://127.0.0.1:8765/health

# Live collector only (sudo)
sudo python3 scripts/collector_live.py --truncate

# Unseen simulator (demo)
python3 "dataset/3-natasha-mamoon-20260529T122553Z-3-001/3-natasha-mamoon/unseen keyloggers/unseen_level3_agent_collector_queue.py"

# Re-train / verify offline
python scripts/train_ml.py --split-mode all --feature-policy standard
python scripts/verify_artifacts.py
```

## Important paths

| Item | Path |
|------|------|
| Dataset manifest | `dataset/manifest.yaml` |
| Training script | `scripts/train_ml.py` |
| Latest evaluation | `artifacts/run_20260529_193015/evaluation.json` |
| ML API docs | `docs/ML_API.md` |
| Live telemetry CSV | `/tmp/fyp_telemetry_live.csv` |
| ML API | `http://127.0.0.1:8765/predict` |
| LKM watchdog status | `/tmp/fyp_lkm_status.json` |
| Unseen simulators | `dataset/.../unseen keyloggers/*.py` |
| Local status (gitignored) | `current.md` |

## Next steps (optional)

- Tune `FYP_ML_THRESHOLD` on live benign + unseen scripts before examiner demo
- Wire ML Insights page to show `per_level` scores history
- Capture unseen-script CSVs for offline Tier D evaluation

## System versions

Kernel v0.6 | Daemon v0.2 | GUI v3.3
