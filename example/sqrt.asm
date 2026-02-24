/*
使用二分法求一个数的整数平方根
R0: 输入的数: num。不能
R1: R0的整数平方根: ans
R2: low
R3: high
SP: mid
IO: tmp
*/

MOVLZ R0, 16, 0  // R0 = num

// 对0的异常处理
MOVLZ PC, end, R0
// low=1, high=num, ans=0
MOVZ R2, 1, 0
MOVZ R3, R0, 0

// do{...}while(low <= high)
loop:
    // mid = (low + high) >> 1;
    ADD SP, R2, R3  // SP = low + high
    SHR SP, SP, 1   // SP = SP >> 1
    // tmp = num / mid
    MOVZ IO, 0, 0  // IO = 0
    // while(tmp) IO += mid, tmp -= 1
    MOVLZ PC, mul_end, SP // if mid == 0 goto mul_end
    mul_start:
        ADD IO, IO, SP  // IO += mid
        DEC SP  // mid --
        MOVLZ PC, mul_start, SP  // if mid != 0 goto mul_start
    mul_end: // IO = mid * mid
    // 此时AF=原SP，而SP=0。现需恢复SP
    /*
    if(IO <= R0){
        R1 = SP;
        R2 = SP + 1;
    }else{
        R3 = SP - 1;
    }
    */
    CMP IO, R0
    AND AF, AF, 0b011 // keep CF|ZF
    MOVLZ PC, io_not_less_equal, AF  // if !(IO <= R0) goto io_not_less_equal

    // io_less_equal
        MOVZ R1, SP, 0  // R1 = SP
        MOVZ R2, SP, 0  // R2 = SP
        INC R2  // R2 ++
    io_not_less_equal:
        MOVZ R3, SP, 0  // R3 = SP
        DEC R3  // R3 --
    
    // if(low <= high) goto loop
    CMP R2, R3
    AND AF, AF, 0b011 // keep CF|ZF
    MOVLN PC, loop, AF  // if low <= high goto loop

end:
    PAUSE