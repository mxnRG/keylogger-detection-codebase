# GUI Modular Refactoring Guide

## Current Status

✅ **All fixes implemented in single file:**
- Gray/silver navbar icons
- Functional configuration page
- Fixed ML insights formatting
- Process termination feature
- Log export functionality

📝 **File:** `/home/fyp/project/gui/fyp_gui.py` (1740 lines)

---

## Recommended Modular Structure

```
project/gui/
├── main_gui.py              # Main window + orchestration (200 lines)
├── theme.py                 # DARK_THEME stylesheet (300 lines)
├── daemon_monitor.py        # DaemonMonitor class (100 lines)
├── components/              # Reusable UI components
│   ├── __init__.py
│   ├── status_indicator.py  # StatusIndicator widget
│   ├── sidebar_button.py    # SidebarButton widget
│   └── charts.py            # EventRateChart + ProcessBarChart
├── pages/                   # Page implementations
│   ├── __init__.py
│   ├── dashboard.py         # DashboardPage class
│   ├── alerts.py            # AlertsPage class
│   ├── processes.py         # ProcessesPage class
│   ├── event_stream.py      # EventStreamPage class
│   ├── ai_assistant.py      # AIAssistantPage (placeholder)
│   ├── ml_insights.py       # MLInsightsPage (placeholder)
│   └── configuration.py     # ConfigurationPage (functional)
└── models/                  # Data models
    ├── __init__.py
    └── alert.py             # Alert dataclass
```

---

## Why Refactor?

### Current (Single File):
❌ 1740 lines in one file  
❌ Hard to navigate  
❌ Difficult to test individual components  
❌ Multiple developers can't work simultaneously  
❌ Git merge conflicts more likely  

### Modular (Proposed):
✅ Each file < 300 lines  
✅ Clear separation of concerns  
✅ Easy to test components in isolation  
✅ Multiple developers can work on different pages  
✅ Reusable components across projects  

---

## Refactoring Steps

### Step 1: Extract Theme
```bash
# Create theme.py
cat > gui/theme.py << 'EOF'
"""
FYP GUI Theme - GitHub-inspired dark theme
"""

DARK_THEME = """
/* ... entire stylesheet ... */
"""
EOF
```

### Step 2: Extract Components

**File: `gui/components/status_indicator.py`**
```python
from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Property, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QPainter, QColor, QBrush, QPen, QRadialGradient
from PySide6.QtCore import Qt

class StatusIndicator(QWidget):
    """Animated pulsing status indicator"""
    # ... copy from fyp_gui.py lines 324-382 ...
```

**File: `gui/components/sidebar_button.py`**
```python
from PySide6.QtWidgets import QPushButton
from PySide6.QtCore import QPropertyAnimation, QEasingCurve
from PySide6.QtCore import Qt

class SidebarButton(QPushButton):
    """Custom sidebar navigation button"""
    # ... copy from fyp_gui.py lines 387-415 ...
```

**File: `gui/components/charts.py`**
```python
from PySide6.QtCharts import QChartView, QChart, QSplineSeries, QBarSeries, QBarSet
from PySide6.QtWidgets import QWidget
# ... etc

class EventRateChart(QChartView):
    # ... copy from fyp_gui.py lines 418-509 ...

class ProcessBarChart(QChartView):
    # ... copy from fyp_gui.py lines 512-572 ...
```

### Step 3: Extract Pages

**File: `gui/pages/dashboard.py`**
```python
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QGroupBox
from gui.components import EventRateChart, ProcessBarChart

class DashboardPage(QWidget):
    """Dashboard page with stats and charts"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
    
    def init_ui(self):
        # ... copy from create_dashboard_page() ...
    
    def create_stat_card(self, label, value):
        # ... helper method ...
    
    def update_stats(self, data):
        """Called by main window when data updates"""
        # Update cards and charts
```

**File: `gui/pages/configuration.py`**
```python
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, 
                               QGroupBox, QSlider, QCheckBox, etc.)
from PySide6.QtCore import Signal
import subprocess
import logging

class ConfigurationPage(QWidget):
    """Functional configuration and process management"""
    
    # Signals for communication with main window
    threshold_changed = Signal(int)
    process_terminated = Signal(int)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.alerts = []  # Will be set by main window
        self.init_ui()
    
    def init_ui(self):
        # ... copy from create_config_page() ...
    
    def set_alerts(self, alerts):
        """Set alerts list from main window"""
        self.alerts = alerts
    
    # All the helper methods (refresh_risky_processes, terminate_selected_process, etc.)
```

### Step 4: Create Main Window

**File: `gui/main_gui.py`**
```python
#!/usr/bin/env python3
"""
FYP Keylogger Detection System - Main GUI
Professional interface with modular architecture
"""

import sys
from PySide6.QtWidgets import QApplication, QMainWindow, QWidget, QHBoxLayout, QStackedWidget
from PySide6.QtCore import Qt

# Import theme
from theme import DARK_THEME

# Import components
from components import StatusIndicator, SidebarButton

# Import pages
from pages import (DashboardPage, AlertsPage, ProcessesPage, 
                   EventStreamPage, AIAssistantPage, MLInsightsPage, 
                   ConfigurationPage)

# Import monitoring
from daemon_monitor import DaemonMonitor

class FYPMainWindow(QMainWindow):
    """Professional main window with sidebar navigation"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("FYP Keylogger Detection System")
        self.setMinimumSize(1400, 900)
        
        self.alerts = []
        self.current_page = "dashboard"
        
        # Initialize monitoring
        self.daemon_monitor = DaemonMonitor()
        self.daemon_monitor.status_updated.connect(self.on_status_update)
        self.daemon_monitor.alert_received.connect(self.on_alert_received)
        
        self.setup_tray()
        self.init_ui()
        self.daemon_monitor.start()
    
    def init_ui(self):
        # Create sidebar
        # Create pages
        self.pages = {
            "dashboard": DashboardPage(self),
            "alerts": AlertsPage(self),
            "processes": ProcessesPage(self),
            "stream": EventStreamPage(self),
            "ai_assistant": AIAssistantPage(self),
            "ml_insights": MLInsightsPage(self),
            "config": ConfigurationPage(self)
        }
        
        # Connect signals
        self.pages["config"].threshold_changed.connect(self.on_threshold_changed)
        self.pages["config"].set_alerts(self.alerts)
        
        # ... rest of setup ...
    
    def on_status_update(self, data):
        # Distribute updates to all pages
        self.pages["dashboard"].update_stats(data)
        self.pages["processes"].update_table(data.get('processes', {}))
        # etc.

def main():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    app.setStyleSheet(DARK_THEME)
    
    window = FYPMainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
```

### Step 5: Run Script Update

**File: `start.sh` or `run_gui.sh`**
```bash
#!/bin/bash
cd "$(dirname "$0")"
python3 gui/main_gui.py "$@"
```

---

## Benefits of This Refactoring

### 1. **Maintainability**
- Each file has a single responsibility
- Easy to find specific functionality
- Changes to one page don't affect others

### 2. **Testability**
```python
# Can test components in isolation
from gui.components import StatusIndicator

def test_status_indicator():
    indicator = StatusIndicator()
    indicator.set_status('success', pulse=True)
    assert indicator._color == QColor(46, 160, 67)
```

### 3. **Reusability**
```python
# Use components in other projects
from gui.components import EventRateChart

class MyOtherApp:
    def create_chart(self):
        return EventRateChart()  # Reusable!
```

### 4. **Collaboration**
- Developer A: Works on `pages/dashboard.py`
- Developer B: Works on `pages/configuration.py`
- No git conflicts!

### 5. **Performance**
- Lazy loading: Import pages only when needed
- Smaller files = faster IDE loading
- Easier to optimize individual components

---

## Implementation Timeline

### Phase 1 (1-2 hours): Extract Components
✅ Create `components/` directory  
✅ Move StatusIndicator, SidebarButton, Charts  
✅ Update imports  
✅ Test that GUI still works  

### Phase 2 (2-3 hours): Extract Pages
✅ Create `pages/` directory  
✅ Move each page to separate file  
✅ Add `update()` methods for data binding  
✅ Test each page individually  

### Phase 3 (1 hour): Create Main Orchestrator
✅ Create `main_gui.py`  
✅ Move main window logic  
✅ Wire up signals between pages  
✅ Test full application  

### Phase 4 (30 minutes): Extract Theme + Monitor
✅ Move DARK_THEME to `theme.py`  
✅ Move DaemonMonitor to `daemon_monitor.py`  
✅ Final testing  

### Phase 5 (30 minutes): Update Documentation
✅ Update README with new structure  
✅ Add module docstrings  
✅ Create architecture diagram  

**Total Time:** ~5-6 hours

---

## Testing Checklist

After refactoring, verify:

- [ ] GUI launches without errors
- [ ] All 7 pages load correctly
- [ ] Status indicators animate
- [ ] Charts update with live data
- [ ] Configuration page functions work
  - [ ] Threshold slider
  - [ ] Process termination
  - [ ] Export functionality
- [ ] Alerts display correctly
- [ ] System tray icon works
- [ ] All imports resolve correctly

---

## Current Working Version

**For now, the single-file version (`fyp_gui.py`) is FULLY FUNCTIONAL with:**
- ✅ Gray/silver navbar icons
- ✅ Functional configuration page
- ✅ Process termination feature
- ✅ Data export
- ✅ Fixed ML insights formatting
- ✅ All 7 pages working

**You can use it as-is for your FYP demo!**

---

## When to Refactor?

### Refactor NOW if:
- Multiple people working on GUI
- Adding many more features
- Planning to reuse components
- Project will grow significantly

### Refactor LATER if:
- Demo deadline is soon
- Working alone
- Current code works well
- Focusing on other features (kernel/daemon)

---

## Quick Start (Current Version)

```bash
cd /home/fyp/project
./start.sh

# Or manually:
python3 gui/fyp_gui.py
```

Everything works! The modular refactoring is **optional** for better organization.
