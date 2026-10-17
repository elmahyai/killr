#include "e1071_rng.h"

static unsigned long libsvm_rng_state = 1;

void e1071_libsvm_set_rng(unsigned long seed) { libsvm_rng_state = seed ? seed : 1; }

double e1071_unif_rand(void)
{
    libsvm_rng_state = libsvm_rng_state * 6364136223846793005UL + 1;
    return (double)((libsvm_rng_state >> 33) & 0x7fffffff) / 2147483648.0;
}
