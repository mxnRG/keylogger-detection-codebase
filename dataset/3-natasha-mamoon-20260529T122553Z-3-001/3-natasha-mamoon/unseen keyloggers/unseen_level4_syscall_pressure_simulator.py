# unseen_level4_syscall_pressure_simulator.py
# Safe Level 4-like syscall pressure simulator
# Mimics LKM-style kernel read/write pressure using ONLY userspace syscalls
# No kernel module. No insmod. No module hiding. No privilege escalation.

import os
import time
import threading
import subprocess
import random

running = True
read_count = 0
write_count = 0
exec_count = 0

PROC_TARGETS = [
    "/proc/self/status",
    "/proc/self/maps",
    "/proc/self/fd",
    "/proc/uptime",
    "/proc/loadavg",
    "/proc/meminfo",
    "/proc/stat",
    "/proc/net/dev",
    "/proc/modules",
    "/proc/interrupts",
    "/proc/sys/kernel/hostname",
    "/proc/sys/kernel/ostype",
]

SYS_TARGETS = [
    "/sys/module",
    "/sys/class",
    "/sys/devices",
    "/sys/kernel",
    "/sys/bus",
]

WRITE_TMP = "/tmp/.l4_pressure_tmp"

def syscall_read_pressure():
    """Rapid read() pressure on /proc entries — mimics kernel data inspection."""
    global running, read_count
    while running:
        for path in PROC_TARGETS:
            try:
                fd = os.open(path, os.O_RDONLY)
                os.read(fd, 512)
                os.close(fd)
                read_count += 1
            except Exception:
                pass
        time.sleep(0.02)

def syscall_write_pressure():
    """Rapid write() pressure on a tmp file — mimics kernel buffer write behavior."""
    global running, write_count
    while running:
        try:
            fd = os.open(WRITE_TMP, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
            for _ in range(20):
                os.write(fd, b"\x00" * 64)
                write_count += 1
            os.close(fd)
        except Exception:
            pass
        time.sleep(0.05)

def sys_stat_pressure():
    """Rapid stat() on /sys entries — mimics sysfs module enumeration."""
    global running
    while running:
        for path in SYS_TARGETS:
            try:
                entries = os.listdir(path)
                for entry in entries[:5]:
                    os.stat(os.path.join(path, entry))
            except Exception:
                pass
        time.sleep(0.1)

def subprocess_burst():
    """Spawns short subprocess bursts mimicking LKM inspection tools."""
    global running, exec_count
    cmds = [
        ["cat", "/proc/modules"],
        ["ls", "/sys/module"],
        ["cat", "/proc/interrupts"],
        ["cat", "/proc/kallsyms"],
        ["dmesg", "--level=err"],
        ["cat", "/proc/self/status"],
    ]
    while running:
        cmd = random.choice(cmds)
        try:
            subprocess.run(cmd, capture_output=True, timeout=3)
            exec_count += 1
        except Exception:
            pass
        time.sleep(random.uniform(0.5, 2.0))

def context_switch_pressure():
    """Creates thread contention to increase kernel_context_switches_delta."""
    global running
    shared = [0]
    lock = threading.Lock()
    def busy():
        while running:
            with lock:
                shared[0] = (shared[0] + 1) % 1000
    workers = [threading.Thread(target=busy, daemon=True) for _ in range(4)]
    for w in workers:
        w.start()

def reporter():
    while running:
        time.sleep(10)
        print(f"[reporter] reads: {read_count} | writes: {write_count} | execs: {exec_count}")

if __name__ == "__main__":
    print("[*] Starting safe Level 4-like syscall pressure simulator...")
    context_switch_pressure()
    threads = [
        threading.Thread(target=syscall_read_pressure, daemon=True),
        threading.Thread(target=syscall_write_pressure, daemon=True),
        threading.Thread(target=sys_stat_pressure, daemon=True),
        threading.Thread(target=subprocess_burst, daemon=True),
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
        if os.path.exists(WRITE_TMP):
            os.remove(WRITE_TMP)
        print("[*] Simulator stopped.")
