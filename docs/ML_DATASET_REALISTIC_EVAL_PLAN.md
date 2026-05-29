# Realistic ML on Fixed Telemetry Dataset

**Date:** 2026-05-29  
**Status:** Active — implemented in `scripts/train_ml.py`  
**Latest run:** `artifacts/run_20260529_193015`

## Problem

Row-level stratified splits on the L2–L4 eBPF dataset produce **AUC ≈ 1.0** because:

1. Only **one benign + one malicious CSV per level** (different VMs/sessions).
2. Environment features (`disk_usage_percent`, `swap_memory`, process counts on L2) are perfect class separators.
3. Kernel delta features also differ strongly between keylogger and benign captures.

We **cannot re-collect data**. This plan makes the existing ~94k rows usable with honest, tiered evaluation.

## Dataset (fixed)

| Level | Benign | Malicious | Rows (approx) |
|-------|--------|-----------|---------------|
| L2 | `Mamoon (ubuntu)/level2 benign/level2.csv` | `Data/Level 2_ Hook trap/level2_ebpf_keylogger.csv` | 8.2k + 16.8k |
| L3 | `haider ubuntu/Level 3/level3_benign_ebpf.csv` | `Data/Level 3_ RootKit/level3_ebpf_keylogger_v2.csv` | 12.9k + 29.0k |
| L4 | `haider ubuntu/Level 4/level4_benign_ebpf.csv` | `Data/Level 4_ kernel Level/level4_ebpf_kernel_behavior.csv` | 12.5k + 14.5k |

Manifest: [`dataset/manifest.yaml`](../dataset/manifest.yaml)  
Analysis report: [`docs/DATASET_ANALYSIS_LATEST.md`](DATASET_ANALYSIS_LATEST.md)

**Do not train on** `Data/combined/all_levels_ebpf_keylogger.csv` (malicious-only).

## Three evaluation tiers

| Tier | Split | Features | Purpose |
|------|-------|----------|---------|
| **A** | Per-level row stratified | Standard + leakage drops | In-distribution **upper bound** |
| **B** | Cross-level holdout (train 2 levels, test 1) | Standard + leakage drops | Generalization across attack levels |
| **C** | Cross-level holdout | Behavioral-only (env fingerprint strip) | **Realistic thesis metric** |

### Latest results (`run_20260529_193015`)

**Tier A (macro avg):** all models `test_auc ≈ 1.0` — optimistic.

**Tier B (macro avg):** RF/ET/XGB `test_auc ≈ 0.9998–1.0` — behavioral signal generalizes across levels; still near-perfect.

**Tier C (macro avg) — cite this for FYP:**

| Model | test_auc | test_ap |
|-------|----------|---------|
| random_forest | 0.927 | 0.967 |
| extra_trees | 0.754 | 0.853 |
| xgboost | 0.990 | 0.995 |

Tier C removes VM fingerprint features and evaluates cross-level — **defensible, non-perfect scores**.

## Commands

```bash
# Analyze dataset (no training)
python scripts/analyze_dataset.py --data-dir dataset

# Full pipeline: tier A + B + C
python scripts/train_ml.py --split-mode all --feature-policy standard

# Cross-level only (faster)
python scripts/train_ml.py --split-mode cross_level --feature-policy standard

# Verify artifacts
python scripts/verify_artifacts.py --run-dir artifacts/run_<timestamp>
```

Outputs per run under `artifacts/run_<timestamp>/`:

- `metrics.json` — per-level tier A details
- `evaluation.json` — tiers A/B/C summary (**primary for reporting**)
- `ensemble_manifest.json` — deployed model paths
- `cross_level_B/`, `cross_level_C/` — fold models and plots

## Feature policies

**Environment fingerprint blocklist** (tier C forced drop):

`swap_memory`, `disk_usage_percent`, `system_uptime_minutes`, `process_count`, `active_processes`, `background_processes`, `total_open_files`, `users_logged_in`, `keyboard_events`, `keyboard_to_process_ratio`, `cpu_threads`, `hour`, `minute`, `second`

**Behavioral features** (tier C allowlist): kernel deltas, keyboard ratios, network counts, process-type counts, `cpu_usage`, `memory_usage`, `total_threads`.

## Thesis wording

1. **Constraint:** Single benign + malicious capture per level; no re-collection.
2. **Confounding:** Row-level metrics are optimistic (tier A).
3. **Primary result:** Tier C cross-level AUC/AP on behavioral features.
4. **Secondary:** Tier B shows patterns generalize across L2–L4 when env features remain.
5. **Limitation:** Unseen keylogger scripts exist without CSV telemetry — future work.

## Implementation files

- [`scripts/train_ml.py`](../scripts/train_ml.py) — training + `evaluation.json`
- [`scripts/analyze_dataset.py`](../scripts/analyze_dataset.py) — dataset report
- [`scripts/verify_artifacts.py`](../scripts/verify_artifacts.py) — artifact checks
- [`docs/ML_plan.md`](ML_plan.md) — original L1–L5 pipeline spec
- [`docs/SESSION_RESUME.md`](SESSION_RESUME.md) — SSH session quick resume
