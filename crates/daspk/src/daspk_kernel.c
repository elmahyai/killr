/* DDASPK driver adapted from deSolve src/call_daspk.c (R-function path only). */

#include <stddef.h>
#include <stdlib.h>
#include <string.h>

typedef void (*res_fn)(double *, double *, double *, double *, double *, int *,
                       double *, int *);
typedef void (*jac_fn)(double *, double *, double *, double *, double *, double *,
                       int *);

extern void ddaspk_(res_fn res, int *neq, double *t, double *y, double *yprime,
                    double *tout, int *info, double *rtol, double *atol, int *idid,
                    double *rwork, int *lrw, int *iwork, int *liw, double *rpar,
                    int *ipar, jac_fn jac, void (*psol)(void));

typedef struct {
    res_fn res;
    jac_fn jac;
    int n;
    int nt;
    int out_row;
    double *yout;
} DaspkCtx;

static DaspkCtx g_ctx;

static void dummy_psol(void) {}

static void c_res(double *t, double *y, double *yprime, double *cj, double *delta,
                  int *ires, double *rpar, int *ipar) {
    (void)rpar;
    (void)ipar;
    *ires = 0;
    if (g_ctx.res) {
        g_ctx.res(t, y, yprime, cj, delta, ires, rpar, ipar);
    }
}

static void c_jac(double *t, double *y, double *yprime, double *pd, double *cj,
                  double *rpar, int *ipar) {
    (void)rpar;
    (void)ipar;
    if (g_ctx.jac) {
        g_ctx.jac(t, y, yprime, pd, cj, rpar, ipar);
    }
}

int daspk_integrate(int n, int nt, double *y, double *yprime, double *times,
                    double *yout, int *istate23, double *rstate3, int *info25,
                    int *iwork, int liw, double *rwork, int lrw, double *rtol,
                    int lrtol, double *atol, int latol, int maxit, jac_fn jac) {
    int idid = 1;
    int it;
    int repcount;
    int j;
    int ny = n;
    int ntot = n;
    int stride = ntot + 1;
    double tin, tout;
    double *xytmp = NULL;
    double *xdytmp = NULL;
    double *Atol = NULL;
    double *Rtol = NULL;
    int *Info = NULL;
    int ninfo = 25;
    int ipar[1] = {0};
    double rpar[1] = {0.0};
    jac_fn jac_call = NULL;

    if (n <= 0 || nt <= 0 || !y || !yprime || !times || !yout || !info25) {
        return -999;
    }

    xytmp = (double *)malloc((size_t)n * sizeof(double));
    xdytmp = (double *)malloc((size_t)n * sizeof(double));
    Atol = (double *)malloc((size_t)latol * sizeof(double));
    Rtol = (double *)malloc((size_t)lrtol * sizeof(double));
    Info = (int *)malloc((size_t)ninfo * sizeof(int));
    if (!xytmp || !xdytmp || !Atol || !Rtol || !Info) {
        idid = -999;
        goto cleanup;
    }

    for (j = 0; j < n; j++) {
        xytmp[j] = y[j];
        xdytmp[j] = yprime[j];
    }
    for (j = 0; j < latol; j++) {
        Atol[j] = atol[j];
    }
    for (j = 0; j < lrtol; j++) {
        Rtol[j] = rtol[j];
    }
    for (j = 0; j < ninfo; j++) {
        Info[j] = info25[j];
    }

    g_ctx.n = n;
    g_ctx.nt = nt;
    g_ctx.out_row = 0;
    g_ctx.yout = yout;
    g_ctx.jac = jac;

    yout[0] = times[0];
    for (j = 0; j < n; j++) {
        yout[j + 1] = y[j];
    }
    g_ctx.out_row = 1;

    jac_call = (Info[4] == 1 && jac) ? c_jac : NULL;

    for (it = 0; it < nt - 1; it++) {
        tin = times[it];
        tout = times[it + 1];
        repcount = 0;
        do {
            ddaspk_(c_res, &ny, &tin, xytmp, xdytmp, &tout, Info, Rtol, Atol, &idid,
                    rwork, &lrw, iwork, &liw, rpar, ipar, jac_call, dummy_psol);
            repcount++;
            if (idid == -1) {
                Info[0] = 1;
            } else if (idid < 0 && idid != -1) {
                repcount = maxit + 2;
            }
        } while (tin < tout && repcount < maxit);

        yout[(it + 1) * stride + 0] = tin;
        for (j = 0; j < n; j++) {
            yout[(it + 1) * stride + 1 + j] = xytmp[j];
        }

        if (repcount > maxit || tin < tout || idid <= 0) {
            idid = 0;
            goto finish;
        }
    }

finish:
    if (istate23) {
        istate23[0] = idid;
        for (j = 0; j < 22; j++) {
            istate23[j + 1] = iwork[j];
        }
    }
    if (rstate3) {
        rstate3[0] = rwork[1];
        rstate3[1] = rwork[2];
        rstate3[2] = rwork[3];
    }

cleanup:
    free(Info);
    free(Rtol);
    free(Atol);
    free(xdytmp);
    free(xytmp);
    g_ctx.res = NULL;
    g_ctx.jac = NULL;
    return idid;
}

void daspk_set_res(res_fn res) { g_ctx.res = res; }
