# Phase 2 Implementation Order

## Overview
Build userspace components in logical dependency order.

---

## Step 1: Kernel Module Procfs Interface (v0.4)
**Estimated time:** 2-3 hours  
**File:** `kernel/fyp_kbd.c`

### Tasks:
1. [ ] Add circular buffer for events
2. [ ] Implement `/proc/fyp_detector/events` read handler
3. [ ] Implement `/proc/fyp_detector/stats` read handler
4. [ ] Implement `/proc/fyp_detector/control` write handler
5. [ ] Test with `cat /proc/fyp_detector/events`
6. [ ] Test with `cat /proc/fyp_detector/stats`

### Testing:
```bash
# Build and load
cd kernel/
make clean && make
sudo insmod fyp_kbd.ko

# Verify procfs created
ls -la /proc/fyp_detector/

# Read stats
cat /proc/fyp_detector/stats

# Type some keys, then tail events
tail -f /proc/fyp_detector/events

# Test control
echo "reset" | sudo tee /proc/fyp_detector/control
cat /proc/fyp_detector/stats  # Should show zeros

# Unload
sudo rmmod fyp_kbd
```

---

## Step 2: Python Daemon (Minimal)
**Estimated time:** 2-3 hours  
**File:** `daemon/fyp_daemon.py`

### Tasks:
1. [ ] Create daemon directory structure
2. [ ] Implement ProcessStats dataclass
3. [ ] Implement event parsing
4. [ ] Implement event reader thread
5. [ ] Add basic logging
6. [ ] Test reading from procfs

### Testing:
```bash
# Ensure kernel module loaded
sudo insmod kernel/fyp_kbd.ko

# Run daemon
python3 daemon/fyp_daemon.py

# Type keys in another terminal
# Watch daemon logs for events

# Ctrl+C to stop
```

---

## Step 3: Detection Engine
**Estimated time:** 1-2 hours  
**File:** `daemon/fyp_daemon.py` (add DetectionEngine)

### Tasks:
1. [ ] Implement Rapid Typing rule
2. [ ] Implement Unknown Process rule
3. [ ] Implement Burst Pattern rule
4. [ ] Define process whitelist
5. [ ] Test with normal typing
6. [ ] Test with simulated automated input

### Testing:
```bash
# Normal typing test
python3 daemon/fyp_daemon.py
# Type normally → Should see few/no alerts

# Automated test (simulate rapid input)
# Use a script or key-repeat to trigger alerts
```

---

## Step 4: Qt GUI (Minimal)
**Estimated time:** 3-4 hours  
**File:** `gui/fyp_gui.py`

### Tasks:
1. [ ] Install PySide6: `pip3 install PySide6`
2. [ ] Create basic window layout
3. [ ] Add event list widget
4. [ ] Add alerts panel
5. [ ] Add process table
6. [ ] Add status indicators
7. [ ] Test GUI alone (with mock data)

### Testing:
```bash
# Install Qt
pip3 install PySide6

# Run GUI standalone
python3 gui/fyp_gui.py

# Should see window, even without data
```

---

## Step 5: Daemon ↔ GUI Communication
**Estimated time:** 2-3 hours  
**Files:** `daemon/fyp_daemon.py`, `gui/fyp_gui.py`

### Options:
**A) Simple File-based IPC** (Easiest)
- Daemon writes JSON to `/tmp/fyp_status.json`
- GUI reads file periodically

**B) Unix Socket** (Better)
- Daemon creates socket at `/tmp/fyp_daemon.sock`
- GUI connects and receives updates

**C) D-Bus** (Most proper, but complex)
- Use system message bus
- Requires more setup

**Recommendation:** Start with **Option A (File-based)** for prototype

### Tasks:
1. [ ] Daemon: Write status to `/tmp/fyp_status.json` every second
2. [ ] GUI: Read file on timer (500ms)
3. [ ] GUI: Parse JSON and update widgets
4. [ ] Test integration

### Testing:
```bash
# Terminal 1: Kernel module
sudo insmod kernel/fyp_kbd.ko

# Terminal 2: Daemon
python3 daemon/fyp_daemon.py

# Terminal 3: GUI
python3 gui/fyp_gui.py

# Type keys → Should see in GUI
```

---

## Step 6: Polish & Demo Preparation
**Estimated time:** 2-3 hours

### Tasks:
1. [ ] Add color coding (green/yellow/red for risk levels)
2. [ ] Add "Flag Process" button functionality
3. [ ] Add friendly awareness messages
4. [ ] Create demo scenarios:
   - Normal typing (low alerts)
   - Automated script (high alerts)
   - Unknown process (medium alert)
5. [ ] Create demo video/screenshots
6. [ ] Update documentation

### Demo Scenarios:

**Scenario 1: Normal Use**
```bash
# Just type normally in terminal
# Should show:
# - Green status
# - Low rapid ratio
# - No alerts
```

**Scenario 2: Automated Keylogger Simulation**
```bash
# Create test script that reads keyboard rapidly
# tools/simulate_keylogger.sh
# Should trigger:
# - High rapid ratio alert
# - Burst pattern alert
# - Red status
```

**Scenario 3: Unknown Process**
```bash
# Run a renamed Python script
cp daemon/fyp_daemon.py /tmp/mystery_app.py
python3 /tmp/mystery_app.py
# Should trigger:
# - Unknown process alert
# - Yellow status
```

---

## Estimated Total Time: 12-18 hours

**Breakdown:**
- Kernel procfs: 2-3h
- Daemon basic: 2-3h
- Detection engine: 1-2h
- GUI basic: 3-4h
- Integration: 2-3h
- Polish/demo: 2-3h

---

## Recommended Order for Single Day

### Morning (4 hours):
1. Kernel procfs interface (2h)
2. Python daemon skeleton (2h)

**Checkpoint:** Can read events from kernel in Python ✓

### Afternoon (4 hours):
3. Detection engine (1.5h)
4. Qt GUI basic layout (2.5h)

**Checkpoint:** GUI displays, daemon detects ✓

### Evening (3 hours):
5. Integration (1.5h)
6. Polish & demo prep (1.5h)

**Checkpoint:** Full prototype demo-ready ✓

---

## Quick Start Commands

```bash
# Create directory structure
mkdir -p daemon/ gui/ tools/

# Install dependencies
sudo apt install python3-pip
pip3 install PySide6

# Build kernel module v0.4
cd kernel/
make clean && make
sudo insmod fyp_kbd.ko

# Verify procfs
ls -la /proc/fyp_detector/
cat /proc/fyp_detector/stats

# Run daemon
cd ../daemon/
python3 fyp_daemon.py &

# Run GUI
cd ../gui/
python3 fyp_gui.py

# Type keys and watch detection!
```

---

## Troubleshooting

### Procfs not appearing
```bash
# Check module loaded
lsmod | grep fyp_kbd

# Check dmesg for errors
dmesg | grep FYP

# Reload module
sudo rmmod fyp_kbd
sudo insmod fyp_kbd.ko
```

### Daemon can't read procfs
```bash
# Check permissions
ls -la /proc/fyp_detector/events

# Try with sudo (shouldn't be needed)
sudo python3 daemon/fyp_daemon.py
```

### GUI not updating
```bash
# Check if daemon is running
ps aux | grep fyp_daemon

# Check if status file exists
ls -la /tmp/fyp_status.json
cat /tmp/fyp_status.json

# Check GUI logs
# Add print() statements in update_display()
```

---

Ready to start implementation!
