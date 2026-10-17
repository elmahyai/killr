/*
   The R-level steps that turn an EM factor into pdSymm parameters.

   This file is not part of nlme. In R, MEEM (R/lme.R) ends with
   matrix(object[[i]]) <- crossprod(matrix(zz[...], ncol = q)). For a
   pdSymm, matrix<-.pdMat calls chol() and pdConstruct.pdSymm then takes
   svd() of that factor and returns v %*% (log(d) * t(v)) as the parameters
   (upper triangle, column-major). The steps below call the same BLAS and
   LAPACK routines R calls, in the same order and with the same workspace
   queries, so the parameters match R's bit for bit:

     crossprod(B)         R: symcrossprod   -> dsyrk("U", "T")
     chol(M)              R: La_chol        -> dpotrf("U"), lower zeroed
     svd(U, nu = 0)       R: La_svd         -> dgesdd("S")
     log(d) * t(v)        R: elementwise, log from libm
     v %*% B              R: matprod        -> dgemm("N", "N") or dgemv (q = 1)

   GPL-2.0-or-later, as the nlme sources: see LICENSE.note.
*/

#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "R.h"

void F77_NAME(dsyrk)(const char *uplo, const char *trans, int *n, int *k,
		     double *alpha, double *a, int *lda, double *beta,
		     double *c, int *ldc, size_t uplo_len, size_t trans_len);
void F77_NAME(dpotrf)(const char *uplo, int *n, double *a, int *lda,
		      int *info, size_t uplo_len);
void F77_NAME(dgesdd)(const char *jobz, int *m, int *n, double *a, int *lda,
		      double *s, double *u, int *ldu, double *vt, int *ldvt,
		      double *work, int *lwork, int *iwork, int *info,
		      size_t jobz_len);
void F77_NAME(dgemm)(const char *transa, const char *transb, int *m, int *n,
		     int *k, double *alpha, double *a, int *lda, double *b,
		     int *ldb, double *beta, double *c, int *ldc,
		     size_t transa_len, size_t transb_len);
void F77_NAME(dgemv)(const char *trans, int *m, int *n, double *alpha,
		     double *a, int *lda, double *x, int *incx, double *beta,
		     double *y, int *incy, size_t trans_len);

/* block: q x q column-major (the EM factor block). params: q (q + 1) / 2
   values out. Returns 0, or 1 with msg set when a LAPACK step fails. */
int
nlme_pdsymm_start(double *block, int q, double *params, char *msg,
		  size_t msglen)
{
    int n = q, one_i = 1, info = 0, lwork = -1, i, j, k;
    double one = 1.0, zero = 0.0;
    double *m, *u, *a, *uu, *s, *vt, *v, *b, *obj, *work, tmp;
    int *iwork;
    char *uplo_u = "U", *trans_t = "T", *trans_n = "N", *jobz_s = "S";

    if (q < 1) {
	if (msg && msglen) snprintf(msg, msglen, "order must be positive");
	return 1;
    }
    m   = R_Calloc((size_t) q * q, double);
    u   = R_Calloc((size_t) q * q, double);
    a   = R_Calloc((size_t) q * q, double);
    uu  = R_Calloc((size_t) q * q, double);
    s   = R_Calloc((size_t) q, double);
    vt  = R_Calloc((size_t) q * q, double);
    v   = R_Calloc((size_t) q * q, double);
    b   = R_Calloc((size_t) q * q, double);
    obj = R_Calloc((size_t) q * q, double);
    iwork = R_Calloc((size_t) (8 * q), int);

    /* symcrossprod: dsyrk on the upper triangle, then mirror it. */
    F77_CALL(dsyrk)(uplo_u, trans_t, &n, &n, &one, block, &n, &zero, m, &n, 1, 1);
    for (i = 1; i < q; i++)
	for (j = 0; j < i; j++)
	    m[i + (size_t) q * j] = m[j + (size_t) q * i];

    /* La_chol: the lower triangle is zeroed, then dpotrf("U"). */
    memcpy(u, m, sizeof(double) * (size_t) q * q);
    for (j = 0; j < q; j++)
	for (i = j + 1; i < q; i++)
	    u[i + (size_t) q * j] = 0.0;
    F77_CALL(dpotrf)(uplo_u, &n, u, &n, &info, 1);
    if (info != 0) {
	if (msg && msglen) {
	    if (info > 0)
		snprintf(msg, msglen, "the leading minor of order %d is not positive", info);
	    else
		snprintf(msg, msglen, "argument %d of Lapack routine dpotrf had invalid value", -info);
	}
	goto fail;
    }

    /* La_svd with jobu "S": workspace query, then the call. */
    memcpy(a, u, sizeof(double) * (size_t) q * q);
    F77_CALL(dgesdd)(jobz_s, &n, &n, a, &n, s, uu, &n, vt, &n, &tmp, &lwork, iwork, &info, 1);
    if (info != 0) goto fail;
    lwork = (int) tmp;
    work = R_Calloc((size_t) lwork, double);
    memcpy(a, u, sizeof(double) * (size_t) q * q);
    F77_CALL(dgesdd)(jobz_s, &n, &n, a, &n, s, uu, &n, vt, &n, work, &lwork, iwork, &info, 1);
    R_Free(work);
    if (info != 0) {
	if (msg && msglen) snprintf(msg, msglen, "error code %d from Lapack routine 'dgesdd'", info);
	goto fail;
    }
    /* The right singular vectors are vt, so v = t(vt). */
    for (j = 0; j < q; j++)
	for (i = 0; i < q; i++)
	    v[i + (size_t) q * j] = vt[j + (size_t) q * i];

    /* log(d) * t(v): t(v)[i, j] = v[j, i] scaled by log(d[i]). */
    for (j = 0; j < q; j++)
	for (i = 0; i < q; i++)
	    b[i + (size_t) q * j] = log(s[i]) * v[j + (size_t) q * i];

    /* v %*% B: dgemv for q = 1 (ncy == 1), dgemm otherwise. */
    if (q == 1) {
	F77_CALL(dgemv)(trans_n, &n, &n, &one, v, &n, b, &one_i, &zero, obj, &one_i, 1);
    } else {
	F77_CALL(dgemm)(trans_n, trans_n, &n, &n, &n, &one, v, &n, b, &n, &zero, obj, &n, 1, 1);
    }

    /* object[row(object) <= col(object)], column-major. */
    k = 0;
    for (j = 0; j < q; j++)
	for (i = 0; i <= j; i++)
	    params[k++] = obj[i + (size_t) q * j];

    R_Free(m); R_Free(u); R_Free(a); R_Free(uu); R_Free(s); R_Free(vt);
    R_Free(v); R_Free(b); R_Free(obj); R_Free(iwork);
    return 0;

fail:
    R_Free(m); R_Free(u); R_Free(a); R_Free(uu); R_Free(s); R_Free(vt);
    R_Free(v); R_Free(b); R_Free(obj); R_Free(iwork);
    return 1;
}
