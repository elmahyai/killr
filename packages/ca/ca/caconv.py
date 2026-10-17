"""Conversions among frequency, response-pattern, indicator, and Burt data."""

import numpy as np


def caconv(x, from_="freq", to="rpm", nlev=None, vars=(1, 2), **kwargs):
    # Accept R-style ``from`` through kwargs because it is a Python keyword.
    from_ = kwargs.pop("from", from_)
    a = np.asarray(x)
    if from_ == to:
        return a.copy()
    if from_ in ("rpm", "ind") and from_ == "rpm":
        levels = [list(dict.fromkeys(a[:, j].tolist())) for j in range(a.shape[1])]
        ind = _indicator(a, levels)
    elif from_ == "ind":
        ind = a.astype(float)
        if nlev is None:
            nlev = _infer_nlev(ind)
        levels = [list(range(k)) for k in nlev]
    elif from_ == "freq":
        freq = a.astype(int)
        levels = [list(range(freq.shape[0])), list(range(freq.shape[1]))]
        rpm = np.repeat(
            np.column_stack(np.unravel_index(np.arange(freq.size), freq.shape)),
            freq.ravel(), axis=0,
        )
        ind = _indicator(rpm, levels)
    elif from_ == "Burt":
        burt = a.astype(float)
        if nlev is None:
            nlev = _infer_nlev(burt)
        if to == "freq":
            return _slice_variables(burt, nlev, vars)
        raise ValueError("Option 'Burt' to indicator/rpm is not implemented")
    else:
        raise ValueError("unknown input type")
    if to == "ind":
        return ind
    if to == "Burt":
        return ind.T @ ind
    if to == "rpm":
        if from_ == "rpm":
            return a.copy()
        return _decode_indicator(ind, levels)
    if to == "freq":
        if from_ == "freq":
            return a.copy()
        if nlev is None:
            nlev = [len(z) for z in levels]
        return _slice_variables(ind @ ind.T, nlev, vars)
    raise ValueError("unknown output type")


def _indicator(values, levels):
    out = np.zeros((len(values), sum(len(z) for z in levels)), dtype=float)
    off = 0
    for j, lev in enumerate(levels):
        lookup = {v: i for i, v in enumerate(lev)}
        for i, value in enumerate(values[:, j]):
            out[i, off + lookup[value]] = 1
        off += len(lev)
    return out


def _decode_indicator(ind, levels):
    out = np.empty((len(ind), len(levels)), dtype=int)
    off = 0
    for j, lev in enumerate(levels):
        out[:, j] = np.argmax(ind[:, off:off + len(lev)], axis=1)
        off += len(lev)
    return out


def _infer_nlev(burt):
    zero = burt.copy()
    np.fill_diagonal(zero, 0)
    result, start = [], 0
    for i in range(1, len(zero)):
        if np.any(zero[start:i + 1, start:i + 1]) or i == len(zero) - 1:
            result.append(i - start + (i == len(zero) - 1))
            start = i
    return result


def _slice_variables(matrix, nlev, vars):
    starts = np.r_[0, np.cumsum(nlev)]
    i, j = np.asarray(vars, dtype=int)
    if i >= 1 and j >= 1:
        i, j = i - 1, j - 1
    return matrix[starts[i]:starts[i + 1], starts[j]:starts[j + 1]]
