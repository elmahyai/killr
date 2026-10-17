/* DLSODES driver adapted from deSolve src/call_lsoda.c (solver 3, R path only). */

#include <stddef.h>
#include <stdlib.h>
#include <string.h>

typedef void (*lsodes_deriv_fn)(int *neq, double *t, double *y, double *ydot, double *rpar,
                                int *ipar);
typedef void (*lsodes_jacvec_fn)(int *neq, double *t, double *y, int *j, int *ian, int *jan,
                                 double *pdj, double *rpar, int *ipar);

extern void dlsodes_(
    lsodes_deriv_fn f,
    int *neq,
    double *y,
    double *t,
    double *tout,
    int *itol,
    double *rtol,
    double *atol,
    int *itask,
    int *istate,
    int *iopt,
    double *rwork,
    int *lrw,
    int *iwork,
    int *liw,
    int *iwk,
    lsodes_jacvec_fn jac,
    int *mf,
    double *rpar,
    int *ipar);

typedef struct {
    lsodes_deriv_fn deriv;
    lsodes_jacvec_fn jacvec;
} LsodesCtx;

static LsodesCtx g_ctx;

void lsodes_set_callbacks(lsodes_deriv_fn deriv, lsodes_jacvec_fn jacvec) {
    g_ctx.deriv = deriv;
    g_ctx.jacvec = jacvec;
}

static void c_deriv(int *neq, double *t, double *y, double *ydot, double *rpar, int *ipar) {
    if (g_ctx.deriv) {
        g_ctx.deriv(neq, t, y, ydot, rpar, ipar);
    }
}

static void c_jacvec(int *neq, double *t, double *y, int *j, int *ian, int *jan, double *pdj,
                     double *rpar, int *ipar) {
    (void)ian;
    (void)jan;
    if (g_ctx.jacvec) {
        g_ctx.jacvec(neq, t, y, j, ian, jan, pdj, rpar, ipar);
    }
}

int lsodes_integrate(
    int n,
    int nt,
    double *y,
    double *times,
    double *yout,
    int *istate21,
    double *rstate5,
    int imp,
    int maxord,
    int maxsteps,
    int nnz,
    int liw_hint,
    int lrw_hint,
    double hini,
    double hmax,
    double hmin,
    double tcrit,
    int has_tcrit,
    double *rtol,
    int lrtol,
    double *atol,
    int latol,
    int *iwork_in,
    int liw,
    lsodes_deriv_fn deriv,
    lsodes_jacvec_fn jacvec) {
    int itol;
    int itask;
    int istate;
    int iopt;
    int jt;
    int ipar[1] = {0};
    double rpar[1] = {0.0};
    int moss;
    int meth;
    int miter;
    int lenr = 2;
    int lrw;
    int i;
    int it;
    int repcount;
    int maxit = 10;
    double tin;
    double tout;
    double *xytmp = NULL;
    double *Atol = NULL;
    double *Rtol = NULL;
    int *iwork = NULL;
    double *rwork = NULL;
    int *iwk = NULL;

    if (n <= 0 || nt <= 0 || !y || !times || !yout) {
        return -999;
    }

    moss = imp / 100;
    meth = (imp % 100) / 10;
    miter = imp % 10;
    (void)meth;

    if (lrw_hint > 0) {
        lrw = lrw_hint;
    } else {
        lrw = 20 + n * (maxord + 1) + 3 * n + 20;
        if (miter == 1) {
            lrw += 2 * nnz + 2 * n + (nnz + 9 * n) / lenr;
        }
        if (miter == 2) {
            lrw += 2 * nnz + 2 * n + (nnz + 10 * n) / lenr;
        }
        if (miter == 3) {
            lrw += n + 2;
        }
    }
    if (lrw < 20) {
        lrw = 20;
    }

    if (liw_hint > liw) {
        liw = liw_hint;
    }
    if (moss == 0 && (miter == 1 || miter == 2)) {
        if (liw < 31 + n + nnz + 30) {
            liw = 31 + n + nnz + 30;
        }
    } else if (liw < 30) {
        liw = 30;
    }

    xytmp = (double *)malloc((size_t)n * sizeof(double));
    Atol = (double *)malloc((size_t)latol * sizeof(double));
    Rtol = (double *)malloc((size_t)lrtol * sizeof(double));
    iwork = (int *)malloc((size_t)liw * sizeof(int));
    rwork = (double *)malloc((size_t)lrw * sizeof(double));
    if (!xytmp || !Atol || !Rtol || !iwork || !rwork) {
        istate = -999;
        goto cleanup;
    }
    iwk = (int *)rwork;

    for (i = 0; i < n; i++) {
        xytmp[i] = y[i];
    }
    for (i = 0; i < latol; i++) {
        Atol[i] = atol[i];
    }
    for (i = 0; i < lrtol; i++) {
        Rtol[i] = rtol[i];
    }
    memset(iwork, 0, (size_t)liw * sizeof(int));
    if (iwork_in) {
        int copy = liw;
        if (copy > liw) {
            copy = liw;
        }
        memcpy(iwork, iwork_in, (size_t)copy * sizeof(int));
    }
    memset(rwork, 0, (size_t)lrw * sizeof(double));

    iwork[4] = maxord;
    iwork[5] = maxsteps;
    if (has_tcrit) {
        rwork[0] = tcrit;
    }
    rwork[4] = hini;
    rwork[5] = hmax;
    rwork[6] = hmin;

    if (latol == 1 && lrtol == 1) {
        itol = 1;
    } else if (latol > 1 && lrtol == 1) {
        itol = 2;
    } else if (latol == 1 && lrtol > 1) {
        itol = 3;
    } else {
        itol = 4;
    }

    itask = has_tcrit ? 4 : 1;
    istate = 1;
    iopt = 0;
    if (hini > 0.0 || hmax > 0.0 || hmin > 0.0 || has_tcrit) {
        iopt = 1;
    }
    for (i = 4; i < 7; i++) {
        if (rwork[i] != 0.0) {
            iopt = 1;
        }
    }
    for (i = 4; i < 9; i++) {
        if (iwork[i] != 0) {
            iopt = 1;
        }
    }

    jt = imp;
    g_ctx.deriv = deriv;
    g_ctx.jacvec = jacvec;

    yout[0] = times[0];
    for (i = 0; i < n; i++) {
        yout[i + 1] = y[i];
    }

    for (it = 0; it < nt - 1; it++) {
        tin = times[it];
        tout = times[it + 1];
        repcount = 0;
        do {
            dlsodes_(c_deriv, &n, xytmp, &tin, &tout, &itol, Rtol, Atol, &itask, &istate, &iopt,
                     rwork, &lrw, iwork, &liw, iwk, jacvec ? c_jacvec : NULL, &jt, rpar, ipar);
            if (istate == -2) {
                for (i = 0; i < lrtol; i++) {
                    Rtol[i] *= 10.0;
                }
                for (i = 0; i < latol; i++) {
                    Atol[i] *= 10.0;
                }
                istate = 3;
            }
            repcount++;
            if (istate < 0 && istate != -1) {
                break;
            }
        } while (tin < tout && istate >= 0 && repcount < maxit);

        yout[(it + 1) * (n + 1) + 0] = tin;
        for (i = 0; i < n; i++) {
            yout[(it + 1) * (n + 1) + 1 + i] = xytmp[i];
        }
        if (istate < 0 || tin < tout) {
            break;
        }
    }

    if (istate21) {
        istate21[0] = istate;
        for (i = 0; i < 20; i++) {
            istate21[i + 1] = iwork[i];
        }
    }
    if (rstate5) {
        for (i = 0; i < 5; i++) {
            rstate5[i] = rwork[10 + i];
        }
    }

cleanup:
    free(xytmp);
    free(Atol);
    free(Rtol);
    free(iwork);
    free(rwork);
    g_ctx.deriv = NULL;
    g_ctx.jacvec = NULL;
    return istate;
}
