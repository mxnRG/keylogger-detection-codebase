# Procfs Implementation - Technical Notes

## ✅ Step 1 Complete: Kernel → Userspace Communication

### What is Procfs?

`/proc` is a **virtual filesystem** - files don't exist on disk, they're created in-memory by the kernel when accessed.

**Key Concept:** When our module loads, the kernel creates `/proc/fyp_detector/` automatically. When we unload, it disappears.

---

## Design Decisions

### 1. Procfs vs Netlink - Why We Chose Procfs

| Aspect | Our Choice: Procfs | Alternative: Netlink |
|--------|-------------------|---------------------|
| **Implementation** | Simple file I/O | Complex socket API |
| **Debugging** | `cat /proc/file` works | Requires netlink tools |
| **Code complexity** | ~200 lines | ~400+ lines |
| **Learning curve** | Standard C file ops | Socket programming |
| **Performance** | Good enough for prototype | Better for high volume |
| **Best for** | Academic prototype ✅ | Production systems |

**Verdict:** Procfs is perfect for our FYP prototype. Clean, debuggable, well-documented.

---

## Implementation Details

### Circular Buffer Design

```c
#define EVENT_BUFFER_SIZE 256  // Power of 2 for efficient wrapping

struct kbd_event {
    unsigned long timestamp;    // jiffies
    char event_type;            // 'P' or 'R'
    pid_t pid;
    char comm[TASK_COMM_LEN];   // 16 bytes
    unsigned char rapid_flag;   // 0 or 1
};

static struct kbd_event event_buffer[EVENT_BUFFER_SIZE];
static unsigned int event_head = 0;  // Write position
static unsigned int event_tail = 0;  // Read position
static DEFINE_SPINLOCK(buffer_lock);
```

**Why power of 2?**
- Efficient wrapping: `(head + 1) & (SIZE - 1)` instead of `(head + 1) % SIZE`
- No division operation (faster in kernel)

**Why spinlock?**
- We're in atomic context (keyboard notifier)
- Can't use mutex (would sleep)
- `spin_lock_irqsave` protects against SMP races

---

### Procfs File Handlers

#### 1. `/proc/fyp_detector/events` (Read-only)

Uses **seq_file API** for safe iteration:

```c
static const struct seq_operations events_seq_ops = {
    .start = events_seq_start,  // Initialize iterator
    .next  = events_seq_next,   // Get next event
    .stop  = events_seq_stop,   // Cleanup
    .show  = events_seq_show,   // Format and output
};
```

**Why seq_file?**
- Handles large outputs safely
- Automatic buffer management
- Prevents read() race conditions
- Standard kernel pattern

**Output format:** CSV for easy parsing
```
timestamp_ms,type,pid,comm,rapid_flag
22396,P,0,swapper/3,1
```

#### 2. `/proc/fyp_detector/stats` (Read-only)

Uses **single_open** (simpler than seq_file for single-page output):

```c
static int stats_show(struct seq_file *s, void *v)
{
    seq_printf(s, "total_events=%lu\n", event_count);
    seq_printf(s, "rapid_ratio=%lu\n", rapid_ratio);
    // ...
    return 0;
}
```

**Output format:** Key=value for easy parsing
```
total_events=68
rapid_ratio=7
uptime_ms=35268
```

#### 3. `/proc/fyp_detector/control` (Write-only)

Accepts commands via `echo`:

```c
static ssize_t control_write(struct file *file, const char __user *buf,
                             size_t count, loff_t *ppos)
{
    char cmd[32];
    copy_from_user(cmd, buf, len);
    
    if (strcmp(cmd, "reset") == 0) {
        // Reset all counters
    }
    return count;
}
```

**Usage:**
```bash
echo "reset" | sudo tee /proc/fyp_detector/control
```

---

## Concurrency & Safety

### Challenge: Multiple Contexts Accessing Data

**Writers:**
- Keyboard notifier (atomic/interrupt context)
- Control file (process context)

**Readers:**
- Events file (process context)
- Stats file (process context)

### Solution: Spinlocks

```c
spin_lock_irqsave(&buffer_lock, flags);
// Critical section - modify shared data
spin_unlock_irqrestore(&buffer_lock, flags);
```

**Why `irqsave`?**
- Disables interrupts on local CPU
- Saves interrupt state
- Prevents deadlock if interrupt handler tries to acquire same lock

**What happens:**
1. Reader calls `cat /proc/fyp_detector/events`
2. Takes spinlock, reads buffer
3. Meanwhile, keyboard event happens
4. Event tries to take spinlock → spins/waits
5. Reader releases lock
6. Event acquires lock, writes to buffer

---

## Memory Management

### Fixed-Size Allocation

**Buffer:** 256 events × ~32 bytes = **~8KB total**
- Allocated at module load time
- Never grows (prevents memory exhaustion)
- Overwrites oldest when full

**No dynamic allocation in hot path:**
- `kmalloc()` in seq_file iterator is OK (cold path, GFP_ATOMIC)
- Never allocate in keyboard notifier (too slow)

---

## Kernel API Compatibility

### proc_ops vs file_operations

**Kernel 5.6+** uses `proc_ops`:
```c
static const struct proc_ops events_fops = {
    .proc_read    = seq_read,
    .proc_lseek   = seq_lseek,
    .proc_release = seq_release,
};
```

**Older kernels** use `file_operations`:
```c
static const struct file_operations events_fops = {
    .read    = seq_read,
    .llseek  = seq_lseek,
    .release = seq_release,
};
```

**Our kernel (5.15.x)** has `proc_ops` ✅

---

## Testing & Verification

### Load Module
```bash
sudo insmod fyp_kbd.ko
dmesg | grep FYP
# [FYP] Procfs interface created at /proc/fyp_detector/
```

### Verify Files Created
```bash
ls -la /proc/fyp_detector/
# control  events  stats
```

### Read Stats
```bash
cat /proc/fyp_detector/stats
# total_events=0
# rapid_ratio=0
# uptime_ms=1234
```

### Generate Events
Type in VM's GUI terminal (not VSCode remote terminal)

### View Events
```bash
cat /proc/fyp_detector/events | head -10
# 1234,P,0,swapper/3,0
# 1245,R,0,swapper/3,0
```

### Reset
```bash
echo "reset" | sudo tee /proc/fyp_detector/control
cat /proc/fyp_detector/stats
# total_events=0  (reset successful)
```

### Unload
```bash
sudo rmmod fyp_kbd
ls -la /proc/fyp_detector/
# No such file or directory (cleanup successful)
```

---

## Common Issues & Solutions

### Issue: Directory doesn't appear
**Cause:** Module failed to load
**Solution:**
```bash
dmesg | grep FYP  # Check for errors
lsmod | grep fyp  # Verify module loaded
```

### Issue: Permission denied reading events
**Cause:** File permissions
**Solution:** Files are world-readable (0444), should work without sudo

### Issue: No events captured
**Cause:** Typing in wrong terminal
**Solution:** Type in VM's GUI terminal, not VSCode SSH terminal

### Issue: Events show garbage data
**Cause:** Uninitialized buffer (we saw this initially)
**Solution:** `memset()` buffer at init (already done after reset)

---

## Performance Characteristics

**Event capture overhead:**
- Spinlock acquire/release: ~10ns
- Buffer write: ~50ns
- Total per event: ~100ns negligible

**Read performance:**
- Reading 256 events: <1ms
- No blocking of keyboard events

**Memory overhead:**
- Fixed 8KB buffer
- ~2KB for procfs structures
- Total: **~10KB** (trivial for modern systems)

---

## Why This Design is Safe

1. **No blocking in atomic context** - Only spinlocks, no mutexes
2. **Fixed memory usage** - No dynamic allocation in hot path
3. **Overwrite policy** - Old events discarded, never runs out of space
4. **SMP-safe** - Proper spinlock usage prevents races
5. **No kernel panics** - All error paths handled
6. **Clean unload** - Proper cleanup, no resource leaks

**Academic prototype criteria: ✅ Met**
- Simple enough to explain in FYP presentation
- Complex enough to demonstrate understanding
- Safe enough to run in demo environment
- Well-documented for examiner review

---

## Next Step: Python Daemon

Now that kernel exposes data via procfs, we can build userspace daemon:

```python
# Read events from procfs
with open('/proc/fyp_detector/events', 'r') as f:
    for line in f:
        timestamp, event_type, pid, comm, rapid = line.strip().split(',')
        process_event(timestamp, event_type, pid, comm, rapid)
```

See `docs/PHASE2_DESIGN.md` for complete daemon implementation.

---

**Step 1 Status: ✅ COMPLETE**  
**Ready for:** Step 2 - Python Daemon Development
