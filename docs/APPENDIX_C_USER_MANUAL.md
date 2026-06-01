# Appendix C — User Manual

## C.1 Audience

For the **operator / examiner** running the dashboard on the Ubuntu VM. No login; all features are local.

## C.2 What runs in the background

| Component | Role |
|-----------|------|
| Kernel module | Keyboard behavioural metadata & syscall telemetry (no key content) |
| Daemon | Keyboard heuristics (rapid access, bursts) |
| eBPF collector | Syscall telemetry every 0.5 s |
| ML API | Live scoring + calibration |
| GUI | Dashboard and alerts |

**Alerts:** **ML** (eBPF/models) and **daemon** (keyboard) are separate. Simulator scripts may trigger ML only.

## C.3 Start and warm-up

```bash
cd /home/fyp/project
sudo scripts/stop_demo_stack.sh
sudo scripts/run_demo_verbose.sh
```

1. Wait for smoke test **passed**.
2. GUI opens; leave system **idle ~30 s** until **System Clean** (green).

## C.4 Main screens

| Page | Use |
|------|-----|
| **Dashboard** | ML status, charts, LKM status |
| **Alerts** | All ML and daemon alerts |
| **Processes** | Tracked processes |
| **Event Stream** | Live keyboard events |

## C.5 ML status panel (Dashboard)

| Display | Meaning |
|---------|---------|
| **Calibrating… (N/20)** | Wait; no alerts yet |
| **System Clean** | Normal |
| **Keylogger Detected — Level N** | Threat; read **Detection:** line |
| **ML Offline** | Restart stack (Appendix B) |

**Detection:** e.g. `ml-L2`, `spike-L3` — shows how detection was decided.

## C.6 Stop

```bash
sudo /home/fyp/project/scripts/stop_demo_stack.sh
```

## C.7 Quick reference

| Task | Action |
|------|--------|
| Start | `sudo scripts/run_demo_verbose.sh` |
| Stop | `sudo scripts/stop_demo_stack.sh` |

