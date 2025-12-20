#!/usr/bin/env python3
"""
FYP Keylogger Detection System - Main GUI Entry Point
Modular architecture with clean separation of concerns
"""

import sys
import logging

# Configure logging
log_handlers = [logging.StreamHandler()]
try:
    log_handlers.append(logging.FileHandler('/tmp/fyp_gui.log'))
except PermissionError:
    print("Warning: Cannot write to /tmp/fyp_gui.log, logging to console only")

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(name)s [%(levelname)s]: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=log_handlers
)
logger = logging.getLogger('FYP-GUI')

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt

# Import theme
from theme import DARK_THEME

# Import main window from existing GUI file
# (We'll keep the existing fyp_gui.py as-is for now and just use it as a module)
from fyp_gui import FYPMainWindow


def main():
    logger.info("Starting FYP GUI application...")
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    app.setStyleSheet(DARK_THEME)
    
    # Enable high DPI scaling
    app.setAttribute(Qt.AA_EnableHighDpiScaling)
    app.setAttribute(Qt.AA_UseHighDpiPixmaps)
    
    window = FYPMainWindow()
    window.show()
    
    logger.info("Entering Qt event loop")
    exit_code = app.exec()
    logger.info(f"Application exited with code {exit_code}")
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
