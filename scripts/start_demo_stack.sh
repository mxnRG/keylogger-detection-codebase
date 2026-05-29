#!/bin/bash
# Start full FYP demo stack: LKM, watchdog, daemon, ML API, collector, GUI

set -e

PROJECT_DIR="${FYP_PROJECT_DIR:-/home/fyp/project}"
KERNEL_DIR="$PROJECT_DIR/kernel"
DAEMON_DIR="$PROJECT_DIR/daemon"
GUI_DIR="$PROJECT_DIR/gui"
SCRIPTS_DIR="$PROJECT_DIR/scripts"
ARTIFACT_RUN="${FYP_ARTIFACT_RUN:-$PROJECT_DIR/artifacts/run_20260529_193015}"

export FYP_PROJECT_DIR="$PROJECT_DIR"
export FYP_ARTIFACT_RUN="$ARTIFACT_RUN"
export FYP_TELEMETRY_CSV="${FYP_TELEMETRY_CSV:-/tmp/fyp_telemetry_live.csv}"
export FYP_ML_API_URL="${FYP_ML_API_URL:-http://127.0.0.1:8765/predict}"

if [ "$EUID" -ne 0 ]; then
    echo "Re-running with sudo for kernel module and eBPF collector..."
    exec sudo -E env DISPLAY="${DISPLAY:-:0}" SUDO_USER="${SUDO_USER:-$USER}" "$0" "$@"
fi

ACTUAL_USER="${SUDO_USER:-$USER}"

echo "========================================="
echo "FYP Demo Stack"
echo "========================================="

touch /tmp/fyp_daemon.log /tmp/fyp_gui.log /tmp/fyp_lkm_watchdog.log 2>/dev/null || true
chmod 666 /tmp/fyp_daemon.log /tmp/fyp_gui.log 2>/dev/null || true
chown "$ACTUAL_USER:$ACTUAL_USER" /tmp/fyp_daemon.log /tmp/fyp_gui.log 2>/dev/null || true

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
    nohup bash "$SCRIPTS_DIR/lkm_watchdog.sh" >>/tmp/fyp_lkm_watchdog.log 2>&1 &
else
    echo "[2/6] LKM watchdog already running"
fi

# Daemon
if ! pgrep -f "fyp_daemon.py" >/dev/null; then
    echo "[3/6] Starting daemon..."
    sudo -u "$ACTUAL_USER" bash -c "cd '$DAEMON_DIR' && python3 fyp_daemon.py >> /tmp/fyp_daemon.log 2>&1 &"
    sleep 2
else
    echo "[3/6] Daemon already running"
fi

# ML API
if ! pgrep -f "ml_api.py" >/dev/null; then
    echo "[4/6] Starting ML API..."
    sudo -u "$ACTUAL_USER" bash -c "
        cd '$SCRIPTS_DIR' &&
        export FYP_ARTIFACT_RUN='$ARTIFACT_RUN' &&
        nohup python3 ml_api.py >> /tmp/fyp_ml_api.log 2>&1 &
    "
    sleep 2
else
    echo "[4/6] ML API already running"
fi

# Live collector (truncate fresh session)
if ! pgrep -f "collector_live.py" >/dev/null; then
    echo "[5/6] Starting live eBPF collector..."
    nohup python3 "$SCRIPTS_DIR/collector_live.py" --truncate >>/tmp/fyp_collector_live.log 2>&1 &
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
        nohup python3 main_gui.py >> /tmp/fyp_gui.log 2>&1 &
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
echo "  ML API:    $(pgrep -c -f ml_api.py || echo 0) process(es) — curl http://127.0.0.1:8765/health"
echo "  Collector: $(pgrep -c -f collector_live.py || echo 0) process(es) — $FYP_TELEMETRY_CSV"
echo "  GUI:       $(pgrep -c -f 'main_gui.py|fyp_gui.py' || echo 0) process(es)"
echo ""
echo "Unseen keylogger demo (separate terminal, as user):"
echo "  python3 \"$PROJECT_DIR/dataset/3-natasha-mamoon-20260529T122553Z-3-001/3-natasha-mamoon/unseen keyloggers/unseen_level3_agent_collector_queue.py\""
echo ""
echo "Stop: pkill -f 'collector_live|ml_api|fyp_daemon|lkm_watchdog|main_gui|fyp_gui'; sudo rmmod fyp_kbd"
echo "========================================="
