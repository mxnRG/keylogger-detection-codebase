#!/bin/bash
# Copy shareable demo logs into project logs/
set -euo pipefail
PROJECT_DIR="${FYP_PROJECT_DIR:-/home/fyp/project}"
LOG_DIR="${FYP_DEMO_LOG_DIR:-/tmp/fyp-demo}"
OUT="$PROJECT_DIR/logs/demo_latest.txt"
mkdir -p "$PROJECT_DIR/logs"
{
  echo "=== FYP demo log export $(date -Iseconds) ==="
  for f in fyp_ml_api.log fyp_ml_decisions.log fyp_collector_live.log fyp_daemon.log fyp_gui.log; do
    echo ""
    echo "==> $LOG_DIR/$f <=="
    [ -f "$LOG_DIR/$f" ] && tail -200 "$LOG_DIR/$f" || echo "(missing)"
  done
} > "$OUT"
echo "Exported → $OUT"
