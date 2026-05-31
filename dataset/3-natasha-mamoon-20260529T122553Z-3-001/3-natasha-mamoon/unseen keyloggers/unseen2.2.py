# unseen_level2_fifo_pipe_monitor.py
# Safe named-pipe IPC simulator — mimics inter-thread event passing in logger architectures
# No keystroke capture. No real data exfiltration.

import os
import time
import threading
import tempfile

FIFO_PATH = "/tmp/.cache_fifo_test"
running = True
event_count = 0

def writer_thread():
    """Continuously writes dummy event tokens into the FIFO."""
    global running
    while running:
        try:
            fd = os.open(FIFO_PATH, os.O_WRONLY | os.O_NONBLOCK)
            payload = b"EVT:dummy_keylike_event\n"
            os.write(fd, payload)
            os.close(fd)
        except OSError:
            pass
        time.sleep(0.1)

def reader_thread():
    """Continuously reads from the FIFO and discards content."""
    global running, event_count
    while running:
        try:
            fd = os.open(FIFO_PATH, os.O_RDONLY | os.O_NONBLOCK)
            data = os.read(fd, 256)
            os.close(fd)
            event_count += 1
        except OSError:
            pass
        time.sleep(0.1)

def reporter():
    while running:
        time.sleep(5)
        print(f"[reporter] FIFO events processed: {event_count}")

if __name__ == "__main__":
    # Create FIFO if it doesn't exist
    if not os.path.exists(FIFO_PATH):
        os.mkfifo(FIFO_PATH)
    print(f"[*] FIFO created at {FIFO_PATH}")
    print("[*] Starting safe named-pipe IPC simulator...")

    tw = threading.Thread(target=writer_thread, daemon=True)
    tr = threading.Thread(target=reader_thread, daemon=True)
    trep = threading.Thread(target=reporter, daemon=True)

    tw.start()
    tr.start()
    trep.start()

    try:
        time.sleep(60)
    except KeyboardInterrupt:
        pass
    finally:
        running = False
        if os.path.exists(FIFO_PATH):
            os.remove(FIFO_PATH)
        print("[*] Simulator stopped. FIFO removed.")
