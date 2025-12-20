/*
 * FYP Keylogger Detection - Kernel Module v0.6 (Runtime Configuration Edition)
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
 *   - Process context (PID, comm, cmdline)
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
 *   FALLBACK: Procfs interface
 *     /proc/fyp_detector/stats - Current statistics (read-only)
 *     /proc/fyp_detector/config - Runtime configuration (read/write)
 * 
 * RATE LIMITING:
 * - Token bucket per-PID (1000 events/sec max per process)
 * - Anti-flood protection against malicious synthetic events
 * - Dropped events counted in statistics
 * 
 * RUNTIME CONFIGURATION (via sysfs):
 * - /sys/module/fyp_kbd/parameters/rapid_threshold_ms (default: 50ms)
 * - /sys/module/fyp_kbd/parameters/burst_threshold_eps (default: 100 events/sec)
 * 
 * SAFETY NOTES:
 * - Keyboard notifier runs in atomic context (cannot sleep)
 * - All allocations use GFP_ATOMIC (safe for interrupt context)
 * - Netlink send is non-blocking
 * - Process context (current) may be interrupt context (PID 0/swapper)
 * - Workqueue used for delayed cmdline capture (avoids atomic context issues)
 */

#include <linux/module.h>
#include <linux/kernel.h>
#include <linux/init.h>
#include <linux/keyboard.h>
#include <linux/notifier.h>
#include <linux/sched.h>          /* for task_struct, current */
#include <linux/sched/signal.h>   /* for task_lock */
#include <linux/sched/mm.h>       /* for mm_struct access */
#include <linux/mm.h>             /* for memory management */
#include <linux/jiffies.h>        /* for timing analysis */
#include <linux/proc_fs.h>        /* for procfs fallback */
#include <linux/seq_file.h>       /* for seq_file API */
#include <linux/spinlock.h>       /* for rate limiter locks */
#include <linux/slab.h>           /* for kmalloc/kfree */
#include <linux/hashtable.h>      /* for per-PID rate limiter */
#include <linux/workqueue.h>      /* for deferred cmdline capture */
#include <net/sock.h>             /* for netlink */
#include <net/netlink.h>          /* for netlink APIs */
#include <linux/uaccess.h>        /* for copy_from_user */

MODULE_LICENSE("GPL");
MODULE_AUTHOR("FYP Team");
MODULE_DESCRIPTION("FYP Keylogger Detection - Behavioral Observer with Runtime Config");
MODULE_VERSION("0.6");

/* ========================================================================
 * RUNTIME CONFIGURATION (MODULE PARAMETERS)
 * ======================================================================== */

/*
 * Runtime-tunable parameters via sysfs
 * 
 * Examples:
 *   echo 100 > /sys/module/fyp_kbd/parameters/rapid_threshold_ms
 *   echo 200 > /sys/module/fyp_kbd/parameters/burst_threshold_eps
 */
static int rapid_threshold_ms = 50;
module_param(rapid_threshold_ms, int, 0644);
MODULE_PARM_DESC(rapid_threshold_ms, "Threshold in ms for rapid event detection (default: 50)");

static int burst_threshold_eps = 100;
module_param(burst_threshold_eps, int, 0644);
MODULE_PARM_DESC(burst_threshold_eps, "Threshold in events/sec for burst detection (default: 100)");

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
 * Netlink Event Message Format (STABLE ABI v2)
 * Total size: 158 bytes (fixed, includes cmdline)
 * 
 * Userspace must use matching struct for parsing
 */
struct fyp_netlink_event {
	__u64 timestamp_ns;          /* Event time (nanoseconds since boot) */
	__u32 pid;                   /* Process ID (may be 0 for interrupt context) */
	char comm[TASK_COMM_LEN];    /* Process name (16 bytes, null-terminated) */
	char cmdline[128];           /* Process command line (captured via workqueue) */
	__u8 event_type;             /* 0=press, 1=release */
	__u8 rapid_flag;             /* 1 if inter-event time <rapid_threshold_ms */
} __attribute__((packed));

/* Netlink socket */
static struct sock *nl_sock = NULL;

/* Userspace daemon PID (for unicast delivery) */
static __u32 daemon_pid = 0;
static DEFINE_SPINLOCK(daemon_pid_lock);

/* ========================================================================
 * WORKQUEUE FOR DEFERRED CMDLINE CAPTURE
 * ======================================================================== */

/*
 * Workqueue work item for cmdline extraction
 * 
 * Why workqueue?
 * - Keyboard notifier runs in atomic context (cannot access mm_struct safely)
 * - Cmdline requires reading from process memory (mm->arg_start to mm->arg_end)
 * - Workqueue runs in process context where we can safely access memory
 */
struct cmdline_work {
	struct work_struct work;
	pid_t pid;
	char comm[TASK_COMM_LEN];
	__u64 timestamp_ns;
	__u8 event_type;
	__u8 rapid_flag;
};

/*
 * Extract process cmdline safely
 * 
 * @pid: Process ID
 * @cmdline: Output buffer (128 bytes)
 * 
 * Return: 0 on success, negative on error
 * 
 * Context: Process context (workqueue handler)
 */
static int extract_cmdline(pid_t pid, char *cmdline)
{
	struct task_struct *task;
	struct mm_struct *mm;
	unsigned long arg_start, arg_end, len;
	int ret = 0;

	memset(cmdline, 0, 128);

	/* Find task by PID */
	rcu_read_lock();
	task = pid_task(find_vpid(pid), PIDTYPE_PID);
	if (!task) {
		rcu_read_unlock();
		return -ESRCH;
	}

	/* Get mm_struct with reference count */
	mm = get_task_mm(task);
	rcu_read_unlock();

	if (!mm) {
		/* Kernel thread or exiting process - no mm */
		strncpy(cmdline, "[kernel]", 128);
		return 0;
	}

	/* Extract cmdline from memory */
	arg_start = mm->arg_start;
	arg_end = mm->arg_end;

	if (arg_start >= arg_end) {
		mmput(mm);
		return -EINVAL;
	}

	len = arg_end - arg_start;
	if (len > 127)
		len = 127;

	/* Copy cmdline from user memory */
	ret = access_process_vm(task, arg_start, cmdline, len, 0);
	if (ret <= 0) {
		mmput(mm);
		return -EFAULT;
	}

	/* Replace null bytes with spaces for readability */
	int i;
	for (i = 0; i < ret - 1; i++) {
		if (cmdline[i] == '\0')
			cmdline[i] = ' ';
	}
	cmdline[ret] = '\0';

	mmput(mm);
	return 0;
}

/* Forward declaration */
static int netlink_send_event(const struct fyp_netlink_event *event);

/*
 * Workqueue handler for cmdline capture
 * 
 * Context: Process context (system_wq)
 */
static void cmdline_work_handler(struct work_struct *work)
{
	struct cmdline_work *cmd_work = container_of(work, struct cmdline_work, work);
	struct fyp_netlink_event event;

	/* Build complete event with cmdline */
	memset(&event, 0, sizeof(event));
	event.timestamp_ns = cmd_work->timestamp_ns;
	event.pid = cmd_work->pid;
	strncpy(event.comm, cmd_work->comm, TASK_COMM_LEN);
	event.event_type = cmd_work->event_type;
	event.rapid_flag = cmd_work->rapid_flag;

	/* Extract cmdline (safe in process context) */
	if (extract_cmdline(cmd_work->pid, event.cmdline) < 0) {
		strncpy(event.cmdline, "[unavailable]", 128);
	}

	/* Send event via netlink */
	netlink_send_event(&event);

	/* Free work item */
	kfree(cmd_work);
}

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
static unsigned long rapid_events = 0;      /* Events within rapid_threshold_ms */
static unsigned long dropped_events = 0;    /* Rate-limited events */
static unsigned long netlink_send_errors = 0;  /* Failed sends */
static unsigned long cmdline_work_queued = 0;  /* Workqueue items scheduled */
static unsigned long last_event_jiffies = 0;
static unsigned long module_start_jiffies = 0;

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
	struct cmdline_work *work;
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
		if (time_delta_ms < rapid_threshold_ms) {
			rapid_events++;
			is_rapid = true;
		}
	}
	last_event_jiffies = current_jiffies;

	/* Schedule workqueue for cmdline capture and event delivery */
	{
		struct cmdline_work *work = kmalloc(sizeof(*work), GFP_ATOMIC);
		if (work) {
			INIT_WORK(&work->work, cmdline_work_handler);
			work->pid = pid;
			strncpy(work->comm, comm, TASK_COMM_LEN);
			work->timestamp_ns = ktime_get_ns();
			work->event_type = param->down ? 0 : 1;
			work->rapid_flag = is_rapid ? 1 : 0;
			
			schedule_work(&work->work);
			cmdline_work_queued++;
		} else {
			/* Fallback: send basic event without cmdline */
			struct fyp_netlink_event fallback_event;
			memset(&fallback_event, 0, sizeof(fallback_event));
			fallback_event.timestamp_ns = ktime_get_ns();
			fallback_event.pid = pid;
			strncpy(fallback_event.comm, comm, TASK_COMM_LEN);
			fallback_event.event_type = param->down ? 0 : 1;
			fallback_event.rapid_flag = is_rapid ? 1 : 0;
			strncpy(fallback_event.cmdline, "[oom]", 128);
			netlink_send_event(&fallback_event);
		}
	}

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
static struct proc_dir_entry *proc_config = NULL;

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
	seq_printf(m, "cmdline_work_queued=%lu\n", cmdline_work_queued);

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

/*
 * /proc/fyp_detector/config reader
 * 
 * Displays current configuration parameters
 */
static int config_show(struct seq_file *m, void *v)
{
	seq_printf(m, "rapid_threshold_ms=%d\n", rapid_threshold_ms);
	seq_printf(m, "burst_threshold_eps=%d\n", burst_threshold_eps);
	seq_printf(m, "\n# Runtime tunable via sysfs:\n");
	seq_printf(m, "# echo VALUE > /sys/module/fyp_kbd/parameters/rapid_threshold_ms\n");
	seq_printf(m, "# echo VALUE > /sys/module/fyp_kbd/parameters/burst_threshold_eps\n");
	return 0;
}

static int config_open(struct inode *inode, struct file *file)
{
	return single_open(file, config_show, NULL);
}

static const struct proc_ops config_ops = {
	.proc_open = config_open,
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

	pr_info("fyp_detector: Initializing keylogger detection module v0.6\n");

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
		
		/* Create config file */
		proc_config = proc_create("config", 0444, proc_dir, &config_ops);
		if (!proc_config) {
			pr_warn("fyp_detector: Failed to create /proc/fyp_detector/config\n");
		}
	}

	/* Register keyboard notifier */
	ret = register_keyboard_notifier(&fyp_nb);
	if (ret) {
		pr_err("fyp_detector: Failed to register keyboard notifier (%d)\n", ret);
		if (proc_config) proc_remove(proc_config);
		if (proc_stats) proc_remove(proc_stats);
		if (proc_dir) proc_remove(proc_dir);
		netlink_kernel_release(nl_sock);
		return ret;
	}

	pr_info("fyp_detector: Module loaded successfully\n");
	pr_info("fyp_detector: Runtime config: rapid_threshold=%dms, burst_threshold=%deps\n", 
		rapid_threshold_ms, burst_threshold_eps);
	pr_info("fyp_detector: Waiting for daemon registration...\n");
	pr_info("fyp_detector: Statistics: /proc/fyp_detector/stats\n");
	pr_info("fyp_detector: Configuration: /proc/fyp_detector/config\n");
	pr_info("fyp_detector: Tune via: echo VALUE > /sys/module/fyp_kbd/parameters/PARAM\n");

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

	/* Flush workqueue (wait for pending cmdline captures) */
	flush_scheduled_work();
	pr_info("fyp_detector: Workqueue flushed (%lu items processed)\n", cmdline_work_queued);

	/* Remove procfs entries */
	if (proc_config) proc_remove(proc_config);
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
