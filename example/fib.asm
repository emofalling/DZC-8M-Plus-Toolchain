/*
Fibonacci Sequence Generator
R0: Output
*/
//_start:
/* MOVZ R0, 1, 0 */ INC R0
/* MOVZ R1, 1, 0 */ INC R1
flag:
    PAUSE # User Input
    ADD R2, R0, R1 # R2 = R0 + R1
    MOVZ R0, R1, 0 # R0 = R1
    MOVZ R1, R2, 0 # R1 = R2
    MOVZ PC, flag, 0 # Loop