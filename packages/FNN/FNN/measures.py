"""Entropy, divergence, and mutual information from FNN."""

import math

import numpy as np

from .search import get_knn, get_knnx, knn_dist, knnx_dist, match_arg


def digamma_positive(n):
    """R ``digamma`` on the positive integers ``1 .. n`` is not requested.

    ``digamma(m)`` for an integer ``m >= 1`` is ``-γ + H_{m-1}``.
    """
    m = int(n)
    if m < 1:
        return math.nan
    if m == 1:
        return float(-np.euler_gamma)
    return float(-np.euler_gamma + np.sum(1.0 / np.arange(1, m)))


def _digamma_range(k):
    return np.array([digamma_positive(i) for i in range(1, int(k) + 1)])


def _volume(p):
    return 0.5 * p * math.log(math.pi) - math.lgamma(p / 2.0 + 1.0)


def entropy(X, k=10, algorithm=None):
    algorithm = match_arg(algorithm, ("kd_tree", "brute"))
    data = np.asarray(X, dtype=float)
    if data.ndim == 1:
        data = data.reshape(-1, 1)
    n, p = data.shape
    if k >= n:
        raise ValueError("k must less than the sample size!")
    distances = knn_dist(data, k, algorithm)
    mean_log = np.mean(np.log(distances), axis=0)
    return digamma_positive(n) - _digamma_range(k) + _volume(p) + p * mean_log


def crossentropy(X, Y, k=10, algorithm=None):
    algorithm = match_arg(algorithm, ("kd_tree", "cover_tree", "brute"))
    left = np.asarray(X, dtype=float)
    right = np.asarray(Y, dtype=float)
    if left.ndim == 1:
        left = left.reshape(-1, 1)
    if right.ndim == 1:
        right = right.reshape(-1, 1)
    n, p = left.shape
    m = right.shape[0]
    if k >= n:
        raise ValueError("k must less than the sample size!")
    distances = knnx_dist(right, left, k, algorithm)
    mean_log = np.mean(np.log(distances), axis=0)
    return digamma_positive(m) - _digamma_range(k) + _volume(p) + p * mean_log


def KL_divergence(X, Y, k=10, algorithm=None):
    algorithm = match_arg(algorithm, ("kd_tree", "cover_tree", "brute"))
    left = np.asarray(X, dtype=float)
    right = np.asarray(Y, dtype=float)
    if left.ndim == 1:
        left = left.reshape(-1, 1)
    if right.ndim == 1:
        right = right.reshape(-1, 1)
    n = left.shape[0]
    m = right.shape[0]
    p = left.shape[1]
    far = np.mean(np.log(knnx_dist(right, left, k, algorithm)), axis=0)
    near = np.mean(np.log(knn_dist(left, k, algorithm)), axis=0)
    return math.log(m / n) + p * (far - near)


def KL_dist(X, Y, k=10, algorithm=None):
    return KL_divergence(X, Y, k, algorithm) + KL_divergence(Y, X, k, algorithm)


def KLx_divergence(X, Y, k=10, algorithm="kd_tree"):
    if algorithm != "kd_tree":
        raise ValueError("algorithm must be kd_tree")
    return KL_divergence(X, Y, k, "kd_tree")


def KLx_dist(X, Y, k=10, algorithm="kd_tree"):
    if algorithm != "kd_tree":
        raise ValueError("algorithm must be kd_tree")
    left = np.asarray(X, dtype=float)
    right = np.asarray(Y, dtype=float)
    if left.ndim == 1:
        left = left.reshape(-1, 1)
    if right.ndim == 1:
        right = right.reshape(-1, 1)
    n, d = left.shape
    m = right.shape[0]
    # log of the squared distance, then divide by 2, is log of the Euclidean distance.
    yx = np.sum(np.log(np.square(knnx_dist(left, right, k, "kd_tree"))), axis=0)
    xx = np.sum(np.log(np.square(knn_dist(left, k, "kd_tree"))), axis=0)
    xy = np.sum(np.log(np.square(knnx_dist(right, left, k, "kd_tree"))), axis=0)
    yy = np.sum(np.log(np.square(knn_dist(right, k, "kd_tree"))), axis=0)
    return d * (yx / m + xy / n - xx / n - yy / m) / 2.0


def _chebyshev_neighbors(X, Y, k):
    """Counts from ``mdmutinfo``: max-norm radius, then strict counts."""
    X = np.asarray(X, dtype=float)
    Y = np.asarray(Y, dtype=float)
    if X.ndim == 1:
        X = X.reshape(-1, 1)
    if Y.ndim == 1:
        Y = Y.reshape(-1, 1)
    n = X.shape[0]
    nx = np.zeros(n, dtype=int)
    ny = np.zeros(n, dtype=int)
    room = _room(k)
    for i in range(n):
        kn = k
        nndist = np.full(room, 0.99 * np.finfo(float).max)
        for j in range(n):
            if j == i:
                continue
            dist = 0.0
            for col in range(X.shape[1]):
                dist = max(dist, abs(X[i, col] - X[j, col]))
            for col in range(Y.shape[1]):
                dist = max(dist, abs(Y[i, col] - Y[j, col]))
            if dist <= nndist[k - 1]:
                for slot in range(kn + 1):
                    if dist < nndist[slot]:
                        for move in range(kn, slot, -1):
                            nndist[move] = nndist[move - 1]
                        nndist[slot] = dist
                        if nndist[kn] <= nndist[k - 1]:
                            kn += 1
                            if kn == 1000 - 1:
                                raise ValueError("too many ties in knn")
                        break
            nndist[kn] = 0.99 * np.finfo(float).max
        radius = nndist[k - 1]
        for j in range(n):
            dx = 0.0
            for col in range(X.shape[1]):
                dx = max(dx, abs(X[i, col] - X[j, col]))
            dy = 0.0
            for col in range(Y.shape[1]):
                dy = max(dy, abs(Y[i, col] - Y[j, col]))
            if dx < radius:
                nx[i] += 1
            if dy < radius:
                ny[i] += 1
    return nx, ny


def _room(k):
    return 1000 + int(k)


def mutinfo(X, Y, k=10, direct=True):
    left = np.asarray(X, dtype=float)
    right = np.asarray(Y, dtype=float)
    if left.ndim == 1:
        left = left.reshape(-1, 1)
    if right.ndim == 1:
        right = right.reshape(-1, 1)
    n = left.shape[0]
    if k >= n:
        raise ValueError("k must less than the sample size!")
    if direct:
        nx, ny = _chebyshev_neighbors(left, right, int(k))
        return digamma_positive(n) + digamma_positive(k) - float(np.mean(np.array([digamma_positive(a) + digamma_positive(b) for a, b in zip(nx, ny)])))
    hx = entropy(left, k, "kd_tree")
    hy = entropy(right, k, "kd_tree")
    both = entropy(np.column_stack([left, right]), k, "kd_tree")
    return hx + hy - both
