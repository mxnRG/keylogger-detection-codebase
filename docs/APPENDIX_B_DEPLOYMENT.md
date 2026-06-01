# Appendix B — Deployment / Installation Guide

## B.1 Purpose

Install the FYP Keylogger Detection System on an **Ubuntu 22.04/24.04 LTS** VM. The live stack: kernel module → daemon → eBPF collector → ML API → GUI.

## B.2 Requirements

| Item | Requirement |
|------|-------------|
| OS | Ubuntu 22.04 or 24.04 (64-bit) |
| RAM | 4 GB+ (8 GB recommended) |
| Access | `sudo`, graphical desktop |

## B.3 One-time setup

**System packages:**

```bash
sudo apt-get update
sudo apt-get install -y build-essential linux-headers-$(uname -r) \
  python3 python3-pip bpfcc-tools python3-bcc \
  libxcb-cursor0 libnotify-bin curl git
```

**Python packages** (from project root, e.g. `/home/fyp/project`):

```bash
cd /home/fyp/project
pip3 install -r requirements.txt
chmod +x scripts/*.sh
```

**Build kernel module:**

```bash
cd /home/fyp/project/kernel
make
```

## B.4 Start the system

```bash
cd /home/fyp/project
sudo scripts/stop_demo_stack.sh
sudo scripts/start_demo_stack.sh
```

## B.5 Verify installation

```bash
lsmod | grep fyp_kbd
curl -s http://127.0.0.1:8765/health | python3 -m json.tool
bash scripts/demo_smoke_test.sh
```

Logs: `/tmp/fyp-demo/` · Telemetry: `/tmp/fyp_telemetry_live.csv`

## B.6 Stop the system

```bash
cd /home/fyp/project
sudo scripts/stop_demo_stack.sh
```

## B.7 Common issues

| Problem | Fix |
|---------|-----|
| Kernel build fails | Install `linux-headers-$(uname -r)` |
| Collector error | Install `python3-bcc` |
| GUI missing | Run from desktop; check `DISPLAY` |
| Old behaviour after edits | Run `stop_demo_stack.sh`, then start again |

**Note:** Use only on authorized lab VMs. The system does not capture keystroke content.
