#!/usr/bin/env python3
"""
Telemetry collection for ML dataset generation.

Linux note: the `keyboard` module typically requires root to access input devices.
"""

import argparse
import os
import time
from datetime import datetime
from pathlib import Path

import psutil
import pandas as pd
import keyboard


def parse_args():
    default_output = Path(__file__).resolve().parent / ".." / "dataset" / "benign_data.csv"
    parser = argparse.ArgumentParser(description="Collect system telemetry for ML dataset.")
    parser.add_argument(
        "--output",
        default=str(default_output),
        help="Output CSV path (default: ../dataset/benign_data.csv relative to this script)",
    )
    parser.add_argument(
        "--label",
        default="benign",
        help="Label to write for each row (default: benign)",
    )
    parser.add_argument(
        "--keyboard-window",
        type=float,
        default=2.0,
        help="Seconds to sample keyboard activity per row (default: 2.0)",
    )
    parser.add_argument(
        "--cpu-interval",
        type=float,
        default=0.3,
        help="Seconds for psutil CPU percent interval (default: 0.3)",
    )
    return parser.parse_args()


def require_keyboard_access():
    if hasattr(os, "geteuid") and os.geteuid() != 0:
        raise PermissionError(
            "The 'keyboard' module needs root on most Linux systems. Run with sudo."
        )
    try:
        keyboard.is_pressed("a")
    except Exception as exc:
        raise PermissionError(
            "Keyboard access failed. Run with sudo or ensure input device permissions."
        ) from exc


def main():
    args = parse_args()

    print("Collecting optimized Linux telemetry... Press CTRL+C to stop.")

    output_path = Path(args.output).expanduser().resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    require_keyboard_access()

    # Prime process CPU counters so we get non-zero values on the next read.
    for proc in psutil.process_iter():
        try:
            proc.cpu_percent(None)
        except Exception:
            pass

    try:
        while True:
            # ---------------------------------
            # Basic System Telemetry
            # ---------------------------------
            cpu = psutil.cpu_percent(interval=args.cpu_interval)
            memory = psutil.virtual_memory().percent
            swap_memory = psutil.swap_memory().percent
            disk_usage = psutil.disk_usage("/").percent
            system_uptime = round((time.time() - psutil.boot_time()) / 60, 2)
            process_count = len(psutil.pids())
            cpu_threads = psutil.cpu_count()

            # ---------------------------------
            # Keyboard Activity Monitoring
            # ---------------------------------
            keyboard_events = 0
            start = time.time()

            while time.time() - start < args.keyboard_window:
                if keyboard.is_pressed("a"):
                    keyboard_events += 1

                if keyboard.is_pressed("space"):
                    keyboard_events += 1

                time.sleep(0.02)

            # ---------------------------------
            # Process Snapshot (speed optimized)
            # ---------------------------------
            all_processes = list(
                psutil.process_iter([
                    "pid",
                    "name",
                    "cpu_percent",
                    "memory_percent",
                    "terminal",
                    "status",
                ])
            )

            # ---------------------------------
            # Process Telemetry
            # ---------------------------------
            active_processes = 0
            background_processes = 0
            high_cpu_processes = 0
            high_memory_processes = 0
            python_processes = 0
            shell_processes = 0
            suspicious_process_names = 0
            zombie_processes = 0
            total_threads = 0
            total_open_files = 0
            total_connections = 0

            suspicious_names = [
                "keylogger",
                "logger",
                "hook",
                "monitor",
                "spy",
                "capture",
                "record",
            ]

            for proc in all_processes:
                try:
                    active_processes += 1
                    name = proc.info.get("name") or ""

                    if proc.info.get("terminal") is None:
                        background_processes += 1

                    if (proc.info.get("cpu_percent") or 0) > 10:
                        high_cpu_processes += 1

                    if (proc.info.get("memory_percent") or 0) > 5:
                        high_memory_processes += 1

                    if "python" in name.lower():
                        python_processes += 1

                    if name.lower() in ["bash", "sh", "zsh"]:
                        shell_processes += 1

                    if any(keyword in name.lower() for keyword in suspicious_names):
                        suspicious_process_names += 1

                    if proc.info.get("status") == psutil.STATUS_ZOMBIE:
                        zombie_processes += 1

                    total_threads += proc.num_threads()

                    try:
                        total_open_files += len(proc.open_files())
                    except Exception:
                        pass

                    try:
                        total_connections += len(proc.net_connections())
                    except Exception:
                        pass

                except Exception:
                    pass

            # ---------------------------------
            # Network Telemetry
            # ---------------------------------
            try:
                network_connections = len(psutil.net_connections())
            except Exception:
                network_connections = 0

            # ---------------------------------
            # User Activity
            # ---------------------------------
            try:
                users_logged_in = len(psutil.users())
            except Exception:
                users_logged_in = 0

            # ---------------------------------
            # Time Features
            # ---------------------------------
            timestamp_now = datetime.now()
            hour = timestamp_now.hour
            minute = timestamp_now.minute
            second = timestamp_now.second

            # ---------------------------------
            # Behavioral Ratios
            # ---------------------------------
            keyboard_to_process_ratio = round(
                keyboard_events / max(process_count, 1),
                4,
            )

            cpu_to_keyboard_ratio = round(
                cpu / max(keyboard_events, 1),
                4,
            )

            thread_to_process_ratio = round(
                total_threads / max(process_count, 1),
                4,
            )

            # ---------------------------------
            # Final Telemetry Row
            # ---------------------------------
            row = {
                # Time
                "timestamp": timestamp_now.isoformat(),
                "hour": hour,
                "minute": minute,
                "second": second,

                # System telemetry
                "cpu_usage": cpu,
                "memory_usage": memory,
                "swap_memory": swap_memory,
                "disk_usage_percent": disk_usage,
                "system_uptime_minutes": system_uptime,

                # Process telemetry
                "process_count": process_count,
                "active_processes": active_processes,
                "background_processes": background_processes,
                "high_cpu_processes": high_cpu_processes,
                "high_memory_processes": high_memory_processes,
                "python_processes": python_processes,
                "shell_processes": shell_processes,
                "suspicious_process_names": suspicious_process_names,
                "zombie_processes": zombie_processes,

                # Thread telemetry
                "cpu_threads": cpu_threads,
                "total_threads": total_threads,
                "thread_to_process_ratio": thread_to_process_ratio,

                # Keyboard telemetry
                "keyboard_events": keyboard_events,
                "keyboard_to_process_ratio": keyboard_to_process_ratio,

                # Files & network
                "total_open_files": total_open_files,
                "network_connections": network_connections,
                "total_connections": total_connections,

                # User telemetry
                "users_logged_in": users_logged_in,

                # Behavioral ratios
                "cpu_to_keyboard_ratio": cpu_to_keyboard_ratio,

                # Label
                "label": args.label,
            }

            # ---------------------------------
            # Save to CSV
            # ---------------------------------
            df = pd.DataFrame([row])

            if output_path.exists():
                df.to_csv(output_path, mode="a", header=False, index=False)
            else:
                df.to_csv(output_path, mode="w", header=True, index=False)

            print(row)

    except KeyboardInterrupt:
        print("\nTelemetry collection stopped.")


if __name__ == "__main__":
    main()
