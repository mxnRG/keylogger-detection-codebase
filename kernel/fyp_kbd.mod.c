#include <linux/module.h>
#define INCLUDE_VERMAGIC
#include <linux/build-salt.h>
#include <linux/elfnote-lto.h>
#include <linux/vermagic.h>
#include <linux/compiler.h>

BUILD_SALT;
BUILD_LTO_INFO;

MODULE_INFO(vermagic, VERMAGIC_STRING);
MODULE_INFO(name, KBUILD_MODNAME);

__visible struct module __this_module
__section(".gnu.linkonce.this_module") = {
	.name = KBUILD_MODNAME,
	.init = init_module,
#ifdef CONFIG_MODULE_UNLOAD
	.exit = cleanup_module,
#endif
	.arch = MODULE_ARCH_INIT,
};

#ifdef CONFIG_RETPOLINE
MODULE_INFO(retpoline, "Y");
#endif

static const struct modversion_info ____versions[]
__used __section("__versions") = {
	{ 0xd3166ddb, "module_layout" },
	{ 0x489d4c0d, "single_release" },
	{ 0x9526f10e, "seq_lseek" },
	{ 0xed9b9516, "seq_read" },
	{ 0x37a0cba, "kfree" },
	{ 0x87a21cb3, "__ubsan_handle_out_of_bounds" },
	{ 0x9ed554b3, "unregister_keyboard_notifier" },
	{ 0xaaed2b3f, "netlink_kernel_release" },
	{ 0x8290fc60, "proc_remove" },
	{ 0x96554810, "register_keyboard_notifier" },
	{ 0x36621f31, "proc_create" },
	{ 0xacd0205e, "proc_mkdir" },
	{ 0x48ff7fc3, "__netlink_kernel_create" },
	{ 0x68f65135, "init_net" },
	{ 0xd0da656b, "__stack_chk_fail" },
	{ 0xabc74fb3, "netlink_unicast" },
	{ 0xb47e5161, "__nlmsg_put" },
	{ 0x794c6d79, "kfree_skb_reason" },
	{ 0xa72d62b6, "__alloc_skb" },
	{ 0x9166fada, "strncpy" },
	{ 0xb43f9365, "ktime_get" },
	{ 0xa0440539, "kmem_cache_alloc_trace" },
	{ 0x2c330630, "kmalloc_caches" },
	{ 0x4caefef8, "__get_task_comm" },
	{ 0xfac3ac2f, "current_task" },
	{ 0x80827451, "seq_printf" },
	{ 0x37befc70, "jiffies_to_msecs" },
	{ 0x15ba50a6, "jiffies" },
	{ 0xc866e771, "single_open" },
	{ 0x5b8239ca, "__x86_return_thunk" },
	{ 0x92997ed8, "_printk" },
	{ 0xd35cce70, "_raw_spin_unlock_irqrestore" },
	{ 0x34db050b, "_raw_spin_lock_irqsave" },
	{ 0xbdfb6dbb, "__fentry__" },
};

MODULE_INFO(depends, "");


MODULE_INFO(srcversion, "3FF413D99560562B45119F2");
