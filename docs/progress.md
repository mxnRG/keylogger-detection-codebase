# Progress Log

## 2026-05-29 (live ML demo integration)
- Added `scripts/collector_live.py` → `/tmp/fyp_telemetry_live.csv` (0.5s, full L3 eBPF schema).
- Added `scripts/ml_api.py` (FastAPI `POST /predict`, per-level ensemble, threshold hysteresis).
- Added `scripts/lkm_watchdog.sh` (auto-reload `fyp_kbd.ko` if detached) and `/tmp/fyp_lkm_status.json`.
- Added `scripts/start_demo_stack.sh` for one-command demo startup.
- Added `gui/telemetry_ml_monitor.py`, `gui/lkm_status_monitor.py`, Dashboard ML panel in `fyp_gui.py`.
- Added `docs/ML_API.md`; updated `QUICKSTART.md`, `SESSION_RESUME.md`, `current.md`.
- Fixed `gui/run_gui.sh` procfs check (`/proc/fyp_detector/stats` for kernel v0.6).

## 2026-05-29
- Implemented tiered ML evaluation (A/B/C) in scripts/train_ml.py with evaluation.json output.
- Added scripts/analyze_dataset.py and docs/DATASET_ANALYSIS_LATEST.md.
- Updated dataset/manifest.yaml with capture_groups and evaluation_policy.
- Added docs/ML_DATASET_REALISTIC_EVAL_PLAN.md and docs/SESSION_RESUME.md for SSH continuity.
- Ran full training: artifacts/run_20260529_193015 — Tier C macro AUC 0.75–0.99 (realistic).
- Updated verify_artifacts.py to validate evaluation.json and tier B metrics.

## 2026-05-23
- Added ML plan documentation file (docs/ML_plan.md).
- Created project tracking files (docs/progress.md, docs/plan.md).

## 2026-05-24
- Analyzed L1/L2 benign and malicious telemetry datasets for size, schema, label balance, and feature variance.
- Identified malformed rows and NUL bytes in L1_malicious.csv; noted schema deltas between L1 and L2 datasets.
- Computed benign vs malicious feature shifts (Cohen's d) and variance ratios to identify strong discriminators.
- Authored dataset quality and analysis report for team sharing.
- Implemented dataset cleaning (NUL stripping, malformed row handling) and quality reporting in training pipeline.
- Enforced Linux-only ingestion, added feature whitelist (core + context), and per-level training with RF/ExtraTrees/XGBoost.
- Added ensemble manifest output and model artifact saving per level.
- Installed ML dependencies including XGBoost for the new ensemble pipeline.
- Ran training successfully and generated artifacts under /artifacts.
- Reviewed run_20260524_180917 metrics and dataset quality report (Linux-only, L1/L2).
- Investigated perfect scores: L1 has high duplicate rows and train/test overlap; L2 shows single-feature separators.
- Updated per-level training to dedupe feature rows and use a single 80/20 split for validation/testing.
- Reran training with deduped 80/20 split and generated new artifacts.
- Reviewed run_20260524_183913 metrics; scores remain perfect after deduping.
- Applied L2 separator feature drops and block-based 80/20 splits for a harder diagnostic run.
- Reran training with the diagnostic split/feature changes and generated new artifacts.
- Reviewed run_20260524_234718 metrics; scores remain perfect even after L2 separator drop and block split.
- Performed full dataset deep dive (schema, missingness, constants, leakage flags) across all CSVs.
- Implemented leakage-safe feature drops and added per-file feature dive reporting.
- Ran leakage-safe training and generated feature_dive.json in artifacts.
- Reviewed feature_dive.json and leakage-safe run_20260525_001445 metrics.
- Updated training pipeline to focus on L2-only runs for current evaluation.
- Ran L2-only training and generated new artifacts.
- Reviewed L2-only run_20260525_001722 metrics (still perfect scores).
- Documented why perfect scores persist and next diagnostic steps.
