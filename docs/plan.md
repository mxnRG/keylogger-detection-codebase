# Project Plan Log

## 2026-05-23 - ML Plan Documentation and Tracking

Goal
- Document the ML plan for L1-L5 telemetry and establish project plan/progress logs.

Planned Actions
- Create docs/ML_plan.md with detailed ML pipeline plan.
- Create docs/progress.md with a dated progress log.
- Create docs/plan.md and append this plan section.

Status
- Completed.

Next Checks
- Re-capture datasets with varied benign/malicious workflows to reduce deterministic patterns.
- Add session_id and split by session to validate generalization.

Updates
- Switched training to L2-only for current evaluation.

Notes
- L2-only metrics remain perfect after leakage-safe drops, indicating deterministic separation.

Next Checks
- Verify capture methodology differences between benign/malicious runs (background load, scripts, fixed patterns).
- Add true session IDs and split by session; avoid row-level splits.

Next Checks
- Investigate label leakage or deterministic data generation artifacts causing perfect separation.
- Validate with truly independent capture sessions or synthetic noise injection.

Notes
- Level1 benign has constant keyboard features and a label-matching flag from keyboard_events.
- Windows L1 shows a label-matching flag on zombie_processes; exclude from training.

Updates
- Added leakage-safe feature removal (constants + label-matching + forced drops) and per-file feature dive reports.

Status
- Completed.

## 2026-05-24 - L1/L2 Dataset Deep Dive

Goal
- Analyze L1/L2 benign and malicious datasets for ML readiness, feature-set alignment, and class balance.

Planned Actions
- Compute dataset sizes, label counts, missingness, and basic numeric summaries.
- Compare schemas across L1 vs L2 and Linux vs Windows.
- Flag data quality issues that may affect training.

Status
- Completed.

## 2026-05-24 - Benign vs Malicious Feature Shifts

Goal
- Quantify feature shifts and variance differences between benign and malicious telemetry.

Planned Actions
- Compute effect sizes (Cohen's d) for numeric features.
- Compare variance ratios to highlight unstable or highly variable features.

Status
- Completed.

## 2026-05-24 - Dataset Quality and Analysis Report

Goal
- Produce a shareable markdown report describing dataset quality, schema alignment, and ML readiness.

Planned Actions
- Summarize dataset sizes, label balance, schema drift, and data quality issues.
- Document feature shift findings and ML readiness verdict.

Status
- Completed.

## 2026-05-24 - Clean, Validate, and Train (Linux Only)

Goal
- Clean datasets and enforce validation prior to training.
- Train Linux-only models with curated feature set and per-level ensemble.

Planned Actions
- Add cleaning (NUL stripping, malformed row handling) and dataset quality reporting.
- Enforce Linux-only ingestion and feature whitelist (core + context).
- Train per level with Random Forest, Extra Trees, and XGBoost; save artifacts and ensemble manifest.

Status
- Completed.

## 2026-05-24 - Execute Training Run

Goal
- Install dependencies and execute the updated Linux-only training run.

Planned Actions
- Install Python dependencies (including XGBoost).
- Run training to generate metrics and plots under /artifacts.

Status
- Completed.

## 2026-05-24 - Metrics Review and Leakage Check

Goal
- Review model metrics/quality reports and assess potential leakage or overly easy splits.

Planned Actions
- Inspect metrics and validate that splits are representative for L1/L2.
- Add safeguards if results appear too perfect (e.g., session-aware splits).

Status
- Completed.

Next Checks
- Drop single-feature separators for L2 and re-evaluate.
- Add a harder split (e.g., time/block split) if session IDs are unavailable.

Updates
- Dropped L2 separator features and added block-based 80/20 splits with stratified fallback.

Status
- Completed.

Notes
- L1 duplicates and train/test overlap require deduping before split.
- L2 has single-feature thresholds that perfectly separate classes; verify data generation and consider feature pruning or stronger validation split.

Updates
- Implemented per-level deduplication and 80/20 split for validation/testing.

## 2026-05-29 - Realistic ML on Fixed Telemetry Dataset

Goal
- Use existing L2-L4 eBPF CSVs without re-collection; avoid claiming perfect AUC from row splits.

Planned Actions
- Add tiered evaluation (A row split, B cross-level, C behavioral cross-level).
- Add analyze_dataset.py, evaluation.json, SESSION_RESUME.md for SSH continuity.
- Update manifest with capture_groups; ingest session_id from source_file.

Status
- Completed.

Results (run_20260529_193015)
- Tier A/B: test_auc ~1.0 (optimistic / generalizes across levels).
- Tier C: random_forest 0.927, extra_trees 0.754, xgboost 0.990 — cite for thesis.

Next Checks
- Optional GUI ML Insights wired to evaluation.json.
- Unseen keylogger script captures if VM access allows one run.
