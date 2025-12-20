# FYP Keylogger Detection GUI v2.0 - User Guide

## Overview
Modern, production-grade GUI with dark theme, real-time charts, and system tray integration.

## Features

### 🎨 Visual Design
- **Dark Theme**: Professional dark color scheme (#1e1e1e background, #007acc accents)
- **Animated Status Indicators**: Glowing colored dots for system status
- **Gradient Charts**: Real-time line and bar charts with color-coded thresholds
- **Smooth Transitions**: Hover effects, focus borders, animated updates

### 📊 Dashboard Tab
**Event Rate Chart (Line Graph)**
- Real-time scrolling line chart showing events per second
- X-axis: Last 60 seconds
- Y-axis: Auto-scaling based on event rate
- Color coding:
  - Green: < 50 events/sec (normal)
  - Yellow: 50-100 events/sec (elevated)
  - Red: > 100 events/sec (suspicious)
- Smooth spline interpolation for visual appeal

**Process Activity (Bar Chart)**
- Top 5 processes by event count
- Horizontal bars with process name and PID
- Auto-updates every 500ms
- Color: Accent blue (#007acc)

### 🚨 Alerts Tab
**Features:**
- Searchable alert table with real-time filtering
- Severity filter dropdown (ALL, HIGH, MEDIUM, LOW)
- Process name search box
- Checkboxes for marking alerts as reviewed
- Color-coded severity badges:
  - 🔴 RED: HIGH severity
  - 🟡 YELLOW: MEDIUM severity
  - 🟢 GREEN: LOW severity

**Actions:**
- **Clear All**: Remove all alerts from table
- **Export CSV**: Save alerts to `/tmp/fyp_alerts_YYYYMMDD_HHMMSS.csv`

### ⚙️ Processes Tab
**Process Statistics Table:**
- Sortable columns (click header to sort)
- Columns:
  - PID: Process ID
  - Process: Command name
  - Events: Total event count
  - Rapid %: Rapid typing ratio (highlighted if > 50%)
  - Rate (eps): Current events per second (highlighted if > 100)
- Background color warnings for suspicious activity
- Real-time updates every 500ms

### 📋 Event Stream Tab
**Raw Event Log:**
- Last 100 events from kernel module
- Monospace font (Courier) for readability
- Auto-scroll toggle (enable/disable)
- Clear button to reset stream
- Timestamp + PID + Process + Event Type format

### 🔔 System Tray
**Features:**
- Always-on tray icon in system notification area
- Color-coded status:
  - 🟢 Green: Normal operation
  - 🟡 Yellow: Medium alerts detected
  - 🔴 Red: HIGH severity alerts
  - ⚫ Gray: Daemon disconnected
- Right-click menu:
  - Show Window
  - Quit
- Double-click to restore from tray
- Minimize to tray on window close

### 🔔 Desktop Notifications
**Behavior:**
- Automatic notifications for HIGH severity alerts only
- Uses `notify-send` on Linux
- Notification content:
  - Title: "Security Alert: [Process Name]"
  - Body: Alert message
  - Icon: security-high
  - Urgency: critical
- Throttled: Maximum 1 notification per alert
- Click notification to bring GUI to foreground

### 📈 Status Header
**Real-Time Indicators:**
- **Kernel Module**: 🟢 Active / 🔴 Inactive (animated dot)
- **Daemon Status**: 🟢 Running / 🔴 Stopped / 🟡 Stale
- **Event Counter**: Total events processed (formatted with commas)
- **Event Rate**: Current events per second
- **Refresh Button**: Manual status update trigger

## Usage

### Starting the GUI
```bash
cd /home/fyp/project/gui
./fyp_gui.py
```

Or via run script:
```bash
./run_gui.sh
```

### Navigation
- **Tab Switching**: Click tab titles or use Ctrl+Tab / Ctrl+Shift+Tab
- **Table Sorting**: Click column headers in Processes tab
- **Search**: Type in search box (Alerts tab) for real-time filtering
- **Filters**: Use dropdown menus to filter by severity

### Monitoring Workflow
1. **Dashboard**: Monitor real-time event rate chart
   - Green line = normal activity
   - Yellow/Red spike = investigate Alerts tab
   
2. **Alerts**: Review new alerts
   - Check HIGH severity alerts first
   - Use search to find specific processes
   - Mark as reviewed (checkbox column)
   
3. **Processes**: Identify suspicious processes
   - Sort by "Events" column (highest first)
   - Look for high "Rapid %" (> 50%)
   - Note processes with > 100 eps rate
   
4. **Event Stream**: Examine raw data
   - Enable auto-scroll for real-time monitoring
   - Disable for detailed inspection
   - Use Ctrl+F to search within stream

### Exporting Data
1. **Alert Export**:
   - Go to Alerts tab
   - Click "Export CSV"
   - File saved to `/tmp/fyp_alerts_[timestamp].csv`
   - Format: Timestamp,Severity,Process,PID,Message

2. **Event Stream Export**:
   - Select all text (Ctrl+A)
   - Copy (Ctrl+C)
   - Paste into text editor

### System Tray Usage
- **Normal**: GUI runs minimized in tray, icon is green
- **Alert**: Icon turns yellow/red, click to view
- **Restore**: Double-click tray icon or right-click > Show Window
- **Quit**: Right-click tray icon > Quit

## Configuration

### Refresh Rate
Default: 500ms (2 updates per second)

To change, edit `fyp_gui.py`:
```python
self.daemon_monitor.start(1000)  # 1000ms = 1 update per second
```

### Chart History
Default: 60 seconds of event rate data

To change, edit `EventRateChart` class:
```python
self.time_points = deque(maxlen=120)  # 120 seconds
self.rate_points = deque(maxlen=120)
```

### Top Processes Count
Default: Top 5 processes

To change, edit `ProcessBarChart.update_data()`:
```python
sorted_procs = sorted(...)[:10]  # Top 10
```

## Keyboard Shortcuts
- **Ctrl+Q**: Quit application
- **Ctrl+R**: Refresh status
- **Ctrl+W**: Close window (minimize to tray)
- **Ctrl+Tab**: Next tab
- **Ctrl+Shift+Tab**: Previous tab
- **Ctrl+F**: Find in Event Stream (standard Qt)

## Troubleshooting

### GUI Won't Start
**Issue**: `Could not load the Qt platform plugin "xcb"`

**Solution**:
```bash
sudo apt-get install libxcb-cursor0
```

### No Data Showing
**Check**:
1. Daemon running: `ps aux | grep fyp_daemon`
2. Status file exists: `ls -l /tmp/fyp_status.json`
3. Kernel module loaded: `lsmod | grep fyp_kbd`

**Fix**:
```bash
# Load kernel module
cd /home/fyp/project/kernel
sudo insmod fyp_kbd.ko

# Start daemon
cd /home/fyp/project/daemon
./fyp_daemon.py &
```

### Charts Not Updating
- Click "🔄 Refresh" button in status header
- Check daemon indicator is green
- Verify `/tmp/fyp_status.json` is being updated: `watch -n 1 cat /tmp/fyp_status.json`

### Notifications Not Working
**Install notify-send**:
```bash
sudo apt-get install libnotify-bin
```

**Test**:
```bash
notify-send "Test" "Notification working"
```

### System Tray Not Showing
**Issue**: Some desktop environments hide tray icons

**Solution** (GNOME):
```bash
sudo apt-get install gnome-shell-extension-appindicator
```

**Solution** (KDE/XFCE)**:
Tray should work by default

## Performance

### Resource Usage
- **Memory**: ~80-120 MB (with 1000 events)
- **CPU**: < 1% idle, < 5% during rapid events
- **Disk**: None (reads from `/tmp/fyp_status.json`)

### Optimization Tips
1. **Increase refresh interval** for lower CPU usage:
   ```python
   self.daemon_monitor.start(2000)  # 2 seconds
   ```

2. **Limit table rows** in Processes tab:
   ```python
   if len(processes) > 50:
       processes = dict(list(processes.items())[:50])
   ```

3. **Disable auto-scroll** in Event Stream for large logs

## Technical Details

### Data Flow
1. Daemon writes `/tmp/fyp_status.json` (every 500ms)
2. GUI polls file for updates (file modification time check)
3. On update: Parse JSON → Update widgets → Redraw charts
4. Event rate calculated: `(current_events - last_events) * 2`

### Chart Rendering
- Uses QtCharts (hardware-accelerated via OpenGL)
- Spline interpolation for smooth curves
- Double-buffered rendering (no flicker)
- Antialiasing enabled for smooth edges

### Thread Safety
- GUI runs in main Qt thread
- File I/O in QTimer callback (non-blocking)
- No worker threads needed (lightweight polling)

## Known Limitations

1. **X Display Required**: Cannot run in pure terminal (SSH without X forwarding)
2. **Single Instance**: No multi-instance detection (can run multiple GUIs)
3. **Alert Persistence**: Alerts cleared on GUI restart (not saved to disk)
4. **Chart History**: Limited to last 60 seconds (not configurable via GUI)

## Future Enhancements (Not Implemented)

- [ ] Settings dialog for configuration
- [ ] Historical data persistence (SQLite database)
- [ ] Alert filtering by time range (last hour, today, all)
- [ ] Process whitelist/blacklist
- [ ] Custom alert rules editor
- [ ] Export charts as PNG images
- [ ] Multi-language support
- [ ] Network monitoring (remote daemon connection)

## Version History

### v2.0 (Dec 20, 2025) - CURRENT
- Complete UI overhaul with modern dark theme
- Added QtCharts for real-time visualization
- Implemented system tray integration
- Added desktop notifications (HIGH alerts)
- Searchable and filterable alert table
- CSV export functionality
- Animated status indicators
- Color-coded severity and performance warnings

### v0.1 (Dec 15, 2025) - DEPRECATED
- Basic 3-tab interface
- Simple tables and text displays
- No charts or visualizations
- No system tray or notifications
- Limited styling
