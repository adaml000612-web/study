#include "main.h"

void div(int a, int b)
{
    if (b == 0) {
        printf("Division by zero is undefined.\n");
        return;
    }
    printf("a/b=%f\n", (double)a / b);
}
