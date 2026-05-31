# unseen_level2_stat_metadata_poller.py
# Safe metadata polling simulator — mimics file-watch behavior of basic loggers
# Does NOT read file contents. Does NOT capture keystrokes.

import os
import time
import threading

WATCH_TARGETS = [
    os.path.expanduser("~/.bashrc"),
    os.path.expanduser("~/.profile"),
    os.path.expanduser("~/.bash_history"),
    "/etc/hostname",
    "/etc/os-release",
    "/proc/uptime",
    "/proc/loadavg",
    "/proc/version",
    "/tmp",
    "/var/log",
]

poll_count = 0
lock = threading.Lock()
running = True

def stat_poll_worker(targets, interval=0.05):
    global poll_count
    while running:
        for path in targets:
            try:
                st = os.stat(path)
                _ = st.st_mtime  # access mtime only
            except Exception:
                pass
        with lock:
            poll_count += 1
        time.sleep(interval)
def reporter():
    while running:
        time.sleep(5)
        with lock:
            print(f"[reporter] Poll cycles completed: {poll_count}")

if __name__ == "__main__":
    print("[*] Starting safe stat/metadata polling simulator...")

    # Two worker threads with slightly staggered intervals
    t1 = threading.Thread(target=stat_poll_worker, args=(WATCH_TARGETS, 0.05), daemon=True)
    t2 = threading.Thread(target=stat_poll_worker, args=(WATCH_TARGETS[:5], 0.08), daemon=True)
    t3 = threading.Thread(target=reporter, daemon=True)

    t1.start()
    t2.start()
    t3.start()

    try:
        time.sleep(60)
    except KeyboardInterrupt:
        pass
    finally:
        running = False
        print("[*] Simulator stopped.")
