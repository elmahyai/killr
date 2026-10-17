"""Bootstrap replicates for right-censored data.

This is the CRAN boot 1.3-32 ``censboot`` path: case resampling, the
conditional bootstrap, model-based resampling, and the weird bootstrap.
Survival curves are the numeric ``time`` and ``surv`` values R would pass
in. A Cox fit is an object with a coefficient vector. This module does not
fit a Cox model and does not import survival.

Random index draws use ``boot.rng``, which matches R's ``set.seed`` and
``sample.int``. The checked path is serial.
"""

from __future__ import annotations

import math
import warnings

import numpy as np

from boot import rng


class CensBoot:
    """Bootstrap result with the components R stores on a ``censboot`` object."""

    def __init__(self, t0, t, R, sim, data, seed, statistic, strata):
        self.t0 = t0
        self.t = t
        self.R = R
        self.sim = sim
        self.data = data
        self.seed = seed
        self.statistic = statistic
        self.strata = strata


def _r_random_seed():
    """``.Random.seed`` for the default Mersenne-Twister, Inversion, Rejection."""
    seed = np.empty(626, dtype=np.int32)
    seed[0] = np.int32(10403)
    seed[1] = np.int32(rng._mti)
    mt = np.asarray(rng._mt, dtype=np.uint32)
    seed[2:] = mt.view(np.int32)
    return seed


def _match_arg(value, choices):
    matches = [choice for choice in choices if choice.startswith(value)]
    if len(matches) == 1:
        return matches[0]
    listed = ", ".join(f'"{choice}"' for choice in choices)
    if not matches:
        raise ValueError(f"'parallel' should be one of {listed}")
    raise ValueError("there is more than one match in match.arg")


def _component(obj, *names, optional=False):
    """Read a survfit or coxph field under either R or Python spelling."""
    if isinstance(obj, dict):
        for name in names:
            if name in obj:
                return obj[name]
    else:
        for name in names:
            if hasattr(obj, name):
                return getattr(obj, name)
    if optional:
        return None
    raise AttributeError(names[0])


def _factor_codes(values):
    """1-based codes from ``tapply(seq_len(n), as.numeric(values))`` with no FUN.

    Missing ``FUN`` makes ``tapply`` return factor codes. Levels are the
    sorted numeric labels, so the smallest label becomes code 1.
    """
    flat = np.asarray(values).reshape(-1)
    if flat.dtype.kind in "iu":
        labels = [int(item) for item in flat.tolist()]
    else:
        labels = [float(item) for item in flat.tolist()]
    levels = sorted(set(labels))
    mapping = {level: index + 1 for index, level in enumerate(levels)}
    return [mapping[label] for label in labels]


def _prepare_strata(strata, n, sim):
    supplied = strata is not None
    if not supplied:
        values = np.ones((n, 2), dtype=float)
    else:
        values = np.asarray(strata)
        if values.ndim == 1:
            if values.shape[0] != n:
                raise ValueError("'strata' of wrong length")
        elif values.ndim == 2:
            if values.shape[0] != n:
                raise ValueError("'strata' of wrong length")
        else:
            raise ValueError("'strata' of wrong length")
    if values.ndim == 1:
        if sim not in ("weird", "ordinary"):
            values = np.column_stack([values, np.ones(n, dtype=float)])
    elif sim in ("weird", "ordinary"):
        values = np.asarray(values[:, 0])
    else:
        values = np.asarray(values[:, :2])
    stored = np.array(values, copy=True)
    if stored.ndim == 2:
        codes = np.column_stack([_factor_codes(stored[:, column]) for column in range(stored.shape[1])])
    else:
        codes = np.asarray(_factor_codes(stored), dtype=int)
    return stored, codes, supplied


def _statistic_vector(value):
    array = np.asarray(value, dtype=float)
    if array.ndim == 0:
        return array.reshape(1)
    return np.ravel(array, order="F")


def _row_subset(data, rows_1based):
    """``data[rows, ]``, dropping a single row the way R does."""
    rows = np.asarray(rows_1based, dtype=int)
    subset = data[rows - 1]
    if subset.ndim == 2 and subset.shape[0] == 1:
        return subset[0]
    return subset


def _revsort(values, index):
    """R ``revsort``: 1-based heapsort into descending order."""
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


def _normalize_probability(prob):
    weights = [float(value) for value in prob]
    total = 0.0
    for weight in weights:
        if not math.isfinite(weight):
            raise ValueError("NA in probability vector")
        if weight < 0.0:
            raise ValueError("negative probability")
        if weight > 0.0:
            total += weight
    if total <= 0.0:
        raise ValueError("too few positive probabilities")
    return [weight / total for weight in weights]


def _prob_sample_replace(weights, size):
    """R ``ProbSampleReplace`` after probabilities have been normalized."""
    n = len(weights)
    values = list(weights)
    perm = list(range(1, n + 1))
    _revsort(values, perm)
    for index in range(1, n):
        values[index] += values[index - 1]
    last = n - 1
    chosen = []
    for _ in range(size):
        draw = rng.unif()
        slot = last
        for index in range(last):
            if draw <= values[index]:
                slot = index
                break
        chosen.append(perm[slot])
    return chosen


def _walker_sample_replace(weights, size):
    """R ``walker_ProbSampleReplace`` for the default rejection sample kind."""
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
        slot = rng.unif_index(n)
        proposal = slot + rng.unif()
        if proposal < q[slot]:
            chosen.append(slot + 1)
        else:
            chosen.append(alias[slot] + 1)
    return chosen


def _weighted_index(n, size, prob):
    """``sample.int(n, size, replace=TRUE, prob=prob)``, 1-based."""
    weights = _normalize_probability(prob)
    if len(weights) != n:
        raise ValueError("incorrect number of probabilities")
    heavy = sum(1 for weight in weights if n * weight > 0.1)
    if heavy > 200:
        return _walker_sample_replace(weights, size)
    return _prob_sample_replace(weights, size)


def _bsample(population, size, prob=None):
    """R ``bsample``: sample ``population`` with replacement."""
    values = list(population)
    if prob is None:
        picks = rng.sample_int(len(values), size, replace=True)
    else:
        picks = _weighted_index(len(values), size, prob)
    return [values[pick - 1] for pick in picks]


def _r_pow_di(x, n):
    power = 1.0
    if n:
        if n < 0:
            n = -n
            x = 1.0 / x
        while True:
            if n & 1:
                power *= x
            n >>= 1
            if n:
                x *= x
            else:
                break
    return power


def _rbinom_one(nin, pp):
    """One draw from R's ``rbinom``. ``nin`` is the number of trials."""
    if nin == 0 or pp == 0.0:
        return 0
    if pp == 1.0:
        return int(nin)
    n = int(nin)
    p = min(pp, 1.0 - pp)
    q = 1.0 - p
    np_ = n * p
    ratio = p / q
    g = ratio * (n + 1)
    if np_ < 30.0:
        qn = _r_pow_di(q, n)
        ix = 0
        f = qn
        u = rng.unif()
        while u >= f:
            if ix > 110:
                u = rng.unif()
                ix = 0
                f = qn
                continue
            u -= f
            ix += 1
            f *= (g / ix - ratio)
        return (n - ix) if pp > 0.5 else ix
    ffm = np_ + p
    mode = int(ffm)
    fm = float(mode)
    npq = np_ * q
    p1 = int(2.195 * math.sqrt(npq) - 4.6 * q) + 0.5
    xm = fm + 0.5
    xl = xm - p1
    xr = xm + p1
    c = 0.134 + 20.5 / (15.3 + fm)
    al = (ffm - xl) / (ffm - xl * p)
    xll = al * (1.0 + 0.5 * al)
    al = (xr - ffm) / (xr * q)
    xlr = al * (1.0 + 0.5 * al)
    p2 = p1 * (1.0 + c + c)
    p3 = p2 + c / xll
    p4 = p3 + c / xlr
    while True:
        u = rng.unif() * p4
        v = rng.unif()
        if u <= p1:
            ix = int(xm - p1 * v + u)
            break
        if u <= p2:
            x = xl + (u - p1) / c
            v = v * c + 1.0 - abs(xm - x) / p1
            if v > 1.0 or v <= 0.0:
                continue
            ix = int(x)
        else:
            if u > p3:
                ix = int(xr - math.log(v) / xlr)
                if ix > n:
                    continue
                v = v * (u - p3) * xlr
            else:
                ix = int(xl + math.log(v) / xll)
                if ix < 0:
                    continue
                v = v * (u - p2) * xll
        k = abs(ix - mode)
        if k <= 20 or k >= npq / 2.0 - 1.0:
            f = 1.0
            if mode < ix:
                for i in range(mode + 1, ix + 1):
                    f *= (g / i - ratio)
            elif mode > ix:
                for i in range(ix + 1, mode + 1):
                    f /= (g / i - ratio)
            if v <= f:
                break
        else:
            amaxp = (k / npq) * ((k * (k / 3.0 + 0.625) + 0.1666666666666) / npq + 0.5)
            ynorm = -k * k / (2.0 * npq)
            alv = math.log(v)
            if alv < ynorm - amaxp:
                break
            if alv <= ynorm + amaxp:
                x1 = ix + 1.0
                f1 = fm + 1.0
                z = n + 1.0 - fm
                w = n - ix + 1.0
                z2 = z * z
                x2 = x1 * x1
                f2 = f1 * f1
                w2 = w * w
                stirling = (
                    xm * math.log(f1 / x1)
                    + (n - mode + 0.5) * math.log(z / w)
                    + (ix - mode) * math.log(w * p / (x1 * q))
                    + (13860.0 - (462.0 - (132.0 - (99.0 - 140.0 / f2) / f2) / f2) / f2) / f1 / 166320.0
                    + (13860.0 - (462.0 - (132.0 - (99.0 - 140.0 / z2) / z2) / z2) / z2) / z / 166320.0
                    + (13860.0 - (462.0 - (132.0 - (99.0 - 140.0 / x2) / x2) / x2) / x2) / x1 / 166320.0
                    + (13860.0 - (462.0 - (132.0 - (99.0 - 140.0 / w2) / w2) / w2) / w2) / w / 166320.0
                )
                if alv <= stirling:
                    break
    return (n - ix) if pp > 0.5 else ix


def _cens_case(n, strata_codes, replicates):
    """Case resampling within strata. Rows are 1-based indices."""
    out = np.empty((replicates, n), dtype=float)
    n_strata = max(strata_codes)
    for code in range(1, int(n_strata) + 1):
        inds = [i + 1 for i, value in enumerate(strata_codes) if int(value) == code]
        drawn = _bsample(inds, len(inds) * replicates)
        block = np.asarray(drawn, dtype=float).reshape((replicates, len(inds)), order="F")
        out[:, [i - 1 for i in inds]] = block
    return out


def _stratum_lengths(surv, n_time):
    strata = _component(surv, "strata", optional=True)
    if strata is None:
        return None
    lengths = [int(value) for value in np.ravel(np.asarray(strata))]
    if not lengths:
        return None
    return lengths


def _cens_weird(data, surv, strata_codes):
    """Weird bootstrap: binomial event counts at the observed failure times."""
    surv_time = np.asarray(_component(surv, "time"), dtype=float).reshape(-1)
    n_risk = np.asarray(_component(surv, "n.risk", "n_risk"), dtype=float).reshape(-1)
    n_event = np.asarray(_component(surv, "n.event", "n_event"), dtype=float).reshape(-1)
    m = len(surv_time)
    if len(n_risk) != m or len(n_event) != m:
        raise ValueError("'F.surv' time, n.risk, and n.event must have the same length")
    lengths = _stratum_lengths(surv, m)
    if lengths is None:
        nstr = 1
        point_stratum = [1] * m
    else:
        nstr = len(lengths)
        point_stratum = []
        for code, length in enumerate(lengths, start=1):
            point_stratum.extend([code] * length)
        if len(point_stratum) != m:
            raise ValueError("'F.surv' strata do not match the length of time")

    def draw_events():
        counts = []
        for risk, event in zip(n_risk, n_event):
            probability = float(event) / float(risk) if float(risk) != 0.0 else 0.0
            counts.append(_rbinom_one(int(risk), probability))
        return counts

    n_ev = draw_events()
    while True:
        totals = {code: 0 for code in range(1, nstr + 1)}
        for count, code in zip(n_ev, point_stratum):
            totals[code] = totals.get(code, 0) + count
        if all(total > 0 for total in totals.values()):
            break
        n_ev = draw_events()

    times = []
    groups = []
    for time, count, code in zip(surv_time, n_ev, point_stratum):
        times.extend([float(time)] * int(count))
        groups.extend([code] * int(count))
    times = np.asarray(times, dtype=float)
    groups = np.asarray(groups, dtype=int)
    pieces = []
    data_codes = np.asarray(strata_codes, dtype=int)
    for code in range(1, nstr + 1):
        event_times = times[groups == code]
        event_rows = (
            np.column_stack([event_times, np.ones(event_times.size)])
            if event_times.size
            else np.empty((0, 2))
        )
        censored = data[(data_codes == code) & (data[:, 1] == 0)]
        if censored.size:
            block = np.vstack([event_rows, censored]) if event_rows.size else np.array(censored, copy=True)
        else:
            block = event_rows
        block = np.column_stack([block, np.full(block.shape[0], code, dtype=float)])
        order = np.lexsort((1.0 - block[:, 1], block[:, 0]))
        pieces.append(block[order])
    if not pieces:
        return np.empty((0, 3))
    return np.vstack(pieces)


def _survival_mass(time, survival):
    """Discrete masses of a product-limit curve, with a final point at infinity."""
    time = np.asarray(time, dtype=float).reshape(-1)
    survival = np.asarray(survival, dtype=float).reshape(-1)
    if survival.size and survival[-1] > 0:
        survival = np.concatenate([survival, [0.0]])
        time = np.concatenate([time, [np.inf]])
    probs = np.diff(-np.concatenate([[1.0], survival]))
    return time, probs


def _fill_product_limit(replicates, n_obs, time, survival):
    time, probs = _survival_mass(time, survival)
    drawn = _bsample(time, n_obs * replicates, probs)
    return np.asarray(drawn, dtype=float).reshape((replicates, n_obs), order="F")


def _gety2(replicates, time, survival, eta):
    time = np.asarray(time, dtype=float).reshape(-1)
    survival = np.asarray(survival, dtype=float).reshape(-1)
    if survival.size and survival[-1] > 0:
        survival = np.concatenate([survival, [0.0]])
        time = np.concatenate([time, [np.inf]])
    ex = np.exp(np.asarray(eta, dtype=float).reshape(-1))
    fh = 1.0 - np.power(survival[:, None], ex[None, :])
    padded = np.vstack([np.zeros(ex.size), fh])
    result = np.empty((replicates, ex.size), dtype=float)
    for column in range(ex.size):
        result[:, column] = _bsample(time, replicates, np.diff(padded[:, column]))
    return result


def _getc2(replicates, time, survival, observed):
    time, probs = _survival_mass(time, survival)
    n_obs = observed.shape[0]
    cout = np.empty((replicates, n_obs), dtype=float)
    for i in range(n_obs):
        if observed[i, 1] == 0:
            cout[:, i] = observed[i, 0]
            continue
        keep = time > observed[i, 0]
        ti = time[keep]
        pri = probs[keep]
        if ti.size == 1:
            cout[:, i] = ti[0]
        elif ti.size == 0:
            raise ValueError("no censoring time above the observed failure")
        else:
            cout[:, i] = _bsample(ti, replicates, pri)
    return cout


def _largest_failure(data, strata, index):
    """Positional ``tapply`` maximum of observed failure times, repeated by row."""
    cens_col = index[1] - 1
    time_col = index[0] - 1
    event = np.flatnonzero(data[:, cens_col] == 1)
    n = data.shape[0]
    replicates = None
    if event.size == 0:
        return None
    ev_codes = np.asarray(strata[event, 0], dtype=int)
    ev_times = data[event, time_col]
    levels = sorted(set(ev_codes.tolist()))
    positional = [float(np.max(ev_times[ev_codes == level])) for level in levels]
    per_obs = np.full(n, np.nan)
    codes = np.asarray(strata[:, 0], dtype=int)
    length = len(positional)
    for i, code in enumerate(codes):
        if 1 <= code <= length:
            per_obs[i] = positional[code - 1]
    return per_obs


def _cens_resamp(data, replicates, f_surv, g_surv, strata, index, cox, sim):
    """Conditional or model-based resample. Result shape is ``(R, n, 2)``."""
    n = data.shape[0]
    f_time = np.asarray(_component(f_surv, "time"), dtype=float).reshape(-1)
    f_surv_values = np.asarray(_component(f_surv, "surv"), dtype=float).reshape(-1)
    g_time = np.asarray(_component(g_surv, "time"), dtype=float).reshape(-1)
    g_surv_values = np.asarray(_component(g_surv, "surv"), dtype=float).reshape(-1)
    f_lengths = _stratum_lengths(f_surv, len(f_time))
    if f_lengths is None:
        f_lengths = [len(f_time)]
    g_lengths = _stratum_lengths(g_surv, len(g_time))
    if g_lengths is None:
        g_lengths = [len(g_time)]
    linear = None
    if cox is not None:
        linear = np.asarray(
            _component(cox, "linear.predictors", "linear_predictors"), dtype=float
        ).reshape(-1)

    y0 = np.full((replicates, n), np.nan)
    f_start = 0
    failure_codes = np.asarray(strata[:, 0], dtype=int)
    n_failure = int(np.max(failure_codes))
    for code in range(1, n_failure + 1):
        columns = np.flatnonzero(failure_codes == code)
        length = f_lengths[code - 1]
        inds = slice(f_start, f_start + length)
        if linear is None:
            y0[:, columns] = _fill_product_limit(
                replicates, columns.size, f_time[inds], f_surv_values[inds]
            )
        else:
            y0[:, columns] = _gety2(
                replicates, f_time[inds], f_surv_values[inds], linear[columns]
            )
        f_start += length

    c0 = np.full((replicates, n), np.nan)
    g_start = 0
    censor_codes = np.asarray(strata[:, 1], dtype=int)
    n_censor = int(np.max(censor_codes))
    time_col = index[0] - 1
    cens_col = index[1] - 1
    for code in range(1, n_censor + 1):
        columns = np.flatnonzero(censor_codes == code)
        length = g_lengths[code - 1]
        inds = slice(g_start, g_start + length)
        if sim != "cond":
            c0[:, columns] = _fill_product_limit(
                replicates, columns.size, g_time[inds], g_surv_values[inds]
            )
        else:
            observed = data[columns][:, [time_col, cens_col]]
            c0[:, columns] = _getc2(replicates, g_time[inds], g_surv_values[inds], observed)
        g_start += length

    both_infinite = np.isinf(y0) & np.isinf(c0)
    if np.any(both_infinite):
        per_obs = _largest_failure(data, strata, index)
        if per_obs is not None:
            y0 = y0.copy()
            y0[both_infinite] = np.broadcast_to(per_obs, y0.shape)[both_infinite]
    times = np.minimum(y0, c0)
    events = (y0 <= c0).astype(float)
    return np.stack([times, events], axis=-1)


def censboot(
    data,
    statistic,
    R,
    F_surv=None,
    G_surv=None,
    strata=None,
    sim="ordinary",
    cox=None,
    index=(1, 2),
    parallel="no",
    ncpus=1,
    cl=None,
    **kwargs,
):
    """Bootstrap replicates for right-censored data.

    ``sim`` is ``"ordinary"``, ``"model"``, ``"cond"``, or ``"weird"``.
    ``F_surv`` and ``G_surv`` carry the numeric survival-curve vectors R
    would pass (``time`` and ``surv``, plus ``n.risk``, ``n.event``, and
    ``strata`` when the weird or stratified curves need them). ``cox`` is
    an object with a ``coefficients`` vector and, for model-based failure
    times, ``linear_predictors``. Indices are 1-based. Only serial
    resampling is run.
    """
    del cl
    if sim not in ("ordinary", "model", "cond", "weird"):
        raise ValueError("unknown value of 'sim'")
    if sim == "model" and cox is None:
        sim = "ordinary"
    parallel = _match_arg(parallel, ("no", "multicore", "snow"))
    if parallel != "no" and int(ncpus) > 1:
        warnings.warn("only serial resampling is implemented; parallel was ignored", stacklevel=2)
    seed = _r_random_seed()

    data = np.array(data, dtype=float, copy=True)
    if data.ndim != 2 or data.shape[1] < 2:
        raise ValueError("'data' must be a matrix with at least 2 columns")
    if np.isnan(data).any():
        raise ValueError("missing values not allowed in 'data'")
    n = data.shape[0]
    index = [int(value) for value in np.ravel(np.asarray(index))]
    if len(index) < 2:
        raise ValueError("'index' must contain 2 elements")
    if len(index) > 2:
        warnings.warn("only first 2 elements of 'index' used", stacklevel=2)
        index = index[:2]
    if min(index) < 1 or data.shape[1] < max(index):
        raise ValueError("indices are incompatible with 'ncol(data)'")
    if sim == "weird":
        if cox is not None:
            raise ValueError('sim = "weird" cannot be used with a "coxph" object')
        if data.shape[1] > 2:
            warnings.warn(
                f"only columns {index[0]} and {index[1]} of 'data' used",
                stacklevel=2,
            )
        data = np.array(data[:, [index[0] - 1, index[1] - 1]], copy=True)
    if cox is not None and _component(cox, "coefficients", optional=True) is None and sim in ("cond", "model"):
        warnings.warn("no coefficients in Cox model -- model ignored", stacklevel=2)
        cox = None
    if sim != "ordinary" and F_surv is None:
        raise ValueError("'F.surv' is required but missing")
    if G_surv is None and sim in ("cond", "model"):
        raise ValueError("'G.surv' is required but missing")

    stored_strata, strata_codes, strata_supplied = _prepare_strata(strata, n, sim)
    if sim == "weird" and strata_supplied:
        t0 = _statistic_vector(statistic(data, stored_strata, **kwargs))
    else:
        t0 = _statistic_vector(statistic(data, **kwargs))
    replicates = int(R)

    if sim == "ordinary":
        case_index = _cens_case(n, strata_codes, replicates)

        def evaluate(r):
            return statistic(_row_subset(data, np.sort(case_index[r])), **kwargs)

    elif sim == "weird":

        def evaluate(_r, supplied=strata_supplied):
            bootdata = _cens_weird(data, F_surv, strata_codes)
            if supplied:
                return statistic(bootdata[:, :2], bootdata[:, 2], **kwargs)
            return statistic(bootdata[:, :2], **kwargs)

    else:
        resampled = _cens_resamp(data, replicates, F_surv, G_surv, strata_codes, index, cox, sim)
        columns = [index[0] - 1, index[1] - 1]

        def evaluate(r, columns=columns, resampled=resampled):
            bootdata = np.array(data, copy=True)
            bootdata[:, columns] = resampled[r]
            times = resampled[r, :, 0]
            censor = resampled[r, :, 1]
            order = np.lexsort((1.0 - censor, times))
            return statistic(_row_subset(bootdata, order + 1), **kwargs)

    replicates_out = [_statistic_vector(evaluate(r)) for r in range(replicates)]
    if replicates_out and any(value.size != t0.size for value in replicates_out):
        raise ValueError("statistic returned a different length on a replicate")
    t = np.empty((replicates, t0.size), dtype=float)
    for r, value in enumerate(replicates_out):
        t[r, :] = value
    return CensBoot(t0, t, replicates, sim, data, seed, statistic, stored_strata)
