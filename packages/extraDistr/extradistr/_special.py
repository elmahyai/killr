"""R special functions used by extraDistr.

pnorm is math.erf. The other cdfs and densities are SciPy, which matched
R 4.5 to well inside 1e-8 on these calls.
"""

import math

from scipy import special
from scipy.stats import beta, binom, gamma, nbinom, norm, poisson, t

from extradistr._rng import qnorm

_LOG_2PI = math.log(2.0 * math.pi)


def dnorm(x, mean=0.0, sd=1.0, log=False):
    if sd <= 0 or not math.isfinite(sd):
        return math.nan
    z = (x - mean) / sd
    logp = -0.5 * (z * z + _LOG_2PI) - math.log(sd)
    return logp if log else math.exp(logp)


def pnorm(x, mean=0.0, sd=1.0, lower_tail=True, log_p=False):
    if sd < 0 or not math.isfinite(sd):
        return math.nan
    if sd == 0:
        p = 1.0 if x >= mean else 0.0
    else:
        z = (x - mean) / sd
        p = 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))
    if not lower_tail:
        p = 1.0 - p
    if log_p:
        return math.log(p) if p > 0 else -math.inf
    return p


def pbeta(x, a, b, lower_tail=True, log_p=False):
    if a <= 0 or b <= 0:
        return math.nan
    p = float(beta.cdf(x, a, b))
    if not lower_tail:
        p = 1.0 - p
    if log_p:
        return math.log(p) if p > 0 else -math.inf
    return p


def qbeta(p, a, b, lower_tail=True, log_p=False):
    if log_p:
        p = math.exp(p)
    if not lower_tail:
        p = 1.0 - p
    if a <= 0 or b <= 0 or not 0.0 <= p <= 1.0:
        return math.nan
    return float(beta.ppf(p, a, b))


def dbeta(x, a, b, log=False):
    if a <= 0 or b <= 0:
        return math.nan
    if log:
        return float(beta.logpdf(x, a, b))
    return float(beta.pdf(x, a, b))


def pgamma(x, shape, scale=1.0, lower_tail=True, log_p=False):
    if shape <= 0 or scale <= 0:
        return math.nan
    p = float(gamma.cdf(x, a=shape, scale=scale))
    if not lower_tail:
        p = 1.0 - p
    if log_p:
        return math.log(p) if p > 0 else -math.inf
    return p


def qgamma(p, shape, scale=1.0, lower_tail=True, log_p=False):
    if log_p:
        p = math.exp(p)
    if not lower_tail:
        p = 1.0 - p
    if shape <= 0 or scale <= 0 or not 0.0 <= p <= 1.0:
        return math.nan
    return float(gamma.ppf(p, a=shape, scale=scale))


def dgamma(x, shape, scale=1.0, log=False):
    if shape <= 0 or scale <= 0:
        return math.nan
    if log:
        return float(gamma.logpdf(x, a=shape, scale=scale))
    return float(gamma.pdf(x, a=shape, scale=scale))


def dpois(x, lam, log=False):
    if lam < 0:
        return math.nan
    if log:
        return float(poisson.logpmf(x, lam))
    return float(poisson.pmf(x, lam))


def ppois(q, lam, lower_tail=True, log_p=False):
    if lam < 0:
        return math.nan
    p = float(poisson.cdf(q, lam))
    if not lower_tail:
        p = 1.0 - p
    if log_p:
        return math.log(p) if p > 0 else -math.inf
    return p


def qpois(p, lam, lower_tail=True, log_p=False):
    if log_p:
        p = math.exp(p)
    if not lower_tail:
        p = 1.0 - p
    if lam < 0 or not 0.0 <= p <= 1.0:
        return math.nan
    return float(poisson.ppf(p, lam))


def dbinom(x, n, prob, log=False):
    if log:
        return float(binom.logpmf(x, n, prob))
    return float(binom.pmf(x, n, prob))


def pbinom(q, n, prob, lower_tail=True, log_p=False):
    p = float(binom.cdf(q, n, prob))
    if not lower_tail:
        p = 1.0 - p
    if log_p:
        return math.log(p) if p > 0 else -math.inf
    return p


def qbinom(p, n, prob, lower_tail=True, log_p=False):
    if log_p:
        p = math.exp(p)
    if not lower_tail:
        p = 1.0 - p
    return float(binom.ppf(p, n, prob))


def dnbinom(x, size, prob, log=False):
    if log:
        return float(nbinom.logpmf(x, size, prob))
    return float(nbinom.pmf(x, size, prob))


def pnbinom(q, size, prob, lower_tail=True, log_p=False):
    p = float(nbinom.cdf(q, size, prob))
    if not lower_tail:
        p = 1.0 - p
    if log_p:
        return math.log(p) if p > 0 else -math.inf
    return p


def qnbinom(p, size, prob, lower_tail=True, log_p=False):
    if log_p:
        p = math.exp(p)
    if not lower_tail:
        p = 1.0 - p
    return float(nbinom.ppf(p, size, prob))


def dt(x, df, log=False):
    if log:
        return float(t.logpdf(x, df))
    return float(t.pdf(x, df))


def pt(q, df, lower_tail=True, log_p=False):
    p = float(t.cdf(q, df))
    if not lower_tail:
        p = 1.0 - p
    if log_p:
        return math.log(p) if p > 0 else -math.inf
    return p


def qt(p, df, lower_tail=True, log_p=False):
    if log_p:
        p = math.exp(p)
    if not lower_tail:
        p = 1.0 - p
    return float(t.ppf(p, df))


def lgamma(x):
    return math.lgamma(x)


def lbeta(a, b):
    return math.lgamma(a) + math.lgamma(b) - math.lgamma(a + b)


def lchoose(n, k):
    return special.gammaln(n + 1) - special.gammaln(k + 1) - special.gammaln(n - k + 1)


def bessel_i(x, nu, expon_scaled=False):
    return float(special.iv(nu, x)) if not expon_scaled else float(special.ive(nu, x))
