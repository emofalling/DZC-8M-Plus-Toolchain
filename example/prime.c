#include <stdio.h>
#include <stdint.h>

// prime.asm 参考代码

uint8_t R0;
uint8_t R1;
uint8_t R2;
uint8_t R3;

int main() {
    _start:
    R0 = 2; // 起始质数
    start:

    check_start:
    R1 = 2;
    while(1) {
        // 如果R1 == R0，认为R0是质数
        if (R1 == R0) {
            goto is_prime;
        }
        /*
        R2 = R0 % R1;
        */
        R2 = R0;
        while (R2 >= R1){
            R2 -= R1;
        }
        if (R2 == 0) {
            // 不是质数
            goto is_not_prime;
        }
        R1++;
    }
    is_not_prime:
        R0++;
        goto start;
    is_prime:
    printf("Prime: %d\nEnter to continue...", R0);
    // 等待Enter
    getchar();
    R0++;
    goto start;
}