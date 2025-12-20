# FYP Keylogger Detection System - Quick Start Guide

**Version:** 0.4 (Complete Prototype)  
**Date:** December 15, 2025

## System Overview

This project implements a real-time keylogger detection system for Linux:
- **Kernel Module** (v0.4): Captures keyboard behavioral metadata
- **Python Daemon** (v0.1): Processes events and applies detection heuristics
- **Qt GUI** (v0.1): Real-time visualization and alerts

## Prerequisites

### 1. Install Dependencies
```bash
# Install build tools for kernel module
sudo apt update
sudo apt install build-essential linux-headers-$(uname -r)

# Install Python and Qt
sudo apt install python3 python3-pip
pip3 install PySide6
```

### 2. Verify System
```bash
uname -r  # Should be 5.15.0 or similar
```

## Installation & Launch

### Step 1: Build and Load Kernel Module
```bash
cd /home/fyp/project/kernel

# Build the module
make clean
make

# Load the module (requires sudo)
sudo insmod fyp_kbd.ko

# Verify it's loaded
lsmod | grep fyp_kbd
ls -la /proc/fyp_detector/
```

Expected output:
```
/proc/fyp_detector/
├── events   (event stream in CSV format)
├── stats    (real-time statistics)
└── control  (accepts commands like 'reset')
```

### Step 2: Start the Daemon
Open a **new terminal** (keep module loaded):
```bash
cd /home/fyp/project/daemon
python3 fyp_daemon.py
```

Expected output:
```
[HH:MM:SS] INFO: FYP Keylogger Detection Daemon v0.1
[HH:MM:SS] INFO: ✓ Kernel module detected
[HH:MM:SS] INFO: Event reader thread started
[HH:MM:SS] INFO: Daemon running. Press Ctrl+C to stop.
```

### Step 3: Start the GUI
Open a **third terminal** (keep daemon running):
```bash
cd /home/fyp/project/gui
chmod +x run_gui.sh
./run_gui.sh
```

The Qt GUI window should open showing:
- 🟢 **System Status**: Kernel Active, Daemon Running
- **Alerts Tab**: Real-time security alerts
- **Statistics Tab**: Per-process metrics
- **Event Stream Tab**: Raw event log

## Usage

### Generate Test Events
1. **Normal Typing**: Type naturally in any terminal → Low rapid ratio
2. **Automated Script**: Run `yes | head -100` → High rapid ratio (alert)
3. **Burst Test**: Run a script with rapid keypresses → Burst alert

### View Real-Time Data

**GUI (Recommended):**
- Watch the **Alerts** tab for detections
- Check **Statistics** tab for per-process metrics
- Monitor **Event Stream** for raw data

**Command Line (Alternative):**
```bash
# View real-time events
cat /proc/fyp_detector/events

# View statistics
cat /proc/fyp_detector/stats

# Reset counters
echo "reset" | sudo tee /proc/fyp_detector/control
```

## Detection Heuristics

The system uses 3 rules (no machine learning):

1. **Rapid Typing** (HIGH severity)
   - Trigger: >50% events flagged as "rapid"
   - Indicates: Automated input, possible keylogger playback

2. **Unknown Process** (MEDIUM severity)
   - Trigger: Process not in whitelist
   - Indicates: Unfamiliar application accessing keyboard

3. **Burst Pattern** (HIGH severity)
   - Trigger: >100 events/second sustained
   - Indicates: Scripted input, automation

## Shutdown

### Stop GUI
- Click the window's close button, or press `Ctrl+C` in terminal

### Stop Daemon
```bash
# In daemon terminal, press Ctrl+C
```

### Unload Kernel Module
```bash
cd /home/fyp/project/kernel
sudo rmmod fyp_kbd

# Verify it's removed
lsmod | grep fyp_kbd  # Should return nothing
ls /proc/fyp_detector/  # Should not exist
```

## Troubleshooting

### "Kernel module not loaded"
```bash
# Check dmesg for errors
dmesg | tail -n 20

# Verify module compiled correctly
cd kernel && make clean && make

# Load with verbose output
sudo insmod fyp_kbd.ko && dmesg | tail
```

### "PySide6 not installed"
```bash
pip3 install PySide6 --user
```

### "Permission denied" reading /proc/fyp_detector/events
The events file should be world-readable. Check:
```bash
ls -la /proc/fyp_detector/
cat /proc/fyp_detector/events  # Should work without sudo
```

### No events captured
- **Type in VM GUI terminal**, not VSCode SSH terminal
- Keyboard notifier captures TTY input primarily
- Try: `cat > /dev/null` then type keys

### GUI shows "No data"
- Daemon must be running first
- Check `/tmp/fyp_status.json` exists
- Restart daemon if needed

## File Structure

```
/home/fyp/project/
├── kernel/
│   ├── fyp_kbd.c          # Kernel module source (v0.4)
│   ├── Makefile           # Build configuration
│   └── PROCFS_NOTES.md    # Technical details
├── daemon/
│   └── fyp_daemon.py      # Detection daemon (v0.1)
├── gui/
│   ├── fyp_gui.py         # Qt GUI application (v0.1)
│   └── run_gui.sh         # Launch script
├── docs/
│   ├── PHASE2_DESIGN.md   # Architecture docs
│   └── IMPLEMENTATION_ORDER.md
├── current.md             # Project status
└── QUICKSTART.md          # This file
```

## Next Steps

- **Demo Scenarios**: Test different input patterns
- **Fine-tune Heuristics**: Adjust thresholds in daemon
- **Add Features**: Process whitelisting, logging, etc.
- **Documentation**: Write FYP report sections

## Support

For technical details:
- Kernel implementation: See `kernel/PROCFS_NOTES.md`
- System design: See `docs/PHASE2_DESIGN.md`
- Progress tracking: See `current.md`
