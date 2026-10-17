"""Empirical influence values, linear bootstrap approximations, and envelopes.

This is the CRAN boot 1.3-32 code for empinf, linear.approx, and envelope.
A bootstrap argument is any object with the components those functions read
(data, statistic, stype, sim, strata, R, t, t0, seed). Indices passed to a
statistic with stype "i" are 1-based, as in R. This module does not call boot().
"""

from __future__ import annotations

import math
import warnings
from types import SimpleNamespace

import numpy as np

from boot import rng

__all__ = ["empinf", "linear_approx", "envelope"]


def empinf(
    boot_out=None,
    data=None,
    statistic=None,
    type=None,
    stype=None,
    index=1,
    t=None,
    strata=None,
    eps=0.001,
    **kwargs,
):
    """Empirical influence values for a statistic on one or more samples.

    type is "inf" (infinitesimal jackknife), "jack" (delete-one), "pos"
    (include-one-twice), or "reg" (regression on bootstrap frequencies).
    The default follows the R rule: "reg" when t is supplied, otherwise
    "inf" when stype is "w", otherwise "reg" or "jack" from the bootstrap
    object, and "jack" when none of those apply.
    """
    if boot_out is not None:
        if getattr(boot_out, "sim", None) == "parametric":
            raise ValueError(
                "influence values cannot be found from a parametric bootstrap"
            )
        data = boot_out.data
        if statistic is None:
            statistic = boot_out.statistic
        if stype is None:
            stype = boot_out.stype
        boot_strata = getattr(boot_out, "strata", None)
        if boot_strata is not None:
            strata = boot_strata
    else:
        if data is None:
            raise ValueError("neither 'data' nor bootstrap object specified")
        if statistic is None:
            raise ValueError("neither 'statistic' nor bootstrap object specified")
        if stype is None:
            stype = "w"

    n = _nrow(data)
    if strata is None:
        strata = np.ones(n, dtype=int)

    if type is None:
        if t is not None:
            type = "reg"
        elif stype == "w":
            type = "inf"
        elif (
            boot_out is not None
            and getattr(boot_out, "sim", None) != "parametric"
            and getattr(boot_out, "sim", None) != "permutation"
        ):
            if boot_out.R < n:
                type = "jack"
            else:
                type = "reg"
        else:
            type = "jack"

    if type == "inf":
        if stype != "w":
            raise ValueError("'stype' must be \"w\" for type=\"inf\"")
        index = _one_index(index)
        if t is not None:
            warnings.warn("input 't' ignored; type=\"inf\"", stacklevel=2)
        return _inf_jack(data, statistic, index, strata, eps, **kwargs)
    if type == "reg":
        if boot_out is None:
            raise ValueError("bootstrap object needed for type=\"reg\"")
        if t is None:
            index = _one_index(index)
            replicates = np.asarray(boot_out.t, dtype=float)
            if replicates.ndim == 1:
                t = replicates
            else:
                t = replicates[:, index - 1]
        return _empinf_reg(boot_out, t)
    if type == "jack":
        if t is not None:
            warnings.warn("input 't' ignored; type=\"jack\"", stacklevel=2)
        index = _one_index(index)
        return _usual_jack(data, statistic, stype, index, strata, **kwargs)
    if type == "pos":
        if t is not None:
            warnings.warn("input 't' ignored; type=\"pos\"", stacklevel=2)
        index = _one_index(index)
        return _positive_jack(data, statistic, stype, index, strata, **kwargs)
    raise ValueError("type must be \"inf\", \"reg\", \"jack\", or \"pos\"")


def linear_approx(boot_out, L=None, index=1, type=None, t0=None, t=None, **kwargs):
    """Linear approximation to each bootstrap replicate.

    For frequency row f and stratum sizes n_s the approximation is
    t0 + sum_s (f_s · L_s) / n_s. L is taken from empinf when it is omitted.
    Frequencies are rebuilt from boot_out.seed the way boot.array does for
    an ordinary or permutation bootstrap.
    """
    frequencies = _boot_array(boot_out)
    n = frequencies.shape[1]
    if _index_length(index) > 1 and (t0 is None or t is None):
        warnings.warn("only first element of 'index' used", stacklevel=2)
    index = int(np.atleast_1d(np.asarray(index)).ravel()[0])

    if t0 is None:
        observed = np.atleast_1d(np.asarray(boot_out.t0, dtype=float)).ravel()
        t0 = observed[index - 1]
        if L is None:
            L = empinf(boot_out, index=index, type=type, **kwargs)
    elif t is None and L is None:
        warnings.warn(
            "input 't0' ignored: neither 't' nor 'L' supplied",
            stacklevel=2,
        )
        supplied = np.atleast_1d(np.asarray(t0, dtype=float)).ravel()
        t0 = supplied[index - 1]
        L = empinf(boot_out, index=index, type=type, **kwargs)
    elif L is None:
        L = empinf(boot_out, type=type, t=t, **kwargs)

    t0_values = np.atleast_1d(np.asarray(t0, dtype=float)).ravel()
    # R's rep(t0, R) repeats the whole vector R times. A scalar is the usual case.
    replicates = int(boot_out.R)
    if t0_values.size == 1:
        tL = np.full(replicates, float(t0_values[0]))
    else:
        tL = np.tile(t0_values, replicates)

    strata = _group_codes(getattr(boot_out, "strata", None), n)
    influence = np.asarray(L, dtype=float).ravel()
    n_groups = int(strata.max())
    for group in range(1, n_groups + 1):
        columns = np.flatnonzero(strata == group)
        addition = frequencies[:, columns] @ influence[columns]
        tL = tL + np.asarray(addition, dtype=float).ravel() / columns.size
    return np.asarray(tL, dtype=float).ravel()


def envelope(boot_out=None, mat=None, level=0.95, index=None):
    """Pointwise and overall confidence envelopes for a curve.

    mat has one row per bootstrap replicate and one column per abscissa.
    When boot_out is supplied and boot_out.t is a matrix, that matrix is used.
    index chooses columns and is 1-based. level is one confidence level for
    both envelopes, or a pair (pointwise, overall).
    """

    def emperr(rmat, p=0.05, k=None):
        rows = rmat.shape[0]
        if k is None:
            k = p * (rows + 1) / 2.0
        else:
            p = 2.0 * float(k) / (rows + 1)
        limit = (rows + 1) - k
        count = 0
        for row in rmat:
            if row.min() <= k or row.max() >= limit:
                count += 1
        return np.array([float(k), float(p), count / (rows + 1)], dtype=float)

    def kfun(x, k1, k2):
        positions = np.concatenate(
            [np.atleast_1d(np.asarray(k1, dtype=float)), np.atleast_1d(np.asarray(k2, dtype=float))]
        )
        positions = np.rint(positions).astype(int)
        ordered = np.sort(np.asarray(x, dtype=float))
        if np.any(positions < 1) or np.any(positions > ordered.size):
            bad = int(positions[np.where((positions < 1) | (positions > ordered.size))[0][0]])
            raise ValueError(f"'partial' index {bad} outside bounds")
        return ordered[positions - 1]

    if boot_out is not None and _is_matrix(getattr(boot_out, "t", None)):
        mat = boot_out.t
    if not _is_matrix(mat):
        raise ValueError("bootstrap output matrix missing")
    mat = np.asarray(mat, dtype=float)
    if index is None:
        index = np.arange(1, mat.shape[1] + 1)
    index = np.atleast_1d(np.asarray(index, dtype=int)).ravel()
    if index.size < 2:
        raise ValueError("use 'boot.ci' for scalar parameters")
    mat = mat[:, index - 1]
    ranked = np.column_stack([_rank_average(mat[:, j]) for j in range(mat.shape[1])])
    rows = mat.shape[0]
    level = np.atleast_1d(np.asarray(level, dtype=float)).ravel()
    if level.size == 1:
        level = np.array([level[0], level[0]], dtype=float)
    k_point = math.floor((rows + 1) * (1.0 - level[0]) / 2.0 + 1e-10)
    k_point = np.array([k_point, rows + 1 - k_point], dtype=float)
    err_point = emperr(ranked, k=k_point[0])
    overall_error = emperr(ranked, k=1)
    edge = err_point.copy()
    nominal = 1.0 - level[1]
    if overall_error[2] > nominal:
        warnings.warn("unable to achieve requested overall error rate", stacklevel=2)
    else:
        keep_searching = not (edge[2] < nominal)
        while keep_searching:
            span = edge[2] - overall_error[2]
            step = (edge[0] - overall_error[0]) * (nominal - overall_error[2]) / span
            kk = overall_error[0] + float(np.round(step))
            if kk == overall_error[0]:
                kk = kk + 1.0
            elif kk == edge[0]:
                kk = kk - 1.0
            trial = emperr(ranked, k=kk)
            if trial[2] > nominal:
                edge = trial
            else:
                overall_error = trial
            keep_searching = not (edge[0] == overall_error[0] + 1.0)
    k_overall = np.array(
        [overall_error[0], rows + 1 - overall_error[0]], dtype=float
    )
    columns = [kfun(mat[:, j], k_point, k_overall) for j in range(mat.shape[1])]
    out = np.column_stack(columns)
    return SimpleNamespace(
        point=out[[1, 0], :],
        overall=out[[3, 2], :],
        k_pt=k_point,
        err_pt=err_point[1:],
        k_ov=k_overall,
        err_ov=overall_error[1:],
        err_nom=1.0 - level[:2],
    )


def _inf_jack(data, stat, index, strata, eps, **kwargs):
    n = _nrow(data)
    eps = eps / n
    groups = _group_codes(strata, n)
    counts = np.bincount(groups)
    w_orig = 1.0 / counts[groups]
    observed = _at(stat(data, w_orig, **kwargs), index)
    influence = np.empty(n, dtype=float)
    for i in range(n):
        member = groups == groups[i]
        weights = w_orig.copy()
        weights[member] = (1.0 - eps) * weights[member]
        weights[i] = weights[i] + eps
        influence[i] = (_at(stat(data, weights, **kwargs), index) - observed) / eps
    return influence


def _empinf_reg(boot_out, t):
    replicates = np.ravel(np.asarray(t, dtype=float), order="F")
    finite = np.isfinite(replicates)
    replicates = replicates[finite]
    n = _nrow(boot_out.data)
    groups = _group_codes(getattr(boot_out, "strata", None), n)
    counts = np.bincount(groups)
    frequencies = _boot_array(boot_out)[finite, :]
    design = frequencies / counts[groups]
    dropped = []
    n_groups = int(groups.max())
    for group in range(1, n_groups + 1):
        dropped.append(int(np.flatnonzero(groups == group).min()))
    keep = np.setdiff1d(np.arange(n), np.asarray(dropped, dtype=int))
    influence = np.zeros(n, dtype=float)
    if keep.size:
        predictors = np.column_stack([np.ones(replicates.size), design[:, keep]])
        coefficients, *_ = np.linalg.lstsq(predictors, replicates, rcond=None)
        influence[keep] = coefficients[1:]
    means = np.zeros(n_groups + 1, dtype=float)
    for group in range(1, n_groups + 1):
        means[group] = influence[groups == group].mean()
    return influence - means[groups]


def _usual_jack(data, stat, stype, index, strata, **kwargs):
    n = _nrow(data)
    groups = _group_codes(strata, n)
    influence = np.zeros(n, dtype=float)
    if stype == "w":
        counts = np.bincount(groups)
        w0 = 1.0 / counts[groups]
        observed = _at(stat(data, w0, **kwargs), index)
        for i in range(n):
            weights = w0.copy()
            weights[i] = 0.0
            member = groups == groups[i]
            weights[member] = weights[member] / weights[member].sum()
            influence[i] = (member.sum() - 1) * (
                observed - _at(stat(data, weights, **kwargs), index)
            )
    elif stype == "f":
        f0 = np.ones(n, dtype=float)
        observed = _at(stat(data, f0, **kwargs), index)
        for i in range(n):
            frequencies = f0.copy()
            frequencies[i] = 0.0
            member = groups == groups[i]
            influence[i] = (member.sum() - 1) * (
                observed - _at(stat(data, frequencies, **kwargs), index)
            )
    else:
        indices = np.arange(1, n + 1)
        observed = _at(stat(data, indices, **kwargs), index)
        for i in range(n):
            left_out = np.concatenate([indices[:i], indices[i + 1 :]])
            member = groups == groups[i]
            influence[i] = (member.sum() - 1) * (
                observed - _at(stat(data, left_out, **kwargs), index)
            )
    return influence


def _positive_jack(data, stat, stype, index, strata, **kwargs):
    n = _nrow(data)
    groups = _group_codes(strata, n)
    influence = np.zeros(n, dtype=float)
    if stype == "w":
        counts = np.bincount(groups)
        w0 = 1.0 / counts[groups]
        observed = _at(stat(data, w0, **kwargs), index)
        for i in range(n):
            expanded = np.concatenate([groups, [groups[i]]])
            expanded_counts = np.bincount(expanded)
            weights = 1.0 / expanded_counts[groups]
            weights = np.array(weights, dtype=float, copy=True)
            weights[i] = 2.0 * weights[i]
            member = groups == groups[i]
            weights[member] = weights[member] / weights[member].sum()
            influence[i] = (member.sum() + 1) * (
                _at(stat(data, weights, **kwargs), index) - observed
            )
    elif stype == "f":
        f0 = np.ones(n, dtype=float)
        observed = _at(stat(data, f0, **kwargs), index)
        for i in range(n):
            frequencies = f0.copy()
            frequencies[i] = 2.0
            member = groups == groups[i]
            influence[i] = (member.sum() + 1) * (
                _at(stat(data, frequencies, **kwargs), index) - observed
            )
    elif stype == "i":
        indices = np.arange(1, n + 1)
        observed = _at(stat(data, indices, **kwargs), index)
        for i in range(n):
            doubled = np.concatenate([indices, [i + 1]])
            member = groups == groups[i]
            influence[i] = (member.sum() + 1) * (
                _at(stat(data, doubled, **kwargs), index) - observed
            )
    return influence


def _boot_array(boot_out):
    """Frequency array for an ordinary or permutation bootstrap.

    Restores boot_out.seed, draws the same indices as boot.array, then
    restores the previous generator state. seed may be an integer passed
    to set.seed, or the length-626 .Random.seed vector stored on a boot object.
    """
    sim = getattr(boot_out, "sim", None)
    if sim == "parametric":
        raise ValueError("array cannot be found for parametric bootstrap")
    boot_type = getattr(boot_out, "boot_type", None)
    if boot_type not in (None, "boot"):
        raise ValueError("array cannot be found for this bootstrap object")
    saved = (rng._mti, list(rng._mt))
    try:
        _restore_seed(boot_out.seed)
        n = _nrow(boot_out.data)
        replicates = int(boot_out.R)
        groups = _group_codes(getattr(boot_out, "strata", None), n)
        if sim == "ordinary":
            indices = _ordinary_array(n, replicates, groups)
        elif sim == "permutation":
            indices = _permutation_array(n, replicates, groups)
        else:
            raise ValueError(f"array cannot be found for sim={sim!r}")
        return _freq_array(indices)
    finally:
        rng._mti = saved[0]
        rng._mt[:] = saved[1]


def _ordinary_array(n, replicates, groups):
    levels = np.unique(groups)
    if levels.size == 1:
        draws = rng.sample_int(n, n * replicates, replace=True)
        return np.asarray(draws, dtype=int).reshape((replicates, n), order="F")
    output = np.zeros((replicates, n), dtype=int)
    for level in levels:
        positions = np.flatnonzero(groups == level)
        labels = positions + 1
        if positions.size == 1:
            output[:, positions] = labels[0]
        else:
            picks = rng.sample_int(positions.size, replicates * positions.size, replace=True)
            values = labels[np.asarray(picks, dtype=int) - 1]
            output[:, positions] = np.asarray(values, dtype=int).reshape(
                (replicates, positions.size), order="F"
            )
    return output


def _permutation_array(n, replicates, groups):
    output = np.tile(np.arange(1, n + 1, dtype=int)[:, None], (1, replicates))
    for level in np.unique(groups):
        positions = np.flatnonzero(groups == level)
        if positions.size > 1:
            for column in range(replicates):
                order = np.asarray(rng.sample_int(positions.size), dtype=int) - 1
                output[positions, column] = output[positions, column][order]
    return output.T


def _freq_array(indices):
    replicates, n = indices.shape
    frequencies = np.empty((replicates, n), dtype=float)
    for row in range(replicates):
        frequencies[row] = np.bincount(indices[row], minlength=n + 1)[1 : n + 1]
    return frequencies


def _restore_seed(seed):
    values = np.asarray(seed, dtype=np.int64).ravel()
    if values.size == 1:
        rng.set_seed(int(values[0]))
        return
    if values.size != 626:
        raise ValueError("seed must be an integer or R .Random.seed of length 626")
    rng._mti = int(values[1])
    state = np.mod(values[2:], 2**32).astype(np.uint64)
    rng._mt[:] = [int(item) for item in state]


def _rank_average(x):
    values = np.asarray(x, dtype=float)
    n = values.size
    order = np.argsort(values, kind="mergesort")
    ranks = np.empty(n, dtype=float)
    ordered = values[order]
    start = 0
    while start < n:
        stop = start + 1
        while stop < n and ordered[stop] == ordered[start]:
            stop += 1
        ranks[order[start:stop]] = (start + 1 + stop) / 2.0
        start = stop
    return ranks


def _group_codes(strata, n):
    """1-based codes from tapply(strata, as.numeric(strata)) with FUN omitted."""
    if strata is None:
        return np.ones(n, dtype=int)
    values = _as_numeric(strata)
    if values.size != n:
        raise ValueError("arguments must have same length")
    if np.any(~np.isfinite(values)):
        raise ValueError("missing values in 'strata'")
    levels = np.unique(values)
    return (np.searchsorted(levels, values) + 1).astype(int)


def _as_numeric(strata):
    array = np.asarray(strata)
    if array.dtype.kind in "iuf":
        return np.ravel(array.astype(float))
    # A factor's as.numeric() codes follow sorted level names.
    labels = [str(item) for item in array.ravel().tolist()]
    levels = sorted(set(labels))
    mapping = {label: float(i + 1) for i, label in enumerate(levels)}
    return np.array([mapping[label] for label in labels], dtype=float)


def _nrow(data):
    if isinstance(data, dict):
        if not data:
            raise ValueError("no data in call")
        return len(np.asarray(next(iter(data.values()))))
    array = np.asarray(data)
    if array.ndim == 0:
        return 1
    return int(array.shape[0])


def _is_matrix(value):
    if value is None:
        return False
    return np.asarray(value).ndim == 2


def _index_length(index):
    return int(np.atleast_1d(np.asarray(index)).size)


def _one_index(index):
    values = np.atleast_1d(np.asarray(index)).ravel()
    if values.size != 1:
        warnings.warn("only first element of 'index' used", stacklevel=3)
    return int(values[0])


def _at(value, index):
    flat = np.ravel(np.asarray(value, dtype=float), order="F")
    return float(flat[index - 1])
