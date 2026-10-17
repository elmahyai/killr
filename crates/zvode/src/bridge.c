#include <stddef.h>

typedef struct {
    double re;
    double im;
} zvode_complex;

typedef void (*zvode_deriv_fn)(int *neq, double *t, zvode_complex *y, zvode_complex *ydot);
typedef void (*zvode_jac_fn)(
    int *neq,
    double *t,
    zvode_complex *y,
    int *ml,
    int *mu,
    zvode_complex *pd,
    int *nrowpd
);

static zvode_deriv_fn g_deriv = NULL;
static zvode_jac_fn g_jac = NULL;

void zvode_set_callbacks(zvode_deriv_fn deriv, zvode_jac_fn jac) {
    g_deriv = deriv;
    g_jac = jac;
}

void zvode_f(
    int *neq,
    double *t,
    zvode_complex *y,
    zvode_complex *ydot,
    zvode_complex *rpar,
    int *ipar
) {
    (void)rpar;
    (void)ipar;
    if (g_deriv) {
        g_deriv(neq, t, y, ydot);
    }
}

void zvode_jac_dummy(
    int *neq,
    double *t,
    zvode_complex *y,
    int *ml,
    int *mu,
    zvode_complex *pd,
    int *nrowpd,
    zvode_complex *rpar,
    int *ipar
) {
    (void)rpar;
    (void)ipar;
    if (g_jac) {
        g_jac(neq, t, y, ml, mu, pd, nrowpd);
    }
}
