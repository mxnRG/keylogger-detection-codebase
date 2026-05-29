# Dataset Analysis (Latest)

Generated from manifest at `dataset/manifest.yaml`.

## Summary

- Training levels: [2, 3, 4]
- Archive root: `3-natasha-mamoon-20260529T122553Z-3-001/3-natasha-mamoon`
- Files per level: 1 benign + 1 malicious (no leave-one-file-out with both classes in train and test)

## Per-Level Feature Separation

### Level 2

- Benign: `level2.csv` (8,202 rows) — capture group `unknown`
- Malicious: `level2_ebpf_keylogger.csv` (16,845 rows) — capture group `unknown`
- Perfect separators: ['active_processes', 'background_processes', 'cpu_threads', 'disk_usage_percent', 'keyboard_events', 'process_count', 'swap_memory', 'total_open_files']

| Feature | Benign range | Malicious range | Perfect separator |
|---------|--------------|-----------------|-------------------|
| `active_processes` | 258–318 | 186–230 | yes |
| `background_processes` | 247–307 | 177–220 | yes |
| `cpu_threads` | 4–4 | 3–3 | yes |
| `cpu_to_keyboard_ratio` | 0–0.3665 | 0–0.4954 | no |
| `cpu_usage` | 0–100 | 0–100 | no |
| `disk_usage_percent` | 77.8–78.4 | 83.8–85.3 | yes |
| `high_cpu_processes` | 0–10 | 0–10 | no |
| `high_memory_processes` | 0–6 | 0–11 | no |
| `hour` | 0–23 | 11–14 | no |
| `kernel_context_switches_delta` | 0–5.429e+04 | 0–7.984e+04 | no |
| `kernel_sys_read_delta` | 8–2.709e+04 | 42–5.287e+05 | no |
| `kernel_sys_write_delta` | 0–3.952e+05 | 0–1.213e+06 | no |
| `keyboard_events` | 258–318 | 186–233 | yes |
| `keyboard_hardware_interrupts` | 0–33 | 0–44 | no |
| `keyboard_to_process_ratio` | 1–1 | 1–1 | no |
| `memory_usage` | 27.9–98.9 | 29.2–89.4 | no |
| `minute` | 0–59 | 0–59 | no |
| `network_connections` | 18–337 | 3–152 | no |
| `process_count` | 258–318 | 186–233 | yes |
| `python_processes` | 1–1 | 1–2 | no |
| `second` | 0–59 | 0–59 | no |
| `shell_processes` | 8–11 | 2–11 | no |
| `suspicious_process_names` | 5–5 | 5–6 | no |
| `swap_memory` | 64.1–100 | 0–51.6 | yes |
| `system_uptime_minutes` | 66.03–166.6 | 13.91–216.5 | no |
| `thread_to_process_ratio` | 2.54–6.454 | 2.264–4.338 | no |
| `total_connections` | 18–337 | 3–152 | no |
| `total_open_files` | 258–318 | 186–233 | yes |
| `total_threads` | 665–2036 | 435–989 | no |
| `users_logged_in` | 2–2 | 1–5 | no |
| `zombie_processes` | 0–42 | 0–5 | no |

### Level 3

- Benign: `level3_benign_ebpf.csv` (12,874 rows) — capture group `unknown`
- Malicious: `level3_ebpf_keylogger_v2.csv` (29,012 rows) — capture group `unknown`
- Perfect separators: ['cpu_threads', 'disk_usage_percent', 'hour', 'python_processes']

| Feature | Benign range | Malicious range | Perfect separator |
|---------|--------------|-----------------|-------------------|
| `active_processes` | 221–242 | 196–246 | no |
| `background_processes` | 214–235 | 187–237 | no |
| `cpu_threads` | 4–4 | 3–3 | yes |
| `cpu_to_keyboard_ratio` | 0–0.3888 | 0–0.4652 | no |
| `cpu_usage` | 0–91.4 | 0–100 | no |
| `disk_usage_percent` | 50.1–50.3 | 84.4–84.6 | yes |
| `high_cpu_processes` | 0–6 | 0–8 | no |
| `high_memory_processes` | 1–4 | 2–12 | no |
| `hour` | 21–23 | 12–15 | yes |
| `kernel_connect_delta` | 0–192 | 0–118 | no |
| `kernel_context_switches_delta` | 2–2.419e+04 | 4–2.19e+04 | no |
| `kernel_execve_delta` | 0–330 | 2–178 | no |
| `kernel_openat_delta` | 6–8756 | 76–2.273e+04 | no |
| `kernel_sys_read_delta` | 27–2.046e+04 | 143–6.627e+05 | no |
| `kernel_sys_write_delta` | 5–3.431e+06 | 10–3.13e+06 | no |
| `keyboard_events` | 221–242 | 196–250 | no |
| `keyboard_hardware_interrupts` | 0–11 | 0–30 | no |
| `keyboard_to_process_ratio` | 1–1 | 1–1 | no |
| `memory_usage` | 22.5–49.8 | 40.1–81.4 | no |
| `minute` | 0–59 | 0–59 | no |
| `network_connections` | 10–66 | 3–81 | no |
| `process_count` | 221–242 | 196–250 | no |
| `python_processes` | 1–1 | 2–7 | yes |
| `second` | 0–59 | 0–59 | no |
| `shell_processes` | 2–6 | 2–18 | no |
| `suspicious_process_names` | 5–5 | 5–5 | no |
| `swap_memory` | 0–0 | 0–58.2 | no |
| `system_uptime_minutes` | 50.55–198.7 | 4.2–183.2 | no |
| `thread_to_process_ratio` | 2.206–3.616 | 2.353–3.929 | no |
| `total_connections` | 10–66 | 3–81 | no |
| `total_open_files` | 221–242 | 196–250 | no |
| `total_threads` | 497–875 | 473–826 | no |
| `users_logged_in` | 2–2 | 1–3 | no |
| `zombie_processes` | 0–2 | 0–4 | no |

### Level 4

- Benign: `level4_benign_ebpf.csv` (12,466 rows) — capture group `unknown`
- Malicious: `level4_ebpf_kernel_behavior.csv` (14,478 rows) — capture group `unknown`
- Perfect separators: ['cpu_threads', 'disk_usage_percent']

| Feature | Benign range | Malicious range | Perfect separator |
|---------|--------------|-----------------|-------------------|
| `active_processes` | 215–257 | 186–235 | no |
| `background_processes` | 209–250 | 177–224 | no |
| `cpu_threads` | 4–4 | 3–3 | yes |
| `cpu_to_keyboard_ratio` | 0–0.4203 | 0–0.5102 | no |
| `cpu_usage` | 0–97.5 | 0–100 | no |
| `disk_usage_percent` | 51.3–59.3 | 84.6–86.2 | yes |
| `high_cpu_processes` | 0–9 | 0–9 | no |
| `high_memory_processes` | 1–5 | 0–11 | no |
| `hour` | 16–22 | 6–17 | no |
| `kernel_connect_delta` | 0–365 | 0–214 | no |
| `kernel_context_switches_delta` | 2–3.56e+04 | 0–2.441e+04 | no |
| `kernel_execve_delta` | 0–111 | 0–98 | no |
| `kernel_openat_delta` | 21–3.734e+04 | 10–6624 | no |
| `kernel_sys_read_delta` | 40–4.023e+04 | 211–8.317e+05 | no |
| `kernel_sys_write_delta` | 5–2.988e+06 | 10–1.046e+07 | no |
| `keyboard_events` | 215–257 | 186–235 | no |
| `keyboard_hardware_interrupts` | 0–30 | 0–54 | no |
| `keyboard_to_process_ratio` | 1–1 | 1–1 | no |
| `memory_usage` | 20.2–57.8 | 31–86.9 | no |
| `minute` | 0–59 | 0–59 | no |
| `network_connections` | 10–253 | 3–230 | no |
| `process_count` | 215–257 | 186–235 | no |
| `python_processes` | 1–1 | 1–1 | no |
| `second` | 0–59 | 0–59 | no |
| `shell_processes` | 2–4 | 3–16 | no |
| `suspicious_process_names` | 5–6 | 5–5 | no |
| `swap_memory` | 0–0 | 0–70.9 | no |
| `system_uptime_minutes` | 0.9–89.3 | 27.24–171.9 | no |
| `thread_to_process_ratio` | 2.096–4.812 | 2.204–4.809 | no |
| `total_connections` | 10–253 | 3–230 | no |
| `total_open_files` | 215–257 | 186–235 | no |
| `total_threads` | 476–1229 | 432–1111 | no |
| `users_logged_in` | 2–2 | 1–2 | no |
| `zombie_processes` | 0–2 | 0–12 | no |

## Split Feasibility

| Strategy | Feasible? | Notes |
|----------|-----------|-------|
| Row-level stratified split | yes | Upper-bound metric; same capture files in train and test → optimistic AUC |
| Leave-one-file-out | no | One benign + one malicious file per level; holdout leaves single class |
| Cross-level holdout | yes | **Primary thesis metric** — train 2 levels, test held-out level |
| Session-aware group split | limited | Only 2 `split_group` values per level → falls back to row split |

## Recommended Feature Drops

### Environment fingerprint blocklist (always exclude for tier C)

```
swap_memory, disk_usage_percent, system_uptime_minutes, process_count, active_processes, background_processes, total_open_files, users_logged_in, keyboard_events, keyboard_to_process_ratio, cpu_threads, hour, minute, second
```

### Per-level perfect separators (also exclude for honest eval)

- **L2:** ['active_processes', 'background_processes', 'cpu_threads', 'disk_usage_percent', 'keyboard_events', 'process_count', 'swap_memory', 'total_open_files']
- **L3:** ['cpu_threads', 'disk_usage_percent', 'hour', 'python_processes']
- **L4:** ['cpu_threads', 'disk_usage_percent']

### Behavioral feature set (tier C training)

```
kernel_context_switches_delta, kernel_sys_read_delta, kernel_sys_write_delta, kernel_openat_delta, kernel_execve_delta, kernel_connect_delta, keyboard_hardware_interrupts, cpu_to_keyboard_ratio, thread_to_process_ratio, network_connections, total_connections, shell_processes, python_processes, suspicious_process_names, high_cpu_processes, high_memory_processes, zombie_processes, cpu_usage, memory_usage, total_threads
```

## Evaluation Tiers

| Tier | Split | Feature policy | Purpose |
|------|-------|----------------|---------|
| A | Per-level row stratified | Standard + leakage drops | In-distribution upper bound |
| B | Cross-level holdout | Standard + leakage drops | **Primary thesis metric** |
| C | Cross-level or per-level | Behavioral-only + env strip | Signal beyond VM fingerprints |

## Commands

```bash
python scripts/analyze_dataset.py --data-dir dataset
python scripts/train_ml.py --split-mode all --feature-policy standard
python scripts/verify_artifacts.py
```
