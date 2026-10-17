/* Integration driver adapted from deSolve src/call_radau.c (basic R-func path). */

#include <stddef.h>
#include <stdlib.h>
#include <string.h>

typedef void (*deriv_fn)(int *, double *, double *, double *, double *, int *);
typedef void (*jac_fn)(int *, double *, double *, int *, int *, double *, int *,
                       double *, int *);
typedef void (*mas_fn)(int *, double *, int *, double *, int *);
typedef void (*solout_fn)(int *, double *, double *, double *, double *, int *,
                          int *, double *, int *, int *);

extern void radau5_(int *, deriv_fn, double *, double *, double *, double *,
                    double *, double *, int *, jac_fn, int *, int *, int *,
                    mas_fn, int *, int *, int *, solout_fn, int *, double *,
                    int *, int *, int *, double *, int *, int *);
extern void contr5_(int *, double *, double *, int *, double *);

typedef struct {
    deriv_fn deriv;
    jac_fn jac;
    int n;
    int nt;
    int ntot;
    int it;
    int maxt;
    double *tt;
    double *yout;
    double *ytmp;
} RadauCtx;

static RadauCtx g_ctx;

static void dummy_jac(int *n, double *t, double *y, int *ml, int *mu, double *pd,
                      int *ldpd, double *rpar, int *ipar) {
    (void)n;
    (void)t;
    (void)y;
    (void)ml;
    (void)mu;
    (void)pd;
    (void)ldpd;
    (void)rpar;
    (void)ipar;
}

static void dummy_mas(int *n, double *am, int *lmas, double *rpar, int *ipar) {
    (void)n;
    (void)am;
    (void)lmas;
    (void)rpar;
    (void)ipar;
}

static void solout_dummy(int *nr, double *told, double *t, double *y, double *con,
                         int *lrc, int *neq, double *rpar, int *ipar, int *irtrn) {
    (void)nr;
    (void)told;
    (void)t;
    (void)y;
    (void)con;
    (void)lrc;
    (void)neq;
    (void)rpar;
    (void)ipar;
    *irtrn = 0;
}

static void saveOut(double t, const double *y) {
    int j;
    int stride = g_ctx.ntot + 1;
    int col = g_ctx.it;
    g_ctx.yout[col * stride + 0] = t;
    for (j = 0; j < g_ctx.n; j++) {
        g_ctx.yout[col * stride + 1 + j] = y[j];
    }
}

static void solout_basic(int *nr, double *told, double *t, double *y, double *con,
                         int *lrc, int *neq, double *rpar, int *ipar, int *irtrn) {
    double tmin;
    (void)nr;
    (void)y;
    (void)rpar;
    (void)ipar;
    if (*told == *t) {
        return;
    }
    *irtrn = 0;
    tmin = *t;
    while (g_ctx.it < g_ctx.maxt && *told <= g_ctx.tt[g_ctx.it] && g_ctx.tt[g_ctx.it] < tmin) {
        contr5_(neq, &g_ctx.tt[g_ctx.it], con, lrc, g_ctx.ytmp);
        saveOut(g_ctx.tt[g_ctx.it], g_ctx.ytmp);
        g_ctx.it++;
    }
}

int radau5_integrate(
    int n, int nt, const double *y0, double *times, double *yout, int *istate7,
    double *rstate5, const double *rtol, const double *atol, int itol, double hmax,
    double hini, int maxsteps, const int *nind3, int ijac, int mljac, int mujac,
    int imas, int mlmas, int mumas, deriv_fn deriv, jac_fn jac, int dense_out) {
    int ljac, lmas, le, lrw, liw;
    int iwork[256];
    double rwork[256];
    double *rwork_full = NULL;
    int *iwork_full = NULL;
    double *xytmp = NULL;
    double *ytmp_buf = NULL;
    double *Atol = NULL;
    double *Rtol = NULL;
    double tol_buf[1];
    int itol_local = itol;
    int idid = 0;
    int iout = dense_out ? 2 : 0;
    int j;
    double tin, tout;
    mas_fn mas = dummy_mas;
    jac_fn jac_call = dummy_jac;
    solout_fn solout = dense_out ? solout_basic : solout_dummy;
    int ipar[3] = {0, 0, 0};
    double rpar[1] = {0.0};
    int neq = n;

    if (n <= 0 || nt <= 0 || !y0 || !times || !yout || !istate7 || !deriv) {
        return -999;
    }

    lmas = n;
    if (mljac == n) {
        ljac = n;
        if (imas == 1) {
            lmas = n;
        }
        le = n;
    } else {
        ljac = mljac + mujac + 1;
        lmas = mlmas + mumas + 1;
        le = 2 * mljac + mujac + 1;
    }

    lrw = n * (ljac + lmas + 3 * le + 12) + 20;
    liw = 20 + 3 * n;
    if (lrw < 20 || liw < 20) {
        return -999;
    }

    rwork_full = (double *)calloc((size_t)lrw, sizeof(double));
    iwork_full = (int *)calloc((size_t)liw, sizeof(int));
    xytmp = (double *)malloc((size_t)n * sizeof(double));
    ytmp_buf = (double *)malloc((size_t)n * sizeof(double));
    Atol = (double *)malloc((size_t)n * sizeof(double));
    Rtol = (double *)malloc((size_t)n * sizeof(double));
    if (!rwork_full || !iwork_full || !xytmp || !ytmp_buf || !Atol || !Rtol) {
        idid = -999;
        goto cleanup;
    }

    for (j = 0; j < n; j++) {
        xytmp[j] = y0[j];
    }

    if (itol_local == 0) {
        Atol[0] = atol[0];
        Rtol[0] = rtol[0];
        tol_buf[0] = atol[0];
    } else {
        for (j = 0; j < n; j++) {
            Atol[j] = atol[j];
            Rtol[j] = rtol[j];
        }
    }

    memset(iwork_full, 0, (size_t)liw * sizeof(int));
    memset(rwork_full, 0, (size_t)lrw * sizeof(double));
    iwork_full[1] = maxsteps;
    if (nind3) {
        iwork_full[4] = nind3[0];
        iwork_full[5] = nind3[1];
        iwork_full[6] = nind3[2];
    }
    rwork_full[0] = 1.1102230246251565e-16;
    rwork_full[1] = 0.9;
    rwork_full[2] = 0.001;
    rwork_full[6] = hmax;

    g_ctx.deriv = deriv;
    g_ctx.jac = jac;
    g_ctx.n = n;
    g_ctx.nt = nt;
    g_ctx.ntot = n;
    g_ctx.it = 0;
    g_ctx.maxt = nt;
    g_ctx.tt = times;
    g_ctx.yout = yout;
    g_ctx.ytmp = ytmp_buf;

    if (ijac == 1 && jac) {
        jac_call = jac;
    }

    tin = times[0];
    tout = times[nt - 1];
    if (dense_out) {
        saveOut(tin, xytmp);
        g_ctx.it++;
    }

    do {
        radau5_(&neq, deriv, &tin, xytmp, &tout, &hini, Rtol, Atol, &itol_local,
                jac_call, &ijac, &mljac, &mujac, mas, &imas, &mlmas, &mumas, solout,
                &iout, rwork_full, &lrw, iwork_full, &liw, rpar, ipar, &idid);
    } while (tin < tout && idid >= 0);

    if (dense_out) {
        if (g_ctx.it <= nt - 1) {
            saveOut(tin, xytmp);
        }
    } else {
        g_ctx.it = 0;
        saveOut(tout, xytmp);
    }

    istate7[0] = idid;
    for (j = 0; j < 6; j++) {
        istate7[j + 1] = iwork_full[13 + j];
    }
    rstate5[0] = hini;
    rstate5[1] = tin;

cleanup:
    free(rwork_full);
    free(iwork_full);
    free(xytmp);
    free(ytmp_buf);
    free(Atol);
    free(Rtol);
    return idid;
}
