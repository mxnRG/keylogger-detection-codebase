# Session Resume — FYP Live ML Demo

**Last updated:** 2026-05-31  
**Companion:** [`ml_work.md`](ml_work.md) (detailed work log) | [`ML_API.md`](ML_API.md) (API contract)

Quick reference to restart the demo stack, run unseen simulators, and read logs after a break.

---

## Current state (2026-05-31 session)

| Item | Value |
|------|--------|
| **Live artifact run** | `artifacts/run_20260531_l2_hybrid` (tuned L2 + baseline L3/L4) |
| **L2 offline tune run** | `artifacts/run_20260531_021332` (`l2_behavioral` features) |
| **Baseline offline run** | `artifacts/run_20260529_193015` |
| **ML API** | `scripts/ml_api.py` v2 — calibration, sim detect, L4 spikes |
| **Logs** | `/tmp/fyp-demo/` (not removed — use verbose runner to tail) |
| **L2 live alerts** | **Ignored** (`FYP_ML_IGNORE_LEVELS=2`) — sim-L2 still works |
| **Idle false positive fix** | L2/L3 spike + roll rules **off** by default; roll-L3 was causing idle alerts |

### What this session did

1. **L2 model tuning (no re-collection)** — `l2_behavioral` retrain + demo VM supplement → idle L2 score ~0.07 (was ~0.65).
2. **Hybrid deploy bundle** — `run_20260531_l2_hybrid` = tuned L2 + old L3/L4.
3. **Live API v2** — kernel baseline calibration, sim process scan, level-specific thresholds.
4. **Idle FP debugging** — logs showed `roll-L3` (not L2) firing on normal connect sums (~44/10s); disabled by default.
5. **Restored logging** — `demo_log.py`, `run_demo_verbose.sh`, `stop_demo_stack.sh`, `export_demo_logs.sh`.
6. **Restored demo files** — `ml_api.py`, `collector_live.py`, `fyp_gui.py`, etc. (had been deleted from working tree).

---

## Full commands

### Stop stack (always after code changes)

```bash
cd /home/fyp/project
sudo scripts/stop_demo_stack.sh
```

### Start stack (background)

```bash
cd /home/fyp/project
sudo scripts/start_demo_stack.sh
```

Wait **~15 s** for `Baseline calibrated (20 rows)` in logs.

### Start with live log tail (recommended)

```bash
cd /home/fyp/project
sudo scripts/stop_demo_stack.sh
sudo scripts/run_demo_verbose.sh
```

Ctrl+C stops tail only; stack keeps running.

### Health check

```bash
curl -s http://127.0.0.1:8765/health | python3 -m json.tool
```

Expect: `"run_dir": ".../run_20260531_l2_hybrid"`, `"ignore_levels": [2]`, `"calibrated": true`.

### Watch decisions (why benign/malicious)

```bash
tail -f /tmp/fyp-demo/fyp_ml_decisions.log
```

Idle should be: `BENIGN | mode=idle level=None ...`

### Export shareable logs

```bash
cd /home/fyp/project
bash scripts/export_demo_logs.sh
# → logs/demo_latest.txt
```

### Unseen simulators (separate terminal, **no sudo**)

Base path (quotes required):

```text
/home/fyp/project/dataset/3-natasha-mamoon-20260529T122553Z-3-001/3-natasha-mamoon/unseen keyloggers/
```

**L2 device scan:**
```bash
python3 "/home/fyp/project/dataset/3-natasha-mamoon-20260529T122553Z-3-001/3-natasha-mamoon/unseen keyloggers/unseen2.py"
```

**L2 unix socket:**
```bash
python3 "/home/fyp/project/dataset/3-natasha-mamoon-20260529T122553Z-3-001/3-natasha-mamoon/unseen keyloggers/unseen_level2_unix_socket_heartbeat.py"
```

**L3 agent:**
```bash
python3 "/home/fyp/project/dataset/3-natasha-mamoon-20260529T122553Z-3-001/3-natasha-mamoon/unseen keyloggers/unseen_level3_agent_collector_queue.py"
```

**L3 DNS beacon:**
```bash
python3 "/home/fyp/project/dataset/3-natasha-mamoon-20260529T122553Z-3-001/3-natasha-mamoon/unseen keyloggers/unseen_level3_dns_beacon_sysinfo.py"
```

**L4 syscall pressure:**
```bash
python3 "/home/fyp/project/dataset/3-natasha-mamoon-20260529T122553Z-3-001/3-natasha-mamoon/unseen keyloggers/unseen_level4_syscall_pressure_simulator.py"
```

Expect log lines: `mode=sim-L2` / `sim-L3` / `sim-L4`.

---

## Log files

| File | Purpose |
|------|---------|
| `/tmp/fyp-demo/fyp_ml_decisions.log` | Per-tick ML decision (mode, raw/adj scores) |
| `/tmp/fyp-demo/fyp_ml_api.log` | API startup, STATE CHANGE lines |
| `/tmp/fyp-demo/fyp_collector_live.log` | eBPF collector |
| `/tmp/fyp-demo/fyp_daemon.log` | Daemon |
| `/tmp/fyp-demo/fyp_gui.log` | GUI |
| `logs/demo_latest.txt` | Exported snapshot |
| `logs/demo_sessions/demo_verbose_*.txt` | Timestamped verbose sessions |

---

## Live ML env vars (defaults in `start_demo_stack.sh`)

| Variable | Default | Purpose |
|----------|---------|---------|
| `FYP_ARTIFACT_RUN` | `artifacts/run_20260531_l2_hybrid` | Model manifest |
| `FYP_DEMO_LOG_DIR` | `/tmp/fyp-demo` | All demo logs |
| `FYP_ML_IGNORE_LEVELS` | `2` | L2 excluded from alert level (score still shown) |
| `FYP_ML_CALIBRATE_SAMPLES` | `20` | Baseline calibration rows (~10 s) |
| `FYP_ML_L2_DELTA` | `0.55` | Min L2 adj delta for ml-L2 (high bar) |
| `FYP_ML_L3_DELTA` | `0.20` | Min L3 adj delta for ml-L3 |
| `FYP_ML_L2_SPIKES` | `0` | L2 openat/read spike rules off |
| `FYP_ML_L3_SPIKES` | `0` | L3 instant spike rules off |
| `FYP_ML_L3_ROLLING` | `0` | L3 rolling window rules off (was idle FP) |
| `FYP_ML_L4_SPIKES` | `1` | L4 syscall spikes on |
| `FYP_ML_SIM_DETECT` | `1` | Process scan for unseen scripts |
| `FYP_ML_SIM_MALICIOUS_STREAK` | `1` | Fast alert when sim running |
| `FYP_ML_MALICIOUS_STREAK` | `3` | Idle hysteresis |
| `FYP_TELEMETRY_CSV` | `/tmp/fyp_telemetry_live.csv` | Live collector output |
| `FYP_ML_API_URL` | `http://127.0.0.1:8765/predict` | GUI → API |

---

## Demo script map

| Script | Role |
|--------|------|
| `scripts/start_demo_stack.sh` | Start LKM + daemon + ML API + collector + GUI |
| `scripts/stop_demo_stack.sh` | Stop all demo processes |
| `scripts/run_demo_verbose.sh` | Start stack + tail all logs |
| `scripts/export_demo_logs.sh` | Copy logs → `logs/demo_latest.txt` |
| `scripts/ml_api.py` | Live inference API |
| `scripts/collector_live.py` | eBPF → CSV |
| `scripts/demo_log.py` | Shared logging helpers |

---

## Examiner demo flow (recommended)

1. `sudo scripts/run_demo_verbose.sh` — confirm idle **System Clean** after calibration.
2. Explain: dashboard **L2 score** may fluctuate; **detection level** comes from sim assist + L3/L4.
3. Run L4 sim → red panel + `sim-L4` or `spike-L4` in logs.
4. Run L3 sim → `sim-L3` in logs.
5. Run L2 `unseen2.py` → `sim-L2` in logs.
6. `bash scripts/export_demo_logs.sh` if examiner wants proof.

---

## Known limits (thesis honesty)

- **L2 ML-only** on unseen sims: weak without keyboard IRQ signal; use **sim-L2** for demo.
- **L3 ML-only**: mild sims below rootkit training intensity; use **sim-L3** + optional L4-style spikes.
- **Stat poller (`unseen2.1.py`)**: invisible to eBPF (`stat()` not probed).
- **No time for re-collection**: tuning used existing live CSV bootstrap in `dataset/l2_supplement/`.

---

## System versions

Kernel v0.6 | Daemon v0.2 | GUI v3.3
