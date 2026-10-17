"""Surrogates, the bootstrap, quadmap, and the readers."""

from __future__ import annotations

import math
from pathlib import Path

import numpy as np

from tseries._num import embed, match_arg


def _as_vector(x):
    values = np.asarray(x, dtype=float).reshape(-1)
    if np.isnan(values).any():
        raise ValueError("NAs in x")
    return values


def quadmap(xi=0.2, a=4.0, n=1000):
    n = int(n)
    if n < 1:
        raise ValueError("n is not positive")
    if xi < 0 or xi > 1:
        raise ValueError("xi is not in [0,1]")
    if a < 0 or a > 4:
        raise ValueError("a is not in [0,4]")
    out = np.empty(n, dtype=float)
    out[0] = xi
    for i in range(1, n):
        out[i] = a * (1.0 - out[i - 1]) * out[i - 1]
    return out


def _rank_average(x):
    order = np.argsort(x, kind="mergesort")
    ranks = np.empty(len(x), dtype=float)
    i = 0
    n = len(x)
    while i < n:
        j = i + 1
        while j < n and x[order[j]] == x[order[i]]:
            j += 1
        average = (i + 1 + j) / 2.0
        ranks[order[i:j]] = average
        i = j
    return ranks


def _runif(n, minimum=0.0, maximum=1.0):
    from boot.rng import unif

    span = maximum - minimum
    return np.array([minimum + span * unif() for _ in range(n)], dtype=float)


def _rnorm(n):
    from extradistr._rng import norm_rand

    return np.array([norm_rand() for _ in range(n)], dtype=float)


def fftsurr(x):
    """Theiler algorithm 1. The phase draws are R ``runif``."""
    series = np.asarray(x, dtype=float).reshape(-1)
    transformed = np.fft.fft(series)
    spun = transformed * np.exp(1j * _runif(len(transformed), maximum=2 * math.pi))
    right = spun[1:]
    left = spun[:0:-1]
    real = np.real(right + left) / 2
    imag = np.imag(right - left) / 2
    first = np.real(spun[0] + spun[0]) / 2 + 1j * np.imag(spun[0] - spun[0]) / 2
    rebuilt = np.concatenate([[first], real + 1j * imag])
    # R's inverse FFT is unnormalized: fft(z, inverse=TRUE) equals n * numpy.ifft.
    return np.real(np.fft.ifft(rebuilt)) * len(rebuilt)


def ampsurr(x):
    """Theiler algorithm 2."""
    series = np.asarray(x, dtype=float).reshape(-1)
    ordered = np.sort(series)
    ranks = _rank_average(series)
    normal = _rnorm(len(series))
    ranked = np.sort(normal)[np.trunc(ranks).astype(int) - 1]
    scrambled = fftsurr(ranked)
    back = _rank_average(scrambled)
    return ordered[np.trunc(back).astype(int) - 1]


def _permute(x):
    from boot.rng import sample_int

    index = sample_int(len(x), len(x), replace=False)
    return np.asarray(x, dtype=float)[np.array(index) - 1]


def surrogate(x, ns=1, fft=False, amplitude=False, statistic=None):
    series = _as_vector(x)
    ns = int(ns)
    if ns < 1:
        raise ValueError("ns is not positive")
    if statistic is None:
        columns = []
        for _ in range(ns):
            if fft and amplitude:
                columns.append(ampsurr(series))
            elif fft:
                columns.append(fftsurr(series))
            else:
                columns.append(_permute(series))
        if ns == 1:
            return columns[0]
        return np.column_stack(columns)
    original = np.atleast_1d(np.asarray(statistic(series), dtype=float))
    stats = []
    for _ in range(ns):
        if fft and amplitude:
            draw = ampsurr(series)
        elif fft:
            draw = fftsurr(series)
        else:
            draw = _permute(series)
        stats.append(np.atleast_1d(np.asarray(statistic(draw), dtype=float)))
    table = np.vstack(stats)
    bias = table.mean(axis=0) - original
    se = table.std(axis=0, ddof=1)
    return {
        "statistic": table[0] if ns == 1 else table,
        "orig_statistic": original[0] if original.size == 1 else original,
        "bias": bias[0] if bias.size == 1 else bias,
        "se": se[0] if se.size == 1 else se,
    }


def _exp_rand():
    """R ``exp_rand``: Ahrens-Dieter, not ``-log(unif_rand())``."""
    from extradistr._rng import exp_rand

    return exp_rand()


def _geodev(p):
    b = -1.0 / math.log(1.0 - p)
    return int(b * _exp_rand())


def _disuni(n):
    from boot.rng import unif

    return int(unif() * n + 1.0)


def _wrap(i, n):
    if i < 1:
        return i - math.trunc(i / n) * n + n
    if i > n:
        return (i - 1) % n + 1
    return i


def _stat_boot(x, p):
    values = np.asarray(x, dtype=float).reshape(-1)
    n = len(values)
    out = np.empty(n, dtype=float)
    i = 0
    while i < n:
        start = _disuni(n)
        length = _geodev(p)
        j = 0
        while j < length and i < n:
            out[i] = values[_wrap(start + j, n) - 1]
            i += 1
            j += 1
    return out


def _block_boot(x, length):
    values = np.asarray(x, dtype=float).reshape(-1)
    n = len(values)
    block = int(length)
    out = np.empty(n, dtype=float)
    i = 0
    while i < n:
        start = _disuni(n - block + 1)
        j = 0
        while j < block and i < n:
            out[i] = values[start - 1 + j]
            i += 1
            j += 1
    return out


def tsbootstrap(x, nb=1, statistic=None, m=1, b=None, type="stationary"):
    series = _as_vector(x)
    kind = match_arg(type, ("stationary", "block"))
    nb = int(nb)
    m = int(m)
    if nb < 1:
        raise ValueError("nb is not positive")
    n = len(series)
    if n <= m:
        raise ValueError("x should contain more than m observations")
    const = 3.15
    if kind == "stationary":
        if b is None:
            b = const * n ** (1.0 / 3.0)
        b = 1.0 / b
        if b <= 1 / n or b >= 1:
            raise ValueError("b should be in (1,length(x)) for the stationary bootstrap")
    else:
        if b is None:
            b = const * n ** (1.0 / 3.0)
        if b < 1 or b > n:
            raise ValueError("b should be in [1,length(x)] for the blockwise bootstrap")
    if statistic is None:
        if m > 1:
            raise ValueError("can only return bootstrap data for m = 1")
        columns = []
        for _ in range(nb):
            if kind == "stationary":
                columns.append(_stat_boot(series, b))
            else:
                columns.append(_block_boot(series, b))
        if nb == 1:
            return columns[0]
        return np.column_stack(columns)
    window = embed(series, m)
    original = np.atleast_1d(np.asarray(statistic(window[:, 0] if m == 1 else window), dtype=float))
    index = np.arange(1, len(window) + 1, dtype=float)
    stats = []
    for _ in range(nb):
        if kind == "stationary":
            drawn = _stat_boot(index, b)
        else:
            drawn = _block_boot(index, b)
        rows = np.trunc(drawn).astype(int) - 1
        sample = window[rows, 0] if m == 1 else window[rows]
        stats.append(np.atleast_1d(np.asarray(statistic(sample), dtype=float)))
    table = np.vstack(stats)
    bias = table.mean(axis=0) - original
    se = table.std(axis=0, ddof=1)
    return {
        "statistic": table[0] if nb == 1 else table,
        "orig_statistic": original[0] if original.size == 1 else original,
        "bias": bias[0] if bias.size == 1 else bias,
        "se": se[0] if se.size == 1 else se,
    }


def _split_fields(line, sep):
    if sep == "":
        return line.split()
    return line.split(sep)


def read_matrix(file, header=False, sep="", skip=0):
    text = Path(file).read_text().splitlines()
    text = text[int(skip) :]
    rows = [_split_fields(line, sep) for line in text if line.strip() != ""]
    if not rows:
        raise ValueError("wrong number of columns")
    width = len(rows[0])
    if any(len(row) != width for row in rows):
        raise ValueError("number of columns is not constant")
    names = None
    if header:
        names = rows[0]
        rows = rows[1:]
        if not rows:
            raise ValueError("wrong number of columns")
        width = len(rows[0])
        if any(len(row) != width for row in rows):
            raise ValueError("number of columns is not constant")
    if width < 1:
        raise ValueError("wrong number of columns")
    flat = [float(item) for row in rows for item in row]
    if width == 1:
        values = np.array(flat, dtype=float)
    else:
        values = np.array(flat, dtype=float).reshape(len(rows), width)
    if names is None:
        return values
    return values, names


def read_ts(file, header=False, sep="", skip=0, start=1, frequency=1):
    loaded = read_matrix(file, header=header, sep=sep, skip=skip)
    if isinstance(loaded, tuple):
        values = loaded[0]
    else:
        values = loaded
    return np.asarray(values, dtype=float), float(start), float(frequency)


def na_remove(object, tsp=None):
    values = np.asarray(object, dtype=float)
    if tsp is None:
        return _na_remove_default(values)
    return _na_remove_ts(values, tsp)


def _na_remove_default(values):
    if values.ndim == 2:
        missing = np.isnan(values).any(axis=1)
        if not missing.any():
            return values, None
        kept = values[~missing]
        removed = (np.flatnonzero(missing) + 1).astype(int)
        return kept, removed
    missing = np.isnan(values.reshape(-1))
    if not missing.any():
        return values.reshape(-1), None
    kept = values.reshape(-1)[~missing]
    removed = (np.flatnonzero(missing) + 1).astype(int)
    return kept, removed


def _na_remove_ts(values, tsp):
    start, end, frequency = tsp
    if not np.isnan(np.asarray(values, dtype=float)).any():
        return np.asarray(values, dtype=float).reshape(-1), None, (start, end, frequency)
    kept, removed = _na_remove_default(values)
    n = np.asarray(values).reshape(-1).shape[0] if np.asarray(values).ndim == 1 else np.asarray(values).shape[0]
    ok = [i for i in range(1, n + 1) if i not in set(int(v) for v in removed)]
    new_start = start + (ok[0] - 1) / frequency
    new_end = start + (ok[-1] - 1) / frequency
    span = new_end - new_start
    new_freq = (len(np.asarray(kept)) - 1) / span if span != 0 else frequency
    return np.asarray(kept, dtype=float).reshape(-1) if np.asarray(kept).ndim == 1 else kept, removed, (
        new_start,
        new_end,
        new_freq,
    )
