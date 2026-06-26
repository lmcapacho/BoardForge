.section .text
.global _start

.equ UART0_BASE, 0x10000000
.equ UART_THR, 0x00
.equ UART_LSR, 0x05
.equ UART_LSR_THRE, 0x20

_start:
    la s0, message
1:
    lbu a0, 0(s0)
    beqz a0, 2f
    jal ra, uart_putc
    addi s0, s0, 1
    j 1b

2:
    wfi
    j 2b

uart_putc:
    li t0, UART0_BASE
3:
    lbu t1, UART_LSR(t0)
    andi t1, t1, UART_LSR_THRE
    beqz t1, 3b
    sb a0, UART_THR(t0)
    ret

.section .rodata
message:
    .asciz "Hello from Boardforge!\r\n"
