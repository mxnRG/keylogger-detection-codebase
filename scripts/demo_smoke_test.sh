#!/bin/bash
# Headless checks that the ML API is demo-safe before presentation.
set -euo pipefail

PROJECT_DIR="${FYP_PROJECT_DIR:-/home/fyp/project}"
API_BASE="${FYP_ML_API_BASE:-http://127.0.0.1:8765}"
BENIGN_CSV="${FYP_SMOKE_BENIGN_CSV:-$PROJECT_DIR/dataset/l2_supplement/demo_vm_benign.csv}"
EXPECTED_RUN="${FYP_ARTIFACT_RUN:-$PROJECT_DIR/artifacts/run_20260531_l2_hybrid}"

fail() {
    echo "SMOKE TEST FAIL: $*" >&2
    exit 1
}

echo "=== Demo smoke test ==="

health_json="$(curl -sf "$API_BASE/health" 2>/dev/null)" || fail "ML API not reachable at $API_BASE/health"

python3 - <<'PY' "$health_json" "$EXPECTED_RUN" || fail "health check assertions"
import json, sys
health = json.loads(sys.argv[1])
expected_run = sys.argv[2]
run_dir = health.get("run_dir", "")
if expected_run not in run_dir and "run_20260531_l2_hybrid" not in run_dir:
    raise SystemExit(f"unexpected run_dir: {run_dir}")
ignore = health.get("ignore_levels", [])
sim_detect = health.get("sim_detect", True)
profile = "ml-first" if not sim_detect and 2 not in ignore else "sim-assist"
if sim_detect and 2 in ignore:
    profile = "sim-assist"
print(f"OK health: run_dir={run_dir} profile={profile} ignore_levels={ignore} sim_detect={sim_detect}")
PY

if [ ! -f "$BENIGN_CSV" ]; then
    fail "benign CSV not found: $BENIGN_CSV"
fi

python3 - <<'PY' "$API_BASE" "$BENIGN_CSV" || fail "benign predict loop"
import csv
import json
import sys
import time
import urllib.request
import urllib.error

api_base = sys.argv[1]
csv_path = sys.argv[2]
url = f"{api_base.rstrip('/')}/predict"

rows = []
with open(csv_path, newline="", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    for row in reader:
        rows.append(row)
        if len(rows) >= 10:
            break

if len(rows) < 5:
    raise SystemExit(f"need at least 5 benign rows, got {len(rows)}")

for i, row in enumerate(rows, 1):
    features = {k: v for k, v in row.items() if k not in ("timestamp", "scenario", "collector_type")}
    payload = json.dumps({"features": features}).encode()
    req = urllib.request.Request(
        url, data=payload, headers={"Content-Type": "application/json"}, method="POST"
    )
    # Startup can be CPU-heavy (eBPF compile). Retry a few times to avoid flaky timeouts.
    body = None
    last_exc = None
    for attempt in range(1, 4):
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                body = json.loads(resp.read().decode())
            break
        except (TimeoutError, urllib.error.URLError) as exc:
            last_exc = exc
            time.sleep(1.5 * attempt)
    if body is None:
        raise SystemExit(f"row {i}: request failed after retries: {last_exc}")
    if body.get("label") != "benign":
        raise SystemExit(f"row {i}: expected benign, got {body.get('label')} mode={body.get('detection_mode')}")

print(f"OK: {len(rows)} benign rows → all label=benign")

# High openat row — still benign when L2 spikes off
features = dict(rows[0])
features["kernel_openat_delta"] = "50000"
features["kernel_sys_read_delta"] = "50000"
payload = json.dumps({"features": features}).encode()
req = urllib.request.Request(
    url, data=payload, headers={"Content-Type": "application/json"}, method="POST"
)
body = None
last_exc = None
for attempt in range(1, 4):
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            body = json.loads(resp.read().decode())
        break
    except (TimeoutError, urllib.error.URLError) as exc:
        last_exc = exc
        time.sleep(1.5 * attempt)
if body is None:
    raise SystemExit(f"spike row: request failed after retries: {last_exc}")
if body.get("label") != "benign":
    raise SystemExit(f"spike row: expected benign, got {body.get('label')} mode={body.get('detection_mode')}")
print("OK: high openat/read row still benign")
PY

echo "=== Smoke test passed ==="
