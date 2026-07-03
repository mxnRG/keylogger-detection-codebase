import psutil
import pandas as pd
import keyboard
import time
import os
from datetime import datetime

print("Collecting Windows telemetry... Press CTRL+C to stop.")

# Create dataset folder if it doesn't exist
os.makedirs("../dataset", exist_ok=True)

csv_file = "../dataset/windows_benign_data.csv"

try:
    while True:

        # -----------------------------
        # Basic System Telemetry
        # -----------------------------
        cpu = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory().percent
        swap_memory = psutil.swap_memory().percent
        disk_usage = psutil.disk_usage('C:\\').percent
        boot_time = round((time.time() - psutil.boot_time()) / 60, 2)

        process_count = len(psutil.pids())
        cpu_threads = psutil.cpu_count()

        # -----------------------------
        # Keyboard Activity Monitoring
        # -----------------------------
        keyboard_events = 0

        start = time.time()

        while time.time() - start < 5:
            event = keyboard.read_event(suppress=False)

            if event.event_type == keyboard.KEY_DOWN:
                keyboard_events += 1

        # -----------------------------
        # Process-Based Telemetry
        # -----------------------------
        active_processes = 0
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
            "record"
        ]

        for proc in psutil.process_iter([
            'pid',
            'name',
            'cpu_percent',
            'memory_percent',
            'status'
        ]):

            try:
                active_processes += 1

                name = proc.info['name']

                if proc.info['cpu_percent'] > 10:
                    high_cpu_processes += 1

                if proc.info['memory_percent'] > 5:
                    high_memory_processes += 1

                if "python" in name.lower():
                    python_processes += 1

                if name.lower() in [
                    "powershell.exe",
                    "cmd.exe"
                ]:
                    shell_processes += 1

                if any(
                    keyword in name.lower()
                    for keyword in suspicious_names
                ):
                    suspicious_process_names += 1

                if proc.info['status'] == psutil.STATUS_ZOMBIE:
                    zombie_processes += 1

                # Thread count
                total_threads += proc.num_threads()

                # Open files
                try:
                    total_open_files += len(proc.open_files())
                except:
                    pass

                # Network connections
                try:
                    total_connections += len(proc.connections())
                except:
                    pass

            except:
                pass

        # -----------------------------
        # Network Telemetry
        # -----------------------------
        network_connections = len(psutil.net_connections())

        # -----------------------------
        # User Activity
        # -----------------------------
        users_logged_in = len(psutil.users())

        # -----------------------------
        # Timing Features
        # -----------------------------
        timestamp_now = datetime.now()

        hour = timestamp_now.hour
        minute = timestamp_now.minute
        second = timestamp_now.second

        # -----------------------------
        # Derived Behavioral Features
        # -----------------------------
        keyboard_to_process_ratio = round(
            keyboard_events / max(process_count, 1),
            4
        )

        cpu_to_keyboard_ratio = round(
            cpu / max(keyboard_events, 1),
            4
        )

        thread_to_process_ratio = round(
            total_threads / max(process_count, 1),
            4
        )

        # -----------------------------
        # Final Telemetry Row
        # -----------------------------
        row = {

            # Time
            "timestamp": timestamp_now,
            "hour": hour,
            "minute": minute,
            "second": second,

            # System telemetry
            "cpu_usage": cpu,
            "memory_usage": memory,
            "swap_memory": swap_memory,
            "disk_usage_percent": disk_usage,
            "system_uptime_minutes": boot_time,

            # Process telemetry
            "process_count": process_count,
            "active_processes": active_processes,
            "high_cpu_processes": high_cpu_processes,
            "high_memory_processes": high_memory_processes,
            "python_processes": python_processes,
            "shell_processes": shell_processes,
            "suspicious_process_names": suspicious_process_names,
            "zombie_processes": zombie_processes,

            # Threads
            "cpu_threads": cpu_threads,
            "total_threads": total_threads,
            "thread_to_process_ratio": thread_to_process_ratio,

            # Keyboard telemetry
            "keyboard_events": keyboard_events,
            "keyboard_to_process_ratio": keyboard_to_process_ratio,

            # Files & connections
            "total_open_files": total_open_files,
            "network_connections": network_connections,
            "total_connections": total_connections,

            # User telemetry
            "users_logged_in": users_logged_in,

            # Behavioral ratios
            "cpu_to_keyboard_ratio": cpu_to_keyboard_ratio,

            # Label
            "label": "benign"
        }

        # -----------------------------
        # Save Dataset
        # -----------------------------
        df = pd.DataFrame([row])

        # Append if file exists
        if os.path.exists(csv_file):
            df.to_csv(
                csv_file,
                mode='a',
                header=False,
                index=False
            )

        # Create file if it doesn't exist
        else:
            df.to_csv(
                csv_file,
                mode='w',
                header=True,
                index=False
            )

        print(row)

except KeyboardInterrupt:
    print("\nTelemetry collection stopped.")