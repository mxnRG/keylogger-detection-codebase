#!/bin/bash
# Start full FYP demo stack: LKM, watchdog, daemon, ML API, collector, GUI

set -e

PROJECT_DIR="${FYP_PROJECT_DIR:-/home/fyp/project}"
KERNEL_DIR="$PROJECT_DIR/kernel"
DAEMON_DIR="$PROJECT_DIR/daemon"
GUI_DIR="$PROJECT_DIR/gui"
SCRIPTS_DIR="$PROJECT_DIR/scripts"
LOG_DIR="${FYP_DEMO_LOG_DIR:-/tmp/fyp-demo}"

export FYP_PROJECT_DIR="$PROJECT_DIR"
export FYP_DEMO_LOG_DIR="$LOG_DIR"
export FYP_DEMO_VERBOSE="${FYP_DEMO_VERBOSE:-1}"
export FYP_ML_DEEP_LOG="${FYP_ML_DEEP_LOG:-1}"
export FYP_TELEMETRY_CSV="${FYP_TELEMETRY_CSV:-/tmp/fyp_telemetry_live.csv}"
export FYP_ML_API_URL="${FYP_ML_API_URL:-http://127.0.0.1:8765/predict}"

# ML-first by default (FYP thesis demo). FYP_DEMO_PROFILE=safe → sim-assist fallback.
DEMO_PROFILE="${FYP_DEMO_PROFILE:-ml}"
if [ "$DEMO_PROFILE" = "safe" ]; then
    # shellcheck source=scripts/demo_safe.env
    source "$SCRIPTS_DIR/demo_safe.env"
else
    # shellcheck source=scripts/demo_ml.env
    source "$SCRIPTS_DIR/demo_ml.env"
fi

mkdir -p "$LOG_DIR"
chmod 777 "$LOG_DIR" 2>/dev/null || true

if [ "$EUID" -ne 0 ]; then
    echo "Re-running with sudo for kernel module and eBPF collector..."
    exec sudo -E env DISPLAY="${DISPLAY:-:0}" SUDO_USER="${SUDO_USER:-$USER}" "$0" "$@"
fi

ACTUAL_USER="${SUDO_USER:-$USER}"

echo "========================================="
echo "FYP Demo Stack"
echo "========================================="

touch "$LOG_DIR/fyp_daemon.log" "$LOG_DIR/fyp_gui.log" "$LOG_DIR/fyp_lkm_watchdog.log" \
      "$LOG_DIR/fyp_ml_api.log" "$LOG_DIR/fyp_ml_decisions.log" \
      "$LOG_DIR/fyp_collector_live.log" 2>/dev/null || true
chmod 666 "$LOG_DIR"/*.log 2>/dev/null || true
chown "$ACTUAL_USER:$ACTUAL_USER" "$LOG_DIR"/*.log 2>/dev/null || true

# Initial LKM load
if ! lsmod | grep -q '^fyp_kbd '; then
    echo "[1/6] Loading kernel module..."
    cd "$KERNEL_DIR"
    [ -f fyp_kbd.ko ] || make
    insmod fyp_kbd.ko
    sleep 1
else
    echo "[1/6] Kernel module already loaded"
fi

# LKM watchdog
if ! pgrep -f "lkm_watchdog.sh" >/dev/null; then
    echo "[2/6] Starting LKM watchdog..."
    chmod +x "$SCRIPTS_DIR/lkm_watchdog.sh"
    nohup bash "$SCRIPTS_DIR/lkm_watchdog.sh" >>"$LOG_DIR/fyp_lkm_watchdog.log" 2>&1 &
else
    echo "[2/6] LKM watchdog already running"
fi

# Daemon
if ! pgrep -f "fyp_daemon.py" >/dev/null; then
    echo "[3/6] Starting daemon..."
    sudo -u "$ACTUAL_USER" bash -c "cd '$DAEMON_DIR' && python3 fyp_daemon.py >> '$LOG_DIR/fyp_daemon.log' 2>&1 &"
    sleep 2
else
    echo "[3/6] Daemon already running"
fi

# ML API
if ! pgrep -f "ml_api.py" >/dev/null; then
    echo "[4/6] Starting ML API..."
    sudo -u "$ACTUAL_USER" bash -c "
        cd '$SCRIPTS_DIR' &&
        export FYP_DEMO_LOG_DIR='$LOG_DIR' &&
        export FYP_DEMO_VERBOSE='${FYP_DEMO_VERBOSE}' &&
        export FYP_ML_DEEP_LOG='${FYP_ML_DEEP_LOG}' &&
        export FYP_ARTIFACT_RUN='${FYP_ARTIFACT_RUN}' &&
        export FYP_ML_IGNORE_LEVELS='${FYP_ML_IGNORE_LEVELS}' &&
        export FYP_ML_CALIBRATE_SAMPLES='${FYP_ML_CALIBRATE_SAMPLES}' &&
        export FYP_ML_L2_THRESHOLD='${FYP_ML_L2_THRESHOLD}' &&
        export FYP_ML_L3_THRESHOLD='${FYP_ML_L3_THRESHOLD}' &&
        export FYP_ML_L2_DELTA='${FYP_ML_L2_DELTA}' &&
        export FYP_ML_L3_DELTA='${FYP_ML_L3_DELTA}' &&
        export FYP_ML_L2_SPIKES='${FYP_ML_L2_SPIKES}' &&
        export FYP_ML_L3_SPIKES='${FYP_ML_L3_SPIKES}' &&
        export FYP_ML_L3_ROLLING='${FYP_ML_L3_ROLLING}' &&
        export FYP_ML_L4_SPIKES='${FYP_ML_L4_SPIKES}' &&
        export FYP_ML_SIM_DETECT='${FYP_ML_SIM_DETECT}' &&
        export FYP_ML_SIM_MALICIOUS_STREAK='${FYP_ML_SIM_MALICIOUS_STREAK}' &&
        export FYP_ML_MALICIOUS_STREAK='${FYP_ML_MALICIOUS_STREAK}' &&
        export FYP_ML_RULE_STREAK='${FYP_ML_RULE_STREAK}' &&
        export FYP_ML_HOLD_TICKS='${FYP_ML_HOLD_TICKS}' &&
        export FYP_ML_BENIGN_STREAK='${FYP_ML_BENIGN_STREAK}' &&
        export FYP_ML_SPIKES_REQUIRE_SIM='${FYP_ML_SPIKES_REQUIRE_SIM}' &&
        export FYP_ML_L2_SPIKE_STREAK='${FYP_ML_L2_SPIKE_STREAK}' &&
        export FYP_ML_L3_SPIKE_STREAK='${FYP_ML_L3_SPIKE_STREAK}' &&
        export FYP_ML_L2_OPENAT_MARGIN='${FYP_ML_L2_OPENAT_MARGIN}' &&
        export FYP_ML_L2_READ_MARGIN='${FYP_ML_L2_READ_MARGIN}' &&
        nohup python3 ml_api.py >> '$LOG_DIR/fyp_ml_api.log' 2>&1 &
    "
    sleep 2
else
    echo "[4/6] ML API already running"
fi

# Live collector (truncate fresh session)
if ! pgrep -f "collector_live.py" >/dev/null; then
    echo "[5/6] Starting live eBPF collector..."
    nohup python3 "$SCRIPTS_DIR/collector_live.py" --truncate >>"$LOG_DIR/fyp_collector_live.log" 2>&1 &
    sleep 1
else
    echo "[5/6] Live collector already running"
fi

# GUI
if ! pgrep -f "main_gui.py\|fyp_gui.py" >/dev/null; then
    echo "[6/6] Launching GUI..."
    sudo -u "$ACTUAL_USER" bash -c "
        cd '$GUI_DIR' &&
        DISPLAY='${DISPLAY:-:0}' \
        FYP_TELEMETRY_CSV='$FYP_TELEMETRY_CSV' \
        FYP_ML_API_URL='$FYP_ML_API_URL' \
        nohup python3 main_gui.py >> '$LOG_DIR/fyp_gui.log' 2>&1 &
    "
    sleep 2
else
    echo "[6/6] GUI already running"
fi

echo ""
echo "Demo stack status:"
echo "  LKM:       $(lsmod | grep -c '^fyp_kbd ' || echo 0) loaded"
echo "  Watchdog:  $(pgrep -c -f lkm_watchdog.sh || echo 0) process(es)"
echo "  Daemon:    $(pgrep -c -f fyp_daemon.py || echo 0) process(es)"
echo "  Logs:      $LOG_DIR/"
echo "  ML API:    $(pgrep -c -f ml_api.py || echo 0) process(es) — curl http://127.0.0.1:8765/health"
echo "  Collector: $(pgrep -c -f collector_live.py || echo 0) process(es) — $FYP_TELEMETRY_CSV"
echo "  GUI:       $(pgrep -c -f 'main_gui.py|fyp_gui.py' || echo 0) process(es)"
echo ""
echo "Unseen keylogger demo (separate terminal, as user):"
echo "  python3 \"$PROJECT_DIR/dataset/3-natasha-mamoon-20260529T122553Z-3-001/3-natasha-mamoon/unseen keyloggers/unseen_level3_agent_collector_queue.py\""
echo ""
echo "Verbose logs:  sudo scripts/run_demo_verbose.sh"
echo "Decision log:  $LOG_DIR/fyp_ml_decisions.log"
echo "Stop:          sudo scripts/stop_demo_stack.sh"
echo "========================================="
