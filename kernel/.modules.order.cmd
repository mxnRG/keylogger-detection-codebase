cmd_/home/fyp/project/kernel/modules.order := {   echo /home/fyp/project/kernel/fyp_kbd.ko; :; } | awk '!x[$$0]++' - > /home/fyp/project/kernel/modules.order
