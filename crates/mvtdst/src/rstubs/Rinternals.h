#ifndef MVTNORM_STUB_RINTERNALS_H
#define MVTNORM_STUB_RINTERNALS_H
#include <stdlib.h>
#include <string.h>

#define REALSXP 14
#define INTSXP 13

typedef struct SEXPREC {
    int type;
    int len;
    double *real;
    int *integer;
} *SEXP;

static inline double *REAL(SEXP s) { return s->real; }
static inline int *INTEGER(SEXP s) { return s->integer; }
static inline int LENGTH(SEXP s) { return s->len; }
#define PROTECT(x) (x)
#define UNPROTECT(n) ((void)(n))

static inline SEXP allocVector(int type, int n) {
    SEXP s = (SEXP)calloc(1, sizeof(struct SEXPREC));
    s->type = type;
    s->len = n;
    if (type == REALSXP)
        s->real = (double *)calloc((size_t)n, sizeof(double));
    else
        s->integer = (int *)calloc((size_t)n, sizeof(int));
    return s;
}
#endif
