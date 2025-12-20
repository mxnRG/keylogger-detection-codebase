# Kernel Module Technical Documentation

**FYP Keylogger Detection - Kernel Module v0.6**

## Overview

The kernel module is the core component of the detection system, operating at ring 0 (kernel space) to observe keyboard event patterns at the lowest level. It captures **behavioral metadata only** - never actual keystrokes.

### Key Capabilities

- **Keyboard Event Observation**: Hooks into `keyboard_notifier_list` to receive all keyboard events
- **Process Context Tracking**: Identifies which processes are accessing keyboard events
- **Behavioral Analysis**: Calculates inter-event timing, rapid event ratios, and burst patterns
- **Real-Time Communication**: Delivers events to userspace via Netlink sockets (<1ms latency)
- **Runtime Configuration**: Tunable detection thresholds via sysfs parameters
- **Rate Limiting**: Token bucket algorithm prevents malicious flooding (1000 events/sec per PID)

---

## Architecture

### Communication Flow

```
Keyboard Hardware
    ↓
Linux Input Subsystem
    ↓
keyboard_notifier_list (kernel notifier chain)
    ↓
[FYP Kernel Module - fyp_kbd.ko]
    ├─→ Rate Limiter (per-PID token bucket)
    ├─→ Behavioral Stats (timing, rapid events)
    ├─→ Workqueue (cmdline capture)
    └─→ Netlink Socket (PROTOCOL 31)
            ↓
[Userspace Daemon - fyp_daemon.py]
```

### Data Flow

1. **Keyboard Event** → Notifier callback (atomic context)
2. **Rate Limit Check** → Token bucket verification
3. **Metadata Collection** → PID, comm, timing
4. **Workqueue Scheduling** → Deferred cmdline extraction
5. **Netlink Transmission** → Unicast to daemon

---

## Netlink Protocol

### Protocol Number
- **Family**: `NETLINK_FYP_DETECTOR` (31)
- **Type**: Unicast (single daemon listener)
- **Direction**: Bidirectional (events to daemon, registration from daemon)

### Event Message Format (v2)

```c
struct fyp_netlink_event {
    __u64 timestamp_ns;          // nanoseconds since boot (ktime_get_ns)
    __u32 pid;                   // Process ID (may be 0 for interrupt context)
    char comm[16];               // Process name (TASK_COMM_LEN)
    char cmdline[128];           // Full command line (from /proc/[pid]/cmdline)
    __u8 event_type;             // 0=keypress, 1=keyrelease
    __u8 rapid_flag;             // 1 if inter-event time < rapid_threshold_ms
} __attribute__((packed));       // Total: 158 bytes
```

**ABI Stability**: This struct is a stable userspace ABI. Changes require version increment.

### Registration Protocol

Daemon registers for event delivery:

```python
# Python example (daemon side)
import socket
import struct

# Create netlink socket
sock = socket.socket(socket.AF_NETLINK, socket.SOCK_RAW, 31)  # Protocol 31
sock.bind((0, 0))  # Bind to kernel

# Register daemon PID
daemon_pid = os.getpid()
msg = struct.pack("I", daemon_pid)  # u32
sock.send(msg)

# Now receive events
while True:
    data, addr = sock.recvfrom(256)
    event = struct.unpack("=Q I 16s 128s B B", data)
    # Process event...
```

---

## Workqueue Architecture

### Why Workqueue?

Keyboard notifier runs in **atomic context** (interrupts disabled):
- Cannot sleep
- Cannot take mutex locks
- Cannot access process memory (`mm_struct`)

**Solution**: Schedule deferred work to extract process cmdline safely.

### Implementation

```c
struct cmdline_work {
    struct work_struct work;     // Kernel workqueue work item
    pid_t pid;                   // Target process
    char comm[16];               // Process name (already captured)
    __u64 timestamp_ns;          // Event timestamp
    __u8 event_type;             // Press/release
    __u8 rapid_flag;             // Rapid event indicator
};

static void cmdline_work_handler(struct work_struct *work) {
    struct cmdline_work *cmd_work = container_of(work, struct cmdline_work, work);
    struct fyp_netlink_event event;
    
    // Build event with cmdline (safe in process context)
    extract_cmdline(cmd_work->pid, event.cmdline);
    netlink_send_event(&event);
    kfree(cmd_work);
}
```

### Cmdline Extraction

```c
static int extract_cmdline(pid_t pid, char *cmdline) {
    struct task_struct *task;
    struct mm_struct *mm;
    
    // Find task by PID
    task = pid_task(find_vpid(pid), PIDTYPE_PID);
    if (!task) return -ESRCH;
    
    // Get mm_struct with refcount (NULL check for safety)
    mm = get_task_mm(task);
    if (!mm) {
        strcpy(cmdline, "[kernel]");
        return 0;
    }
    
    // Copy from process memory (arg_start to arg_end)
    access_process_vm(task, mm->arg_start, cmdline, len, 0);
    mmput(mm);
    return 0;
}
```

**Safety**: Always check `mm` for NULL (kernel threads have no mm_struct).

---

## Runtime Configuration

### Module Parameters (sysfs)

#### 1. Rapid Threshold (ms)

```bash
# Default: 50ms
cat /sys/module/fyp_kbd/parameters/rapid_threshold_ms
50

# Tune to 100ms (less sensitive)
echo 100 > /sys/module/fyp_kbd/parameters/rapid_threshold_ms

# Tune to 30ms (more sensitive)
echo 30 > /sys/module/fyp_kbd/parameters/rapid_threshold_ms
```

**Effect**: Events closer than this threshold are flagged as "rapid" (potential automation).

#### 2. Burst Threshold (events/sec)

```bash
# Default: 100 eps
cat /sys/module/fyp_kbd/parameters/burst_threshold_eps
100

# Tune to 200 eps (less sensitive)
echo 200 > /sys/module/fyp_kbd/parameters/burst_threshold_eps
```

**Effect**: Processes exceeding this rate trigger burst detection alerts.

### Procfs Interface

#### Statistics (`/proc/fyp_detector/stats`)

```bash
$ cat /proc/fyp_detector/stats
uptime_ms=123456
total_events=5432
press_events=2716
release_events=2716
rapid_events=54
dropped_events=0
netlink_errors=0
cmdline_work_queued=5432
rapid_ratio=1
```

#### Configuration (`/proc/fyp_detector/config`)

```bash
$ cat /proc/fyp_detector/config
rapid_threshold_ms=50
burst_threshold_eps=100

# Runtime tunable via sysfs:
# echo VALUE > /sys/module/fyp_kbd/parameters/rapid_threshold_ms
# echo VALUE > /sys/module/fyp_kbd/parameters/burst_threshold_eps
```

---

## Rate Limiting

### Token Bucket Algorithm

**Purpose**: Prevent malicious processes from flooding the system with synthetic keyboard events.

**Parameters**:
- Bucket size: 1000 tokens
- Refill rate: 100 tokens per 100ms (1000 tokens/sec)
- Per-process isolation: Each PID has own bucket

### Implementation

```c
struct rate_limiter {
    pid_t pid;                   // Hash key
    unsigned int tokens;         // Available tokens (0-1000)
    unsigned long last_refill;   // Last refill time (jiffies)
    struct hlist_node node;      // Hash table linkage
};

// Hash table (256 buckets for O(1) lookup)
DECLARE_HASHTABLE(rate_limiters, 8);

static bool rate_limit_check(pid_t pid) {
    // Find or create limiter for PID
    // Refill tokens based on elapsed time
    // Consume 1 token if available
    // Return false if exhausted (drop event)
}
```

### Rate Limit Behavior

- **Normal typing**: 2-15 events/sec → No limiting
- **Fast automation**: 100-500 events/sec → Token bucket smooths bursts
- **Malicious flood**: >1000 events/sec → Excess events dropped
- **Statistics**: `dropped_events` counter tracks rate-limited events

---

## Compilation and Loading

### Build Requirements

```bash
# Ubuntu/Debian
sudo apt-get install build-essential linux-headers-$(uname -r)

# Verify kernel headers
ls /lib/modules/$(uname -r)/build
```

### Makefile

```makefile
obj-m += fyp_kbd.o

all:
	make -C /lib/modules/$(shell uname -r)/build M=$(PWD) modules

clean:
	make -C /lib/modules/$(shell uname -r)/build M=$(PWD) clean
```

### Build and Load

```bash
cd /home/fyp/project/kernel

# Compile
make

# Load module
sudo insmod fyp_kbd.ko

# Verify loaded
lsmod | grep fyp_kbd
dmesg | tail -10

# Check sysfs parameters
ls -l /sys/module/fyp_kbd/parameters/
```

### Unload

```bash
# Unload module
sudo rmmod fyp_kbd

# Verify workqueue flushed
dmesg | grep "Workqueue flushed"
```

---

## Debugging

### Kernel Logs

```bash
# Real-time kernel messages
sudo dmesg -w | grep fyp_detector

# Recent messages
sudo dmesg | grep fyp_detector | tail -20
```

### Common Issues

#### 1. Module won't load

**Error**: `insmod: ERROR: could not insert module: Invalid module format`

**Solution**: Kernel version mismatch
```bash
# Check kernel version
uname -r
ls /lib/modules/$(uname -r)/build

# Rebuild module
make clean && make
```

#### 2. No events received

**Check**:
```bash
# Is module loaded?
lsmod | grep fyp_kbd

# Is daemon registered?
sudo dmesg | grep "Daemon registered"

# Are events being captured?
cat /proc/fyp_detector/stats
# (type some keys and check if total_events increases)
```

#### 3. High dropped_events count

**Cause**: Rate limiting triggered

**Solutions**:
- Check for malicious process generating events
- Increase rate limit (for testing only): edit `RATE_LIMIT_EVENTS_PER_SEC` in source

---

## Security Considerations

### What We Capture

✅ **Safe (behavioral metadata)**:
- Event timestamps
- Process ID and name
- Process command line
- Inter-event timing
- Event frequency

### What We DON'T Capture

❌ **Unsafe (keystroke content)**:
- Keycodes (`param->value` is never logged)
- Key sequences or patterns
- Modifier states (Shift, Ctrl, Alt)
- Which key was pressed
- User identity
- Terminal session info

### Kernel Safety

- **Non-blocking**: All operations safe for atomic context
- **GFP_ATOMIC**: Memory allocations safe for interrupt context
- **NOTIFY_OK**: Events propagate normally (we observe, not intercept)
- **Workqueue**: Deferred work prevents atomic context violations
- **NULL checks**: Safe handling of kernel threads (no mm_struct)

---

## Performance Characteristics

### CPU Overhead

- **Normal operation**: <0.5% CPU (minimal)
- **Keyboard event processing**: ~1-5 µs per event
- **Netlink send**: ~10-50 µs (atomic, non-blocking)
- **Workqueue cmdline**: ~100-500 µs (deferred, process context)

### Memory Usage

- **Module code**: ~25 KB
- **Rate limiter hash table**: ~16 KB (256 buckets)
- **Workqueue items**: ~64 bytes per event (temporary)
- **Total static**: ~50 KB

### Scalability

- **Max event rate**: 1000 events/sec per process (rate limited)
- **Hash table**: O(1) lookups (256 buckets)
- **Workqueue**: System workqueue handles bursts efficiently

---

## API Reference

### Module Parameters

| Parameter | Type | Default | Range | Description |
|-----------|------|---------|-------|-------------|
| `rapid_threshold_ms` | int | 50 | 10-1000 | Inter-event threshold for rapid detection |
| `burst_threshold_eps` | int | 100 | 10-1000 | Events per second for burst detection |

### Procfs Files

| Path | Permission | Format | Description |
|------|------------|--------|-------------|
| `/proc/fyp_detector/stats` | 0444 (r--r--r--) | key=value | Real-time statistics |
| `/proc/fyp_detector/config` | 0444 (r--r--r--) | key=value | Current configuration |

### Netlink Protocol

| Direction | Type | Format | Description |
|-----------|------|--------|-------------|
| Kernel→Daemon | Event | `struct fyp_netlink_event` (158 bytes) | Keyboard event metadata |
| Daemon→Kernel | Register | `__u32` (4 bytes) | Daemon PID registration |

---

## Future Enhancements

### Planned Features

1. **Kernel-Side Whitelisting**
   - Array of trusted process names
   - Skip sending events for whitelisted processes
   - Reduces userspace processing overhead

2. **Event Batching**
   - Group multiple events into single netlink message
   - Reduces syscall overhead
   - Configurable batch size

3. **Per-Process Statistics**
   - Kernel-side hash table tracking per-PID stats
   - Expose via separate procfs file
   - Enables kernel-level filtering

4. **NETLINK_GENERIC Migration**
   - Use generic netlink family instead of custom protocol
   - Production-ready netlink implementation
   - Better namespace support

---

## References

- **Kernel Notifier Chains**: `Documentation/driver-api/notifier-chains.rst`
- **Netlink Sockets**: `Documentation/userspace-api/netlink/intro.rst`
- **Workqueues**: `Documentation/core-api/workqueue.rst`
- **Module Parameters**: `Documentation/admin-guide/kernel-parameters.txt`

---

**Version**: 0.6  
**Last Updated**: December 20, 2025  
**Authors**: FYP Team  
**License**: GPL v2
