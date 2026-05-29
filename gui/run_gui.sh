#!/bin/bash
# Launch script for FYP GUI
# Checks prerequisites and starts the Qt application

echo "FYP Keylogger Detection - GUI Launcher"
echo "========================================"

# Check if kernel module is loaded (v0.6 procfs)
if ! lsmod | grep -q '^fyp_kbd ' || [ ! -r /proc/fyp_detector/stats ]; then
    echo "WARNING: Kernel module not loaded or procfs unavailable"
    echo "Start demo stack: sudo ../scripts/start_demo_stack.sh"
    echo "Or manually: cd ../kernel && sudo insmod fyp_kbd.ko"
fi

# Check if daemon is running
if [ ! -f /tmp/fyp_status.json ]; then
    echo "WARNING: Daemon not running - no status file found"
    echo "The daemon should be running. Start it with:"
    echo "  cd ../daemon && python3 fyp_daemon.py"
    echo ""
    echo "Starting GUI anyway (will show 'No data' until daemon starts)..."
fi

# Check PySide6
python3 -c "import PySide6" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "ERROR: PySide6 not installed"
    echo "Install with: pip3 install PySide6"
    exit 1
fi

echo "Starting GUI..."
python3 fyp_gui.py
