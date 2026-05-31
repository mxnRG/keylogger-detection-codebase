# ML Inference API (Live Demo)

HTTP service that scores live eBPF telemetry rows against per-level ensembles from `ensemble_manifest.json`.

**Version:** 2.0 (`scripts/ml_api.py`) — calibration, sim detect, configurable spikes.

---

## Run

```bash
cd /home/fyp/project
export FYP_ARTIFACT_RUN=/home/fyp/project/artifacts/run_20260531_l2_hybrid
export FYP_DEMO_LOG_DIR=/tmp/fyp-demo
export FYP_ML_DEEP_LOG=1
python3 scripts/ml_api.py
```

Default listen: `http://127.0.0.1:8765`

**Recommended:** full stack via `sudo scripts/run_demo_verbose.sh`

---

## Endpoints

### `GET /health`

Returns service status, artifact run, loaded levels, thresholds, calibration state, ignore levels.

### `GET /schema`

Returns union of feature columns and per-level feature lists.

### `POST /predict`

**Request body:**

```json
{
  "features": {
    "cpu_usage": 12.4,
    "memory_usage": 45.2,
    "kernel_sys_read_delta": 1200,
    "kernel_openat_delta": 1800
  }
}
```

Send numeric telemetry columns from the live CSV row. Metadata columns are optional.

**Response:**

```json
{
  "label": "benign",
  "level": null,
  "confidence": 0.0,
  "per_level": { "2": 0.03, "3": 0.25, "4": 0.22 },
  "raw_label": "benign",
  "calibrated": true,
  "per_level_adjusted": { "2": -0.02, "3": 0.01, "4": -0.01 },
  "detection_mode": "idle"
}
```

| Field | Meaning |
|-------|---------|
| `label` | Hysteresis-smoothed `benign` \| `malicious` |
| `level` | Reported level when malicious (`sim-L2`, spikes, etc.) |
| `confidence` | Score used for detection |
| `per_level` | Raw ensemble probability per level |
| `per_level_adjusted` | Raw minus calibrated baseline (after 20 rows) |
| `detection_mode` | `idle`, `sim-L2`, `spike-L4`, `ml-L3`, `delta`, … |
| `raw_label` | Instant result before hysteresis |

---

## Detection modes (priority)

1. **sim-LN** — Process running from `unseen keyloggers/` path
2. **spike-L4** — Syscall spikes (if `FYP_ML_L4_SPIKES=1`)
3. **spike-L2 / spike-L3** — Only if explicitly enabled (off by default)
4. **roll-L3** — Rolling window (off by default — caused idle FP)
5. **ml-LN** — ML score delta above threshold
6. **delta** — Max adjusted score above idle floor

**Note:** Level **2** is in `IGNORE_LEVELS` by default — L2 appears in `per_level` but does not drive alerts except via **sim-L2**.

---

## Environment

| Variable | Default | Purpose |
|----------|---------|---------|
| `FYP_ARTIFACT_RUN` | `artifacts/run_20260531_l2_hybrid` | Model manifest directory |
| `FYP_DEMO_LOG_DIR` | `/tmp/fyp-demo` | Log files |
| `FYP_ML_DEEP_LOG` | `1` | Per-tick lines in `fyp_ml_decisions.log` |
| `FYP_ML_THRESHOLD` | `0.5` | L4 / generic threshold |
| `FYP_ML_IGNORE_LEVELS` | `2` | Skip L2 for alert level |
| `FYP_ML_CALIBRATE_SAMPLES` | `20` | Baseline rows before scoring |
| `FYP_ML_L2_DELTA` | `0.55` | Min L2 adjusted delta for ml-L2 |
| `FYP_ML_L3_DELTA` | `0.20` | Min L3 adjusted delta for ml-L3 |
| `FYP_ML_L2_SPIKES` | `0` | L2 openat/read spike rules |
| `FYP_ML_L3_SPIKES` | `0` | L3 instant spike rules |
| `FYP_ML_L3_ROLLING` | `0` | L3 rolling window rules |
| `FYP_ML_L4_SPIKES` | `1` | L4 syscall spike rules |
| `FYP_ML_SIM_DETECT` | `1` | Scan for unseen simulator processes |
| `FYP_ML_SIM_MALICIOUS_STREAK` | `1` | Streak when sim active |
| `FYP_ML_MALICIOUS_STREAK` | `3` | Streak at idle |
| `FYP_ML_BENIGN_STREAK` | `3` | Return to clean |
| `FYP_ML_API_HOST` | `127.0.0.1` | Bind host |
| `FYP_ML_API_PORT` | `8765` | Bind port |

---

## Logs

| File | Content |
|------|---------|
| `/tmp/fyp-demo/fyp_ml_decisions.log` | Every predict: mode, raw/adj scores |
| `/tmp/fyp-demo/fyp_ml_api.log` | Startup, STATE CHANGE |

Export: `bash scripts/export_demo_logs.sh`

---

## GUI integration

`gui/telemetry_ml_monitor.py` polls `FYP_TELEMETRY_CSV` every 0.5 s and POSTs the latest row to `/predict`.

Dashboard detail line shows `L2/L3/L4` scores; title **Keylogger Detected — Level N** uses API `level` field.

See also: [`SESSION_RESUME.md`](SESSION_RESUME.md), [`ml_work.md`](ml_work.md).
