#!/bin/bash
# FYP Keylogger Detection System - Unified Start Script
# Loads kernel module, starts daemon, launches GUI

set -e

PROJECT_DIR="/home/fyp/project"
KERNEL_DIR="$PROJECT_DIR/kernel"
DAEMON_DIR="$PROJECT_DIR/daemon"
GUI_DIR="$PROJECT_DIR/gui"

echo "========================================="
echo "FYP Keylogger Detection System - Startup"
echo "========================================="
echo ""

# Setup log files with proper permissions
echo "→ Preparing log files..."
touch /tmp/fyp_daemon.log /tmp/fyp_gui.log 2>/dev/null || true
chmod 666 /tmp/fyp_daemon.log /tmp/fyp_gui.log 2>/dev/null || true

# Check if running as root for kernel module
if [ "$EUID" -ne 0 ]; then
    echo "⚠ This script requires sudo for kernel module loading"
    exec sudo "$0" "$@"
    exit $?
fi

# Step 1: Load kernel module
echo "[1/3] Checking kernel module..."
if lsmod | grep -q "^fyp_kbd "; then
    echo "✓ Kernel module already loaded"
else
    echo "→ Loading kernel module..."
    cd "$KERNEL_DIR"
    
    # Compile if .ko doesn't exist
    if [ ! -f "fyp_kbd.ko" ]; then
        echo "  Compiling kernel module..."
        make
    fi
    
    # Load module
    insmod fyp_kbd.ko
    sleep 1
    
    if lsmod | grep -q "^fyp_kbd "; then
        echo "✓ Kernel module loaded successfully"
        dmesg | tail -3
    else
        echo "✗ Failed to load kernel module"
        exit 1
    fi
fi

echo ""

# Step 2: Start daemon
echo "[2/3] Checking daemon..."
if pgrep -f "fyp_daemon.py" > /dev/null; then
    echo "✓ Daemon already running (PID: $(pgrep -f fyp_daemon.py))"
else
    echo "→ Starting daemon..."
    cd "$DAEMON_DIR"
    
    # Get the actual user (not root if using sudo)
    ACTUAL_USER=${SUDO_USER:-$USER}
    
    # Ensure log file exists with correct permissions
    sudo touch /tmp/fyp_daemon.log
    sudo chown "$ACTUAL_USER:$ACTUAL_USER" /tmp/fyp_daemon.log
    sudo chmod 664 /tmp/fyp_daemon.log
    
    # Start daemon as the actual user (use bash -c for proper redirection)
    sudo -u "$ACTUAL_USER" bash -c "python3 fyp_daemon.py > /tmp/fyp_daemon.log 2>&1 &"
    DAEMON_PID=$!
    sleep 2
    
    if pgrep -f "fyp_daemon.py" > /dev/null; then
        echo "✓ Daemon started successfully (PID: $(pgrep -f fyp_daemon.py))"
    else
        echo "✗ Failed to start daemon"
        echo "  Check logs: tail -20 /tmp/fyp_daemon.log"
        exit 1
    fi
fi

echo ""

# Step 3: Launch GUI
echo "[3/3] Launching GUI..."
# Ensure log file exists with correct permissions
sudo touch /tmp/fyp_gui.log
sudo chown "$ACTUAL_USER:$ACTUAL_USER" /tmp/fyp_gui.log
sudo chmod 664 /tmp/fyp_gui.log

ACTUAL_USER=${SUDO_USER:-$USER}
DISPLAY_VAR="${DISPLAY:-:0}"

# Launch GUI as actual user with proper display (use bash -c for proper redirection)
sudo -u "$ACTUAL_USER" bash -c "cd '$GUI_DIR' && DISPLAY='$DISPLAY_VAR' python3 main_gui.py > /tmp/fyp_gui.log 2>&1 &"
GUI_PID=$!

sleep 2

if pgrep -f "main_gui.py\|fyp_gui.py" > /dev/null; then
    echo "✓ GUI launched successfully (PID: $(pgrep -f 'main_gui.py\|fyp_gui.py'))"
else
    echo "✗ Failed to launch GUI"
    echo "  Check logs: tail -20 /tmp/fyp_gui.log"
    echo "  Check X display: echo \$DISPLAY"
fi

echo ""
echo "========================================="
echo "System Status:"
echo "========================================="
echo "Kernel Module: $(lsmod | grep fyp_kbd | awk '{print "Loaded (" $2 " size)"}')"
echo "Daemon:        Running (PID: $(pgrep -f fyp_daemon.py 2>/dev/null || echo 'Not running'))"
echo "GUI:           Running (PID: $(pgrep -f 'main_gui.py\|fyp_gui.py' 2>/dev/null || echo 'Not running'))"
echo ""
echo "Log files:"
echo "  Daemon: /tmp/fyp_daemon.log"
echo "  GUI:    /tmp/fyp_gui.log"
echo "  Kernel: dmesg | grep fyp_detector"
echo ""
echo "To stop:"
echo "  pkill -f fyp_daemon.py"
echo "  pkill -f 'main_gui.py\|fyp_gui.py'"
echo "  sudo rmmod fyp_kbd"
echo "========================================="
