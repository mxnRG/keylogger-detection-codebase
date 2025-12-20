# GUI Enhancement Plan - Days 2-4

## Current State (v0.1)
- Basic 3-tab interface (Alerts, Statistics, Event Stream)
- QTableWidget for alerts and events
- JSON status file polling (1s interval)
- Minimal styling

## Day 2-3: Core Enhancements

### 1. QtCharts Integration
**Event Rate Chart** (Line Chart)
- X-axis: Time (last 60 seconds)
- Y-axis: Events per second
- Real-time scrolling graph
- Color: Green (<50 eps), Yellow (50-100), Red (>100)

**Process Distribution** (Bar Chart)
- Top 5 processes by event count
- Horizontal bars with PID labels
- Update every 5 seconds

**Rapid Typing Ratio** (Gauge/Progress Bar)
- Circular gauge: 0-100%
- Color gradient: Green → Yellow → Red
- Threshold markers at 50%

### 2. Dark Theme
**Color Palette**
```
Background:     #1e1e1e
Surface:        #2d2d2d
Border:         #404040
Text Primary:   #e0e0e0
Text Secondary: #a0a0a0
Accent:         #007acc
Success:        #4ec9b0
Warning:        #ce9178
Error:          #f48771
```

**QSS Stylesheet**
- QMainWindow, QWidget backgrounds
- QTableWidget alternating row colors
- QPushButton hover effects
- QGroupBox styled borders
- QTabWidget custom tabs

### 3. System Tray Integration
**Features**
- Minimize to tray on close
- Tray icon states:
  - Green: Normal (no alerts)
  - Yellow: Medium alerts
  - Red: High severity alerts
- Right-click context menu:
  - Show/Hide window
  - Pause monitoring
  - Quit

### 4. Desktop Notifications
**Trigger Rules**
- HIGH severity alerts only
- Throttle: Max 1 notification per 30s
- Content: Process name + alert reason
- Action: Click to show GUI

**Implementation**
- Use `notify-send` on Linux
- Fallback: QSystemTrayIcon.showMessage()

### 5. Alert Management
**Filtering**
- Severity dropdown: ALL, HIGH, MEDIUM, LOW
- Time range: Last hour, Today, All
- Process name search box

**Actions**
- Clear all alerts button
- Export to CSV
- Mark as reviewed (checkbox column)

## Day 4: Polish & Testing

### 1. Additional Features
- Refresh rate selector (1s, 2s, 5s)
- Pause/Resume monitoring toggle
- Daemon connection indicator (green dot/red dot)
- Auto-scroll toggle for event stream

### 2. Performance
- Limit table rows (max 1000, circular buffer)
- Chart data points (max 60 for line chart)
- Lazy loading for historical alerts

### 3. User Experience
- Keyboard shortcuts (Ctrl+Q quit, Ctrl+R refresh)
- Tooltips on all controls
- Status bar with last update time
- Window state persistence (size, position)

## Technical Notes

### File Structure
```
gui/
├── fyp_gui.py (main application)
├── styles/
│   └── dark_theme.qss
├── icons/
│   ├── tray_normal.png
│   ├── tray_warning.png
│   └── tray_alert.png
└── run_gui.sh
```

### Dependencies
- PySide6 (Qt 6) - already installed ✓
- QtCharts - already installed ✓
- Standard library only (no additional packages)

### Testing Checklist
- [ ] Charts update in real-time
- [ ] Dark theme applied correctly
- [ ] System tray minimize/restore
- [ ] Notifications on HIGH alerts
- [ ] Alert filtering works
- [ ] CSV export functional
- [ ] No memory leaks (24hr test)
- [ ] Responsive at 1000+ events/min
