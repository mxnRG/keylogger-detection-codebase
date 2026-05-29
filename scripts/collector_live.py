#!/usr/bin/env python3
"""
Live eBPF telemetry collector for ML demo integration.

Writes append-only CSV rows compatible with L3 training schema (full kernel probes).
Default: /tmp/fyp_telemetry_live.csv every 0.5s. Requires root (BCC).
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from datetime import datetime
from pathlib import Path

import pandas as pd
import psutil
from bcc import BPF

DEFAULT_OUTPUT = "/tmp/fyp_telemetry_live.csv"

BPF_SOURCE = """
#include <uapi/linux/ptrace.h>
#include <linux/sched.h>

BPF_HASH(sys_read_counter, u32, u64);
BPF_HASH(sys_write_counter, u32, u64);
BPF_HASH(sys_openat_counter, u32, u64);
BPF_HASH(sys_execve_counter, u32, u64);
BPF_HASH(sys_connect_counter, u32, u64);

int trace_read(struct pt_regs *ctx) {
    u32 pid = bpf_get_current_pid_tgid() >> 32;
    u64 init_val = 1, *val;
    val = sys_read_counter.lookup(&pid);
    if (val) { *val += 1; } else { sys_read_counter.update(&pid, &init_val); }
    return 0;
}

int trace_write(struct pt_regs *ctx) {
    u32 pid = bpf_get_current_pid_tgid() >> 32;
    u64 init_val = 1, *val;
    val = sys_write_counter.lookup(&pid);
    if (val) { *val += 1; } else { sys_write_counter.update(&pid, &init_val); }
    return 0;
}

int trace_openat(struct pt_regs *ctx) {
    u32 pid = bpf_get_current_pid_tgid() >> 32;
    u64 init_val = 1, *val;
    val = sys_openat_counter.lookup(&pid);
    if (val) { *val += 1; } else { sys_openat_counter.update(&pid, &init_val); }
    return 0;
}

int trace_execve(struct pt_regs *ctx) {
    u32 pid = bpf_get_current_pid_tgid() >> 32;
    u64 init_val = 1, *val;
    val = sys_execve_counter.lookup(&pid);
    if (val) { *val += 1; } else { sys_execve_counter.update(&pid, &init_val); }
    return 0;
}

int trace_connect(struct pt_regs *ctx) {
    u32 pid = bpf_get_current_pid_tgid() >> 32;
    u64 init_val = 1, *val;
    val = sys_connect_counter.lookup(&pid);
    if (val) { *val += 1; } else { sys_connect_counter.update(&pid, &init_val); }
    return 0;
}
"""

SUSPICIOUS_NAMES = [
    "keylogger", "logger", "hook", "monitor", "spy", "capture", "record",
    "clipboard", "stealth", "mail", "email", "webhook",
]


def parse_args():
    parser = argparse.ArgumentParser(description="Live eBPF telemetry collector for ML demo.")
    parser.add_argument("--output", default=DEFAULT_OUTPUT, help="Output CSV path")
    parser.add_argument("--interval", type=float, default=0.5, help="Seconds between samples")
    parser.add_argument("--label", default="live", help="Label column value per row")
    parser.add_argument("--truncate", action="store_true", help="Remove existing output file on start")
    return parser.parse_args()


def require_root():
    if os.geteuid() != 0:
        print("Run with sudo: sudo python3 scripts/collector_live.py", file=sys.stderr)
        sys.exit(1)


def get_hardware_keyboard_interrupts() -> int:
    try:
        with open("/proc/interrupts", "r", encoding="utf-8") as handle:
            for line in handle:
                line_lower = line.lower()
                if any(k in line_lower for k in ("i8042", "atkbd", "keyboard", "hid", "isa0060")):
                    return sum(int(x) for x in line.split()[1:] if x.isdigit())
    except OSError:
        pass
    return 0


def collect_row(
    bpf_module,
    prev_interrupts: int,
    prev_ctx_switches: int,
    label: str,
) -> tuple[dict, int, int]:
    read_map = bpf_module.get_table("sys_read_counter")
    write_map = bpf_module.get_table("sys_write_counter")
    openat_map = bpf_module.get_table("sys_openat_counter")
    execve_map = bpf_module.get_table("sys_execve_counter")
    connect_map = bpf_module.get_table("sys_connect_counter")

    total_kernel_reads = sum(val.value for _, val in read_map.items())
    total_kernel_writes = sum(val.value for _, val in write_map.items())
    total_kernel_openat = sum(val.value for _, val in openat_map.items())
    total_kernel_execve = sum(val.value for _, val in execve_map.items())
    total_kernel_connect = sum(val.value for _, val in connect_map.items())

    for table in (read_map, write_map, openat_map, execve_map, connect_map):
        table.clear()

    actual_interrupts = get_hardware_keyboard_interrupts()
    keyboard_events_delta = max(0, actual_interrupts - prev_interrupts)
    actual_ctx_switches = psutil.cpu_stats().ctx_switches
    ctx_switches_delta = max(0, actual_ctx_switches - prev_ctx_switches)

    cpu = psutil.cpu_percent(interval=0.1)
    memory = psutil.virtual_memory().percent
    swap_memory = psutil.swap_memory().percent
    disk_usage = psutil.disk_usage("/").percent
    system_uptime = round((time.time() - psutil.boot_time()) / 60, 2)
    process_count = len(psutil.pids())
    cpu_threads = psutil.cpu_count() or 0
    keyboard_events = process_count
    total_open_files = process_count

    active_processes = 0
    background_processes = 0
    high_cpu_processes = 0
    high_memory_processes = 0
    python_processes = 0
    shell_processes = 0
    suspicious_process_names = 0
    zombie_processes = 0
    total_threads = 0

    for proc in psutil.process_iter(["name", "cpu_percent", "memory_percent", "terminal", "status"]):
        try:
            active_processes += 1
            name = proc.info.get("name") or ""
            if proc.info.get("terminal") is None:
                background_processes += 1
            if (proc.info.get("cpu_percent") or 0) > 10:
                high_cpu_processes += 1
            if (proc.info.get("memory_percent") or 0) > 5:
                high_memory_processes += 1
            if "python" in name.lower():
                python_processes += 1
            if name.lower() in ("bash", "sh", "zsh"):
                shell_processes += 1
            if any(kw in name.lower() for kw in SUSPICIOUS_NAMES):
                suspicious_process_names += 1
            if proc.info.get("status") == psutil.STATUS_ZOMBIE:
                zombie_processes += 1
            total_threads += proc.num_threads()
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass

    network_connections = len(psutil.net_connections())
    users_logged_in = len(os.popen("who").readlines())
    timestamp_now = datetime.now()

    row = {
        "timestamp": timestamp_now.isoformat(),
        "hour": timestamp_now.hour,
        "minute": timestamp_now.minute,
        "second": timestamp_now.second,
        "cpu_usage": cpu,
        "memory_usage": memory,
        "swap_memory": swap_memory,
        "disk_usage_percent": disk_usage,
        "system_uptime_minutes": system_uptime,
        "process_count": process_count,
        "active_processes": active_processes,
        "background_processes": background_processes,
        "high_cpu_processes": high_cpu_processes,
        "high_memory_processes": high_memory_processes,
        "python_processes": python_processes,
        "shell_processes": shell_processes,
        "suspicious_process_names": suspicious_process_names,
        "zombie_processes": zombie_processes,
        "cpu_threads": cpu_threads,
        "total_threads": total_threads,
        "thread_to_process_ratio": round(total_threads / max(process_count, 1), 4),
        "keyboard_events": keyboard_events,
        "keyboard_to_process_ratio": round(keyboard_events / max(process_count, 1), 4),
        "total_open_files": total_open_files,
        "network_connections": network_connections,
        "total_connections": network_connections,
        "users_logged_in": users_logged_in,
        "cpu_to_keyboard_ratio": round(cpu / max(keyboard_events, 1), 4),
        "keyboard_hardware_interrupts": keyboard_events_delta,
        "kernel_context_switches_delta": ctx_switches_delta,
        "kernel_sys_read_delta": total_kernel_reads,
        "kernel_sys_write_delta": total_kernel_writes,
        "kernel_openat_delta": total_kernel_openat,
        "kernel_execve_delta": total_kernel_execve,
        "kernel_connect_delta": total_kernel_connect,
        "scenario": "live_demo",
        "collector_type": "ebpf",
        "label": label,
    }
    return row, actual_interrupts, actual_ctx_switches


def append_row(output_path: Path, row: dict) -> None:
    df = pd.DataFrame([row])
    if output_path.exists():
        df.to_csv(output_path, mode="a", header=False, index=False)
    else:
        df.to_csv(output_path, mode="w", header=True, index=False)


def main():
    args = parse_args()
    require_root()
    output_path = Path(args.output).expanduser().resolve()
    if args.truncate and output_path.exists():
        output_path.unlink()

    print(f"Live telemetry → {output_path} (every {args.interval}s). Ctrl+C to stop.")

    bpf_module = BPF(text=BPF_SOURCE)
    for syscall in ("read", "write", "openat", "execve", "connect"):
        bpf_module.attach_kprobe(
            event=bpf_module.get_syscall_fnname(syscall),
            fn_name=f"trace_{syscall}",
        )

    prev_interrupts = get_hardware_keyboard_interrupts()
    prev_ctx_switches = psutil.cpu_stats().ctx_switches

    try:
        while True:
            row, prev_interrupts, prev_ctx_switches = collect_row(
                bpf_module, prev_interrupts, prev_ctx_switches, args.label
            )
            append_row(output_path, row)
            time.sleep(args.interval)
    except KeyboardInterrupt:
        print("\nLive telemetry collection stopped.")


if __name__ == "__main__":
    main()
