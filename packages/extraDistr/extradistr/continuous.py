"""Continuous families from extraDistr 1.10.0.5.

Scalar functions follow the C++ in src/. The R wrappers decide argument
order and, for inverse-gamma, which parameterization reaches that C++.
"""

import math

from extradistr._rgen import rbeta, rcauchy, rchisq, rgamma, rt
from extradistr._rng import exp_rand, norm_rand, qnorm, runif, unif
from extradistr._special import (
    dbeta,
    dnorm,
    dt,
    lbeta,
    lgamma,
    pbeta,
    pgamma,
    pnorm,
    pt,
    qbeta,
    qgamma,
    qt,
)
from extradistr._vec import as_vec, density, generate, probability, quantile

_SQRT_2PI = 2.506628274631000241612
_PHI0 = 0.3989422804014327028632
_LOG2 = 0.6931471805599452862268
_SQRT_E = math.sqrt(math.e)


def _nan_sum(*parts):
    if any(math.isnan(part) for part in parts):
        return math.fsum(parts)
    return None


def _log_pos(value):
    if math.isnan(value):
        return value
    if value > 0.0:
        return math.log(value)
    if value == 0.0:
        return -math.inf
    return math.nan


def _reciprocal(value):
    if value == 0.0:
        return math.copysign(math.inf, value)
    return 1.0 / value


def _log(value):
    """C log: log(0) is -Inf, and a negative argument is NaN."""
    if value == 0.0:
        return -math.inf
    if value < 0.0 or math.isnan(value):
        return math.nan
    return math.log(value)


def _log1p(value):
    """C log1p: log1p(-1) is -Inf."""
    if value == -1.0:
        return -math.inf
    if value < -1.0 or math.isnan(value):
        return math.nan
    return math.log1p(value)


def _pow(base, exp):
    """C pow for a base in [0, 1]. 0^negative is +Inf."""
    if base == 0.0:
        if exp > 0.0:
            return 0.0
        if exp < 0.0:
            return math.inf
        return 1.0
    return base**exp


def _prob_ok(p):
    return 0.0 <= p <= 1.0


def _warn_nan(thrown):
    thrown[0] = True
    return math.nan


# --- Wald (inverse Gaussian) -------------------------------------------------


def _logpdf_wald(x, mu, lam, thrown):
    total = _nan_sum(x, mu, lam)
    if total is not None:
        return total
    if mu <= 0.0 or lam <= 0.0:
        return _warn_nan(thrown)
    if x <= 0.0 or not math.isfinite(x):
        return -math.inf
    return (
        0.5 * math.log(lam / (2.0 * math.pi * x * x * x))
        - (lam * (x - mu) * (x - mu)) / (2.0 * mu * mu * x)
    )


def _log_phi_neg(a):
    """log(Phi(-a)) for a > 0. erfc is the same normal tail as erf, kept in range."""
    z = a / math.sqrt(2.0)
    tail = math.erfc(z)
    if tail > 0.0:
        return math.log(tail) - _LOG2
    if not math.isfinite(a):
        return -math.inf
    return -0.5 * a * a - math.log(a) - 0.5 * math.log(2.0 * math.pi)


def _cdf_wald(x, mu, lam, thrown):
    total = _nan_sum(x, mu, lam)
    if total is not None:
        return total
    if mu <= 0.0 or lam <= 0.0:
        return _warn_nan(thrown)
    if x <= 0.0:
        return 0.0
    if math.isinf(x) and x > 0.0:
        return 1.0
    root = math.sqrt(lam / x)
    left = root * (x / mu - 1.0)
    right = root * (x / mu + 1.0)
    return pnorm(left) + math.exp((2.0 * lam) / mu + _log_phi_neg(right))


def _rng_wald(mu, lam, thrown):
    if math.isnan(mu) or math.isnan(lam) or mu <= 0.0 or lam <= 0.0:
        return _warn_nan(thrown)
    u = unif()
    y = norm_rand() ** 2
    x = (
        mu
        + (mu * mu * y) / (2.0 * lam)
        - mu / (2.0 * lam) * math.sqrt(4.0 * mu * lam * y + (mu * mu) * (y * y))
    )
    if u <= mu / (mu + x):
        return x
    return (mu * mu) / x


def dwald(x, mu, lambda_, log=False):
    return density(log, _logpdf_wald, x, mu, lambda_)


def pwald(q, mu, lambda_, lower_tail=True, log_p=False):
    return probability(lower_tail, log_p, _cdf_wald, q, mu, lambda_)


def rwald(n, mu, lambda_):
    return generate(n, _rng_wald, mu, lambda_)


# --- Birnbaum-Saunders (fatigue) --------------------------------------------


def _logpdf_fatigue(x, alpha, beta, mu, thrown):
    total = _nan_sum(x, alpha, beta, mu)
    if total is not None:
        return total
    if alpha <= 0.0 or beta <= 0.0:
        return _warn_nan(thrown)
    if x <= mu or not math.isfinite(x):
        return -math.inf
    z = x - mu
    zb = math.sqrt(z / beta)
    bz = math.sqrt(beta / z)
    return (
        math.log(zb + bz)
        - _LOG2
        - math.log(alpha)
        - math.log(z)
        + dnorm((zb - bz) / alpha, log=True)
    )


def _cdf_fatigue(x, alpha, beta, mu, thrown):
    total = _nan_sum(x, alpha, beta, mu)
    if total is not None:
        return total
    if alpha <= 0.0 or beta <= 0.0:
        return _warn_nan(thrown)
    if x <= mu:
        return 0.0
    z = x - mu
    zb = math.sqrt(z / beta)
    bz = math.sqrt(beta / z)
    zscore = (zb - bz) / alpha
    # erfc keeps the same normal tail as erf when the score is largely negative.
    if zscore < 0.0:
        return 0.5 * math.erfc(-zscore / math.sqrt(2.0))
    return pnorm(zscore)


def _invcdf_fatigue(p, alpha, beta, mu, thrown):
    total = _nan_sum(p, alpha, beta, mu)
    if total is not None:
        return total
    if alpha <= 0.0 or beta <= 0.0 or not _prob_ok(p):
        return _warn_nan(thrown)
    if p == 0.0:
        return mu
    z = alpha / 2.0 * qnorm(p)
    return (z + math.sqrt(z * z + 1.0)) ** 2.0 * beta + mu


def _rng_fatigue(alpha, beta, mu, thrown):
    if (
        math.isnan(alpha)
        or math.isnan(beta)
        or math.isnan(mu)
        or alpha <= 0.0
        or beta <= 0.0
    ):
        return _warn_nan(thrown)
    z = alpha / 2.0 * norm_rand()
    return (z + math.sqrt(z * z + 1.0)) ** 2.0 * beta + mu


def dfatigue(x, alpha, beta=1, mu=0, log=False):
    return density(log, _logpdf_fatigue, x, alpha, beta, mu)


def pfatigue(q, alpha, beta=1, mu=0, lower_tail=True, log_p=False):
    return probability(lower_tail, log_p, _cdf_fatigue, q, alpha, beta, mu)


def qfatigue(p, alpha, beta=1, mu=0, lower_tail=True, log_p=False):
    return quantile(lower_tail, log_p, _invcdf_fatigue, p, alpha, beta, mu)


def rfatigue(n, alpha, beta=1, mu=0):
    return generate(n, _rng_fatigue, alpha, beta, mu)


# --- Huber -------------------------------------------------------------------


def _logpdf_huber(x, mu, sigma, c, thrown):
    total = _nan_sum(x, mu, sigma, c)
    if total is not None:
        return total
    if sigma <= 0.0 or c <= 0.0:
        return _warn_nan(thrown)
    z = abs((x - mu) / sigma)
    scale = _LOG2 + math.log(_SQRT_2PI) + math.log(pnorm(c) + dnorm(c) / c - 0.5)
    if z <= c:
        rho = (z * z) / 2.0
    else:
        rho = c * z - (c * c) / 2.0
    return -rho - scale - math.log(sigma)


def _cdf_huber(x, mu, sigma, c, thrown):
    total = _nan_sum(x, mu, sigma, c)
    if total is not None:
        return total
    if sigma <= 0.0 or c <= 0.0:
        return _warn_nan(thrown)
    area = 2.0 * (dnorm(c) / c - pnorm(-c) + 0.5)
    z = (x - mu) / sigma
    az = -abs(z)
    if az <= -c:
        p = math.exp((c * c) / 2.0) / c * math.exp(c * az) / _SQRT_2PI / area
    else:
        p = (dnorm(c) / c + pnorm(az) - pnorm(-c)) / area
    if z <= 0.0:
        return p
    return 1.0 - p


def _huber_dev(pm, c):
    area = 2.0 * _SQRT_2PI * (pnorm(c) + dnorm(c) / c - 0.5)
    if pm <= _SQRT_2PI * dnorm(c) / (c * area):
        return _log(c * pm * area) / c - c / 2.0
    return qnorm(abs(1.0 - pnorm(c) + pm * area / _SQRT_2PI - dnorm(c) / c))


def _invcdf_huber(p, mu, sigma, c, thrown):
    total = _nan_sum(p, mu, sigma, c)
    if total is not None:
        return total
    if sigma <= 0.0 or c <= 0.0 or not _prob_ok(p):
        return _warn_nan(thrown)
    x = _huber_dev(min(p, 1.0 - p), c)
    if p < 0.5:
        return mu + x * sigma
    return mu - x * sigma


def _rng_huber(mu, sigma, c, thrown):
    if (
        math.isnan(mu)
        or math.isnan(sigma)
        or math.isnan(c)
        or sigma <= 0.0
        or c <= 0.0
    ):
        return _warn_nan(thrown)
    u = unif()
    x = _huber_dev(min(u, 1.0 - u), c)
    if u < 0.5:
        return mu + x * sigma
    return mu - x * sigma


def dhuber(x, mu=0, sigma=1, epsilon=1.345, log=False):
    return density(log, _logpdf_huber, x, mu, sigma, epsilon)


def phuber(q, mu=0, sigma=1, epsilon=1.345, lower_tail=True, log_p=False):
    return probability(lower_tail, log_p, _cdf_huber, q, mu, sigma, epsilon)


def qhuber(p, mu=0, sigma=1, epsilon=1.345, lower_tail=True, log_p=False):
    return quantile(lower_tail, log_p, _invcdf_huber, p, mu, sigma, epsilon)


def rhuber(n, mu=0, sigma=1, epsilon=1.345):
    return generate(n, _rng_huber, mu, sigma, epsilon)


# --- Slash -------------------------------------------------------------------


def _logpdf_slash(x, mu, sigma, thrown):
    total = _nan_sum(x, mu, sigma)
    if total is not None:
        return total
    if sigma <= 0.0:
        return _warn_nan(thrown)
    z = (x - mu) / sigma
    if z == 0.0:
        return _log_pos(0.19947114020071635)
    return _log_pos((_PHI0 - dnorm(z)) / (z * z) / sigma)


def _cdf_slash(x, mu, sigma, thrown):
    total = _nan_sum(x, mu, sigma)
    if total is not None:
        return total
    if sigma <= 0.0:
        return _warn_nan(thrown)
    z = (x - mu) / sigma
    if z == 0.0:
        return 0.5
    return pnorm(z) - (_PHI0 - dnorm(z)) / z


def _rng_slash(mu, sigma, thrown):
    if math.isnan(mu) or math.isnan(sigma) or sigma <= 0.0:
        return _warn_nan(thrown)
    z = norm_rand()
    u = unif()
    return z / u * sigma + mu


def dslash(x, mu=0, sigma=1, log=False):
    return density(log, _logpdf_slash, x, mu, sigma)


def pslash(q, mu=0, sigma=1, lower_tail=True, log_p=False):
    return probability(lower_tail, log_p, _cdf_slash, q, mu, sigma)


def rslash(n, mu=0, sigma=1):
    return generate(n, _rng_slash, mu, sigma)


# --- Tukey lambda ------------------------------------------------------------


def _invcdf_tlambda(p, lam, thrown):
    total = _nan_sum(p, lam)
    if total is not None:
        return total
    if not _prob_ok(p):
        return _warn_nan(thrown)
    if lam == 0.0:
        return _log(p) - _log(1.0 - p)
    return (_pow(p, lam) - _pow(1.0 - p, lam)) / lam


def _rng_tlambda(lam, thrown):
    if math.isnan(lam):
        return _warn_nan(thrown)
    u = unif()
    if lam == 0.0:
        return _log(u) - _log(1.0 - u)
    return (_pow(u, lam) - _pow(1.0 - u, lam)) / lam


def qtlambda(p, lambda_, lower_tail=True, log_p=False):
    return quantile(lower_tail, log_p, _invcdf_tlambda, p, lambda_)


def rtlambda(n, lambda_):
    return generate(n, _rng_tlambda, lambda_)


# --- Half-normal -------------------------------------------------------------


def _logpdf_hnorm(x, sigma, thrown):
    total = _nan_sum(x, sigma)
    if total is not None:
        return total
    if sigma <= 0.0:
        return _warn_nan(thrown)
    if x < 0.0:
        return -math.inf
    return _LOG2 + dnorm(x, sd=sigma, log=True)


def _cdf_hnorm(x, sigma, thrown):
    total = _nan_sum(x, sigma)
    if total is not None:
        return total
    if sigma <= 0.0:
        return _warn_nan(thrown)
    if x < 0.0:
        return 0.0
    return 2.0 * pnorm(x, sd=sigma) - 1.0


def _invcdf_hnorm(p, sigma, thrown):
    total = _nan_sum(p, sigma)
    if total is not None:
        return total
    if sigma <= 0.0 or not _prob_ok(p):
        return _warn_nan(thrown)
    return qnorm((p + 1.0) / 2.0, sd=sigma)


def _rng_hnorm(sigma, thrown):
    if math.isnan(sigma) or sigma <= 0.0:
        return _warn_nan(thrown)
    return abs(norm_rand()) * sigma


def dhnorm(x, sigma=1, log=False):
    return density(log, _logpdf_hnorm, x, sigma)


def phnorm(q, sigma=1, lower_tail=True, log_p=False):
    return probability(lower_tail, log_p, _cdf_hnorm, q, sigma)


def qhnorm(p, sigma=1, lower_tail=True, log_p=False):
    return quantile(lower_tail, log_p, _invcdf_hnorm, p, sigma)


def rhnorm(n, sigma=1):
    return generate(n, _rng_hnorm, sigma)


# --- Half-Cauchy -------------------------------------------------------------


def _logpdf_hcauchy(x, sigma, thrown):
    total = _nan_sum(x, sigma)
    if total is not None:
        return total
    if sigma <= 0.0:
        return _warn_nan(thrown)
    if x < 0.0:
        return -math.inf
    return (
        _LOG2
        - math.log(math.pi)
        - _log1p(math.exp((_log(x) - math.log(sigma)) * 2.0))
        - math.log(sigma)
    )


def _cdf_hcauchy(x, sigma, thrown):
    total = _nan_sum(x, sigma)
    if total is not None:
        return total
    if sigma <= 0.0:
        return _warn_nan(thrown)
    if x < 0.0:
        return 0.0
    return 2.0 / math.pi * math.atan(x / sigma)


def _invcdf_hcauchy(p, sigma, thrown):
    total = _nan_sum(p, sigma)
    if total is not None:
        return total
    if sigma <= 0.0 or not _prob_ok(p):
        return _warn_nan(thrown)
    return sigma * math.tan((math.pi * p) / 2.0)


def _rng_hcauchy(sigma, thrown):
    if math.isnan(sigma) or sigma <= 0.0:
        return _warn_nan(thrown)
    return abs(rcauchy(0.0, sigma))


def dhcauchy(x, sigma=1, log=False):
    return density(log, _logpdf_hcauchy, x, sigma)


def phcauchy(q, sigma=1, lower_tail=True, log_p=False):
    return probability(lower_tail, log_p, _cdf_hcauchy, q, sigma)


def qhcauchy(p, sigma=1, lower_tail=True, log_p=False):
    return quantile(lower_tail, log_p, _invcdf_hcauchy, p, sigma)


def rhcauchy(n, sigma=1):
    return generate(n, _rng_hcauchy, sigma)


# --- Half-t ------------------------------------------------------------------


def _logpdf_ht(x, nu, sigma, thrown):
    total = _nan_sum(x, nu, sigma)
    if total is not None:
        return total
    if sigma <= 0.0 or nu <= 0.0:
        return _warn_nan(thrown)
    if x < 0.0:
        return -math.inf
    return _LOG2 + dt(x / sigma, nu, log=True) - math.log(sigma)


def _cdf_ht(x, nu, sigma, thrown):
    total = _nan_sum(x, nu, sigma)
    if total is not None:
        return total
    if sigma <= 0.0 or nu <= 0.0:
        return _warn_nan(thrown)
    if x < 0.0:
        return 0.0
    return 2.0 * pt(x / sigma, nu) - 1.0


def _invcdf_ht(p, nu, sigma, thrown):
    total = _nan_sum(p, nu, sigma)
    if total is not None:
        return total
    if sigma <= 0.0 or nu <= 0.0 or not _prob_ok(p):
        return _warn_nan(thrown)
    return qt((p + 1.0) / 2.0, nu) * sigma


def _rng_ht(nu, sigma, thrown):
    if math.isnan(nu) or math.isnan(sigma) or sigma <= 0.0 or nu <= 0.0:
        return _warn_nan(thrown)
    return abs(rt(nu) * sigma)


def dht(x, nu, sigma=1, log=False):
    return density(log, _logpdf_ht, x, nu, sigma)


def pht(q, nu, sigma=1, lower_tail=True, log_p=False):
    return probability(lower_tail, log_p, _cdf_ht, q, nu, sigma)


def qht(p, nu, sigma=1, lower_tail=True, log_p=False):
    return quantile(lower_tail, log_p, _invcdf_ht, p, nu, sigma)


def rht(n, nu, sigma=1):
    return generate(n, _rng_ht, nu, sigma)


# --- Location-scale t --------------------------------------------------------


def _logpdf_lst(x, nu, mu, sigma, thrown):
    total = _nan_sum(x, nu, mu, sigma)
    if total is not None:
        return total
    if nu <= 0.0 or sigma <= 0.0:
        return _warn_nan(thrown)
    return dt((x - mu) / sigma, nu, log=True) - math.log(sigma)


def _cdf_lst(x, nu, mu, sigma, thrown):
    total = _nan_sum(x, nu, mu, sigma)
    if total is not None:
        return total
    if nu <= 0.0 or sigma <= 0.0:
        return _warn_nan(thrown)
    return pt((x - mu) / sigma, nu)


def _invcdf_lst(p, nu, mu, sigma, thrown):
    total = _nan_sum(p, nu, mu, sigma)
    if total is not None:
        return total
    if nu <= 0.0 or sigma <= 0.0 or not _prob_ok(p):
        return _warn_nan(thrown)
    return qt(p, nu) * sigma + mu


def _rng_lst(nu, mu, sigma, thrown):
    if (
        math.isnan(nu)
        or math.isnan(mu)
        or math.isnan(sigma)
        or nu <= 0.0
        or sigma <= 0.0
    ):
        return _warn_nan(thrown)
    return rt(nu) * sigma + mu


def dlst(x, df, mu=0, sigma=1, log=False):
    return density(log, _logpdf_lst, x, df, mu, sigma)


def plst(q, df, mu=0, sigma=1, lower_tail=True, log_p=False):
    return probability(lower_tail, log_p, _cdf_lst, q, df, mu, sigma)


def qlst(p, df, mu=0, sigma=1, lower_tail=True, log_p=False):
    return quantile(lower_tail, log_p, _invcdf_lst, p, df, mu, sigma)


def rlst(n, df, mu=0, sigma=1):
    return generate(n, _rng_lst, df, mu, sigma)


# --- Inverse-gamma -----------------------------------------------------------
# dinvgamma passes 1/beta into the C++ density. The cdf keeps beta.


def _logpdf_invgamma_cpp(x, alpha, beta, thrown):
    total = _nan_sum(x, alpha, beta)
    if total is not None:
        return total
    if alpha <= 0.0 or beta <= 0.0:
        return _warn_nan(thrown)
    if x <= 0.0:
        return -math.inf
    return (
        math.log(beta) * -alpha
        - lgamma(alpha)
        + math.log(x) * (-alpha - 1.0)
        - 1.0 / (beta * x)
    )


def _cdf_invgamma_cpp(x, alpha, beta, thrown):
    total = _nan_sum(x, alpha, beta)
    if total is not None:
        return total
    if alpha <= 0.0 or beta <= 0.0:
        return _warn_nan(thrown)
    if x <= 0.0:
        return 0.0
    return pgamma(1.0 / x, alpha, scale=1.0 / beta, lower_tail=False)


def _dinvgamma_one(x, alpha, beta, thrown):
    return _logpdf_invgamma_cpp(x, alpha, _reciprocal(beta), thrown)


def dinvgamma(x, alpha, beta=1, log=False):
    return density(log, _dinvgamma_one, x, alpha, beta)


def pinvgamma(q, alpha, beta=1, lower_tail=True, log_p=False):
    return probability(lower_tail, log_p, _cdf_invgamma_cpp, q, alpha, beta)


def _invcdf_invgamma(p, alpha, beta, thrown):
    total = _nan_sum(p, alpha, beta)
    if total is not None:
        return total
    if alpha <= 0.0 or beta <= 0.0 or not _prob_ok(p):
        return _warn_nan(thrown)
    draw = qgamma(p, alpha, scale=_reciprocal(beta), lower_tail=False)
    if draw == 0.0:
        return math.inf
    if math.isinf(draw):
        return 0.0
    return 1.0 / draw


def qinvgamma(p, alpha, beta=1, lower_tail=True, log_p=False):
    return quantile(lower_tail, log_p, _invcdf_invgamma, p, alpha, beta)


def _rng_invgamma(alpha, beta, thrown):
    if math.isnan(alpha) or math.isnan(beta) or alpha <= 0.0 or beta <= 0.0:
        return _warn_nan(thrown)
    draw = rgamma(alpha, _reciprocal(beta))
    if draw == 0.0:
        return math.inf
    return 1.0 / draw


def rinvgamma(n, alpha, beta=1):
    return generate(n, _rng_invgamma, alpha, beta)


# --- Inverse chi-squared -----------------------------------------------------


def dinvchisq(x, nu, tau=None, log=False):
    if tau is None:
        return dinvgamma(x, as_vec(nu) / 2.0, 0.5, log=log)

    def one(x, nu, tau, thrown):
        return _dinvgamma_one(x, nu / 2.0, (nu * tau) / 2.0, thrown)

    return density(log, one, x, nu, tau)


def pinvchisq(q, nu, tau=None, lower_tail=True, log_p=False):
    if tau is None:
        return pinvgamma(q, as_vec(nu) / 2.0, 0.5, lower_tail=lower_tail, log_p=log_p)

    def one(q, nu, tau, thrown):
        return _cdf_invgamma_cpp(q, nu / 2.0, (nu * tau) / 2.0, thrown)

    return probability(lower_tail, log_p, one, q, nu, tau)


def _invcdf_invchisq(p, nu, tau, thrown):
    total = _nan_sum(p, nu, tau)
    if total is not None:
        return total
    if nu <= 0.0 or tau <= 0.0 or not _prob_ok(p):
        return _warn_nan(thrown)
    draw = qgamma(p, nu / 2.0, scale=_reciprocal((nu * tau) / 2.0), lower_tail=False)
    if draw == 0.0:
        return math.inf
    if math.isinf(draw):
        return 0.0
    return 1.0 / draw


def _invcdf_invchisq_plain(p, nu, thrown):
    total = _nan_sum(p, nu)
    if total is not None:
        return total
    if nu <= 0.0 or not _prob_ok(p):
        return _warn_nan(thrown)
    draw = qgamma(p, nu / 2.0, scale=2.0, lower_tail=False)
    if draw == 0.0:
        return math.inf
    if math.isinf(draw):
        return 0.0
    return 1.0 / draw


def qinvchisq(p, nu, tau=None, lower_tail=True, log_p=False):
    if tau is None:
        return quantile(lower_tail, log_p, _invcdf_invchisq_plain, p, nu)
    return quantile(lower_tail, log_p, _invcdf_invchisq, p, nu, tau)


def _rng_invchisq(nu, thrown):
    if math.isnan(nu) or nu <= 0.0:
        return _warn_nan(thrown)
    draw = rchisq(nu)
    if draw == 0.0:
        return math.inf
    return 1.0 / draw


def _rng_invchisq_scaled(nu, tau, thrown):
    if math.isnan(nu) or math.isnan(tau) or nu <= 0.0 or tau <= 0.0:
        return _warn_nan(thrown)
    draw = rgamma(nu / 2.0, _reciprocal((nu * tau) / 2.0))
    if draw == 0.0:
        return math.inf
    return 1.0 / draw


def rinvchisq(n, nu, tau=None):
    if tau is None:
        return generate(n, _rng_invchisq, nu)
    return generate(n, _rng_invchisq_scaled, nu, tau)


# --- Beta prime --------------------------------------------------------------


def _logpdf_betapr(x, alpha, beta, sigma, thrown):
    total = _nan_sum(x, alpha, beta, sigma)
    if total is not None:
        return total
    if alpha <= 0.0 or beta <= 0.0 or sigma <= 0.0:
        return _warn_nan(thrown)
    if x <= 0.0 or not math.isfinite(x):
        return -math.inf
    z = x / sigma
    return (
        _log(z) * (alpha - 1.0)
        + _log1p(z) * (-alpha - beta)
        - lbeta(alpha, beta)
        - math.log(sigma)
    )


def _cdf_betapr(x, alpha, beta, sigma, thrown):
    total = _nan_sum(x, alpha, beta, sigma)
    if total is not None:
        return total
    if alpha <= 0.0 or beta <= 0.0 or sigma <= 0.0:
        return _warn_nan(thrown)
    if x <= 0.0:
        return 0.0
    if not math.isfinite(x):
        return 1.0
    z = x / sigma
    return pbeta(z / (1.0 + z), alpha, beta)


def _invcdf_betapr(p, alpha, beta, sigma, thrown):
    total = _nan_sum(p, alpha, beta, sigma)
    if total is not None:
        return total
    if alpha <= 0.0 or beta <= 0.0 or sigma <= 0.0 or not _prob_ok(p):
        return _warn_nan(thrown)
    if p == 0.0:
        return 0.0
    if p == 1.0:
        return math.inf
    x = qbeta(p, alpha, beta)
    if x == 1.0:
        return math.inf
    return x / (1.0 - x) * sigma


def _rng_betapr(alpha, beta, sigma, thrown):
    if (
        math.isnan(alpha)
        or math.isnan(beta)
        or math.isnan(sigma)
        or alpha <= 0.0
        or beta <= 0.0
        or sigma <= 0.0
    ):
        return _warn_nan(thrown)
    x = rbeta(alpha, beta)
    if x == 1.0:
        return math.inf
    return x / (1.0 - x) * sigma


def dbetapr(x, shape1, shape2, scale=1, log=False):
    return density(log, _logpdf_betapr, x, shape1, shape2, scale)


def pbetapr(q, shape1, shape2, scale=1, lower_tail=True, log_p=False):
    return probability(lower_tail, log_p, _cdf_betapr, q, shape1, shape2, scale)


def qbetapr(p, shape1, shape2, scale=1, lower_tail=True, log_p=False):
    return quantile(lower_tail, log_p, _invcdf_betapr, p, shape1, shape2, scale)


def rbetapr(n, shape1, shape2, scale=1):
    return generate(n, _rng_betapr, shape1, shape2, scale)


# --- Non-standard beta -------------------------------------------------------


def _logpdf_nsbeta(x, alpha, beta, lower, upper, thrown):
    total = _nan_sum(x, alpha, beta, lower, upper)
    if total is not None:
        return total
    if lower >= upper or alpha < 0.0 or beta < 0.0:
        return _warn_nan(thrown)
    span = upper - lower
    return dbeta((x - lower) / span, alpha, beta, log=True) - math.log(span)


def _cdf_nsbeta(x, alpha, beta, lower, upper, thrown):
    total = _nan_sum(x, alpha, beta, lower, upper)
    if total is not None:
        return total
    if lower >= upper or alpha < 0.0 or beta < 0.0:
        return _warn_nan(thrown)
    return pbeta((x - lower) / (upper - lower), alpha, beta)


def _invcdf_nsbeta(p, alpha, beta, lower, upper, thrown):
    total = _nan_sum(p, alpha, beta, lower, upper)
    if total is not None:
        return total
    if lower >= upper or alpha < 0.0 or beta < 0.0 or not _prob_ok(p):
        return _warn_nan(thrown)
    return qbeta(p, alpha, beta) * (upper - lower) + lower


def _rng_nsbeta(alpha, beta, lower, upper, thrown):
    if (
        math.isnan(alpha)
        or math.isnan(beta)
        or math.isnan(lower)
        or math.isnan(upper)
        or lower >= upper
        or alpha < 0.0
        or beta < 0.0
    ):
        return _warn_nan(thrown)
    return rbeta(alpha, beta) * (upper - lower) + lower


def dnsbeta(x, shape1, shape2, min=0, max=1, log=False):
    return density(log, _logpdf_nsbeta, x, shape1, shape2, min, max)


def pnsbeta(q, shape1, shape2, min=0, max=1, lower_tail=True, log_p=False):
    return probability(lower_tail, log_p, _cdf_nsbeta, q, shape1, shape2, min, max)


def qnsbeta(p, shape1, shape2, min=0, max=1, lower_tail=True, log_p=False):
    return quantile(lower_tail, log_p, _invcdf_nsbeta, p, shape1, shape2, min, max)


def rnsbeta(n, shape1, shape2, min=0, max=1):
    return generate(n, _rng_nsbeta, shape1, shape2, min, max)


# --- Proportion (reparametrized beta) ----------------------------------------


def _logpdf_prop(x, size, mean, prior, thrown):
    total = _nan_sum(x, size, mean, prior)
    if total is not None:
        return total
    if size <= 0.0 or mean <= 0.0 or mean >= 1.0 or prior < 0.0:
        return _warn_nan(thrown)
    return dbeta(x, size * mean + prior, size * (1.0 - mean) + prior, log=True)


def _cdf_prop(x, size, mean, prior, thrown):
    total = _nan_sum(x, size, mean, prior)
    if total is not None:
        return total
    if size <= 0.0 or mean <= 0.0 or mean >= 1.0 or prior < 0.0:
        return _warn_nan(thrown)
    return pbeta(x, size * mean + prior, size * (1.0 - mean) + prior)


def _invcdf_prop(p, size, mean, prior, thrown):
    total = _nan_sum(p, size, mean, prior)
    if total is not None:
        return total
    if size <= 0.0 or mean <= 0.0 or mean >= 1.0 or prior < 0.0 or not _prob_ok(p):
        return _warn_nan(thrown)
    return qbeta(p, size * mean + prior, size * (1.0 - mean) + prior)


def _rng_prop(size, mean, prior, thrown):
    if (
        math.isnan(size)
        or math.isnan(mean)
        or math.isnan(prior)
        or size <= 0.0
        or mean <= 0.0
        or mean >= 1.0
        or prior < 0.0
    ):
        return _warn_nan(thrown)
    return rbeta(size * mean + prior, size * (1.0 - mean) + prior)


def dprop(x, size, mean, prior=0, log=False):
    return density(log, _logpdf_prop, x, size, mean, prior)


def pprop(q, size, mean, prior=0, lower_tail=True, log_p=False):
    return probability(lower_tail, log_p, _cdf_prop, q, size, mean, prior)


def qprop(p, size, mean, prior=0, lower_tail=True, log_p=False):
    return quantile(lower_tail, log_p, _invcdf_prop, p, size, mean, prior)


def rprop(n, size, mean, prior=0):
    return generate(n, _rng_prop, size, mean, prior)


# --- Bhattacharjee -----------------------------------------------------------


def _dunif(x, left, right):
    if left > right:
        return math.nan
    if left == right:
        return math.inf if x == left else 0.0
    if left <= x <= right:
        return 1.0 / (right - left)
    return 0.0


def _punif(x, left, right):
    if left > right:
        return math.nan
    if x <= left:
        return 0.0
    if x >= right:
        return 1.0
    return (x - left) / (right - left)


def _logpdf_bhatt(x, mu, sigma, a, thrown):
    total = _nan_sum(x, mu, sigma, a)
    if total is not None:
        return total
    if sigma < 0.0 or a < 0.0:
        return _warn_nan(thrown)
    if sigma == 0.0:
        return _log_pos(_dunif(x, mu - a, mu + a))
    if a == 0.0:
        return dnorm(x, mu, sigma, log=True)
    z = x - mu
    return _log_pos((pnorm((z + a) / sigma) - pnorm((z - a) / sigma)) / (2.0 * a))


def _cdf_bhatt(x, mu, sigma, a, thrown):
    total = _nan_sum(x, mu, sigma, a)
    if total is not None:
        return total
    if sigma < 0.0 or a < 0.0:
        return _warn_nan(thrown)
    if math.isinf(x) and x < 0.0:
        return 0.0
    if math.isinf(x) and x > 0.0:
        return 1.0
    if sigma == 0.0:
        return _punif(x, mu - a, mu + a)
    if a == 0.0:
        return pnorm(x, mu, sigma)

    def g(z):
        return z * pnorm(z) + dnorm(z)

    z = x - mu
    return sigma / (2.0 * a) * (g((z + a) / sigma) - g((z - a) / sigma))


def _rng_bhatt(mu, sigma, a, thrown):
    if math.isnan(mu) or math.isnan(sigma) or math.isnan(a) or sigma < 0.0 or a < 0.0:
        return _warn_nan(thrown)
    if sigma == 0.0:
        return runif(mu - a, mu + a)
    if a == 0.0:
        return mu + sigma * norm_rand()
    return runif(-a, a) + norm_rand() * sigma + mu


def dbhatt(x, mu=0, sigma=1, a=None, log=False):
    if a is None:
        a = sigma
    return density(log, _logpdf_bhatt, x, mu, sigma, a)


def pbhatt(q, mu=0, sigma=1, a=None, lower_tail=True, log_p=False):
    if a is None:
        a = sigma
    return probability(lower_tail, log_p, _cdf_bhatt, q, mu, sigma, a)


def rbhatt(n, mu=0, sigma=1, a=None):
    if a is None:
        a = sigma
    return generate(n, _rng_bhatt, mu, sigma, a)


# --- Truncated normal --------------------------------------------------------


def _logpdf_tnorm(x, mu, sigma, a, b, thrown):
    total = _nan_sum(x, mu, sigma, a, b)
    if total is not None:
        return total
    if sigma <= 0.0 or b <= a:
        return _warn_nan(thrown)
    if a == -math.inf and b == math.inf:
        return dnorm(x, mu, sigma, log=True)
    if x > a and x < b:
        phi_a = pnorm((a - mu) / sigma)
        phi_b = pnorm((b - mu) / sigma)
        return _log_pos(
            math.exp(-((x - mu) * (x - mu)) / (2.0 * sigma * sigma))
            / (_SQRT_2PI * sigma * (phi_b - phi_a))
        )
    return -math.inf


def _cdf_tnorm(x, mu, sigma, a, b, thrown):
    total = _nan_sum(x, mu, sigma, a, b)
    if total is not None:
        return total
    if sigma <= 0.0 or b <= a:
        return _warn_nan(thrown)
    if a == -math.inf and b == math.inf:
        return pnorm(x, mu, sigma)
    if x > a and x < b:
        phi_x = pnorm((x - mu) / sigma)
        phi_a = pnorm((a - mu) / sigma)
        phi_b = pnorm((b - mu) / sigma)
        return (phi_x - phi_a) / (phi_b - phi_a)
    if x >= b:
        return 1.0
    return 0.0


def _invcdf_tnorm(p, mu, sigma, a, b, thrown):
    total = _nan_sum(p, mu, sigma, a, b)
    if total is not None:
        return total
    if sigma <= 0.0 or b <= a or not _prob_ok(p):
        return _warn_nan(thrown)
    if a == -math.inf and b == math.inf:
        return qnorm(p, mu, sigma)
    phi_a = pnorm((a - mu) / sigma)
    phi_b = pnorm((b - mu) / sigma)
    return qnorm(phi_a + p * (phi_b - phi_a)) * sigma + mu


def _rng_tnorm(mu, sigma, a, b, thrown):
    if (
        math.isnan(mu)
        or math.isnan(sigma)
        or math.isnan(a)
        or math.isnan(b)
        or sigma <= 0.0
        or b <= a
    ):
        return _warn_nan(thrown)
    if a == -math.inf and b == math.inf:
        return mu + sigma * norm_rand()
    za = (a - mu) / sigma
    zb = (b - mu) / sigma
    za_sq = za * za
    zb_sq = zb * zb
    if abs(za) <= 1e-16 and zb == math.inf:
        r = norm_rand()
        if r < 0.0:
            r = -r
    elif za == math.inf and abs(zb) <= 1e-16:
        r = norm_rand()
        if r > 0.0:
            r = -r
    elif (za < 0.0 and zb == math.inf) or (za == -math.inf and zb > 0.0) or (
        za != math.inf
        and zb != math.inf
        and za < 0.0
        and zb > 0.0
        and zb - za > _SQRT_2PI
    ):
        while True:
            r = norm_rand()
            if r >= za and r <= zb:
                break
    elif za >= 0.0 and (
        zb
        > za
        + 2.0
        * _SQRT_E
        / (za + math.sqrt(za_sq + 4.0))
        * math.exp((za * 2.0 - za * math.sqrt(za_sq + 4.0)) / 4.0)
    ):
        aa = (za + math.sqrt(za_sq + 4.0)) / 2.0
        while True:
            r = exp_rand() / aa + za
            u = unif()
            if u <= math.exp(-((r - aa) * (r - aa)) / 2.0) and r <= zb:
                break
    elif zb <= 0.0 and (
        -za
        > -zb
        + 2.0
        * _SQRT_E
        / (-zb + math.sqrt(zb_sq + 4.0))
        * math.exp((zb * 2.0 + zb * math.sqrt(zb_sq + 4.0)) / 4.0)
    ):
        aa = (-zb + math.sqrt(zb_sq + 4.0)) / 2.0
        while True:
            r = exp_rand() / aa - zb
            u = unif()
            if u <= math.exp(-((r - aa) * (r - aa)) / 2.0) and r <= -za:
                r = -r
                break
    elif 0.0 < za:
        while True:
            r = runif(za, zb)
            u = unif()
            if u <= math.exp((za_sq - r * r) / 2.0):
                break
    elif zb < 0.0:
        while True:
            r = runif(za, zb)
            u = unif()
            if u <= math.exp((zb_sq - r * r) / 2.0):
                break
    else:
        while True:
            r = runif(za, zb)
            u = unif()
            if u <= math.exp(-(r * r) / 2.0):
                break
    return mu + sigma * r


def dtnorm(x, mean=0, sd=1, a=-math.inf, b=math.inf, log=False):
    return density(log, _logpdf_tnorm, x, mean, sd, a, b)


def ptnorm(q, mean=0, sd=1, a=-math.inf, b=math.inf, lower_tail=True, log_p=False):
    return probability(lower_tail, log_p, _cdf_tnorm, q, mean, sd, a, b)


def qtnorm(p, mean=0, sd=1, a=-math.inf, b=math.inf, lower_tail=True, log_p=False):
    return quantile(lower_tail, log_p, _invcdf_tnorm, p, mean, sd, a, b)


def rtnorm(n, mean=0, sd=1, a=-math.inf, b=math.inf):
    return generate(n, _rng_tnorm, mean, sd, a, b)


# --- Shifted Gompertz --------------------------------------------------------


def _logpdf_sgomp(x, b, eta, thrown):
    total = _nan_sum(x, b, eta)
    if total is not None:
        return total
    if b <= 0.0 or eta <= 0.0:
        return _warn_nan(thrown)
    if x < 0.0 or not math.isfinite(x):
        return -math.inf
    ebx = math.exp(-b * x)
    return math.log(b) + _log(ebx) - eta * ebx + _log1p(eta * (1.0 - ebx))


def _cdf_sgomp(x, b, eta, thrown):
    total = _nan_sum(x, b, eta)
    if total is not None:
        return total
    if b <= 0.0 or eta <= 0.0:
        return _warn_nan(thrown)
    if x < 0.0:
        return 0.0
    if math.isinf(x) and x > 0.0:
        return 1.0
    ebx = math.exp(-b * x)
    return math.exp(_log1p(-ebx) - eta * ebx)


def _rng_sgomp(b, eta, thrown):
    if math.isnan(b) or math.isnan(eta) or b <= 0.0 or eta <= 0.0:
        return _warn_nan(thrown)
    u = exp_rand()
    v = exp_rand()
    rg = -_log(u / eta) / b
    re = v / b
    if rg > re:
        return rg
    return re


def dsgomp(x, b, eta, log=False):
    return density(log, _logpdf_sgomp, x, b, eta)


def psgomp(q, b, eta, lower_tail=True, log_p=False):
    return probability(lower_tail, log_p, _cdf_sgomp, q, b, eta)


def rsgomp(n, b, eta):
    return generate(n, _rng_sgomp, b, eta)
