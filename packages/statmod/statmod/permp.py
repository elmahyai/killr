"""Exact permutation p-values for resampled permutation tests.

Translated from statmod 1.5.2 ``permp`` in ``R/permp.R``.
"""

from __future__ import annotations

import math

import numpy as np

from statmod.gauss_quad import _gausq2, _match_arg

_METHODS = ("auto", "exact", "approximate")


def permp(x, nperm, n1=None, n2=None, total_nperm=None, method="auto", twosided=True):
    """P-values when permutations are drawn with replacement."""
    values = np.asarray(x, dtype=float)
    flat = values.reshape(-1)
    if np.any(flat < 0):
        raise ValueError("negative x values")
    nperm = int(nperm)
    if np.any(flat > nperm):
        raise ValueError("x cannot exceed nperm")

    if total_nperm is None:
        if n1 is None or n2 is None:
            raise TypeError("total.nperm is NULL")
        total_nperm = math.comb(int(n1) + int(n2), int(n1))
        if int(n1) == int(n2) and twosided:
            total_nperm = total_nperm // 2

    method = _match_arg(method, _METHODS)
    if method == "auto":
        method = "approximate" if total_nperm > 10000 else "exact"

    out = flat.copy()
    if method == "exact":
        probs = (np.arange(1, total_nperm + 1, dtype=float)) / float(total_nperm)
        columns = []
        for count in flat:
            columns.append(_pbinom(count, nperm, probs))
        out[:] = np.column_stack(columns).mean(axis=0)
    else:
        quad = _gauss_quad_prob_uniform(128, l=0.0, u=0.5 / float(total_nperm))
        probs = quad["nodes"]
        weights = quad["weights"]
        scale = 0.5 / float(total_nperm)
        columns = []
        for count in flat:
            y = _pbinom(count, nperm, probs)
            integral = scale * float(np.sum(weights * y))
            columns.append((count + 1.0) / (nperm + 1.0) - integral)
        out[:] = np.asarray(columns, dtype=float)

    return out.reshape(values.shape)


def _pbinom(q, size, prob):
    """``stats::pbinom`` lower tail with vector ``prob`` and scalar ``q``."""
    q = int(math.floor(float(q)))
    size = int(size)
    prob = np.asarray(prob, dtype=float)
    out = np.empty(prob.shape, dtype=float)
    for index, p in enumerate(prob.reshape(-1)):
        if not math.isfinite(p) or p < 0.0 or p > 1.0:
            out.reshape(-1)[index] = math.nan
            continue
        if q < 0:
            out.reshape(-1)[index] = 0.0
            continue
        if q >= size:
            out.reshape(-1)[index] = 1.0
            continue
        total = 0.0
        tail = 1.0 - p
        for k in range(q + 1):
            total += math.comb(size, k) * (p**k) * (tail ** (size - k))
        out.reshape(-1)[index] = total
    return out


def _gauss_quad_prob_uniform(n, l=0.0, u=1.0):
    """Uniform ``gauss.quad.prob`` nodes and weights."""
    count = int(n)
    if count < 0:
        raise ValueError("need non-negative number of nodes")
    if count == 0:
        empty = np.zeros(0, dtype=float)
        return {"nodes": empty, "weights": empty.copy()}
    if count == 1:
        node = (float(l) + float(u)) / 2.0
        return {"nodes": np.array([node], dtype=float), "weights": np.array([1.0], dtype=float)}
    index = np.arange(1, count + 1, dtype=float)
    lower = index[:-1]
    diagonal = np.zeros(count, dtype=float)
    sub = lower / np.sqrt(4.0 * lower * lower - 1.0)
    sub = np.concatenate([sub, np.array([0.0])])
    first = np.zeros(count, dtype=float)
    first[0] = 1.0
    nodes, lead, _ierr = _gausq2(diagonal, sub, first)
    nodes = np.asarray(nodes, dtype=float)
    weights = np.square(np.asarray(lead, dtype=float))
    nodes = float(l) + (float(u) - float(l)) * (nodes + 1.0) / 2.0
    return {"nodes": nodes, "weights": weights}
