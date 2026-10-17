#ifndef E1071_RNG_H
#define E1071_RNG_H

#ifdef __cplusplus
extern "C" {
#endif

void e1071_libsvm_set_rng(unsigned long seed);
double e1071_unif_rand(void);

#define GetRNGstate() ((void)0)
#define PutRNGstate() ((void)0)
#define unif_rand e1071_unif_rand
#define Rprintf(...) ((void)0)
#define REprintf(...) fprintf(stderr, __VA_ARGS__)

#ifdef __cplusplus
}
#endif

#endif
