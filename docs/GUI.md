# GUI Documentation

**FYP Keylogger Detection System - GUI v3.3**

## Overview

Professional dark-themed Qt6 application with responsive 2-column layout, real-time charts, and resource monitoring.

### Key Features

- **7 Navigation Pages**: Dashboard, Alerts, Processes, Event Stream, AI Assistant (planned), ML Insights (planned), Configuration
- **Responsive Design**: 2-column layout (>1280px) automatically stacks vertically on smaller screens
- **Real-Time Updates**: 500ms event polling, 1s resource monitoring
- **Resource Tracking**: Combined CPU/Memory usage of GUI + Daemon processes
- **Dark Theme**: GitHub-inspired color scheme (#0d1117 background)
- **System Tray**: Color-coded status indicator with notifications

---

## Architecture

### Component Structure

```
main_gui.py (Entry Point)
    ↓
fyp_gui.py (Main Implementation)
    ├── FYPMainWindow
    │   ├── Dashboard (2-column responsive)
    │   ├── Alerts Page
    │   ├── Processes Page
    │   ├── Event Stream Page
    │   ├── AI Assistant (placeholder)
    │   ├── ML Insights (placeholder)
    │   └── Configuration Page
    ├── ResourceMonitorWidget (NEW in v3.3)
    ├── EventRateChart
    ├── ProcessBarChart
    ├── StatusIndicator
    └── DaemonMonitor
theme.py (Stylesheet)
```

---

## Dashboard Layout (v3.3)

### Responsive 2-Column Design

**Wide Screen (≥1280px)**:
```
┌─────────────────────────────────────────────────────┐
│ LEFT COLUMN (60%)    │ RIGHT COLUMN (40%)           │
├───────────────────────┼──────────────────────────────┤
│ Event Rate Chart     │ Total Events Card             │
│                      │ Event Rate Card               │
│                      │ Active Alerts Card            │
│ Process Bar Chart    │ Resource Monitor Widget       │
│                      │  - CPU/Memory Progress Bars   │
│                      │  - 60s History Line Chart     │
│                      │  - Hover for Breakdown        │
└───────────────────────┴──────────────────────────────┘
```

**Narrow Screen (<1280px)**:
```
┌─────────────────────────────────────────────────────┐
│ LEFT COLUMN (stacked vertically)                    │
├─────────────────────────────────────────────────────┤
│ Event Rate Chart                                    │
│ Process Bar Chart                                   │
├─────────────────────────────────────────────────────┤
│ RIGHT COLUMN (stacked below)                        │
├─────────────────────────────────────────────────────┤
│ Total Events Card                                   │
│ Event Rate Card                                     │
│ Active Alerts Card                                  │
│ Resource Monitor Widget                             │
└─────────────────────────────────────────────────────┘
```

---

## Resource Monitoring Widget

### Features

**Display Elements**:
- Combined CPU % (GUI + Daemon)
- Combined Memory MB (GUI + Daemon)
- Progress bars with color coding:
  - Blue: <20% CPU (normal)
  - Yellow: 20-50% CPU (elevated)
  - Red: >50% CPU (high)
- 60-second history line chart

**Hover Interaction**:
- Shows detailed breakdown on hover:
  ```
  GUI Process:    1.2% CPU, 25.5 MB
  Daemon Process: 0.3% CPU, 12.1 MB
  Total:          1.5% CPU, 37.6 MB
  ```

**Fallback Behavior**:
- If `psutil` not installed, displays warning message
- Resource monitoring gracefully disabled

---

## Dependencies

### Python Packages

```bash
pip3 install PySide6>=6.5.0 psutil>=5.9.0
```

### System Requirements

```bash
# Ubuntu/Debian
sudo apt-get install libxcb-cursor0 libnotify-bin
```

---

## Running the GUI

### Standalone

```bash
cd /home/fyp/project/gui
python3 main_gui.py
```

### Via Startup Script

```bash
cd /home/fyp/project
sudo ./start.sh  # Loads kernel, starts daemon, launches GUI
```

---

## Color Scheme

**GitHub Dark Theme**:
- Background: `#0d1117`
- Surface: `#161b22`
- Border: `#30363d`
- Text Primary: `#c9d1d9`
- Text Secondary: `#8b949e`
- Accent Blue: `#1f6feb`
- Success Green: `#2ea043`
- Warning Yellow: `#d4a72c`
- Error Red: `#da3633`

---

## Performance

- **60 FPS** animations (QSplineSeries with smooth interpolation)
- **500ms** event data updates
- **1000ms** resource monitoring updates
- **<30 MB** memory footprint (without PyQt overhead)

---

**Version**: 3.3  
**Last Updated**: December 20, 2025  
**Framework**: PySide6 (Qt6 for Python)
