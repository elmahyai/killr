#ifndef MVTNORM_STUB_RMATH_H
#define MVTNORM_STUB_RMATH_H
#include <math.h>

static inline double dnorm(double x, double mu, double sigma, int give_log) {
    double z = (x - mu) / sigma;
    double logd = -0.5 * z * z - log(sigma) - 0.5 * log(2.0 * 3.14159265358979323846);
    return give_log ? logd : exp(logd);
}

static inline double pnorm(double x, double mu, double sigma, int lower_tail, int log_p) {
    double z = (x - mu) / sigma;
    double p = 0.5 * (1.0 + erf(z / sqrt(2.0)));
    if (!lower_tail)
        p = 1.0 - p;
    return log_p ? log(p) : p;
}
#endif
