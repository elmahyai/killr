"""Closed-form extraDistr families.

Scalar functions follow the C++ in the CRAN sources. The vector helpers apply
log, lower.tail, and log.p. Lomax's R argument lambda is lambda_.
"""

import math

import numpy as np

from extradistr._rng import exp_rand, rng_sign, unif
from extradistr._vec import density, generate, probability, quantile

_LOG2 = math.log(2.0)
_MISSING = object()


def _sum(*values):
    total = values[0]
    for value in values[1:]:
        total += value
    return total


def _any_nan(*values):
    return any(math.isnan(value) for value in values)


def _exp(x):
    if math.isnan(x):
        return math.nan
    try:
        return math.exp(x)
    except OverflowError:
        return math.inf


def _log(x):
    if math.isnan(x):
        return math.nan
    if x == 0.0:
        return -math.inf
    try:
        return math.log(x)
    except ValueError:
        return math.nan


def _log1p(x):
    if math.isnan(x):
        return math.nan
    try:
        return math.log1p(x)
    except ValueError:
        return math.nan
    except OverflowError:
        return math.inf


def _sqrt(x):
    if math.isnan(x):
        return math.nan
    try:
        return math.sqrt(x)
    except ValueError:
        return math.nan


def _pow(base, exponent):
    if math.isnan(base) or math.isnan(exponent):
        return math.nan
    if base == 0.0:
        if exponent == 0.0:
            return 1.0
        if exponent < 0.0:
            return math.inf
        return 0.0
    try:
        return math.pow(base, exponent)
    except ValueError:
        return math.nan
    except OverflowError:
        return math.inf if exponent > 0.0 else 0.0


def _valid_prob(p):
    return 0.0 <= p <= 1.0


def _midpoint(a, b):
    left = np.asarray(a, dtype=float).reshape(-1)
    right = np.asarray(b, dtype=float).reshape(-1)
    if left.size == 1 and right.size == 1:
        return float((left[0] + right[0]) / 2.0)
    n = max(left.size, right.size)
    if left.size != n:
        left = np.resize(left, n)
    if right.size != n:
        right = np.resize(right, n)
    return (left + right) / 2.0


def _peak(a, b, c):
    if c is _MISSING:
        return _midpoint(a, b)
    return c


# --- Laplace -----------------------------------------------------------------

def _dlaplace(x, mu, sigma, thrown):
    if _any_nan(x, mu, sigma):
        return _sum(x, mu, sigma)
    if sigma <= 0.0:
        thrown[0] = True
        return math.nan
    z = abs(x - mu) / sigma
    return -z - _LOG2 - math.log(sigma)


def _plaplace(x, mu, sigma, thrown):
    if _any_nan(x, mu, sigma):
        return _sum(x, mu, sigma)
    if sigma <= 0.0:
        thrown[0] = True
        return math.nan
    z = (x - mu) / sigma
    if x < mu:
        return _exp(z - _LOG2)
    return 1.0 - _exp(-z - _LOG2)


def _qlaplace(p, mu, sigma, thrown):
    if _any_nan(p, mu, sigma):
        return _sum(p, mu, sigma)
    if sigma <= 0.0 or not _valid_prob(p):
        thrown[0] = True
        return math.nan
    if p < 0.5:
        return mu + sigma * _log(2.0 * p)
    return mu - sigma * _log(2.0 * (1.0 - p))


def _rlaplace(mu, sigma, thrown):
    if _any_nan(mu, sigma) or sigma <= 0.0:
        thrown[0] = True
        return math.nan
    return exp_rand() * rng_sign() * sigma + mu


def dlaplace(x, mu=0, sigma=1, log=False):
    return density(log, _dlaplace, x, mu, sigma)


def plaplace(q, mu=0, sigma=1, lower_tail=True, log_p=False):
    return probability(lower_tail, log_p, _plaplace, q, mu, sigma)


def qlaplace(p, mu=0, sigma=1, lower_tail=True, log_p=False):
    return quantile(lower_tail, log_p, _qlaplace, p, mu, sigma)


def rlaplace(n, mu=0, sigma=1):
    return generate(n, _rlaplace, mu, sigma)


# --- Pareto ------------------------------------------------------------------

def _dpareto(x, a, b, thrown):
    if _any_nan(x, a, b):
        return _sum(x, a, b)
    if a <= 0.0 or b <= 0.0:
        thrown[0] = True
        return math.nan
    if x < b:
        return -math.inf
    return math.log(a) + math.log(b) * a - math.log(x) * (a + 1.0)


def _ppareto(x, a, b, thrown):
    if _any_nan(x, a, b):
        return _sum(x, a, b)
    if a <= 0.0 or b <= 0.0:
        thrown[0] = True
        return math.nan
    if x < b:
        return 0.0
    return 1.0 - _pow(b / x, a)


def _qpareto(p, a, b, thrown):
    if _any_nan(p, a, b):
        return _sum(p, a, b)
    if a <= 0.0 or b <= 0.0 or not _valid_prob(p):
        thrown[0] = True
        return math.nan
    return b / _pow(1.0 - p, 1.0 / a)


def _rpareto(a, b, thrown):
    if _any_nan(a, b) or a <= 0.0 or b <= 0.0:
        thrown[0] = True
        return math.nan
    return b / _pow(unif(), 1.0 / a)


def dpareto(x, a=1, b=1, log=False):
    return density(log, _dpareto, x, a, b)


def ppareto(q, a=1, b=1, lower_tail=True, log_p=False):
    return probability(lower_tail, log_p, _ppareto, q, a, b)


def qpareto(p, a=1, b=1, lower_tail=True, log_p=False):
    return quantile(lower_tail, log_p, _qpareto, p, a, b)


def rpareto(n, a=1, b=1):
    return generate(n, _rpareto, a, b)


# --- Rayleigh ----------------------------------------------------------------

def _drayleigh(x, sigma, thrown):
    if _any_nan(x, sigma):
        return _sum(x, sigma)
    if sigma <= 0.0:
        thrown[0] = True
        return math.nan
    if x <= 0.0 or not math.isfinite(x):
        return -math.inf
    lsigsq = 2.0 * math.log(sigma)
    lxsq = 2.0 * math.log(x)
    return math.log(x) - lsigsq - _exp(lxsq - _LOG2 - lsigsq)


def _prayleigh(x, sigma, thrown):
    if _any_nan(x, sigma):
        return _sum(x, sigma)
    if sigma <= 0.0:
        thrown[0] = True
        return math.nan
    if x < 0.0:
        return 0.0
    if not math.isfinite(x):
        return 1.0
    return 1.0 - _exp(-(x * x) / (2.0 * (sigma * sigma)))


def _qrayleigh(p, sigma, thrown):
    if _any_nan(p, sigma):
        return _sum(p, sigma)
    if not _valid_prob(p) or sigma <= 0.0:
        thrown[0] = True
        return math.nan
    return _sqrt(-2.0 * (sigma * sigma) * _log(1.0 - p))


def _rrayleigh(sigma, thrown):
    if _any_nan(sigma) or sigma <= 0.0:
        thrown[0] = True
        return math.nan
    return _sqrt(-2.0 * (sigma * sigma) * _log(unif()))


def drayleigh(x, sigma=1, log=False):
    return density(log, _drayleigh, x, sigma)


def prayleigh(q, sigma=1, lower_tail=True, log_p=False):
    return probability(lower_tail, log_p, _prayleigh, q, sigma)


def qrayleigh(p, sigma=1, lower_tail=True, log_p=False):
    return quantile(lower_tail, log_p, _qrayleigh, p, sigma)


def rrayleigh(n, sigma=1):
    return generate(n, _rrayleigh, sigma)


# --- Lomax -------------------------------------------------------------------

def _dlomax(x, lambda_, kappa, thrown):
    if _any_nan(x, lambda_, kappa):
        return _sum(x, lambda_, kappa)
    if lambda_ <= 0.0 or kappa <= 0.0:
        thrown[0] = True
        return math.nan
    if x <= 0.0:
        return -math.inf
    return math.log(lambda_) + math.log(kappa) - _log1p(lambda_ * x) * (kappa + 1.0)


def _plomax(x, lambda_, kappa, thrown):
    if _any_nan(x, lambda_, kappa):
        return _sum(x, lambda_, kappa)
    if lambda_ <= 0.0 or kappa <= 0.0:
        thrown[0] = True
        return math.nan
    if x <= 0.0:
        return 0.0
    return 1.0 - _exp(_log1p(lambda_ * x) * (-kappa))


def _qlomax(p, lambda_, kappa, thrown):
    if _any_nan(p, lambda_, kappa):
        return _sum(p, lambda_, kappa)
    if lambda_ <= 0.0 or kappa <= 0.0 or not _valid_prob(p):
        thrown[0] = True
        return math.nan
    return (_pow(1.0 - p, -1.0 / kappa) - 1.0) / lambda_


def _rlomax(lambda_, kappa, thrown):
    if _any_nan(lambda_, kappa) or lambda_ <= 0.0 or kappa <= 0.0:
        thrown[0] = True
        return math.nan
    return (_pow(unif(), -1.0 / kappa) - 1.0) / lambda_


def dlomax(x, lambda_, kappa, log=False):
    return density(log, _dlomax, x, lambda_, kappa)


def plomax(q, lambda_, kappa, lower_tail=True, log_p=False):
    return probability(lower_tail, log_p, _plomax, q, lambda_, kappa)


def qlomax(p, lambda_, kappa, lower_tail=True, log_p=False):
    return quantile(lower_tail, log_p, _qlomax, p, lambda_, kappa)


def rlomax(n, lambda_, kappa):
    return generate(n, _rlomax, lambda_, kappa)


# --- Kumaraswamy -------------------------------------------------------------

def _dkumar(x, a, b, thrown):
    if _any_nan(x, a, b):
        return _sum(x, a, b)
    if a <= 0.0 or b <= 0.0:
        thrown[0] = True
        return math.nan
    if x < 0.0 or x > 1.0:
        return -math.inf
    pdf = a * b * _pow(x, a - 1.0) * _pow(1.0 - _pow(x, a), b - 1.0)
    return _log(pdf)


def _pkumar(x, a, b, thrown):
    if _any_nan(x, a, b):
        return _sum(x, a, b)
    if a <= 0.0 or b <= 0.0:
        thrown[0] = True
        return math.nan
    if x < 0.0:
        return 0.0
    if x >= 1.0:
        return 1.0
    return 1.0 - _pow(1.0 - _pow(x, a), b)


def _qkumar(p, a, b, thrown):
    if _any_nan(p, a, b):
        return _sum(p, a, b)
    if a <= 0.0 or b <= 0.0 or not _valid_prob(p):
        thrown[0] = True
        return math.nan
    return _pow(1.0 - _pow(1.0 - p, 1.0 / b), 1.0 / a)


def _rkumar(a, b, thrown):
    if _any_nan(a, b) or a <= 0.0 or b <= 0.0:
        thrown[0] = True
        return math.nan
    return _pow(1.0 - _pow(unif(), 1.0 / b), 1.0 / a)


def dkumar(x, a=1, b=1, log=False):
    return density(log, _dkumar, x, a, b)


def pkumar(q, a=1, b=1, lower_tail=True, log_p=False):
    return probability(lower_tail, log_p, _pkumar, q, a, b)


def qkumar(p, a=1, b=1, lower_tail=True, log_p=False):
    return quantile(lower_tail, log_p, _qkumar, p, a, b)


def rkumar(n, a=1, b=1):
    return generate(n, _rkumar, a, b)


# --- Frechet -----------------------------------------------------------------

def _dfrechet(x, lambda_, mu, sigma, thrown):
    if _any_nan(x, lambda_, mu, sigma):
        return _sum(x, lambda_, mu, sigma)
    if lambda_ <= 0.0 or sigma <= 0.0:
        thrown[0] = True
        return math.nan
    if x <= mu:
        return -math.inf
    z = (x - mu) / sigma
    return (
        math.log(lambda_)
        - math.log(sigma)
        + math.log(z) * (-1.0 - lambda_)
        - _exp(math.log(z) * -lambda_)
    )


def _pfrechet(x, lambda_, mu, sigma, thrown):
    if _any_nan(x, lambda_, mu, sigma):
        return _sum(x, lambda_, mu, sigma)
    if lambda_ <= 0.0 or sigma <= 0.0:
        thrown[0] = True
        return math.nan
    if x <= mu:
        return 0.0
    z = (x - mu) / sigma
    return _exp(-_pow(z, -lambda_))


def _qfrechet(p, lambda_, mu, sigma, thrown):
    if _any_nan(p, lambda_, mu, sigma):
        return _sum(p, lambda_, mu, sigma)
    if lambda_ <= 0.0 or sigma <= 0.0 or not _valid_prob(p):
        thrown[0] = True
        return math.nan
    if p == 1.0:
        return math.inf
    return mu + sigma * _pow(-_log(p), -1.0 / lambda_)


def _rfrechet(lambda_, mu, sigma, thrown):
    if _any_nan(lambda_, mu, sigma) or lambda_ <= 0.0 or sigma <= 0.0:
        thrown[0] = True
        return math.nan
    return mu + sigma * _pow(-_log(unif()), -1.0 / lambda_)


def dfrechet(x, lambda_=1, mu=0, sigma=1, log=False):
    return density(log, _dfrechet, x, lambda_, mu, sigma)


def pfrechet(q, lambda_=1, mu=0, sigma=1, lower_tail=True, log_p=False):
    return probability(lower_tail, log_p, _pfrechet, q, lambda_, mu, sigma)


def qfrechet(p, lambda_=1, mu=0, sigma=1, lower_tail=True, log_p=False):
    return quantile(lower_tail, log_p, _qfrechet, p, lambda_, mu, sigma)


def rfrechet(n, lambda_=1, mu=0, sigma=1):
    return generate(n, _rfrechet, lambda_, mu, sigma)


# --- Gumbel ------------------------------------------------------------------

def _dgumbel(x, mu, sigma, thrown):
    if _any_nan(x, mu, sigma):
        return _sum(x, mu, sigma)
    if sigma <= 0.0:
        thrown[0] = True
        return math.nan
    if not math.isfinite(x):
        return -math.inf
    z = (x - mu) / sigma
    return -(z + _exp(-z)) - math.log(sigma)


def _pgumbel(x, mu, sigma, thrown):
    if _any_nan(x, mu, sigma):
        return _sum(x, mu, sigma)
    if sigma <= 0.0:
        thrown[0] = True
        return math.nan
    z = (x - mu) / sigma
    return _exp(-_exp(-z))


def _qgumbel(p, mu, sigma, thrown):
    if _any_nan(p, mu, sigma):
        return _sum(p, mu, sigma)
    if sigma <= 0.0 or not _valid_prob(p):
        thrown[0] = True
        return math.nan
    return mu - sigma * _log(-_log(p))


def _rgumbel(mu, sigma, thrown):
    if _any_nan(mu, sigma) or sigma <= 0.0:
        thrown[0] = True
        return math.nan
    return mu - sigma * _log(exp_rand())


def dgumbel(x, mu=0, sigma=1, log=False):
    return density(log, _dgumbel, x, mu, sigma)


def pgumbel(q, mu=0, sigma=1, lower_tail=True, log_p=False):
    return probability(lower_tail, log_p, _pgumbel, q, mu, sigma)


def qgumbel(p, mu=0, sigma=1, lower_tail=True, log_p=False):
    return quantile(lower_tail, log_p, _qgumbel, p, mu, sigma)


def rgumbel(n, mu=0, sigma=1):
    return generate(n, _rgumbel, mu, sigma)


# --- Gompertz ----------------------------------------------------------------

def _dgompertz(x, a, b, thrown):
    if _any_nan(x, a, b):
        return _sum(x, a, b)
    if a <= 0.0 or b <= 0.0:
        thrown[0] = True
        return math.nan
    if x < 0.0 or not math.isfinite(x):
        return -math.inf
    return math.log(a) + (b * x - a / b * (_exp(b * x) - 1.0))


def _pgompertz(x, a, b, thrown):
    if _any_nan(x, a, b):
        return _sum(x, a, b)
    if a <= 0.0 or b <= 0.0:
        thrown[0] = True
        return math.nan
    if x < 0.0:
        return 0.0
    if not math.isfinite(x):
        return 1.0
    return 1.0 - _exp(-a / b * (_exp(b * x) - 1.0))


def _qgompertz(p, a, b, thrown):
    if _any_nan(p, a, b):
        return _sum(p, a, b)
    if a <= 0.0 or b <= 0.0 or not _valid_prob(p):
        thrown[0] = True
        return math.nan
    return _log(1.0 - b / a * _log(1.0 - p)) / b


def _rgompertz(a, b, thrown):
    if _any_nan(a, b) or a <= 0.0 or b <= 0.0:
        thrown[0] = True
        return math.nan
    return _log(1.0 - b / a * _log(unif())) / b


def dgompertz(x, a=1, b=1, log=False):
    return density(log, _dgompertz, x, a, b)


def pgompertz(q, a=1, b=1, lower_tail=True, log_p=False):
    return probability(lower_tail, log_p, _pgompertz, q, a, b)


def qgompertz(p, a=1, b=1, lower_tail=True, log_p=False):
    return quantile(lower_tail, log_p, _qgompertz, p, a, b)


def rgompertz(n, a=1, b=1):
    return generate(n, _rgompertz, a, b)


# --- Power -------------------------------------------------------------------

def _dpower(x, alpha, beta, thrown):
    if _any_nan(x, alpha, beta):
        return _sum(x, alpha, beta)
    if alpha <= 0.0 or beta <= 0.0:
        thrown[0] = True
        return math.nan
    if x <= 0.0 or x >= alpha:
        return -math.inf
    return math.log(beta) + math.log(x) * (beta - 1.0) - math.log(alpha) * beta


def _ppower(x, alpha, beta, thrown):
    if _any_nan(x, alpha, beta):
        return _sum(x, alpha, beta)
    if alpha <= 0.0 or beta <= 0.0:
        thrown[0] = True
        return math.nan
    if x <= 0.0:
        return 0.0
    if x >= alpha:
        return 1.0
    return _exp(math.log(x) * beta - math.log(alpha) * beta)


def _qpower(p, alpha, beta, thrown):
    if _any_nan(p, alpha, beta):
        return _sum(p, alpha, beta)
    if alpha <= 0.0 or beta <= 0.0 or not _valid_prob(p):
        thrown[0] = True
        return math.nan
    return alpha * _pow(p, 1.0 / beta)


def _rpower(alpha, beta, thrown):
    if _any_nan(alpha, beta) or alpha <= 0.0 or beta <= 0.0:
        thrown[0] = True
        return math.nan
    return alpha * _pow(unif(), 1.0 / beta)


def dpower(x, alpha, beta, log=False):
    return density(log, _dpower, x, alpha, beta)


def ppower(q, alpha, beta, lower_tail=True, log_p=False):
    return probability(lower_tail, log_p, _ppower, q, alpha, beta)


def qpower(p, alpha, beta, lower_tail=True, log_p=False):
    return quantile(lower_tail, log_p, _qpower, p, alpha, beta)


def rpower(n, alpha, beta):
    return generate(n, _rpower, alpha, beta)


# --- Generalized Pareto ------------------------------------------------------

def _dgpd(x, mu, sigma, xi, thrown):
    if _any_nan(x, mu, sigma, xi):
        return _sum(x, mu, sigma, xi)
    if sigma <= 0.0:
        thrown[0] = True
        return math.nan
    z = (x - mu) / sigma
    if z > 0.0 and 1.0 + xi * z > 0.0:
        if xi != 0.0:
            return _log1p(xi * z) * (-(xi + 1.0) / xi) - math.log(sigma)
        return -z - math.log(sigma)
    return -math.inf


def _pgpd(x, mu, sigma, xi, thrown):
    if _any_nan(x, mu, sigma, xi):
        return _sum(x, mu, sigma, xi)
    if sigma <= 0.0:
        thrown[0] = True
        return math.nan
    z = (x - mu) / sigma
    if xi != 0.0:
        if z > 0.0 and 1.0 + xi * z > 0.0:
            return 1.0 - _exp(_log1p(xi * z) * (-1.0 / xi))
        if z > 0.0 and z >= -1.0 / xi:
            return 1.0
        return 0.0
    if z > 0.0 and 1.0 + xi * z > 0.0:
        return 1.0 - _exp(-z)
    if z > 0.0 and z >= -1.0 / xi:
        return 1.0
    return 0.0


def _qgpd(p, mu, sigma, xi, thrown):
    if _any_nan(p, mu, sigma, xi):
        return _sum(p, mu, sigma, xi)
    if sigma <= 0.0 or not _valid_prob(p):
        thrown[0] = True
        return math.nan
    if xi != 0.0:
        return mu + sigma * (_pow(1.0 - p, -xi) - 1.0) / xi
    return mu - sigma * _log(1.0 - p)


def _rgpd(mu, sigma, xi, thrown):
    if _any_nan(mu, sigma, xi) or sigma <= 0.0:
        thrown[0] = True
        return math.nan
    if xi != 0.0:
        return mu + sigma * (_pow(unif(), -xi) - 1.0) / xi
    return mu + sigma * exp_rand()


def dgpd(x, mu=0, sigma=1, xi=0, log=False):
    return density(log, _dgpd, x, mu, sigma, xi)


def pgpd(q, mu=0, sigma=1, xi=0, lower_tail=True, log_p=False):
    return probability(lower_tail, log_p, _pgpd, q, mu, sigma, xi)


def qgpd(p, mu=0, sigma=1, xi=0, lower_tail=True, log_p=False):
    return quantile(lower_tail, log_p, _qgpd, p, mu, sigma, xi)


def rgpd(n, mu=0, sigma=1, xi=0):
    return generate(n, _rgpd, mu, sigma, xi)


# --- Generalized extreme value -----------------------------------------------

def _dgev(x, mu, sigma, xi, thrown):
    if _any_nan(x, mu, sigma, xi):
        return _sum(x, mu, sigma, xi)
    if sigma <= 0.0:
        thrown[0] = True
        return math.nan
    z = (x - mu) / sigma
    if 1.0 + xi * z > 0.0:
        if xi != 0.0:
            return (
                -math.log(sigma)
                + _log1p(xi * z) * (-1.0 - (1.0 / xi))
                - _exp(_log1p(xi * z) * (-1.0 / xi))
            )
        return -math.log(sigma) - z - _exp(-z)
    return -math.inf


def _pgev(x, mu, sigma, xi, thrown):
    if _any_nan(x, mu, sigma, xi):
        return _sum(x, mu, sigma, xi)
    if sigma <= 0.0:
        thrown[0] = True
        return math.nan
    z = (x - mu) / sigma
    if 1.0 + xi * z > 0.0:
        if xi != 0.0:
            return _exp(-_exp(_log1p(xi * z) * (-1.0 / xi)))
        return _exp(-_exp(-z))
    if z > 0.0 and z >= -1.0 / xi:
        return 1.0
    return 0.0


def _qgev(p, mu, sigma, xi, thrown):
    if _any_nan(p, mu, sigma, xi):
        return _sum(p, mu, sigma, xi)
    if sigma <= 0.0 or not _valid_prob(p):
        thrown[0] = True
        return math.nan
    if p == 1.0:
        return math.inf
    if xi != 0.0:
        return mu - sigma / xi * (1.0 - _pow(-_log(p), -xi))
    return mu - sigma * _log(-_log(p))


def _rgev(mu, sigma, xi, thrown):
    if _any_nan(mu, sigma, xi) or sigma <= 0.0:
        thrown[0] = True
        return math.nan
    u = exp_rand()
    if xi != 0.0:
        return mu + sigma / xi * (_pow(u, -xi) - 1.0)
    return mu - sigma * _log(u)


def dgev(x, mu=0, sigma=1, xi=0, log=False):
    return density(log, _dgev, x, mu, sigma, xi)


def pgev(q, mu=0, sigma=1, xi=0, lower_tail=True, log_p=False):
    return probability(lower_tail, log_p, _pgev, q, mu, sigma, xi)


def qgev(p, mu=0, sigma=1, xi=0, lower_tail=True, log_p=False):
    return quantile(lower_tail, log_p, _qgev, p, mu, sigma, xi)


def rgev(n, mu=0, sigma=1, xi=0):
    return generate(n, _rgev, mu, sigma, xi)


# --- Triangular --------------------------------------------------------------

def _dtriang(x, a, b, c, thrown):
    if _any_nan(x, a, b, c):
        return _sum(x, a, b, c)
    if a > c or c > b or a == b:
        thrown[0] = True
        return math.nan
    if x < a or x > b:
        return -math.inf
    if x < c:
        return _LOG2 + math.log(x - a) - math.log(b - a) - math.log(c - a)
    if x > c:
        return _LOG2 + math.log(b - x) - math.log(b - a) - math.log(b - c)
    return _LOG2 - math.log(b - a)


def _ptriang(x, a, b, c, thrown):
    if _any_nan(x, a, b, c):
        return _sum(x, a, b, c)
    if a > c or c > b or a == b:
        thrown[0] = True
        return math.nan
    if x < a:
        return 0.0
    if x >= b:
        return 1.0
    if x <= c:
        return _exp(math.log(x - a) * 2.0 - math.log(b - a) - math.log(c - a))
    return 1.0 - _exp(math.log(b - x) * 2.0 - math.log(b - a) - math.log(b - c))


def _qtriang(p, a, b, c, thrown):
    if _any_nan(p, a, b, c):
        return _sum(p, a, b, c)
    if a > c or c > b or a == b or not _valid_prob(p):
        thrown[0] = True
        return math.nan
    fc = (c - a) / (b - a)
    if p < fc:
        return a + _sqrt(p * (b - a) * (c - a))
    return b - _sqrt((1.0 - p) * (b - a) * (b - c))


def _rtriang(a, b, c, thrown):
    if _any_nan(a, b, c) or a > c or c > b or a == b:
        thrown[0] = True
        return math.nan
    span = b - a
    cc = (c - a) / span
    u = unif()
    v = unif()
    return ((1.0 - cc) * min(u, v) + cc * max(u, v)) * span + a


def dtriang(x, a=-1, b=1, c=_MISSING, log=False):
    return density(log, _dtriang, x, a, b, _peak(a, b, c))


def ptriang(q, a=-1, b=1, c=_MISSING, lower_tail=True, log_p=False):
    return probability(lower_tail, log_p, _ptriang, q, a, b, _peak(a, b, c))


def qtriang(p, a=-1, b=1, c=_MISSING, lower_tail=True, log_p=False):
    return quantile(lower_tail, log_p, _qtriang, p, a, b, _peak(a, b, c))


def rtriang(n, a=-1, b=1, c=_MISSING):
    return generate(n, _rtriang, a, b, _peak(a, b, c))
