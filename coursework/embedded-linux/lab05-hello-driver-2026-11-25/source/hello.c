#include <linux/init.h>
#include <linux/module.h>
#include <linux/kernel.h>

static int __init hello_init(void)
{
    printk(KERN_INFO "hello 202412902108 202412902113\n");
    return 0;
}

static void __exit hello_exit(void)
{
    printk(KERN_INFO "goodbye 202412902108 202412902113\n");
}

module_init(hello_init);
module_exit(hello_exit);

MODULE_LICENSE("GPL");
MODULE_AUTHOR("202412902108 202412902113");
MODULE_DESCRIPTION("Hello kernel module for embedded Linux lab 5");
