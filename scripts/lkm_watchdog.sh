#!/bin/bash
# Watch fyp_kbd.ko and reload if detached. Writes /tmp/fyp_lkm_status.json

set -u

PROJECT_DIR="${FYP_PROJECT_DIR:-/home/fyp/project}"
KERNEL_DIR="$PROJECT_DIR/kernel"
DAEMON_DIR="$PROJECT_DIR/daemon"
LOG_FILE="/tmp/fyp_lkm_watchdog.log"
STATUS_FILE="/tmp/fyp_lkm_status.json"
FAIL_FLAG="/tmp/fyp_lkm_reload_failed"
INTERVAL="${FYP_LKM_WATCH_INTERVAL:-5}"
COOLDOWN="${FYP_LKM_RELOAD_COOLDOWN:-30}"
MAX_FAILURES="${FYP_LKM_MAX_FAILURES:-3}"
FAILURE_WINDOW="${FYP_LKM_FAILURE_WINDOW:-600}"

last_reload=0
failure_count=0
window_start=$(date +%s)

log() {
    echo "[$(date -Iseconds)] $*" | tee -a "$LOG_FILE"
}

write_status() {
    local loaded="$1"
    local state="$2"
    local message="$3"
    local failures="${4:-0}"
    LOADED="$loaded" STATE="$state" MESSAGE="$message" FAILURES="$failures" STATUS_FILE="$STATUS_FILE" \
    python3 -c '
import json, os
from datetime import datetime, timezone
payload = {
    "loaded": os.environ.get("LOADED") == "true",
    "state": os.environ["STATE"],
    "message": os.environ["MESSAGE"],
    "failures": int(os.environ.get("FAILURES", "0")),
    "timestamp": datetime.now(timezone.utc).isoformat(),
}
with open(os.environ["STATUS_FILE"], "w") as f:
    json.dump(payload, f)
'
}

lkm_healthy() {
    lsmod | grep -q '^fyp_kbd ' && test -r /proc/fyp_detector/stats
}

load_lkm() {
    cd "$KERNEL_DIR" || return 1
    if [ ! -f "fyp_kbd.ko" ]; then
        log "Building kernel module..."
        make >>"$LOG_FILE" 2>&1 || return 1
    fi
    insmod fyp_kbd.ko >>"$LOG_FILE" 2>&1
    sleep 1
    lkm_healthy
}

restart_daemon_if_stale() {
    local actual_user="${SUDO_USER:-$USER}"
    if [ ! -f /tmp/fyp_status.json ]; then
        needs=1
    else
        needs=0
        age=$(($(date +%s) - $(stat -c %Y /tmp/fyp_status.json 2>/dev/null || echo 0)))
        [ "$age" -gt 10 ] && needs=1
    fi
    if [ "$needs" -eq 1 ] && pgrep -f "fyp_daemon.py" >/dev/null; then
        log "Restarting daemon after LKM reload..."
        pkill -f "fyp_daemon.py" || true
        sleep 1
    fi
    if ! pgrep -f "fyp_daemon.py" >/dev/null; then
        touch /tmp/fyp_daemon.log 2>/dev/null || true
        chown "$actual_user:$actual_user" /tmp/fyp_daemon.log 2>/dev/null || true
        sudo -u "$actual_user" bash -c "cd '$DAEMON_DIR' && python3 fyp_daemon.py >> /tmp/fyp_daemon.log 2>&1 &" || true
        sleep 2
    fi
}

record_failure() {
    local now
    now=$(date +%s)
    if [ $((now - window_start)) -gt "$FAILURE_WINDOW" ]; then
        failure_count=0
        window_start=$now
    fi
    failure_count=$((failure_count + 1))
    if [ "$failure_count" -ge "$MAX_FAILURES" ]; then
        touch "$FAIL_FLAG"
        log "Auto-reload disabled after $failure_count failures"
    fi
}

log "LKM watchdog started (interval=${INTERVAL}s)"
write_status false "starting" "Watchdog started" 0

while true; do
    if lkm_healthy; then
        rm -f "$FAIL_FLAG" 2>/dev/null || true
        failure_count=0
        write_status true "loaded" "Kernel module active" 0
    else
        if [ -f "$FAIL_FLAG" ]; then
            write_status false "failed" "Auto-reload disabled; check $LOG_FILE" "$failure_count"
            sleep "$INTERVAL"
            continue
        fi

        now=$(date +%s)
        since_last=$((now - last_reload))
        if [ "$last_reload" -gt 0 ] && [ "$since_last" -lt "$COOLDOWN" ]; then
            write_status false "waiting" "Cooldown before next reload (${since_last}s)" "$failure_count"
            sleep "$INTERVAL"
            continue
        fi

        write_status false "reloading" "Reloading kernel module..." "$failure_count"
        log "LKM missing — attempting insmod"
        if load_lkm; then
            log "LKM reloaded successfully"
            last_reload=$now
            restart_daemon_if_stale
            write_status true "loaded" "Kernel module reloaded" 0
        else
            log "LKM reload failed"
            last_reload=$now
            record_failure
            write_status false "offline" "Failed to load fyp_kbd.ko" "$failure_count"
        fi
    fi
    sleep "$INTERVAL"
done
