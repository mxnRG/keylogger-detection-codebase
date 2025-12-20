# Linux Keylogger Detection System

> **Final Year Project - Linux Kernel Security**  
> A behavioral-based keylogger detection system for Linux using kernel modules and real-time monitoring

[![License: GPL v2](https://img.shields.io/badge/License-GPL%20v2-blue.svg)](https://www.gnu.org/licenses/old-licenses/gpl-2.0.en.html)
[![Kernel: 5.15.x](https://img.shields.io/badge/Kernel-5.15.x-orange.svg)]()
[![Platform: Ubuntu 22.04](https://img.shields.io/badge/Platform-Ubuntu%2022.04-red.svg)]()
[![Version](https://img.shields.io/badge/Kernel-v0.6-green.svg)]()
[![Version](https://img.shields.io/badge/GUI-v3.3-blue.svg)]()
[![Version](https://img.shields.io/badge/Daemon-v0.2-orange.svg)]()

## 🎯 Project Overview

This project implements a **keylogger detection system** that monitors keyboard activity at the kernel level to identify suspicious behavior patterns indicative of keylogging malware. 

**Key Principle:** We detect keyloggers through **behavioral analysis**, not by capturing keystrokes.

### What This Is
- ✅ A **detector** that identifies suspicious keyboard monitoring behavior
- ✅ Educational research project for academic purposes
- ✅ Demonstrates kernel-level security monitoring techniques

### What This Is NOT
- ❌ A keylogger or keystroke capture tool
- ❌ Production-ready security software
- ❌ A privacy-invasive surveillance system

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    KERNEL SPACE (v0.6)                      │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  Keyboard Notifier Hook (fyp_kbd.ko)                │   │
│  │  - Observes keyboard events (press/release)         │   │
│  │  - Collects behavioral metadata + cmdline           │   │
│  │  - Runtime-configurable thresholds (sysfs)          │   │
│  │  - Workqueue for safe process inspection            │   │
│  │  - NO keystroke content capture                     │   │
│  └──────────────────┬──────────────────────────────────┘   │
└─────────────────────┼──────────────────────────────────────┘
                      │
                      │ Netlink Socket (Protocol 31)
                      ▼
┌─────────────────────────────────────────────────────────────┐
│                   USER SPACE (v0.2 / v3.3)                  │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  Python Daemon (fyp_daemon.py)                      │   │
│  │  - Receives events via Netlink                      │   │
│  │  - Applies 3 heuristic detection rules              │   │
│  │  - Generates security alerts                        │   │
│  │  - Writes JSON status file                          │   │
│  └──────────────────┬──────────────────────────────────┘   │
│                     │                                       │
│                     │ File-based IPC (/tmp/fyp_status.json)│
│                     ▼                                       │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  Web Dashboard (Flask + WebSockets) (planned)       │   │
│  │  - Real-time activity visualization                 │   │
│  │  - Alert notifications                              │   │
│  │  - System status monitoring                         │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

## 🚀 Current Status

### ✅ Completed (Phase 1)

**Kernel Module (v0.3)** - Behavioral Observer
- Stable kernel module for Linux 5.15.x
- Keyboard notifier chain integration
- Behavioral metadata collection:
  - Event frequency and timing
  - Process context (PID, process name)
  - Inter-keystroke timing patterns
  - Rapid event detection (<10ms intervals)
- **Ethical design:** NO keycode or keystroke capture
- Clean compilation on Ubuntu 22.04 LTS

### ✅ Complete (Phase 2)

- [x] Kernel → Userspace communication (Netlink Protocol 31)
- [x] Python daemon v0.2 with 3 heuristic detection rules
- [x] Qt GUI v3.3 with responsive 2-column dashboard
- [x] Real-time resource monitoring (CPU/Memory tracking)
- [x] Runtime-configurable thresholds via sysfs parameters

### 🔬 Research Contributions

- [x] Behavioral fingerprinting without keystroke capture
- [x] Process-context attribution for keyboard events
- [x] Timing-based anomaly detection framework
- [x] Comprehensive ethical analysis and privacy safeguards

## 🛠️ Technical Stack

| Component | Technology |
|-----------|-----------|
| **OS** | Ubuntu 22.04 LTS |
| **Kernel** | Linux 5.15.x (GA kernel) |
| **Virtualization** | Oracle VirtualBox |
| **Kernel Module** | C (Loadable Kernel Module v0.6) |
| **Userspace Daemon** | Python 3.10+ (v0.2) |
| **GUI Framework** | PySide6 (Qt6 for Python) |
| **Resource Monitor** | psutil |
| **Communication** | Netlink sockets (Protocol 31) + JSON file IPC |

## 📦 Installation & Usage

### Prerequisites

```bash
# System dependencies (kernel headers and Qt6 libraries)
sudo apt update
sudo apt install linux-headers-$(uname -r) build-essential libxcb-cursor0 libnotify-bin python3-pip

# Python dependencies
pip3 install -r requirements.txt

# Verify kernel version (must be 5.15.x)
uname -r
```

### Python Dependencies

The project requires the following Python packages (see `requirements.txt`):

- **PySide6 >= 6.5.0** - Qt6 for Python (GUI framework)
  - Includes QtWidgets, QtCharts, QtCore, QtGui- **psutil >= 5.9.0** - System and process monitoring (resource usage tracking)
All other dependencies are part of Python's standard library (json, socket, threading, logging, etc.)

### Quick Start (Automated)

The easiest way to start the entire system:

```bash
# Run the unified start script (requires sudo)
./start.sh
```

This script will:
1. ✓ Load the kernel module (if not already loaded)
2. ✓ Start the daemon (if not already running)
3. ✓ Launch the GUI

### Manual Start (Step by Step)

If you prefer manual control:

#### 1. Build & Load Kernel Module

```bash
cd kernel/
make
sudo insmod fyp_kbd.ko

# Verify module loaded
lsmod | grep fyp_kbd
```

#### 2. Start Daemon

```bash
cd daemon/
./fyp_daemon.py &

# Check daemon is running
ps aux | grep fyp_daemon
```

#### 3. Launch GUI

```bash
cd gui/
./fyp_gui.py
```

### Runtime Configuration (Optional)

```bash
# View current thresholds
cat /sys/module/fyp_kbd/parameters/rapid_threshold_ms
cat /sys/module/fyp_kbd/parameters/burst_threshold_eps

# Tune thresholds dynamically (no module reload needed)
echo 100 | sudo tee /sys/module/fyp_kbd/parameters/rapid_threshold_ms
echo 150 | sudo tee /sys/module/fyp_kbd/parameters/burst_threshold_eps

# View updated configuration
cat /proc/fyp_detector/config
```

### Viewing Activity

```bash
# Check kernel module statistics
cat /proc/fyp_detector/stats

# View runtime configuration
cat /proc/fyp_detector/config

# View kernel logs (Netlink events)
sudo dmesg -w | grep fyp_detector

# View daemon logs (detection events)
tail -f /tmp/fyp_daemon.log

# Monitor GUI resource usage (in GUI dashboard)
# See "Resource Monitor" widget for real-time CPU/Memory
```

### Stopping the System

```bash
# Stop all components
pkill -f fyp_daemon.py
pkill -f fyp_gui.py
sudo rmmod fyp_kbd

# Or use the Makefile
cd kernel/
sudo make unload
```

## 🔍 Detection Methodology

### Behavioral Indicators (No Keystroke Content Required)

1. **Typing Speed Anomalies**
   - Rapid ratio >50% indicates automated/scripted input
   - Humans cannot sustain <10ms inter-key timing

2. **Process Behavior**
   - Unknown processes with keyboard event access
   - System processes with unexpected keyboard activity

3. **Statistical Patterns**
   - Perfectly regular timing (suggests automation)
   - Burst patterns inconsistent with human typing

4. **Contextual Anomalies**
   - Keyboard activity without active user session
   - Events during screen lock or off-hours

### Example: Detecting Automated Input

**Normal typing:**
```
[FYP]   Rapid events:    3
[FYP]   Rapid ratio:     2%
```

**Suspected keylogger/automated tool:**
```
[FYP]   Rapid events:    7,500
[FYP]   Rapid ratio:     75%
```

## 🛡️ Ethical Considerations

### Privacy-Preserving Design

**What we DON'T collect:**
- ❌ Keycodes (which key was pressed)
- ❌ Shift or modifier states  
- ❌ Key sequences or patterns
- ❌ Any data revealing typed content

**What we DO collect:**
- ✅ Event type (press/release only)
- ✅ Event timing (for pattern analysis)
- ✅ Process context (PID, process name)
- ✅ Statistical aggregates

**Why this matters:** A keylogger DETECTOR doesn't need to see keystrokes, only identify suspicious behavior patterns.

### Academic Use Only

This software is intended for:
- Educational research and learning
- Security awareness demonstrations
- Academic project evaluation

**NOT intended for:**
- Surveillance or monitoring others
- Production deployment without privacy review
- Use on systems without proper authorization

## 📚 Documentation

### Comprehensive Guides
- [`docs/KERNEL_MODULE.md`](docs/KERNEL_MODULE.md) - Kernel module architecture (Netlink, workqueue, sysfs)
- [`docs/DAEMON.md`](docs/DAEMON.md) - Detection daemon and heuristics
- [`docs/GUI.md`](docs/GUI.md) - Qt GUI responsive design and resource monitoring
- [`docs/ETHICS.md`](docs/ETHICS.md) - Privacy-by-design and responsible use
- [`docs/RESEARCH.md`](docs/RESEARCH.md) - Novel contributions and academic context
- [`docs/TESTING.md`](docs/TESTING.md) - Testing methodology and validation

### Quick References
- [`QUICKSTART.md`](QUICKSTART.md) - Quick setup guide
- [`current.md`](current.md) - Current development status

## 🧪 Testing

```bash
# Build and test the kernel module
cd kernel/
make clean
make
sudo insmod fyp_kbd.ko

# Type some keys in the terminal
# Then check logs
sudo dmesg | grep FYP | tail -10

# Unload and view statistics
sudo rmmod fyp_kbd
```

## 🤝 Contributing

This is an academic project for a Final Year Project. While not actively seeking contributions, feedback and suggestions are welcome through issues.

## 📄 License

This project is licensed under the GNU General Public License v2.0 - see the [LICENSE](LICENSE) file for details.

## ⚠️ Disclaimer

**FOR EDUCATIONAL PURPOSES ONLY**

This software is provided for academic research and educational purposes. Users are responsible for ensuring compliance with all applicable laws and regulations. The authors assume no liability for misuse of this software.

**Important:**
- Only use on systems you own or have explicit permission to monitor
- Understand and comply with privacy laws in your jurisdiction
- This is a prototype, not production-ready software
- No warranty or guarantee of fitness for any purpose

## 👨‍💻 Author

**FYP Team**  
Final Year Project - Linux Kernel Security  
Academic Year 2024-2025

## 🔗 Links

- GitHub Repository: [keylogger-detection-codebase](https://github.com/mxnRG/keylogger-detection-codebase)
- Documentation: See `/kernel` directory for detailed technical docs

---

**Last Updated:** December 20, 2025  
**Version:** Kernel v0.6 | Daemon v0.2 | GUI v3.3  
**Status:** Phase 1 Complete ✅ | Phase 2 Complete ✅
