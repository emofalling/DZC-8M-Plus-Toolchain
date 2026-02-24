// 先赋值
MOVLZ R0, -125, 0
MOVLZ R1, -120, 0

CMP R0, R1
AND R2, AF, 0b010  // 提取 AF:C 位
PAUSE
/*unsigned:
R0 < R1，R2 ≠ 0;
R0 ≥ R1，R2 = 0;
*/


CMP R0, R1
AND R2, AF, 0b011  // 提取 AF:C 和 AF:Z
PAUSE
/*unsigned:
R0 ≤ R1，R2 ≠ 0
R0 > R1，R2 = 0
*/

SUB R2, R0, R1  // R2 = R0 - R1
// 此时AF:2 = O (溢出标志)
SHR R2, R2, 5   // 将结果右移到最低位，此时R2:2 = N (符号位)
XOR R2, AF, R2  // [仅考虑第2位] 若O==N，R2:2=1；否则， R2[2]=0
AND R2, R2, 0b100 // 提取R2:2
PAUSE
/*signed:
R0 < R1，R2 ≠ 0;
R0 ≥ R1，R2 = 0;
*/

SUB R2, R0, R1      // R2 = R0 - R1，AF 中包含 O 和 Z
SHR R2, R2, 5       // 将结果右移 5 位，使符号位 N 移至第 2 位
AND R2, R2, 0b100   // 仅保留符号位 N（位于第 2 位）
XOR R2, AF, R2      // 比较 O 与 N：若 O == N 则 R2 第 2 位为 0，否则为 1；同时 AF 中的 Z 位被保留
AND R2, R2, 0b101   // 提取第 0 位（Z）和第 2 位（O != N 的结果）
PAUSE
/*signed:
R0 ≤ R1，R2 ≠ 0;
R0 > R1，R2 = 0;
*/