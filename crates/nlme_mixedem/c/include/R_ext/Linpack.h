/*
   Minimal R_ext/Linpack.h shim for the vendored nlme sources (see R.h).
   Signatures follow R's LINPACK routines in src/appl (dqrdc2.f, dqrsl.f,
   dtrsl.f, dqrls.f from R 4.5.0), which the vendored Fortran provides.
*/

#ifndef NLME_MIXEDEM_R_EXT_LINPACK_H
#define NLME_MIXEDEM_R_EXT_LINPACK_H

#include "RS.h"

void F77_NAME(dqrdc2)(double *x, int *ldx, int *n, int *p, double *tol,
		      int *rank, double *qraux, int *pivot, double *work);
void F77_NAME(dqrsl)(double *x, int *ldx, int *n, int *k, double *qraux,
		     double *y, double *qy, double *qty, double *b,
		     double *rsd, double *xb, int *job, int *info);
void F77_NAME(dqrls)(double *x, int *n, int *p, double *y, int *ny,
		     double *tol, double *b, double *rsd, double *qty,
		     int *k, int *jpvt, double *qraux, double *work);
void F77_NAME(dtrsl)(double *t, int *ldt, int *n, double *b, int *job,
		     int *info);

#endif /* NLME_MIXEDEM_R_EXT_LINPACK_H */
