/* Callbacks stand in for the R math library that mvtnorm's Fortran calls. */

typedef double (*mvn_d)(double);
typedef double (*mvn_id)(int, double);
typedef double (*mvn_v)(void);

static mvn_v cb_unif = 0;
static mvn_d cb_pnorm = 0;
static mvn_d cb_qnorm = 0;
static mvn_id cb_pt = 0;
static mvn_id cb_sqrt_qchisq = 0;

void c_mvn_set_callbacks(mvn_v unif, mvn_d pnorm, mvn_d qnorm, mvn_id pt,
                         mvn_id sqrt_qchisq) {
    cb_unif = unif;
    cb_pnorm = pnorm;
    cb_qnorm = qnorm;
    cb_pt = pt;
    cb_sqrt_qchisq = sqrt_qchisq;
}

double unifrnd_(void) { return cb_unif(); }

double phid_(double *z) { return cb_pnorm(*z); }

double mvphi_(double *z) { return cb_pnorm(*z); }

double mvphnv_(double *p) { return cb_qnorm(*p); }

double studnt_(int *nu, double *t) { return cb_pt(*nu, *t); }

double sqrtqchisqint_(int *n, double *p) { return cb_sqrt_qchisq(*n, *p); }

extern void mvtdst_(int *n, int *nu, double *lower, double *upper, int *infin,
                    double *correl, double *delta, int *maxpts, double *abseps,
                    double *releps, double *error, double *value, int *inform);

extern void tvtlrcall_(int *nu, double *h, double *r, double *epsi, double *tvtl);

extern void bvtlrcall_(int *nu, double *dh, double *dk, double *r, double *bvtl);

void c_mvn_mvtdst(int n, int nu, double *lower, double *upper, int *infin,
                  double *correl, double *delta, int maxpts, double abseps,
                  double releps, double *error, double *value, int *inform) {
    mvtdst_(&n, &nu, lower, upper, infin, correl, delta, &maxpts, &abseps,
            &releps, error, value, inform);
}

void c_mvn_tvtl(int nu, double *h, double *r, double epsi, double *tvtl) {
    tvtlrcall_(&nu, h, r, &epsi, tvtl);
}

void c_mvn_bvtl(int nu, double dh, double dk, double r, double *bvtl) {
    bvtlrcall_(&nu, &dh, &dk, &r, bvtl);
}
