#include <stddef.h>

typedef void (*dlsoda_deriv_fn)(int *neq, double *t, double *y, double *ydot);
typedef void (*dlsoda_jac_fn)(
    int *neq,
    double *t,
    double *y,
    int *ml,
    int *mu,
    double *pd,
    int *nrowpd
);
typedef void (*dlsoda_post_fn)(int *neq, double *t, double *y);

static dlsoda_deriv_fn g_deriv = NULL;
static dlsoda_jac_fn g_jac = NULL;
static dlsoda_post_fn g_post = NULL;

void dlsoda_set_callbacks(dlsoda_deriv_fn deriv, dlsoda_jac_fn jac, dlsoda_post_fn post) {
    g_deriv = deriv;
    g_jac = jac;
    g_post = post;
}

void dlsoda_f(int *neq, double *t, double *y, double *ydot, double *rpar, int *ipar) {
    (void)rpar;
    (void)ipar;
    if (g_deriv) {
        g_deriv(neq, t, y, ydot);
    }
}

void dlsoda_jac(
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

void dlsoda_jac_dummy(
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

void dlsoda_post_step(int *neq, double *t, double *y) {
    if (g_post) {
        g_post(neq, t, y);
    }
}
