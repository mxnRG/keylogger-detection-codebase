# unseen_level2_unix_socket_heartbeat.py
# Safe Unix domain socket IPC simulator — mimics logger heartbeat/IPC architecture
# No keystroke capture. No network traffic. Purely local.

import socket
import os
import time
import threading

SOCK_PATH = "/tmp/.cache_hb_test.sock"
running = True
hb_count = 0

def server_thread():
    """Listens on a Unix domain socket and discards received data."""
    global running
    if os.path.exists(SOCK_PATH):
        os.remove(SOCK_PATH)
    srv = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    srv.bind(SOCK_PATH)
    srv.listen(5)
    srv.settimeout(1.0)
    while running:
        try:
            conn, _ = srv.accept()
            data = conn.recv(256)
            conn.close()
            # Data discarded — not stored
        except socket.timeout:
            pass
        except Exception:
            pass
    srv.close()
    if os.path.exists(SOCK_PATH):
        os.remove(SOCK_PATH)

def client_thread():
    """Sends periodic dummy heartbeat messages to the server."""
    global running, hb_count
    time.sleep(0.5)  # Let server start first
    while running:
        try:
            cli = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            cli.connect(SOCK_PATH)
            cli.sendall(b"HB:alive\n")
            cli.close()
            hb_count += 1
        except Exception:
            pass
        time.sleep(0.2)

def reporter():
    while running:
        time.sleep(5)
        print(f"[reporter] Heartbeats sent: {hb_count}")

if __name__ == "__main__":
    print("[*] Starting safe Unix domain socket heartbeat simulator...")
    ts = threading.Thread(target=server_thread, daemon=True)
    tc = threading.Thread(target=client_thread, daemon=True)
    tr = threading.Thread(target=reporter, daemon=True)

    ts.start()
    tc.start()
    tr.start()

    try:
        time.sleep(60)
    except KeyboardInterrupt:
        pass
    finally:
        running = False
        print("[*] Simulator stopped.")
