/*
   Minimal Rinternals.h shim for the vendored nlme sources (see R.h).
   The list functions are declared so that nlmefit.c compiles. They are
   never reached from the mixed_EM path, and they abort if called.
*/

#ifndef NLME_MIXEDEM_RINTERNALS_H
#define NLME_MIXEDEM_RINTERNALS_H

#include <stddef.h>

typedef struct SEXPREC *SEXP;

typedef enum {
    NILSXP = 0,
    LGLSXP = 10,
    INTSXP = 13,
    REALSXP = 14,
    STRSXP = 16,
    VECSXP = 19
} SEXPTYPE;

extern SEXP R_NilValue;
extern SEXP R_NamesSymbol;

SEXP Rf_getAttrib(SEXP x, SEXP name);
int Rf_length(SEXP x);
SEXP STRING_ELT(SEXP x, long i);
const char *CHAR(SEXP x);
SEXP VECTOR_ELT(SEXP x, long i);
SEXP coerceVector(SEXP x, SEXPTYPE type);
int *INTEGER(SEXP x);
SEXP Rf_protect(SEXP x);
void Rf_unprotect(int n);

#define getAttrib Rf_getAttrib
#define length Rf_length
#define PROTECT(x) Rf_protect(x)
#define UNPROTECT(n) Rf_unprotect(n)

#endif /* NLME_MIXEDEM_RINTERNALS_H */
