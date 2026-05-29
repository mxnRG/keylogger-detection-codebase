# FYP Keylogger Detector - AI Agent Context

**Last Updated:** May 29, 2026  
**Project Status:** Phase 3 — ML on fixed telemetry dataset  
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
│  │  - Timing analysis (<50ms = "rapid")     │   │
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
│  │  - timestamp_ns, pid, comm, cmdline[128] │   │
│  │  - event_type, rapid_flag                │   │
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
│  │  - Parses 30-byte subset (no cmdline)    │   │
│  │  - Blocking receive loop + error logging │   │
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
│  │  - Alerts list + processes dict          │   │
│  │  - Severity: MEDIUM, HIGH (current rules)│   │
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
│  │  - Stacked rows layout (stats/charts/resources) │   │
│  └──────────────┬───────────────────────────┘   │
│                 │                                │
│  ┌──────────────▼───────────────────────────┐   │
│  │  Dashboard Pages (7 total)               │   │
│  │  1. Dashboard: Overview + resource monitor   │
│  │  2. Alerts: Detection timeline           │   │
│  │  3. Processes: Per-process metrics       │   │
│  │  4. Event Stream: Raw event log          │   │
│  │  5. AI Assistant: Placeholder            │   │
│  │  6. ML Insights: Placeholder             │   │
│  │  7. Configuration: Threshold + controls  │   │
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
    u64 timestamp_ns;        // Nanoseconds since boot
    u32 pid;
    char comm[16];           // TASK_COMM_LEN
    char cmdline[128];
    u8 event_type;           // 0=press, 1=release
    u8 rapid_flag;           // 1 if rapid
};

struct cmdline_work {
    struct work_struct work;
    pid_t pid;
    char comm[TASK_COMM_LEN];
    u64 timestamp_ns;
    u8 event_type;
    u8 rapid_flag;
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
- `netlink_send_event()` - Sends 158-byte event via Netlink

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
- Message size: 158 bytes (daemon currently parses 30-byte subset)

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
import os

NETLINK_FYP_DETECTOR = 31
sock = socket.socket(socket.AF_NETLINK, socket.SOCK_RAW, NETLINK_FYP_DETECTOR)
sock.bind((os.getpid(), 0))  # Unicast

# Parse 30-byte event subset (cmdline ignored in current daemon)
fmt = '<QI16sBB'  # timestamp_ns, pid, comm, event_type, rapid_flag
data = sock.recv(4096)
payload = data[16:16 + 30]
timestamp_ns, pid, comm, event_type, rapid_flag = struct.unpack(fmt, payload)
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
WHITELIST = {
    'gnome-shell', 'Xorg', 'gdm-x-session',
    'bash', 'sh', 'zsh', 'fish',
    'python3', 'python', 'code', 'firefox',
    'gnome-terminal', 'konsole', 'xterm',
    'vim', 'nano', 'emacs',
    'swapper/0', 'swapper/1', 'swapper/2', 'swapper/3'
}
```

**Status File Format:**
```json
{
    "timestamp": "2026-05-22T12:34:56.123456",
    "daemon_running": true,
    "kernel_loaded": true,
    "total_events": 5432,
    "processes": {
        "1913": {
            "comm": "gnome-shell",
            "total_events": 2500,
            "rapid_ratio": 2.0,
            "events_per_second": 4.5
        }
    },
    "alerts": [
        {
            "timestamp": "2026-05-22T12:34:50.000000",
            "severity": "HIGH",
            "message": "Rapid Input Stream Access: Rapid fetching ratio: 80.0% (threshold: 50.0%)",
            "process": "suspicious",
            "pid": 2048
        }
    ],
    "recent_events": [
        "123456789,P,2048,suspicious,1"
    ]
}
```

---

### GUI (fyp_gui.py / main_gui.py) - v3.3

**File:** `/home/fyp/project/gui/fyp_gui.py` (main application logic)  
**Entry Point:** `/home/fyp/project/gui/main_gui.py` (imports and launches fyp_gui)

**Note:** The `components/` and `pages/` packages exist but are not wired into `fyp_gui.py` yet. The GUI currently defines its widgets and pages inline.

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

**Dashboard Layout:**
- Current build uses stacked rows (stats, charts, resources)
- Responsive 2-column switching is not wired in the active dashboard layout

**Resource Monitor Widget:**
```python
class ResourceMonitorWidget(QGroupBox):
    def update_resources(self, total_cpu, total_mem, gui_cpu, gui_mem,
                         daemon_cpu, daemon_mem, cpu_history, mem_history):
        # Update totals and color-coded CPU bar
        # Update chart history (60 seconds)
        # Provide hover tooltip with GUI/daemon breakdown
        pass
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
        
        total_cpu = gui_cpu + daemon_cpu
        total_mem = gui_mem + daemon_mem

        # Update widget
        self.resource_widget.update_resources(
            total_cpu, total_mem,
            gui_cpu, gui_mem,
            daemon_cpu, daemon_mem,
            list(self.cpu_history),
            list(self.memory_history)
        )
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

## ML Pipeline (Phase 3)

### Dataset

- **Location:** `dataset/manifest.yaml` → L2–L4 Linux eBPF CSVs (~94k rows)
- **Constraint:** One benign + one malicious file per level; different capture VMs
- **Do not use:** `Data/combined/all_levels_ebpf_keylogger.csv` (malicious-only)

### Evaluation tiers (`evaluation.json`)

| Tier | Split | Use in thesis |
|------|-------|---------------|
| A | Per-level row stratified | Upper bound only (~1.0 AUC) |
| B | Cross-level holdout | Secondary (~1.0 AUC — signal generalizes) |
| C | Cross-level + behavioral features | **Primary realistic metric** (0.75–0.99 AUC) |

### Key scripts

```bash
python scripts/train_ml.py --split-mode all --feature-policy standard
python scripts/analyze_dataset.py
python scripts/verify_artifacts.py
```

### Resume after SSH disconnect

Read `docs/SESSION_RESUME.md` and `docs/ML_DATASET_REALISTIC_EVAL_PLAN.md` first.

### Latest artifact run

`artifacts/run_20260529_193015/evaluation.json`

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
│   ├── fyp_gui.py         # v3.3 - Dashboard + resource monitor
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
│   ├── ML_DATASET_REALISTIC_EVAL_PLAN.md  # Phase 3 ML plan
│   ├── SESSION_RESUME.md  # SSH session quick resume
│   ├── DATASET_ANALYSIS_LATEST.md         # Auto-generated dataset report
│   ├── copilot_context.md # This file
│   └── archive/           # Historical docs (6 files)
├── scripts/
│   ├── train_ml.py        # ML training + evaluation.json
│   ├── analyze_dataset.py # Dataset analysis report
│   └── verify_artifacts.py
├── dataset/
│   └── manifest.yaml      # Canonical L2-L4 CSV paths
├── artifacts/             # Training runs (run_<timestamp>/)
├── requirements.txt       # PySide6>=6.5.0, psutil>=5.9.0
├── README.md              # Main project documentation
├── QUICKSTART.md          # Quick setup guide
└── current.md             # Phase 3 ML status (gitignored locally)
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
| v3.3 | Dec 19-20, 2025 | GUI | Dashboard + resource monitor |

---

## AI Agent Guidelines

1. **Always check version numbers** before suggesting changes (current: v0.6 / v0.2 / v3.3)
2. **Netlink is the IPC mechanism** (not procfs events file)
3. **Workqueue is mandatory** for mm_struct access (kernel notifier is atomic context)
4. **NULL-check mm_struct** (kernel threads return NULL from `get_task_mm()`)
5. **Use psutil for resource monitoring** (with graceful fallback if unavailable)
6. **Dashboard layout is stacked rows** (stats, charts, resources); responsive 2-column switching is not wired
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
