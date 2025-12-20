# FYP GUI - Modular Structure

## Directory Layout

```
gui/
├── main_gui.py              # Main entry point (60 lines)
├── fyp_gui.py              # Main window + page implementations (1950 lines)
├── theme.py                # Dark theme stylesheet (300 lines)
├── models.py               # Data models (Alert class)
├── daemon_monitor.py       # Daemon monitoring (100 lines)
├── components/             # Reusable UI components
│   ├── __init__.py
│   ├── widgets.py          # StatusIndicator, SidebarButton
│   └── charts.py           # EventRateChart, ProcessBarChart
└── pages/                  # Page implementations (ready for extraction)
    └── __init__.py
```

## Component Modules

### 1. `main_gui.py` - Entry Point
- Initializes QApplication
- Applies theme
- Launches main window
- **Usage:** `python3 main_gui.py`

### 2. `theme.py` - Styling
- GitHub-inspired dark theme
- All QSS stylesheets
- Color definitions
- **Import:** `from theme import DARK_THEME`

### 3. `models.py` - Data Classes
- `Alert` dataclass
- Future: Add more models as needed
- **Import:** `from models import Alert`

### 4. `daemon_monitor.py` - Monitoring
- `DaemonMonitor` class
- Polls `/tmp/fyp_status.json`
- Emits signals for updates
- **Import:** `from daemon_monitor import DaemonMonitor`

### 5. `components/` - Reusable Widgets

#### `components/widgets.py`
- `StatusIndicator`: Animated status dot with pulse
- `SidebarButton`: Custom navigation button

#### `components/charts.py`
- `EventRateChart`: Real-time line chart (60fps)
- `ProcessBarChart`: Top processes bar chart

**Import:** `from components import StatusIndicator, EventRateChart`

### 6. `fyp_gui.py` - Main Window & Pages
- `FYPMainWindow`: Main application window
- All 7 page creation methods
- Event handlers
- System tray integration
- **Note:** Pages ready to extract to `pages/` directory

## Running the GUI

### Option 1: Use start script (recommended)
```bash
cd /home/fyp/project
./start.sh
```

### Option 2: Run directly
```bash
cd /home/fyp/project/gui
python3 main_gui.py
```

### Option 3: Old method (still works)
```bash
cd /home/fyp/project/gui
python3 fyp_gui.py
```

## Benefits of Modular Structure

### ✅ Separation of Concerns
- Theme in one file
- Components reusable
- Clear dependencies

### ✅ Easier Testing
```python
# Test individual components
from components import StatusIndicator
indicator = StatusIndicator()
indicator.set_status('success', pulse=True)
```

### ✅ Parallel Development
- Developer A: Work on charts
- Developer B: Work on pages
- No merge conflicts!

### ✅ Cleaner Imports
```python
# Before (monolithic)
from fyp_gui import StatusIndicator, EventRateChart, DARK_THEME, Alert

# After (modular)
from theme import DARK_THEME
from models import Alert
from components import StatusIndicator, EventRateChart
```

## Next Steps (Optional)

### Phase 1: Extract Pages
Move each page to `pages/` directory:
- `pages/dashboard.py`
- `pages/alerts.py`
- `pages/processes.py`
- `pages/event_stream.py`
- `pages/ai_assistant.py`
- `pages/ml_insights.py`
- `pages/configuration.py`

### Phase 2: Refactor Main Window
Simplify `FYPMainWindow` to use page modules:
```python
from pages import DashboardPage, AlertsPage, ConfigurationPage

class FYPMainWindow(QMainWindow):
    def init_ui(self):
        self.pages = {
            "dashboard": DashboardPage(self),
            "alerts": AlertsPage(self),
            "config": ConfigurationPage(self)
        }
```

### Phase 3: Unit Tests
Create tests for components:
```python
# tests/test_components.py
def test_status_indicator():
    indicator = StatusIndicator()
    assert indicator._opacity == 1.0
    indicator.set_status('error', pulse=True)
    assert indicator._color == QColor(218, 54, 51)
```

## Current Status

✅ **Working:**
- All components extracted and functional
- Theme separated
- Models isolated
- Daemon monitor standalone
- Entry point created
- Start script updated

⏳ **Pending (Optional):**
- Page extraction to `pages/` directory
- Further FYPMainWindow simplification
- Unit test framework

## Dependencies

All imports are properly configured:
- `main_gui.py` → imports everything
- `components/` → self-contained (only Qt imports)
- `daemon_monitor.py` → imports from `models.py`
- No circular dependencies

## Backwards Compatibility

The old way still works:
```bash
python3 gui/fyp_gui.py  # ✓ Still functional
```

But new way is cleaner:
```bash
python3 gui/main_gui.py  # ✓ Recommended
```

## File Sizes

| File | Lines | Purpose |
|------|-------|---------|
| `main_gui.py` | 60 | Entry point |
| `theme.py` | 300 | Stylesheets |
| `models.py` | 10 | Data classes |
| `daemon_monitor.py` | 100 | Monitoring |
| `components/widgets.py` | 100 | UI widgets |
| `components/charts.py` | 150 | Chart components |
| `fyp_gui.py` | 1950 | Main window + pages |

**Total:** ~2670 lines (was 1950 monolithic)  
**Reduction in main file:** Still large, but ready for page extraction

## Summary

The GUI is now **modular and maintainable**:
- ✅ Clear separation of concerns
- ✅ Reusable components
- ✅ Independent modules
- ✅ Cleaner imports
- ✅ Ready for testing
- ✅ Backwards compatible

The refactoring provides a solid foundation for future development while keeping everything functional!
