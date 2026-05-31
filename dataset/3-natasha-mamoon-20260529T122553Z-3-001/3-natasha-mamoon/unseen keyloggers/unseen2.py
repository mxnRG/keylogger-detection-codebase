import os
import glob
import time
from datetime import datetime

print("Running SAFE unseen Level 2 device scanner behavior...")

log_file = "unseen_level2_device_scan.log"

paths_to_scan = [
    "/dev/input/*",
    "/proc/bus/input/devices",
    "/proc/interrupts",
    "/proc/modules",
]

while True:
    try:
        for path_pattern in paths_to_scan:
            for path in glob.glob(path_pattern):
                try:
                    with open(path, "rb") as f:
                        f.read(128)
                except Exception:
                    pass

        with open(log_file, "a") as f:
            f.write(f"{datetime.now()} | device/proc scan cycle completed\n")

    except Exception:
        pass

    time.sleep(1)
