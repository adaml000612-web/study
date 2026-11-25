obj-m := hello.o
KDIR := /home/linux/workdir/linux-3.4.39
PWD := $(shell pwd)

all:
	$(MAKE) -C $(KDIR) M=$(PWD) modules
