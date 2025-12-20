"""
FYP GUI Data Models
"""

from dataclasses import dataclass

@dataclass
class Alert:
    timestamp: str
    severity: str
    message: str
    process_name: str
    pid: int
    reviewed: bool = False
