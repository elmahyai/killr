#include <stddef.h>

typedef void (*lsodar_deriv_fn)(int *neq, double *t, double *y, double *ydot);
typedef void (*lsodar_root_fn)(int *neq, double *t, double *y, int *ng, double *gout);
typedef void (*lsodar_jac_fn)(
    int *neq,
    double *t,
    double *y,
    int *ml,
    int *mu,
    double *pd,
    int *nrowpd
);

static lsodar_deriv_fn g_deriv = NULL;
static lsodar_root_fn g_root = NULL;
static lsodar_jac_fn g_jac = NULL;

void lsodar_set_callbacks(lsodar_deriv_fn deriv, lsodar_jac_fn jac, lsodar_root_fn root) {
    g_deriv = deriv;
    g_jac = jac;
    g_root = root;
}

void lsodar_f(int *neq, double *t, double *y, double *ydot, double *rpar, int *ipar) {
    (void)rpar;
    (void)ipar;
    if (g_deriv) {
        g_deriv(neq, t, y, ydot);
    }
}

void lsodar_g(int *neq, double *t, double *y, int *ng, double *gout, double *rpar, int *ipar) {
    (void)rpar;
    (void)ipar;
    if (g_root) {
        g_root(neq, t, y, ng, gout);
    }
}

void lsodar_jac(
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

void lsodar_jac_dummy(
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
}
