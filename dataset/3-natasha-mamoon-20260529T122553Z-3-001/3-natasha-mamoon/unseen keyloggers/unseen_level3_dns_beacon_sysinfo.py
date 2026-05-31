# unseen_level3_dns_beacon_sysinfo.py
# Safe DNS-beacon + sysinfo dump simulator
# No real credentials. No real data sent. DNS resolution only (no data in query).
# Dummy chunks written to local .cache_test/ only.

import os
import socket
import subprocess
import threading
import time
import random
import string

CACHE_DIR = os.path.expanduser("~/.cache_test")
os.makedirs(CACHE_DIR, exist_ok=True)

running = True
beacon_count = 0
dump_count = 0

BEACON_DOMAINS = [
    "example.com",
    "example.org",
    "example.net",
]

def random_dummy_chunk(size=128):
    """Generates random dummy text — not real data."""
    return ''.join(random.choices(string.ascii_letters + string.digits, k=size))

def dns_beacon_thread():
    """Simulates C2-style DNS beaconing using only safe test domains."""
    global running, beacon_count
    while running:
        domain = random.choice(BEACON_DOMAINS)
        try:
            socket.gethostbyname(domain)
            beacon_count += 1
        except Exception:
            pass
        time.sleep(random.uniform(8, 15))

def sysinfo_dump_thread():
    """Collects harmless system info via subprocess and writes dummy chunks."""
    global running, dump_count
    cmds = [
        ["uname", "-a"],
        ["id"],
        ["hostname"],
        ["uptime"],
    ]
    while running:
        for cmd in cmds:
            try:
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=3)
                # We do NOT store the real output — store only a dummy chunk
                chunk = random_dummy_chunk(64)
                out_path = os.path.join(CACHE_DIR, f"chunk_{dump_count % 10}.tmp")
                with open(out_path, "w") as f:
                    f.write(chunk)
                dump_count += 1
            except Exception:
                pass
        time.sleep(10)

def chunk_rotate_thread():
    """Periodically overwrites chunk files with fresh dummy data (log rotation analog)."""
    global running
    while running:
        for i in range(10):
            path = os.path.join(CACHE_DIR, f"chunk_{i}.tmp")
            try:
                with open(path, "w") as f:
                    f.write(random_dummy_chunk(128))
            except Exception:
                pass
        time.sleep(20)

def reporter():
    while running:
        time.sleep(10)
        print(f"[reporter] DNS beacons: {beacon_count} | sysinfo dumps: {dump_count}")

if __name__ == "__main__":
    print("[*] Starting safe DNS beacon + sysinfo dump simulator...")
    threads = [
        threading.Thread(target=dns_beacon_thread, daemon=True),
        threading.Thread(target=sysinfo_dump_thread, daemon=True),
        threading.Thread(target=chunk_rotate_thread, daemon=True),
        threading.Thread(target=reporter, daemon=True),
    ]
    for t in threads:
        t.start()
    try:
        time.sleep(120)
    except KeyboardInterrupt:
        pass
    finally:
        running = False
        print("[*] Simulator stopped.")
