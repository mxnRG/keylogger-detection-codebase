# ML Inference API (Live Demo)

HTTP service that scores live eBPF telemetry rows against per-level ensembles from `ensemble_manifest.json`.

## Run

```bash
export FYP_ARTIFACT_RUN=/home/fyp/project/artifacts/run_20260529_193015
cd /home/fyp/project/scripts
python3 ml_api.py
```

Default listen: `http://127.0.0.1:8765`

Or use the full stack: `sudo scripts/start_demo_stack.sh`

## Endpoints

### `GET /health`

Returns service status, artifact run directory, loaded levels, and threshold.

### `GET /schema`

Returns union of feature columns and per-level feature lists.

### `POST /predict`

**Request body:**

```json
{
  "features": {
    "cpu_usage": 12.4,
    "memory_usage": 45.2,
    "kernel_sys_read_delta": 1200
  }
}
```

Send all numeric telemetry columns from the live CSV row. Metadata columns (`timestamp`, `label`, `scenario`, `collector_type`) are optional and ignored for scoring.

**Response:**

```json
{
  "label": "malicious",
  "level": 3,
  "confidence": 0.87,
  "per_level": { "2": 0.15, "3": 0.87, "4": 0.22 },
  "raw_label": "malicious"
}
```

- `label` — hysteresis-smoothed (`benign` | `malicious`)
- `level` — argmax level when malicious, else `null`
- `confidence` — highest per-level malicious probability
- `raw_label` — instant threshold result before hysteresis

## Environment

| Variable | Default | Purpose |
|----------|---------|---------|
| `FYP_ARTIFACT_RUN` | `artifacts/run_20260529_193015` | Model manifest directory |
| `FYP_ML_THRESHOLD` | `0.5` | Malicious probability threshold |
| `FYP_ML_MALICIOUS_STREAK` | `3` | Consecutive raw-malicious rows before `label=malicious` |
| `FYP_ML_BENIGN_STREAK` | `3` | Consecutive raw-benign rows before `label=benign` |
| `FYP_ML_API_HOST` | `127.0.0.1` | Bind host |
| `FYP_ML_API_PORT` | `8765` | Bind port |

## GUI integration

PySide6 dashboard polls `/tmp/fyp_telemetry_live.csv` every 0.5s and POSTs the latest row to `/predict`. See `gui/telemetry_ml_monitor.py`.
