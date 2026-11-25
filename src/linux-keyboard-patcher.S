# Copyright (C) 2026 Blek
# SPDX-License-Identifier: GPL-3.0-only
.section .rodata
python_path:
    .asciz "/usr/bin/python3"
proc_exe_path:
    .asciz "/proc/self/exe"
python_c_flag:
    .asciz "-c"
binary_path_flag:
    .asciz "--binary-path"

.section .text
.global _start
.type _start, @function
_start:
    movq (%rsp), %r12                 # original argc
    cmpq $500, %r12
    ja .Lexit_error
    leaq 8(%rsp), %r13               # original argv

    # Resolve this executable's path so pkexec can relaunch the same binary.
    leaq proc_exe_path(%rip), %rdi
    leaq binary_path(%rip), %rsi
    movq $4095, %rdx
    movq $89, %rax                   # readlink
    syscall
    testq %rax, %rax
    jle .Lexit_error
    leaq binary_path(%rip), %r14
    movb $0, (%r14,%rax,1)

    # Python -c receives the embedded source and the app's arguments.
    leaq new_argv(%rip), %r15
    leaq python_path(%rip), %rax
    movq %rax, 0(%r15)
    leaq python_c_flag(%rip), %rax
    movq %rax, 8(%r15)
    leaq embedded_app(%rip), %rax
    movq %rax, 16(%r15)
    leaq binary_path_flag(%rip), %rax
    movq %rax, 24(%r15)
    leaq binary_path(%rip), %rax
    movq %rax, 32(%r15)

    movq $1, %r10                    # copy original argv[1:] to argv[5:]
.Lcopy_args:
    cmpq %r12, %r10
    jae .Largs_done
    movq (%r13,%r10,8), %rax
    movq %rax, 32(%r15,%r10,8)
    incq %r10
    jmp .Lcopy_args

.Largs_done:
    movq $0, 32(%r15,%r12,8)         # NULL at new argc + 4
    movq $59, %rax                   # execve
    leaq python_path(%rip), %rdi
    movq %r15, %rsi
    leaq 8(%r13,%r12,8), %rdx        # original envp
    syscall

.Lexit_error:
    movq $127, %rdi
    movq $60, %rax                   # exit
    syscall
.size _start, .-_start

.section .rodata
.balign 16
embedded_app:
    .incbin "app-embedded.py"
    .byte 0

.section .bss
.balign 16
new_argv:
    .zero 4096
binary_path:
    .zero 4096

.section .note.GNU-stack,"",@progbits
