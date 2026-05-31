# unseen_level4_proc_sys_netlink_inspector.py
# Safe Level 4-like /proc + /sys + Netlink inspector
# Mimics rootkit-style kernel-space inspection using only safe userspace calls.
# No kernel module. No insmod. No privilege escalation. No process hiding.

import os
import socket
import struct
import time
import threading
import subprocess
import random

running = True
netlink_count = 0
proc_scan_count = 0

# Netlink constants
NETLINK_ROUTE = 0
RTM_GETLINK = 18
NLM_F_REQUEST = 0x01
NLM_F_DUMP = 0x300
NLMSG_HDRLEN = 16

PROC_NET_TARGETS = [
    "/proc/net/dev",
    "/proc/net/tcp",
    "/proc/net/udp",
    "/proc/net/if_inet6",
    "/proc/net/route",
    "/proc/net/arp",
    "/proc/net/unix",
]

SYS_KERNEL_TARGETS = [
    "/proc/sys/kernel/hostname",
    "/proc/sys/kernel/ostype",
    "/proc/sys/kernel/pid_max",
    "/proc/sys/kernel/threads-max",
    "/proc/sys/vm/swappiness",
    "/sys/kernel/mm",
    "/sys/kernel",
]

def netlink_route_inspect():
    """Uses NETLINK_ROUTE to enumerate kernel network interfaces — rootkit-like pattern."""
    global running, netlink_count
    while running:
        try:
            nl = socket.socket(socket.AF_NETLINK, socket.SOCK_RAW, NETLINK_ROUTE)
            nl.bind((os.getpid(), 0))
            # Build RTM_GETLINK dump request
            msg_type = RTM_GETLINK
            flags = NLM_F_REQUEST | NLM_F_DUMP
            seq = random.randint(1, 0xFFFF)
            # ifi_family=AF_UNSPEC(0), ifi_type=0, ifi_index=0, ifi_flags=0, ifi_change=0
            ifinfomsg = struct.pack("BBHiII", 0, 0, 0, 0, 0, 0)
            nlmsg_len = NLMSG_HDRLEN + len(ifinfomsg)
            header = struct.pack("IHHII", nlmsg_len, msg_type, flags, seq, os.getpid())
            nl.sendall(header + ifinfomsg)
            # Read response — discarded
            nl.recv(8192)
            nl.close()
            netlink_count += 1
        except Exception:
            pass
        time.sleep(random.uniform(3, 8))

def proc_net_scanner():
    """Reads /proc/net/ entries continuously."""
    global running, proc_scan_count
    while running:
        for path in PROC_NET_TARGETS:
            try:
                with open(path, "r") as f:
                    _ = f.read(512)  # Read partial, discard
                proc_scan_count += 1
            except Exception:
                pass
        time.sleep(random.uniform(0.5, 1.5))

def sys_kernel_poller():
    """Polls /proc/sys and /sys/kernel entries with jittered timing."""
    global running
    while running:
        for path in SYS_KERNEL_TARGETS:
            try:
                if os.path.isfile(path):
                    with open(path, "r") as f:
                        _ = f.read(64)
                elif os.path.isdir(path):
                    os.listdir(path)
            except Exception:
                pass
        time.sleep(random.uniform(1.0, 3.0))

def socketpair_ipc():
    """Uses socketpair() for local IPC — contributes to kernel_connect_delta analog."""
    global running
    while running:
        try:
            a, b = socket.socketpair(socket.AF_UNIX, socket.SOCK_STREAM)
            a.sendall(b"PROBE\n")
            b.recv(32)
            a.close()
            b.close()
        except Exception:
            pass
        time.sleep(0.3)

def subprocess_probe():
    """Runs safe inspection commands mimicking rootkit enumeration tools."""
    global running
    cmds = [
        ["ss", "-tulpn"],
        ["cat", "/proc/net/route"],
        ["ip", "link", "show"],
        ["cat", "/proc/sys/kernel/pid_max"],
    ]
    while running:
        cmd = random.choice(cmds)
        try:
            subprocess.run(cmd, capture_output=True, timeout=3)
        except Exception:
            pass
        time.sleep(random.uniform(4, 10))

def reporter():
    while running:
        time.sleep(10)
        print(f"[reporter] Netlink probes: {netlink_count} | /proc/net scans: {proc_scan_count}")

if __name__ == "__main__":
    print("[*] Starting safe Level 4-like /proc+/sys+Netlink inspector...")
    threads = [
        threading.Thread(target=netlink_route_inspect, daemon=True),
        threading.Thread(target=proc_net_scanner, daemon=True),
        threading.Thread(target=sys_kernel_poller, daemon=True),
        threading.Thread(target=socketpair_ipc, daemon=True),
        threading.Thread(target=subprocess_probe, daemon=True),
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
