# Daemon Documentation

**FYP Keylogger Detection - Userspace Daemon v0.2**

## Overview

The daemon is the userspace intelligence layer that receives events from the kernel module, applies heuristic detection rules, and manages alerts for the GUI.

### Key Responsibilities

- **Event Reception**: Receives keyboard event metadata via Netlink socket
- **Heuristic Detection**: Applies 3 detection rules (rapid typing, unknown process, burst pattern)
- **Process Whitelisting**: Maintains list of trusted processes
- **Alert Generation**: Creates security alerts for suspicious activity
- **Status Output**: Writes JSON status file for GUI consumption

---

## Architecture

### Components

```
┌─────────────────────────────────────────────┐
│         FYP Daemon (fyp_daemon.py)          │
├─────────────────────────────────────────────┤
│                                             │
│  ┌──────────────────────────────────────┐  │
│  │     NetlinkReceiver                  │  │
│  │  - Binds to NETLINK_FYP_DETECTOR(31) │  │
│  │  - Receives events from kernel        │  │
│  │  - Parses 158-byte event structure    │  │
│  └──────────────┬───────────────────────┘  │
│                 │                           │
│                 ↓                           │
│  ┌──────────────────────────────────────┐  │
│  │     DetectionEngine                  │  │
│  │  - Rule 1: Rapid Typing Detection    │  │
│  │  - Rule 2: Unknown Process Detection │  │
│  │  - Rule 3: Burst Pattern Detection   │  │
│  └──────────────┬───────────────────────┘  │
│                 │                           │
│                 ↓                           │
│  ┌──────────────────────────────────────┐  │
│  │     ProcessStats (per-PID tracking)  │  │
│  │  - Total events                       │  │
│  │  - Rapid ratio %                      │  │
│  │  - Events per second                  │  │
│  └──────────────┬───────────────────────┘  │
│                 │                           │
│                 ↓                           │
│  ┌──────────────────────────────────────┐  │
│  │     AlertManager                     │  │
│  │  - Generates Alert objects            │  │
│  │  - Severity classification            │  │
│  └──────────────┬───────────────────────┘  │
│                 │                           │
│                 ↓                           │
│  ┌──────────────────────────────────────┐  │
│  │     StatusWriter                     │  │
│  │  - Writes /tmp/fyp_status.json        │  │
│  │  - Updates every 500ms                │  │
│  └──────────────────────────────────────┘  │
└─────────────────────────────────────────────┘
```

---

## Detection Heuristics

### Rule 1: Rapid Typing Detection

**Severity**: HIGH  
**Threshold**: >50% rapid events

```python
if process.rapid_ratio > 50.0:
    alert = Alert(
        severity="HIGH",
        message=f"Rapid Input Stream Access: {rapid_ratio:.1f}% rapid events",
        process=process_name,
        pid=pid
    )
```

**Rationale**: Human typing cannot sustain >50% of events with inter-keystroke intervals <50ms. This indicates automated keystroke capture.

**False Positives**:
- Screen recording software
- Accessibility tools (e.g., on-screen keyboards)
- Clipboard managers with auto-paste

**Mitigation**: Whitelist known legitimate tools.

### Rule 2: Unknown Process Detection

**Severity**: MEDIUM  
**Threshold**: Process not in whitelist

```python
WHITELIST = {
    'gnome-shell',  # GNOME desktop
    'Xorg',         # X Window System
    'bash',         # Shell
    'zsh',          # Z Shell
    'firefox',      # Web browser
    'chrome',       # Web browser
    'code',         # VS Code
    # ... add more as needed
}

if process_name not in WHITELIST:
    alert = Alert(
        severity="MEDIUM",
        message=f"Unknown Process accessing keyboard events",
        process=process_name,
        pid=pid
    )
```

**Rationale**: Legitimate keyboard access is typically from well-known system processes. Unknown processes warrant investigation.

**False Positives**:
- New legitimate applications
- Development tools
- Custom scripts

**Mitigation**: User-managed whitelist (add trusted processes).

### Rule 3: Burst Pattern Detection

**Severity**: HIGH  
**Threshold**: >100 events per second sustained

```python
if process.events_per_second > 100:
    alert = Alert(
        severity="HIGH",
        message=f"Burst Pattern - Automated Input: {eps:.1f} eps",
        process=process_name,
        pid=pid
    )
```

**Rationale**: Human typing averages 2-15 keys/sec. Rates >100 eps indicate automated event generation.

**False Positives**:
- Game input macros
- Automated testing tools
- Keyboard testing utilities

**Mitigation**: Whitelist or temporarily disable detection during testing.

---

## Status File Format

### Location
`/tmp/fyp_status.json`

### Format (JSON)

```json
{
  "timestamp": "2025-12-20T15:30:45.123456",
  "daemon_running": true,
  "daemon_pid": 1234,
  "kernel_loaded": true,
  "total_events": 5432,
  "processes": {
    "1913": {
      "comm": "gnome-shell",
      "cmdline": "/usr/bin/gnome-shell",
      "total_events": 2500,
      "rapid_events": 50,
      "rapid_ratio": 2.0,
      "events_per_second": 4.5,
      "last_seen": "2025-12-20T15:30:45.100000"
    },
    "2048": {
      "comm": "suspicious",
      "cmdline": "/tmp/suspicious --keylog",
      "total_events": 1500,
      "rapid_events": 1200,
      "rapid_ratio": 80.0,
      "events_per_second": 150.0,
      "last_seen": "2025-12-20T15:30:45.120000"
    }
  },
  "alerts": [
    {
      "timestamp": "2025-12-20T15:30:40.000000",
      "severity": "HIGH",
      "message": "Rapid Input Stream Access: 80.0% rapid events",
      "process": "suspicious",
      "pid": 2048,
      "acknowledged": false
    }
  ],
  "recent_events": [
    "1703089845123456789,0,2048,suspicious,1",
    "1703089845234567890,1,2048,suspicious,1",
    "..."
  ]
}
```

### Field Descriptions

| Field | Type | Description |
|-------|------|-------------|
| `timestamp` | ISO8601 string | Last update time |
| `daemon_running` | boolean | Daemon health status |
| `daemon_pid` | int | Daemon process ID (for resource monitoring) |
| `kernel_loaded` | boolean | Kernel module loaded status |
| `total_events` | int | Cumulative event count since daemon start |
| `processes` | object | Per-process statistics keyed by PID |
| `processes[pid].comm` | string | Process name (from kernel) |
| `processes[pid].cmdline` | string | Full command line (from kernel v0.6+) |
| `processes[pid].rapid_ratio` | float | Percentage of rapid events |
| `processes[pid].events_per_second` | float | Current event rate |
| `alerts` | array | Active security alerts |
| `alerts[].severity` | string | HIGH, MEDIUM, or LOW |
| `alerts[].acknowledged` | boolean | User acknowledgment status |
| `recent_events` | array | Last 100 events (CSV format) |

---

## Configuration

### Whitelist Management

#### Location
`/home/fyp/project/daemon/whitelist.conf` (future enhancement)

#### Format
```
# FYP Daemon Whitelist
# One process name per line, comments supported

# System processes
gnome-shell
Xorg
systemd

# Shells
bash
zsh
fish

# Editors
code
vim
nano

# Browsers
firefox
chrome
chromium
```

#### Runtime Reload
```bash
# Send SIGHUP to reload whitelist
kill -HUP $(pgrep -f fyp_daemon.py)
```

### Detection Thresholds

Currently hardcoded in `fyp_daemon.py`:

```python
# Thresholds
RAPID_THRESHOLD_PERCENT = 50.0    # Rapid ratio alert threshold
BURST_THRESHOLD_EPS = 100.0        # Burst pattern threshold (events/sec)

# Timeouts
PROCESS_TIMEOUT_SEC = 60           # Remove idle processes after 60s
STATUS_WRITE_INTERVAL_MS = 500     # Write status file every 500ms
```

**Future Enhancement**: Read from config file or accept via command-line arguments.

---

## Startup and Operation

### Manual Start

```bash
cd /home/fyp/project/daemon
python3 fyp_daemon.py
```

### Background Start

```bash
cd /home/fyp/project/daemon
python3 fyp_daemon.py > /tmp/fyp_daemon.log 2>&1 &
echo $! > /tmp/fyp_daemon.pid
```

### Systemd Service (Production)

```ini
[Unit]
Description=FYP Keylogger Detection Daemon
After=network.target

[Service]
Type=simple
User=fyp
ExecStart=/usr/bin/python3 /home/fyp/project/daemon/fyp_daemon.py
Restart=on-failure
RestartSec=5s
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable fyp-daemon
sudo systemctl start fyp-daemon
sudo systemctl status fyp-daemon
```

---

## Logging

### Log Location
`/tmp/fyp_daemon.log`

### Log Format
```
[2025-12-20 15:30:45] FYP-Daemon [INFO]: Starting FYP Detection Daemon v0.2
[2025-12-20 15:30:45] FYP-Daemon [INFO]: Netlink socket bound to protocol 31
[2025-12-20 15:30:45] FYP-Daemon [INFO]: Daemon PID 1234 registered with kernel
[2025-12-20 15:30:50] FYP-Daemon [WARNING]: Alert: [HIGH] suspicious (PID 2048) - Rapid Input Stream Access: 80.0%
[2025-12-20 15:31:00] FYP-Daemon [INFO]: Status written: 5432 events, 2 processes, 1 alerts
```

### Log Levels

- **DEBUG**: Event-level details (verbose)
- **INFO**: Operational status, statistics
- **WARNING**: Detection alerts, anomalies
- **ERROR**: Netlink errors, file I/O errors
- **CRITICAL**: Unrecoverable failures

---

## IPC Protocol (Future)

### Current: File-Based

GUI reads `/tmp/fyp_status.json` every 500ms (polling).

**Limitations**:
- No bidirectional communication
- Configuration changes require daemon restart
- High I/O overhead

### Planned: Socket-Based

**Unix Domain Socket**: `/tmp/fyp_daemon.sock`

```python
# GUI → Daemon: Update threshold
{
    "command": "set_threshold",
    "parameter": "rapid_threshold_percent",
    "value": 60.0
}

# Daemon → GUI: Acknowledgment
{
    "status": "ok",
    "parameter": "rapid_threshold_percent",
    "value": 60.0
}

# GUI → Daemon: Add to whitelist
{
    "command": "whitelist_add",
    "process": "myapp"
}

# Daemon → GUI: Real-time alerts
{
    "type": "alert",
    "severity": "HIGH",
    "message": "...",
    "process": "suspicious",
    "pid": 2048
}
```

---

## Troubleshooting

### Daemon Won't Start

**Error**: `PermissionError: [Errno 13] Permission denied: '/tmp/fyp_status.json'`

**Solution**: Check file permissions
```bash
ls -l /tmp/fyp_status.json
chmod 666 /tmp/fyp_status.json
```

### No Events Received

**Check**:
```bash
# Is kernel module loaded?
lsmod | grep fyp_kbd

# Is daemon registered?
sudo dmesg | grep "Daemon registered"

# Check daemon logs
tail -f /tmp/fyp_daemon.log
```

### High False Positive Rate

**Solution 1**: Add to whitelist
```python
# Edit fyp_daemon.py
WHITELIST = {
    'gnome-shell',
    'Xorg',
    'mylegitimateapp',  # Add your app
    # ...
}
```

**Solution 2**: Increase thresholds
```python
RAPID_THRESHOLD_PERCENT = 70.0  # Increase from 50%
BURST_THRESHOLD_EPS = 200.0      # Increase from 100 eps
```

---

## Performance

### Resource Usage

- **CPU**: 0.3-1% (normal operation)
- **Memory**: 10-20 MB (depends on active processes)
- **Disk I/O**: Minimal (status file updated every 500ms)

### Scalability

- **Max processes tracked**: Unlimited (dict-based)
- **Event processing rate**: ~10,000 events/sec
- **Alert latency**: <10ms (from event to alert)

---

## API Reference (Future)

### Command Interface

#### `set_threshold(parameter, value)`
Update detection threshold at runtime.

#### `whitelist_add(process_name)`
Add process to whitelist.

#### `whitelist_remove(process_name)`
Remove process from whitelist.

#### `get_stats()`
Retrieve current statistics.

#### `clear_alerts()`
Clear all active alerts.

---

## Future Enhancements

1. **Machine Learning Integration**
   - Train classifier on labeled data
   - Replace heuristics with ML model
   - Adaptive threshold learning

2. **Persistent Storage**
   - SQLite database for historical data
   - Alert history retention
   - Process reputation tracking

3. **Multi-Daemon Support**
   - Multicast netlink for multiple listeners
   - Distributed detection across hosts
   - Central alerting server

4. **Advanced Whitelisting**
   - Process path verification
   - Digital signature checking
   - Behavior-based trust scoring

---

**Version**: 0.2  
**Last Updated**: December 20, 2025  
**Authors**: FYP Team  
**License**: GPL v2
