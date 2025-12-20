# FYP Keylogger Detector - AI Agent Context

**Last Updated:** December 20, 2025  
**Project Status:** Phase 2 Complete ✅  
**Versions:** Kernel v0.6 | Daemon v0.2 | GUI v3.3

---

## Purpose of This Document

This file provides context for AI coding assistants (GitHub Copilot, Claude, GPT-4) to understand the project structure, current implementation state, and coding conventions. Use this as the authoritative reference for making informed suggestions and edits.

---

## Project Overview

### Mission Statement
A Linux-based **keylogger detection system** using behavioral analysis without capturing keystroke content. Privacy-preserving design identifies malicious keyboard monitoring software through timing patterns and process context.

### System Architecture

```
┌─────────────────────────────────────────────────┐
│         Kernel Space (v0.6)                     │
│  ┌──────────────────────────────────────────┐   │
│  │  Keyboard Notifier (keyboard_notifier_list) │
│  │  - Captures behavioral metadata          │   │
│  │  - NO keycode capture (privacy-by-design)│   │
│  │  - Timing analysis (<10ms = "rapid")     │   │
│  └──────────────┬───────────────────────────┘   │
│                 │                                │
│  ┌──────────────▼───────────────────────────┐   │
│  │  Workqueue Handler (system_wq)           │   │
│  │  - Deferred cmdline capture              │   │
│  │  - NULL-safe mm_struct access            │   │
│  │  - Graceful kernel thread handling       │   │
│  └──────────────┬───────────────────────────┘   │
│                 │                                │
│  ┌──────────────▼───────────────────────────┐   │
│  │  Netlink Socket (Protocol 31)            │   │
│  │  - 158-byte struct fyp_netlink_event     │   │
│  │  - PID, PPID, comm, cmdline[128]         │   │
│  │  - rapid_events, total_events, ratio     │   │
│  └──────────────┬───────────────────────────┘   │
│                 │                                │
│  ┌──────────────▼───────────────────────────┐   │
│  │  Sysfs Parameters (runtime config)       │   │
│  │  - rapid_threshold_ms (default: 50)      │   │
│  │  - burst_threshold_eps (default: 100)    │   │
│  └──────────────────────────────────────────┘   │
│                                                  │
│  ┌──────────────────────────────────────────┐   │
│  │  Procfs Interface (/proc/fyp_detector/)  │   │
│  │  - stats: Real-time statistics           │   │
│  │  - config: Current threshold values      │   │
│  └──────────────────────────────────────────┘   │
└─────────────────────────────────────────────────┘
                         │ Netlink Protocol 31
                         │ (158-byte events)
                         ↓
┌─────────────────────────────────────────────────┐
│         User Space - Daemon (v0.2)              │
│  ┌──────────────────────────────────────────┐   │
│  │  Netlink Socket Receiver                 │   │
│  │  - Registers NETLINK_FYP_DETECTOR        │   │
│  │  - Parses 158-byte events                │   │
│  │  - Timeout handling, disconnect detection│   │
│  └──────────────┬───────────────────────────┘   │
│                 │                                │
│  ┌──────────────▼───────────────────────────┐   │
│  │  Detection Engine (3 Heuristic Rules)    │   │
│  │  1. Rapid Typing: rapid_ratio > 50%      │   │
│  │  2. Unknown Process: not in whitelist    │   │
│  │  3. Burst Pattern: >100 events/sec       │   │
│  └──────────────┬───────────────────────────┘   │
│                 │                                │
│  ┌──────────────▼───────────────────────────┐   │
│  │  Status File Writer                      │   │
│  │  - Outputs /tmp/fyp_status.json          │   │
│  │  - Latest alert, process list            │   │
│  │  - Severity: LOW, MEDIUM, HIGH           │   │
│  └──────────────────────────────────────────┘   │
└─────────────────────────────────────────────────┘
                         │ JSON File IPC
                         │ (Polls every 500ms)
                         ↓
┌─────────────────────────────────────────────────┐
│         User Space - GUI (v3.3)                 │
│  ┌──────────────────────────────────────────┐   │
│  │  PySide6 (Qt6 for Python)                │   │
│  │  - GitHub dark theme (#0d1117, #1f6feb)  │   │
│  │  - Responsive 2-column layout (1280px)   │   │
│  └──────────────┬───────────────────────────┘   │
│                 │                                │
│  ┌──────────────▼───────────────────────────┐   │
│  │  Dashboard Pages (7 total)               │   │
│  │  1. Dashboard: Overview + resource monitor   │
│  │  2. Processes: Per-process metrics       │   │
│  │  3. Alerts: Detection timeline           │   │
│  │  4. Whitelist: Trusted processes         │   │
│  │  5. Logs: System event viewer            │   │
│  │  6. Settings: Configuration              │   │
│  │  7. About: Project info                  │   │
│  └──────────────┬───────────────────────────┘   │
│                 │                                │
│  ┌──────────────▼───────────────────────────┐   │
│  │  Resource Monitor Widget (psutil)        │   │
│  │  - Combined GUI + Daemon CPU/Memory      │   │
│  │  - 60-second history charts (QSplineSeries)  │
│  │  - Hover tooltip with breakdown          │   │
│  │  - Color-coded bars (blue/yellow/red)    │   │
│  │  - Updates every 1000ms                  │   │
│  └──────────────────────────────────────────┘   │
└─────────────────────────────────────────────────┘
```

---

## Critical Implementation Details

### Kernel Module (fyp_kbd.c) - v0.6

**File:** `/home/fyp/project/kernel/fyp_kbd.c`

**Key Structures:**
```c
struct fyp_netlink_event {
    u32 pid;
    u32 ppid;
    char process_name[16];
    char cmdline[128];        // NEW in v0.6
    u32 rapid_events;
    u32 total_events;
    u32 rapid_ratio;
};

struct cmdline_work {
    struct work_struct work;
    struct fyp_netlink_event event;
};
```

**Module Parameters (sysfs):**
```c
static int rapid_threshold_ms = 50;
static int burst_threshold_eps = 100;
module_param(rapid_threshold_ms, int, 0644);
module_param(burst_threshold_eps, int, 0644);
```

**Critical Functions:**
- `fyp_keyboard_notifier()` - Keyboard event callback (atomic context)
- `extract_cmdline()` - Safely captures command line with NULL checks
- `cmdline_work_handler()` - Workqueue handler for deferred processing
- `send_netlink_event()` - Sends 158-byte event via Netlink

**Workqueue Pattern:**
```c
work = kmalloc(sizeof(*work), GFP_ATOMIC);
INIT_WORK(&work->work, cmdline_work_handler);
schedule_work(&work->work);
```

**NULL-Safe mm_struct Access:**
```c
struct mm_struct *mm = get_task_mm(task);
if (!mm) {
    strcpy(cmdline, "[kernel]");
    return;
}
// ... safe access to mm->arg_start/arg_end
mmput(mm);
```

**Netlink Socket:**
- Protocol: 31 (`NETLINK_FYP_DETECTOR`)
- Group: 0 (unicast only)
- Message size: 158 bytes

**Procfs Files:**
- `/proc/fyp_detector/stats` - Real-time statistics
- `/proc/fyp_detector/config` - Current thresholds

---

### Daemon (fyp_daemon.py) - v0.2

**File:** `/home/fyp/project/daemon/fyp_daemon.py`

**Netlink Receiver:**
```python
import socket
import struct

NETLINK_FYP_DETECTOR = 31
sock = socket.socket(socket.AF_NETLINK, socket.SOCK_RAW, NETLINK_FYP_DETECTOR)
sock.bind((0, 0))  # PID 0 = kernel assigns, Group 0 = unicast

# Parse 158-byte events
fmt = '=II16s128sIII'  # PID, PPID, comm, cmdline, rapid, total, ratio
data = sock.recv(158)
pid, ppid, comm, cmdline, rapid, total, ratio = struct.unpack(fmt, data)
```

**Detection Rules:**
```python
def check_rapid_typing(rapid_ratio):
    return rapid_ratio > 50  # HIGH severity

def check_unknown_process(process_name, whitelist):
    return process_name not in whitelist  # MEDIUM severity

def check_burst_pattern(events_per_sec):
    return events_per_sec > 100  # HIGH severity
```

**Whitelist (Default):**
```python
WHITELIST = [
    'bash', 'zsh', 'fish',
    'python3', 'python',
    'vim', 'nano', 'emacs',
    'code', 'codium',
    'gnome-terminal', 'konsole', 'xterm'
]
```

**Status File Format:**
```json
{
    "timestamp": "2025-12-20T12:34:56",
    "latest_alert": {
        "severity": "HIGH",
        "rule": "Rapid Typing",
        "pid": 1234,
        "process": "bash",
        "cmdline": "/bin/bash",
        "rapid_ratio": 0.75
    },
    "processes": [
        {
            "pid": 1234,
            "name": "bash",
            "rapid_events": 750,
            "total_events": 1000,
            "rapid_ratio": 0.75
        }
    ]
}
```

---

### GUI (fyp_gui.py / main_gui.py) - v3.3

**File:** `/home/fyp/project/gui/fyp_gui.py` (main application logic)  
**Entry Point:** `/home/fyp/project/gui/main_gui.py` (imports and launches fyp_gui)

**Dependencies:**
```python
from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtCharts import *
import psutil  # Resource monitoring
import json
import os
from collections import deque
```

**Responsive Layout (Breakpoint: 1280px):**
```python
class FYPMainWindow(QMainWindow):
    def eventFilter(self, obj, event):
        if event.type() == QEvent.Resize:
            if self.width() > 1280:
                # Horizontal 2-column layout
                self.dashboard_layout = QHBoxLayout()
            else:
                # Vertical stacked layout
                self.dashboard_layout = QVBoxLayout()
```

**Resource Monitor Widget:**
```python
class ResourceMonitorWidget(QWidget):
    def __init__(self):
        self.cpu_history = deque(maxlen=60)  # 60-second window
        self.memory_history = deque(maxlen=60)
        
        # Progress bars (color-coded)
        self.cpu_bar = QProgressBar()
        self.memory_bar = QProgressBar()
        
        # History chart (QSplineSeries)
        self.chart = QChart()
        self.cpu_series = QSplineSeries()
        self.mem_series = QSplineSeries()
    
    def update_resources(self, gui_cpu, gui_mem, daemon_cpu, daemon_mem):
        combined_cpu = gui_cpu + daemon_cpu
        combined_mem = gui_mem + daemon_mem
        
        # Color-coded thresholds
        if combined_cpu < 20:
            self.cpu_bar.setStyleSheet("QProgressBar::chunk { background: #1f6feb; }")  # Blue
        elif combined_cpu < 50:
            self.cpu_bar.setStyleSheet("QProgressBar::chunk { background: #f9c513; }")  # Yellow
        else:
            self.cpu_bar.setStyleSheet("QProgressBar::chunk { background: #f85149; }")  # Red
```

**Resource Tracking (psutil):**
```python
def update_resource_usage(self):
    try:
        # GUI process
        gui_process = psutil.Process(self.gui_pid)
        gui_cpu = gui_process.cpu_percent()
        gui_mem = gui_process.memory_info().rss / (1024 * 1024)  # MB
        
        # Daemon process (discover PID if unknown)
        if not self.daemon_pid:
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                if 'fyp_daemon.py' in ' '.join(proc.info['cmdline'] or []):
                    self.daemon_pid = proc.info['pid']
                    break
        
        if self.daemon_pid:
            daemon_process = psutil.Process(self.daemon_pid)
            daemon_cpu = daemon_process.cpu_percent()
            daemon_mem = daemon_process.memory_info().rss / (1024 * 1024)
        else:
            daemon_cpu, daemon_mem = 0.0, 0.0
        
        # Update widget
        self.resource_widget.update_resources(gui_cpu, gui_mem, daemon_cpu, daemon_mem)
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        pass  # Graceful fallback
```

**Theme Colors:**
```python
# GitHub Dark Theme
BACKGROUND = "#0d1117"
ACCENT = "#1f6feb"
CARD_BG = "#161b22"
TEXT = "#c9d1d9"
TEXT_SECONDARY = "#8b949e"
BORDER = "#30363d"
SUCCESS = "#3fb950"
WARNING = "#f9c513"
DANGER = "#f85149"
```

---

## File Structure Reference

```
/home/fyp/project/
├── kernel/
│   ├── fyp_kbd.c          # v0.6 - Netlink + workqueue + sysfs
│   ├── Makefile
│   └── PROCFS_NOTES.md    # Legacy technical notes
├── daemon/
│   └── fyp_daemon.py      # v0.2 - Netlink receiver + 3 heuristics
├── gui/
│   ├── main_gui.py        # Entry point (imports fyp_gui)
│   ├── fyp_gui.py         # v3.3 - Responsive layout + resource monitor
│   ├── daemon_monitor.py  # Daemon status checker
│   ├── models.py          # Data models
│   ├── theme.py           # Color scheme definitions
│   ├── components/
│   │   ├── charts.py      # Chart widgets
│   │   └── widgets.py     # Reusable UI components
│   └── pages/
│       └── __init__.py
├── docs/
│   ├── KERNEL_MODULE.md   # Comprehensive kernel guide (15+ pages)
│   ├── DAEMON.md          # Daemon architecture (10+ pages)
│   ├── GUI.md             # GUI design doc (5 pages)
│   ├── ETHICS.md          # Privacy analysis (12+ pages)
│   ├── RESEARCH.md        # Academic contributions (15+ pages)
│   ├── TESTING.md         # Testing methodology (10+ pages)
│   ├── copilot_context.md # This file
│   └── archive/           # Historical docs (6 files)
├── requirements.txt       # PySide6>=6.5.0, psutil>=5.9.0
├── README.md              # Main project documentation
├── QUICKSTART.md          # Quick setup guide
└── current.md             # Phase 2 completion summary
```

---

## Coding Conventions

### Kernel Module (C)

**Naming:**
- Functions: `snake_case` with `fyp_` prefix (e.g., `fyp_keyboard_notifier`)
- Structures: `snake_case` (e.g., `struct fyp_netlink_event`)
- Module parameters: `snake_case` (e.g., `rapid_threshold_ms`)

**Memory Management:**
- Use `GFP_ATOMIC` for allocations in atomic context (keyboard notifier)
- Use `GFP_KERNEL` for workqueue handlers (sleeping context)
- Always pair `kmalloc()` with `kfree()`
- Always pair `get_task_mm()` with `mmput()`

**Error Handling:**
- Check return values of all kernel APIs
- Log errors with `pr_err()`, info with `pr_info()`
- Return `NOTIFY_OK` from keyboard notifier (never `NOTIFY_STOP`)

**Workqueue Pattern:**
```c
struct my_work {
    struct work_struct work;
    // ... payload
};

void handler(struct work_struct *work) {
    struct my_work *my_work = container_of(work, struct my_work, work);
    // ... process
    kfree(my_work);
}

// In atomic context:
struct my_work *work = kmalloc(sizeof(*work), GFP_ATOMIC);
INIT_WORK(&work->work, handler);
schedule_work(&work->work);
```

### Daemon (Python)

**Naming:**
- Functions: `snake_case` (e.g., `check_rapid_typing`)
- Classes: `PascalCase` (e.g., `DetectionEngine`)
- Constants: `UPPER_SNAKE_CASE` (e.g., `NETLINK_FYP_DETECTOR`)

**Error Handling:**
- Use `try/except` blocks for Netlink socket operations
- Log errors with `logging.error()`, info with `logging.info()`
- Graceful degradation on kernel module disconnect

**Threading:**
- Use `threading.Thread` for Netlink receiver (blocking socket)
- Use `threading.Lock` for shared data structures

### GUI (Python + Qt)

**Naming:**
- Classes: `PascalCase` (e.g., `FYPMainWindow`, `ResourceMonitorWidget`)
- Methods: `snake_case` (e.g., `update_resource_usage`)
- Signals/Slots: `camelCase` (Qt convention, e.g., `onButtonClicked`)

**Layout Pattern:**
```python
def create_page(self):
    widget = QWidget()
    layout = QVBoxLayout(widget)
    
    # Add components
    layout.addWidget(component1)
    layout.addWidget(component2)
    
    return widget
```

**Timer Pattern:**
```python
self.timer = QTimer(self)
self.timer.timeout.connect(self.update_function)
self.timer.start(1000)  # ms
```

**Chart Pattern:**
```python
chart = QChart()
series = QSplineSeries()
series.append(x, y)
chart.addSeries(series)
chart.createDefaultAxes()
chart_view = QChartView(chart)
```

---

## Development Workflow

### Building Kernel Module
```bash
cd /home/fyp/project/kernel
make clean
make
sudo insmod fyp_kbd.ko

# Verify
lsmod | grep fyp_kbd
dmesg | tail -5
```

### Running Daemon
```bash
cd /home/fyp/project/daemon
python3 fyp_daemon.py  # Foreground
python3 fyp_daemon.py &  # Background
```

### Running GUI
```bash
cd /home/fyp/project/gui
python3 main_gui.py
# or
./run_gui.sh
```

### Debugging

**Kernel Module:**
```bash
sudo dmesg -w | grep fyp_detector  # Live kernel logs
cat /proc/fyp_detector/stats       # Statistics
cat /proc/fyp_detector/config      # Current thresholds
```

**Daemon:**
```bash
tail -f /tmp/fyp_daemon.log        # Daemon logs
cat /tmp/fyp_status.json | jq      # Status file (formatted)
```

**GUI:**
```bash
# GUI logs to stdout/stderr when run from terminal
python3 main_gui.py 2>&1 | tee gui.log
```

---

## Common Tasks for AI Agents

### Adding a New Detection Rule

1. **Daemon:** Add rule logic to `fyp_daemon.py`
2. **Update documentation:** `docs/DAEMON.md` section on heuristics
3. **GUI:** Add visualization if needed (Alerts page)

### Tuning Thresholds

**Runtime (no code changes):**
```bash
echo 100 | sudo tee /sys/module/fyp_kbd/parameters/rapid_threshold_ms
```

**Default values (requires recompile):**
Edit `kernel/fyp_kbd.c`:
```c
static int rapid_threshold_ms = 100;  // Changed from 50
```

### Adding GUI Widgets

1. **Create widget class** in `gui/components/widgets.py`
2. **Integrate into page** in `gui/fyp_gui.py` (e.g., `create_dashboard_page()`)
3. **Add update logic** in timer callback
4. **Document in** `docs/GUI.md`

### Modifying Netlink Event Structure

1. **Kernel:** Update `struct fyp_netlink_event` in `kernel/fyp_kbd.c`
2. **Daemon:** Update `struct.unpack()` format string in `daemon/fyp_daemon.py`
3. **Document:** Update protocol specification in `docs/KERNEL_MODULE.md`

---

## Known Limitations & Workarounds

### 1. Procfs Circular Buffer (Legacy)
**Status:** Obsolete (migrated to Netlink in v0.5)  
**Historical Note:** v0.4 used `/proc/fyp_detector/events` with 10-event circular buffer

### 2. Daemon PID Discovery
**Issue:** Daemon PID unknown to GUI on startup  
**Workaround:** Search `psutil.process_iter()` for `fyp_daemon.py` in cmdline

### 3. VirtualBox Keyboard Passthrough
**Issue:** Some key events may be filtered by VirtualBox  
**Workaround:** Type in VM GUI terminal, not SSH or VSCode remote

### 4. Kernel Thread Handling
**Issue:** Kernel threads have no `mm_struct` (causes NULL pointer)  
**Solution:** NULL check in `extract_cmdline()`, fallback to `"[kernel]"`

---

## Testing Commands

### Unit Tests (Kernel Module)
```bash
cd /home/fyp/project/kernel
sudo insmod fyp_kbd.ko
cat /proc/fyp_detector/stats  # Should show zeros initially
# Type 10 keys
cat /proc/fyp_detector/stats  # Should show total_events=10
sudo rmmod fyp_kbd
```

### Integration Test (End-to-End)
```bash
# Terminal 1: Load kernel
cd kernel && sudo insmod fyp_kbd.ko

# Terminal 2: Start daemon
cd daemon && python3 fyp_daemon.py

# Terminal 3: Start GUI
cd gui && python3 main_gui.py

# Terminal 4: Generate test input
yes | head -100  # Should trigger Burst Pattern alert in GUI
```

### Performance Test
```bash
# Monitor CPU usage
top -p $(pgrep fyp_daemon) -p $(pgrep python | head -1)

# Generate high-throughput events
for i in {1..1000}; do echo "test"; done

# Check event processing latency
sudo dmesg | grep "fyp_detector" | tail -20
```

---

## Version History

| Version | Date | Component | Key Changes |
|---------|------|-----------|-------------|
| v0.4 | Dec 1, 2025 | Kernel | Initial procfs implementation |
| v0.5 | Dec 10, 2025 | Kernel | Migrated to Netlink sockets |
| v0.6 | Dec 17-18, 2025 | Kernel | Sysfs parameters + workqueue cmdline |
| v0.1 | Dec 12, 2025 | Daemon | Procfs event reader + 3 heuristics |
| v0.2 | Dec 12, 2025 | Daemon | Netlink receiver |
| v0.1 | Dec 15, 2025 | GUI | Qt6 initial release |
| v3.3 | Dec 19-20, 2025 | GUI | Responsive layout + resource monitor |

---

## AI Agent Guidelines

1. **Always check version numbers** before suggesting changes (current: v0.6 / v0.2 / v3.3)
2. **Netlink is the IPC mechanism** (not procfs events file)
3. **Workqueue is mandatory** for mm_struct access (kernel notifier is atomic context)
4. **NULL-check mm_struct** (kernel threads return NULL from `get_task_mm()`)
5. **Use psutil for resource monitoring** (with graceful fallback if unavailable)
6. **Responsive layout breakpoint is 1280px** (horizontal >1280px, vertical <1280px)
7. **Color thresholds:** Blue <20%, Yellow 20-50%, Red >50%
8. **Documentation is comprehensive** - refer agents to `docs/` for detailed technical specs
9. **Privacy-by-design:** NEVER suggest capturing keycodes or keystroke content
10. **Test on Ubuntu 22.04 LTS** with Linux 5.15.0-164-generic (VirtualBox VM)

---

## Quick Reference: File Paths

| What | Where |
|------|-------|
| Kernel module source | `/home/fyp/project/kernel/fyp_kbd.c` |
| Kernel module binary | `/home/fyp/project/kernel/fyp_kbd.ko` |
| Daemon script | `/home/fyp/project/daemon/fyp_daemon.py` |
| GUI entry point | `/home/fyp/project/gui/main_gui.py` |
| GUI main logic | `/home/fyp/project/gui/fyp_gui.py` |
| Requirements file | `/home/fyp/project/requirements.txt` |
| Procfs stats | `/proc/fyp_detector/stats` |
| Procfs config | `/proc/fyp_detector/config` |
| Sysfs rapid threshold | `/sys/module/fyp_kbd/parameters/rapid_threshold_ms` |
| Sysfs burst threshold | `/sys/module/fyp_kbd/parameters/burst_threshold_eps` |
| Status file | `/tmp/fyp_status.json` |
| Daemon log | `/tmp/fyp_daemon.log` |

---

**End of Context Document**  
**For questions, refer to comprehensive guides in `/home/fyp/project/docs/`**
