# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 Blek
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
    movl (%esp), %esi                 # original argc
    cmpl $500, %esi
    ja .Lexit_error
    leal 4(%esp), %edi               # original argv

    # Resolve this executable's path so pkexec can relaunch the same binary.
    movl $proc_exe_path, %ebx
    movl $binary_path, %ecx
    movl $4095, %edx
    movl $85, %eax                   # readlink
    int $0x80
    testl %eax, %eax
    jle .Lexit_error
    movb $0, binary_path(%eax)

    # Python -c receives the embedded source and the app's arguments.
    movl $new_argv, %ebp
    movl $python_path, 0(%ebp)
    movl $python_c_flag, 4(%ebp)
    movl $embedded_app, 8(%ebp)
    movl $binary_path_flag, 12(%ebp)
    movl $binary_path, 16(%ebp)

    movl $1, %ecx                    # copy original argv[1:] to argv[5:]
.Lcopy_args:
    cmpl %esi, %ecx
    jae .Largs_done
    movl (%edi,%ecx,4), %eax
    movl %eax, 16(%ebp,%ecx,4)
    incl %ecx
    jmp .Lcopy_args

.Largs_done:
    leal 16(%ebp,%esi,4), %eax       # NULL at new argc + 4
    movl $0, (%eax)
    movl $11, %eax                   # execve
    movl $python_path, %ebx
    movl %ebp, %ecx
    leal 8(%edi,%esi,4), %edx        # original envp
    int $0x80

.Lexit_error:
    movl $127, %ebx
    movl $1, %eax                    # exit
    int $0x80
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
