"""Small computational utilities from mclust."""

import math
from collections import Counter

import numpy as np


def count(x, bins):
    """Count occurrences of each bin, in the order supplied."""
    values = np.asarray(x).ravel()
    labels = np.asarray(bins).ravel()
    return np.asarray([np.sum(values == b) for b in labels], dtype=int)


def dmvnorm(data, mean=None, sigma=None, log=False):
    """Multivariate normal density, matching mclust's row-wise interface."""
    x = np.atleast_2d(np.asarray(data, dtype=float))
    n, d = x.shape
    mu = np.zeros(d) if mean is None else np.asarray(mean, dtype=float).ravel()
    if mu.size != d:
        raise ValueError("data and mean have non-conforming size")
    cov = np.eye(d) if sigma is None else np.asarray(sigma, dtype=float)
    if cov.ndim != 2 or cov.shape[1] != d:
        raise ValueError("data and sigma have non-conforming size")
    if np.max(np.abs(cov - cov.T)) > math.sqrt(np.finfo(float).eps):
        raise ValueError("sigma must be a symmetric matrix")
    sign, logdet = np.linalg.slogdet(cov)
    if sign <= 0:
        raise ValueError("sigma must be positive definite")
    delta = x - mu
    logdens = -0.5 * (d * math.log(2 * math.pi) + logdet +
                      np.einsum("ni,ij,nj->n", delta, np.linalg.inv(cov), delta))
    return logdens if log else np.exp(logdens)


def covw(X, Z, normalize=True):
    """Weighted means, covariances, and scattering matrices."""
    x = np.asarray(X, dtype=float)
    z = np.asarray(Z, dtype=float)
    if x.ndim == 1:
        x = x[:, None]
    if z.ndim == 1:
        z = z[:, None]
    if x.shape[0] != z.shape[0]:
        raise ValueError("X and Z must have same number of rows")
    if normalize:
        z = z / z.sum(axis=1, keepdims=True)
    weights = z.sum(axis=0)
    means = x.T @ z / weights
    scatter = np.empty((x.shape[1], x.shape[1], z.shape[1]))
    covariance = np.empty_like(scatter)
    for k, wk in enumerate(weights):
        centered = x - means[:, k]
        scatter[:, :, k] = centered.T @ (centered * z[:, k, None])
        covariance[:, :, k] = scatter[:, :, k] / wk
    return {"mean": means, "S": covariance, "W": scatter}


def hdrlevels(density, prob):
    """Density thresholds for requested highest-density probabilities."""
    p = np.clip(np.asarray(prob, dtype=float), 0, 1)
    return np.quantile(np.asarray(density).ravel(), 1 - p, method="linear")


def hypvol(data, reciprocal=False):
    """Minimum axis-aligned/PCA hypervolume used by mclust."""
    a = np.asarray(data, dtype=float)
    if a.ndim == 1 or (a.ndim == 2 and a.shape[1] == 1):
        value = np.ptp(a)
        return 1.0 / value if reciprocal else value
    if a.ndim != 2:
        raise ValueError("data must be a vector or a matrix")
    bd = np.ptp(a, axis=0)
    centered = a - a.mean(axis=0)
    scores = centered @ np.linalg.svd(centered, full_matrices=False)[2].T
    pc = np.ptp(scores, axis=0)
    log_volume = min(np.log(bd).sum(), np.log(pc).sum())
    return float(np.exp(-log_volume if reciprocal else log_volume))


def majorityVote(x):
    """Return the frequency table, winning index, and winning label."""
    values = np.asarray(x).ravel()
    labels, frequencies = np.unique(values, return_counts=True)
    index = int(np.flatnonzero(frequencies == frequencies.max())[0])
    return {"table": dict(zip(labels.tolist(), frequencies.tolist())),
            "ind": index + 1, "majority": str(labels[index])}


def matchCluster(group, cluster):
    """Map cluster labels to group labels by row/column modal agreement."""
    g = np.asarray(group).ravel()
    c = np.asarray(cluster).ravel()
    if g.size != c.size:
        raise ValueError("arguments must be vector of the same length")
    ug, gi = np.unique(g, return_inverse=True)
    uc, ci = np.unique(c, return_inverse=True)
    tab = np.zeros((ug.size, uc.size), dtype=int)
    np.add.at(tab, (gi, ci), 1)
    a_to_b = uc[np.argmax(tab, axis=1)]
    b_to_a = ug[np.argmax(tab, axis=0)]
    mapped = a_to_b[ci]
    return {"cluster": mapped, "misclassified": c != g, "ord": a_to_b}


def randomOrthogonalMatrix(nrow, ncol, n=None, d=None, seed=None):
    """Return the Q factor of a random normal matrix."""
    if nrow is None:
        nrow = n
    if ncol is None:
        ncol = d
    if nrow is None or ncol is None:
        raise ValueError("missing dimensions")
    rng = np.random.default_rng(seed)
    q, r = np.linalg.qr(rng.normal(size=(nrow, ncol)), mode="reduced")
    signs = np.sign(np.diag(r))
    signs[signs == 0] = 1
    return q * signs


def randomPairs(data, seed=None, **kwargs):
    """Generate the initial random pairing tree used by hcRandomPairs."""
    n = np.asarray(data).shape[0]
    m = n - (n % 2)
    rng = np.random.default_rng(seed)
    tree = rng.choice(n, size=m, replace=False).reshape(2, m // 2)
    tree.sort(axis=0)
    ind = np.unique(tree[0])
    while tree.shape[1] < m - 1:
        add = np.sort(rng.choice(ind, size=2, replace=False))
        ind = ind[ind != add[1]]
        tree = np.column_stack((tree, add))
    return tree + 1


def coordProj(*args, **kwargs):
    raise NotImplementedError("coordProj is a plotting function")


def randProj(*args, **kwargs):
    raise NotImplementedError("randProj is a plotting function")
