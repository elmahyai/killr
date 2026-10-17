#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

/* MINPACK drivers from minpack.lm 1.2-4. nprint passed to Fortran is 1 so
 * each iteration reports iflag 0; the user's nprint only gates the line. */

#define TRACE_MAX 1025

typedef int (*resid_fn)(const double *par, int n, double *fvec, int m);
typedef int (*jac_fn)(const double *par, int n, double *fjac, int m);

static resid_fn g_resid = NULL;
static jac_fn g_jac = NULL;

void nls_lm_set_callbacks(resid_fn resid, jac_fn jac) {
    g_resid = resid;
    g_jac = jac;
}

typedef struct {
    const double *lower;
    const double *upper;
    int nprint;
    int maxiter;
    int niter;
    double rsstrace[TRACE_MAX];
} OptState;

static OptState g_os;

static void clamp(double *par, int n) {
    int i;
    for (i = 0; i < n; i++) {
        if (par[i] < g_os.lower[i]) {
            par[i] = g_os.lower[i];
        }
        if (par[i] > g_os.upper[i]) {
            par[i] = g_os.upper[i];
        }
    }
}

static void print_iter(const double *par, int n) {
    int i;
    int slot = g_os.niter;
    double rss = 0.0;
    if (slot >= 0 && slot < TRACE_MAX) {
        rss = g_os.rsstrace[slot];
    }
    printf("It. %4d, RSS = %10g, Par. =", slot, rss);
    for (i = 0; i < n; i++) {
        printf(" % 10g", par[i]);
    }
    printf("\n");
    fflush(stdout);
}

static void note_rss(const double *fvec, int m) {
    int i;
    double sumf = 0.0;
    if (g_os.niter < 0 || g_os.niter >= TRACE_MAX) {
        return;
    }
    for (i = 0; i < m; i++) {
        sumf += fvec[i] * fvec[i];
    }
    g_os.rsstrace[g_os.niter] = sumf;
}

void fcn_lmdif(int *m, int *n, double *par, double *fvec, int *iflag) {
    clamp(par, *n);
    if (*iflag == 0) {
        if (g_os.nprint > 0) {
            print_iter(par, *n);
        }
        g_os.niter++;
    } else if (*iflag == 1 || *iflag == 2) {
        if (g_resid == NULL || g_resid(par, *n, fvec, *m) != 0) {
            *iflag = -1;
        } else {
            note_rss(fvec, *m);
        }
    }
    if (g_os.niter == g_os.maxiter) {
        *iflag = -1;
    }
}

void fcn_lmder(int *m, int *n, double *par, double *fvec, double *fjac, int *ldfjac, int *iflag) {
    (void)ldfjac;
    clamp(par, *n);
    if (*iflag == 0) {
        if (g_os.nprint > 0) {
            print_iter(par, *n);
        }
        g_os.niter++;
    } else if (*iflag == 1) {
        if (g_resid == NULL || g_resid(par, *n, fvec, *m) != 0) {
            *iflag = -1;
        } else {
            note_rss(fvec, *m);
        }
    } else if (*iflag == 2) {
        if (g_jac == NULL || g_jac(par, *n, fjac, *m) != 0) {
            *iflag = -1;
        }
    }
    if (g_os.niter == g_os.maxiter) {
        *iflag = -1;
    }
}

extern void lmdif_(
    void (*fcn)(int *, int *, double *, double *, int *),
    int *m,
    int *n,
    double *x,
    double *fvec,
    double *ftol,
    double *xtol,
    double *gtol,
    int *maxfev,
    double *epsfcn,
    double *diag,
    int *mode,
    double *factor,
    int *nprint,
    int *info,
    int *nfev,
    double *fjac,
    int *ldfjac,
    int *ipvt,
    double *qtf,
    double *wa1,
    double *wa2,
    double *wa3,
    double *wa4
);

extern void lmder_(
    void (*fcn)(int *, int *, double *, double *, double *, int *, int *),
    int *m,
    int *n,
    double *x,
    double *fvec,
    double *fjac,
    int *ldfjac,
    double *ftol,
    double *xtol,
    double *gtol,
    int *maxfev,
    double *diag,
    int *mode,
    double *factor,
    int *nprint,
    int *info,
    int *nfev,
    int *njev,
    int *ipvt,
    double *qtf,
    double *wa1,
    double *wa2,
    double *wa3,
    double *wa4
);

static void fcn_message(char *msg, int info, int maxfev, int maxiter) {
    if (info == 1) {
        snprintf(msg, 256, "Relative error in the sum of squares is at most `ftol'.");
    } else if (info == 2) {
        snprintf(msg, 256, "Relative error between `par' and the solution is at most `ptol'.");
    } else if (info == 3) {
        snprintf(msg, 256, "Conditions for `info = 1' and `info = 2' both hold.");
    } else if (info == 4) {
        snprintf(
            msg,
            256,
            "The cosine of the angle between `fvec' and any column of the Jacobian is at most `gtol' in absolute value."
        );
    } else if (info == 5) {
        snprintf(msg, 256, "Number of calls to `fcn' has reached or exceeded `maxfev' == %d.", maxfev);
    } else if (info == 6) {
        snprintf(msg, 256, "`ftol' is too small. No further reduction in the sum of squares is possible.");
    } else if (info == 7) {
        snprintf(msg, 256, "`ptol' is too small. No further improvement in the approximate solution `par' is possible.");
    } else if (info == 8) {
        snprintf(msg, 256, "`gtol' is too small. `fvec' is orthogonal to the columns of the Jacobian to machine precision.");
    } else if (info < 0) {
        snprintf(msg, 256, "Number of iterations has reached `maxiter' == %d.", maxiter);
    } else if (info == 0) {
        snprintf(msg, 256, "Improper input parameters.");
    } else {
        msg[0] = '\0';
    }
}

static void transpose(const double *x, int nrx, int ncx, double *y) {
    int i, j;
    for (i = 0; i < ncx; i++) {
        for (j = 0; j < nrx; j++) {
            y[j * ncx + i] = x[i * nrx + j];
        }
    }
}

static void matprod(const double *x, int nrx, int ncx, const double *y, int nry, int ncy, double *z) {
    int i, j, k;
    for (i = 0; i < nrx * ncy; i++) {
        z[i] = 0.0;
    }
    if (nrx <= 0 || ncx <= 0 || nry <= 0 || ncy <= 0) {
        return;
    }
    for (k = 0; k < ncy; k++) {
        for (j = 0; j < ncx; j++) {
            double yjk = y[j + k * nry];
            for (i = 0; i < nrx; i++) {
                z[i + k * nrx] += x[i + j * nrx] * yjk;
            }
        }
    }
}

static void crossprod(const double *x, int nrx, int ncx, const double *y, int nry, int ncy, double *z) {
    int i, j, k;
    for (i = 0; i < ncx * ncy; i++) {
        z[i] = 0.0;
    }
    if (nrx <= 0 || ncx <= 0 || nry <= 0 || ncy <= 0) {
        return;
    }
    for (k = 0; k < ncy; k++) {
        for (i = 0; i < ncx; i++) {
            double sum = 0.0;
            for (j = 0; j < nrx; j++) {
                sum += x[j + i * nrx] * y[j + k * nry];
            }
            z[i + k * ncx] = sum;
        }
    }
}

static void hessian_from_qr(const double *fjac, int ldfjac, const int *ipvt, int n, double *hess) {
    int i, j;
    double *perm = (double *)calloc((size_t)n * (size_t)n, sizeof(double));
    double *perm_t = (double *)calloc((size_t)n * (size_t)n, sizeof(double));
    double *r = (double *)calloc((size_t)n * (size_t)n, sizeof(double));
    double *r2 = (double *)calloc((size_t)n * (size_t)n, sizeof(double));
    double *r2_x_perm_t = (double *)calloc((size_t)n * (size_t)n, sizeof(double));
    if (perm == NULL || perm_t == NULL || r == NULL || r2 == NULL || r2_x_perm_t == NULL) {
        free(perm);
        free(perm_t);
        free(r);
        free(r2);
        free(r2_x_perm_t);
        return;
    }
    for (j = 0; j < n; j++) {
        for (i = 0; i < n; i++) {
            perm[j * n + i] = (i + 1 == ipvt[j]) ? 1.0 : 0.0;
            r[j * n + i] = (i <= j) ? fjac[j * ldfjac + i] : 0.0;
        }
    }
    transpose(perm, n, n, perm_t);
    crossprod(r, n, n, r, n, n, r2);
    matprod(r2, n, n, perm_t, n, n, r2_x_perm_t);
    matprod(perm, n, n, r2_x_perm_t, n, n, hess);
    free(perm);
    free(perm_t);
    free(r);
    free(r2);
    free(r2_x_perm_t);
}

int nls_lm_solve(
    double *par,
    const double *lower,
    const double *upper,
    int n,
    int m,
    double ftol,
    double ptol,
    double gtol,
    double epsfcn,
    double factor,
    int maxfev,
    int maxiter,
    int nprint,
    int mode,
    double *diag,
    double *fvec,
    double *hessian,
    double *rsstrace,
    int *rsstrace_len,
    int *info,
    int *niter,
    char *message,
    int has_jac
) {
    int i;
    int ldfjac = m;
    int nfev = 0;
    int njev = 0;
    int npr = 1;
    int info_local = 0;
    double *fjac = NULL;
    double *qtf = NULL;
    double *wa1 = NULL;
    double *wa2 = NULL;
    double *wa3 = NULL;
    double *wa4 = NULL;
    int *ipvt = NULL;

    if (n <= 0 || m <= 0 || par == NULL || lower == NULL || upper == NULL || diag == NULL) {
        return 1;
    }
    fjac = (double *)calloc((size_t)ldfjac * (size_t)n, sizeof(double));
    qtf = (double *)calloc((size_t)n, sizeof(double));
    wa1 = (double *)calloc((size_t)n, sizeof(double));
    wa2 = (double *)calloc((size_t)n, sizeof(double));
    wa3 = (double *)calloc((size_t)n, sizeof(double));
    wa4 = (double *)calloc((size_t)m, sizeof(double));
    ipvt = (int *)calloc((size_t)n, sizeof(int));
    if (fjac == NULL || qtf == NULL || wa1 == NULL || wa2 == NULL || wa3 == NULL || wa4 == NULL || ipvt == NULL) {
        free(fjac);
        free(qtf);
        free(wa1);
        free(wa2);
        free(wa3);
        free(wa4);
        free(ipvt);
        return 2;
    }
    memset(&g_os, 0, sizeof(g_os));
    g_os.lower = lower;
    g_os.upper = upper;
    g_os.nprint = nprint > 0 ? 1 : 0;
    g_os.maxiter = maxiter;
    g_os.niter = 0;

    if (has_jac) {
        lmder_(
            fcn_lmder,
            &m,
            &n,
            par,
            fvec,
            fjac,
            &ldfjac,
            &ftol,
            &ptol,
            &gtol,
            &maxfev,
            diag,
            &mode,
            &factor,
            &npr,
            &info_local,
            &nfev,
            &njev,
            ipvt,
            qtf,
            wa1,
            wa2,
            wa3,
            wa4
        );
    } else {
        lmdif_(
            fcn_lmdif,
            &m,
            &n,
            par,
            fvec,
            &ftol,
            &ptol,
            &gtol,
            &maxfev,
            &epsfcn,
            diag,
            &mode,
            &factor,
            &npr,
            &info_local,
            &nfev,
            fjac,
            &ldfjac,
            ipvt,
            qtf,
            wa1,
            wa2,
            wa3,
            wa4
        );
    }

    hessian_from_qr(fjac, ldfjac, ipvt, n, hessian);
    fcn_message(message, info_local, maxfev, g_os.maxiter);
    *info = info_local;
    *niter = g_os.niter - 1;
    *rsstrace_len = g_os.niter;
    if (*rsstrace_len < 0) {
        *rsstrace_len = 0;
    }
    if (*rsstrace_len > TRACE_MAX) {
        *rsstrace_len = TRACE_MAX;
    }
    for (i = 0; i < *rsstrace_len; i++) {
        rsstrace[i] = g_os.rsstrace[i];
    }

    free(fjac);
    free(qtf);
    free(wa1);
    free(wa2);
    free(wa3);
    free(wa4);
    free(ipvt);
    return 0;
}
