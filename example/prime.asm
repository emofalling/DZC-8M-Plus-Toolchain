/*
从2开始输出所有质数
R0: 质数输出。当输出有效时，暂停。
R1: 与R0相除的值
R2: 缓存
*/

MOVZ R0, 2, 0 // R0 = 2

next:
    MOVZ R1, 2, 0 // R1 = 2
    check_loop:
        // R1 == R0, goto is_prime
        XOR R2, R0, R1
        MOVLZ PC, is_prime, R2
        // R2 = R0 % R1
        MOVZ R2, R0, 0 // R2 = R0
        // while(R2 >= R1) R2 -= R1
        mod_loop:
            SUB R2, R2, R1 // R2 -= R1，同时产生相较于原本的R1和R2的符号位
            AND AF, AF, 0b011 // 提取 AF:C|Z 位。R2 > R1, AF=0.
            MOVLZ PC, mod_loop, AF
        // if(R2 == 0) goto is_not_prime
        MOVLZ PC, is_not_prime, R2
        INC R1 // R1++
        MOVZ PC, check_loop, 0 // goto check_loop

    is_prime:
        PAUSE
    is_not_prime:
        INC R0 // R0++
        MOVZ PC, next, 0 // goto next