#include <stddef.h>

typedef void (*lsoda_deriv_fn)(int *neq, double *t, double *y, double *ydot);
typedef void (*lsoda_jac_fn)(
    int *neq,
    double *t,
    double *y,
    int *ml,
    int *mu,
    double *pd,
    int *nrowpd
);

static lsoda_deriv_fn g_deriv = NULL;
static lsoda_jac_fn g_jac = NULL;

void lsoda_set_callbacks(lsoda_deriv_fn deriv, lsoda_jac_fn jac) {
    g_deriv = deriv;
    g_jac = jac;
}

void lsoda_f(int *neq, double *t, double *y, double *ydot, double *rpar, int *ipar) {
    (void)rpar;
    (void)ipar;
    if (g_deriv) {
        g_deriv(neq, t, y, ydot);
    }
}

void lsoda_jac(
    int *neq,
    double *t,
    double *y,
    int *ml,
    int *mu,
    double *pd,
    int *nrowpd,
    double *rpar,
    int *ipar
) {
    (void)rpar;
    (void)ipar;
    if (g_jac) {
        g_jac(neq, t, y, ml, mu, pd, nrowpd);
    }
}

void lsoda_jac_dummy(
    int *neq,
    double *t,
    double *y,
    int *ml,
    int *mu,
    double *pd,
    int *nrowpd,
    double *rpar,
    int *ipar
) {
    (void)neq;
    (void)t;
    (void)y;
    (void)ml;
    (void)mu;
    (void)pd;
    (void)nrowpd;
    (void)rpar;
    (void)ipar;
    if (g_jac) {
        g_jac(neq, t, y, ml, mu, pd, nrowpd);
    }
}
