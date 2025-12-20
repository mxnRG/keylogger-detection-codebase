"""
FYP GUI Pages Module
Modular page components for the detection system GUI
"""

from .dashboard import DashboardPage
from .alerts import AlertsPage
from .processes import ProcessesPage
from .event_stream import EventStreamPage
from .ai_assistant import AIAssistantPage
from .ml_insights import MLInsightsPage
from .configuration import ConfigurationPage

__all__ = [
    'DashboardPage',
    'AlertsPage',
    'ProcessesPage',
    'EventStreamPage',
    'AIAssistantPage',
    'MLInsightsPage',
    'ConfigurationPage'
]
