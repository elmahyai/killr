#include <Rinternals.h>
#include <string.h>

SEXP R_miwa(SEXP steps, SEXP corr, SEXP upper, SEXP lower, SEXP infin);

double c_mvn_miwa(int steps, int dim, const double *corr, const double *upper,
                  const double *lower, const int *infin) {
    SEXP st = allocVector(INTSXP, 1);
    INTEGER(st)[0] = steps;
    SEXP c = allocVector(REALSXP, dim * dim);
    SEXP u = allocVector(REALSXP, dim);
    SEXP l = allocVector(REALSXP, dim);
    SEXP inf = allocVector(INTSXP, dim);
    memcpy(REAL(c), corr, (size_t)dim * (size_t)dim * sizeof(double));
    memcpy(REAL(u), upper, (size_t)dim * sizeof(double));
    memcpy(REAL(l), lower, (size_t)dim * sizeof(double));
    memcpy(INTEGER(inf), infin, (size_t)dim * sizeof(int));
    SEXP ans = R_miwa(st, c, u, l, inf);
    return REAL(ans)[0];
}
