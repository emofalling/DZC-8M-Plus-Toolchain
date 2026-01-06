/*
移位乘法器
R0: 乘数1
R1: 乘数2
R2: 结果
R3: 临时寄存器
*/

// _start:
MOVZ R0, 6, 0
MOVZ R1, 7, 0

loop:
    AND R3, R1, 1 // 取最低位
    // 若 R3 == 1, 将 R0 加到 R2
    MOVLZ PC, skip_add, R3
// add:
    ADD R2, R2, R0
skip_add:
    // 将 R1 右移一位
    SHR R1, R1, 1
    // 将R0 左移一位
    SHL R0, R0, 1
    // 若 R1 != 0, 跳转到 loop. R0 ！= 0也可以, 但这样效率低
    MOVN PC, loop, R1