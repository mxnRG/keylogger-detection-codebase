# Phase 2 Design - Userspace Components

## 1. Procfs vs Netlink Decision

### ✅ Choosing Procfs (Recommended for Prototype)

| Aspect | Procfs | Netlink |
|--------|--------|---------|
| **Simplicity** | ✅ Simple file I/O | ❌ Complex socket API |
| **Debugging** | ✅ `cat /proc/file` | ❌ Requires tools |
| **Kernel API** | ✅ Well-documented | ⚠️ More complex |
| **Performance** | ⚠️ Polling required | ✅ Event-driven |
| **Scalability** | ❌ Not ideal for high volume | ✅ Designed for it |
| **Bi-directional** | ⚠️ Read/write files | ✅ Native support |
| **Prototype fit** | ✅ Perfect | ⚠️ Overkill |

**Verdict:** **Use Procfs for Phase 2**
- Easier to implement and debug
- Sufficient for prototype event rates
- Standard file operations in Python
- Can migrate to netlink later if needed

---

## 2. Procfs Interface Design (Kernel Side)

### Directory Structure
```
/proc/fyp_detector/
├── events        # Read: Stream of keyboard events (one per line)
├── stats         # Read: Current aggregated statistics  
├── control       # Write: Control commands (reset, enable/disable)
└── version       # Read: Module version info
```

### Event Format (events file)
```
# One event per line, pipe-delimited
# Timestamp|EventType|PID|ProcessName|RapidFlag
1734278400|PRESS|1913|gnome-shell|0
1734278401|RELEASE|1913|gnome-shell|0
1734278402|PRESS|1913|gnome-shell|1
```

**Fields:**
- `Timestamp`: Unix timestamp (seconds since epoch)
- `EventType`: "PRESS" or "RELEASE"
- `PID`: Process ID
- `ProcessName`: Process comm (up to 16 chars)
- `RapidFlag`: 1 if event was rapid (<10ms), 0 otherwise

### Stats Format (stats file)
```
total_events: 1523
press_events: 762
release_events: 761
rapid_events: 45
rapid_ratio: 2.95
active_since: 1734278000
```

### Control Commands (control file)
```bash
# Reset all counters
echo "reset" > /proc/fyp_detector/control

# Disable event collection (module stays loaded)
echo "disable" > /proc/fyp_detector/control

# Re-enable
echo "enable" > /proc/fyp_detector/control
```

---

## 3. Kernel Module Changes (v0.3 → v0.4)

### New Data Structures

```c
// Circular buffer for events
#define EVENT_BUFFER_SIZE 1024

struct kbd_event {
    unsigned long timestamp;    // jiffies
    char event_type[8];         // "PRESS" or "RELEASE"
    pid_t pid;
    char comm[TASK_COMM_LEN];
    int rapid_flag;             // 1 if rapid, 0 otherwise
};

static struct kbd_event event_buffer[EVENT_BUFFER_SIZE];
static unsigned int event_head = 0;    // Write position
static unsigned int event_tail = 0;    // Read position
static DEFINE_SPINLOCK(buffer_lock);   // Protect buffer access
```

### Procfs Handlers

```c
// Read handler for /proc/fyp_detector/events
static ssize_t events_read(struct file *file, char __user *buf,
                           size_t count, loff_t *ppos)
{
    // Format events from circular buffer
    // Copy to userspace
    return bytes_read;
}

// Read handler for /proc/fyp_detector/stats
static ssize_t stats_read(struct file *file, char __user *buf,
                          size_t count, loff_t *ppos)
{
    char stats_buf[512];
    snprintf(stats_buf, sizeof(stats_buf),
             "total_events: %lu\n"
             "press_events: %lu\n"
             "release_events: %lu\n"
             "rapid_events: %lu\n"
             "rapid_ratio: %.2f\n",
             event_count, press_count, release_count,
             rapid_events,
             (event_count > 0) ? (rapid_events * 100.0 / event_count) : 0.0);
    
    return simple_read_from_buffer(buf, count, ppos,
                                   stats_buf, strlen(stats_buf));
}

// Write handler for /proc/fyp_detector/control
static ssize_t control_write(struct file *file, const char __user *buf,
                             size_t count, loff_t *ppos)
{
    char cmd[32];
    if (count > sizeof(cmd) - 1)
        return -EINVAL;
    
    if (copy_from_user(cmd, buf, count))
        return -EFAULT;
    
    cmd[count] = '\0';
    
    if (strncmp(cmd, "reset", 5) == 0) {
        event_count = 0;
        press_count = 0;
        release_count = 0;
        rapid_events = 0;
        pr_info("[FYP] Statistics reset\n");
    }
    // Handle other commands...
    
    return count;
}
```

### File Operations Structures

```c
static const struct proc_ops events_fops = {
    .proc_read = events_read,
};

static const struct proc_ops stats_fops = {
    .proc_read = stats_read,
};

static const struct proc_ops control_fops = {
    .proc_write = control_write,
};
```

### Module Init/Exit Updates

```c
static int __init fyp_init(void)
{
    int ret;
    
    // ... existing keyboard notifier registration ...
    
    // Create /proc/fyp_detector/ directory
    proc_dir = proc_mkdir("fyp_detector", NULL);
    if (!proc_dir) {
        pr_err("[FYP] Failed to create /proc/fyp_detector\n");
        unregister_keyboard_notifier(&fyp_nb);
        return -ENOMEM;
    }
    
    // Create events file
    proc_events = proc_create("events", 0444, proc_dir, &events_fops);
    if (!proc_events) {
        pr_err("[FYP] Failed to create events file\n");
        proc_remove(proc_dir);
        unregister_keyboard_notifier(&fyp_nb);
        return -ENOMEM;
    }
    
    // Create stats file
    proc_stats = proc_create("stats", 0444, proc_dir, &stats_fops);
    
    // Create control file
    proc_create("control", 0220, proc_dir, &control_fops);
    
    pr_info("[FYP] Procfs interface ready at /proc/fyp_detector/\n");
    return 0;
}

static void __exit fyp_exit(void)
{
    // Remove procfs entries
    proc_remove(proc_dir);
    
    // ... existing cleanup ...
}
```

---

## 4. Python Daemon Architecture

### File: `daemon/fyp_daemon.py`

```python
#!/usr/bin/env python3
"""
FYP Keylogger Detection Daemon

Reads keyboard events from kernel procfs interface,
applies detection heuristics, and manages alerts.
"""

import time
import threading
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, List
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s: %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class ProcessStats:
    """Per-process statistics tracker"""
    pid: int
    comm: str
    total_events: int = 0
    press_events: int = 0
    release_events: int = 0
    rapid_events: int = 0
    first_seen: float = field(default_factory=time.time)
    last_seen: float = field(default_factory=time.time)
    
    @property
    def rapid_ratio(self) -> float:
        """Calculate rapid event percentage"""
        if self.total_events == 0:
            return 0.0
        return (self.rapid_events / self.total_events) * 100.0
    
    @property
    def duration(self) -> float:
        """Time span of activity in seconds"""
        return self.last_seen - self.first_seen
    
    @property
    def events_per_second(self) -> float:
        """Average event rate"""
        if self.duration == 0:
            return 0.0
        return self.total_events / self.duration


@dataclass
class Alert:
    """Detection alert"""
    timestamp: float
    severity: str  # "LOW", "MEDIUM", "HIGH"
    process_name: str
    pid: int
    rule: str
    details: str


class DetectionEngine:
    """Applies heuristic detection rules"""
    
    # Heuristic thresholds
    RAPID_RATIO_THRESHOLD = 50.0  # %
    BURST_THRESHOLD = 100         # events
    BURST_WINDOW = 1.0            # seconds
    
    # Process whitelist (known-good applications)
    WHITELIST = {
        'gnome-shell', 'Xorg', 'gdm-x-session',
        'bash', 'python3', 'code', 'firefox',
        'gnome-terminal'
    }
    
    def __init__(self):
        self.alerts: List[Alert] = []
    
    def check_rapid_typing(self, stats: ProcessStats) -> Alert | None:
        """Rule 1: Detect automated/rapid typing"""
        if stats.total_events < 10:  # Need minimum sample size
            return None
        
        if stats.rapid_ratio > self.RAPID_RATIO_THRESHOLD:
            return Alert(
                timestamp=time.time(),
                severity="HIGH",
                process_name=stats.comm,
                pid=stats.pid,
                rule="Rapid Typing",
                details=f"Rapid ratio: {stats.rapid_ratio:.1f}% "
                       f"(threshold: {self.RAPID_RATIO_THRESHOLD}%)"
            )
        return None
    
    def check_unknown_process(self, stats: ProcessStats) -> Alert | None:
        """Rule 2: Flag processes not in whitelist"""
        if stats.comm not in self.WHITELIST:
            return Alert(
                timestamp=time.time(),
                severity="MEDIUM",
                process_name=stats.comm,
                pid=stats.pid,
                rule="Unknown Process",
                details=f"Process '{stats.comm}' not in whitelist"
            )
        return None
    
    def check_burst_pattern(self, stats: ProcessStats) -> Alert | None:
        """Rule 3: Detect burst of events in short time"""
        if stats.duration < self.BURST_WINDOW:
            return None  # Not enough time passed
        
        if stats.events_per_second > self.BURST_THRESHOLD:
            return Alert(
                timestamp=time.time(),
                severity="HIGH",
                process_name=stats.comm,
                pid=stats.pid,
                rule="Burst Pattern",
                details=f"Event rate: {stats.events_per_second:.1f} events/sec "
                       f"(threshold: {self.BURST_THRESHOLD})"
            )
        return None
    
    def evaluate(self, stats: ProcessStats) -> List[Alert]:
        """Apply all heuristics to process stats"""
        alerts = []
        
        # Check each rule
        if alert := self.check_rapid_typing(stats):
            alerts.append(alert)
        
        if alert := self.check_unknown_process(stats):
            alerts.append(alert)
        
        if alert := self.check_burst_pattern(stats):
            alerts.append(alert)
        
        return alerts


class FYPDaemon:
    """Main daemon class"""
    
    PROCFS_EVENTS = "/proc/fyp_detector/events"
    PROCFS_STATS = "/proc/fyp_detector/stats"
    
    def __init__(self):
        self.running = False
        self.process_stats: Dict[int, ProcessStats] = {}
        self.detection_engine = DetectionEngine()
        self.event_count = 0
        
    def read_event_line(self, line: str) -> dict | None:
        """Parse event line from procfs"""
        try:
            parts = line.strip().split('|')
            if len(parts) != 5:
                return None
            
            return {
                'timestamp': float(parts[0]),
                'event_type': parts[1],
                'pid': int(parts[2]),
                'comm': parts[3],
                'rapid_flag': int(parts[4])
            }
        except (ValueError, IndexError):
            logger.warning(f"Failed to parse event line: {line}")
            return None
    
    def process_event(self, event: dict):
        """Process a single keyboard event"""
        pid = event['pid']
        
        # Get or create process stats
        if pid not in self.process_stats:
            self.process_stats[pid] = ProcessStats(
                pid=pid,
                comm=event['comm']
            )
        
        stats = self.process_stats[pid]
        
        # Update statistics
        stats.total_events += 1
        stats.last_seen = time.time()
        
        if event['event_type'] == 'PRESS':
            stats.press_events += 1
        elif event['event_type'] == 'RELEASE':
            stats.release_events += 1
        
        if event['rapid_flag']:
            stats.rapid_events += 1
        
        # Apply detection rules periodically
        if stats.total_events % 10 == 0:  # Check every 10 events
            alerts = self.detection_engine.evaluate(stats)
            for alert in alerts:
                logger.warning(f"ALERT: {alert.rule} - {alert.details}")
                # TODO: Send to GUI
    
    def event_reader_thread(self):
        """Background thread that reads events from procfs"""
        logger.info("Event reader thread started")
        
        try:
            with open(self.PROCFS_EVENTS, 'r') as f:
                while self.running:
                    line = f.readline()
                    if not line:
                        time.sleep(0.1)  # No new events, sleep briefly
                        continue
                    
                    event = self.read_event_line(line)
                    if event:
                        self.process_event(event)
                        self.event_count += 1
        
        except FileNotFoundError:
            logger.error(f"Procfs file not found: {self.PROCFS_EVENTS}")
        except Exception as e:
            logger.error(f"Event reader error: {e}")
        
        logger.info("Event reader thread stopped")
    
    def start(self):
        """Start the daemon"""
        logger.info("FYP Daemon starting...")
        self.running = True
        
        # Start event reader thread
        reader = threading.Thread(target=self.event_reader_thread, daemon=True)
        reader.start()
        
        logger.info("FYP Daemon running. Press Ctrl+C to stop.")
        
        try:
            while self.running:
                time.sleep(1)
                # TODO: Periodic status updates
        except KeyboardInterrupt:
            logger.info("Shutting down...")
            self.running = False
    
    def stop(self):
        """Stop the daemon"""
        self.running = False


if __name__ == '__main__':
    daemon = FYPDaemon()
    daemon.start()
```

---

## 5. Detection Heuristics (Simple, No ML)

### Rule 1: Rapid Typing Detection
```python
if rapid_ratio > 50%:
    severity = HIGH
    reason = "Automated input detected"
```
**Rationale:** Humans cannot sustain >50% rapid events (<10ms intervals)

### Rule 2: Unknown Process Alert
```python
if process_name not in WHITELIST:
    severity = MEDIUM
    reason = "Process not recognized"
```
**Rationale:** Flag unfamiliar processes for user review

### Rule 3: Burst Pattern Detection
```python
if events_per_second > 100:
    severity = HIGH
    reason = "Burst input pattern"
```
**Rationale:** Normal typing ~5-10 keys/sec, >100/sec is suspicious

### Future Enhancements (Post-Prototype)
- Process reputation scoring
- Temporal pattern analysis
- Cross-correlation with file access
- ML-based anomaly detection

---

## 6. Qt GUI Design (PySide6)

### Main Window Layout

```
┌─────────────────────────────────────────────────────────────┐
│  FYP Keylogger Detector              [Status: Active ●]     │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────┐  ┌────────────────────────────────────┐  │
│  │ Live Events  │  │  Detection Alerts                   │  │
│  │ (Scrolling)  │  │  ┌──────────────────────────────┐  │  │
│  │              │  │  │ [!] HIGH: Rapid Typing       │  │  │
│  │ PRESS        │  │  │     Process: hidden_logger   │  │  │
│  │ pid=1234     │  │  │     Rapid ratio: 75%         │  │  │
│  │ bash         │  │  └──────────────────────────────┘  │  │
│  │              │  │  ┌──────────────────────────────┐  │  │
│  │ RELEASE      │  │  │ [?] MED: Unknown Process     │  │  │
│  │ pid=1234     │  │  │     Process: mystery_app     │  │  │
│  │ bash         │  │  └──────────────────────────────┘  │  │
│  └──────────────┘  └────────────────────────────────────┘  │
│                                                               │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ Process Statistics                                   │   │
│  │ Process    PID    Events  Rapid%  Risk   Action      │   │
│  │ bash       1234   145     2.1%    ✓      [Flag]      │   │
│  │ gnome      1913   89      1.2%    ✓      [Flag]      │   │
│  │ mystery    6666   230     68%     ⚠      [Flag]      │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                               │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ ℹ️ User Awareness Message:                           │   │
│  │ Your keyboard activity is being monitored to detect  │   │
│  │ potential keyloggers. All data stays local.          │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                               │
│  Total Events: 464  │  Active Processes: 3  │  Alerts: 2    │
└─────────────────────────────────────────────────────────────┘
```

### GUI Code Structure

```python
# gui/fyp_gui.py
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTableWidget, QListWidget, QLabel, QPushButton,
    QTextEdit
)
from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QColor

class DetectorGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("FYP Keylogger Detector")
        self.setGeometry(100, 100, 1000, 700)
        
        # Main widget and layout
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        
        # Status bar
        self.status_label = QLabel("Status: Active ●")
        layout.addWidget(self.status_label)
        
        # Top section: Events + Alerts
        top_layout = QHBoxLayout()
        
        # Live events list
        self.events_list = QListWidget()
        top_layout.addWidget(self.events_list, 1)
        
        # Alerts panel
        self.alerts_panel = QTextEdit()
        self.alerts_panel.setReadOnly(True)
        top_layout.addWidget(self.alerts_panel, 2)
        
        layout.addLayout(top_layout)
        
        # Process statistics table
        self.process_table = QTableWidget()
        self.process_table.setColumnCount(6)
        self.process_table.setHorizontalHeaderLabels(
            ["Process", "PID", "Events", "Rapid%", "Risk", "Action"]
        )
        layout.addWidget(self.process_table)
        
        # Awareness message
        awareness = QLabel(
            "ℹ️ Your keyboard activity is monitored locally to detect "
            "keyloggers. All data stays on your system."
        )
        awareness.setWordWrap(True)
        layout.addWidget(awareness)
        
        # Stats footer
        self.footer_label = QLabel("Total Events: 0 | Active Processes: 0 | Alerts: 0")
        layout.addWidget(self.footer_label)
        
        # Timer for updates
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_display)
        self.timer.start(500)  # Update every 500ms
    
    def update_display(self):
        """Refresh display from daemon data"""
        # TODO: Read from daemon (IPC, file, socket)
        pass
    
    def add_alert(self, alert):
        """Add alert to alerts panel"""
        color = {
            "HIGH": "red",
            "MEDIUM": "orange",
            "LOW": "yellow"
        }.get(alert.severity, "gray")
        
        self.alerts_panel.append(
            f'<div style="color: {color};">'
            f'[{alert.severity}] {alert.rule}: {alert.details}'
            f'</div>'
        )
```

---

## Summary

**Phase 2 Components:**
1. ✅ Procfs interface design (simple, debuggable)
2. ✅ Kernel module updates (circular buffer, procfs handlers)
3. ✅ Python daemon architecture (event reading, heuristics)
4. ✅ Simple detection rules (rapid typing, unknown process, burst)
5. ✅ Qt GUI design (live events, alerts, process stats)

**Next Steps:**
1. Implement procfs in kernel module (v0.4)
2. Build Python daemon
3. Build Qt GUI
4. Integration testing
5. Demo scenario creation
