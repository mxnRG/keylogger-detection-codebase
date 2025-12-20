"""
FYP GUI Chart Components
"""

from collections import deque
from PySide6.QtCharts import QChartView, QChart, QSplineSeries, QBarSeries, QBarSet, QValueAxis, QBarCategoryAxis
from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Qt, QMargins
from PySide6.QtGui import QPainter, QColor, QBrush, QPen, QFont


class EventRateChart(QChartView):
    """Smooth real-time event rate chart with 60fps"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setRenderHint(QPainter.Antialiasing)
        
        # Enable OpenGL for 60fps smooth rendering
        try:
            from PySide6.QtOpenGLWidgets import QOpenGLWidget
            gl_widget = QOpenGLWidget()
            self.setViewport(gl_widget)
        except:
            pass  # Fallback to software rendering if OpenGL not available
        
        self.time_points = deque(maxlen=60)
        self.rate_points = deque(maxlen=60)
        
        self.chart = QChart()
        self.chart.setTheme(QChart.ChartThemeDark)
        self.chart.setBackgroundBrush(QBrush(QColor(22, 27, 34)))
        self.chart.setTitleBrush(QBrush(QColor(240, 246, 252)))
        self.chart.setTitleFont(QFont('Inter', 14, QFont.Bold))
        self.chart.setTitle("Event Rate Over Time")
        self.chart.legend().hide()
        self.chart.setMargins(QMargins(0, 0, 0, 0))
        
        # Use spline for smooth curves
        self.series = QSplineSeries()
        self.series.setColor(QColor(31, 111, 235))
        self.series.setPen(QPen(QColor(31, 111, 235), 3))
        self.chart.addSeries(self.series)
        
        # Axes with better styling
        self.axis_x = QValueAxis()
        self.axis_x.setRange(0, 60)
        self.axis_x.setTitleText("Time (seconds ago)")
        self.axis_x.setTitleFont(QFont('Inter', 10))
        self.axis_x.setLabelsFont(QFont('Inter', 9))
        self.axis_x.setLabelsColor(QColor(139, 148, 158))
        self.axis_x.setTitleBrush(QBrush(QColor(139, 148, 158)))
        self.axis_x.setGridLineColor(QColor(48, 54, 61))
        
        self.axis_y = QValueAxis()
        self.axis_y.setRange(0, 100)
        self.axis_y.setTitleText("Events/second")
        self.axis_y.setTitleFont(QFont('Inter', 10))
        self.axis_y.setLabelsFont(QFont('Inter', 9))
        self.axis_y.setLabelsColor(QColor(139, 148, 158))
        self.axis_y.setTitleBrush(QBrush(QColor(139, 148, 158)))
        self.axis_y.setGridLineColor(QColor(48, 54, 61))
        
        self.chart.addAxis(self.axis_x, Qt.AlignBottom)
        self.chart.addAxis(self.axis_y, Qt.AlignLeft)
        self.series.attachAxis(self.axis_x)
        self.series.attachAxis(self.axis_y)
        
        self.setChart(self.chart)
        
        # Enable OpenGL for better performance
        self.setRenderHint(QPainter.Antialiasing)
        
    def add_data_point(self, events_per_sec: float):
        self.time_points.append(0)
        self.rate_points.append(events_per_sec)
        
        for i in range(len(self.time_points) - 1):
            self.time_points[i] += 1
        
        # Update series with smooth animation
        self.series.clear()
        for i in range(len(self.time_points)):
            x = 60 - self.time_points[i]
            y = self.rate_points[i]
            self.series.append(x, y)
        
        if self.rate_points:
            max_rate = max(self.rate_points)
            self.axis_y.setRange(0, max(100, max_rate * 1.2))
            
            # Color code based on severity
            if max_rate > 100:
                self.series.setColor(QColor(218, 54, 51))  # Red
                self.series.setPen(QPen(QColor(218, 54, 51), 3))
            elif max_rate > 50:
                self.series.setColor(QColor(212, 167, 44))  # Yellow
                self.series.setPen(QPen(QColor(212, 167, 44), 3))
            else:
                self.series.setColor(QColor(46, 160, 67))  # Green
                self.series.setPen(QPen(QColor(46, 160, 67), 3))


class ProcessBarChart(QChartView):
    """Horizontal bar chart for top processes"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setRenderHint(QPainter.Antialiasing)
        
        # Enable OpenGL for 60fps smooth rendering
        try:
            from PySide6.QtOpenGLWidgets import QOpenGLWidget
            gl_widget = QOpenGLWidget()
            self.setViewport(gl_widget)
        except:
            pass  # Fallback to software rendering
        
        self.chart = QChart()
        self.chart.setTheme(QChart.ChartThemeDark)
        self.chart.setBackgroundBrush(QBrush(QColor(22, 27, 34)))
        self.chart.setTitleBrush(QBrush(QColor(240, 246, 252)))
        self.chart.setTitleFont(QFont('Inter', 14, QFont.Bold))
        self.chart.setTitle("Top Active Processes")
        self.chart.legend().hide()
        self.chart.setMargins(QMargins(0, 0, 0, 0))
        
        self.series = QBarSeries()
        self.chart.addSeries(self.series)
        
        self.axis_x = QBarCategoryAxis()
        self.axis_x.setLabelsFont(QFont('Inter', 9))
        self.axis_x.setLabelsColor(QColor(139, 148, 158))
        
        self.axis_y = QValueAxis()
        self.axis_y.setTitleText("Event Count")
        self.axis_y.setTitleFont(QFont('Inter', 10))
        self.axis_y.setLabelsFont(QFont('Inter', 9))
        self.axis_y.setLabelsColor(QColor(139, 148, 158))
        self.axis_y.setTitleBrush(QBrush(QColor(139, 148, 158)))
        self.axis_y.setGridLineColor(QColor(48, 54, 61))
        
        self.chart.addAxis(self.axis_x, Qt.AlignBottom)
        self.chart.addAxis(self.axis_y, Qt.AlignLeft)
        self.series.attachAxis(self.axis_x)
        self.series.attachAxis(self.axis_y)
        
        self.setChart(self.chart)
        
    def update_data(self, processes: dict):
        sorted_procs = sorted(processes.items(), key=lambda x: x[1].get('total_events', 0), reverse=True)[:5]
        if not sorted_procs:
            return
        
        self.series.clear()
        bar_set = QBarSet("Events")
        bar_set.setColor(QColor(31, 111, 235))
        
        categories = []
        for pid, stats in sorted_procs:
            comm = stats.get('comm', 'unknown')
            categories.append(f"{comm}\n({pid})")
            bar_set.append(stats.get('total_events', 0))
        
        self.series.append(bar_set)
        self.axis_x.setCategories(categories)
        
        max_events = max(stats.get('total_events', 0) for _, stats in sorted_procs)
        self.axis_y.setRange(0, max(10, max_events * 1.2))
