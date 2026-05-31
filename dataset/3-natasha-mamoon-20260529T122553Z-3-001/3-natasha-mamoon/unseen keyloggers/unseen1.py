import os
import time
import gzip
import socket
import threading
import subprocess
from datetime import datetime

print("Running SAFE unseen Level 3 telemetry sample...")
print("No keystrokes, clipboard, or private data are collected.")

BASE_DIR = "unseen_level3_activity"
LOG_FILE = os.path.join(BASE_DIR, "activity.log")
ARCHIVE_DIR = os.path.join(BASE_DIR, "archive")

os.makedirs(BASE_DIR, exist_ok=True)
os.makedirs(ARCHIVE_DIR, exist_ok=True)

running = True


def write_dummy_activity():
    counter = 0

    while running:
        try:
            with open(LOG_FILE, "a") as f:
                f.write(
                    f"{datetime.now()} | dummy_monitor_event | "
                    f"event_id={counter} | status=active\n"
                )

            counter += 1
            time.sleep(0.7)

        except Exception:
            pass


def rotate_and_compress_logs():
    rotation_id = 0

    while running:
        try:
            time.sleep(15)

            if os.path.exists(LOG_FILE):
                archive_path = os.path.join(
                    ARCHIVE_DIR,
                    f"activity_{rotation_id}.log.gz"
                )

                with open(LOG_FILE, "rb") as src:
                    with gzip.open(archive_path, "wb") as dst:
                        dst.write(src.read())

                open(LOG_FILE, "w").close()
                rotation_id += 1

        except Exception:
            pass


def safe_network_heartbeat():
    while running:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(3)
            s.connect(("example.com", 80))

            request = (
                "HEAD / HTTP/1.1\r\n"
                "Host: example.com\r\n"
                "User-Agent: safe-unseen-telemetry-test\r\n"
                "Connection: close\r\n\r\n"
            )

            s.send(request.encode())
            s.close()

        except Exception:
            pass

        time.sleep(20)


def process_activity():
    while running:
        try:
            subprocess.run(
                ["whoami"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )

            subprocess.run(
                ["date"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )

        except Exception:
            pass

        time.sleep(5)


threads = [
    threading.Thread(target=write_dummy_activity, daemon=True),
    threading.Thread(target=rotate_and_compress_logs, daemon=True),
    threading.Thread(target=safe_network_heartbeat, daemon=True),
    threading.Thread(target=process_activity, daemon=True),
]

for t in threads:
    t.start()

try:
    while True:
        time.sleep(1)

except KeyboardInterrupt:
    running = False
    print("\nSafe unseen telemetry sample stopped.")
