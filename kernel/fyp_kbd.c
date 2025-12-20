/*
 * FYP Keylogger Detection - Kernel Module v0.5 (Netlink Edition)
 * 
 * ETHICAL NOTICE: This is a keylogger DETECTOR, not a keylogger.
 * We collect BEHAVIORAL PATTERNS only - NO individual keystroke data.
 * 
 * Uses keyboard_notifier_list (kernel 5.15.x) to observe keyboard activity
 * Delivers events via Netlink socket for real-time userspace processing
 * 
 * WHAT WE COLLECT (Safe for detection):
 *   - Event frequency and rate
 *   - Timing patterns (inter-keystroke intervals)
 *   - Process context (PID, comm)
 *   - Statistical anomalies
 * 
 * WHAT WE DO NOT COLLECT (Avoids keylogging):
 *   - Keycodes (which key was pressed)
 *   - Shift/modifier states
 *   - Key sequences or patterns
 *   - Anything that reveals actual keystrokes
 * 
 * COMMUNICATION:
 *   PRIMARY: Netlink socket (NETLINK_FYP_DETECTOR = 31)
 *     - Real-time event-driven delivery (<1ms latency)
 *     - No polling overhead, no circular buffer
 *     - Unicast messages to userspace daemon
 * 
 *   FALLBACK: Procfs stats (debugging only)
 *     /proc/fyp_detector/stats - Current statistics (read-only)
 * 
 * RATE LIMITING:
 * - Token bucket per-PID (1000 events/sec max per process)
 * - Anti-flood protection against malicious synthetic events
 * - Dropped events counted in statistics
 * 
 * SAFETY NOTES:
 * - Keyboard notifier runs in atomic context (cannot sleep)
 * - All allocations use GFP_ATOMIC (safe for interrupt context)
 * - Netlink send is non-blocking
 * - Process context (current) may be interrupt context (PID 0/swapper)
 */

#include <linux/module.h>
#include <linux/kernel.h>
#include <linux/init.h>
#include <linux/keyboard.h>
#include <linux/notifier.h>
#include <linux/sched.h>          /* for task_struct, current */
#include <linux/sched/signal.h>   /* for task_lock */
#include <linux/jiffies.h>        /* for timing analysis */
#include <linux/proc_fs.h>        /* for procfs fallback */
#include <linux/seq_file.h>       /* for seq_file API */
#include <linux/spinlock.h>       /* for rate limiter locks */
#include <linux/slab.h>           /* for kmalloc/kfree */
#include <linux/hashtable.h>      /* for per-PID rate limiter */
#include <net/sock.h>             /* for netlink */
#include <net/netlink.h>          /* for netlink APIs */

MODULE_LICENSE("GPL");
MODULE_AUTHOR("FYP Team");
MODULE_DESCRIPTION("FYP Keylogger Detection - Behavioral Observer with Netlink");
MODULE_VERSION("0.5");

/* ========================================================================
 * NETLINK CONFIGURATION
 * ======================================================================== */

/*
 * Custom Netlink Protocol Family
 * Using protocol 31 (unused in standard kernel)
 * 
 * WARNING: In production, register via NETLINK_GENERIC subsystem
 * For academic prototype, direct protocol assignment is acceptable
 */
#define NETLINK_FYP_DETECTOR 31

/*
 * Netlink Event Message Format (STABLE ABI)
 * Total size: 30 bytes (fixed, no dynamic allocation needed)
 * 
 * Userspace must use matching struct for parsing
 */
struct fyp_netlink_event {
	__u64 timestamp_ns;          /* Event time (nanoseconds since boot) */
	__u32 pid;                   /* Process ID (may be 0 for interrupt context) */
	char comm[TASK_COMM_LEN];    /* Process name (16 bytes, null-terminated) */
	__u8 event_type;             /* 0=press, 1=release */
	__u8 rapid_flag;             /* 1 if inter-event time <50ms, 0 otherwise */
} __attribute__((packed));

/* Netlink socket */
static struct sock *nl_sock = NULL;

/* Userspace daemon PID (for unicast delivery) */
static __u32 daemon_pid = 0;
static DEFINE_SPINLOCK(daemon_pid_lock);

/* ========================================================================
 * RATE LIMITING (TOKEN BUCKET PER PID)
 * ======================================================================== */

/*
 * Rate Limiter Configuration
 * 
 * Strategy: Token bucket algorithm per PID
 * - Each process gets 1000 tokens (events) per second
 * - Tokens refill at steady rate
 * - Excess events are dropped silently
 * 
 * Purpose: Prevent malicious processes from flooding with synthetic events
 */
#define RATE_LIMIT_EVENTS_PER_SEC 1000
#define RATE_LIMIT_BUCKET_SIZE RATE_LIMIT_EVENTS_PER_SEC
#define RATE_LIMIT_REFILL_INTERVAL_MS 100  /* Refill every 100ms */
#define RATE_LIMIT_TOKENS_PER_REFILL (RATE_LIMIT_EVENTS_PER_SEC / 10)  /* 100 tokens */

/*
 * Per-PID rate limiter entry
 * Stored in hash table for O(1) lookup
 */
struct rate_limiter {
	pid_t pid;                   /* Process ID (hash key) */
	unsigned int tokens;         /* Available tokens (0-1000) */
	unsigned long last_refill;   /* Last refill time (jiffies) */
	struct hlist_node node;      /* Hash table linkage */
};

/* Hash table for rate limiters (256 buckets) */
#define RATE_LIMITER_HASH_BITS 8
static DECLARE_HASHTABLE(rate_limiters, RATE_LIMITER_HASH_BITS);
static DEFINE_SPINLOCK(rate_limiter_lock);

/*
 * Token bucket refill logic
 * Called before consuming tokens
 * 
 * @limiter: Rate limiter entry to refill
 * 
 * Context: Atomic (holds spinlock)
 */
static void rate_limiter_refill(struct rate_limiter *limiter)
{
	unsigned long now = jiffies;
	unsigned long elapsed_ms;
	unsigned int tokens_to_add;

	/* Calculate elapsed time since last refill */
	elapsed_ms = jiffies_to_msecs(now - limiter->last_refill);

	/* Refill tokens based on elapsed time */
	if (elapsed_ms >= RATE_LIMIT_REFILL_INTERVAL_MS) {
		tokens_to_add = (elapsed_ms / RATE_LIMIT_REFILL_INTERVAL_MS) * RATE_LIMIT_TOKENS_PER_REFILL;

		limiter->tokens += tokens_to_add;
		if (limiter->tokens > RATE_LIMIT_BUCKET_SIZE)
			limiter->tokens = RATE_LIMIT_BUCKET_SIZE;

		limiter->last_refill = now;
	}
}

/*
 * Check if event is allowed under rate limit
 * 
 * @pid: Process ID to check
 * 
 * Return: true if event allowed, false if rate-limited (drop event)
 * 
 * Context: Atomic (called from keyboard notifier)
 */
static bool rate_limit_check(pid_t pid)
{
	struct rate_limiter *limiter = NULL;
	unsigned long flags;
	bool allowed = true;

	spin_lock_irqsave(&rate_limiter_lock, flags);

	/* Find existing limiter for this PID */
	hash_for_each_possible(rate_limiters, limiter, node, pid) {
		if (limiter->pid == pid) {
			/* Found existing limiter */
			rate_limiter_refill(limiter);

			if (limiter->tokens > 0) {
				limiter->tokens--;
				allowed = true;
			} else {
				/* Rate limit exceeded */
				allowed = false;
			}

			goto out_unlock;
		}
	}

	/* No existing limiter - create new one */
	limiter = kmalloc(sizeof(*limiter), GFP_ATOMIC);
	if (!limiter) {
		/* Allocation failed - allow event (fail open) */
		allowed = true;
		goto out_unlock;
	}

	limiter->pid = pid;
	limiter->tokens = RATE_LIMIT_BUCKET_SIZE - 1;  /* Consume 1 token */
	limiter->last_refill = jiffies;
	hash_add(rate_limiters, &limiter->node, pid);

out_unlock:
	spin_unlock_irqrestore(&rate_limiter_lock, flags);
	return allowed;
}

/*
 * Cleanup all rate limiters
 * Called during module unload
 */
static void rate_limiter_cleanup(void)
{
	struct rate_limiter *limiter;
	struct hlist_node *tmp;
	unsigned long flags;
	int bkt;

	spin_lock_irqsave(&rate_limiter_lock, flags);
	hash_for_each_safe(rate_limiters, bkt, tmp, limiter, node) {
		hash_del(&limiter->node);
		kfree(limiter);
	}
	spin_unlock_irqrestore(&rate_limiter_lock, flags);
}

/* ========================================================================
 * STATISTICS (GLOBAL COUNTERS)
 * ======================================================================== */

/* Behavioral statistics (detection metadata only) */
static unsigned long event_count = 0;
static unsigned long press_count = 0;
static unsigned long release_count = 0;
static unsigned long rapid_events = 0;      /* Events within 50ms */
static unsigned long dropped_events = 0;    /* Rate-limited events */
static unsigned long netlink_send_errors = 0;  /* Failed sends */
static unsigned long last_event_jiffies = 0;
static unsigned long module_start_jiffies = 0;

#define RAPID_THRESHOLD_MS 50  /* Threshold for detecting rapid/automated typing */

/* ========================================================================
 * NETLINK MESSAGE DELIVERY
 * ======================================================================== */

/*
 * Send event to userspace daemon via Netlink
 * 
 * @event: Event data to send (30 bytes)
 * 
 * Context: Atomic (called from keyboard notifier)
 * 
 * Return: 0 on success, negative error code on failure
 * 
 * DESIGN NOTES:
 * - Uses unicast delivery (single daemon listener)
 * - Non-blocking send (safe for atomic context)
 * - Allocates skb with GFP_ATOMIC (safe for interrupt context)
 * - If daemon not registered (daemon_pid == 0), events are dropped silently
 */
static int netlink_send_event(const struct fyp_netlink_event *event)
{
	struct sk_buff *skb;
	struct nlmsghdr *nlh;
	__u32 pid;
	unsigned long flags;
	int ret;

	/* Check if daemon is registered */
	spin_lock_irqsave(&daemon_pid_lock, flags);
	pid = daemon_pid;
	spin_unlock_irqrestore(&daemon_pid_lock, flags);

	if (pid == 0) {
		/* No daemon listening - drop event silently */
		return -ENOENT;
	}

	/* Allocate netlink message buffer (atomic-safe) */
	skb = nlmsg_new(sizeof(*event), GFP_ATOMIC);
	if (!skb) {
		netlink_send_errors++;
		return -ENOMEM;
	}

	/* Build netlink message header */
	nlh = nlmsg_put(skb, 0, 0, 0, sizeof(*event), 0);
	if (!nlh) {
		kfree_skb(skb);
		netlink_send_errors++;
		return -EMSGSIZE;
	}

	/* Copy event data into message payload */
	memcpy(nlmsg_data(nlh), event, sizeof(*event));

	/* Send to daemon (unicast, non-blocking) */
	ret = nlmsg_unicast(nl_sock, skb, pid);
	if (ret < 0) {
		netlink_send_errors++;
		return ret;
	}

	return 0;
}

/*
 * Handle incoming Netlink messages from userspace
 * 
 * Currently supports one command:
 *   - REGISTER: Daemon registers its PID for event delivery
 * 
 * Message format: Single u32 containing daemon PID
 * 
 * Context: Process context (netlink receive handler)
 */
static void netlink_recv_handler(struct sk_buff *skb)
{
	struct nlmsghdr *nlh;
	__u32 pid;
	unsigned long flags;

	nlh = nlmsg_hdr(skb);

	/* Parse message payload (expect single u32: daemon PID) */
	if (nlmsg_len(nlh) < sizeof(__u32)) {
		pr_warn("fyp_detector: Invalid netlink message (too short)\n");
		return;
	}

	pid = *(__u32 *)nlmsg_data(nlh);

	/* Register daemon PID */
	spin_lock_irqsave(&daemon_pid_lock, flags);
	daemon_pid = pid;
	spin_unlock_irqrestore(&daemon_pid_lock, flags);

	pr_info("fyp_detector: Daemon registered (PID %u)\n", pid);
}

/* ========================================================================
 * KEYBOARD NOTIFIER (EVENT CAPTURE)
 * ======================================================================== */

/*
 * Keyboard notifier callback
 * 
 * Context: Atomic (interrupt context or process context with interrupts disabled)
 * Can: Log, increment counters, collect metadata, send netlink
 * Cannot: Sleep, allocate memory (GFP_KERNEL), take mutexes, block
 * 
 * @nblock: Notifier block (our registration structure)
 * @code: Event code (KBD_KEYCODE, KBD_UNBOUND_KEYCODE, etc.)
 * @_param: Pointer to keyboard_notifier_param structure
 * 
 * Return: NOTIFY_OK to allow event propagation
 * 
 * IMPORTANT NOTES:
 * - We observe events but do NOT intercept them (return NOTIFY_OK)
 * - Process context (current) is often interrupt-time context (PID 0/swapper)
 * - This is acceptable limitation - document in FYP report
 * - Detection logic runs in userspace daemon, not here
 */
static int fyp_keyboard_notifier(struct notifier_block *nblock,
				 unsigned long code, void *_param)
{
	struct keyboard_notifier_param *param = _param;
	struct task_struct *task;
	struct fyp_netlink_event event;
	unsigned long current_jiffies, time_delta_ms;
	pid_t pid;
	char comm[TASK_COMM_LEN];
	bool is_rapid;

	/* Filter: only process actual keycode events */
	if (code != KBD_KEYCODE)
		return NOTIFY_OK;

	/* Get current process context */
	task = current;
	pid = task_pid_nr(task);
	get_task_comm(comm, task);

	/* RATE LIMITING: Check if event allowed */
	if (!rate_limit_check(pid)) {
		dropped_events++;
		return NOTIFY_OK;  /* Drop event but allow normal keyboard processing */
	}

	/* Update global behavioral counters */
	event_count++;
	if (param->down)
		press_count++;
	else
		release_count++;

	/* Calculate inter-event timing (for rapid typing detection) */
	current_jiffies = jiffies;
	is_rapid = false;
	if (last_event_jiffies != 0) {
		time_delta_ms = jiffies_to_msecs(current_jiffies - last_event_jiffies);
		if (time_delta_ms < RAPID_THRESHOLD_MS) {
			rapid_events++;
			is_rapid = true;
		}
	}
	last_event_jiffies = current_jiffies;

	/* Build Netlink event message */
	memset(&event, 0, sizeof(event));
	event.timestamp_ns = ktime_get_ns();  /* High-precision timestamp */
	event.pid = pid;
	strncpy(event.comm, comm, TASK_COMM_LEN);
	event.comm[TASK_COMM_LEN - 1] = '\0';  /* Ensure null-termination */
	event.event_type = param->down ? 0 : 1;  /* 0=press, 1=release */
	event.rapid_flag = is_rapid ? 1 : 0;

	/* Send to userspace daemon via Netlink */
	netlink_send_event(&event);

	/*
	 * IMPORTANT: Return NOTIFY_OK (not NOTIFY_STOP)
	 * This allows the keyboard event to propagate normally
	 * We are observing, not intercepting
	 */
	return NOTIFY_OK;
}

/*
 * Notifier block registration structure
 * Priority 0 = default (runs after core handlers, before user handlers)
 */
static struct notifier_block fyp_nb = {
	.notifier_call = fyp_keyboard_notifier,
	.priority = 0,
};

/* ========================================================================
 * PROCFS INTERFACE (STATISTICS FALLBACK)
 * ======================================================================== */

/* Procfs entries */
static struct proc_dir_entry *proc_dir = NULL;
static struct proc_dir_entry *proc_stats = NULL;

/*
 * /proc/fyp_detector/stats reader
 * 
 * Displays current statistics in key=value format
 * Useful for debugging and monitoring
 */
static int stats_show(struct seq_file *m, void *v)
{
	unsigned long uptime_ms;

	uptime_ms = jiffies_to_msecs(jiffies - module_start_jiffies);

	seq_printf(m, "uptime_ms=%lu\n", uptime_ms);
	seq_printf(m, "total_events=%lu\n", event_count);
	seq_printf(m, "press_events=%lu\n", press_count);
	seq_printf(m, "release_events=%lu\n", release_count);
	seq_printf(m, "rapid_events=%lu\n", rapid_events);
	seq_printf(m, "dropped_events=%lu\n", dropped_events);
	seq_printf(m, "netlink_errors=%lu\n", netlink_send_errors);

	if (event_count > 0) {
		seq_printf(m, "rapid_ratio=%lu\n", (rapid_events * 100) / event_count);
	}

	return 0;
}

static int stats_open(struct inode *inode, struct file *file)
{
	return single_open(file, stats_show, NULL);
}

static const struct proc_ops stats_ops = {
	.proc_open = stats_open,
	.proc_read = seq_read,
	.proc_lseek = seq_lseek,
	.proc_release = single_release,
};

/* ========================================================================
 * MODULE INITIALIZATION AND CLEANUP
 * ======================================================================== */

/*
 * Module initialization
 * 
 * Sets up:
 * 1. Netlink socket for event delivery
 * 2. Procfs interface for statistics
 * 3. Keyboard notifier for event capture
 * 4. Rate limiter hash table
 */
static int __init fyp_init(void)
{
	struct netlink_kernel_cfg cfg = {
		.input = netlink_recv_handler,
	};
	int ret;

	pr_info("fyp_detector: Initializing keylogger detection module v0.5\n");

	/* Record module start time */
	module_start_jiffies = jiffies;

	/* Initialize rate limiter hash table */
	hash_init(rate_limiters);

	/* Create Netlink socket */
	nl_sock = netlink_kernel_create(&init_net, NETLINK_FYP_DETECTOR, &cfg);
	if (!nl_sock) {
		pr_err("fyp_detector: Failed to create Netlink socket\n");
		return -ENOMEM;
	}
	pr_info("fyp_detector: Netlink socket created (protocol %d)\n", NETLINK_FYP_DETECTOR);

	/* Create procfs directory */
	proc_dir = proc_mkdir("fyp_detector", NULL);
	if (!proc_dir) {
		pr_warn("fyp_detector: Failed to create /proc/fyp_detector directory\n");
		/* Non-fatal - continue without procfs */
	} else {
		/* Create stats file */
		proc_stats = proc_create("stats", 0444, proc_dir, &stats_ops);
		if (!proc_stats) {
			pr_warn("fyp_detector: Failed to create /proc/fyp_detector/stats\n");
		}
	}

	/* Register keyboard notifier */
	ret = register_keyboard_notifier(&fyp_nb);
	if (ret) {
		pr_err("fyp_detector: Failed to register keyboard notifier (%d)\n", ret);
		if (proc_stats) proc_remove(proc_stats);
		if (proc_dir) proc_remove(proc_dir);
		netlink_kernel_release(nl_sock);
		return ret;
	}

	pr_info("fyp_detector: Module loaded successfully\n");
	pr_info("fyp_detector: Waiting for daemon registration...\n");
	pr_info("fyp_detector: Statistics available at /proc/fyp_detector/stats\n");

	return 0;
}

/*
 * Module cleanup
 * 
 * Tears down:
 * 1. Keyboard notifier
 * 2. Procfs interface
 * 3. Netlink socket
 * 4. Rate limiter entries
 */
static void __exit fyp_exit(void)
{
	pr_info("fyp_detector: Unloading module...\n");

	/* Unregister keyboard notifier (stop capturing events) */
	unregister_keyboard_notifier(&fyp_nb);
	pr_info("fyp_detector: Keyboard notifier unregistered\n");

	/* Remove procfs entries */
	if (proc_stats) proc_remove(proc_stats);
	if (proc_dir) proc_remove(proc_dir);
	pr_info("fyp_detector: Procfs interface removed\n");

	/* Release Netlink socket */
	if (nl_sock) {
		netlink_kernel_release(nl_sock);
		pr_info("fyp_detector: Netlink socket released\n");
	}

	/* Cleanup rate limiters */
	rate_limiter_cleanup();
	pr_info("fyp_detector: Rate limiters cleaned up\n");

	pr_info("fyp_detector: Module unloaded (captured %lu events, dropped %lu)\n",
		event_count, dropped_events);
}

module_init(fyp_init);
module_exit(fyp_exit);
