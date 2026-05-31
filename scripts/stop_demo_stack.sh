#!/bin/bash
# Stop FYP demo stack processes
set -e
pkill -f 'collector_live.py' 2>/dev/null || true
pkill -f 'ml_api.py' 2>/dev/null || true
pkill -f 'fyp_daemon.py' 2>/dev/null || true
pkill -f 'lkm_watchdog.sh' 2>/dev/null || true
pkill -f 'main_gui.py' 2>/dev/null || true
pkill -f 'fyp_gui.py' 2>/dev/null || true
if lsmod | grep -q '^fyp_kbd '; then
  rmmod fyp_kbd 2>/dev/null || true
fi
echo "Demo stack stopped."
