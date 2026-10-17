/*
 * Implementations of the R API pieces used by the vendored ordinal kernels.
 *
 * Normal, logistic and Cauchy functions follow R's formulas, computed with
 * libm (erfc, atan, exp). They agree with R's Rmath to about 1e-15 relative,
 * far inside the 1e-8 check. pgamma is not used by the random-effect kernels
 * (only the Aranda-Ordaz and log-gamma links need it), so it reports an error
 * and returns NaN instead of implementing the incomplete gamma function.
 */
#include <stdarg.h>
#include <stdio.h>
#include <math.h>
#include "R.h"

double R_pow(double x, double y)
{
    if (x == 1. || y == 0.)
        return 1.;
    if (x == 0.) {
        if (y > 0.) return 0.;
        else if (y < 0.) return INFINITY;
        else return y; /* NaN */
    }
    return pow(x, y);
}

double R_pow_di(double x, int n)
{
    /* R 4.5 arithmetic.c: repeated squaring of x, then the reciprocal for n < 0. */
    double xn = 1.0;
    if (isnan(x)) return x;
    if (n != 0) {
        int is_neg;
        if (!isfinite(x)) return R_pow(x, (double) n);
        is_neg = (n < 0);
        if (is_neg) n = -n;
        for (;;) {
            if (n & 01) xn *= x;
            if (n >>= 1) x *= x;
            else break;
        }
        if (is_neg) xn = 1. / xn;
    }
    return xn;
}

void Rprintf(const char *fmt, ...)
{
    va_list ap;
    va_start(ap, fmt);
    vprintf(fmt, ap);
    va_end(ap);
}

void error(const char *fmt, ...)
{
    va_list ap;
    va_start(ap, fmt);
    fprintf(stderr, "ordinal_clmm: ");
    vfprintf(stderr, fmt, ap);
    va_end(ap);
}

double dnorm(double x, double mu, double sigma, int give_log)
{
    double z = (x - mu) / sigma;
    if (give_log)
        return -(0.918938533204672741780329736406 + 0.5 * z * z + log(sigma));
    return 0.398942280401432677939946059934 * exp(-0.5 * z * z) / sigma;
}

double pnorm(double x, double mu, double sigma, int lower_tail, int log_p)
{
    double z = (x - mu) / sigma;
    double p = lower_tail ? 0.5 * erfc(-z / M_SQRT2) : 0.5 * erfc(z / M_SQRT2);
    return log_p ? log(p) : p;
}

double dlogis(double x, double loc, double scale, int give_log)
{
    /* R's dlogis(): e / (scale * f * f) with x = |z|. */
    double z = fabs((x - loc) / scale);
    double e = exp(-z);
    double f = 1.0 + e;
    return give_log ? -(z + log(scale * f * f)) : e / (scale * f * f);
}

double plogis(double x, double loc, double scale, int lower_tail, int log_p)
{
    /* Same expression as R's plogis() for log_p = 0: 1 / (1 + exp(-x)) in the lower tail. */
    double z = (x - loc) / scale;
    double p = 1 / (1 + exp(lower_tail ? -z : z));
    return log_p ? log(p) : p;
}

double dcauchy(double x, double loc, double scale, int give_log)
{
    double z = (x - loc) / scale;
    double d = 1.0 / (M_PI * scale * (1.0 + z * z));
    return give_log ? log(d) : d;
}

double pcauchy(double x, double loc, double scale, int lower_tail, int log_p)
{
    double z = (x - loc) / scale;
    double p;
    if (fabs(z) > 1.0) {
        double y = atan(1.0 / z) / M_PI;
        if (z > 0) p = lower_tail ? 1.0 - y : y;
        else p = lower_tail ? -y : 1.0 + y;
    } else {
        double y = atan(z) / M_PI;
        p = lower_tail ? 0.5 + y : 0.5 - y;
    }
    return log_p ? log(p) : p;
}

double pgamma(double x, double alph, double scale, int lower_tail, int log_p)
{
    (void) x; (void) alph; (void) scale; (void) lower_tail; (void) log_p;
    error("pgamma is not available in the ordinal_clmm shim\n");
    return NAN;
}

double lgammafn(double x)
{
    return lgamma(x);
}

/* R's sum(log(x)): each log() in double, accumulated in long double as R's rsum() does. */
double ordinal_sum_log(const double *x, int n)
{
    long double s = 0.0L;
    int i;
    for (i = 0; i < n; i++)
        s += log(x[i]);
    return (double) s;
}
