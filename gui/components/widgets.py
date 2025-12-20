"""
FYP GUI Reusable Components
"""

from PySide6.QtWidgets import QWidget, QPushButton
from PySide6.QtCore import Property, QPropertyAnimation, QEasingCurve, Qt
from PySide6.QtGui import QPainter, QColor, QBrush, QPen, QRadialGradient


class StatusIndicator(QWidget):
    """Animated pulsing status indicator"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(12, 12)
        self._color = QColor(139, 148, 158)  # Gray
        self._opacity = 1.0
        
        # Pulse animation
        self.pulse_animation = QPropertyAnimation(self, b"opacity")
        self.pulse_animation.setDuration(1500)
        self.pulse_animation.setStartValue(1.0)
        self.pulse_animation.setEndValue(0.3)
        self.pulse_animation.setEasingCurve(QEasingCurve.InOutQuad)
        self.pulse_animation.setLoopCount(-1)
        
    def set_status(self, status: str, pulse: bool = False):
        color_map = {
            'success': QColor(46, 160, 67),    # Green
            'warning': QColor(212, 167, 44),   # Yellow
            'error': QColor(218, 54, 51),      # Red
            'unknown': QColor(139, 148, 158)   # Gray
        }
        self._color = color_map.get(status, color_map['unknown'])
        
        if pulse:
            self.pulse_animation.start()
        else:
            self.pulse_animation.stop()
            self._opacity = 1.0
        
        self.update()
    
    def get_opacity(self):
        return self._opacity
    
    def set_opacity(self, value):
        self._opacity = value
        self.update()
    
    opacity = Property(float, get_opacity, set_opacity)
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setOpacity(self._opacity)
        
        # Glow effect
        gradient = QRadialGradient(6, 6, 6)
        gradient.setColorAt(0, self._color.lighter(130))
        gradient.setColorAt(0.7, self._color)
        gradient.setColorAt(1, self._color.darker(120))
        
        painter.setBrush(QBrush(gradient))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(1, 1, 10, 10)


class SidebarButton(QPushButton):
    """Custom sidebar navigation button with hover animation"""
    def __init__(self, text, icon_text, parent=None):
        super().__init__(parent)
        self.setText(f"  {icon_text}  {text}")
        self.setObjectName("sidebarButton")
        self.setCursor(Qt.PointingHandCursor)
        self.setMinimumHeight(44)
        self.selected = False
        
        # Hover animation
        self.hover_animation = QPropertyAnimation(self, b"styleSheet")
        self.hover_animation.setDuration(150)
        self.hover_animation.setEasingCurve(QEasingCurve.OutCubic)
        
    def set_selected(self, selected: bool):
        self.selected = selected
        self.setProperty("selected", "true" if selected else "false")
        self.style().unpolish(self)
        self.style().polish(self)
        
    def enterEvent(self, event):
        if not self.selected:
            # Smooth hover effect already in QSS
            pass
        super().enterEvent(event)
