# FYP Keylogger Detection System - Quick Start Guide

**Version:** Kernel v0.6 | Daemon v0.2 | GUI v3.3  
**Date:** December 20, 2025

## System Overview

This project implements a real-time keylogger detection system for Linux:
- **Kernel Module** (v0.6): Captures keyboard behavioral metadata via keyboard notifier, sends events via Netlink socket (Protocol 31), runtime-configurable via sysfs parameters
- **Python Daemon** (v0.2): Receives Netlink events, applies 3 heuristic detection rules, writes status to JSON file
- **Qt GUI** (v3.3): Responsive 2-column dashboard with real-time resource monitoring (CPU/Memory tracking)

## Prerequisites

### 1. Install Dependencies
```bash
# Install build tools for kernel module
sudo apt update
sudo apt install build-essential linux-headers-$(uname -r)

# Install Python and Qt dependencies
sudo apt install python3 python3-pip
pip3 install PySide6 psutil  # Qt GUI framework + resource monitoring
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
dmesg | tail -5
```

Expected output:
```
/proc/fyp_detector/
├── config   (runtime threshold configuration)
└── stats    (real-time statistics)

[fyp_detector] Netlink socket created (Protocol 31)
[fyp_detector] Keyboard notifier registered
```

**Optional: Runtime Threshold Tuning**
```bash
# View current thresholds
cat /sys/module/fyp_kbd/parameters/rapid_threshold_ms  # Default: 50
cat /sys/module/fyp_kbd/parameters/burst_threshold_eps # Default: 100

# Adjust thresholds (no module reload needed)
echo 100 | sudo tee /sys/module/fyp_kbd/parameters/rapid_threshold_ms
echo 150 | sudo tee /sys/module/fyp_kbd/parameters/burst_threshold_eps

# Verify changes
cat /proc/fyp_detector/config
```

### Step 2: Start the Daemon
Open a **new terminal** (keep module loaded):
```bash
cd /home/fyp/project/daemon
python3 fyp_daemon.py
```

Expected output:
```
[HH:MM:SS] INFO: FYP Keylogger Detection Daemon v0.2
[HH:MM:SS] INFO: Registering Netlink socket (Protocol 31)...
[HH:MM:SS] INFO: ✓ Connected to kernel detector via Netlink
[HH:MM:SS] INFO: Daemon running. Press Ctrl+C to stop.
[HH:MM:SS] INFO: Received event: PID=1234 comm=bash cmdline=/bin/bash rapid_events=5 total_events=150
```

### Step 3: Start the GUI
Open a **third terminal** (keep daemon running):
```bash
cd /home/fyp/project/gui
chmod +x run_gui.sh
./run_gui.sh
```

The Qt GUI window should open showing:
- 🟢Responsive Dashboard**: 2-column layout (>1280px) or stacked (<1280px)
- **Resource Monitor Widget**: Real-time GUI + Daemon CPU/Memory tracking with 60s history charts
- **Alerts Tab**: Real-time security alerts
- **Processes Tab**: Per-process behavioral metrics
- **Event Stream Tab**: Detailed detection metrics
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
# View runtime configuration
cat /proc/fyp_detector/config

# View kernel statistics
cat /proc/fyp_detector/stats

# View Netlink events in real-time
sudo dmesg -w | grep fyp_detector

# Tune thresholds dynamically
echo 100 | sudo tee /sys/module/fyp_kbd/parameters/rapid_threshold_ms
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
│   ├── fyp_kbd.c          # Kernel module source (v0.6 - Netlink + workqueue)
│   ├── Makefile           # Build configuration
│   └── PROCFS_NOTES.md    # Legacy technical notes
├── daemon/
│   └── fyp_daemon.py      # Detection daemon (v0.2 - Netlink receiver)
├── gui/
│   ├── fyp_gui.py         # Qt GUI application (v3.3 - responsive + resource monitor)
│   └── run_gui.sh         # Launch script
├── docs/
│   ├── KERNEL_MODULE.md   # Comprehensive kernel module guide
│   ├── DAEMON.md          # Daemon architecture and heuristics
│   ├── GUI.md             # GUI design and resource monitoring
│   ├── ETHICS.md          # Privacy-by-design and responsible use
│   ├── RESEARCH.md        # Novel contributions and literature review
│   ├── TESTING.md         # Testing methodology
│   └── archive/           # Historical documentation
├── requirements.txt       # Python dependencies (PySide6, psutil)
├── current.md             # Project status
└── QUICKSTART.md          # This file
```

## Next Steps

- **Runtime Tuning**: Experiment with sysfs threshold parameters
- **Demo Scenarios**: Test different input patterns (see `docs/TESTING.md`)
- **Resource Monitoring**: Observe GUI and daemon CPU/Memory usage under load
- **Documentation**: Review comprehensive guides in `docs/` directory

## Support

For technical details:
- Kernel architecture: See `docs/KERNEL_MODULE.md` (Netlink, workqueue, sysfs)
- Detection heuristics: See `docs/DAEMON.md` (3 detection rules)
- GUI features: See `docs/GUI.md` (responsive design, resource monitoring)
- Ethical considerations: See `docs/ETHICS.md`
- Progress tracking: See `current.md`
