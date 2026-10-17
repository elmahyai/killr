/*
 * Minimal stand-in for R's R.h, used only to compile the vendored ordinal
 * kernels (utilityFuns.c, links.c) outside R. It defines the handful of R API
 * names those files use: NA/Inf constants, finiteness tests, R_pow, R_pow_di,
 * fmin2, Rprintf and error. The distribution functions they call are declared
 * in Rmath.h and implemented in src/shim/rshim.c. Nothing here is a port of R's
 * evaluator.
 */
#ifndef ORDINAL_CLMM_SHIM_R_H
#define ORDINAL_CLMM_SHIM_R_H

#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include "Rmath.h"

#define R_PosInf INFINITY
#define R_NegInf (-INFINITY)
#define NA_REAL NAN
#define ISNAN(x) isnan(x)
#define R_FINITE(x) isfinite(x)

double R_pow(double x, double y);
double R_pow_di(double x, int n);
void Rprintf(const char *fmt, ...);
void error(const char *fmt, ...);

static inline double fmin2(double a, double b) { return (a < b) ? a : b; }

#endif
