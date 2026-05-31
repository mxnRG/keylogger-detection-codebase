# unseen_level3_agent_collector_queue.py
# Safe multi-agent queue-based simulator — mimics logger agent/collector architecture
# No keystroke capture. No clipboard. No real exfiltration.

import os
import time
import threading
import queue
import socket
import random
import string
import tempfile

running = True
event_queue = queue.Queue(maxsize=500)
LOCAL_PORT = 19876

CACHE_DIR = tempfile.mkdtemp(prefix=".cache_agent_")

def random_token(n=32):
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=n))

# --- Agent: generates dummy event tokens at high rate ---
def event_agent():
    global running
    while running:
        token = f"EVT:{random_token(24)}:{time.time():.3f}"
        try:
            event_queue.put_nowait(token)
        except queue.Full:
            pass
        time.sleep(0.05)

# --- Collector: dequeues and writes to rotating temp files ---
def collector_agent():
    global running
    batch = []
    file_idx = 0
    while running:
        try:
            item = event_queue.get(timeout=0.5)
            batch.append(item)
            if len(batch) >= 20:
                path = os.path.join(CACHE_DIR, f"batch_{file_idx % 5}.log")
                with open(path, "w") as f:
                    f.write("\n".join(batch))
                batch.clear()
                file_idx += 1
        except queue.Empty:
            pass

# --- Network agent: sends dummy payload to local TCP server ---
def net_agent():
    global running
    while running:
        try:
            with socket.create_connection(("127.0.0.1", LOCAL_PORT), timeout=1) as s:
                s.sendall(b"PING:" + random_token(16).encode() + b"\n")
        except Exception:
            pass
        time.sleep(3)

# --- Local TCP server: accepts and discards ---
def local_server():
    global running
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(("127.0.0.1", LOCAL_PORT))
    srv.listen(10)
    srv.settimeout(1.0)
    while running:
        try:
            conn, _ = srv.accept()
            conn.recv(256)
            conn.close()
        except socket.timeout:
            pass
        except Exception:
            pass
    srv.close()

def reporter():
    while running:
        time.sleep(8)
        qsize = event_queue.qsize()
        files = os.listdir(CACHE_DIR)
        print(f"[reporter] Queue size: {qsize} | Batch files: {len(files)}")

if __name__ == "__main__":
    print(f"[*] Cache dir: {CACHE_DIR}")
    print("[*] Starting safe agent/collector queue simulator...")
    threads = [
        threading.Thread(target=local_server, daemon=True),
        threading.Thread(target=event_agent, daemon=True),
        threading.Thread(target=collector_agent, daemon=True),
        threading.Thread(target=net_agent, daemon=True),
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
