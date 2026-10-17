/*
 * Declarations of the R distribution functions used by the vendored ordinal
 * kernels. Implementations are in src/shim/rshim.c.
 */
#ifndef ORDINAL_CLMM_SHIM_RMATH_H
#define ORDINAL_CLMM_SHIM_RMATH_H

double dnorm(double x, double mu, double sigma, int give_log);
double pnorm(double x, double mu, double sigma, int lower_tail, int log_p);
double dlogis(double x, double loc, double scale, int give_log);
double plogis(double x, double loc, double scale, int lower_tail, int log_p);
double dcauchy(double x, double loc, double scale, int give_log);
double pcauchy(double x, double loc, double scale, int lower_tail, int log_p);
double pgamma(double x, double alph, double scale, int lower_tail, int log_p);
double lgammafn(double x);

#endif
