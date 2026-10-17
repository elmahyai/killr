"""Model-based hierarchical clustering backed by the mclust kernels."""

from __future__ import annotations

import numpy as np

from ._bic_objects import with_initial_partition
from .model_metadata import partconv


def _partition(partition, n):
    """R ``partconv(partition, consec = TRUE)``: classes numbered by first appearance."""
    if partition is None:
        return np.arange(1, n + 1, dtype=np.int32)
    values = np.asarray(partition).reshape(-1)
    if len(values) != n:
        raise ValueError("partition must assign a class to each observation")
    return partconv(values, consec=True).astype(np.int32)


def _colmeans(x):
    """R ``colMeans``: a long double running sum, divided by n in long double, then rounded."""
    total = np.add.accumulate(x.astype(np.longdouble), axis=0)[-1]
    return (total / np.longdouble(x.shape[0])).astype(float)


def _center(x):
    """R ``scale(x, center = TRUE, scale = FALSE)``."""
    return x - _colmeans(x)


def _scale(x, centered):
    """R ``scale(x, center = TRUE, scale = TRUE)`` given the centred values.

    R: ``sqrt(sum(v^2) / max(1, length(v) - 1))`` with ``sum`` in long double.
    """
    n = x.shape[0]
    sq = (centered * centered).astype(np.longdouble)
    ss = np.add.accumulate(sq, axis=0)[-1].astype(float)
    return centered / np.sqrt(ss / max(1, n - 1))


def _drop_nonfinite(x):
    """R ``dropCols``: keep the columns whose values are all finite."""
    return x[:, np.all(np.isfinite(x), axis=0)]


def _traceW(x):
    """R ``traceW(x)``: the Fortran ``mcltrw`` routine, run from mclust_kernels."""
    import mclust_kernels

    n, p = x.shape
    out = mclust_kernels.mcltrw((np.asarray(x, order="F").ravel(order="F").tolist(), n, p, [0.0] * p, 0.0))
    return float(out[4])


def _prep(data, use):
    x = np.asarray(data, dtype=float)
    if x.ndim == 1:
        x = x.reshape(-1, 1)
    if x.ndim != 2:
        raise ValueError("data must be a matrix or vector")
    use = str(use).upper()
    if use == "VARS":
        return x
    centered = _center(x)
    if use == "STD":
        return _drop_nonfinite(_scale(x, centered))
    if use == "PCS":
        _, _, v = np.linalg.svd(centered, full_matrices=False)
        return _drop_nonfinite(centered @ v.T)
    if use == "PCR":
        z = _drop_nonfinite(_scale(x, centered))
        _, _, v = np.linalg.svd(z, full_matrices=False)
        return z @ v.T
    if use == "SPH":
        # R: Sigma = var(data) * (n - 1) / n; Z = data %*% V %*% diag(1 / sqrt(d))
        sigma = np.cov(centered, rowvar=False, bias=True).reshape(x.shape[1], x.shape[1])
        _, s, vt = np.linalg.svd(sigma)
        return centered @ vt.T / np.sqrt(s)
    if use == "SVD":
        # R: data = dropCols(scale(data)); Z = data %*% V %*% diag(1 / sqrt(d), p, p)
        z = _drop_nonfinite(_scale(x, centered))
        _, s, vt = np.linalg.svd(z, full_matrices=False)
        return (z @ vt.T) * (1.0 / np.sqrt(s))
    if use == "RND":
        raise NotImplementedError("random-pairs hierarchical clustering is not translated")
    raise ValueError("invalid use")


def _kernel(name, x, partition, minclus, alpha=1.0, beta=1.0):
    import mclust_kernels

    n, p = x.shape
    ic = _partition(partition, n)
    l = int(ic.max())
    m = l - int(minclus)
    if int(minclus) < 1 or m <= 0:
        raise ValueError("initial number of clusters is not greater than minclus")
    ld = max(l * (l - 1) // 2, 3 * m)
    xf = np.asarray(x, order="F").ravel(order="F").tolist()
    if name == "E":
        out = mclust_kernels.hc1e((xf, n, ic.tolist(), l, m, ld, [0.0] * ld))
        return np.vstack((out[0][:m], out[2][:m]))
    if name == "V":
        a = alpha * float(np.sum((x - x.mean(axis=0)) ** 2) / n)
        a = min(a, np.finfo(float).eps)
        out = mclust_kernels.hc1v((xf, n, ic.tolist(), l, m, a, ld, [0.0] * ld))
        return np.vstack((out[0][:m], out[2][:m]))
    if name == "EII":
        out = mclust_kernels.hceii((xf, n, p, ic.tolist(), l, m, [0.0] * p, ld, [0.0] * ld))
        xx = np.asarray(out[0], dtype=float).reshape((n, p), order="F")
        return xx[:m, :2].T
    if name == "VII":
        ld = max(n, l * (l - 1) // 2, 3 * m)
        a = alpha * float(np.sum((x - x.mean(axis=0)) ** 2) / (n * p))
        a = max(a, np.finfo(float).eps)
        out = mclust_kernels.hcvii((xf, n, p, ic.tolist(), l, m, a, [0.0] * p, ld, [0.0] * ld))
        xx = np.asarray(out[0], dtype=float).reshape((n, p), order="F")
        return xx[:m, :2].T
    if name == "EEE":
        out = mclust_kernels.hceee((xf, n, p, ic.tolist(), l, m,
                                    [0] * max(m, 1), [0] * max(m, 1),
                                    [0.0] * p, [0.0] * (p * p),
                                    [0.0] * (p * p), [0.0] * (p * p)))
        xx = np.asarray(out[0], dtype=float).reshape((n, p), order="F")
        if p < 3:
            return np.vstack((np.asarray(out[6], dtype=float)[:m],
                              np.asarray(out[7], dtype=float)[:m]))
        if p < 4:
            return np.vstack((xx[1:, 2], np.asarray(out[7], dtype=float)[:m]))
        return xx[1:m + 1, 2:4].T
    if name == "VVV":
        ld = max(n, l * (l - 1) // 2 + 1, 3 * m)
        # R: alpha <- alpha * traceW(data / sqrt(n * p)); alpha <- max(alpha, eps)
        a = alpha * _traceW(x / np.sqrt(n * p))
        a = max(a, np.finfo(float).eps)
        out = mclust_kernels.hcvvv((np.column_stack((x, np.zeros(n))).ravel(order="F").tolist(),
                                    n, p, ic.tolist(), l, m, a, beta,
                                    [0.0] * p, [0.0] * (p * p), [0.0] * (p * p),
                                    [0.0] * (p * p), ld, [0.0] * ld))
        xx = np.asarray(out[0], dtype=float).reshape((n, p + 1), order="F")
        return xx[:m, :2].T
    raise ValueError("invalid modelName")


def hc(data, modelName="VVV", use="VARS", partition=None, minclus=1, **kwargs):
    """Perform model-based hierarchical clustering."""
    model = str(modelName).upper()
    if model not in {"E", "V", "EII", "VII", "EEE", "VVV"}:
        raise ValueError("invalid modelName")
    z = _prep(data, use)
    # R: hcXXX takes partition = NULL, which means 1:n; the classes are renumbered by
    # partconv and stored as the initialPartition attribute.
    part = _partition(partition, z.shape[0])
    out = _kernel(model, z, part, minclus, kwargs.get("alpha", 1.0), kwargs.get("beta", 1.0))
    return with_initial_partition(out, part)


__all__ = ["hc"]
