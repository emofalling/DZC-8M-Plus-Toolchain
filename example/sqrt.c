
int intsqrt(const int num) {
    if(num == 0) return 0;

    int low = 1;
    int high = num;
    int ans = 0;

    while(low <= high){
        int mid = (low + high) >> 1;
        /*if(mid * mid <= num){*/
        if(mid <= num/mid) {
            ans = mid;
            low = mid + 1;
        }else{
            high = mid - 1;
        }
    }

    return ans;
}

#include <stdio.h>
int main(){
    int num;
    printf("请输入一个整数：");
    scanf("%d", &num);
    int result = intsqrt(num);
    printf("%d的整数平方根是%d\n", num, result);
    return 0;
}