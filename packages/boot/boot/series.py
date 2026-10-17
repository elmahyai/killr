"""Time series bootstrap from CRAN boot 1.3-32.

``tsboot`` follows ``ts.array``, ``make.ends``, ``tsboot``, ``scramble``,
and ``ts.return`` in ``R/bootfuns.q``. Block starts come from ``sample.int``.
Geometric lengths are ``1 + rgeom(1/l)``, and that geometric draw is R's
``rpois(exp_rand * (l - 1))``. When the Poisson mean is at least 10, R's
default Inversion normal is ``qnorm`` of two uniforms packed into one
probability.
"""

from __future__ import annotations

import math

import numpy as np

from boot import rng
from boot.rng import sample_int, unif

_PARALLEL = ("no", "multicore", "snow")

# Ahrens-Dieter exponential, the generator behind R's rexp and rgeom.
_QEXP = (
    0.6931471805599453,
    0.9333736875190459,
    0.9888777961838675,
    0.9984959252914960,
    0.9998292811061389,
    0.9999833164100727,
    0.9999985691438762,
    0.9999998906925558,
    0.9999999924734159,
    0.9999999995283275,
    0.9999999999728814,
    0.9999999999985598,
    0.9999999999999289,
    0.9999999999999968,
    0.9999999999999999,
    1.0000000000000000,
)

# Wichura AS 241, the rational part of R's qnorm. The center is then
# polished with Halley's method so the result matches qnorm on (0, 1).
_SQRT2 = math.sqrt(2.0)
_INV_SQRT_2PI = 0.398942280401432677939946059934
_BIG = 134217728  # 2^27, the split R's Inversion normal uses

_FACT = (1.0, 1.0, 2.0, 6.0, 24.0, 120.0, 720.0, 5040.0, 40320.0, 362880.0)
_STIRLING = (
    -0.5,
    0.3333333,
    -0.2500068,
    0.2000118,
    -0.1661269,
    0.1421878,
    -0.1384794,
    0.1250060,
)
_ONE_7 = 0.1428571428571428571
_ONE_12 = 0.0833333333333333333
_ONE_24 = 0.0416666666666666667


class Tsboot:
    """Result of ``tsboot``, the object ``ts.return`` builds.

    ``t0`` is the statistic on the original series, or ``None`` when
    ``orig_t`` is false. ``t`` has one row per replicate. ``data`` is the
    series that was passed in. The remaining fields are the simulation
    settings R stores for that ``sim``.
    """

    def __init__(self, **fields):
        self.__dict__.update(fields)

    def __repr__(self):
        t0 = self.t0
        t0_text = "NULL" if t0 is None else _format_number(t0)
        rows = np.asarray(self.t, dtype=float).reshape(self.R, -1)
        lines = [f"tsboot (R = {self.R}, sim = {self.sim})", f"t0: {t0_text}", "t:"]
        for row in rows:
            lines.append(" " + " ".join(_format_number(value) for value in row))
        return "\n".join(lines)


def _format_number(value):
    array = np.asarray(value, dtype=float).reshape(-1)
    if array.size != 1:
        return " ".join(_format_number(item) for item in array)
    number = float(array[0])
    if math.isnan(number):
        return "NaN"
    return f"{number:.10g}"


def _match_arg(value, choices):
    if not isinstance(value, str):
        raise ValueError("parallel must be a character string")
    matches = [choice for choice in choices if choice.startswith(value)]
    if len(matches) == 1:
        return matches[0]
    listed = ", ".join(f'"{choice}"' for choice in choices)
    if not matches:
        raise ValueError(f"parallel should be one of {listed}")
    raise ValueError("there is more than one match in match.arg")


def _series_matrix(tseries):
    """Columns are variables. A vector is one column, as ``as.matrix`` does."""
    array = np.asarray(tseries)
    if array.ndim == 0 or array.size == 0:
        raise ValueError("tseries must have at least one observation")
    if array.ndim == 1:
        return array.reshape(-1, 1), False
    if array.ndim == 2:
        return array, True
    raise ValueError("tseries must be a vector or a matrix")


def _qnorm_rational(p):
    q = p - 0.5
    if abs(q) <= 0.425:
        r = 0.180625 - q * q
        return q * (
            (
                (
                    (
                        (((r * 2509.0809287301226727 + 33430.575583588128105) * r + 67265.770927008700853) * r + 45921.953931549871457)
                        * r
                        + 13731.536185768826317
                    )
                    * r
                    + 1971.5909503065514427
                )
                * r
                + 133.14166789178437745
            )
            * r
            + 3.387132872796366608
        ) / (
            (
                (
                    (
                        (((r * 5226.495278852854561 + 28729.085735721942674) * r + 39307.89580009271061) * r + 21213.794301586595867)
                        * r
                        + 5394.1960214247511077
                    )
                    * r
                    + 687.1870074920579083
                )
                * r
                + 42.313330701600911252
            )
            * r
            + 1.0
        )
    tail = (1.0 - p) if q > 0.0 else p
    r = math.sqrt(-math.log(tail))
    if r <= 5.0:
        r = r - 1.6
        val = (
            (
                (
                    (((r * 7.7454501427834140764e-4 + 0.0227238449892691845833) * r + 0.24178072517745061177) * r + 1.27045825245236838258)
                    * r
                    + 3.64784832476320460504
                )
                * r
                + 5.7694972214606914055
            )
            * r
            + 4.6303378461565452959
        ) * r + 1.42343711074968357734
        val /= (
            (
                (
                    (
                        (((r * 1.05075007164441684324e-9 + 5.475938084995344946e-4) * r + 0.0151986665636164571966) * r + 0.14810397642748007459)
                        * r
                        + 0.68976733498510000455
                    )
                    * r
                    + 1.6763848301838038494
                )
                * r
                + 2.05319162663775882187
            )
            * r
            + 1.0
        )
    else:
        r = r - 5.0
        val = (
            (
                (
                    (((r * 2.01033439929228813265e-7 + 2.71155556874348757815e-5) * r + 0.0012426609473880784386) * r + 0.026532189526576123093)
                    * r
                    + 0.29656057182850489123
                )
                * r
                + 1.7848265399172913358
            )
            * r
            + 5.4637849111641143699
        ) * r + 6.6579046435011037772
        val /= (
            (
                (
                    (
                        (((r * 2.04426310338993978564e-15 + 1.4215117583164458887e-7) * r + 1.8463183175100546818e-5) * r + 7.868691311456132591e-4)
                        * r
                        + 0.0148753612908506148525
                    )
                    * r
                    + 0.13692988092273580531
                )
                * r
                + 0.59983220655588793769
            )
            * r
            + 1.0
        )
    if q < 0.0:
        val = -val
    return val


def _pnorm(z):
    return 0.5 * (1.0 + math.erf(z / _SQRT2))


def qnorm(p):
    """R ``qnorm(p)`` for a probability in [0, 1]."""
    if math.isnan(p):
        return math.nan
    if p == 0.0:
        return -math.inf
    if p == 1.0:
        return math.inf
    if p < 0.0 or p > 1.0:
        return math.nan
    if p == 0.5:
        return 0.0
    z = _qnorm_rational(p)
    if abs(p - 0.5) > 0.425:
        return z
    for _ in range(3):
        err = _pnorm(z) - p
        if err == 0.0:
            return z
        pdf = math.exp(-0.5 * z * z) * _INV_SQRT_2PI
        denom = pdf + 0.5 * z * err
        if denom == 0.0 or not math.isfinite(denom):
            return z
        step = err / denom
        if not math.isfinite(step):
            return z
        z = z - step
        if abs(step) <= 1e-15 * (1.0 + abs(z)):
            return z
    return z


def _exp_rand():
    a = 0.0
    u = unif()
    while u <= 0.0 or u >= 1.0:
        u = unif()
    while True:
        u += u
        if u > 1.0:
            break
        a += _QEXP[0]
    u -= 1.0
    if u <= _QEXP[0]:
        return a + u
    i = 0
    ustar = unif()
    umin = ustar
    while u > _QEXP[i]:
        ustar = unif()
        if umin > ustar:
            umin = ustar
        i += 1
    return a + umin * _QEXP[0]


def _norm_rand():
    """R's Inversion ``norm_rand``: ``qnorm`` of two ``unif`` draws."""
    u1 = unif()
    u2 = unif()
    packed = (math.trunc(_BIG * u1) + u2) / _BIG
    return qnorm(packed)


class _PoissonState:
    """Static tables from R's ``rpois``, kept for the life of the process."""

    def __init__(self):
        self.l = 0
        self.m = 0
        self.b1 = 0.0
        self.b2 = 0.0
        self.c = 0.0
        self.c0 = 0.0
        self.c1 = 0.0
        self.c2 = 0.0
        self.c3 = 0.0
        self.pp = [0.0] * 36
        self.p0 = 0.0
        self.p = 0.0
        self.q = 0.0
        self.s = 0.0
        self.d = 0.0
        self.omega = 0.0
        self.big_l = 0.0
        self.muprev = 0.0
        self.muprev2 = 0.0

    def rpois(self, mu):
        if not math.isfinite(mu) or mu < 0.0:
            return math.nan
        if mu <= 0.0:
            return 0.0
        big_mu = mu >= 10.0
        new_big_mu = False
        if not (big_mu and mu == self.muprev):
            if big_mu:
                new_big_mu = True
                self.muprev = mu
                self.s = math.sqrt(mu)
                self.d = 6.0 * mu * mu
                self.big_l = math.floor(mu - 1.1484)
            else:
                if mu != self.muprev:
                    self.muprev = mu
                    self.m = max(1, int(mu))
                    self.l = 0
                    self.q = self.p0 = self.p = math.exp(-mu)
                while True:
                    u = unif()
                    if u <= self.p0:
                        return 0.0
                    if self.l != 0:
                        k0 = 1 if u <= 0.458 else min(self.l, self.m)
                        for k in range(k0, self.l + 1):
                            if u <= self.pp[k]:
                                return float(k)
                        if self.l == 35:
                            continue
                    for k in range(self.l + 1, 36):
                        self.p *= mu / k
                        self.q += self.p
                        self.pp[k] = self.q
                        if u <= self.q:
                            self.l = k
                            return float(k)
                    self.l = 35
        g = mu + self.s * _norm_rand()
        pois = -1.0
        u = 0.0
        fk = 0.0
        difmuk = 0.0
        if g >= 0.0:
            pois = math.floor(g)
            if pois >= self.big_l:
                return pois
            fk = pois
            difmuk = mu - fk
            u = unif()
            if self.d * u >= difmuk * difmuk * difmuk:
                return pois
        if new_big_mu or mu != self.muprev2:
            self.muprev2 = mu
            self.omega = _INV_SQRT_2PI / self.s
            self.b1 = _ONE_24 / mu
            self.b2 = 0.3 * self.b1 * self.b1
            self.c3 = _ONE_7 * self.b1 * self.b2
            self.c2 = self.b2 - 15.0 * self.c3
            self.c1 = self.b1 - 6.0 * self.b2 + 45.0 * self.c3
            self.c0 = 1.0 - self.b1 + 3.0 * self.b2 - 15.0 * self.c3
            self.c = 0.1069 / mu
        entered = g >= 0.0
        kflag = 0 if entered else 1
        while True:
            if not entered:
                expo = _exp_rand()
                u = 2.0 * unif() - 1.0
                t = 1.8 + (abs(expo) if u >= 0.0 else -abs(expo))
                if t <= -0.6744:
                    continue
                pois = math.floor(mu + self.s * t)
                fk = pois
                difmuk = mu - fk
                kflag = 1
            else:
                expo = 0.0
            entered = False
            if pois < 10:
                px = -mu
                py = (mu ** pois) / _FACT[int(pois)]
            else:
                delta = _ONE_12 / fk
                delta = delta * (1.0 - 4.8 * delta * delta)
                v = difmuk / fk
                if abs(v) <= 0.25:
                    poly = _STIRLING[7]
                    for coef in _STIRLING[6::-1]:
                        poly = poly * v + coef
                    px = fk * v * v * poly - delta
                else:
                    px = fk * math.log(1.0 + v) - difmuk - delta
                py = _INV_SQRT_2PI / math.sqrt(fk)
            x = (0.5 - difmuk) / self.s
            x *= x
            fx = -0.5 * x
            fy = self.omega * (((self.c3 * x + self.c2) * x + self.c1) * x + self.c0)
            if kflag > 0:
                if self.c * abs(u) <= py * math.exp(px + expo) - fy * math.exp(fx + expo):
                    return pois
            elif fy - u * fy <= py * math.exp(px - fx):
                return pois


_POISSON = _PoissonState()


def _rpois(mu):
    return _POISSON.rpois(mu)


def _rgeom(prob):
    return _rpois(_exp_rand() * ((1.0 - prob) / prob))


def _rank_average(values):
    """R ``rank`` with the default average tie method. Ranks start at 1."""
    array = np.asarray(values, dtype=float).reshape(-1)
    n = array.size
    order = np.argsort(array, kind="mergesort")
    ranks = np.empty(n, dtype=float)
    ordered = array[order]
    start = 0
    while start < n:
        stop = start + 1
        while stop < n and ordered[stop] == ordered[start]:
            stop += 1
        ranks[order[start:stop]] = 0.5 * ((start + 1) + stop)
        start = stop
    return ranks


def _seed_snapshot():
    return (rng._mti, tuple(rng._mt))


def _identity(tser, n_sim, args):
    return tser


def ts_array(n, n_sim, replicates, l, sim, endcorr):
    """Starting points and block lengths for the block bootstrap.

    ``starts`` has one row per replicate. For ``sim="fixed"``, ``lengths``
    is one vector shared by every replicate. For ``sim="geom"`` it is a
    matrix, one row per replicate, including any trailing zeros.
    """
    endpt = n if endcorr else n - l + 1
    if sim == "geom":
        len_tot = [0.0] * replicates
        columns = []
        while True:
            temp = [min(1.0 + _rgeom(1.0 / l), n_sim - len_tot[i]) for i in range(replicates)]
            columns.append(temp)
            len_tot = [len_tot[i] + temp[i] for i in range(replicates)]
            if not any(total < n_sim for total in len_tot):
                break
        lengths = np.column_stack(columns)
        nn = lengths.shape[1]
    else:
        nn = math.ceil(n_sim / l)
        last = 1 + (n_sim - 1) % l
        lengths = np.array([l] * (nn - 1) + [last], dtype=float)
    draws = sample_int(int(endpt), nn * replicates, replace=True)
    starts = np.array(draws, dtype=int).reshape((replicates, nn), order="F")
    return starts, lengths


def make_ends(start, length, n):
    """Circular indices of one block. ``start`` and the result are 1-based."""
    if length == 0:
        return []
    if length < 0:
        raise ValueError("negative block length")
    count = int(length)
    origin = int(start)
    return [((origin + i - 1) % n) + 1 for i in range(count)]


def _block_indices(starts_row, lengths, n, n_sim):
    indices = []
    for start, length in zip(starts_row, lengths):
        indices.extend(make_ends(start, length, n))
    return indices[:n_sim]


def _resampled_series(matrix, indices):
    picked = matrix[np.asarray(indices, dtype=int) - 1, :]
    if picked.shape[0] == 1 or picked.shape[1] == 1:
        return np.ravel(picked)
    return picked


def scramble(ts, norm=True):
    """Phase scramble a univariate series.

    ``norm=True`` keeps normal margins. ``norm=False`` puts the scrambled
    series back onto the exact empirical margins of ``ts``.
    """
    array = np.asarray(ts)
    if array.ndim == 2:
        raise ValueError("multivariate time series not allowed")
    y = np.ravel(array).astype(float)
    center = float(np.mean(y))
    e = y - center
    n = e.size
    if not norm:
        ranks = _rank_average(e)
        e = np.array([qnorm(rank / (n + 1.0)) for rank in ranks])
    angles = np.array([unif() * 2.0 * math.pi for _ in range(n)])
    transformed = np.fft.fft(e) * np.exp(1j * angles)
    conjugate = np.empty(n, dtype=complex)
    conjugate[0] = 0.0
    if n > 1:
        conjugate[1:] = np.conj(transformed[:0:-1])
    mixed = (transformed + conjugate) / math.sqrt(2.0)
    e = np.real(center + np.fft.ifft(mixed))
    if not norm:
        order = np.sort(y)
        index = np.trunc(_rank_average(e)).astype(int) - 1
        e = order[index]
    return e


def _statistic_vector(value):
    return np.asarray(value, dtype=float).reshape(-1)


def tsboot(
    tseries,
    statistic,
    R,
    l=None,
    sim="model",
    endcorr=True,
    n_sim=None,
    orig_t=True,
    ran_gen=None,
    ran_args=None,
    norm=True,
    parallel="no",
    ncpus=1,
    cl=None,
    **kwargs,
):
    """Bootstrap a statistic on a time series.

    ``sim`` is ``"model"``, ``"fixed"``, ``"geom"``, or ``"scramble"``.
    Block methods use length ``l``. Only the serial path is implemented.
    """
    parallel = _match_arg(parallel, _PARALLEL)
    if parallel != "no" and ncpus > 1:
        raise ValueError("only serial tsboot is implemented")

    replicates = math.floor(R)
    if replicates <= 0:
        raise ValueError("'R' must be positive")
    matrix, _multivariate = _series_matrix(tseries)
    n = int(matrix.shape[0])
    if n_sim is None:
        n_sim = n
    n_sim = int(n_sim)
    if n_sim <= 0:
        raise ValueError("n_sim must be positive")

    if sim in ("model", "scramble"):
        l = None
    elif l is None or l <= 0 or l > n:
        raise ValueError("invalid value of 'l'")
    if sim == "geom":
        endcorr = True
    elif sim not in ("model", "scramble", "fixed", "geom"):
        raise ValueError("unrecognized value of 'sim'")

    seed = _seed_snapshot()
    t0 = statistic(tseries, **kwargs) if orig_t else None
    generator = _identity if ran_gen is None else ran_gen

    if sim == "scramble":
        def one_replicate(_r):
            return statistic(scramble(tseries, norm), **kwargs)
    elif sim == "model":
        def one_replicate(_r):
            return statistic(generator(tseries, n_sim, ran_args), **kwargs)
    elif sim in ("fixed", "geom"):
        starts, lengths = ts_array(n, n_sim, replicates, l, sim, endcorr)

        def one_replicate(r):
            block_lengths = lengths[r] if sim == "geom" else lengths
            indices = _block_indices(starts[r], block_lengths, n, n_sim)
            series = _resampled_series(matrix, indices)
            return statistic(generator(series, n_sim, ran_args), **kwargs)
    else:
        raise ValueError("unrecognized value of 'sim'")

    rows = [_statistic_vector(one_replicate(r)) for r in range(replicates)]
    width = rows[0].size
    t = np.empty((replicates, width), dtype=float)
    for r, row in enumerate(rows):
        if row.size != width:
            raise ValueError("statistic returned results of different lengths")
        t[r, :] = row

    fields = {
        "t0": None if t0 is None else t0,
        "t": t,
        "R": replicates,
        "data": tseries,
        "seed": seed,
        "statistic": statistic,
        "sim": sim,
        "n_sim": n_sim,
        "call": f"tsboot(sim={sim!r}, R={replicates})",
        "boot_type": "tsboot",
    }
    if sim == "scramble":
        fields["norm"] = norm
    elif sim == "model":
        fields["ran_gen"] = generator
        fields["ran_args"] = ran_args
    else:
        fields["l"] = l
        fields["endcorr"] = endcorr
        if ran_gen is not None:
            fields["ran_gen"] = generator
            fields["ran_args"] = ran_args
    return Tsboot(**fields)
