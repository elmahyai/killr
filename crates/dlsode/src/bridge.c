#include <stddef.h>

typedef void (*lsode_deriv_fn)(int *neq, double *t, double *y, double *ydot);
typedef void (*lsode_jac_fn)(
    int *neq,
    double *t,
    double *y,
    int *ml,
    int *mu,
    double *pd,
    int *nrowpd
);

static lsode_deriv_fn g_deriv = NULL;
static lsode_jac_fn g_jac = NULL;

void lsode_set_callbacks(lsode_deriv_fn deriv, lsode_jac_fn jac) {
    g_deriv = deriv;
    g_jac = jac;
}

void lsode_f(int *neq, double *t, double *y, double *ydot, double *rpar, int *ipar) {
    (void)rpar;
    (void)ipar;
    if (g_deriv) {
        g_deriv(neq, t, y, ydot);
    }
}

void lsode_jac_dummy(
    int *neq,
    double *t,
    double *y,
    int *ml,
    int *mu,
    double *pd,
    int *nrowpd
) {
    (void)neq;
    (void)t;
    (void)y;
    (void)ml;
    (void)mu;
    (void)pd;
    (void)nrowpd;
    if (g_jac) {
        g_jac(neq, t, y, ml, mu, pd, nrowpd);
    }
}
