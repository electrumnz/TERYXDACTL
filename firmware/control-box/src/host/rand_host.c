// Host build: random numbers for the lock salt. /dev/urandom if there is one.
#include <stdio.h>
#include <stdlib.h>
#include <time.h>

#include "lock.h"

uint32_t lock_random32(void) {
    uint32_t r = 0;
    FILE *fp = fopen("/dev/urandom", "rb");
    if (fp) {
        size_t n = fread(&r, sizeof(r), 1, fp);
        fclose(fp);
        if (n == 1) return r;
    }
    static int seeded;
    if (!seeded) { srand((unsigned)time(NULL)); seeded = 1; }
    return ((uint32_t)rand() << 16) ^ (uint32_t)rand();
}
