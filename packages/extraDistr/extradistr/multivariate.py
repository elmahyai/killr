"""Dirichlet, bivariate normal and Poisson, and normal and Poisson mixtures.

Parameter rows follow the C++ GETM rule: row i uses row i modulo the number of
rows. A vector is one row. Random draws use boot's Mersenne-Twister.
"""

import math
import warnings

import numpy as np

from extradistr._rgen import rgamma, rpois
from extradistr._rng import norm_rand, unif
from extradistr._special import dnorm, dpois, lchoose, lgamma, pnorm, ppois
from extradistr._vec import as_vec, density, first_flag, sample_size

_TOL = 1e-8


def _as_r_vector(value):
    if isinstance(value, (str, bytes)):
        raise TypeError("numeric argument expected")
    array = np.asarray(value, dtype=float)
    if array.ndim >= 2:
        return np.reshape(array, -1, order="F")
    return as_vec(value)


def _matrix(value):
    """R's vector-to-row rule: a vector becomes a one-row matrix."""
    if isinstance(value, (str, bytes)):
        raise TypeError("numeric argument expected")
    array = np.asarray(value, dtype=float)
    if array.ndim == 0:
        return array.reshape(1, 1)
    if array.ndim == 1:
        return array.reshape(1, array.shape[0])
    if array.ndim == 2:
        return array
    raise ValueError("invalid arguments")


def _at(array, index):
    return float(array[index % len(array)])


def _cell(matrix, i, j):
    return float(matrix[i % matrix.shape[0], j])


def _log(x):
    if x > 0.0:
        return math.log(x)
    if x == 0.0:
        return -math.inf
    return math.nan


def _div(numer, denom):
    if denom == 0.0 or math.isnan(denom):
        if numer == 0.0 or math.isnan(numer) or math.isnan(denom):
            return math.nan
        return math.copysign(math.inf, numer)
    return numer / denom


def _is_integer(x):
    if math.isnan(x):
        return False
    rounded = math.ceil(x) if x < 0.0 else math.floor(x)
    if rounded != x:
        warnings.warn("non-integer: %f" % x, stacklevel=4)
        return False
    return True


def _warn(message, thrown):
    if thrown[0]:
        warnings.warn(message, stacklevel=3)


def _maybe_exp(values, log):
    if first_flag(log):
        return values
    out = np.empty(len(values), dtype=float)
    for i, value in enumerate(values):
        out[i] = math.exp(value)
    return out


def _logsumexp(terms):
    mx = -math.inf
    for term in terms:
        if term > mx:
            mx = term
    total = 0.0
    for term in terms:
        total += math.exp(term - mx)
    if total == 0.0:
        logged = -math.inf
    elif math.isnan(total):
        return math.nan
    else:
        logged = math.log(total)
    return logged + mx


def _rnorm(mean, sd):
    if math.isnan(mean) or not math.isfinite(sd) or sd < 0.0:
        return math.nan
    if sd == 0.0 or not math.isfinite(mean):
        return mean
    return mean + sd * norm_rand()


def _count(n):
    count = sample_size(n)
    if count < 0:
        raise ValueError("invalid arguments")
    return count


def _split_xy(x, y):
    if y is None:
        array = np.asarray(x, dtype=float)
        if array.ndim == 2 and array.shape[1] == 2:
            return array[:, 0], array[:, 1]
        raise ValueError("y is not provided while x is not a two-column matrix")
    return x, y


def _guard_pair(columns):
    if any(len(col) == 0 for col in columns):
        return np.asarray([], dtype=float)
    if len(columns[0]) != len(columns[1]):
        raise ValueError("lengths of x and y differ")
    return None


def _logpdf_bvnorm(x, y, mu1, mu2, sigma1, sigma2, rho, thrown):
    if (
        math.isnan(x)
        or math.isnan(y)
        or math.isnan(mu1)
        or math.isnan(mu2)
        or math.isnan(sigma1)
        or math.isnan(sigma2)
        or math.isnan(rho)
    ):
        return x + y + mu1 + mu2 + sigma1 + sigma2 + rho
    if sigma1 <= 0.0 or sigma2 <= 0.0 or rho <= -1.0 or rho >= 1.0:
        thrown[0] = True
        return math.nan
    if not math.isfinite(x) or not math.isfinite(y):
        return -math.inf
    z1 = (x - mu1) / sigma1
    z2 = (y - mu2) / sigma2
    quad = z1 * z1 - 2.0 * rho * z1 * z2 + z2 * z2
    log_c1 = -math.log(2.0 * math.pi * math.sqrt(1.0 - rho * rho) * sigma1 * sigma2)
    c2 = -1.0 / (2.0 * (1.0 - rho * rho))
    return log_c1 + c2 * quad


def _logpmf_bvpois(x, y, a, b, c, thrown):
    if math.isnan(x) or math.isnan(y) or math.isnan(a) or math.isnan(b) or math.isnan(c):
        return x + y + a + b + c
    if a < 0.0 or b < 0.0 or c < 0.0:
        thrown[0] = True
        return math.nan
    if (
        not _is_integer(x)
        or x < 0.0
        or not math.isfinite(x)
        or not math.isfinite(y)
        or not _is_integer(y)
    ):
        return -math.inf
    if y < 0.0:
        return -math.inf
    tmp = -(a + b + c)
    tmp += (_log(a) * x - lgamma(x + 1.0)) + (_log(b) * y - lgamma(y + 1.0))
    minxy = int(x if x < y else y)
    lc_ab = _log(c) - _log(a) - _log(b)
    terms = []
    for k in range(minxy + 1):
        dk = float(k)
        terms.append(float(lchoose(x, dk)) + float(lchoose(y, dk)) + lgamma(dk + 1.0) + lc_ab * dk)
    return tmp + _logsumexp(terms)


def _pick_component(alpha, total, u):
    p_tmp = 1.0
    jj = 0
    for j in range(len(alpha) - 1, -1, -1):
        p_tmp -= _div(alpha[j], total)
        if u > p_tmp:
            return j
    return jj


def ddirichlet(x, alpha, log=False):
    xm = _matrix(x)
    am = _matrix(alpha)
    if min(xm.shape[0], xm.shape[1], am.shape[0], am.shape[1]) < 1:
        return np.asarray([], dtype=float)
    nmax = max(xm.shape[0], am.shape[0])
    m = xm.shape[1]
    k = min(m, am.shape[1])
    if k < 2:
        raise ValueError("number of columns in alpha should be >= 2")
    if m != k:
        raise ValueError("number of columns in x does not equal number of columns in alpha")
    thrown = [False]
    out = np.empty(nmax, dtype=float)
    for i in range(nmax):
        wrong_alpha = False
        wrong_x = False
        sum_alpha = 0.0
        sum_x = 0.0
        alphas = []
        xs = []
        for j in range(m):
            aj = _cell(am, i, j)
            xj = _cell(xm, i, j)
            alphas.append(aj)
            xs.append(xj)
            sum_alpha += aj
            sum_x += xj
            if aj <= 0.0:
                wrong_alpha = True
            if xj < 0.0 or xj > 1.0:
                wrong_x = True
        total = sum_x + sum_alpha
        if math.isnan(total):
            out[i] = total
            continue
        if wrong_alpha:
            thrown[0] = True
            out[i] = math.nan
            continue
        if wrong_x:
            out[i] = -math.inf
            continue
        prod_gamma = 0.0
        p_tmp = 0.0
        for j in range(m):
            prod_gamma += lgamma(alphas[j])
            p_tmp += _log(xs[j]) * (alphas[j] - 1.0)
            if alphas[j] == 1.0 and xs[j] == 0.0:
                p_tmp = -math.inf
        out[i] = p_tmp - (prod_gamma - lgamma(sum_alpha))
    _warn("NaNs produced", thrown)
    return _maybe_exp(out, log)


def rdirichlet(n, alpha):
    count = _count(n)
    am = _matrix(alpha)
    k = am.shape[1]
    if min(am.shape[0], k) < 1:
        warnings.warn("NAs produced", stacklevel=2)
        return np.full((count, k), np.nan)
    if k < 2:
        raise ValueError("number of columns in alpha should be >= 2")
    out = np.empty((count, k), dtype=float)
    thrown = [False]
    for i in range(count):
        sum_alpha = 0.0
        row_sum = 0.0
        wrong = False
        for j in range(k):
            aj = _cell(am, i, j)
            sum_alpha += aj
            if aj <= 0.0:
                wrong = True
                break
            draw = rgamma(aj, 1.0)
            out[i, j] = draw
            row_sum += draw
        if math.isnan(sum_alpha) or wrong:
            thrown[0] = True
            out[i, :] = np.nan
        else:
            with np.errstate(divide="ignore", invalid="ignore"):
                out[i, :] = out[i, :] / row_sum
    _warn("NAs produced", thrown)
    return out


def dbvnorm(x, y=None, mean1=0, mean2=None, sd1=1, sd2=None, cor=0, log=False):
    if mean2 is None:
        mean2 = mean1
    if sd2 is None:
        sd2 = sd1
    x, y = _split_xy(x, y)
    columns = (
        _as_r_vector(x),
        _as_r_vector(y),
        _as_r_vector(mean1),
        _as_r_vector(mean2),
        _as_r_vector(sd1),
        _as_r_vector(sd2),
        _as_r_vector(cor),
    )
    empty = _guard_pair(columns)
    if empty is not None:
        return empty
    return density(log, _logpdf_bvnorm, *columns)


def rbvnorm(n, mean1=0, mean2=None, sd1=1, sd2=None, cor=0):
    if mean2 is None:
        mean2 = mean1
    if sd2 is None:
        sd2 = sd1
    count = _count(n)
    columns = (
        _as_r_vector(mean1),
        _as_r_vector(mean2),
        _as_r_vector(sd1),
        _as_r_vector(sd2),
        _as_r_vector(cor),
    )
    out = np.empty((count, 2), dtype=float)
    if any(len(col) == 0 for col in columns):
        warnings.warn("NAs produced", stacklevel=2)
        out.fill(np.nan)
        return out
    thrown = [False]
    for i in range(count):
        mu1 = _at(columns[0], i)
        mu2 = _at(columns[1], i)
        sigma1 = _at(columns[2], i)
        sigma2 = _at(columns[3], i)
        rho = _at(columns[4], i)
        if (
            math.isnan(mu1)
            or math.isnan(mu2)
            or math.isnan(sigma1)
            or math.isnan(sigma2)
            or math.isnan(rho)
            or sigma1 <= 0.0
            or sigma2 <= 0.0
            or rho < -1.0
            or rho > 1.0
        ):
            thrown[0] = True
            out[i, 0] = np.nan
            out[i, 1] = np.nan
        elif abs(rho) >= _TOL:
            u = norm_rand()
            v = norm_rand()
            corr = rho * u + math.sqrt(1.0 - rho * rho) * v
            out[i, 0] = mu1 + sigma1 * u
            out[i, 1] = mu2 + sigma2 * corr
        else:
            out[i, 0] = _rnorm(mu1, sigma1)
            out[i, 1] = _rnorm(mu2, sigma2)
    _warn("NAs produced", thrown)
    return out


def dbvpois(x, y=None, a=None, b=None, c=None, log=False):
    if a is None or b is None or c is None:
        raise TypeError("a, b, and c are required")
    x, y = _split_xy(x, y)
    columns = (
        _as_r_vector(x),
        _as_r_vector(y),
        _as_r_vector(a),
        _as_r_vector(b),
        _as_r_vector(c),
    )
    empty = _guard_pair(columns)
    if empty is not None:
        return empty
    return density(log, _logpmf_bvpois, *columns)


def rbvpois(n, a, b, c):
    count = _count(n)
    columns = (_as_r_vector(a), _as_r_vector(b), _as_r_vector(c))
    out = np.empty((count, 2), dtype=float)
    if any(len(col) == 0 for col in columns):
        warnings.warn("NAs produced", stacklevel=2)
        out.fill(np.nan)
        return out
    thrown = [False]
    for i in range(count):
        aa = _at(columns[0], i)
        bb = _at(columns[1], i)
        cc = _at(columns[2], i)
        if math.isnan(aa) or math.isnan(bb) or math.isnan(cc) or aa < 0.0 or bb < 0.0 or cc < 0.0:
            thrown[0] = True
            out[i, 0] = np.nan
            out[i, 1] = np.nan
        else:
            u = rpois(aa)
            v = rpois(bb)
            w = rpois(cc)
            out[i, 0] = u + w
            out[i, 1] = v + w
    _warn("NAs produced", thrown)
    return out


def _mix_sizes(vector, matrices):
    dims = [len(vector)]
    for matrix in matrices:
        dims.extend(matrix.shape)
    return dims


def dmixnorm(x, mean, sd, alpha, log=False):
    xv = _as_r_vector(x)
    mu = _matrix(mean)
    sigma = _matrix(sd)
    am = _matrix(alpha)
    if min(_mix_sizes(xv, (mu, sigma, am))) < 1:
        return np.asarray([], dtype=float)
    k = am.shape[1]
    if k != mu.shape[1] or k != sigma.shape[1]:
        raise ValueError("sizes of mu, sigma, and alpha do not match")
    nmax = max(len(xv), mu.shape[0], sigma.shape[0], am.shape[0])
    thrown = [False]
    out = np.empty(nmax, dtype=float)
    for i in range(nmax):
        wrong = False
        alpha_tot = 0.0
        nans_sum = 0.0
        alphas = []
        mus = []
        sigmas = []
        for j in range(k):
            aj = _cell(am, i, j)
            sj = _cell(sigma, i, j)
            mj = _cell(mu, i, j)
            alphas.append(aj)
            sigmas.append(sj)
            mus.append(mj)
            if aj < 0.0 or sj <= 0.0:
                wrong = True
            nans_sum += mj + sj
            alpha_tot += aj
        xi = _at(xv, i)
        total = nans_sum + alpha_tot + xi
        if math.isnan(total):
            out[i] = total
            continue
        if wrong:
            thrown[0] = True
            out[i] = math.nan
            continue
        if not math.isfinite(xi):
            out[i] = -math.inf
            continue
        terms = []
        for j in range(k):
            terms.append(
                _log(alphas[j]) - _log(alpha_tot) + dnorm(xi, mus[j], sigmas[j], True)
            )
        out[i] = _logsumexp(terms)
    _warn("NaNs produced", thrown)
    return _maybe_exp(out, log)


def pmixnorm(q, mean, sd, alpha, lower_tail=True, log_p=False):
    xv = _as_r_vector(q)
    mu = _matrix(mean)
    sigma = _matrix(sd)
    am = _matrix(alpha)
    if min(_mix_sizes(xv, (mu, sigma, am))) < 1:
        return np.asarray([], dtype=float)
    k = am.shape[1]
    if k != mu.shape[1] or k != sigma.shape[1]:
        raise ValueError("sizes of mu, sigma, and alpha do not match")
    nmax = max(len(xv), mu.shape[0], sigma.shape[0], am.shape[0])
    lower = first_flag(lower_tail, True)
    thrown = [False]
    out = np.empty(nmax, dtype=float)
    for i in range(nmax):
        wrong = False
        alpha_tot = 0.0
        nans_sum = 0.0
        alphas = []
        mus = []
        sigmas = []
        for j in range(k):
            aj = _cell(am, i, j)
            sj = _cell(sigma, i, j)
            mj = _cell(mu, i, j)
            if aj < 0.0 or sj < 0.0:
                wrong = True
                break
            alphas.append(aj)
            sigmas.append(sj)
            mus.append(mj)
            nans_sum += mj + sj
            alpha_tot += aj
        xi = _at(xv, i)
        total = nans_sum + alpha_tot + xi
        if math.isnan(total):
            out[i] = total
            continue
        if wrong:
            thrown[0] = True
            out[i] = math.nan
            continue
        if xi == -math.inf:
            out[i] = -math.inf if lower else 0.0
            continue
        if xi == math.inf:
            out[i] = 0.0 if lower else -math.inf
            continue
        terms = []
        for j in range(k):
            terms.append(
                _log(alphas[j])
                - _log(alpha_tot)
                + pnorm(xi, mus[j], sigmas[j], lower, True)
            )
        out[i] = _logsumexp(terms)
    _warn("NaNs produced", thrown)
    return _maybe_exp(out, log_p)


def rmixnorm(n, mean, sd, alpha):
    count = _count(n)
    mu = _matrix(mean)
    sigma = _matrix(sd)
    am = _matrix(alpha)
    if min(mu.shape[0], mu.shape[1], sigma.shape[0], sigma.shape[1], am.shape[0], am.shape[1]) < 1:
        warnings.warn("NAs produced", stacklevel=2)
        return np.full(count, np.nan)
    k = am.shape[1]
    if k != mu.shape[1] or k != sigma.shape[1]:
        raise ValueError("sizes of mu, sigma, and alpha do not match")
    thrown = [False]
    out = np.empty(count, dtype=float)
    for i in range(count):
        wrong = False
        u = unif()
        alpha_tot = 0.0
        nans_sum = 0.0
        alphas = []
        mus = []
        sigmas = []
        for j in range(k):
            aj = _cell(am, i, j)
            sj = _cell(sigma, i, j)
            mj = _cell(mu, i, j)
            if aj < 0.0 or sj < 0.0:
                wrong = True
                break
            alphas.append(aj)
            sigmas.append(sj)
            mus.append(mj)
            nans_sum += mj + sj
            alpha_tot += aj
        if math.isnan(nans_sum + alpha_tot) or wrong:
            thrown[0] = True
            out[i] = np.nan
            continue
        jj = _pick_component(alphas, alpha_tot, u)
        out[i] = _rnorm(mus[jj], sigmas[jj])
    _warn("NAs produced", thrown)
    return out


def dmixpois(x, lambda_, alpha, log=False):
    xv = _as_r_vector(x)
    lam = _matrix(lambda_)
    am = _matrix(alpha)
    if min(_mix_sizes(xv, (lam, am))) < 1:
        return np.asarray([], dtype=float)
    k = am.shape[1]
    if k != lam.shape[1]:
        raise ValueError("sizes of lambda and alpha do not match")
    nmax = max(len(xv), lam.shape[0], am.shape[0])
    thrown = [False]
    out = np.empty(nmax, dtype=float)
    for i in range(nmax):
        wrong = False
        alpha_tot = 0.0
        nans_sum = 0.0
        alphas = []
        lambs = []
        for j in range(k):
            aj = _cell(am, i, j)
            lj = _cell(lam, i, j)
            if aj < 0.0 or lj < 0.0:
                wrong = True
                break
            alphas.append(aj)
            lambs.append(lj)
            nans_sum += lj
            alpha_tot += aj
        xi = _at(xv, i)
        total = nans_sum + alpha_tot + xi
        if math.isnan(total):
            out[i] = total
            continue
        if wrong:
            thrown[0] = True
            out[i] = math.nan
            continue
        if xi < 0.0 or not _is_integer(xi):
            out[i] = -math.inf
            continue
        if not math.isfinite(xi):
            out[i] = -math.inf
            continue
        terms = []
        for j in range(k):
            terms.append(_log(alphas[j]) - _log(alpha_tot) + dpois(xi, lambs[j], True))
        out[i] = _logsumexp(terms)
    _warn("NaNs produced", thrown)
    return _maybe_exp(out, log)


def pmixpois(q, lambda_, alpha, lower_tail=True, log_p=False):
    xv = _as_r_vector(q)
    lam = _matrix(lambda_)
    am = _matrix(alpha)
    if min(_mix_sizes(xv, (lam, am))) < 1:
        return np.asarray([], dtype=float)
    k = am.shape[1]
    if k != lam.shape[1]:
        raise ValueError("sizes of lambda and alpha do not match")
    nmax = max(len(xv), lam.shape[0], am.shape[0])
    lower = first_flag(lower_tail, True)
    thrown = [False]
    out = np.empty(nmax, dtype=float)
    for i in range(nmax):
        wrong = False
        alpha_tot = 0.0
        nans_sum = 0.0
        alphas = []
        lambs = []
        for j in range(k):
            aj = _cell(am, i, j)
            lj = _cell(lam, i, j)
            if aj < 0.0 or lj < 0.0:
                wrong = True
                break
            alphas.append(aj)
            lambs.append(lj)
            nans_sum += lj
            alpha_tot += aj
        xi = _at(xv, i)
        total = nans_sum + alpha_tot + xi
        if math.isnan(total):
            out[i] = total
            continue
        if wrong:
            thrown[0] = True
            out[i] = math.nan
            continue
        if xi < 0.0:
            out[i] = -math.inf if lower else 0.0
            continue
        if xi == math.inf:
            out[i] = 0.0 if lower else -math.inf
            continue
        terms = []
        for j in range(k):
            terms.append(
                _log(alphas[j]) - _log(alpha_tot) + ppois(xi, lambs[j], lower, True)
            )
        out[i] = _logsumexp(terms)
    _warn("NaNs produced", thrown)
    return _maybe_exp(out, log_p)


def rmixpois(n, lambda_, alpha):
    count = _count(n)
    lam = _matrix(lambda_)
    am = _matrix(alpha)
    if min(lam.shape[0], lam.shape[1], am.shape[0], am.shape[1]) < 1:
        warnings.warn("NAs produced", stacklevel=2)
        return np.full(count, np.nan)
    k = am.shape[1]
    if k != lam.shape[1]:
        raise ValueError("sizes of lambda and alpha do not match")
    thrown = [False]
    out = np.empty(count, dtype=float)
    for i in range(count):
        wrong = False
        u = unif()
        alpha_tot = 0.0
        nans_sum = 0.0
        alphas = []
        lambs = []
        for j in range(k):
            aj = _cell(am, i, j)
            lj = _cell(lam, i, j)
            if aj < 0.0 or lj < 0.0:
                wrong = True
                break
            alphas.append(aj)
            lambs.append(lj)
            nans_sum += lj
            alpha_tot += aj
        if math.isnan(nans_sum + alpha_tot) or wrong:
            thrown[0] = True
            out[i] = np.nan
            continue
        jj = _pick_component(alphas, alpha_tot, u)
        out[i] = rpois(lambs[jj])
    _warn("NAs produced", thrown)
    return out
