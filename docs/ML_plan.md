# ML Plan (L1-L5 Telemetry)

Date: 2026-05-23
Owner: FYP Team
Status: Active

## Purpose
Build a reproducible ML pipeline for L1-L5 telemetry datasets (benign and malicious),
where L1 is the weakest environment and L5 is the strongest. The pipeline must be
safe against data leakage, support Linux and Windows telemetry in a single model,
and store all evaluation artifacts under /artifacts.

## Scope
- Data sources: L1-L5 telemetry CSVs (Linux + Windows), plus optional external datasets
  only if their schema is explicitly mapped (not automatic).
- Labels: binary only (benign vs malicious).
- Output: trained baseline models, metrics, and plots stored in /artifacts.

## Dataset Contract
Each telemetry CSV must contain the following required columns:
- label (string): benign or malicious
- timestamp (string, ISO preferred)
- hour, minute, second (int)
- cpu_usage, memory_usage, swap_memory, disk_usage_percent, system_uptime_minutes
- process_count, active_processes, background_processes, high_cpu_processes
- high_memory_processes, python_processes, shell_processes, suspicious_process_names
- zombie_processes
- cpu_threads, total_threads, thread_to_process_ratio
- keyboard_events, keyboard_to_process_ratio, cpu_to_keyboard_ratio
- total_open_files, network_connections, total_connections
- users_logged_in

Required metadata columns (either in file content or added during ingestion):
- level (int): 1-5
- os (string): linux or windows
- scenario_id (string): scenario identifier, same for related sessions
- session_id (string): unique ID per capture session
- source_file (string): original filename

Filename conventions:
- Must include level identifier for automatic splitting (e.g., level1.csv, windows_L3.csv).
- OS can be inferred from filename if not in file content.

## Schema Alignment Rules
- All features are numeric; non-numeric columns are excluded from model features.
- Missing columns for a given OS are filled with 0 and recorded in metadata.
- timestamp is not used directly as a feature; hour/minute/second are used instead.
- All rows missing a recognized label are dropped.

## Data Validation Checklist (Pre-Training)
- Labels contain both classes; warn and abort if only one class.
- Required columns exist; fail fast if any are missing.
- No duplicate rows within the same session_id.
- Report per-feature missingness and outlier counts.
- Confirm level distribution and OS distribution.

## Split Strategy (Leakage-Safe)
- If >= 3 numeric levels are present:
  - Train: lowest levels up to L(n-2)
  - Validation: level L(n-1)
  - Test: highest level L(n)
- Within each split, keep session_id grouping intact (no row-level leakage across splits).
- If fewer than 3 levels are present, fallback to stratified random split with
  fixed seed and session-aware grouping.

## Modeling Strategy
Baseline models (first pass):
- Logistic Regression (with standard scaling)
- Random Forest
- Gradient Boosting

Class imbalance handling:
- Use class_weight=balanced for classifiers that support it.
- Track class distribution in metrics report.

Metrics to report:
- ROC AUC, PR AUC
- Confusion matrix at threshold 0.5
- Optional: precision, recall, F1 by class

## Artifacts Policy
All plots and metrics must be stored under /artifacts per run:
- /artifacts/run_<timestamp>/metrics.json
- /artifacts/run_<timestamp>/<model>/
  - <model>_roc_curve.png
  - <model>_pr_curve.png
  - <model>_confusion_matrix.png

## Future L3-L5 Readiness
- Enforce the dataset contract for all new L3-L5 files.
- Ensure scenario_id and session_id are set so later data can be merged safely.
- Keep the level-based split rule intact to preserve evaluation fairness.

## Implementation Notes
- The current training script lives at scripts/train_ml.py and already follows
  most of this plan; it will be extended to enforce session-aware splitting
  and dataset validation as new data arrives.
- External datasets (e.g., Kaggle) must be mapped explicitly and should not be
  combined with telemetry unless the feature space is aligned.
