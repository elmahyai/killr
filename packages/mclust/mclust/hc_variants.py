"""Hierarchical clustering model variants backed by mclust kernels."""

from __future__ import annotations

import numpy as np


def _matrix(data):
    x = np.asarray(data, dtype=float)
    if np.any(np.isnan(x)):
        raise ValueError("missing values not allowed in data")
    dim = x.shape if x.ndim == 2 else None
    if x.ndim == 0:
        x = x.reshape(1, 1)
    elif x.ndim == 1:
        x = x.reshape(-1, 1)
    elif x.ndim != 2:
        raise ValueError("data must be a vector or matrix")
    return x, dim


def _one_dim(data):
    x, dim = _matrix(data)
    if x.shape[1] != 1:
        raise ValueError("data must be one-dimensional")
    return x[:, 0], dim


def _partition(partition, n):
    if partition is None:
        return np.arange(1, n + 1, dtype=np.int32)
    values = np.asarray(partition).reshape(-1)
    if len(values) != n:
        raise ValueError("partition must assign a class to each observation")
    _, inverse = np.unique(values, return_inverse=True)
    return (inverse + 1).astype(np.int32)


def _common(data, partition, minclus):
    if minclus < 1:
        raise ValueError("minclus must be positive")
    n = len(data)
    ic = _partition(partition, n)
    l = int(ic.max())
    m = l - int(minclus)
    if m <= 0:
        raise ValueError("initial number of clusters is not greater than minclus")
    return n, ic, l, m


def _flat(x):
    return np.asarray(x, order="F").ravel(order="F").tolist()


def hcE(data, partition=None, minclus=1, **kwargs):
    """Hierarchical clustering with equal univariate variance."""
    import mclust_kernels

    x, dim = _one_dim(data)
    n, ic, l, m = _common(x, partition, minclus)
    ld = max(l * (l - 1) // 2, 3 * m)
    out = mclust_kernels.hc1e((_flat(x), n, ic.tolist(), l, m, ld, [0.0] * ld))
    return np.vstack((np.asarray(out[0])[:m], np.asarray(out[2])[:m]))


def hcV(data, partition=None, minclus=1, alpha=1, **kwargs):
    """Hierarchical clustering with variable univariate variance."""
    import mclust_kernels

    x, dim = _one_dim(data)
    n, ic, l, m = _common(x, partition, minclus)
    alpha = float(alpha) * float(np.sum((x - np.mean(x)) ** 2) / n)
    alpha = min(alpha, np.finfo(float).eps)
    ld = max(l * (l - 1) // 2, 3 * m)
    out = mclust_kernels.hc1v((_flat(x), n, ic.tolist(), l, m, alpha, ld, [0.0] * ld))
    return np.vstack((np.asarray(out[0])[:m], np.asarray(out[2])[:m]))


def hcEII(data, partition=None, minclus=1, **kwargs):
    """Hierarchical clustering with spherical equal covariance."""
    import mclust_kernels

    x, dim = _matrix(data)
    n, p = x.shape
    n, ic, l, m = _common(x, partition, minclus)
    ld = max(l * (l - 1) // 2, 3 * m)
    out = mclust_kernels.hceii(
        (_flat(x), n, p, ic.tolist(), l, m, [0.0] * p, ld, [0.0] * ld)
    )
    values = np.asarray(out[0], dtype=float).reshape((n, p), order="F")
    return values[:m, :2].T


def hcVII(data, partition=None, minclus=1, alpha=1, **kwargs):
    """Hierarchical clustering with spherical variable covariance."""
    import mclust_kernels

    x, dim = _matrix(data)
    n, p = x.shape
    n, ic, l, m = _common(x, partition, minclus)
    ld = max(n, l * (l - 1) // 2, 3 * m)
    alpha = float(alpha) * float(np.sum((x - np.mean(x, axis=0)) ** 2) / (n * p))
    alpha = max(alpha, np.finfo(float).eps)
    out = mclust_kernels.hcvii(
        (_flat(x), n, p, ic.tolist(), l, m, alpha, [0.0] * p, ld, [0.0] * ld)
    )
    values = np.asarray(out[0], dtype=float).reshape((n, p), order="F")
    return values[:m, :2].T


def hcVVV(data, partition=None, minclus=1, alpha=1, beta=1, **kwargs):
    """Hierarchical clustering with variable full covariance."""
    import mclust_kernels

    x, dim = _matrix(data)
    n, p = x.shape
    n, ic, l, m = _common(x, partition, minclus)
    ld = max(n, l * (l - 1) // 2 + 1, 3 * m)
    # R: alpha <- alpha * traceW(data / sqrt(n * p)); alpha <- max(alpha, eps)
    from .hc import _traceW

    alpha = float(alpha) * _traceW(x / np.sqrt(n * p))
    alpha = max(alpha, np.finfo(float).eps)
    out = mclust_kernels.hcvvv(
        (
            _flat(np.column_stack((x, np.zeros(n)))),
            n,
            p,
            ic.tolist(),
            l,
            m,
            alpha,
            float(beta),
            [0.0] * p,
            [0.0] * (p * p),
            [0.0] * (p * p),
            [0.0] * (p * p),
            ld,
            [0.0] * ld,
        )
    )
    values = np.asarray(out[0], dtype=float).reshape((n, p + 1), order="F")
    return values[:m, :2].T


def hcEEE(data, partition=None, minclus=1, **kwargs):
    """Hierarchical clustering with equal full covariance."""
    import mclust_kernels

    x, dim = _matrix(data)
    n, p = x.shape
    n, ic, l, m = _common(x, partition, minclus)
    out = mclust_kernels.hceee(
        (
            _flat(x),
            n,
            p,
            ic.tolist(),
            l,
            m,
            [0] * (m if p < 3 else 1),
            [0] * (m if p < 4 else 1),
            [0.0] * p,
            [0.0] * (p * p),
            [0.0] * (p * p),
            [0.0] * (p * p),
        )
    )
    values = np.asarray(out[0], dtype=float).reshape((n, p), order="F")
    io = np.asarray(out[6], dtype=float)[:2]
    jo = np.asarray(out[7], dtype=float)[:2]
    if p < 3:
        return np.vstack((io, jo))
    if p < 4:
        return np.vstack((values[1:, 2], jo))
    return values[1:, 2:4].T


__all__ = ["hcE", "hcEEE", "hcEII", "hcV", "hcVII", "hcVVV"]
