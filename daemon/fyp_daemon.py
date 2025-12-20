#!/usr/bin/env python3
"""
FYP Keylogger Detection Daemon v0.2 (Netlink Edition)

Receives keyboard behavioral events from kernel module via Netlink socket.
Applies detection heuristics and manages alerts.

Architecture:
- Netlink receiver thread (event-driven, no polling)
- Detection engine with 3 heuristics
- JSON status file writer for GUI communication

Academic prototype - clarity over performance.
"""

import os
import sys
import time
import json
import struct
import socket
import threading
import logging
import signal
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from datetime import datetime
from pathlib import Path

# Configure logging to file and console
log_handlers = [logging.StreamHandler()]
try:
    log_handlers.append(logging.FileHandler('/tmp/fyp_daemon.log'))
except PermissionError:
    print("Warning: Cannot write to /tmp/fyp_daemon.log, logging to console only")

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(name)s [%(levelname)s]: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=log_handlers
)
logger = logging.getLogger('FYP-Daemon')


# ========================================================================
# NETLINK CONFIGURATION
# ========================================================================

# Must match kernel module definition
NETLINK_FYP_DETECTOR = 31

# Netlink event structure (30 bytes - matches kernel struct)
# struct fyp_netlink_event {
#     u64 timestamp_ns;       // 8 bytes
#     u32 pid;                // 4 bytes
#     char comm[16];          // 16 bytes
#     u8 event_type;          // 1 byte (0=press, 1=release)
#     u8 rapid_flag;          // 1 byte
# }
NETLINK_EVENT_FORMAT = '<QI16sBB'  # Little-endian, 8+4+16+1+1 = 30 bytes
NETLINK_EVENT_SIZE = 30


# ========================================================================
# DATA STRUCTURES
# ========================================================================

@dataclass
class ProcessStats:
    """Per-process statistics tracker"""
    pid: int
    comm: str
    total_events: int = 0
    press_events: int = 0
    release_events: int = 0
    rapid_events: int = 0
    first_seen: float = field(default_factory=time.time)
    last_seen: float = field(default_factory=time.time)
    
    @property
    def rapid_ratio(self) -> float:
        """Calculate rapid event percentage"""
        if self.total_events == 0:
            return 0.0
        return (self.rapid_events / self.total_events) * 100.0
    
    @property
    def duration(self) -> float:
        """Time span of activity in seconds"""
        return max(self.last_seen - self.first_seen, 0.001)  # Avoid division by zero
    
    @property
    def events_per_second(self) -> float:
        """Average event rate"""
        return self.total_events / self.duration


@dataclass
class Alert:
    """Detection alert"""
    timestamp: float
    severity: str  # "LOW", "MEDIUM", "HIGH"
    process_name: str
    pid: int
    rule: str
    details: str
    
    def __str__(self):
        return (f"[{self.severity}] {self.rule}: {self.process_name} (PID {self.pid}) - "
                f"{self.details}")


# ========================================================================
# DETECTION ENGINE
# ========================================================================

class DetectionEngine:
    """Applies heuristic detection rules (NO ML)"""
    
    # Default heuristic thresholds
    RAPID_RATIO_THRESHOLD = 50.0  # % of events that are rapid
    DEFAULT_BURST_THRESHOLD = 100  # events per second (default)
    BURST_WINDOW = 2.0            # seconds to establish rate
    
    # Configuration file path
    CONFIG_FILE = Path("/tmp/fyp_daemon_config.json")
    
    # Process whitelist (known-good applications)
    WHITELIST = {
        'gnome-shell', 'Xorg', 'gdm-x-session',
        'bash', 'sh', 'zsh', 'fish',
        'python3', 'python', 'code', 'firefox',
        'gnome-terminal', 'konsole', 'xterm',
        'vim', 'nano', 'emacs',
        'swapper/0', 'swapper/1', 'swapper/2', 'swapper/3',  # Kernel idle
    }
    
    def __init__(self):
        self.alerts: List[Alert] = []
        self.alerted_pids: set = set()  # Track which PIDs we've alerted on
        self.BURST_THRESHOLD = self.DEFAULT_BURST_THRESHOLD
        self.config_mtime = 0  # Track config file modification time
        self.load_config()  # Load initial configuration
    
    def load_config(self):
        """Load threshold configuration from JSON file if it exists"""
        try:
            if self.CONFIG_FILE.exists():
                # Check if file has been modified since last load
                current_mtime = self.CONFIG_FILE.stat().st_mtime
                if current_mtime != self.config_mtime:
                    with open(self.CONFIG_FILE, 'r') as f:
                        config = json.load(f)
                    
                    # Update burst threshold if present
                    if 'burst_threshold' in config:
                        new_threshold = config['burst_threshold']
                        if self.BURST_THRESHOLD != new_threshold:
                            logger.info(f"✓ Config updated: BURST_THRESHOLD {self.BURST_THRESHOLD} → {new_threshold} eps")
                        self.BURST_THRESHOLD = new_threshold
                    
                    self.config_mtime = current_mtime
        except Exception as e:
            logger.warning(f"Failed to load config from {self.CONFIG_FILE}: {e}")
    
    def check_rapid_typing(self, stats: ProcessStats) -> Optional[Alert]:
        """Rule 1: Detect automated/rapid input stream fetching"""
        if stats.total_events < 20:  # Need minimum sample size
            return None
        
        if stats.rapid_ratio > self.RAPID_RATIO_THRESHOLD:
            # Only alert once per process
            key = (stats.pid, "rapid")
            if key in self.alerted_pids:
                return None
            self.alerted_pids.add(key)
            
            return Alert(
                timestamp=time.time(),
                severity="HIGH",
                process_name=stats.comm,
                pid=stats.pid,
                rule="Rapid Input Stream Access",
                details=f"Rapid fetching ratio: {stats.rapid_ratio:.1f}% "
                       f"(threshold: {self.RAPID_RATIO_THRESHOLD}%) - "
                       f"Process is accessing keyboard events too quickly"
            )
        return None
    
    def check_unknown_process(self, stats: ProcessStats) -> Optional[Alert]:
        """Rule 2: Flag processes not in whitelist"""
        if stats.total_events < 5:  # Avoid noise from transient processes
            return None
        
        if stats.comm not in self.WHITELIST:
            # Only alert once per process
            key = (stats.pid, "unknown")
            if key in self.alerted_pids:
                return None
            self.alerted_pids.add(key)
            
            return Alert(
                timestamp=time.time(),
                severity="MEDIUM",
                process_name=stats.comm,
                pid=stats.pid,
                rule="Unknown Process",
                details=f"Process '{stats.comm}' not in whitelist (may be legitimate)"
            )
        return None
    
    def check_burst_pattern(self, stats: ProcessStats) -> Optional[Alert]:
        """Rule 3: Detect burst of events in short time"""
        if stats.duration < self.BURST_WINDOW:
            return None  # Not enough time passed
        
        if stats.events_per_second > self.BURST_THRESHOLD:
            # Only alert once per process
            key = (stats.pid, "burst")
            if key in self.alerted_pids:
                return None
            self.alerted_pids.add(key)
            
            return Alert(
                timestamp=time.time(),
                severity="HIGH",
                process_name=stats.comm,
                pid=stats.pid,
                rule="Burst Pattern",
                details=f"Event rate: {stats.events_per_second:.1f} events/sec "
                       f"(threshold: {self.BURST_THRESHOLD})"
            )
        return None
    
    def evaluate(self, stats: ProcessStats) -> List[Alert]:
        """Apply all heuristics to process stats"""
        alerts = []
        
        # Check each rule
        if alert := self.check_rapid_typing(stats):
            alerts.append(alert)
        
        if alert := self.check_unknown_process(stats):
            alerts.append(alert)
        
        if alert := self.check_burst_pattern(stats):
            alerts.append(alert)
        
        return alerts


# ========================================================================
# NETLINK RECEIVER
# ========================================================================

class NetlinkReceiver:
    """Receives events from kernel via Netlink socket"""
    
    def __init__(self, callback):
        """
        Initialize Netlink receiver
        
        Args:
            callback: Function to call with each event dict
        """
        self.callback = callback
        self.sock = None
        self.running = False
        
    def start(self):
        """Create Netlink socket and register with kernel"""
        try:
            # Create Netlink socket
            self.sock = socket.socket(socket.AF_NETLINK, socket.SOCK_RAW, NETLINK_FYP_DETECTOR)
            self.sock.bind((os.getpid(), 0))
            
            logger.info(f"Netlink socket created (PID {os.getpid()}, protocol {NETLINK_FYP_DETECTOR})")
            
            # Register our PID with kernel module
            self._register_with_kernel()
            
            self.running = True
            logger.info("Netlink receiver started successfully")
            
        except OSError as e:
            logger.error(f"Failed to create Netlink socket: {e}")
            logger.error("Ensure kernel module is loaded: sudo insmod fyp_kbd.ko")
            raise
    
    def _register_with_kernel(self):
        """Send registration message to kernel module"""
        # Build Netlink message with our PID
        pid = os.getpid()
        nlmsg_len = 16 + 4  # Netlink header + u32 PID
        nlmsg_type = 0
        nlmsg_flags = 0
        nlmsg_seq = 0
        nlmsg_pid = pid
        
        # Pack Netlink header + PID payload
        msg = struct.pack('<IHHII', nlmsg_len, nlmsg_type, nlmsg_flags, nlmsg_seq, nlmsg_pid)
        msg += struct.pack('<I', pid)
        
        self.sock.send(msg)
        logger.info(f"Sent registration message to kernel (PID {pid})")
    
    def receive_loop(self):
        """Main receive loop (blocking)"""
        logger.info("Entering Netlink receive loop...")
        
        try:
            while self.running:
                # Receive Netlink message (blocking)
                data, addr = self.sock.recvfrom(4096)
                
                # Parse Netlink header (16 bytes)
                if len(data) < 16:
                    logger.warning(f"Received short message ({len(data)} bytes)")
                    continue
                
                # Skip Netlink header, extract event payload
                payload = data[16:]
                
                if len(payload) < NETLINK_EVENT_SIZE:
                    logger.warning(f"Invalid event size: {len(payload)} bytes (expected {NETLINK_EVENT_SIZE})")
                    continue
                
                # Parse event structure
                event = self._parse_event(payload[:NETLINK_EVENT_SIZE])
                if event:
                    self.callback(event)
                    
        except Exception as e:
            logger.error(f"Netlink receive loop error: {e}", exc_info=True)
        finally:
            self.running = False
            logger.info("Netlink receive loop stopped")
    
    def _parse_event(self, data: bytes) -> Optional[dict]:
        """
        Parse binary event structure from kernel
        
        Format: <QI16sBB (30 bytes total)
        - Q: u64 timestamp_ns
        - I: u32 pid
        - 16s: char[16] comm
        - B: u8 event_type (0=press, 1=release)
        - B: u8 rapid_flag
        """
        try:
            timestamp_ns, pid, comm_bytes, event_type, rapid_flag = struct.unpack(
                NETLINK_EVENT_FORMAT, data
            )
            
            # Decode process name (null-terminated string)
            comm = comm_bytes.decode('utf-8').rstrip('\x00')
            
            return {
                'timestamp_ns': timestamp_ns,
                'timestamp_ms': timestamp_ns // 1_000_000,  # Convert to ms
                'pid': pid,
                'comm': comm,
                'event_type': 'P' if event_type == 0 else 'R',
                'rapid_flag': bool(rapid_flag)
            }
        except Exception as e:
            logger.error(f"Failed to parse event: {e}")
            return None
    
    def stop(self):
        """Stop receiver and close socket"""
        self.running = False
        if self.sock:
            self.sock.close()
            logger.info("Netlink socket closed")


# ========================================================================
# MAIN DAEMON
# ========================================================================

class FYPDaemon:
    """Main daemon class"""
    
    PROCFS_STATS = "/proc/fyp_detector/stats"
    STATUS_FILE = "/tmp/fyp_status.json"
    
    def __init__(self):
        self.running = False
        self.process_stats: Dict[int, ProcessStats] = {}
        self.detection_engine = DetectionEngine()
        self.event_count = 0
        self.last_stats_time = time.time()
        self.recent_events: List[str] = []  # Keep last 100 events
        self.new_alerts: List[Alert] = []  # Alerts since last status write
        self.last_status_write = time.time()
        self.netlink_receiver = None
        
    def process_event(self, event: dict):
        """Process a single keyboard event from Netlink"""
        pid = event['pid']
        
        # Get or create process stats
        if pid not in self.process_stats:
            self.process_stats[pid] = ProcessStats(
                pid=pid,
                comm=event['comm']
            )
        
        stats = self.process_stats[pid]
        
        # Update statistics
        stats.total_events += 1
        stats.last_seen = time.time()
        
        if event['event_type'] == 'P':
            stats.press_events += 1
        elif event['event_type'] == 'R':
            stats.release_events += 1
        
        if event['rapid_flag']:
            stats.rapid_events += 1
        
        # Store recent event (for GUI display)
        event_line = f"{event['timestamp_ms']},{event['event_type']},{event['pid']},{event['comm']},{int(event['rapid_flag'])}"
        self.recent_events.append(event_line)
        if len(self.recent_events) > 100:
            self.recent_events.pop(0)
        
        # Update global counter
        self.event_count += 1
        
        # Apply detection rules periodically (every 10 events per process)
        if stats.total_events % 10 == 0:
            alerts = self.detection_engine.evaluate(stats)
            for alert in alerts:
                logger.warning(f"🚨 ALERT: {alert}")
                self.new_alerts.append(alert)
        
        # Write status file periodically
        if time.time() - self.last_status_write >= 0.5:
            self.write_status_file()
    
    def write_status_file(self):
        """Write current status to JSON file for GUI consumption"""
        try:
            # Build status data structure
            status = {
                'timestamp': datetime.now().isoformat(),
                'daemon_running': self.running,
                'kernel_loaded': os.path.exists(self.PROCFS_STATS),
                'total_events': self.event_count,
                'processes': {},
                'alerts': [],
                'recent_events': self.recent_events[-100:]
            }
            
            # Add process statistics
            for pid, stats in self.process_stats.items():
                status['processes'][str(pid)] = {
                    'comm': stats.comm,
                    'total_events': stats.total_events,
                    'rapid_ratio': round(stats.rapid_ratio, 1),
                    'events_per_second': round(stats.events_per_second, 1)
                }
            
            # Add new alerts
            for alert in self.new_alerts:
                status['alerts'].append({
                    'timestamp': datetime.fromtimestamp(alert.timestamp).isoformat(),
                    'severity': alert.severity,
                    'message': f"{alert.rule}: {alert.details}",
                    'process': alert.process_name,
                    'pid': alert.pid
                })
            
            if self.new_alerts:
                logger.info(f"Writing {len(self.new_alerts)} new alerts to status file")
            
            # Clear new alerts after adding to status
            self.new_alerts.clear()
            
            # Write atomically (write to temp file, then rename)
            temp_file = self.STATUS_FILE + '.tmp'
            with open(temp_file, 'w') as f:
                json.dump(status, f, indent=2)
            os.rename(temp_file, self.STATUS_FILE)
            
            # Update last write time
            self.last_status_write = time.time()
            
            logger.debug(f"Status file updated: {self.event_count} events, "
                        f"{len(self.process_stats)} processes")
            
        except Exception as e:
            logger.error(f"Failed to write status file: {e}", exc_info=True)
    
    def print_status(self):
        """Print periodic status summary"""
        now = time.time()
        if now - self.last_stats_time < 10:  # Every 10 seconds
            return
        
        self.last_stats_time = now
        
        # Count active processes (seen in last 5 seconds)
        active_procs = sum(1 for s in self.process_stats.values() 
                          if now - s.last_seen < 5)
        
        logger.info(f"Status: {self.event_count} events | "
                   f"{len(self.process_stats)} processes tracked | "
                   f"{active_procs} active | "
                   f"{len(self.detection_engine.alerts)} alerts")
    
    def check_kernel_module(self) -> bool:
        """Verify kernel module is loaded"""
        if not os.path.exists(self.PROCFS_STATS):
            logger.error("Kernel module not loaded!")
            logger.error("Please run: cd kernel && sudo insmod fyp_kbd.ko")
            return False
        
        logger.info("✓ Kernel module detected")
        return True
    
    def status_writer_thread(self):
        """Background thread that writes status file periodically"""
        logger.info("Status writer thread started")
        
        try:
            while self.running:
                time.sleep(1)  # Write every second
                self.write_status_file()
                self.print_status()
                
                # Reload config every cycle to pick up threshold changes
                self.detection_engine.load_config()
        except Exception as e:
            logger.error(f"Status writer error: {e}", exc_info=True)
        
        logger.info("Status writer thread stopped")
    
    def start(self):
        """Start the daemon"""
        logger.info("=" * 60)
        logger.info("FYP Keylogger Detection Daemon v0.2 (Netlink Edition)")
        logger.info("=" * 60)
        
        # Check prerequisites
        if not self.check_kernel_module():
            return
        
        logger.info("Starting daemon...")
        self.running = True
        
        # Create Netlink receiver
        self.netlink_receiver = NetlinkReceiver(callback=self.process_event)
        
        try:
            self.netlink_receiver.start()
        except Exception as e:
            logger.error(f"Failed to start Netlink receiver: {e}")
            return
        
        # Start status writer thread
        writer_thread = threading.Thread(target=self.status_writer_thread, daemon=True)
        writer_thread.start()
        
        logger.info("Daemon running. Press Ctrl+C to stop.")
        logger.info("Events will be delivered via Netlink (real-time, <1ms latency)")
        
        # Run Netlink receive loop (blocking)
        self.netlink_receiver.receive_loop()
    
    def stop(self):
        """Stop the daemon"""
        logger.info("\nShutdown requested...")
        self.running = False
        
        if self.netlink_receiver:
            self.netlink_receiver.stop()
        
        # Write final status
        self.write_status_file()
        
        # Print final statistics
        logger.info("=" * 60)
        logger.info("Final Statistics:")
        logger.info(f"  Total events processed: {self.event_count}")
        logger.info(f"  Unique processes: {len(self.process_stats)}")
        logger.info(f"  Total alerts: {len(self.detection_engine.alerts)}")
        
        # Show top processes by event count
        if self.process_stats:
            logger.info("\nTop processes by activity:")
            sorted_procs = sorted(self.process_stats.values(), 
                                 key=lambda x: x.total_events, reverse=True)[:5]
            for stats in sorted_procs:
                logger.info(f"  {stats.comm:16s} (PID {stats.pid:5d}): "
                          f"{stats.total_events:4d} events, "
                          f"{stats.rapid_ratio:5.1f}% rapid")
        
        logger.info("=" * 60)
        logger.info("Daemon stopped")


def main():
    """Main entry point"""
    daemon = FYPDaemon()
    
    # Handle Ctrl+C gracefully
    def signal_handler(sig, frame):
        daemon.stop()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    daemon.start()


if __name__ == '__main__':
    main()
