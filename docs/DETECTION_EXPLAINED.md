# FYP Keylogger Detection - How It Works

## Your Question: "How does event rate detect keyloggers?"

**Excellent question!** You're absolutely right that a keylogger wouldn't TYPE - it would READ. Here's how our detection actually works:

---

## What We're Actually Detecting

### The Kernel Hook (`keyboard_notifier_list`)

Our kernel module hooks into the Linux keyboard notifier chain. This means:

```c
// When ANY keyboard event happens (press/release):
keyboard_notifier_call_chain(...) 
  → Our callback function runs
  → We capture: WHO is handling the event RIGHT NOW
```

**Key Insight:** `current->pid` and `current->comm` tell us **which process is actively processing keyboard events** at the kernel level.

---

## Normal Typing Flow

When you type normally:
```
Keyboard Hardware
    ↓
Kernel Input Subsystem  ← Our hook sees this!
    ↓
X11/Wayland Display Server
    ↓
Your Application (gnome-terminal, firefox, etc.)
```

Our hook records:
- **PID**: 12345
- **COMM**: "gnome-terminal"
- **Rate**: ~2-5 events/second (human typing speed)
- **Pattern**: Natural inter-keystroke timing (150-300ms)

---

## Keylogger Flow

When a keylogger runs:

### Type 1: Direct Input Device Reading (`/dev/input/eventX`)
```c
// Malicious code:
int fd = open("/dev/input/event3", O_RDONLY);
while (read(fd, &event, sizeof(event))) {
    log_keystroke(event);  ← This process context!
}
```

**What we see:**
- **PID**: 66666
- **COMM**: "suspicious_app" or "backdoor"
- **Rate**: SAME as user's typing (it reads every keystroke)
- **Pattern**: Processes events even when its window isn't in focus!

### Type 2: Input Subsystem Hook (like we do)
```c
// Malicious kernel module or process:
register_keyboard_notifier(&evil_notifier);
```

**What we see:**
- Events being handled by an unknown process/module
- Not in our whitelist (gnome-shell, X, terminals, etc.)
- Suspicious timing patterns if batch-processing

---

## Detection Heuristics

### 1. **Unknown Process Detection**
```python
WHITELIST = {
    'gnome-shell', 'Xorg', 'bash', 'firefox', 
    'gnome-terminal', 'vim', 'code', ...
}

if process not in WHITELIST and events > 5:
    ALERT: "Unknown process accessing keyboard events"
```

**Why this works:**
- Legitimate apps are known and whitelisted
- Any new process handling keyboard events is suspicious
- Keyloggers show up as their own PID

### 2. **Rapid Event Pattern**
```python
if inter_event_time < 50ms for >50% of events:
    ALERT: "Automated/synthetic event pattern"
```

**Why this works:**
- Humans can't type faster than ~20 keys/sec consistently
- Programmatic reading/injection often has different timing
- Batch-processing creates clustered events

### 3. **Event Rate Burst**
```python
if events_per_second > 100 for sustained period:
    ALERT: "High-rate event processing"
```

**Why this works:**
- Normal typing: 2-5 keys/sec
- Fast typing: 10-15 keys/sec
- >100 events/sec indicates programmatic access
- Keylogger reading stream gets ALL events (press + release = 2x rate)

---

## What Makes This Different from Typing Detection?

### ❌ We DON'T Track:
- Which keys were pressed
- What the user typed
- Content of keystrokes
- Keystroke sequences

### ✅ We DO Track:
- **WHO** is processing keyboard events (PID/COMM)
- **WHEN** events occur (timestamp)
- **HOW FAST** events are processed (rate)
- **PATTERN** of event timing (rapid ratio)

---

## Example Scenario

### Normal Usage:
```
Event 1: gnome-terminal (PID 1234) @ 0.000s
Event 2: gnome-terminal (PID 1234) @ 0.150s  (150ms gap - human typing)
Event 3: gnome-terminal (PID 1234) @ 0.280s  (130ms gap)
Event 4: gnome-terminal (PID 1234) @ 0.450s  (170ms gap)
```
**Detection:** ✓ Normal - whitelisted app, human timing

### Keylogger Running:
```
Event 1: gnome-terminal (PID 1234) @ 0.000s
Event 2: evil_logger   (PID 6666) @ 0.001s  (1ms gap - not human!)
Event 3: gnome-terminal (PID 1234) @ 0.150s
Event 4: evil_logger   (PID 6666) @ 0.151s  (1ms gap - suspicious!)
Event 5: gnome-terminal (PID 1234) @ 0.280s
Event 6: evil_logger   (PID 6666) @ 0.281s  (1ms gap - ALERT!)
```

**Detection:** 
- 🚨 PID 6666 "evil_logger" NOT in whitelist → MEDIUM alert
- 🚨 Rapid ratio: 100% (all events <50ms apart) → HIGH alert
- 🚨 Processes events for EVERY keystroke → Suspicious pattern

---

## The Key Principle

**We're not measuring typing speed - we're measuring WHO is accessing the keyboard event stream at the kernel level.**

A keylogger MUST:
1. Register with the input subsystem, OR
2. Read from `/dev/input/*`, OR  
3. Hook the keyboard notifier chain

All of these cause the keylogger's PID to appear in our logs when it processes events.

---

## Why Event Rate Still Matters

Even though keyloggers don't TYPE, they do:

1. **Process Events**: When they read/intercept, they're in the process context
2. **Show Different Patterns**: 
   - Batch reading → Rapid bursts
   - Real-time interception → Suspiciously fast (<1ms between process switches)
   - Always-on monitoring → Events even when window not focused

3. **Trigger Multiple Heuristics**:
   - Unknown process ✓
   - Abnormal timing ✓
   - High event rate (if batch-processing) ✓

---

## Limitations (Academic Honesty)

This is a **behavioral heuristic** system, not cryptographic security:

1. **Sophisticated Keyloggers** could:
   - Mimic legitimate process names
   - Add randomized delays to avoid rapid detection
   - Only log certain windows (targeted)

2. **False Positives** possible for:
   - Legitimate automation tools
   - Accessibility software
   - Gaming macros
   - Screen recording software

3. **This is why we:**
   - Use multiple heuristics (not just one)
   - Provide severity levels (LOW/MEDIUM/HIGH)
   - Show process names for user verification
   - Allow whitelisting (future feature)

---

## Summary

**Your Typing ≠ Events We Measure**

We measure: **Which processes are handling keyboard events in kernel space**

When a keylogger runs, it shows up as its own PID accessing the keyboard input stream, with suspicious patterns that trigger our heuristics.

---

## File References

- **Kernel Module:** [`/home/fyp/project/kernel/fyp_kbd.c`](../kernel/fyp_kbd.c)
  - Lines 1-40: Architecture explanation
  - Lines 230-350: Keyboard notifier callback (where we capture PID/COMM)

- **Daemon Detection:** [`/home/fyp/project/daemon/fyp_daemon.py`](../daemon/fyp_daemon.py)
  - Lines 120-200: DetectionEngine class with 3 heuristics
  - Lines 145-180: Rule implementations

- **GUI Visualization:** [`/home/fyp/project/gui/fyp_gui.py`](../gui/fyp_gui.py)
  - Event rate charts show WHO is generating events
  - Process stats show WHICH processes are handling keyboard events
  - Alert severity based on heuristic triggers
