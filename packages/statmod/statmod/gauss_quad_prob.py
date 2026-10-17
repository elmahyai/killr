"""Gaussian quadrature with probability distributions.

Translated from statmod 1.5.2 ``gauss.quad.prob`` in ``R/gaussquad.R``.
"""

from __future__ import annotations

import math

import numpy as np

from statmod.gauss_quad import _as_float, _as_n, _gausq2, _match_arg

_DISTS = ("uniform", "beta1", "beta2", "normal", "beta", "gamma")


def gauss_quad_prob(
    n,
    dist="uniform",
    l=0,
    u=1,
    mu=0,
    sigma=1,
    alpha=1,
    beta=1,
):
    """Nodes and weights for Gaussian quadrature on a probability distribution."""
    count = _as_n(n)
    if count == 0:
        empty = np.zeros(0, dtype=float)
        return {"nodes": empty, "weights": empty.copy()}
    rule = _match_arg(dist, _DISTS)
    l = _as_float(l)
    u = _as_float(u)
    mu = _as_float(mu)
    sigma = _as_float(sigma)
    alpha = _as_float(alpha)
    beta = _as_float(beta)
    if count == 1:
        node = _one_node(rule, l, u, mu, alpha, beta)
        return {"nodes": np.array([node], dtype=float), "weights": np.array([1.0], dtype=float)}
    if rule == "beta" and alpha == 0.5 and beta == 0.5:
        rule = "beta1"
    if rule == "beta" and alpha == 1.5 and beta == 1.5:
        rule = "beta2"
    diagonal, sub = _coefficients(count, rule, alpha, beta)
    first = np.zeros(count, dtype=float)
    first[0] = 1.0
    nodes, lead, _ierr = _gausq2(diagonal, sub, first)
    nodes = np.asarray(nodes, dtype=float)
    weights = np.square(np.asarray(lead, dtype=float))
    nodes = _transform_nodes(nodes, rule, l, u, mu, sigma, beta)
    return {"nodes": nodes, "weights": weights}


def _one_node(rule, l, u, mu, alpha, beta):
    if rule in ("uniform",):
        return (l + u) / 2.0
    if rule in ("beta1", "beta2", "beta"):
        return alpha / (alpha + beta)
    if rule == "normal":
        return mu
    if rule == "gamma":
        return alpha * beta
    raise ValueError(rule)


def _coefficients(n, rule, alpha, beta):
    index = np.arange(1, n + 1, dtype=float)
    lower = index[:-1]
    if rule == "uniform":
        diagonal = np.zeros(n, dtype=float)
        sub = lower / np.sqrt(4.0 * lower * lower - 1.0)
    elif rule == "beta1":
        diagonal = np.zeros(n, dtype=float)
        sub = np.full(n - 1, 0.5, dtype=float)
        if n == 1:
            sub = np.array([math.sqrt(0.5)], dtype=float)
        else:
            sub[0] = math.sqrt(0.5)
    elif rule == "beta2":
        diagonal = np.zeros(n, dtype=float)
        sub = np.full(max(n - 1, 0), 0.5, dtype=float)
    elif rule == "normal":
        diagonal = np.zeros(n, dtype=float)
        sub = np.sqrt(lower / 2.0)
    elif rule == "beta":
        both = alpha + beta
        diagonal = index.copy()
        diagonal[0] = (alpha - beta) / both
        if n > 1:
            upper = np.arange(2, n + 1, dtype=float)
            step = both - 2.0 + 2.0 * upper
            diagonal[1:] = ((alpha - 1.0) ** 2 - (beta - 1.0) ** 2) / (step - 2.0) / step
        first = math.sqrt(4.0 * alpha * beta / both ** 2 / (both + 1.0))
        if n == 1:
            sub = np.array([first], dtype=float)
        else:
            sub = np.empty(n - 1, dtype=float)
            sub[0] = first
            if n > 2:
                upper = np.arange(2, n, dtype=float)
                step = both - 2.0 + 2.0 * upper
                sub[1:] = np.sqrt(
                    4.0
                    * upper
                    * (upper + alpha - 1.0)
                    * (upper + beta - 1.0)
                    * (upper + both - 2.0)
                    / (step * step - 1.0)
                    / (step * step)
                )
    elif rule == "gamma":
        diagonal = 2.0 * index + alpha - 2.0
        sub = np.sqrt(lower * (lower + alpha - 1.0))
    else:
        raise ValueError(rule)
    sub = np.concatenate([np.asarray(sub, dtype=float).reshape(-1), np.array([0.0])])
    return np.asarray(diagonal, dtype=float), sub


def _transform_nodes(nodes, rule, l, u, mu, sigma, beta):
    if rule == "uniform":
        return l + (u - l) * (nodes + 1.0) / 2.0
    if rule in ("beta1", "beta2", "beta"):
        return (nodes + 1.0) / 2.0
    if rule == "normal":
        return mu + math.sqrt(2.0) * sigma * nodes
    if rule == "gamma":
        return beta * nodes
    raise ValueError(rule)
