obj-m += fyp_kbd.o

KDIR := /lib/modules/$(shell uname -r)/build

all:
	$(MAKE) -C $(KDIR) M=$(PWD) modules

clean:
	$(MAKE) -C $(KDIR) M=$(PWD) clean
	rm -f *.o *.ko *.mod* .*.cmd modules.order Module.symvers

install:
	sudo insmod fyp_kbd.ko

remove:
	sudo rmmod fyp_kbd

logs:
	sudo dmesg | tail -20
