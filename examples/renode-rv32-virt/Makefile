CROSS ?= riscv64-unknown-elf
CC := $(CROSS)-gcc
OBJDUMP := $(CROSS)-objdump

CFLAGS := -march=rv32imac -mabi=ilp32 -nostdlib -ffreestanding -Wall -Wextra
LDFLAGS := -T linker.ld -Wl,--build-id=none

all: hello_uart.elf hello_uart.lst

hello_uart.elf: hello_uart.S linker.ld
	$(CC) $(CFLAGS) $(LDFLAGS) -o $@ hello_uart.S

hello_uart.lst: hello_uart.elf
	$(OBJDUMP) -D $< > $@

clean:
	rm -f hello_uart.elf hello_uart.lst
