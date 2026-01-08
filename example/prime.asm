/*
example: 查找质数
*/
/*
寄存器功能：
R0: 质数输出
R1: 计数器
R2: 缓存变量
*/

//_start:
    MOVZ R0, 2, 0  // R0 = 2


check:
    MOVZ R1, 2, 0  // R1 = 2

loop_check:
    // if R1 == R0 , goto is_prime
    XOR R2, R1, R0
    MOVLZ PC, is_prime, R2  // if R2 == 0 goto is_prime
    // start: R2 = R0 % R1
    MOVZ R2, R0, 0  // R2 = R0
loop_mod:
    // R2 -= R1, and set flags
    SUB R2, R2, R1
    // if R2 > R1, continue loop
    // if AF.CF|AF.ZF == 0, R2 > R1
    AND AF, AF, 0b011 // keep CF|ZF
    MOVLZ PC, loop_mod, AF  // if R2 > R1 goto loop_mod
// loop_mod end
    // if R2 == 0 goto is_not_prime
    MOVLZ PC, is_not_prime, R2  // if R2 == 0 goto is_not_prime
    INC R1  // R1++
    MOVZ PC, loop_check, 0  // goto loop_check

is_prime:
    PAUSE
is_not_prime:
    INC R0  // R0++
    MOVZ PC, check, 0  // goto check

