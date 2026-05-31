#!/bin/bash
# Verbose demo: start stack + multiplex logs to terminal and logs/demo_latest.txt
# Usage: sudo scripts/run_demo_verbose.sh

set -euo pipefail

PROJECT_DIR="${FYP_PROJECT_DIR:-/home/fyp/project}"
LOG_DIR="${FYP_DEMO_LOG_DIR:-/tmp/fyp-demo}"
SESSION_DIR="$PROJECT_DIR/logs/demo_sessions"
LATEST="$PROJECT_DIR/logs/demo_latest.txt"

mkdir -p "$LOG_DIR" "$SESSION_DIR"
chmod 777 "$LOG_DIR" 2>/dev/null || true

export FYP_DEMO_VERBOSE=1
export FYP_DEMO_LOG_DIR="$LOG_DIR"
export FYP_ML_DEEP_LOG=1
export FYP_ML_L2_SPIKE_STREAK="${FYP_ML_L2_SPIKE_STREAK:-2}"
export FYP_ML_L3_SPIKE_STREAK="${FYP_ML_L3_SPIKE_STREAK:-2}"
export FYP_ML_L2_OPENAT_MARGIN="${FYP_ML_L2_OPENAT_MARGIN:-2200}"
export FYP_ML_L2_READ_MARGIN="${FYP_ML_L2_READ_MARGIN:-2800}"

STAMP="$(date +%Y%m%d_%H%M%S)"
SESSION_FILE="$SESSION_DIR/demo_verbose_${STAMP}.txt"

echo "Starting demo stack (verbose)..."
echo "  Log dir:     $LOG_DIR"
echo "  Session log: $SESSION_FILE"
echo "  Latest:      $LATEST"
echo ""

bash "$PROJECT_DIR/scripts/start_demo_stack.sh"

echo ""
echo "Tailing logs (Ctrl+C stops tail only; use stop_demo_stack.sh to tear down)..."
echo "========================================="

touch "$LOG_DIR/fyp_ml_api.log" "$LOG_DIR/fyp_ml_decisions.log" \
      "$LOG_DIR/fyp_collector_live.log" "$LOG_DIR/fyp_daemon.log" "$LOG_DIR/fyp_gui.log"
chmod 666 "$LOG_DIR"/*.log 2>/dev/null || true

tail -F "$LOG_DIR/fyp_ml_api.log" \
      "$LOG_DIR/fyp_ml_decisions.log" \
      "$LOG_DIR/fyp_collector_live.log" \
      "$LOG_DIR/fyp_daemon.log" \
      "$LOG_DIR/fyp_gui.log" 2>/dev/null \
  | tee "$SESSION_FILE" | tee "$LATEST"
