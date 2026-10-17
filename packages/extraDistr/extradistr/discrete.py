"""Discrete families from extraDistr 1.10.0.5.

Densities go through ``_vec.density`` and return a log-density. The C++
quantile for ``qcat`` builds a transformed copy of ``p`` and then reads the
original vector, so ``lower_tail`` and ``log_p`` do not change ``qcat``.

``rbbinom``, ``rbnbinom``, ``rdlaplace``, ``rskellam``, ``rzib``, ``rzip``,
``rzinb``, ``rmnom``, ``rdirmnom``, ``rmvhyper`` (when the draw is not the
whole urn), ``rgpois``, and ``rdgamma`` call ``rbeta``, ``rbinom``, ``rpois``,
``rgamma``, ``rgeom``, ``rnbinom``, or ``rhyper``. Those stubs in ``_rgen``
raise ``NotImplementedError``. ``R::rhyper(white, black, draws)`` is one draw,
written here as ``rhyper(1, white, black, draws)``.
"""

import math
import warnings

import numpy as np
from boot.rng import unif_index

from extradistr._rgen import (
    rbeta,
    rbinom,
    rgamma,
    rgeom,
    rhyper,
    rnbinom,
    rpois,
)
from extradistr._rng import exp_rand, norm_rand, rng_sign, runif, unif
from extradistr._special import (
    bessel_i,
    dbinom,
    dnbinom,
    dpois,
    lbeta,
    lchoose,
    lgamma,
    pbinom,
    pgamma,
    pnorm,
    pnbinom,
    ppois,
    qbinom,
    qnbinom,
    qpois,
)
from extradistr._vec import as_vec, density, generate, probability, quantile

_INT_MAX = 2147483647
_builtin_min = min
_builtin_max = max

__all__ = [
    "dbbinom",
    "dbern",
    "dbnbinom",
    "dcat",
    "ddgamma",
    "ddirmnom",
    "ddlaplace",
    "ddnorm",
    "ddunif",
    "ddweibull",
    "dgpois",
    "dlgser",
    "dmnom",
    "dmvhyper",
    "dnhyper",
    "dskellam",
    "dtbinom",
    "dtpois",
    "dzib",
    "dzinb",
    "dzip",
    "pbbinom",
    "pbern",
    "pbnbinom",
    "pcat",
    "pdgamma",
    "pdlaplace",
    "pdnorm",
    "pdunif",
    "pdweibull",
    "pgpois",
    "plgser",
    "pnhyper",
    "ptbinom",
    "ptpois",
    "pzib",
    "pzinb",
    "pzip",
    "qbern",
    "qcat",
    "qdunif",
    "qdweibull",
    "qlgser",
    "qnhyper",
    "qtbinom",
    "qtpois",
    "qzib",
    "qzinb",
    "qzip",
    "rbbinom",
    "rbern",
    "rbnbinom",
    "rcat",
    "rcatlp",
    "rdgamma",
    "rdirmnom",
    "rdlaplace",
    "rdnorm",
    "rdunif",
    "rdweibull",
    "rgpois",
    "rlgser",
    "rmnom",
    "rmvhyper",
    "rnhyper",
    "rsign",
    "rskellam",
    "rtbinom",
    "rtpois",
    "rzib",
    "rzinb",
    "rzip",
]


def _nans(*values):
    return any(math.isnan(value) for value in values)


def _sum(*values):
    total = 0.0
    for value in values:
        total += value
    return total


def _floor(x):
    if math.isnan(x) or math.isinf(x):
        return x
    return float(math.floor(x))


def _ceil(x):
    if math.isnan(x) or math.isinf(x):
        return x
    return float(math.ceil(x))


def _log(x):
    if math.isnan(x) or x < 0.0:
        return math.nan
    if x == 0.0:
        return -math.inf
    return math.log(x)


def _exp(x):
    if math.isnan(x):
        return math.nan
    if x > 709.782712893384:
        return math.inf
    if x < -745.1332191019412:
        return 0.0
    return math.exp(x)


def _pow(base, exp):
    if math.isnan(base) or math.isnan(exp):
        return math.nan
    try:
        return math.pow(base, exp)
    except ValueError:
        return math.nan
    except OverflowError:
        return math.inf if exp > 0.0 else 0.0


def _div(num, den):
    if math.isnan(num) or math.isnan(den):
        return math.nan
    if den == 0.0:
        if num == 0.0:
            return math.nan
        return math.copysign(math.inf, num)
    return num / den


def _as_log(prob):
    if math.isnan(prob):
        return prob
    if prob == 0.0:
        return -math.inf
    if prob < 0.0:
        return math.nan
    return math.log(prob)


def _log1p(x):
    if x == -1.0:
        return -math.inf
    if x < -1.0 or math.isnan(x):
        return math.nan
    return math.log1p(x)


def is_integer(x, warn=True):
    if math.isnan(x):
        return False
    if math.isinf(x):
        return True
    if x != math.floor(x):
        if warn:
            warnings.warn("non-integer: %f" % x)
        return False
    return True


def is_large_int(x):
    return x > _INT_MAX


def to_pos_int(x):
    if x < 0.0 or math.isnan(x):
        raise ValueError("value cannot be coerced to integer")
    if is_large_int(x):
        raise ValueError("value out of integer range")
    return int(x)


def trunc_p(x):
    if x < 0.0:
        return 0.0
    if x > 1.0:
        return 1.0
    return x


def _lfactorial(x):
    return lgamma(x + 1.0)


def _valid_prob(p):
    return 0.0 <= p <= 1.0


def _flat_n(n):
    if isinstance(n, bool):
        return np.asarray([float(n)], dtype=float)
    if isinstance(n, (list, tuple, np.ndarray)):
        return np.asarray(n, dtype=float).reshape(-1)
    return None


def _n_obs(n):
    """R's ``if (length(n) > 1) n <- length(n)``."""
    flat = _flat_n(n)
    if flat is None:
        return int(math.trunc(float(n)))
    if flat.size == 0:
        raise ValueError("invalid arguments")
    if flat.size > 1:
        return int(flat.size)
    return int(math.trunc(float(flat[0])))


def _n_first(n):
    """Rcpp ``as<int>`` of a numeric vector: the first element."""
    flat = _flat_n(n)
    if flat is None:
        return int(math.trunc(float(n)))
    if flat.size == 0:
        raise ValueError("invalid arguments")
    if flat.size != 1:
        warnings.warn("first element used of vector of length %d" % flat.size)
    return int(math.trunc(float(flat[0])))


def _recycle_len(*lengths):
    if any(length == 0 for length in lengths):
        return 0
    return _builtin_max(lengths)


def _as_matrix(value):
    """A vector is one row, matching ``matrix(x, nrow = 1)``."""
    array = np.asarray(value, dtype=float)
    if array.ndim == 0:
        return array.reshape(1, 1)
    if array.ndim == 1:
        return array.reshape(1, -1)
    if array.ndim != 2:
        raise TypeError("numeric argument expected")
    return np.array(array, dtype=float, copy=True)


def _finite_max_int(values):
    max_x = 0.0
    for value in values:
        if value > 0.0 and not is_large_int(value) and value > max_x:
            max_x = float(value)
    return max_x


def _scale_from(rate, scale, default_rate):
    if scale is None:
        if rate is None:
            rate = default_rate
        return 1.0 / as_vec(rate)
    return scale


def _gamma_conflict(rate, scale):
    if rate is None or scale is None:
        return
    rate0 = float(as_vec(rate)[0])
    scale0 = float(as_vec(scale)[0])
    if abs(rate0 * scale0 - 1.0) < 1e-15:
        warnings.warn("specify 'rate' or 'scale' but not both")
    else:
        raise ValueError("specify 'rate' or 'scale' but not both")


def _apply_labels(values, labels, k):
    if labels is None:
        return values
    labels = list(labels)
    if len(labels) != k:
        warnings.warn("Wrong number of labels.")
        return values
    out = np.empty(len(values), dtype=object)
    for i, value in enumerate(np.asarray(values, dtype=float).reshape(-1)):
        if math.isnan(value):
            out[i] = None
        else:
            out[i] = labels[int(value) - 1]
    return out


def _normalize_rows(mat, thrown):
    tab = np.array(mat, dtype=float, copy=True)
    for i in range(tab.shape[0]):
        total = 0.0
        for j in range(tab.shape[1]):
            total += tab[i, j]
            if math.isnan(total):
                break
            if tab[i, j] < 0.0:
                total = math.nan
                thrown[0] = True
                break
        with np.errstate(divide="ignore", invalid="ignore"):
            tab[i, :] /= total
    return tab


def _cumulative_rows(mat, thrown):
    tab = _normalize_rows(mat, thrown)
    if tab.shape[1]:
        np.cumsum(tab, axis=1, out=tab)
    return tab


def _revsort(values, index):
    """R ``revsort``: descending heapsort, permuting ``index``."""
    n = len(values)
    if n <= 1:
        return
    a = [0.0, *values]
    ib = [0, *index]
    left = (n >> 1) + 1
    right = n
    while True:
        if left > 1:
            left -= 1
            ra = a[left]
            ii = ib[left]
        else:
            ra = a[right]
            ii = ib[right]
            a[right] = a[1]
            ib[right] = ib[1]
            right -= 1
            if right == 1:
                a[1] = ra
                ib[1] = ii
                values[:] = a[1:]
                index[:] = ib[1:]
                return
        i = left
        j = left << 1
        while j <= right:
            if j < right and a[j] > a[j + 1]:
                j += 1
            if ra > a[j]:
                a[i] = a[j]
                ib[i] = ib[j]
                i = j
                j += i
            else:
                j = right + 1
        a[i] = ra
        ib[i] = ii


def _fixup_prob(prob):
    weights = [float(value) for value in prob]
    total = 0.0
    npos = 0
    for weight in weights:
        if not math.isfinite(weight):
            raise ValueError("NA in probability vector")
        if weight < 0.0:
            raise ValueError("negative probability")
        if weight > 0.0:
            npos += 1
            total += weight
    if npos == 0:
        raise ValueError("too few positive probabilities")
    return [weight / total for weight in weights]


def _prob_sample_replace(weights, size):
    n = len(weights)
    values = list(weights)
    perm = list(range(1, n + 1))
    _revsort(values, perm)
    for index in range(1, n):
        values[index] += values[index - 1]
    last = n - 1
    chosen = []
    for _ in range(size):
        draw = unif()
        slot = 0
        while slot < last and draw > values[slot]:
            slot += 1
        chosen.append(perm[slot])
    return chosen


def _walker_sample_replace(weights, size):
    n = len(weights)
    q = [weight * n for weight in weights]
    labels = [0] * n
    small = 0
    large = n
    alias = [0] * n
    for index in range(n):
        if q[index] < 1.0:
            labels[small] = index
            small += 1
        else:
            large -= 1
            labels[large] = index
    if small > 0 and large < n:
        for step in range(n - 1):
            small_index = labels[step]
            large_index = labels[large]
            alias[small_index] = large_index
            q[large_index] += q[small_index] - 1.0
            if q[large_index] < 1.0:
                large += 1
            if large >= n:
                break
    for index in range(n):
        q[index] += index
    chosen = []
    for _ in range(size):
        slot = unif_index(n)
        proposal = slot + unif()
        if proposal < q[slot]:
            chosen.append(slot + 1)
        else:
            chosen.append(alias[slot] + 1)
    return chosen


def _sample_int_prob(prob, size):
    """``sample.int(k, size, replace=TRUE, prob=prob)``, values 1..k."""
    weights = _fixup_prob(prob)
    n = len(weights)
    heavy = sum(1 for weight in weights if n * weight > 0.1)
    if heavy > 200:
        return _walker_sample_replace(weights, size)
    return _prob_sample_replace(weights, size)


def _one_rhyper(white, black, draws):
    value = rhyper(1, white, black, draws)
    if isinstance(value, (list, tuple, np.ndarray)):
        return float(np.asarray(value, dtype=float).reshape(-1)[0])
    return float(value)


# --- Bernoulli --------------------------------------------------------------


def dbern(x, prob=0.5, log=False):
    def fn(xx, pp, thrown):
        if _nans(xx, pp):
            return _sum(xx, pp)
        if not _valid_prob(pp):
            thrown[0] = True
            return math.nan
        if xx == 1.0:
            return _as_log(pp)
        if xx == 0.0:
            return _as_log(1.0 - pp)
        warnings.warn("improper x = %f" % xx)
        return -math.inf

    return density(log, fn, x, prob)


def pbern(q, prob=0.5, lower_tail=True, log_p=False):
    def fn(xx, pp, thrown):
        if _nans(xx, pp):
            return _sum(xx, pp)
        if not _valid_prob(pp):
            thrown[0] = True
            return math.nan
        if xx < 0.0:
            return 0.0
        if xx < 1.0:
            return 1.0 - pp
        return 1.0

    return probability(lower_tail, log_p, fn, q, prob)


def qbern(p, prob=0.5, lower_tail=True, log_p=False):
    def fn(pp, prob_, thrown):
        if _nans(pp, prob_):
            return _sum(pp, prob_)
        if not _valid_prob(prob_) or not _valid_prob(pp):
            thrown[0] = True
            return math.nan
        return 0.0 if pp <= (1.0 - prob_) else 1.0

    return quantile(lower_tail, log_p, fn, p, prob)


def rbern(n, prob=0.5):
    def fn(pp, thrown):
        if math.isnan(pp) or not _valid_prob(pp):
            thrown[0] = True
            return math.nan
        return 0.0 if unif() > pp else 1.0

    return generate(_n_obs(n), fn, prob)


# --- Beta-binomial ----------------------------------------------------------


def _logpmf_bbinom(k, n, alpha, beta, thrown):
    if _nans(k, n, alpha, beta):
        return _sum(k, n, alpha, beta)
    if alpha < 0.0 or beta < 0.0 or n < 0.0 or not is_integer(n, False):
        thrown[0] = True
        return math.nan
    if not is_integer(k) or k < 0.0 or k > n:
        return -math.inf
    return lchoose(n, k) + lbeta(k + alpha, n - k + beta) - lbeta(alpha, beta)


def _cdf_bbinom_table(k, n, alpha, beta):
    if k < 0.0 or k > n or alpha < 0.0 or beta < 0.0:
        raise ValueError("inadmissible values")
    ik = to_pos_int(k)
    p_tab = [0.0] * (ik + 1)
    bab = lbeta(alpha, beta)
    gxy = lgamma(alpha + beta + n)
    nck = 0.0
    gx = lgamma(alpha)
    gy = lgamma(beta + n)
    p_tab[0] = _exp(nck + gx + gy - gxy - bab)
    if ik < 1:
        return p_tab
    nck += _log(n)
    gx += _log(alpha)
    gy -= _log(n + beta - 1.0)
    p_tab[1] = p_tab[0] + _exp(nck + gx + gy - gxy - bab)
    if ik < 2:
        return p_tab
    for j in range(2, ik + 1):
        dj = float(j)
        nck += _log((n + 1.0 - dj) / dj)
        gx += _log(dj + alpha - 1.0)
        gy -= _log(n + beta - dj)
        p_tab[j] = p_tab[j - 1] + _exp(nck + gx + gy - gxy - bab)
    return p_tab


def dbbinom(x, size, alpha=1.0, beta=1.0, log=False):
    return density(log, _logpmf_bbinom, x, size, alpha, beta)


def pbbinom(q, size, alpha=1.0, beta=1.0, lower_tail=True, log_p=False):
    xv, sv, av, bv = as_vec(q), as_vec(size), as_vec(alpha), as_vec(beta)
    n = _recycle_len(len(xv), len(sv), len(av), len(bv))
    need = {}
    for i in range(n):
        xx = float(xv[i % len(xv)])
        ss = float(sv[i % len(sv)])
        aa = float(av[i % len(av)])
        bb = float(bv[i % len(bv)])
        if _nans(xx, ss, aa, bb):
            continue
        if aa <= 0.0 or bb <= 0.0 or ss < 0.0 or not is_integer(ss, False):
            continue
        if xx < 0.0 or xx >= ss or not math.isfinite(xx) or is_large_int(xx):
            continue
        key = (ss, aa, bb)
        if key not in need or xx > need[key]:
            need[key] = xx
    tables = {key: _cdf_bbinom_table(limit, *key) for key, limit in need.items()}

    def fn(xx, ss, aa, bb, thrown):
        if _nans(xx, ss, aa, bb):
            return _sum(xx, ss, aa, bb)
        if aa <= 0.0 or bb <= 0.0 or ss < 0.0 or not is_integer(ss, False):
            thrown[0] = True
            return math.nan
        if xx < 0.0:
            return 0.0
        if xx >= ss:
            return 1.0
        if is_large_int(xx):
            warnings.warn("NAs introduced by coercion to integer range")
            return math.nan
        return tables[(ss, aa, bb)][to_pos_int(xx)]

    return probability(lower_tail, log_p, fn, q, size, alpha, beta)


def rbbinom(n, size, alpha=1.0, beta=1.0):
    def fn(ss, aa, bb, thrown):
        if _nans(ss, aa, bb) or aa < 0.0 or bb < 0.0 or ss < 0.0 or not is_integer(ss, False):
            thrown[0] = True
            return math.nan
        prob = rbeta(aa, bb)
        return rbinom(ss, prob)

    return generate(_n_obs(n), fn, size, alpha, beta)


# --- Beta-negative binomial -------------------------------------------------


def _logpmf_bnbinom(k, r, alpha, beta, thrown):
    if _nans(k, r, alpha, beta):
        return _sum(k, r, alpha, beta)
    if alpha <= 0.0 or beta <= 0.0 or r < 0.0:
        thrown[0] = True
        return math.nan
    if not is_integer(k) or k < 0.0 or not math.isfinite(k):
        return -math.inf
    return (lgamma(r + k) - lgamma(k + 1.0) - lgamma(r)) + lbeta(alpha + r, beta + k) - lbeta(alpha, beta)


def _cdf_bnbinom_table(k, r, alpha, beta):
    if k < 0.0 or not math.isfinite(k) or r < 0.0 or alpha < 0.0 or beta < 0.0:
        raise ValueError("inadmissible values")
    ik = to_pos_int(k)
    p_tab = [0.0] * (ik + 1)
    bab = lbeta(alpha, beta)
    gr = lgamma(r)
    gar = lgamma(alpha + r)
    xf = 0.0
    grx = gr
    gbx = lgamma(beta)
    gabrx = lgamma(alpha + beta + r)
    p_tab[0] = _exp(grx - gr + gar + gbx - gabrx - bab)
    if ik < 1:
        return p_tab
    grx += _log(r)
    gbx += _log(beta)
    gabrx += _log(alpha + beta + r)
    p_tab[1] = p_tab[0] + _exp(grx - gr + gar + gbx - gabrx - bab)
    if ik < 2:
        return p_tab
    for j in range(2, ik + 1):
        dj = float(j)
        grx += _log(r + dj - 1.0)
        gbx += _log(beta + dj - 1.0)
        gabrx += _log(alpha + beta + r + dj - 1.0)
        xf += _log(dj)
        p_tab[j] = p_tab[j - 1] + _exp(grx - (xf + gr) + gar + gbx - gabrx - bab)
    return p_tab


def dbnbinom(x, size, alpha=1.0, beta=1.0, log=False):
    return density(log, _logpmf_bnbinom, x, size, alpha, beta)


def pbnbinom(q, size, alpha=1.0, beta=1.0, lower_tail=True, log_p=False):
    xv, sv, av, bv = as_vec(q), as_vec(size), as_vec(alpha), as_vec(beta)
    n = _recycle_len(len(xv), len(sv), len(av), len(bv))
    limits = {}
    for i in range(n):
        xx = float(xv[i % len(xv)])
        ss = float(sv[i % len(sv)])
        aa = float(av[i % len(av)])
        bb = float(bv[i % len(bv)])
        key = (ss, aa, bb)
        if math.isfinite(xx) and xx > limits.get(key, 0.0):
            limits[key] = xx
    tables = {}

    def fn(xx, ss, aa, bb, thrown):
        if _nans(xx, ss, aa, bb):
            return _sum(xx, ss, aa, bb)
        if aa <= 0.0 or bb <= 0.0 or ss < 0.0:
            thrown[0] = True
            return math.nan
        if xx < 0.0:
            return 0.0
        if not math.isfinite(xx):
            return 1.0
        if is_large_int(xx):
            warnings.warn("NAs introduced by coercion to integer range")
            return math.nan
        key = (ss, aa, bb)
        tab = tables.get(key)
        if tab is None:
            tab = _cdf_bnbinom_table(limits.get(key, 0.0), ss, aa, bb)
            tables[key] = tab
        return tab[to_pos_int(xx)]

    return probability(lower_tail, log_p, fn, q, size, alpha, beta)


def rbnbinom(n, size, alpha=1.0, beta=1.0):
    def fn(ss, aa, bb, thrown):
        if _nans(ss, aa, bb) or aa <= 0.0 or bb <= 0.0 or ss < 0.0:
            thrown[0] = True
            return math.nan
        prob = rbeta(aa, bb)
        return rnbinom(ss, prob)

    return generate(_n_obs(n), fn, size, alpha, beta)


# --- Discrete Laplace -------------------------------------------------------


def ddlaplace(x, location, scale, log=False):
    def fn(xx, loc, sc, thrown):
        if _nans(xx, sc, loc):
            return _sum(xx, sc, loc)
        if sc <= 0.0 or sc >= 1.0:
            thrown[0] = True
            return math.nan
        if not is_integer(xx):
            return -math.inf
        return _log1p(-sc) - _log1p(sc) + _log(sc) * abs(xx - loc)

    return density(log, fn, x, location, scale)


def pdlaplace(q, location, scale, lower_tail=True, log_p=False):
    def fn(xx, loc, sc, thrown):
        if _nans(xx, sc, loc):
            return _sum(xx, sc, loc)
        if sc <= 0.0 or sc >= 1.0:
            thrown[0] = True
            return math.nan
        if xx < 0.0:
            return _exp((_log(sc) * -_floor(xx - loc)) - _log1p(sc))
        return 1.0 - _exp(_log(sc) * (_floor(xx - loc) + 1.0) - _log1p(sc))

    return probability(lower_tail, log_p, fn, q, location, scale)


def rdlaplace(n, location, scale):
    def fn(loc, sc, thrown):
        if _nans(sc, loc) or sc <= 0.0 or sc >= 1.0:
            thrown[0] = True
            return math.nan
        gap = 1.0 - sc
        return rgeom(gap) - rgeom(gap) + loc

    return generate(_n_obs(n), fn, location, scale)


# --- Discrete Weibull -------------------------------------------------------


def ddweibull(x, shape1, shape2, log=False):
    def fn(xx, q, beta, thrown):
        if _nans(xx, q, beta):
            return _sum(xx, q, beta)
        if q <= 0.0 or q >= 1.0 or beta <= 0.0:
            thrown[0] = True
            return math.nan
        if not is_integer(xx) or xx < 0.0:
            return -math.inf
        val = _pow(q, _pow(xx, beta)) - _pow(q, _pow(xx + 1.0, beta))
        return _as_log(val)

    return density(log, fn, x, shape1, shape2)


def pdweibull(q, shape1, shape2, lower_tail=True, log_p=False):
    def fn(xx, shape, beta, thrown):
        if _nans(xx, shape, beta):
            return _sum(xx, shape, beta)
        if shape <= 0.0 or shape >= 1.0 or beta <= 0.0:
            thrown[0] = True
            return math.nan
        if xx < 0.0:
            return 0.0
        return 1.0 - _exp(_log(shape) * _exp(_log1p(xx) * beta))

    return probability(lower_tail, log_p, fn, q, shape1, shape2)


def qdweibull(p, shape1, shape2, lower_tail=True, log_p=False):
    def fn(pp, q, beta, thrown):
        if _nans(pp, q, beta):
            return _sum(pp, q, beta)
        if q <= 0.0 or q >= 1.0 or beta <= 0.0 or not _valid_prob(pp):
            thrown[0] = True
            return math.nan
        if pp == 0.0:
            return 0.0
        return _ceil(_pow(_div(_log(1.0 - pp), _log(q)), 1.0 / beta) - 1.0)

    return quantile(lower_tail, log_p, fn, p, shape1, shape2)


def rdweibull(n, shape1, shape2):
    def fn(q, beta, thrown):
        if _nans(q, beta) or q <= 0.0 or q >= 1.0 or beta <= 0.0:
            thrown[0] = True
            return math.nan
        return _ceil(_pow(_div(_log(unif()), _log(q)), 1.0 / beta) - 1.0)

    return generate(_n_obs(n), fn, shape1, shape2)


# --- Discrete uniform -------------------------------------------------------


def ddunif(x, min, max, log=False):
    def fn(xx, lower, upper, thrown):
        if _nans(xx, lower, upper):
            return _sum(xx, lower, upper)
        if (
            lower > upper
            or not math.isfinite(lower)
            or not math.isfinite(upper)
            or not is_integer(lower, False)
            or not is_integer(upper, False)
        ):
            thrown[0] = True
            return math.nan
        if xx < lower or xx > upper or not is_integer(xx):
            return -math.inf
        return _as_log(1.0 / (upper - lower + 1.0))

    return density(log, fn, x, min, max)


def pdunif(q, min, max, lower_tail=True, log_p=False):
    def fn(xx, lower, upper, thrown):
        if _nans(xx, lower, upper):
            return _sum(xx, lower, upper)
        if (
            lower > upper
            or not math.isfinite(lower)
            or not math.isfinite(upper)
            or not is_integer(lower, False)
            or not is_integer(upper, False)
        ):
            thrown[0] = True
            return math.nan
        if xx < lower:
            return 0.0
        if xx >= upper:
            return 1.0
        return (_floor(xx) - lower + 1.0) / (upper - lower + 1.0)

    return probability(lower_tail, log_p, fn, q, min, max)


def qdunif(p, min, max, lower_tail=True, log_p=False):
    def fn(pp, lower, upper, thrown):
        if _nans(pp, lower, upper):
            return _sum(pp, lower, upper)
        if (
            lower > upper
            or not math.isfinite(lower)
            or not math.isfinite(upper)
            or not is_integer(lower, False)
            or not is_integer(upper, False)
            or not _valid_prob(pp)
        ):
            thrown[0] = True
            return math.nan
        if pp == 0.0 or lower == upper:
            return lower
        return _ceil(pp * (upper - lower + 1.0) + lower - 1.0)

    return quantile(lower_tail, log_p, fn, p, min, max)


def rdunif(n, min, max):
    def fn(lower, upper, thrown):
        if (
            _nans(lower, upper)
            or lower > upper
            or not math.isfinite(lower)
            or not math.isfinite(upper)
            or not is_integer(lower, False)
            or not is_integer(upper, False)
        ):
            thrown[0] = True
            return math.nan
        if lower == upper:
            return lower
        return _ceil(runif(lower - 1.0, upper))

    return generate(_n_obs(n), fn, min, max)


# --- Logarithmic series -----------------------------------------------------


def dlgser(x, theta, log=False):
    def fn(xx, th, thrown):
        if _nans(xx, th):
            return _sum(xx, th)
        if th <= 0.0 or th >= 1.0:
            thrown[0] = True
            return math.nan
        if not is_integer(xx) or xx < 1.0:
            return -math.inf
        a = -1.0 / _log1p(-th)
        return _log(a) + (_log(th) * xx) - _log(xx)

    return density(log, fn, x, theta)


def plgser(q, theta, lower_tail=True, log_p=False):
    def fn(xx, th, thrown):
        if _nans(xx, th):
            return _sum(xx, th)
        if th <= 0.0 or th >= 1.0:
            thrown[0] = True
            return math.nan
        if xx < 1.0:
            return 0.0
        if not math.isfinite(xx):
            return 1.0
        if is_large_int(xx):
            warnings.warn("NAs introduced by coercion to integer range")
            return math.nan
        a = -1.0 / _log1p(-th)
        b = 0.0
        for k in range(1, to_pos_int(xx) + 1):
            dk = float(k)
            b += _pow(th, dk) / dk
        return a * b

    return probability(lower_tail, log_p, fn, q, theta)


def qlgser(p, theta, lower_tail=True, log_p=False):
    def fn(pp, th, thrown):
        if _nans(pp, th):
            return _sum(pp, th)
        if th <= 0.0 or th >= 1.0 or not _valid_prob(pp):
            thrown[0] = True
            return math.nan
        if pp == 0.0:
            return 1.0
        if pp == 1.0:
            return math.inf
        pk = -th / math.log(1.0 - th)
        k = 1.0
        while pp > pk:
            pp -= pk
            pk *= th * k / (k + 1.0)
            k += 1.0
        return k

    return quantile(lower_tail, log_p, fn, p, theta)


def rlgser(n, theta):
    def fn(th, thrown):
        if math.isnan(th) or th <= 0.0 or th >= 1.0:
            thrown[0] = True
            return math.nan
        u = unif()
        pk = -th / math.log(1.0 - th)
        k = 1.0
        while u > pk:
            u -= pk
            pk *= th * k / (k + 1.0)
            k += 1.0
        return k

    return generate(_n_obs(n), fn, theta)


# --- Categorical ------------------------------------------------------------


def dcat(x, prob, log=False):
    mat = _as_matrix(prob)
    xv = as_vec(x)
    if xv.size == 0 or mat.size == 0:
        return np.asarray([], dtype=float)
    k = mat.shape[1]
    if k < 2:
        raise ValueError("number of columns in prob is < 2")
    bad = [False]
    tab = _normalize_rows(mat, bad)
    nrow = tab.shape[0]
    n = _builtin_max(len(xv), nrow)

    def fn(ii, xx, thrown):
        if bad[0]:
            thrown[0] = True
        if math.isnan(xx):
            return xx
        if not is_integer(xx) or xx < 1.0 or xx > float(k):
            return -math.inf
        row = int(ii) % nrow
        return _as_log(float(tab[row, int(xx) - 1]))

    return density(log, fn, np.arange(n, dtype=float), xv)


def pcat(q, prob, lower_tail=True, log_p=False):
    mat = _as_matrix(prob)
    qv = as_vec(q)
    if qv.size == 0 or mat.size == 0:
        return np.asarray([], dtype=float)
    k = mat.shape[1]
    if k < 2:
        raise ValueError("number of columns in prob is < 2")
    bad = [False]
    tab = _cumulative_rows(mat, bad)
    nrow = tab.shape[0]
    n = _builtin_max(len(qv), nrow)

    def fn(ii, xx, thrown):
        if bad[0]:
            thrown[0] = True
        if math.isnan(xx):
            return xx
        if xx < 1.0:
            return 0.0
        if xx >= float(k):
            return 1.0
        row = int(ii) % nrow
        return float(tab[row, to_pos_int(xx) - 1])

    return probability(lower_tail, log_p, fn, np.arange(n, dtype=float), qv)


def qcat(p, prob, lower_tail=True, log_p=False, labels=None):
    # cpp_qcat exponentiates and flips a copy, then reads the original p.
    del lower_tail, log_p
    mat = _as_matrix(prob)
    pv = as_vec(p)
    if pv.size == 0 or mat.size == 0:
        return np.asarray([], dtype=float)
    k = mat.shape[1]
    if k < 2:
        raise ValueError("number of columns in prob is < 2")
    thrown = [False]
    tab = _cumulative_rows(mat, thrown)
    nrow = tab.shape[0]
    n = _builtin_max(len(pv), nrow)
    out = np.empty(n, dtype=float)
    for i in range(n):
        pp = float(pv[i % len(pv)])
        if math.isnan(pp):
            out[i] = pp
            continue
        cell = float(tab[i % nrow, 0])
        if math.isnan(cell):
            out[i] = cell
            continue
        if pp < 0.0 or pp > 1.0:
            out[i] = math.nan
            thrown[0] = True
            continue
        if pp == 0.0:
            out[i] = 1.0
            continue
        if pp == 1.0:
            out[i] = float(k)
            continue
        jj = 1
        for j in range(k):
            if float(tab[i % nrow, j]) >= pp:
                jj = j + 1
                break
        out[i] = float(jj)
    if thrown[0]:
        warnings.warn("NaNs produced")
    return _apply_labels(out, labels, k)


def rcat(n, prob, labels=None):
    count = _n_obs(n)
    array = np.asarray(prob, dtype=float)
    if array.ndim <= 1:
        flat = array.reshape(-1)
        k = int(flat.size)
        if k == 0 or np.any(np.isnan(flat)) or np.any(flat < 0.0):
            warnings.warn("NAs produced")
            out = np.full(count, np.nan)
        else:
            out = np.asarray(_sample_int_prob(flat, count), dtype=float)
        return _apply_labels(out, labels, k)

    mat = _as_matrix(prob)
    if mat.size < 1:
        warnings.warn("NAs produced")
        return np.full(count, np.nan)
    k = mat.shape[1]
    if k < 2:
        raise ValueError("number of columns in prob is < 2")
    bad = [False]
    tab = _cumulative_rows(mat, bad)
    nrow = tab.shape[0]

    def fn(ii, thrown):
        if bad[0]:
            thrown[0] = True
        row = int(ii) % nrow
        if math.isnan(float(tab[row, 0])):
            return float(tab[row, 0])
        u = unif()
        jj = 1
        for j in range(k):
            if float(tab[row, j]) >= u:
                jj = j + 1
                break
        return float(jj)

    out = generate(count, fn, np.arange(count, dtype=float))
    return _apply_labels(out, labels, k)


def rcatlp(n, log_prob, labels=None):
    count = _n_obs(n)
    mat = _as_matrix(log_prob)
    if mat.size < 1:
        warnings.warn("NAs produced")
        return np.full(count, np.nan)
    k = mat.shape[1]
    nrow = mat.shape[0]

    def fn(ii, thrown):
        row = int(ii) % nrow
        max_val = -math.inf
        jj = 0
        for j in range(k):
            gamma = float(mat[row, j])
            if math.isnan(gamma):
                thrown[0] = True
                return math.nan
            glp = -_log(exp_rand()) + gamma
            if glp > max_val:
                max_val = glp
                jj = j
        return float(jj + 1)

    out = generate(count, fn, np.arange(count, dtype=float))
    return _apply_labels(out, labels, k)


# --- Skellam ----------------------------------------------------------------


def dskellam(x, mu1, mu2, log=False):
    def fn(xx, m1, m2, thrown):
        if _nans(xx, m1, m2):
            return _sum(xx, m1, m2)
        if m1 < 0.0 or m2 < 0.0:
            thrown[0] = True
            return math.nan
        if not is_integer(xx) or not math.isfinite(xx):
            return -math.inf
        # R::bessel_i(..., 1) is IZE 1, the unscaled Bessel I.
        val = math.exp(-(m1 + m2)) * _pow(_div(m1, m2), xx / 2.0) * bessel_i(
            2.0 * math.sqrt(m1 * m2), xx, False
        )
        return _as_log(val)

    return density(log, fn, x, mu1, mu2)


def rskellam(n, mu1, mu2):
    def fn(m1, m2, thrown):
        if _nans(m1, m2) or m1 < 0.0 or m2 < 0.0:
            thrown[0] = True
            return math.nan
        return rpois(m1) - rpois(m2)

    return generate(_n_obs(n), fn, mu1, mu2)


# --- Zero-inflated Poisson, binomial, negative binomial ---------------------


def dzip(x, lam, pi, log=False):
    def fn(xx, lambda_, infl, thrown):
        if _nans(xx, lambda_, infl):
            return _sum(xx, lambda_, infl)
        if lambda_ <= 0.0 or not _valid_prob(infl):
            thrown[0] = True
            return math.nan
        if xx < 0.0 or not is_integer(xx) or not math.isfinite(xx):
            return -math.inf
        if xx == 0.0:
            val = infl + _exp(_log1p(-infl) - lambda_)
        else:
            val = _exp(_log1p(-infl) + dpois(xx, lambda_, True))
        return _as_log(val)

    return density(log, fn, x, lam, pi)


def pzip(q, lam, pi, lower_tail=True, log_p=False):
    def fn(xx, lambda_, infl, thrown):
        if _nans(xx, lambda_, infl):
            return _sum(xx, lambda_, infl)
        if lambda_ <= 0.0 or not _valid_prob(infl):
            thrown[0] = True
            return math.nan
        if xx < 0.0:
            return 0.0
        if not math.isfinite(xx):
            return 1.0
        return infl + _exp(_log1p(-infl) + ppois(xx, lambda_, True, True))

    return probability(lower_tail, log_p, fn, q, lam, pi)


def qzip(p, lam, pi, lower_tail=True, log_p=False):
    def fn(pp, lambda_, infl, thrown):
        if _nans(pp, lambda_, infl):
            return _sum(pp, lambda_, infl)
        if lambda_ <= 0.0 or not _valid_prob(infl) or not _valid_prob(pp):
            thrown[0] = True
            return math.nan
        if pp < infl:
            return 0.0
        return qpois(_div(pp - infl, 1.0 - infl), lambda_)

    return quantile(lower_tail, log_p, fn, p, lam, pi)


def rzip(n, lam, pi):
    def fn(lambda_, infl, thrown):
        if _nans(lambda_, infl) or lambda_ <= 0.0 or not _valid_prob(infl):
            thrown[0] = True
            return math.nan
        if unif() < infl:
            return 0.0
        return rpois(lambda_)

    return generate(_n_obs(n), fn, lam, pi)


def dzib(x, size, prob, pi, log=False):
    def fn(xx, n, p, infl, thrown):
        if _nans(xx, n, p, infl):
            return _sum(xx, n, p, infl)
        if not _valid_prob(p) or n < 0.0 or not _valid_prob(infl) or not is_integer(n, False):
            thrown[0] = True
            return math.nan
        if xx < 0.0 or not is_integer(xx) or not math.isfinite(xx):
            return -math.inf
        if xx == 0.0:
            val = infl + _exp(_log1p(-infl) + _log1p(-p) * n)
        else:
            val = _exp(_log1p(-infl) + dbinom(xx, n, p, True))
        return _as_log(val)

    return density(log, fn, x, size, prob, pi)


def pzib(q, size, prob, pi, lower_tail=True, log_p=False):
    def fn(xx, n, p, infl, thrown):
        if _nans(xx, n, p, infl):
            return _sum(xx, n, p, infl)
        if not _valid_prob(p) or n < 0.0 or not _valid_prob(infl) or not is_integer(n, False):
            thrown[0] = True
            return math.nan
        if xx < 0.0:
            return 0.0
        if not math.isfinite(xx):
            return 1.0
        return infl + _exp(_log1p(-infl) + pbinom(xx, n, p, True, True))

    return probability(lower_tail, log_p, fn, q, size, prob, pi)


def qzib(p, size, prob, pi, lower_tail=True, log_p=False):
    def fn(pp, n, p, infl, thrown):
        if _nans(pp, n, p, infl):
            return _sum(pp, n, p, infl)
        if (
            not _valid_prob(p)
            or n < 0.0
            or not _valid_prob(infl)
            or not is_integer(n, False)
            or not _valid_prob(pp)
        ):
            thrown[0] = True
            return math.nan
        if pp < infl:
            return 0.0
        return qbinom(_div(pp - infl, 1.0 - infl), n, p)

    return quantile(lower_tail, log_p, fn, p, size, prob, pi)


def rzib(n, size, prob, pi):
    def fn(size_, p, infl, thrown):
        if (
            _nans(size_, p, infl)
            or not _valid_prob(p)
            or size_ < 0.0
            or not _valid_prob(infl)
            or not is_integer(size_, False)
        ):
            thrown[0] = True
            return math.nan
        if unif() < infl:
            return 0.0
        return rbinom(size_, p)

    return generate(_n_obs(n), fn, size, prob, pi)


def dzinb(x, size, prob, pi, log=False):
    def fn(xx, r, p, infl, thrown):
        if _nans(xx, r, p, infl):
            return _sum(xx, r, p, infl)
        if not _valid_prob(p) or r < 0.0 or not _valid_prob(infl):
            thrown[0] = True
            return math.nan
        if xx < 0.0 or not is_integer(xx) or not math.isfinite(xx):
            return -math.inf
        if xx == 0.0:
            val = infl + _exp(_log1p(-infl) + _log(p) * r)
        else:
            val = _exp(_log1p(-infl) + dnbinom(xx, r, p, True))
        return _as_log(val)

    return density(log, fn, x, size, prob, pi)


def pzinb(q, size, prob, pi, lower_tail=True, log_p=False):
    def fn(xx, r, p, infl, thrown):
        if _nans(xx, r, p, infl):
            return _sum(xx, r, p, infl)
        if not _valid_prob(p) or r < 0.0 or not _valid_prob(infl):
            thrown[0] = True
            return math.nan
        if xx < 0.0:
            return 0.0
        if not math.isfinite(xx):
            return 1.0
        return infl + _exp(_log1p(-infl) + pnbinom(xx, r, p, True, True))

    return probability(lower_tail, log_p, fn, q, size, prob, pi)


def qzinb(p, size, prob, pi, lower_tail=True, log_p=False):
    def fn(pp, r, p, infl, thrown):
        if _nans(pp, r, p, infl):
            return _sum(pp, r, p, infl)
        if not _valid_prob(p) or r < 0.0 or not _valid_prob(infl) or not _valid_prob(pp):
            thrown[0] = True
            return math.nan
        if pp < infl:
            return 0.0
        return qnbinom(_div(pp - infl, 1.0 - infl), r, p)

    return quantile(lower_tail, log_p, fn, p, size, prob, pi)


def rzinb(n, size, prob, pi):
    def fn(r, p, infl, thrown):
        if _nans(r, p, infl) or not _valid_prob(p) or r < 0.0 or not _valid_prob(infl):
            thrown[0] = True
            return math.nan
        if unif() < infl:
            return 0.0
        return rnbinom(r, p)

    return generate(_n_obs(n), fn, size, prob, pi)


# --- Truncated Poisson and binomial -----------------------------------------


def dtpois(x, lam, a=-math.inf, b=math.inf, log=False):
    def fn(xx, lambda_, lower, upper, thrown):
        if _nans(xx, lambda_, lower, upper):
            return _sum(xx, lambda_, lower, upper)
        if lambda_ < 0.0 or upper < lower:
            thrown[0] = True
            return math.nan
        if not is_integer(xx) or xx < 0.0 or xx <= lower or xx > upper or not math.isfinite(xx):
            return -math.inf
        pa = ppois(lower, lambda_)
        pb = ppois(upper, lambda_)
        return dpois(xx, lambda_, True) - _log(pb - pa)

    return density(log, fn, x, lam, a, b)


def ptpois(q, lam, a=-math.inf, b=math.inf, lower_tail=True, log_p=False):
    def fn(xx, lambda_, lower, upper, thrown):
        if _nans(xx, lambda_, lower, upper):
            return _sum(xx, lambda_, lower, upper)
        if lambda_ <= 0.0 or upper < lower:
            thrown[0] = True
            return math.nan
        if xx < 0.0 or xx <= lower:
            return 0.0
        if xx > upper or not math.isfinite(xx):
            return 1.0
        pa = ppois(lower, lambda_)
        pb = ppois(upper, lambda_)
        return (ppois(xx, lambda_) - pa) / (pb - pa)

    return probability(lower_tail, log_p, fn, q, lam, a, b)


def qtpois(p, lam, a=-math.inf, b=math.inf, lower_tail=True, log_p=False):
    def fn(pp, lambda_, lower, upper, thrown):
        if _nans(pp, lambda_, lower, upper):
            return _sum(pp, lambda_, lower, upper)
        if lambda_ < 0.0 or upper < lower or not _valid_prob(pp):
            thrown[0] = True
            return math.nan
        if pp == 0.0:
            return _builtin_max(lower, 0.0)
        if pp == 1.0:
            return upper
        pa = ppois(lower, lambda_)
        pb = ppois(upper, lambda_)
        return qpois(pa + pp * (pb - pa), lambda_)

    return quantile(lower_tail, log_p, fn, p, lam, a, b)


def rtpois(n, lam, a=-math.inf, b=math.inf):
    def fn(lambda_, lower, upper, thrown):
        if _nans(lambda_, lower, upper) or lambda_ < 0.0 or upper < lower:
            thrown[0] = True
            return math.nan
        pa = ppois(lower, lambda_)
        pb = ppois(upper, lambda_)
        return qpois(runif(pa, pb), lambda_)

    return generate(_n_obs(n), fn, lam, a, b)


def dtbinom(x, size, prob, a=-math.inf, b=math.inf, log=False):
    def fn(xx, n, p, lower, upper, thrown):
        if _nans(xx, n, p, lower, upper):
            return _sum(xx, n, p, lower, upper)
        if n < 0.0 or not _valid_prob(p) or upper < lower or not is_integer(n, False):
            thrown[0] = True
            return math.nan
        if not is_integer(xx) or xx < 0.0 or xx <= lower or xx > upper or xx > n:
            return -math.inf
        pa = pbinom(lower, n, p)
        pb = pbinom(upper, n, p)
        return dbinom(xx, n, p, True) - _log(pb - pa)

    return density(log, fn, x, size, prob, a, b)


def ptbinom(q, size, prob, a=-math.inf, b=math.inf, lower_tail=True, log_p=False):
    def fn(xx, n, p, lower, upper, thrown):
        if _nans(xx, n, p, lower, upper):
            return _sum(xx, n, p, lower, upper)
        if n < 0.0 or not _valid_prob(p) or upper < lower or not is_integer(n, False):
            thrown[0] = True
            return math.nan
        if xx < 0.0 or xx <= lower:
            return 0.0
        if xx > upper or xx >= n:
            return 1.0
        pa = pbinom(lower, n, p)
        pb = pbinom(upper, n, p)
        return (pbinom(xx, n, p) - pa) / (pb - pa)

    return probability(lower_tail, log_p, fn, q, size, prob, a, b)


def qtbinom(p, size, prob, a=-math.inf, b=math.inf, lower_tail=True, log_p=False):
    def fn(pp, n, p, lower, upper, thrown):
        if _nans(pp, n, p, lower, upper):
            return _sum(pp, n, p, lower, upper)
        if (
            n < 0.0
            or not _valid_prob(p)
            or upper < lower
            or not is_integer(n, False)
            or not _valid_prob(pp)
        ):
            thrown[0] = True
            return math.nan
        if pp == 0.0:
            return _builtin_max(lower, 0.0)
        if pp == 1.0:
            return _builtin_min(n, upper)
        pa = pbinom(lower, n, p)
        pb = pbinom(upper, n, p)
        return qbinom(pa + pp * (pb - pa), n, p)

    return quantile(lower_tail, log_p, fn, p, size, prob, a, b)


def rtbinom(n, size, prob, a=-math.inf, b=math.inf):
    def fn(size_, p, lower, upper, thrown):
        if (
            _nans(size_, p, lower, upper)
            or size_ < 0.0
            or not _valid_prob(p)
            or upper < lower
            or not is_integer(size_, False)
        ):
            thrown[0] = True
            return math.nan
        pa = pbinom(lower, size_, p)
        pb = pbinom(upper, size_, p)
        return qbinom(runif(pa, pb), size_, p)

    return generate(_n_obs(n), fn, size, prob, a, b)


# --- Negative hypergeometric ------------------------------------------------


def _nhyper_table(n, m, r, cumulative=False):
    if n < 0.0 or m < 0.0 or r < 0.0 or r > m:
        raise ValueError("inadmissible values")
    ni = to_pos_int(n)
    capital = m + n
    start = 1e-200
    h = [0.0] * ni
    t = [0.0] * ni
    p = [0.0] * (ni + 1)
    h[0] = start * r * n / (capital - r)
    t[0] = start + h[0]
    for i in range(1, ni):
        j = float(i) + r
        h[i] = h[i - 1] * j * (n + r - j) / (capital - j) / (j + 1.0 - r)
        t[i] = t[i - 1] + h[i]
    total = t[ni - 1]
    p[0] = start / total
    if cumulative:
        for i in range(1, ni):
            p[i] = t[i - 1] / total
        p[ni] = 1.0
    else:
        for i in range(1, ni + 1):
            p[i] = h[i - 1] / total
    return p


def _nhyper_bad(n, m, r):
    return (
        r > m
        or n < 0.0
        or m < 0.0
        or r < 0.0
        or not is_integer(n, False)
        or not is_integer(m, False)
        or not is_integer(r, False)
    )


def dnhyper(x, n, m, r, log=False):
    memo = {}

    def fn(xx, nn, mm, rr, thrown):
        if _nans(xx, nn, mm, rr):
            return _sum(xx, nn, mm, rr)
        if _nhyper_bad(nn, mm, rr):
            thrown[0] = True
            return math.nan
        if not is_integer(xx) or xx < rr or xx > (nn + rr):
            return -math.inf
        if is_large_int(xx):
            warnings.warn("NAs introduced by coercion to integer range")
            return math.nan
        key = (nn, mm, rr)
        tab = memo.get(key)
        if tab is None:
            tab = _nhyper_table(nn, mm, rr, False)
            memo[key] = tab
        return _as_log(tab[to_pos_int(xx - rr)])

    return density(log, fn, x, n, m, r)


def pnhyper(q, n, m, r, lower_tail=True, log_p=False):
    memo = {}

    def fn(xx, nn, mm, rr, thrown):
        if _nans(xx, nn, mm, rr):
            return _sum(xx, nn, mm, rr)
        if _nhyper_bad(nn, mm, rr):
            thrown[0] = True
            return math.nan
        if xx < rr:
            return 0.0
        if xx >= (nn + rr):
            return 1.0
        if is_large_int(xx):
            warnings.warn("NAs introduced by coercion to integer range")
            return math.nan
        key = (nn, mm, rr)
        tab = memo.get(key)
        if tab is None:
            tab = _nhyper_table(nn, mm, rr, True)
            memo[key] = tab
        return tab[to_pos_int(xx - rr)]

    return probability(lower_tail, log_p, fn, q, n, m, r)


def qnhyper(p, n, m, r, lower_tail=True, log_p=False):
    memo = {}

    def fn(pp, nn, mm, rr, thrown):
        if _nans(pp, nn, mm, rr):
            return _sum(pp, nn, mm, rr)
        if not _valid_prob(pp) or _nhyper_bad(nn, mm, rr):
            thrown[0] = True
            return math.nan
        key = (nn, mm, rr)
        tab = memo.get(key)
        if tab is None:
            tab = _nhyper_table(nn, mm, rr, True)
            memo[key] = tab
        found = 0.0
        for j in range(to_pos_int(nn) + 1):
            if tab[j] >= pp:
                found = float(j) + rr
                break
        return found

    return quantile(lower_tail, log_p, fn, p, n, m, r)


def rnhyper(nn, n, m, r):
    memo = {}

    def fn(n_, m_, r_, thrown):
        if _nans(n_, m_, r_) or _nhyper_bad(n_, m_, r_):
            thrown[0] = True
            return math.nan
        key = (n_, m_, r_)
        tab = memo.get(key)
        if tab is None:
            tab = _nhyper_table(n_, m_, r_, True)
            memo[key] = tab
        u = unif()
        found = 0.0
        for j in range(to_pos_int(n_) + 1):
            if tab[j] >= u:
                found = float(j) + r_
                break
        return found

    return generate(_n_obs(nn), fn, n, m, r)


# --- Multinomial ------------------------------------------------------------


def dmnom(x, size, prob, log=False):
    xm = _as_matrix(x)
    pm = _as_matrix(prob)
    sv = as_vec(size)
    if _builtin_min(xm.shape[0], xm.shape[1], sv.size, pm.shape[0], pm.shape[1]) < 1:
        return np.asarray([], dtype=float)
    if xm.shape[1] != pm.shape[1]:
        raise ValueError("number of columns in x does not equal number of columns in prob")
    k = pm.shape[1]
    n = _builtin_max(xm.shape[0], sv.size, pm.shape[0])

    def fn(ii, ss, thrown):
        i = int(ii)
        row_x = i % xm.shape[0]
        row_p = i % pm.shape[0]
        sum_x = 0.0
        p_tot = 0.0
        wrong_param = False
        for j in range(k):
            if pm[row_p, j] < 0.0:
                wrong_param = True
            p_tot += pm[row_p, j]
            sum_x += xm[row_x, j]
        if math.isnan(p_tot + sum_x + ss):
            return p_tot + sum_x + ss
        if wrong_param or ss < 0.0 or not is_integer(ss, False):
            thrown[0] = True
            return math.nan
        prod_xfac = 0.0
        prod_pow = 0.0
        wrong_x = False
        for j in range(k):
            xj = float(xm[row_x, j])
            if xj < 0.0 or not is_integer(xj):
                wrong_x = True
            else:
                prod_xfac += _lfactorial(xj)
                prod_pow += _log(_div(float(pm[row_p, j]), p_tot)) * xj
        if wrong_x or sum_x < 0.0 or sum_x != ss:
            return -math.inf
        return _lfactorial(ss) - prod_xfac + prod_pow

    return density(log, fn, np.arange(n, dtype=float), sv)


def rmnom(n, size, prob):
    count = _n_obs(n)
    pm = _as_matrix(prob)
    sv = as_vec(size)
    if _builtin_min(sv.size, pm.shape[0], pm.shape[1]) < 1:
        warnings.warn("NAs produced")
        return np.full((count, pm.shape[1]), np.nan)
    k = pm.shape[1]
    out = np.zeros((count, k), dtype=float)
    thrown = [False]
    for i in range(count):
        ss = float(sv[i % len(sv)])
        row = i % pm.shape[0]
        size_left = ss
        sum_p = 1.0
        p_tot = 0.0
        wrong = False
        for j in range(k):
            if pm[row, j] < 0.0:
                wrong = True
                break
            p_tot += pm[row, j]
        if wrong or math.isnan(p_tot + ss) or ss < 0.0 or not is_integer(ss, False):
            thrown[0] = True
            out[i, :] = math.nan
            continue
        for j in range(k - 1):
            if size_left > 0.0:
                p_tmp = float(pm[row, j]) / p_tot
                out[i, j] = rbinom(size_left, trunc_p(_div(p_tmp, sum_p)))
                size_left -= out[i, j]
                sum_p -= p_tmp
            else:
                break
        out[i, k - 1] = size_left
    if thrown[0]:
        warnings.warn("NAs produced")
    return out


# --- Dirichlet-multinomial --------------------------------------------------


def ddirmnom(x, size, alpha, log=False):
    xm = _as_matrix(x)
    am = _as_matrix(alpha)
    sv = as_vec(size)
    if _builtin_min(xm.shape[0], xm.shape[1], sv.size, am.shape[0], am.shape[1]) < 1:
        return np.asarray([], dtype=float)
    m = xm.shape[1]
    k = _builtin_min(m, am.shape[1])
    if k < 2:
        raise ValueError("number of columns in alpha should be >= 2")
    if m != k:
        raise ValueError("number of columns in x does not equal number of columns in alpha")
    n = _builtin_max(xm.shape[0], sv.size, am.shape[0])

    def fn(ii, ss, thrown):
        i = int(ii)
        row_x = i % xm.shape[0]
        row_a = i % am.shape[0]
        sum_alpha = 0.0
        sum_x = 0.0
        wrong_x = False
        wrong_param = False
        for j in range(k):
            aj = float(am[row_a, j])
            xj = float(xm[row_x, j])
            if aj <= 0.0:
                wrong_param = True
            if xj < 0.0 or not is_integer(xj):
                wrong_x = True
            sum_x += xj
            sum_alpha += aj
        if math.isnan(sum_x + sum_alpha + ss):
            return sum_x + sum_alpha + ss
        if wrong_param or ss < 0.0 or not is_integer(ss, False):
            thrown[0] = True
            return math.nan
        if sum_x < 0.0 or sum_x != ss or wrong_x:
            return -math.inf
        prod = 0.0
        for j in range(k):
            xj = float(xm[row_x, j])
            aj = float(am[row_a, j])
            prod += lgamma(xj + aj) - (_lfactorial(xj) + lgamma(aj))
        return (_lfactorial(ss) + lgamma(sum_alpha)) - lgamma(ss + sum_alpha) + prod

    return density(log, fn, np.arange(n, dtype=float), sv)


def rdirmnom(n, size, alpha):
    count = _n_obs(n)
    am = _as_matrix(alpha)
    sv = as_vec(size)
    if _builtin_min(sv.size, am.shape[0], am.shape[1]) < 1:
        warnings.warn("NAs produced")
        return np.full((count, am.shape[1]), np.nan)
    k = am.shape[1]
    if k < 2:
        raise ValueError("Number of columns in alpha should be >= 2")
    out = np.zeros((count, k), dtype=float)
    thrown = [False]
    for i in range(count):
        ss = float(sv[i % len(sv)])
        row = i % am.shape[0]
        row_sum = 0.0
        wrong = False
        pi = [0.0] * k
        sum_alpha = 0.0
        for j in range(k):
            aj = float(am[row, j])
            sum_alpha += aj
            if aj <= 0.0:
                wrong = True
                break
            pi[j] = rgamma(aj, 1.0)
            row_sum += pi[j]
        if wrong or math.isnan(sum_alpha + ss) or ss < 0.0 or not is_integer(ss, False):
            thrown[0] = True
            out[i, :] = math.nan
            continue
        if ss == 0.0:
            continue
        sum_p = 1.0
        size_left = ss
        for j in range(k - 1):
            if size_left > 0.0:
                p_tmp = _div(pi[j], row_sum)
                out[i, j] = rbinom(size_left, trunc_p(_div(p_tmp, sum_p)))
                size_left -= out[i, j]
                sum_p -= p_tmp
            else:
                break
        out[i, k - 1] = size_left
    if thrown[0]:
        warnings.warn("NAs produced")
    return out


# --- Multivariate hypergeometric --------------------------------------------


def dmvhyper(x, n, k, log=False):
    xm = _as_matrix(x)
    nm = _as_matrix(n)
    kv = as_vec(k)
    if _builtin_min(xm.shape[0], xm.shape[1], nm.shape[0], nm.shape[1], kv.size) < 1:
        return np.asarray([], dtype=float)
    if xm.shape[1] != nm.shape[1]:
        raise ValueError("number of columns in x does not equal number of columns in n")
    m = xm.shape[1]
    nmax = _builtin_max(xm.shape[0], nm.shape[0], kv.size)

    def fn(ii, kk, thrown):
        i = int(ii)
        row_x = i % xm.shape[0]
        row_n = i % nm.shape[0]
        wrong_n = False
        sum_x = 0.0
        n_tot = 0.0
        for j in range(m):
            nj = float(nm[row_n, j])
            if not is_integer(nj, False) or nj < 0.0:
                wrong_n = True
            sum_x += float(xm[row_x, j])
            n_tot += nj
        if math.isnan(sum_x + n_tot + kk):
            return sum_x + n_tot + kk
        if wrong_n or kk < 0.0 or kk > n_tot or not is_integer(kk, False):
            thrown[0] = True
            return math.nan
        prod = 0.0
        wrong_x = False
        for j in range(m):
            xj = float(xm[row_x, j])
            nj = float(nm[row_n, j])
            if xj > nj or xj < 0.0 or not is_integer(xj):
                wrong_x = True
            else:
                prod += lchoose(nj, xj)
        if wrong_x or sum_x != kk:
            return -math.inf
        return prod - lchoose(n_tot, kk)

    return density(log, fn, np.arange(nmax, dtype=float), kv)


def rmvhyper(nn, n, k):
    count = _n_obs(nn)
    k_arr = np.asarray(k, dtype=float).reshape(-1)
    n_arr = np.asarray(n, dtype=float)
    if n_arr.ndim <= 1 and k_arr.size == 1:
        flat = n_arr.reshape(-1)
        kk = float(k_arr[0])
        if flat.size == 0 or np.any(np.isnan(flat)) or math.isnan(kk):
            warnings.warn("NAs produced")
            return np.full((count, 1), np.nan)
        if float(np.sum(flat)) == kk:
            return np.tile(flat, (count, 1))
        n_arr = flat.reshape(1, -1)
    elif n_arr.ndim <= 1:
        n_arr = n_arr.reshape(-1, 1)
    else:
        n_arr = np.array(n_arr, dtype=float, copy=True)
    if _builtin_min(n_arr.shape[0], n_arr.shape[1], k_arr.size) < 1:
        warnings.warn("NAs produced")
        return np.full((count, n_arr.shape[1]), np.nan)
    m = n_arr.shape[1]
    out = np.zeros((count, m), dtype=float)
    thrown = [False]
    for i in range(count):
        kk = float(k_arr[i % len(k_arr)])
        row = i % n_arr.shape[0]
        wrong = False
        n_otr = [0.0] * m
        for j in range(1, m):
            nj = float(n_arr[row, j])
            if not is_integer(nj, False) or nj < 0.0 or math.isnan(nj):
                wrong = True
                break
            n_otr[0] += nj
        n0 = float(n_arr[row, 0])
        if (
            wrong
            or math.isnan(kk)
            or math.isnan(n0)
            or not is_integer(n0, False)
            or n0 < 0.0
            or (n_otr[0] + n0) < kk
            or not is_integer(kk, False)
            or kk < 0.0
        ):
            thrown[0] = True
            out[i, :] = math.nan
            continue
        for j in range(1, m):
            n_otr[j] = n_otr[j - 1] - float(n_arr[row, j])
        k_left = kk
        out[i, 0] = _one_rhyper(n0, n_otr[0], k_left)
        k_left -= out[i, 0]
        if m > 2:
            for j in range(1, m - 1):
                out[i, j] = _one_rhyper(float(n_arr[row, j]), n_otr[j], k_left)
                k_left -= out[i, j]
        out[i, m - 1] = k_left
    if thrown[0]:
        warnings.warn("NAs produced")
    return out


# --- Gamma-Poisson ----------------------------------------------------------


def _cdf_gpois_table(x, alpha, beta):
    if x < 0.0 or not math.isfinite(x) or alpha < 0.0 or beta < 0.0:
        raise ValueError("inadmissible values")
    ix = to_pos_int(x)
    p_tab = [0.0] * (ix + 1)
    p = beta / (1.0 + beta)
    qa = _log(_pow(1.0 - p, alpha))
    ga = lgamma(alpha)
    lp = _log(p)
    gax = ga
    p_tab[0] = _exp(qa)
    if ix < 1:
        return p_tab
    gax += _log(alpha)
    px = lp
    p_tab[1] = p_tab[0] + _exp(gax - ga + px + qa)
    if ix < 2:
        return p_tab
    xf = 0.0
    for j in range(2, ix + 1):
        dj = float(j)
        gax += _log(dj + alpha - 1.0)
        xf += _log(dj)
        px += lp
        p_tab[j] = p_tab[j - 1] + _exp(gax - (xf + ga) + px + qa)
    return p_tab


def dgpois(x, shape, rate, scale=None, log=False):
    sc = _scale_from(rate, scale, None)

    def fn(xx, alpha, beta, thrown):
        if _nans(xx, alpha, beta):
            return _sum(xx, alpha, beta)
        if alpha <= 0.0 or beta <= 0.0:
            thrown[0] = True
            return math.nan
        if not is_integer(xx) or xx < 0.0 or not math.isfinite(xx):
            return -math.inf
        p = _exp(_log(beta) - _log1p(beta))
        return (
            lgamma(alpha + xx)
            - _lfactorial(xx)
            - lgamma(alpha)
            + _log(p) * xx
            + _log(1.0 - p) * alpha
        )

    return density(log, fn, x, shape, sc)


def pgpois(q, shape, rate, scale=None, lower_tail=True, log_p=False):
    sc = _scale_from(rate, scale, None)
    mx = _finite_max_int(as_vec(q))
    memo = {}

    def fn(xx, alpha, beta, thrown):
        if _nans(xx, alpha, beta):
            return _sum(xx, alpha, beta)
        if alpha <= 0.0 or beta <= 0.0:
            thrown[0] = True
            return math.nan
        if xx < 0.0:
            return 0.0
        if xx == math.inf:
            return 1.0
        if is_large_int(xx):
            warnings.warn("NAs introduced by coercion to integer range")
            return math.nan
        key = (alpha, beta)
        tab = memo.get(key)
        if tab is None:
            tab = _cdf_gpois_table(mx, alpha, beta)
            memo[key] = tab
        return tab[to_pos_int(xx)]

    return probability(lower_tail, log_p, fn, q, shape, sc)


def rgpois(n, shape, rate, scale=None):
    sc = _scale_from(rate, scale, None)

    def fn(alpha, beta, thrown):
        if _nans(alpha, beta) or alpha <= 0.0 or beta <= 0.0:
            thrown[0] = True
            return math.nan
        return rpois(rgamma(alpha, beta))

    return generate(_n_first(n), fn, shape, sc)


# --- Discrete gamma and discrete normal -------------------------------------


def ddgamma(x, shape, rate=None, scale=None, log=False):
    _gamma_conflict(rate, scale)
    sc = _scale_from(rate, scale, 1.0)

    def fn(xx, sh, s, thrown):
        if _nans(xx, sh, s):
            return _sum(xx, sh, s)
        if sh <= 0.0 or s <= 0.0:
            thrown[0] = True
            return math.nan
        if xx < 0.0 or not is_integer(xx):
            return -math.inf
        val = pgamma(xx + 1.0, sh, scale=s) - pgamma(xx, sh, scale=s)
        return _as_log(val)

    return density(log, fn, x, shape, sc)


def pdgamma(q, shape, rate=None, scale=None, lower_tail=True, log_p=False):
    sc = _scale_from(rate, scale, 1.0)

    def fn(qq, sh, s, thrown):
        if _nans(qq, sh, s):
            return _sum(qq, sh, s)
        if sh <= 0.0 or s <= 0.0 or not math.isfinite(sh) or not math.isfinite(s):
            thrown[0] = True
            return math.nan
        return pgamma(_floor(qq) + 1.0, sh, scale=s)

    return probability(lower_tail, log_p, fn, q, shape, sc)


def rdgamma(n, shape, rate=None, scale=None):
    sc = _scale_from(rate, scale, 1.0)

    def fn(sh, s, thrown):
        return float(_floor(rgamma(sh, s)))

    return generate(_n_obs(n), fn, shape, sc)


def ddnorm(x, mean=0.0, sd=1.0, log=False):
    def fn(xx, mu, sigma, thrown):
        if _nans(xx, mu, sigma):
            return _sum(xx, mu, sigma)
        if sigma <= 0.0:
            thrown[0] = True
            return math.nan
        if not is_integer(xx):
            return -math.inf
        val = pnorm(xx + 1.0, mu, sigma) - pnorm(xx, mu, sigma)
        return _as_log(val)

    return density(log, fn, x, mean, sd)


def pdnorm(q, mean=0.0, sd=1.0, lower_tail=True, log_p=False):
    def fn(qq, mu, sigma, thrown):
        if _nans(qq, mu, sigma):
            return _sum(qq, mu, sigma)
        if sigma < 0.0 or not math.isfinite(sigma):
            thrown[0] = True
            return math.nan
        return pnorm(_floor(qq) + 1.0, mu, sigma)

    return probability(lower_tail, log_p, fn, q, mean, sd)


def rdnorm(n, mean=0.0, sd=1.0):
    def fn(mu, sigma, thrown):
        if math.isnan(mu) or not math.isfinite(sigma) or sigma < 0.0:
            thrown[0] = True
            return math.nan
        if sigma == 0.0 or not math.isfinite(mu):
            val = mu
        else:
            val = mu + sigma * norm_rand()
        return float(_floor(val))

    return generate(_n_obs(n), fn, mean, sd)


# --- Rademacher -------------------------------------------------------------


def rsign(n):
    def fn(thrown):
        del thrown
        return rng_sign()

    return generate(_n_obs(n), fn)
