# Dataset Quality and Analysis Report

Date: 2026-05-24
Scope: L1/L2 telemetry datasets (Linux + Windows)

## Executive Summary
The L1/L2 telemetry datasets contain both benign and malicious samples and show strong, behaviorally meaningful separation across several features (process counts, disk usage, keyboard ratios, and kernel deltas). This is suitable for initial ML training. However, there are data quality issues (malformed rows in L1_malicious.csv and schema drift between L1 and L2) that must be addressed before final model training and evaluation. Overall status: **partially ML-ready**.

## Datasets Reviewed
- Linux benign: level1.csv, level2.csv
- Linux malicious: L1_malicious.csv, L2_malicious.csv
- Windows benign: windows_L1.csv

## Dataset Sizes and Label Balance
Linux L1/L2 combined:
- benign: 19,362 rows
- malicious: 27,446 rows

This is a reasonable binary balance, with a moderate malicious skew. This is not disqualifying, but class weights or balanced sampling should be used during training.

## Schema Alignment Findings
- L2 datasets (benign and malicious) include 4 kernel-level delta features that are not present in L1:
  - kernel_context_switches_delta
  - kernel_sys_read_delta
  - kernel_sys_write_delta
  - keyboard_hardware_interrupts
- Windows L1 is missing one Linux feature:
  - background_processes

Implications:
- L1 and L2 must be aligned before training. Missing features should be filled with 0 and tracked as missing-feature metadata.
- Windows data requires alignment (fill missing background_processes or drop this feature uniformly).

## Data Quality Issues
- L1_malicious.csv contains malformed rows and NUL bytes.
  - 839 malformed rows detected (column count mismatch) after stripping NUL bytes.

Implications:
- L1_malicious.csv should be cleaned or re-exported to avoid silent row drops and label skew.
- Any model trained without cleaning risks inconsistent training statistics and reduced reproducibility.

## Feature Shift Analysis (Benign vs Malicious)
The following features show the largest distribution shifts (high effect sizes), making them strong ML signals:
- disk_usage_percent
- background_processes
- active_processes
- process_count
- users_logged_in
- shell_processes
- python_processes
- suspicious_process_names
- keyboard_to_process_ratio
- zombie_processes
- system_uptime_minutes
- keyboard_events
- kernel_context_switches_delta
- total_threads

Variance shifts (malicious variance >> benign) highlight additional signals:
- kernel_sys_read_delta
- kernel_sys_write_delta
- cpu_to_keyboard_ratio
- high_memory_processes
- memory_usage

These results align well with the project goal of behavioral detection without keystroke capture.

## Feature Stability and Low-Variance Signals
Some features appear low-variance and may contribute less in the current environment:
- users_logged_in
- python_processes
- zombie_processes
- high_cpu_processes
- high_memory_processes
- shell_processes

These should not be removed yet, but can be deprioritized in feature selection if needed.

## ML Readiness Verdict
**Partially ML-ready.**

Ready:
- L1/L2 Linux datasets provide both benign and malicious data.
- Strong, behaviorally relevant feature shifts are present.
- Label balance is acceptable for baseline modeling.

Not Ready:
- L1_malicious.csv requires cleaning due to malformed rows and NUL bytes.
- L1/L2 schema drift requires alignment.
- Windows L1 requires alignment before being merged into a single model.

## Recommendations Before Training
1. Clean L1_malicious.csv (remove malformed rows, strip NUL bytes, re-export).
2. Align schema across L1/L2 and Linux/Windows (fill missing features with 0).
3. Add validation checks to block training if single-class or malformed data is detected.
4. Keep kernel delta features and keyboard ratios; they show strong separation.
5. Use class weights or balanced sampling to address the malicious skew.

## Next Steps
- Implement a data-cleaning and schema-alignment step before training.
- Add a dataset validation report in /artifacts for each training run.
- Recompute the report after cleaning to confirm improved data quality.
