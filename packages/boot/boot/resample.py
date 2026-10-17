"""Bootstrap resampling from CRAN boot 1.3-32.

Ports ``boot``, ``boot.array``, ``c.boot``, ``print.boot``, ``plot.boot``,
and ``jack.after.boot``, together with the index helpers those functions
call. Draws come from :mod:`boot.rng`, which matches R's ``set.seed``.
Index matrices are filled column-major, as R stores them.
"""

from __future__ import annotations

import math
import warnings
from collections.abc import Sequence

import numpy as np

from boot import rng

_MISSING = object()
_STYPE = ("i", "f", "w")
_PARALLEL = ("no", "multicore", "snow")
_SIM = ("ordinary", "parametric", "balanced", "permutation", "antithetic")

# Acklam's rational approximation, refined against the error function.
# Checked against R's qnorm. A chi-squared quantile, when requested, is
# inverted from the same normal quantile and the regularized gamma.
_ACKLAM_A = (
    -3.969683028665376e01,
    2.209460984245205e02,
    -2.759285104469687e02,
    1.383577518672690e02,
    -3.066479806614716e01,
    2.506628277459239e00,
)
_ACKLAM_B = (
    -5.447609879822406e01,
    1.615858368580409e02,
    -1.556989798598866e02,
    6.680131188771972e01,
    -1.328068155288572e01,
)
_ACKLAM_C = (
    -7.784894002430293e-03,
    -3.223964580411365e-01,
    -2.400758277161838e00,
    -2.549732539343734e00,
    4.374664141464968e00,
    2.938163982698783e00,
)
_ACKLAM_D = (
    7.784695709041462e-03,
    3.224671290700398e-01,
    2.445134137142996e00,
    3.754408661907416e00,
)
_ACKLAM_LOW = 0.02425
_ACKLAM_HIGH = 1.0 - _ACKLAM_LOW
_SQRT2 = math.sqrt(2.0)
_INV_SQRT_2PI = 1.0 / math.sqrt(2.0 * math.pi)


class BootCall:
    """The arguments that were supplied to ``boot``, in R's ``match.call`` sense."""

    def __init__(self, text, fields):
        self.text = text
        self._fields = fields

    def __getattr__(self, name):
        if name.startswith("_"):
            raise AttributeError(name)
        return self._fields.get(name)

    def __repr__(self):
        return self.text


class BootResult:
    """Object stored the way ``boot.return`` stores a class ``"boot"`` list."""

    def __init__(self, order, values, call, boot_type="boot"):
        self._order = list(order)
        self.call = call
        self.boot_type = boot_type
        for key in self._order:
            setattr(self, key, values[key])

    def names(self):
        return list(self._order)

    def __str__(self):
        return _format_boot(self, digits=7, index=None)

    def __repr__(self):
        return str(self)


def _capture_rng():
    return (rng._mti, tuple(rng._mt))


def _restore_rng(state):
    mti, mt = state
    rng._mti = mti
    rng._mt[:] = mt


def _match_arg(value, choices, what):
    if value is None:
        return choices[0]
    if not isinstance(value, str):
        raise ValueError(f"{what} must be a character string")
    matches = [choice for choice in choices if choice.startswith(value)] if value else []
    if len(matches) == 1:
        return matches[0]
    listed = ", ".join(f'"{choice}"' for choice in choices)
    if not matches:
        raise ValueError(f"{what} should be one of {listed}")
    raise ValueError("there is more than one match in match.arg")


def _nrow(data):
    if isinstance(data, dict):
        if not data:
            raise ValueError("no data in call to 'boot'")
        return len(next(iter(data.values())))
    array = np.asarray(data)
    if array.ndim == 0 or array.size == 0:
        raise ValueError("no data in call to 'boot'")
    return int(array.shape[0])


def _as_numeric_strata(strata, n):
    """``tapply(seq_len(n), as.numeric(strata))`` with ``FUN`` omitted.

    That call returns the 1-based factor codes of the numeric stratum
    labels, in sorted-level order. A single stratum is a vector of ones.
    """
    if strata is None:
        return [1] * n
    values = np.asarray(strata)
    if values.shape[0] != n:
        raise ValueError("strata must have one value for each observation")
    if values.dtype.kind in "OUS":
        labels = [str(item) for item in values.tolist()]
        levels = sorted(set(labels))
        code = {level: i + 1 for i, level in enumerate(levels)}
        return [code[item] for item in labels]
    numbers = [float(item) for item in np.ravel(values)]
    levels = sorted(set(numbers))
    code = {level: i + 1 for i, level in enumerate(levels)}
    return [code[item] for item in numbers]


def _stratum_ids(strata):
    return sorted(set(strata))


def _positions(strata, code):
    """1-based observation numbers in one stratum, in increasing order."""
    return [i + 1 for i, value in enumerate(strata) if value == code]


def _tabulate(values, nbins):
    counts = [0] * nbins
    for value in values:
        if isinstance(value, float) and not math.isfinite(value):
            continue
        index = int(value)
        if 1 <= index <= nbins:
            counts[index - 1] += 1
    return counts


def _stratum_sizes(strata):
    counts = _tabulate(strata, max(strata) if strata else 0)
    return [counts[code - 1] for code in strata]


def _normalize(wts, strata):
    out = [float(value) for value in wts]
    n = len(strata)
    for code in _stratum_ids(strata):
        group = [i for i in range(n) if strata[i] == code]
        total = sum(out[i] for i in group)
        if total == 0:
            raise ValueError("stratum weights sum to zero")
        for i in group:
            out[i] = out[i] / total
    return out


def _reshape_weights(weights, n, n_sets):
    """``matrix(weights, n, length(R), byrow=TRUE)`` then column-normalize and transpose."""
    flat = np.ravel(np.asarray(weights, dtype=float), order="F")
    need = n * n_sets
    if flat.size == 0:
        raise ValueError("weights must have positive length")
    if need % flat.size != 0 and flat.size % need != 0 and flat.size != need:
        warnings.warn("data length is not a sub-multiple or multiple of the number of rows")
    vals = np.resize(flat, need)
    matrix = vals.reshape((n, n_sets), order="C")
    return matrix


def _r_mean(values):
    array = np.asarray(values, dtype=float).reshape(-1)
    array = array[np.isfinite(array)]
    if array.size == 0:
        return math.nan
    return float(np.sum(array) / array.size)


def _r_var(values):
    """R ``var``: the sample variance with divisor ``n - 1``."""
    array = np.asarray(values, dtype=float).reshape(-1)
    array = array[np.isfinite(array)]
    n = int(array.size)
    if n < 2:
        return math.nan
    mean = float(np.sum(array) / n)
    return float(np.sum((array - mean) ** 2) / (n - 1))


def _const(values, eps=1e-8):
    array = np.asarray(values, dtype=float).reshape(-1)
    center = _r_mean(array)
    if not math.isfinite(center):
        return False
    return bool(np.all(np.abs(array - center) < eps))


def _as_statistic(value):
    if np.isscalar(value):
        return np.asarray([value], dtype=float)
    return np.asarray(value, dtype=float).reshape(-1)


def _sample_positions(population, size, replace=True, prob=None):
    """Draw from ``population`` the way ``bsample`` and ``sample0`` do.

    ``population`` is 1-based. Equal-probability draws use ``sample_int``.
    Unequal probabilities follow R's ``ProbSampleReplace`` and
    ``ProbSampleNoReplace``: sort descending, walk the cumulative sum.
    """
    n = len(population)
    if prob is None:
        picked = rng.sample_int(n, size, replace=replace)
        return [population[i - 1] for i in picked]
    if replace:
        picked = _prob_sample_replace(n, prob, size)
    else:
        picked = _prob_sample_noreplace(n, prob, size)
    return [population[i - 1] for i in picked]


def _revsort(values, index):
    """R ``revsort``: heapsort into descending order, permuting ``index`` too.

    Equal probabilities are reordered. A stable sort would not match
    ``sample.int(..., prob=)``.
    """
    n = len(values)
    if n <= 1:
        return
    a = [0.0] + list(values)
    ib = [0] + list(index)
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


def _prob_sample_replace(n, prob, size):
    weights = [float(value) for value in prob]
    total = math.fsum(weights)
    if total <= 0:
        raise ValueError("too few positive probabilities")
    weights = [value / total for value in weights]
    perm = list(range(1, n + 1))
    _revsort(weights, perm)
    for i in range(1, n):
        weights[i] += weights[i - 1]
    nm1 = n - 1
    out = []
    for _ in range(size):
        draw = rng.unif()
        chosen = nm1
        for j in range(nm1):
            if draw <= weights[j]:
                chosen = j
                break
        out.append(perm[chosen])
    return out


def _prob_sample_noreplace(n, prob, size):
    weights = [float(value) for value in prob]
    total = math.fsum(weights)
    if total <= 0 or size > sum(value > 0 for value in weights):
        raise ValueError("too few positive probabilities")
    weights = [value / total for value in weights]
    perm = list(range(1, n + 1))
    _revsort(weights, perm)
    out = []
    totalmass = 1.0
    n1 = n - 1
    for _ in range(size):
        draw = totalmass * rng.unif()
        mass = 0.0
        chosen = n1
        for j in range(n1):
            mass += weights[j]
            if draw <= mass:
                chosen = j
                break
        out.append(perm[chosen])
        totalmass -= weights[chosen]
        del weights[chosen]
        del perm[chosen]
        n1 -= 1
    return out


def _rperm(values):
    order = rng.sample_int(len(values), replace=False)
    return [values[i - 1] for i in order]


def _fill_columns(target, columns, values):
    """Assign a column-major vector into ``target[:, columns]``."""
    rows = target.shape[0]
    matrix = np.asarray(values, dtype=float).reshape((rows, len(columns)), order="F")
    target[:, list(columns)] = matrix


def _ordinary_array(n, replicates, strata):
    codes = _stratum_ids(strata)
    if len(codes) == 1:
        draws = rng.sample_int(n, n * replicates, replace=True)
        return np.asarray(draws, dtype=float).reshape((replicates, n), order="F")
    output = np.zeros((replicates, n), dtype=float)
    for code in codes:
        group = _positions(strata, code)
        if len(group) == 1:
            output[:, group[0] - 1] = group[0]
        else:
            drawn = _sample_positions(group, replicates * len(group), replace=True)
            _fill_columns(output, [g - 1 for g in group], drawn)
    return output


def _balanced_array(n, replicates, strata):
    output = np.tile(np.arange(1, n + 1, dtype=float), replicates).reshape((n, replicates), order="F")
    for code in _stratum_ids(strata):
        group = [g - 1 for g in _positions(strata, code)]
        if len(group) > 1:
            block = output[np.ix_(group, range(replicates))]
            flat = block.ravel(order="F").tolist()
            shuffled = _rperm(flat)
            output[np.ix_(group, range(replicates))] = np.asarray(shuffled, dtype=float).reshape(
                (len(group), replicates), order="F"
            )
    return output.T.copy()


def _permutation_array(n, replicates, strata):
    output = np.tile(np.arange(1, n + 1, dtype=float), replicates).reshape((n, replicates), order="F")
    for code in _stratum_ids(strata):
        group = [g - 1 for g in _positions(strata, code)]
        if len(group) > 1:
            for column in range(replicates):
                output[group, column] = _rperm(output[group, column].tolist())
    return output.T.copy()


def _rank_average(values):
    n = len(values)
    order = sorted(range(n), key=lambda i: values[i])
    ranks = [0.0] * n
    start = 0
    while start < n:
        stop = start
        while stop + 1 < n and values[order[stop + 1]] == values[order[start]]:
            stop += 1
        average = (start + stop) / 2.0 + 1.0
        for position in range(start, stop + 1):
            ranks[order[position]] = average
        start = stop + 1
    return ranks


def _unique_rank(values):
    ranks = _rank_average(values)
    if len(ranks) != len(set(ranks)):
        index = list(range(1, len(values) + 1))
        unique = sorted(set(ranks))
        counts = {value: ranks.count(value) for value in unique}
        sorted_ranks = sorted(ranks)
        for value in unique:
            if counts[value] > 1:
                group = [i for i, rank in enumerate(ranks) if rank == value]
                slots = [index[k] for k, item in enumerate(sorted_ranks) if item == value]
                assigned = _rperm(slots)
                for position, rank in zip(group, assigned):
                    ranks[position] = float(rank)
    return ranks


def _anti_arr(n, replicates, influence, inds):
    half = replicates // 2
    mat1 = np.asarray(
        _sample_positions(list(inds), half * n, replace=True), dtype=float
    ).reshape((half, n), order="F")
    ranks = _unique_rank(list(influence))
    rev = list(inds)
    for i in range(n):
        target = n + 1 - ranks[i]
        partner = next(k for k, rank in enumerate(ranks) if rank == target)
        rev[i] = inds[partner]
    anti = np.empty_like(mat1)
    for (row, col), value in np.ndenumerate(mat1):
        pointer = int(value)
        if 1 <= pointer <= n:
            anti[row, col] = rev[pointer - 1]
        else:
            anti[row, col] = math.nan
    parts = [mat1, anti]
    if replicates != 2 * half:
        extra = _sample_positions(list(inds), n, replace=True)
        parts.append(np.asarray(extra, dtype=float).reshape((1, n)))
    return np.vstack(parts)


def _antithetic_array(n, replicates, influence, strata):
    output = np.zeros((replicates, n), dtype=float)
    for code in _stratum_ids(strata):
        group = _positions(strata, code)
        local = [influence[i - 1] for i in group]
        output[:, [g - 1 for g in group]] = _anti_arr(len(group), replicates, local, group)
    return output


def _extra_array(n, replicates, m, strata):
    m = np.asarray(m, dtype=float).reshape(-1)
    if m.size == 1:
        count = int(m[0])
        draws = rng.sample_int(n, count * replicates, replace=True)
        return np.asarray(draws, dtype=float).reshape((replicates, count), order="F")
    total = int(np.sum(m))
    output = np.full((replicates, total), math.nan)
    start = 0
    for code in _stratum_ids(strata):
        count = int(m[code - 1])
        if count > 0:
            group = _positions(strata, code)
            drawn = _sample_positions(group, replicates * count, replace=True)
            output[:, start : start + count] = np.asarray(drawn, dtype=float).reshape(
                (replicates, count), order="F"
            )
            start += count
    return output


def _importance_array(n, r_vec, weights, strata):
    weights = np.atleast_2d(np.asarray(weights, dtype=float))
    blocks = []
    for ir, replicates in enumerate(r_vec):
        out = np.tile(np.arange(1, n + 1, dtype=float), (replicates, 1))
        for code in _stratum_ids(strata):
            group = _positions(strata, code)
            probs = weights[ir, [g - 1 for g in group]]
            drawn = _sample_positions(group, replicates * len(group), replace=True, prob=probs)
            _fill_columns(out, [g - 1 for g in group], drawn)
        blocks.append(out)
    return np.vstack(blocks)


def _importance_array_bal(n, r_vec, weights, strata):
    weights = np.atleast_2d(np.asarray(weights, dtype=float))
    blocks = []
    for ir, replicates in enumerate(r_vec):
        out = np.tile(np.arange(1, n + 1, dtype=float), (replicates, 1))
        for code in _stratum_ids(strata):
            group = _positions(strata, code)
            probs = np.asarray(weights[ir, [g - 1 for g in group]], dtype=float)
            total = float(np.sum(probs))
            if total != 1:
                probs = probs / total
            base = np.floor(len(group) * replicates * probs)
            fraction = len(group) * replicates * probs - base
            pool = []
            for index, count in zip(group, base.astype(int)):
                pool.extend([index] * int(count))
            if np.any(fraction != 0):
                extra = int(round(float(np.sum(fraction))))
                if extra:
                    pool.extend(
                        _sample_positions(group, extra, replace=False, prob=fraction.tolist())
                    )
            shuffled = _rperm(pool)
            _fill_columns(out, [g - 1 for g in group], shuffled)
        blocks.append(out)
    return np.vstack(blocks)


def _index_array(n, r_value, sim, strata, m=0, influence=None, weights=None):
    r_vec = [int(value) for value in np.asarray(r_value, dtype=int).reshape(-1)]
    if weights is None:
        replicates = r_vec[0] if len(r_vec) == 1 else int(np.sum(r_vec))
        if sim == "ordinary":
            indices = _ordinary_array(n, replicates, strata)
            if int(np.sum(m)) > 0:
                indices = np.column_stack((indices, _extra_array(n, replicates, m, strata)))
            return indices
        if sim == "balanced":
            return _balanced_array(n, replicates, strata)
        if sim == "antithetic":
            return _antithetic_array(n, replicates, influence, strata)
        if sim == "permutation":
            return _permutation_array(n, replicates, strata)
        return None
    if sim == "ordinary":
        return _importance_array(n, r_vec, weights, strata)
    if sim == "balanced":
        return _importance_array_bal(n, r_vec, weights, strata)
    return None


def _freq_array(index_array):
    """Frequency of each original observation in each resample.

    Private copy of ``freq.array``. The public function is owned elsewhere.
    """
    array = np.asarray(index_array)
    if array.ndim == 1:
        array = array.reshape(1, -1)
    rows, cols = array.shape
    result = np.zeros((rows, cols), dtype=int)
    for row in range(rows):
        result[row, :] = _tabulate(array[row, :].tolist(), cols)
    return result


def _pnorm(z):
    if math.isnan(z):
        return math.nan
    return 0.5 * (1.0 + math.erf(z / _SQRT2))


def _acklam(p):
    if p < _ACKLAM_LOW:
        q = math.sqrt(-2.0 * math.log(p))
        return (
            (((((_ACKLAM_C[0] * q + _ACKLAM_C[1]) * q + _ACKLAM_C[2]) * q + _ACKLAM_C[3]) * q + _ACKLAM_C[4]) * q + _ACKLAM_C[5])
            / ((((_ACKLAM_D[0] * q + _ACKLAM_D[1]) * q + _ACKLAM_D[2]) * q + _ACKLAM_D[3]) * q + 1.0)
        )
    if p > _ACKLAM_HIGH:
        q = math.sqrt(-2.0 * math.log(1.0 - p))
        return -(
            (((((_ACKLAM_C[0] * q + _ACKLAM_C[1]) * q + _ACKLAM_C[2]) * q + _ACKLAM_C[3]) * q + _ACKLAM_C[4]) * q + _ACKLAM_C[5])
            / ((((_ACKLAM_D[0] * q + _ACKLAM_D[1]) * q + _ACKLAM_D[2]) * q + _ACKLAM_D[3]) * q + 1.0)
        )
    q = p - 0.5
    r = q * q
    return (
        (((((_ACKLAM_A[0] * r + _ACKLAM_A[1]) * r + _ACKLAM_A[2]) * r + _ACKLAM_A[3]) * r + _ACKLAM_A[4]) * r + _ACKLAM_A[5])
        * q
        / (((((_ACKLAM_B[0] * r + _ACKLAM_B[1]) * r + _ACKLAM_B[2]) * r + _ACKLAM_B[3]) * r + _ACKLAM_B[4]) * r + 1.0)
    )


def _qnorm(p):
    """Standard normal quantile, checked against R's ``qnorm``."""
    if math.isnan(p):
        return math.nan
    if p == 0.0:
        return -math.inf
    if p == 1.0:
        return math.inf
    if p < 0.0 or p > 1.0:
        return math.nan
    z0 = _acklam(p)
    if abs(z0) > 6.0:
        return z0
    z = z0
    for _ in range(4):
        cdf = _pnorm(z)
        err = cdf - p
        if err == 0.0:
            break
        pdf = math.exp(-0.5 * z * z) * _INV_SQRT_2PI
        if pdf == 0.0 or not math.isfinite(pdf):
            break
        denom = pdf + 0.5 * z * err
        if denom == 0.0 or not math.isfinite(denom):
            break
        step = err / denom
        if not math.isfinite(step):
            break
        z = z - step
        if abs(step) <= 1e-15 * (1.0 + abs(z)):
            break
    if abs(z - z0) > 1e-7:
        return z0
    return z


def _gamma_series(a, x):
    term = 1.0 / a
    total = term
    for n in range(1, 10000):
        term *= x / (a + n)
        total += term
        if abs(term) < abs(total) * 1e-16:
            break
    return total * math.exp(-x + a * math.log(x) - math.lgamma(a))


def _gamma_cf(a, x):
    tiny = 1e-300
    b = x + 1.0 - a
    c = 1.0 / tiny
    d = 1.0 / b
    h = d
    for i in range(1, 10000):
        an = -i * (i - a)
        b += 2.0
        d = an * d + b
        if abs(d) < tiny:
            d = tiny
        c = b + an / c
        if abs(c) < tiny:
            c = tiny
        d = 1.0 / d
        delta = d * c
        h *= delta
        if abs(delta - 1.0) < 1e-15:
            break
    return math.exp(-x + a * math.log(x) - math.lgamma(a)) * h


def _pgamma(x, shape):
    if math.isnan(x) or math.isnan(shape):
        return math.nan
    if x <= 0:
        return 0.0
    if x < shape + 1.0:
        return _gamma_series(shape, x)
    return 1.0 - _gamma_cf(shape, x)


def _pchisq(x, df):
    return _pgamma(x / 2.0, df / 2.0)


def _dchisq(x, df):
    if x <= 0:
        return 0.0
    return math.exp(
        -math.lgamma(df / 2.0) - (df / 2.0) * math.log(2.0) + (df / 2.0 - 1.0) * math.log(x) - x / 2.0
    )


def _qchisq(p, df):
    """Chi-squared quantile. Newton inversion of the regularized gamma, started from Wilson-Hilferty."""
    if math.isnan(p) or math.isnan(df):
        return math.nan
    if p == 0.0:
        return 0.0
    if p == 1.0:
        return math.inf
    if p < 0.0 or p > 1.0 or df <= 0:
        return math.nan
    z = _qnorm(p)
    pivot = 1.0 - 2.0 / (9.0 * df) + z * math.sqrt(2.0 / (9.0 * df))
    guess = df * pivot ** 3 if pivot > 0 else df * 0.5
    if not math.isfinite(guess) or guess <= 0:
        guess = df
    x = guess
    for _ in range(40):
        cdf = _pchisq(x, df)
        pdf = _dchisq(x, df)
        if pdf <= 0 or not math.isfinite(pdf):
            break
        step = (cdf - p) / pdf
        if not math.isfinite(step):
            break
        x_new = x - step
        if x_new <= 0:
            x_new = x / 2.0
        if abs(x_new - x) <= 1e-14 * (1.0 + abs(x)):
            x = x_new
            break
        x = x_new
    # Newton can stop a little short in the far tail. Bisect around the guess.
    lo, hi = x, x
    for _ in range(80):
        if _pchisq(lo, df) <= p:
            break
        lo *= 0.5
    else:
        lo = 0.0
    for _ in range(80):
        if _pchisq(hi, df) >= p:
            break
        hi *= 2.0
    for _ in range(80):
        mid = 0.5 * (lo + hi)
        if _pchisq(mid, df) < p:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def _r_quantile(values, probs):
    """R ``quantile`` type 7, including the small fuzz that snaps to an integer index."""
    array = np.asarray(values, dtype=float).reshape(-1)
    array = array[np.isfinite(array)]
    array.sort()
    n = int(array.size)
    fuzz = 4 * np.finfo(float).eps
    out = []
    for prob in probs:
        if n == 0 or not 0 <= prob <= 1:
            out.append(math.nan)
            continue
        nppm = 1 + (n - 1) * float(prob)
        j = math.floor(nppm + fuzz)
        if abs(nppm - j) < fuzz:
            h = 0.0
        else:
            h = nppm - j
        if j < 1:
            j = 1
        left = array[j - 1]
        if h == 0.0:
            out.append(float(left))
        else:
            right_index = min(j, n - 1)
            out.append(float((1.0 - h) * left + h * array[right_index]))
    return out


def _jackknife_influence(data, statistic, stype, index, strata, **kwargs):
    """Delete-one jackknife influence, ``usual.jack`` in boot.

    Antithetic resampling calls ``empinf`` when ``L`` is missing. With the
    default index statistic that path is this jackknife. ``stype="w"`` uses
    the infinitesimal jackknife instead, which is ``_inf_jack``.
    """
    n = _nrow(data)
    influence = np.zeros(n, dtype=float)
    codes = _as_numeric_strata(strata, n)
    if stype == "w":
        sizes = np.asarray(_stratum_sizes(codes), dtype=float)
        w0 = 1.0 / sizes
        observed = float(_as_statistic(statistic(data, w0, **kwargs))[index])
        for i in range(n):
            weights = w0.copy()
            weights[i] = 0.0
            group = np.asarray(codes) == codes[i]
            weights[group] = weights[group] / np.sum(weights[group])
            influence[i] = (np.sum(group) - 1) * (
                observed - float(_as_statistic(statistic(data, weights, **kwargs))[index])
            )
    elif stype == "f":
        frequencies = np.ones(n, dtype=float)
        observed = float(_as_statistic(statistic(data, frequencies, **kwargs))[index])
        for i in range(n):
            trial = frequencies.copy()
            trial[i] = 0.0
            group = np.asarray(codes) == codes[i]
            influence[i] = (np.sum(group) - 1) * (
                observed - float(_as_statistic(statistic(data, trial, **kwargs))[index])
            )
    else:
        original = np.arange(1, n + 1)
        observed = float(_as_statistic(statistic(data, original, **kwargs))[index])
        for i in range(n):
            trial = np.concatenate((original[:i], original[i + 1 :]))
            group = np.asarray(codes) == codes[i]
            influence[i] = (np.sum(group) - 1) * (
                observed - float(_as_statistic(statistic(data, trial, **kwargs))[index])
            )
    return influence


def _inf_jack(data, statistic, index, strata, eps=0.001, **kwargs):
    n = _nrow(data)
    codes = _as_numeric_strata(strata, n)
    eps = eps / n
    sizes = np.asarray(_stratum_sizes(codes), dtype=float)
    w_orig = 1.0 / sizes
    observed = float(_as_statistic(statistic(data, w_orig, **kwargs))[index])
    influence = np.zeros(n, dtype=float)
    for i in range(n):
        weights = w_orig.copy()
        group = np.asarray(codes) == codes[i]
        weights[group] = (1 - eps) * weights[group]
        weights[i] = weights[i] + eps
        influence[i] = (float(_as_statistic(statistic(data, weights, **kwargs))[index]) - observed) / eps
    return influence


def _empinf_for_antithetic(data, statistic, stype, strata, **kwargs):
    """The ``empinf`` branch ``boot`` uses when ``L`` is omitted.

    No bootstrap object and no ``t`` have been built yet, so ``stype="w"``
    selects the infinitesimal jackknife and every other ``stype`` selects
    the delete-one jackknife.
    """
    if stype == "w":
        return _inf_jack(data, statistic, 0, strata, **kwargs)
    return _jackknife_influence(data, statistic, stype, 0, strata, **kwargs)


def _lm_coef(y, x):
    """Coefficients of ``lm(y ~ x)``, intercept first. ``x`` may be 1-d or 2-d."""
    y = np.asarray(y, dtype=float).reshape(-1)
    x = np.asarray(x, dtype=float)
    if x.ndim == 1:
        x = x.reshape(-1, 1)
    design = np.column_stack((np.ones(y.size), x))
    coef, _, _, _ = np.linalg.lstsq(design, y, rcond=None)
    return coef


def _empinf_reg(boot_out, t):
    finite = np.isfinite(np.asarray(t, dtype=float))
    t = np.asarray(t, dtype=float)[finite]
    n = _nrow(boot_out.data)
    strata = boot_out.strata
    if strata is None:
        codes = [1] * n
    else:
        codes = _as_numeric_strata(strata, n)
    sizes = _tabulate(codes, max(codes))
    frequencies = _freq_array(boot_array(boot_out, indices=True))[finite, :]
    scale = np.asarray([sizes[code - 1] for code in codes], dtype=float)
    design = frequencies / scale
    first = []
    seen = set()
    for i, code in enumerate(codes):
        if code not in seen:
            seen.add(code)
            first.append(i)
    keep = [i for i in range(n) if i not in first]
    beta = _lm_coef(t, design[:, keep])[1:]
    influence = np.zeros(n, dtype=float)
    influence[keep] = beta
    means = {}
    for code in _stratum_ids(codes):
        group = [i for i, value in enumerate(codes) if value == code]
        means[code] = float(np.mean(influence[group]))
    for i, code in enumerate(codes):
        influence[i] -= means[code]
    return influence


def _lookup_influence(boot_out, index, t, supplied, **kwargs):
    if supplied is not None:
        return np.asarray(supplied, dtype=float).reshape(-1)
    if t is not None:
        return _empinf_reg(boot_out, t if np.ndim(t) == 1 else np.asarray(t)[:, 0])
    stype = getattr(boot_out, "stype", "w")
    if stype == "w":
        return _inf_jack(boot_out.data, boot_out.statistic, index, boot_out.strata, **kwargs)
    replicates = int(np.sum(boot_out.R))
    n = _nrow(boot_out.data)
    sim = boot_out.sim
    if sim not in ("parametric", "permutation"):
        if replicates < n:
            return _jackknife_influence(
                boot_out.data, boot_out.statistic, stype, index, boot_out.strata, **kwargs
            )
        column = np.asarray(boot_out.t, dtype=float)[:, index]
        return _empinf_reg(boot_out, column)
    return _jackknife_influence(
        boot_out.data, boot_out.statistic, stype, index, boot_out.strata, **kwargs
    )


def _cens_case(n, strata, replicates):
    output = np.full((replicates, n), math.nan)
    codes = list(dict.fromkeys(strata))
    for code in codes:
        group = _positions(strata, code)
        drawn = _sample_positions(group, len(group) * replicates, replace=True)
        _fill_columns(output, [g - 1 for g in group], drawn)
    return output


def _statistic_name(statistic):
    name = getattr(statistic, "__name__", "statistic")
    if name == "<lambda>":
        return "statistic"
    return name


def _data_label(data):
    array = np.asarray(data)
    if array.ndim == 1 and array.dtype.kind in "iuf":
        values = array.astype(float)
        if values.size and np.all(values == np.arange(1, values.size + 1)):
            return f"1:{values.size}"
    if isinstance(data, dict):
        return "data"
    text = repr(data)
    if len(text) > 60:
        return "data"
    return text


def _r_label(r_value, scalar):
    if scalar:
        return str(int(r_value))
    return "c(" + ", ".join(str(int(value)) for value in np.asarray(r_value).reshape(-1)) + ")"


def _build_call(supplied_text):
    body = ", ".join(supplied_text)
    return f"boot({body})"


def _format_one(value, digits):
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return "NA"
    if value == math.inf:
        return "Inf"
    if value == -math.inf:
        return "-Inf"
    value = float(value)
    if value == 0:
        return "0"
    magnitude = abs(value)
    power = math.floor(math.log10(magnitude))
    if power >= digits or power < -4:
        decimals = max(digits - 1, 0)
        text = f"{value:.{decimals}e}"
        mantissa, exponent = text.split("e")
        mantissa = mantissa.rstrip("0").rstrip(".")
        return f"{mantissa}e{int(exponent):+03d}"
    decimals = max(digits - power - 1, 0)
    text = f"{value:.{decimals}f}"
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text


def _format_column(values, digits):
    values = [float(value) for value in values]
    finite = [abs(value) for value in values if math.isfinite(value) and value != 0]
    negative = any(value < 0 for value in values if math.isfinite(value))
    if len(values) == 1 or not finite:
        texts = [_format_one(value, digits) for value in values]
    else:
        power = max(math.floor(math.log10(value)) for value in finite)
        decimals = max(digits - power - 1, 0)
        if power >= digits or min(math.floor(math.log10(value)) for value in finite) < -4:
            texts = [_format_one(value, digits) for value in values]
        else:
            texts = []
            for value in values:
                if not math.isfinite(value):
                    texts.append(_format_one(value, digits))
                else:
                    texts.append(f"{value:.{decimals}f}")
    if negative:
        texts = [(" " + text) if not text.startswith("-") and text not in ("NA", "Inf") else text for text in texts]
    width = max(len(text) for text in texts)
    return [text.rjust(width) for text in texts]


def _print_numeric_matrix(rows, rownames, colnames, digits):
    columns = []
    for j in range(len(colnames)):
        columns.append(_format_column([row[j] for row in rows], digits))
    widths = []
    for j, name in enumerate(colnames):
        widths.append(max(len(name), max(len(text) for text in columns[j])))
    name_width = max(len(name) for name in rownames) if rownames else 0
    gap = " "
    header = " " * name_width + gap + gap.join(name.rjust(widths[j]) for j, name in enumerate(colnames))
    lines = [header]
    for i, row_name in enumerate(rownames):
        cells = [columns[j][i].rjust(widths[j]) for j in range(len(colnames))]
        lines.append(row_name.ljust(name_width) + gap + gap.join(cells))
    return "\n".join(lines)


def _summary_rows(boot_out, index, digits):
    replicates = np.asarray(boot_out.t, dtype=float)
    if replicates.ndim == 1:
        replicates = replicates.reshape(-1, 1)
    if index is None:
        index = list(range(1, replicates.shape[1] + 1))
    elif isinstance(index, (int, np.integer)):
        index = [int(index)]
    else:
        index = [int(value) for value in index]
    selected = replicates[:, [i - 1 for i in index]]
    all_missing = [bool(np.all(~np.isfinite(selected[:, j]))) for j in range(selected.shape[1])]
    missing_index = [index[j] for j, flag in enumerate(all_missing) if flag]
    kept_index = [index[j] for j, flag in enumerate(all_missing) if not flag]
    kept = selected[:, [j for j, flag in enumerate(all_missing) if not flag]]
    if kept_index and kept.size:
        kept = np.asarray(kept, dtype=float)
        if kept.ndim == 1:
            kept = kept.reshape(-1, 1)
    row_names = [f"t{i}*" for i in kept_index]
    call = boot_out.call
    weighted = call is not None and getattr(call, "weights", None) is not None
    t0 = getattr(boot_out, "t0", None)
    table = None
    colnames = None
    if kept_index:
        if t0 is None:
            if not weighted:
                means = [_r_mean(kept[:, j]) for j in range(kept.shape[1])]
                errors = [math.sqrt(_r_var(kept[:, j])) for j in range(kept.shape[1])]
                table = list(zip(means, errors))
                colnames = ["mean", "std. error"]
            else:
                moments = [_ratio_moments(boot_out, i) for i in kept_index]
                table = [(item[0], math.sqrt(item[1])) for item in moments]
                colnames = ["mean", "std. error"]
        else:
            original = np.asarray(t0, dtype=float).reshape(-1)
            original = original[[i - 1 for i in kept_index]]
            if not weighted:
                bias = [_r_mean(kept[:, j]) - original[j] for j in range(kept.shape[1])]
                errors = [math.sqrt(_r_var(kept[:, j])) for j in range(kept.shape[1])]
                table = list(zip(original.tolist(), bias, errors))
                colnames = ["original", " bias  ", " std. error"]
            else:
                moments = [_ratio_moments(boot_out, i) for i in kept_index]
                means = [_r_mean(kept[:, j]) for j in range(kept.shape[1])]
                table = [
                    (original[j], moments[j][0] - original[j], math.sqrt(moments[j][1]), means[j])
                    for j in range(len(kept_index))
                ]
                colnames = ["original", " bias  ", " std. error", " mean(t*)"]
    return table, colnames, row_names, missing_index


def _imp_weights(boot_out, defensive=True):
    r_value = np.asarray(boot_out.R, dtype=int).reshape(-1)
    if r_value.size == 1:
        defensive = False
    frequencies = _freq_array(boot_array(boot_out, indices=True))
    n = frequencies.shape[1]
    codes = _as_numeric_strata(boot_out.strata, n)
    q = np.ones(n, dtype=float)
    p = np.asarray(boot_out.weights, dtype=float)
    if r_value.size == 1 and np.all(np.abs(p - q) / p < 1e-10):
        return np.ones(int(r_value[0]), dtype=float)
    q = np.asarray(_normalize(q, codes), dtype=float)
    log_q = frequencies @ np.log(q)
    if p.ndim == 1:
        p = p.reshape(1, -1)
    p = np.vstack([_normalize(row, codes) for row in p])
    n_sets = r_value.size
    log_p = np.empty((int(np.sum(r_value)), n_sets), dtype=float)
    for i in range(n_sets):
        positive = np.flatnonzero(p[i, :] > 0)
        log_p[:, i] = frequencies[:, positive] @ np.log(p[i, positive])
    if defensive:
        share = r_value / np.sum(r_value)
        return 1.0 / (np.exp(log_p - log_q.reshape(-1, 1)) @ share)
    index = np.repeat(np.arange(n_sets), r_value)
    rows = np.arange(int(np.sum(r_value)))
    return np.exp(log_q - log_p[rows, index])


def _ratio_moments(boot_out, index):
    t = np.asarray(boot_out.t, dtype=float)[:, index - 1]
    weights = _imp_weights(boot_out)
    finite = np.isfinite(t)
    t = t[finite]
    weights = np.asarray(weights, dtype=float)[finite]
    if _const(weights):
        return (_r_mean(t), _r_var(t))
    y = t * weights
    ratio_mean = float(np.sum(y) / np.sum(weights))
    ratio_var = float(np.sum(weights / np.sum(weights) * (t - ratio_mean) ** 2))
    return (ratio_mean, ratio_var)


def _format_boot(boot_out, digits, index):
    sim = boot_out.sim
    call = boot_out.call
    kind = _find_type(boot_out)
    lines = []
    if kind == "boot":
        if sim == "parametric":
            heading = "\nPARAMETRIC BOOTSTRAP\n\n"
        elif sim == "antithetic":
            if call.strata is None:
                heading = "\nANTITHETIC BOOTSTRAP\n\n"
            else:
                heading = "\nSTRATIFIED ANTITHETIC BOOTSTRAP\n\n"
        elif sim == "permutation":
            if call.strata is None:
                heading = "\nDATA PERMUTATION\n\n"
            else:
                heading = "\nSTRATIFIED DATA PERMUTATION\n\n"
        elif sim == "balanced":
            if call.strata is None and call.weights is None:
                heading = "\nBALANCED BOOTSTRAP\n\n"
            elif call.strata is None:
                heading = "\nBALANCED WEIGHTED BOOTSTRAP\n\n"
            elif call.weights is None:
                heading = "\nSTRATIFIED BALANCED BOOTSTRAP\n\n"
            else:
                heading = "\nSTRATIFIED WEIGHTED BALANCED BOOTSTRAP\n\n"
        else:
            if call.strata is None and call.weights is None:
                heading = "\nORDINARY NONPARAMETRIC BOOTSTRAP\n\n"
            elif call.strata is None:
                heading = "\nWEIGHTED BOOTSTRAP\n\n"
            elif call.weights is None:
                heading = "\nSTRATIFIED BOOTSTRAP\n\n"
            else:
                heading = "\nSTRATIFIED WEIGHTED BOOTSTRAP\n\n"
        lines.append(heading)
    elif kind == "tilt.boot":
        if sim == "balanced":
            lines.append("\nBALANCED TILTED BOOTSTRAP\n\n")
        else:
            lines.append("\nTILTED BOOTSTRAP\n\n")
    elif kind == "tsboot":
        lines.append("\nBLOCK BOOTSTRAP FOR TIME SERIES\n\n")
    elif kind == "censboot":
        lines.append("\nCASE RESAMPLING BOOTSTRAP FOR CENSORED DATA\n\n")
    else:
        warnings.warn('unknown type of "boot" object')
    # dput ends with a newline, and the statistics heading is preceded by two more.
    lines.append("\nCall:\n")
    lines.append((call.text if call is not None else "NULL") + "\n")
    lines.append("\n\nBootstrap Statistics :\n")
    table, colnames, row_names, missing_index = _summary_rows(boot_out, index, digits)
    if table is not None:
        lines.append(_print_numeric_matrix(table, row_names, colnames, digits))
        lines.append("\n")
    for missing in missing_index:
        lines.append(f"WARNING: All values of t{missing}* are NA\n")
    return "".join(lines)


def _find_type(boot_out):
    kind = getattr(boot_out, "boot_type", None)
    if kind:
        return kind
    return "boot"


def _default_ran_gen(data, _mle):
    return data


def boot(
    data,
    statistic,
    R,
    sim=_MISSING,
    stype=_MISSING,
    strata=_MISSING,
    L=_MISSING,
    m=_MISSING,
    weights=_MISSING,
    ran_gen=_MISSING,
    mle=_MISSING,
    simple=_MISSING,
    parallel=_MISSING,
    ncpus=_MISSING,
    cl=_MISSING,
    **kwargs,
):
    """Generate bootstrap replicates of ``statistic`` applied to ``data``.

    ``sim`` is ``"ordinary"``, ``"balanced"``, ``"antithetic"``,
    ``"permutation"``, or ``"parametric"``. ``stype`` says whether the
    second argument of ``statistic`` is an index vector (``"i"``), a
    frequency vector (``"f"``), or within-stratum weights (``"w"``).
    Indices are 1-based. The checked path is serial: ``parallel="no"``.
    """
    sim_supplied = sim is not _MISSING
    stype_supplied = stype is not _MISSING
    strata_supplied = strata is not _MISSING
    l_supplied = L is not _MISSING
    m_supplied = m is not _MISSING
    weights_supplied = weights is not _MISSING
    ran_supplied = ran_gen is not _MISSING
    mle_supplied = mle is not _MISSING
    simple_supplied = simple is not _MISSING
    parallel_supplied = parallel is not _MISSING

    if not sim_supplied:
        sim = "ordinary"
    if sim not in _SIM:
        raise ValueError(f"sim should be one of {', '.join(_SIM)}")
    stype = _match_arg("i" if not stype_supplied else stype, _STYPE, "stype")
    if not m_supplied:
        m = 0
    if not simple_supplied:
        simple = False
    if not ran_supplied:
        ran_gen = _default_ran_gen
    if not mle_supplied:
        mle = None
    if not l_supplied:
        L = None
    if not weights_supplied:
        weights = None
    parallel_value = "no" if not parallel_supplied else parallel
    parallel_value = _match_arg(parallel_value, _PARALLEL, "parallel")
    if parallel_value != "no":
        warnings.warn("only serial resampling is implemented; parallel was ignored", stacklevel=2)

    m_array = np.asarray(m, dtype=float).reshape(-1)
    if simple and (sim != "ordinary" or stype != "i" or float(np.sum(m_array)) != 0):
        warnings.warn(
            "'simple=TRUE' is only valid for 'sim=\"ordinary\", stype=\"i\", n=0', so ignored",
            stacklevel=2,
        )
        simple = False

    seed = _capture_rng()
    n = _nrow(data)
    original_strata = np.ones(n, dtype=int) if not strata_supplied else np.asarray(strata)
    codes = _as_numeric_strata(None if not strata_supplied else strata, n)
    r_scalar = np.isscalar(R) or (isinstance(R, np.ndarray) and np.asarray(R).ndim == 0)
    r_vec = [int(value) for value in np.atleast_1d(np.asarray(R, dtype=int))]
    total = int(sum(r_vec))

    influence = None if L is None else np.asarray(L, dtype=float).reshape(-1)
    pred = None
    if sim != "parametric":
        if sim == "antithetic" and influence is None:
            influence = _empinf_for_antithetic(data, statistic, stype, codes, **kwargs)
        if sim != "ordinary":
            m_array = np.asarray([0.0])
        elif np.any(m_array < 0):
            raise ValueError("negative value of 'm' supplied")
        if m_array.size != 1 and m_array.size != len(_stratum_ids(codes)):
            raise ValueError("length of 'm' incompatible with 'strata'")
        prepared_weights = None
        if sim in ("ordinary", "balanced"):
            if weights is not None and np.asarray(weights).ndim == 2:
                if np.asarray(weights).shape[0] != len(r_vec):
                    raise ValueError("dimensions of 'R' and 'weights' do not match")
            if weights is not None:
                matrix = _reshape_weights(weights, n, len(r_vec))
                prepared_weights = np.vstack([_normalize(matrix[:, j], codes) for j in range(matrix.shape[1])])
        if not simple:
            indices = _index_array(
                n,
                r_vec if prepared_weights is not None else total,
                sim,
                codes,
                m_array,
                None if influence is None else influence,
                prepared_weights,
            )
        else:
            indices = None
        if stype == "f":
            original = np.ones(n, dtype=float)
        elif stype == "w":
            original = 1.0 / np.asarray(_stratum_sizes(codes), dtype=float)
        else:
            original = np.arange(1, n + 1)
        if float(np.sum(m_array)) > 0:
            t0 = _as_statistic(statistic(data, original, np.ones(int(np.sum(m_array))), **kwargs))
        else:
            t0 = _as_statistic(statistic(data, original, **kwargs))
        if indices is not None and indices.shape[1] > n:
            pred = np.asarray(indices[:, n:], dtype=float)
            indices = np.asarray(indices[:, :n], dtype=float)
        if stype in ("f", "w"):
            frequencies = _freq_array(indices).astype(float)
            if stype == "w":
                frequencies = frequencies / np.asarray(_stratum_sizes(codes), dtype=float)
            passed = frequencies
        else:
            passed = indices

        def evaluate(replicate):
            if simple:
                drawn = _index_array(n, 1, sim, codes, m_array, influence, prepared_weights)
                return statistic(data, np.asarray(drawn).reshape(-1), **kwargs)
            if float(np.sum(m_array)) > 0:
                return statistic(data, passed[replicate], pred[replicate], **kwargs)
            return statistic(data, passed[replicate], **kwargs)

        returned_weights = prepared_weights
        if returned_weights is None:
            returned_weights = 1.0 / np.asarray(_stratum_sizes(codes), dtype=float)
        elif returned_weights.shape[0] == 1:
            returned_weights = returned_weights.reshape(-1)
    else:
        t0 = _as_statistic(statistic(data, **kwargs))

        def evaluate(_replicate):
            simulated = ran_gen(data, mle)
            return statistic(simulated, **kwargs)

        returned_weights = None
        influence = None

    results = [_as_statistic(evaluate(replicate)) for replicate in range(total)]
    width = int(t0.size)
    t_star = np.empty((total, width), dtype=float)
    for replicate, value in enumerate(results):
        if value.size != width:
            raise ValueError("statistic returned a result of a different length")
        t_star[replicate, :] = value

    parts = [("data", _data_label(data)), ("statistic", _statistic_name(statistic)), ("R", _r_label(R, r_scalar))]
    if sim_supplied:
        parts.append(("sim", f'"{sim}"'))
    if stype_supplied:
        parts.append(("stype", f'"{stype}"'))
    if strata_supplied:
        parts.append(("strata", "strata"))
    if weights_supplied:
        parts.append(("weights", "weights"))
    if m_supplied and float(np.sum(np.asarray(m, dtype=float))) != 0:
        parts.append(("m", str(m)))
    if l_supplied:
        parts.append(("L", "L"))
    if ran_supplied:
        parts.append(("ran.gen", _statistic_name(ran_gen)))
    if mle_supplied:
        parts.append(("mle", "mle"))
    if simple_supplied:
        parts.append(("simple", "TRUE" if simple else "FALSE"))
    call = BootCall(
        _build_call([f"{name} = {text}" for name, text in parts]),
        {
            "strata": original_strata if strata_supplied else None,
            "weights": weights if weights_supplied else None,
            "sim": sim if sim_supplied else None,
        },
    )
    values = {
        "t0": t0.copy(),
        "t": t_star,
        "R": int(R) if r_scalar else np.asarray(r_vec, dtype=int),
        "data": data,
        "seed": seed,
        "statistic": statistic,
        "sim": sim,
        "call": call,
    }
    order = ["t0", "t", "R", "data", "seed", "statistic", "sim", "call"]
    if sim == "parametric":
        values["ran.gen"] = ran_gen
        values["mle"] = mle
        order.extend(["ran.gen", "mle"])
    elif sim == "antithetic":
        values["stype"] = stype
        values["strata"] = np.asarray(original_strata)
        values["L"] = np.asarray(influence, dtype=float)
        order.extend(["stype", "strata", "L"])
    elif sim == "ordinary":
        values["stype"] = stype
        values["strata"] = np.asarray(original_strata)
        values["weights"] = np.asarray(returned_weights, dtype=float)
        order.extend(["stype", "strata", "weights"])
        if pred is not None:
            values["pred.i"] = pred
            order.append("pred.i")
    elif sim == "balanced":
        values["stype"] = stype
        values["strata"] = np.asarray(original_strata)
        values["weights"] = np.asarray(returned_weights, dtype=float)
        order.extend(["stype", "strata", "weights"])
    else:
        values["stype"] = stype
        values["strata"] = np.asarray(original_strata)
        order.extend(["stype", "strata"])
    return BootResult(order, values, call, boot_type="boot")


def c_boot(*args, recursive=True):
    """Combine bootstrap objects that have the same components.

    ``R`` becomes the sum of the replicate counts and ``t`` is stacked.
    ``recursive`` is accepted because it is part of R's ``c`` method and
    is not used.
    """
    del recursive
    if not args:
        raise ValueError("no bootstrap objects to combine")
    names = [tuple(item.names()) for item in args]
    if any(item != names[0] for item in names):
        raise ValueError('arguments are not all the same type of "boot" object')
    first = args[0]
    values = {name: getattr(first, name) for name in first.names()}
    values["R"] = int(sum(int(np.sum(item.R)) for item in args))
    values["t"] = np.vstack([np.asarray(item.t, dtype=float) for item in args])
    return BootResult(first.names(), values, first.call, boot_type=first.boot_type)


def boot_array(boot_out, indices=False):
    """Recreate the frequency array, or the index array when ``indices`` is true.

    The generator is restored to ``boot_out.seed`` for the recreation and
    then put back. Parametric bootstraps have no index array.
    """
    saved = _capture_rng()
    try:
        _restore_rng(boot_out.seed)
        n = _nrow(boot_out.data)
        sim = boot_out.sim
        kind = _find_type(boot_out)
        if kind == "tsboot":
            raise NotImplementedError("boot.array for tsboot is outside this translation")
        if kind == "censboot":
            if sim != "ordinary":
                raise ValueError("boot.array not implemented for this object")
            codes = _as_numeric_strata(boot_out.strata, n)
            out = _cens_case(n, codes, int(np.sum(boot_out.R)))
        else:
            if sim == "parametric":
                raise ValueError("array cannot be found for parametric bootstrap")
            codes = _as_numeric_strata(boot_out.strata, n)
            if kind == "tilt.boot":
                weights = boot_out.weights
            else:
                weights = None if boot_out.call.weights is None else boot_out.weights
            influence = getattr(boot_out, "L", None)
            out = _index_array(n, boot_out.R, sim, codes, 0, influence, weights)
        if not indices:
            out = _freq_array(out)
        return out
    finally:
        _restore_rng(saved)


def print_boot(x, digits=7, index=None, **_ignored):
    """Print the bootstrap heading, the call, and the bias and standard error.

    The same text is returned. ``index`` is 1-based, matching R.
    """
    text = _format_boot(x, digits=7 if digits is None else digits, index=index)
    print(text, end="" if text.endswith("\n") else "\n")
    return text


def _histogram_breaks(t, t0, nclass):
    if t0 is None:
        return _pretty_breaks(t, nclass)
    low = float(np.min(t))
    high = float(np.max(t))
    if t0 < low:
        low = float(t0)
    elif t0 > high:
        high = float(t0)
    span = high - low
    low -= 0.05 * span
    high += 0.05 * span
    width = (high - low) / (nclass - 2)
    n1 = math.ceil((float(t0) - low) / width)
    n2 = math.ceil((high - float(t0)) / width)
    return np.asarray([float(t0) + k * width for k in range(-n1, n2 + 1)], dtype=float)


def _pretty_breaks(t, nclass):
    """Breaks from R's ``pretty(range(x), n=nclass, min.n=1)`` for a short range.

    Used only when ``t`` is supplied without ``t0``. The ordinary plot path
    passes ``t0`` and uses the explicit breakpoint formula instead.
    """
    low = float(np.min(t))
    high = float(np.max(t))
    if low == high:
        low -= 1
        high += 1
    span = high - low
    raw = span / max(nclass, 1)
    power = 10 ** math.floor(math.log10(raw))
    error = raw / power
    if error <= 1.5:
        step = power
    elif error <= 3:
        step = 2 * power
    elif error <= 7:
        step = 5 * power
    else:
        step = 10 * power
    start = math.floor(low / step) * step
    stop = math.ceil(high / step) * step
    count = int(round((stop - start) / step))
    return start + step * np.arange(count + 1, dtype=float)


def _hist_counts(t, breaks):
    counts = np.zeros(len(breaks) - 1, dtype=int)
    for value in np.asarray(t, dtype=float):
        if value < breaks[0] or value > breaks[-1] or not math.isfinite(value):
            continue
        if value == breaks[0]:
            counts[0] += 1
            continue
        bin_index = int(np.searchsorted(breaks, value, side="left") - 1)
        counts[bin_index] += 1
    return counts


def _qq_coordinates(theoretical, observed):
    sx = np.sort(np.asarray(theoretical, dtype=float))
    sy = np.sort(np.asarray(observed, dtype=float))
    if sy.size < sx.size:
        sx = _approx(sx, sy.size)
    elif sy.size > sx.size:
        sy = _approx(sy, sx.size)
    return sx, sy


def _approx(values, n):
    """R ``approx(seq_along(values), values, n=n)`` with the default linear rule."""
    if n == values.size:
        return values.copy()
    if values.size == 1:
        return np.repeat(values, n)
    x = np.arange(1, values.size + 1, dtype=float)
    xout = np.linspace(1, values.size, n)
    return np.interp(xout, x, values)


def _plot_series(t, t0, qdist, nclass, df):
    finite = np.asarray(t, dtype=float)
    finite = finite[np.isfinite(finite)]
    eps = min(1e-8, _r_mean(finite) / 1e6) if finite.size else 1e-8
    if finite.size and _const(finite, eps):
        return {"constant": True, "mean": _r_mean(finite), "t": finite, "t0": t0}
    if nclass is None:
        nclass = min(max(math.ceil(finite.size / 25), 10), 100)
    nclass = int(nclass)
    breaks = _histogram_breaks(finite, None if t0 is None else float(t0), nclass)
    counts = _hist_counts(finite, breaks)
    widths = np.diff(breaks)
    density = counts / (finite.size * widths)
    replicates = finite.size if t0 is None else None
    # R builds the theoretical quantiles from boot.out$R even if some t are not finite.
    # The caller passes that count separately when it differs. Here length(t) is the
    # finite count, and plot_boot overwrites qq with the original R when needed.
    probability_n = finite.size
    probs = np.arange(1, probability_n + 1, dtype=float) / (probability_n + 1)
    if qdist == "chisq":
        if df is None:
            raise ValueError("df is required when qdist is 'chisq'")
        theoretical = np.asarray([_qchisq(float(p), float(df)) for p in probs], dtype=float)
        intercept, slope = 0.0, 1.0
        qlab = f"Quantiles of Chi-squared({df})"
    else:
        if qdist != "norm":
            warnings.warn(f"'{qdist}' distribution not supported: using normal instead", stacklevel=2)
        theoretical = np.asarray([_qnorm(float(p)) for p in probs], dtype=float)
        intercept = _r_mean(finite)
        slope = math.sqrt(_r_var(finite))
        qlab = "Quantiles of Standard Normal"
    qq_x, qq_y = _qq_coordinates(theoretical, finite)
    return {
        "constant": False,
        "t": finite,
        "t0": None if t0 is None else float(t0),
        "breaks": breaks,
        "counts": counts,
        "density": density,
        "nclass": nclass,
        "qq_x": qq_x,
        "qq_y": qq_y,
        "line_intercept": intercept,
        "line_slope": slope,
        "qlab": qlab,
        "qdist": "chisq" if qdist == "chisq" else "norm",
        "replicates_note": replicates,
    }


def _draw_histogram(ax, series):
    breaks = series["breaks"]
    ax.bar(
        breaks[:-1],
        series["density"],
        width=np.diff(breaks),
        align="edge",
        facecolor="white",
        edgecolor="black",
    )
    if series["t0"] is not None:
        ax.axvline(series["t0"], linestyle="--", color="black")
    ax.set_xlabel("t*")
    ax.set_ylabel("Density")


def _draw_qq(ax, series):
    ax.plot(series["qq_x"], series["qq_y"], linestyle="none", marker="o", color="black")
    intercept = series["line_intercept"]
    slope = series["line_slope"]
    xs = np.asarray(series["qq_x"], dtype=float)
    ax.plot(xs, intercept + slope * xs, linestyle="--", color="black")
    ax.set_xlabel(series["qlab"])
    ax.set_ylabel("t*")


def plot_boot(x, index=1, t0=None, t=None, jack=False, qdist="norm", nclass=None, df=None, **kwargs):
    """Draw a histogram and a Q-Q plot of bootstrap replicates.

    When ``jack`` is true, a jackknife-after-bootstrap panel is added.
    The returned dict is the series the figure is built from: histogram
    breaks, counts and density, and the Q-Q coordinates. R returns the
    bootstrap object invisibly.
    """
    import matplotlib.pyplot as plt

    supplied_t = t is not None
    if t is None:
        replicates = np.asarray(x.t, dtype=float)
        t = replicates[:, index - 1]
        if t0 is None:
            t0 = float(np.asarray(x.t0, dtype=float).reshape(-1)[index - 1])
    else:
        t = np.asarray(t, dtype=float).reshape(-1)
    # qnorm((1:R)/(R+1)) uses the replicate count stored on the bootstrap,
    # not the number of finite values left after the histogram filter.
    original_r = int(np.sum(x.R))
    series = _plot_series(t, None if t0 is None else float(t0), qdist, nclass, df)
    if not series["constant"]:
        probs = np.arange(1, original_r + 1, dtype=float) / (original_r + 1)
        if series["qdist"] == "chisq":
            theoretical = np.asarray([_qchisq(float(p), float(df)) for p in probs])
        else:
            theoretical = np.asarray([_qnorm(float(p)) for p in probs])
        observed = np.asarray(t, dtype=float)
        observed = observed[np.isfinite(observed)]
        series["qq_x"], series["qq_y"] = _qq_coordinates(theoretical, observed)
    if series["constant"]:
        message = f'[1] "All values of t* are equal to  {series["mean"]}"'
        print(message)
        series["message"] = message
        return series
    if jack:
        fig, axes = plt.subplot_mosaic([["hist", "qq"], ["jack", "jack"]], figsize=(8, 8))
        _draw_histogram(axes["hist"], series)
        _draw_qq(axes["qq"], series)
        jack_series = jack_after_boot(x, index=index, t=t if supplied_t else None, ax=axes["jack"], **kwargs)
        series["jack"] = jack_series
        fig.tight_layout()
        series["figure"] = fig
    else:
        fig, axes = plt.subplots(1, 2, figsize=(8, 4))
        _draw_histogram(axes[0], series)
        _draw_qq(axes[1], series)
        fig.tight_layout()
        series["figure"] = fig
    return series


def jack_after_boot(
    boot_out,
    index=1,
    t=None,
    L=None,
    useJ=True,
    stinf=True,
    alpha=None,
    main="",
    ylab=None,
    ax=None,
    **kwargs,
):
    """Jackknife-after-bootstrap plot.

    The returned dict holds the sorted jackknife values, the delete-one
    percentile curves, and the horizontal bootstrap percentiles. Those
    are the coordinates Matplotlib draws. R returns ``NULL``.
    """
    import matplotlib.pyplot as plt

    supplied_t = t
    if isinstance(index, Sequence) and not isinstance(index, (str, bytes)):
        index = list(index)
    else:
        index = [index]
    if t is None:
        if len(index) > 1:
            warnings.warn("only first element of 'index' used", stacklevel=2)
        index = int(index[0])
        t = np.asarray(boot_out.t, dtype=float)[:, index - 1]
    else:
        index = int(index[0])
        t = np.asarray(t, dtype=float).reshape(-1)
    finite = np.isfinite(t)
    t_finite = t[finite]
    if alpha is None:
        alpha = [0.05, 0.1, 0.16, 0.5, 0.84, 0.9, 0.95]
        if ylab is None:
            ylab = "5, 10, 16, 50, 84, 90, 95 %-iles of (T*-t)"
    alpha = [float(value) for value in alpha]
    if ylab is None:
        ylab = "Percentiles of (T*-t)"
    n = _nrow(boot_out.data)
    frequencies = _freq_array(boot_array(boot_out, indices=True))[finite, :]
    percentiles = np.full((len(alpha), n), math.nan)
    jack = np.empty(n, dtype=float)
    for j in range(n):
        values = t_finite[frequencies[:, j] == 0]
        jack[j] = _r_mean(values)
        centered = np.asarray(_r_quantile(values, alpha), dtype=float) - jack[j]
        percentiles[:, j] = centered
    if not useJ:
        jack = _lookup_influence(boot_out, index - 1, supplied_t, L, **kwargs)
        if L is not None or (supplied_t is None and getattr(boot_out, "stype", None) == "w"):
            xtext = "infinitesimal jackknife value"
        else:
            xtext = "regression jackknife value"
    else:
        jack = (n - 1) * (_r_mean(jack) - jack)
        xtext = "jackknife value"
    if stinf:
        scale = math.sqrt(_r_var(jack))
        jack = jack / scale
        xtext = "standardized " + xtext
    top = float(np.nanmax(percentiles))
    bot = float(np.nanmin(percentiles))
    span = top - bot
    ylim = (bot - 0.35 * span, top + 0.1 * span)
    order = np.argsort(jack, kind="mergesort")
    ordered = percentiles[:, order]
    sorted_j = jack[order]
    horizontal = np.asarray(_r_quantile(t_finite, alpha), dtype=float) - _r_mean(t_finite)
    created = ax is None
    if created:
        _fig, ax = plt.subplots(figsize=(8, 5))
    ax.set_ylim(*ylim)
    for row in range(len(alpha)):
        ax.plot(sorted_j, ordered[row], linestyle="-", marker="*", color="black")
    for level in horizontal:
        ax.axhline(level, linestyle="--", color="black")
    label_rows = [
        bot - 0.08 * span,
        bot - 0.14 * span,
        bot - 0.20 * span,
        bot - 0.26 * span,
        bot - 0.32 * span,
    ]
    labels = []
    for position, observation in enumerate(order):
        row = position % 5
        text = str(int(observation) + 1)
        ax.text(sorted_j[position], label_rows[row], text, fontsize=6, ha="center", va="center")
        labels.append({"x": float(sorted_j[position]), "y": float(label_rows[row]), "text": text})
    ax.set_xlabel(xtext)
    ax.set_ylabel(ylab)
    if main:
        ax.set_title(main)
    series = {
        "J": sorted_j,
        "percentiles": ordered,
        "horizontal": horizontal,
        "order": order + 1,
        "labels": labels,
        "ylim": ylim,
        "xtext": xtext,
        "ylab": ylab,
        "alpha": alpha,
    }
    if created:
        ax.figure.tight_layout()
        series["figure"] = ax.figure
    return series
