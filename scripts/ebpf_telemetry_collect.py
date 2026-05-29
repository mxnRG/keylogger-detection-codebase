#!/usr/bin/env python3
"""
Ubuntu eBPF benign telemetry collector.

Collects system and kernel telemetry using BCC and writes to CSV.
"""

import argparse
import os
import sys
import time
from datetime import datetime
from pathlib import Path

import pandas as pd
import psutil
from bcc import BPF


def parse_args():
    default_output = Path(__file__).resolve().parent / ".." / "dataset" / "level2.csv"
    parser = argparse.ArgumentParser(description="Collect Ubuntu eBPF telemetry.")
    parser.add_argument(
        "--output",
        default=str(default_output),
        help="Output CSV path (default: ../dataset/level2.csv relative to this script)",
    )
    parser.add_argument(
        "--label",
        default="benign",
        help="Label to write for each row (default: benign)",
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=0.5,
        help="Seconds between samples (default: 0.5)",
    )
    return parser.parse_args()


def require_root():
    if os.geteuid() != 0:
        print("Run with sudo: sudo python3 scripts/ebpf_telemetry_collect.py")
        sys.exit(1)


def get_hardware_keyboard_interrupts():
    try:
        with open("/proc/interrupts", "r", encoding="utf-8") as handle:
            for line in handle:
                line_lower = line.lower()
                if any(key in line_lower for key in ["i8042", "atkbd", "keyboard", "hid", "isa0060"]):
                    return sum(int(x) for x in line.split()[1:] if x.isdigit())
    except Exception:
        pass
    return 0


def main():
    args = parse_args()
    require_root()

    print("Collecting Ubuntu BENIGN eBPF telemetry... Press CTRL+C to stop.")

    output_path = Path(args.output).expanduser().resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    bpf_source = r"""
#include <uapi/linux/ptrace.h>
#include <linux/sched.h>
BPF_HASH(sys_read_counter, u32, u64);
BPF_HASH(sys_write_counter, u32, u64);
int kprobe__sys_read(struct pt_regs *ctx) {
    u32 pid = bpf_get_current_pid_tgid() >> 32;
    u64 init_val = 1, *val;
    val = sys_read_counter.lookup(&pid);
    if (val) {
        *val += 1;
    } else {
        sys_read_counter.update(&pid, &init_val);
    }
    return 0;
}
int kprobe__sys_write(struct pt_regs *ctx) {
    u32 pid = bpf_get_current_pid_tgid() >> 32;
    u64 init_val = 1, *val;
    val = sys_write_counter.lookup(&pid);
    if (val) {
        *val += 1;
    } else {
        sys_write_counter.update(&pid, &init_val);
    }
    return 0;
}
"""

    bpf_module = BPF(text=bpf_source)

    prev_interrupts = get_hardware_keyboard_interrupts()
    prev_ctx_switches = psutil.cpu_stats().ctx_switches

    try:
        while True:
            read_map = bpf_module.get_table("sys_read_counter")
            write_map = bpf_module.get_table("sys_write_counter")

            total_kernel_reads = sum(val.value for _, val in read_map.items())
            total_kernel_writes = sum(val.value for _, val in write_map.items())

            read_map.clear()
            write_map.clear()

            actual_interrupts = get_hardware_keyboard_interrupts()
            keyboard_events_delta = max(0, actual_interrupts - prev_interrupts)

            actual_ctx_switches = psutil.cpu_stats().ctx_switches
            ctx_switches_delta = max(0, actual_ctx_switches - prev_ctx_switches)

            prev_interrupts = actual_interrupts
            prev_ctx_switches = actual_ctx_switches

            cpu = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory().percent
            swap_memory = psutil.swap_memory().percent
            disk_usage = psutil.disk_usage("/").percent
            system_uptime = round((time.time() - psutil.boot_time()) / 60, 2)
            process_count = len(psutil.pids())
            cpu_threads = psutil.cpu_count()

            keyboard_events = process_count
            total_open_files = process_count

            all_processes = list(
                psutil.process_iter([
                    "pid",
                    "name",
                    "cpu_percent",
                    "memory_percent",
                    "terminal",
                    "status",
                ])
            )

            active_processes = 0
            background_processes = 0
            high_cpu_processes = 0
            high_memory_processes = 0
            python_processes = 0
            shell_processes = 0
            suspicious_process_names = 0
            zombie_processes = 0
            total_threads = 0

            suspicious_names = ["keylogger", "logger", "hook", "monitor", "spy", "capture", "record"]

            for proc in all_processes:
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

                    if name.lower() in ["bash", "sh", "zsh"]:
                        shell_processes += 1

                    if any(keyword in name.lower() for keyword in suspicious_names):
                        suspicious_process_names += 1

                    if proc.info.get("status") == psutil.STATUS_ZOMBIE:
                        zombie_processes += 1

                    total_threads += proc.num_threads()
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    pass

            network_connections = len(psutil.net_connections())
            total_connections = network_connections
            users_logged_in = len(os.popen("who").readlines())

            timestamp_now = datetime.now()

            keyboard_to_process_ratio = round(keyboard_events / max(process_count, 1), 4)
            cpu_to_keyboard_ratio = round(cpu / max(keyboard_events, 1), 4)
            thread_to_process_ratio = round(total_threads / max(process_count, 1), 4)

            row = {
                "timestamp": timestamp_now,
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
                "thread_to_process_ratio": thread_to_process_ratio,
                "keyboard_events": keyboard_events,
                "keyboard_to_process_ratio": keyboard_to_process_ratio,
                "total_open_files": total_open_files,
                "network_connections": network_connections,
                "total_connections": total_connections,
                "users_logged_in": users_logged_in,
                "cpu_to_keyboard_ratio": cpu_to_keyboard_ratio,
                "keyboard_hardware_interrupts": keyboard_events_delta,
                "kernel_context_switches_delta": ctx_switches_delta,
                "kernel_sys_read_delta": total_kernel_reads,
                "kernel_sys_write_delta": total_kernel_writes,
                "label": args.label,
            }

            df = pd.DataFrame([row])
            if output_path.exists():
                df.to_csv(output_path, mode="a", header=False, index=False)
            else:
                df.to_csv(output_path, mode="w", header=True, index=False)

            print(
                f"[BENIGN UBUNTU] Read: {total_kernel_reads} | Write: {total_kernel_writes} | Label: {args.label}"
            )

            time.sleep(args.interval)

    except KeyboardInterrupt:
        print("\nUbuntu benign telemetry collection stopped.")


if __name__ == "__main__":
    main()
