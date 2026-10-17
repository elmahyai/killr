/* GARCH estimation from tseries src/garch.c (Adrian Trapletti), without R. */

#include <math.h>
#include <stdlib.h>
#include <stdio.h>

extern void dsumsl_(int *n, double *d, double *x,
                    void (*calcf)(int *, double *, int *, double *, int *, double *, void (*)(void)),
                    void (*calcg)(int *, double *, int *, double *, int *, double *, void (*)(void)),
                    int *iv, int *liv, int *lv, double *v, int *uiparm, double *urparm,
                    void (*ufparm)(void));
extern void dsmsno_(int *n, double *d, double *x,
                    void (*calcf)(int *, double *, int *, double *, int *, double *, void (*)(void)),
                    int *iv, int *liv, int *lv, double *v, int *uiparm, double *urparm,
                    void (*ufparm)(void));
extern void ddeflt_(int *alg, int *iv, int *liv, int *lv, double *v);

#define BIG 1.0e+10

static double dsqrarg;
#define DSQR(a) ((dsqrarg = (a)) == 0.0 ? 0.0 : dsqrarg * dsqrarg)

static double dmaxarg1, dmaxarg2;
#define DMAX(a, b)                                                                               \
    (dmaxarg1 = (a), dmaxarg2 = (b), (dmaxarg1) > (dmaxarg2) ? (dmaxarg1) : (dmaxarg2))

struct garch_handler {
    double *y;
    double *h;
    double *dh;
    int n;
    int p, q;
};

static struct garch_handler garch_h;

static void calcf_(int *pq, double *p, int *nf, double *f, int *uiparm, double *urparm,
                   void (*ufparm)(void)) {
    int i, j, ok;
    int maxpq = (int)DMAX(garch_h.p, garch_h.q);
    double temp = 0.0;
    double sum = 0.0;

    (void)nf;
    (void)uiparm;
    (void)urparm;
    (void)ufparm;

    ok = 1;
    if (p[0] <= 0.0)
        ok = 0;
    for (i = 1; i < (*pq); i++)
        if (p[i] < 0.0)
            ok = 0;
    if (ok) {
        for (i = maxpq; i < garch_h.n; i++) {
            temp = p[0];
            for (j = 1; j <= garch_h.q; j++)
                temp += p[j] * DSQR(garch_h.y[i - j]);
            for (j = 1; j <= garch_h.p; j++)
                temp += p[garch_h.q + j] * garch_h.h[i - j];
            sum += log(temp) + DSQR(garch_h.y[i]) / temp;
            garch_h.h[i] = temp;
        }
        (*f) = 0.5 * sum;
    } else {
        (*f) = BIG;
    }
}

static void calcg_(int *pq, double *p, int *nf, double *dp, int *uiparm, double *urparm,
                   void (*ufparm)(void)) {
    int i, j, k;
    int maxpq = (int)DMAX(garch_h.p, garch_h.q);
    double temp1, temp2, temp3;

    (void)nf;
    (void)uiparm;
    (void)urparm;
    (void)ufparm;

    for (k = 0; k < (*pq); k++)
        dp[k] = 0.0;
    for (i = maxpq; i < garch_h.n; i++) {
        temp1 = p[0];
        for (j = 1; j <= garch_h.q; j++)
            temp1 += p[j] * DSQR(garch_h.y[i - j]);
        for (j = 1; j <= garch_h.p; j++)
            temp1 += p[garch_h.q + j] * garch_h.h[i - j];
        garch_h.h[i] = temp1;
        temp2 = 0.5 * (1.0 - DSQR(garch_h.y[i]) / temp1) / temp1;
        temp3 = 1.0;
        for (j = 1; j <= garch_h.p; j++)
            temp3 += p[garch_h.q + j] * garch_h.dh[(*pq) * (i - j)];
        garch_h.dh[(*pq) * i] = temp3;
        dp[0] += temp2 * temp3;
        for (k = 1; k <= garch_h.q; k++) {
            temp3 = DSQR(garch_h.y[i - k]);
            for (j = 1; j <= garch_h.p; j++)
                temp3 += p[garch_h.q + j] * garch_h.dh[(*pq) * (i - j) + k];
            garch_h.dh[(*pq) * i + k] = temp3;
            dp[k] += temp2 * temp3;
        }
        for (k = 1; k <= garch_h.p; k++) {
            temp3 = garch_h.h[i - k];
            for (j = 1; j <= garch_h.p; j++)
                temp3 += p[garch_h.q + j] * garch_h.dh[(*pq) * (i - j) + garch_h.q + k];
            garch_h.dh[(*pq) * i + garch_h.q + k] = temp3;
            dp[garch_h.q + k] += temp2 * temp3;
        }
    }
}

static void ufparm_(void) {
    fprintf(stderr, "fatal error in fit_garch ()\n");
    abort();
}

void tseries_fit_garch(double *y, int *n, double *par, int *p, int *q, int *itmax, double *afctol,
                       double *rfctol, double *xctol, double *xftol, double *fret, int *agrad,
                       int *trace) {
    int i, j, pq, liv, lv, alg;
    double *d, *v;
    int *iv;
    double var;

    pq = (*p) + (*q) + 1;
    d = (double *)calloc((size_t)pq, sizeof(double));
    for (i = 0; i < pq; i++)
        d[i] = 1.0;
    liv = 60;
    iv = (int *)calloc((size_t)liv, sizeof(int));
    lv = 77 + pq * (pq + 17) / 2;
    v = (double *)calloc((size_t)lv, sizeof(double));
    alg = 2;
    ddeflt_(&alg, iv, &liv, &lv, v);
    iv[0] = 12;

    iv[16] = 2 * (*itmax);
    iv[17] = (*itmax);
    if (*trace)
        iv[20] = 6;
    else
        iv[20] = 0;
    v[30] = (*afctol);
    v[31] = (*rfctol);
    v[32] = (*xctol);
    v[33] = (*xftol);

    garch_h.p = (*p);
    garch_h.q = (*q);
    garch_h.n = (*n);
    garch_h.y = y;
    garch_h.h = (double *)calloc((size_t)(*n), sizeof(double));
    garch_h.dh = (double *)calloc((size_t)(*n) * (size_t)pq, sizeof(double));
    var = 0.0;
    for (i = 0; i < (*n); i++)
        var += DSQR(y[i]);
    var /= (double)(*n);
    for (i = 0; i < (int)DMAX((*p), (*q)); i++) {
        garch_h.h[i] = var;
        garch_h.dh[pq * i] = 1.0;
        for (j = 1; j < pq; j++)
            garch_h.dh[pq * i + j] = 0.0;
    }

    if (*agrad) {
        dsumsl_(&pq, d, par, calcf_, calcg_, iv, &liv, &lv, v, NULL, NULL, ufparm_);
    } else {
        dsmsno_(&pq, d, par, calcf_, iv, &liv, &lv, v, NULL, NULL, ufparm_);
    }

    (*fret) = v[9];

    free(d);
    free(iv);
    free(v);
    free(garch_h.h);
    free(garch_h.dh);
}

void tseries_pred_garch(double *y, double *h, int *n, double *par, int *p, int *q, int *genuine) {
    double var, temp;
    int i, j, maxpq, N;

    if (*genuine)
        N = (*n) + 1;
    else
        N = (*n);
    maxpq = (int)DMAX((*p), (*q));
    var = 0.0;
    for (i = 1; i <= (*p) + (*q); i++)
        var += par[i];
    var = par[0] / (1.0 - var);
    for (i = 0; i < maxpq; i++)
        h[i] = var;
    for (i = maxpq; i < N; i++) {
        temp = par[0];
        for (j = 1; j <= (*q); j++)
            temp += par[j] * DSQR(y[i - j]);
        for (j = 1; j <= (*p); j++)
            temp += par[(*q) + j] * h[i - j];
        h[i] = temp;
    }
}

void tseries_ophess_garch(double *y, int *n, double *par, double *he, int *p, int *q) {
    double var, temp1, temp2, temp3;
    int i, j, k, pq;
    double *h, *dh, *dpar;

    pq = (*p) + (*q) + 1;
    h = (double *)calloc((size_t)(*n), sizeof(double));
    dh = (double *)calloc((size_t)(*n) * (size_t)pq, sizeof(double));
    dpar = (double *)calloc((size_t)pq, sizeof(double));
    var = 0.0;
    for (i = 0; i < (*n); i++)
        var += DSQR(y[i]);
    var /= (double)(*n);
    for (i = 0; i < (int)DMAX((*p), (*q)); i++) {
        h[i] = var;
        dh[pq * i] = 1.0;
        for (j = 1; j < pq; j++)
            dh[pq * i + j] = 0.0;
    }
    for (k = 0; k < pq; k++)
        for (j = 0; j < pq; j++)
            he[pq * k + j] = 0.0;
    for (i = (int)DMAX((*p), (*q)); i < (*n); i++) {
        temp1 = par[0];
        for (j = 1; j <= (*q); j++)
            temp1 += par[j] * DSQR(y[i - j]);
        for (j = 1; j <= (*p); j++)
            temp1 += par[(*q) + j] * h[i - j];
        h[i] = temp1;
        temp2 = 0.5 * (1.0 - DSQR(y[i]) / temp1) / temp1;
        temp3 = 1.0;
        for (j = 1; j <= (*p); j++)
            temp3 += par[(*q) + j] * dh[pq * (i - j)];
        dh[pq * i] = temp3;
        dpar[0] = temp2 * temp3;
        for (k = 1; k <= (*q); k++) {
            temp3 = DSQR(y[i - k]);
            for (j = 1; j <= (*p); j++)
                temp3 += par[(*q) + j] * dh[pq * (i - j) + k];
            dh[pq * i + k] = temp3;
            dpar[k] = temp2 * temp3;
        }
        for (k = 1; k <= (*p); k++) {
            temp3 = h[i - k];
            for (j = 1; j <= (*p); j++)
                temp3 += par[(*q) + j] * dh[pq * (i - j) + (*q) + k];
            dh[pq * i + (*q) + k] = temp3;
            dpar[(*q) + k] = temp2 * temp3;
        }
        for (k = 0; k < pq; k++)
            for (j = 0; j < pq; j++)
                he[pq * k + j] += dpar[k] * dpar[j];
    }
    free(h);
    free(dh);
    free(dpar);
}
