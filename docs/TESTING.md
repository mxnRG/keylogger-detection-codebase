# Testing Methodology

**FYP Keylogger Detection System - Testing Documentation**

## Overview

This document outlines testing procedures for validating the keylogger detection system across kernel module, daemon, and GUI components.

---

## Test Environment

### Hardware
- **CPU**: Intel Core i5-8250U (or equivalent)
- **RAM**: 8 GB minimum
- **Storage**: 20 GB available

### Software
- **OS**: Ubuntu 22.04 LTS
- **Kernel**: 5.15.0-164-generic
- **Python**: 3.10+

---

## Unit Tests

### Kernel Module Tests

#### Test 1: Module Loading
```bash
cd /home/fyp/project/kernel
make clean && make
sudo insmod fyp_kbd.ko
lsmod | grep fyp_kbd
# Expected: fyp_kbd module listed
sudo rmmod fyp_kbd
```

#### Test 2: Netlink Socket Creation
```bash
sudo insmod fyp_kbd.ko
sudo dmesg | grep "Netlink socket created"
# Expected: "Netlink socket created (protocol 31)"
```

#### Test 3: Runtime Configuration
```bash
cat /sys/module/fyp_kbd/parameters/rapid_threshold_ms
# Expected: 50

echo 100 > /sys/module/fyp_kbd/parameters/rapid_threshold_ms
cat /sys/module/fyp_kbd/parameters/rapid_threshold_ms
# Expected: 100
```

#### Test 4: Statistics Tracking
```bash
cat /proc/fyp_detector/stats
# Type some keys
cat /proc/fyp_detector/stats
# Expected: total_events increased
```

### Daemon Tests

#### Test 5: Daemon Startup
```bash
cd /home/fyp/project/daemon
python3 fyp_daemon.py &
sleep 2
pgrep -f fyp_daemon.py
# Expected: PID displayed
```

#### Test 6: Status File Creation
```bash
ls -l /tmp/fyp_status.json
# Expected: File exists with recent timestamp
cat /tmp/fyp_status.json | python3 -m json.tool
# Expected: Valid JSON output
```

#### Test 7: Netlink Registration
```bash
sudo dmesg | grep "Daemon registered"
# Expected: "Daemon registered (PID XXXX)"
```

### GUI Tests

#### Test 8: GUI Startup
```bash
cd /home/fyp/project/gui
python3 main_gui.py &
# Expected: Window opens without errors
```

#### Test 9: Resource Monitoring
```python
# In Python console
import psutil
print(psutil.Process(<gui_pid>).memory_info())
# Expected: <50 MB memory usage
```

---

## Integration Tests

### Test 10: End-to-End Event Flow

**Procedure**:
1. Load kernel module
2. Start daemon
3. Launch GUI
4. Type 20 keystrokes in terminal
5. Observe GUI dashboard

**Expected**:
- Event count increases by ~40 (20 press + 20 release)
- Event rate chart shows spike
- Process bar chart shows `bash` or terminal process

### Test 11: Alert Generation

**Setup**: Create simple keylogger simulator
```python
# test_keylogger.py
import evdev
import time

device = evdev.InputDevice('/dev/input/event2')  # Adjust event number
count = 0
for event in device.read_loop():
    if event.type == evdev.ecodes.EV_KEY:
        count += 1
        print(f"Event {count}")
        if count > 100:
            break
```

**Procedure**:
1. Run system (kernel + daemon + GUI)
2. Execute `sudo python3 test_keylogger.py`
3. Type rapidly in terminal
4. Check GUI Alerts page

**Expected**:
- HIGH alert: "Rapid Input Stream Access"
- HIGH alert: "Burst Pattern - Automated Input"
- Process listed: `python3` with high event rate

---

## Performance Benchmarks

### Test 12: CPU Overhead

**Procedure**:
```bash
# Measure baseline
top -b -n 1 | grep "Cpu(s)"

# Load system
sudo insmod fyp_kbd.ko
python3 /home/fyp/project/daemon/fyp_daemon.py &
python3 /home/fyp/project/gui/main_gui.py &

# Measure with system running
top -b -n 60 -d 1 | grep "Cpu(s)" | awk '{print $2}' | sed 's/%us,//' > /tmp/cpu_usage.txt

# Calculate average
awk '{s+=$1; c++} END {print s/c}' /tmp/cpu_usage.txt
```

**Expected**: <2% combined CPU usage during normal operation

### Test 13: Event Processing Rate

**Procedure**:
```bash
# Generate high event rate
xdotool key --repeat 1000 --delay 1 a

# Check daemon logs
tail -f /tmp/fyp_daemon.log

# Check kernel stats
cat /proc/fyp_detector/stats
```

**Expected**:
- No dropped_events (or minimal)
- Daemon processes 1000 events
- GUI remains responsive

### Test 14: Memory Usage

**Procedure**:
```bash
# Run for 10 minutes, monitor memory
watch -n 10 "ps aux | grep -E 'fyp_(daemon|gui)'"
```

**Expected**:
- Daemon: <20 MB stable
- GUI: <50 MB stable
- No memory leaks (stable over time)

---

## Demo Scenarios

### Scenario 1: Legitimate Typing

**Setup**: Normal user typing in terminal

**Actions**:
1. Open terminal
2. Type: `echo "Hello World"`
3. Observe dashboard

**Expected**:
- Event rate: 2-10 eps
- Rapid ratio: <10%
- No alerts
- Process: `bash` (whitelisted)

### Scenario 2: Fast Automation Tool

**Setup**: Use `xdotool` for automated typing

**Actions**:
```bash
xdotool type --delay 10 "This is automated typing for testing"
```

**Expected**:
- Event rate: 50-100 eps
- Rapid ratio: 30-50%
- MEDIUM alert: "Unknown Process" (if xdotool not whitelisted)
- Can be whitelisted to remove alert

### Scenario 3: Malicious Keylogger

**Setup**: Custom Python keylogger

**Actions**:
```python
# malicious_logger.py
import evdev
device = evdev.InputDevice('/dev/input/event2')
with open('/tmp/keylog.txt', 'w') as f:
    for event in device.read_loop():
        if event.type == evdev.ecodes.EV_KEY:
            f.write(f"{event.code}\n")
            f.flush()
```

```bash
sudo python3 malicious_logger.py &
# Type in any application
```

**Expected**:
- Event rate: 100-500 eps
- Rapid ratio: 60-90%
- HIGH alerts: "Rapid Input Stream Access" + "Burst Pattern"
- Process: `python3` (unknown, not whitelisted)

---

## Responsive Layout Tests

### Test 15: Window Resize

**Procedure**:
1. Launch GUI
2. Go to Dashboard
3. Resize window width from 1920px → 1280px → 800px
4. Observe layout changes

**Expected**:
- At 1280px+: 2-column horizontal layout
- Below 1280px: Single-column stacked layout
- No layout breaking or overlapping widgets

---

## False Positive Tests

### Test 16: Screen Recording Software

**Setup**: Use OBS Studio or similar

**Actions**:
1. Start OBS recording
2. Type normally
3. Check for alerts

**Expected Result**: May trigger "Unknown Process" alert

**Mitigation**: Add OBS to whitelist

### Test 17: Accessibility Tools

**Setup**: On-screen keyboard

**Actions**:
1. Launch `onboard` (GNOME on-screen keyboard)
2. Use on-screen keyboard to type
3. Check for alerts

**Expected Result**: May trigger "Rapid Input" or "Burst" alerts

**Mitigation**: Add to whitelist in daemon

---

## Regression Tests

### Test 18: Kernel Module Reload

```bash
# Load, unload, reload cycle
sudo insmod fyp_kbd.ko
sleep 5
sudo rmmod fyp_kbd
sleep 2
sudo insmod fyp_kbd.ko
# Check for errors in dmesg
sudo dmesg | tail -20
```

**Expected**: No kernel panics, clean load/unload

### Test 19: Daemon Restart

```bash
# Kill and restart daemon
pkill -f fyp_daemon.py
sleep 2
python3 /home/fyp/project/daemon/fyp_daemon.py &
sleep 2
# Check registration
sudo dmesg | grep "Daemon registered"
```

**Expected**: Clean restart, re-registration with kernel

---

## Stress Tests

### Test 20: Sustained High Load

**Procedure**:
```bash
# Generate 10,000 events
for i in {1..1000}; do
    xdotool key a
    sleep 0.01
done
```

**Expected**:
- System remains responsive
- No crashes
- Statistics accurately reflect event count

---

## Validation Checklist

### Pre-Release Validation

- [ ] Kernel module compiles without warnings
- [ ] Module loads and unloads cleanly
- [ ] Netlink communication works bidirectionally
- [ ] Runtime parameters are tunable via sysfs
- [ ] Daemon starts and registers with kernel
- [ ] Status file is created and updated
- [ ] GUI launches without errors
- [ ] All 7 pages are navigable
- [ ] Resource monitoring displays correctly
- [ ] Responsive layout works at 1920px, 1280px, 1024px
- [ ] Alerts are generated for test keylogger
- [ ] False positives are manageable
- [ ] CPU overhead <2%
- [ ] Memory usage stable
- [ ] No memory leaks after 1 hour
- [ ] System tray icon works
- [ ] Desktop notifications work

---

## Bug Reporting Template

```
**Component**: [Kernel / Daemon / GUI]
**Version**: [0.6 / 0.2 / 3.3]
**OS**: Ubuntu 22.04 LTS
**Kernel**: 5.15.0-164-generic

**Steps to Reproduce**:
1. 
2. 
3. 

**Expected Behavior**:

**Actual Behavior**:

**Logs**:
- Kernel: `dmesg | tail -50`
- Daemon: `cat /tmp/fyp_daemon.log`
- GUI: `cat /tmp/fyp_gui.log`

**System Info**:
- CPU usage: `top -b -n 1`
- Memory: `free -h`
- Processes: `ps aux | grep fyp`
```

---

**Version**: 1.0  
**Last Updated**: December 20, 2025  
**Test Coverage**: Kernel (8 tests), Daemon (3 tests), GUI (3 tests), Integration (11 tests)
