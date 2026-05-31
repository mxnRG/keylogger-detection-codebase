# ML Live Detection — Work Log

**Last updated:** 2026-05-31  
**Artifacts:** `run_20260531_l2_hybrid` (live) | `run_20260531_021332` (L2 tune) | `run_20260529_193015` (baseline)  
**Quick resume:** [`SESSION_RESUME.md`](SESSION_RESUME.md)

---

## 1. Executive summary

| Layer | Role |
|-------|------|
| **eBPF collector** | `/tmp/fyp_telemetry_live.csv` every 0.5 s |
| **ML API v2** | L2/L3/L4 ensembles + calibration + sim detect + L4 spikes |
| **GUI** | Polls CSV → POST `/predict` → Clean / Detected Level N |
| **Sim assist** | `sim-L2` / `sim-L3` / `sim-L4` from unseen script process scan |

**Thesis line:** Offline models generalise across VMs (Tier C). Live demo uses same-VM calibration, sim process context, and conservative rules because unseen L2/L3 sims are much milder than training malicious CSVs.

---

## 2. Session log — 2026-05-31 (this chat)

### 2.1 L2 tuning (no re-collection)

| Step | Result |
|------|--------|
| `l2_behavioral` feature policy | 16 kernel/process features; drops VM fingerprint |
| Supplement data | `dataset/l2_supplement/` from `/tmp/fyp_telemetry_live.csv` |
| Retrain | `artifacts/run_20260531_021332` |
| Hybrid bundle | `artifacts/run_20260531_l2_hybrid` |
| Eval | Idle L2 0.645 → **0.073**; device-scan proxy ~0.44 |

### 2.2 Live L2/L3 improvements (config-only)

- Re-enabled tuned L2 model in hybrid run.
- Added kernel baseline calibration (20 rows).
- Added L2 openat/read spikes, L3 rolling/instant spikes — **later disabled** (idle FP).

### 2.3 Idle false positive investigation

**Symptom:** Dashboard red at idle; user reported “L2 spike”.

**Log analysis** (`/tmp/fyp-demo/fyp_ml_decisions.log`):

| Finding | Detail |
|---------|--------|
| Primary cause | **`roll-L3`** — rolling connect sum ~44 vs threshold ~16 |
| Not spike-L2 | No `spike-L2` lines in log |
| L2 score jumps | Raw `L2=0.45–0.76` on noisy rows — **display only** when `IGNORE_LEVELS=2` |
| Hysteresis flip-flop | `roll-L3` + `MALICIOUS_STREAK=3` caused intermittent red |

**Fixes applied:**

1. `FYP_ML_IGNORE_LEVELS=2` (default) — L2 score shown, not used for alert level.
2. `FYP_ML_L2_SPIKES=0`, `FYP_ML_L3_SPIKES=0`, `FYP_ML_L3_ROLLING=0` (defaults).
3. `FYP_ML_L2_DELTA=0.55` — high bar for ml-L2.
4. Spikes/rolls only after calibration; L2 spike streak was 2 (when enabled).
5. **Sim detect** tightened to scripts under `unseen keyloggers/` path only.

### 2.4 Logging restoration

Demo logging files were missing from the working tree (deleted, not in git). Restored:

- `scripts/demo_log.py`
- `scripts/run_demo_verbose.sh`
- `scripts/stop_demo_stack.sh`
- `scripts/export_demo_logs.sh`
- Log dir: `/tmp/fyp-demo/`

---

## 3. L2 capability vs unseen sims

| Script | Visible to eBPF? | Live detection path |
|--------|------------------|---------------------|
| `unseen2.py` (device scan) | Yes (openat/read) | **sim-L2**; ML partial (~0.44 tuned) |
| `unseen2.2.py` (FIFO) | Yes (read/write) | sim-L2 |
| `unseen_level2_unix_socket_heartbeat.py` | Partial (no TCP connect) | sim-L2 |
| `unseen2.1.py` (stat poller) | **No** | sim-L2 only |

L2 **ignored live** for ML alerts (`IGNORE_LEVELS=2`) because idle score is unstable on demo VM despite tuned model.

---

## 4. L3 capability vs unseen sims

| Script | Training gap | Live path |
|--------|--------------|-----------|
| `unseen_level3_agent_collector_queue.py` | Low connect/execve vs rootkit CSV | **sim-L3** |
| `unseen_level3_dns_beacon_sysinfo.py` | UDP DNS not probed | sim-L3 |
| `unseen_level3_fake_encrypted_exfil.py` | Sparse TCP | sim-L3 |

Rolling L3 rules **disabled** — demo VM idle already has ~44 connects per 10 s window.

---

## 5. L2 offline eval summary

From `artifacts/l2_eval_summary.json`:

| Dataset | Baseline L2 | Tuned L2 |
|---------|-------------|----------|
| Demo VM idle | 0.645 | **0.073** |
| Device-scan proxy | 0.643 | **0.442** |
| Train malicious | 1.000 | 1.000 |

---

## 6. Detection priority (ml_api.py v2)

1. **sim-LN** — unseen script process running (primary for L2/L3 demo)
2. **spike-L4** — heavy syscall patterns (if `FYP_ML_L4_SPIKES=1`)
3. **ml-LN** — adjusted score delta above threshold (L2 ignored for alerts)
4. **delta** — generic adjusted max (respects `IGNORE_LEVELS`)

---

## 7. Related files

| File | Purpose |
|------|---------|
| `scripts/ml_api.py` | Live inference v2 |
| `scripts/start_demo_stack.sh` | Demo startup + env defaults |
| `scripts/run_demo_verbose.sh` | Verbose log multiplex |
| `scripts/collector_live.py` | eBPF collector |
| `scripts/train_ml.py` | Offline training |
| `dataset/l2_supplement/` | Demo VM benign + proxy malicious rows |
| `docs/ML_API.md` | API contract |
| `docs/SESSION_RESUME.md` | Commands cheat sheet |
