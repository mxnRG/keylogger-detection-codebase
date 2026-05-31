import os
import time
import threading
import subprocess
from datetime import datetime

print("Running SAFE unseen Level 3 process worker behavior...")

running = True
log_file = "unseen_level3_process_worker.log"


def file_writer():
    i = 0
    while running:
        with open(log_file, "a") as f:
            f.write(f"{datetime.now()} | background worker event {i}\n")
        i += 1
        time.sleep(0.5)


def command_runner():
    while running:
        try:
            subprocess.run(["whoami"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            subprocess.run(["uname", "-a"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            subprocess.run(["ps", "aux"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            pass
        time.sleep(3)


threading.Thread(target=file_writer, daemon=True).start()
threading.Thread(target=command_runner, daemon=True).start()

try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    running = False
    print("Stopped.")
