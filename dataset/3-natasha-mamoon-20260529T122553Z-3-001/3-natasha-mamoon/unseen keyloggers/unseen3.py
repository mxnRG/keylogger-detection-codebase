import os
import time
import tarfile
import socket
from datetime import datetime

print("Running SAFE unseen Level 3 archive + beacon behavior...")

base = "unseen_level3_archive"
logs = os.path.join(base, "logs")
archive = os.path.join(base, "archives")

os.makedirs(logs, exist_ok=True)
os.makedirs(archive, exist_ok=True)

counter = 0

while True:
    try:
        log_path = os.path.join(logs, f"dummy_{counter}.log")

        with open(log_path, "w") as f:
            f.write(f"{datetime.now()} | dummy security telemetry event {counter}\n")

        if counter % 10 == 0:
            archive_path = os.path.join(archive, f"dummy_archive_{counter}.tar.gz")
            with tarfile.open(archive_path, "w:gz") as tar:
                tar.add(logs, arcname="logs")

        if counter % 5 == 0:
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(3)
                s.connect(("example.com", 80))
                s.send(b"HEAD / HTTP/1.1\r\nHost: example.com\r\nConnection: close\r\n\r\n")
                s.close()
            except Exception:
                pass

        counter += 1

    except Exception:
        pass

    time.sleep(1)
