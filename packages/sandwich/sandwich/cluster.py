"""Clustered covariances, including the multi-way combination of clustering variables."""

from __future__ import annotations

import itertools
import warnings

import numpy as np

from .estfun import estfun, sandwich
from .model import Fit, Formula, SandwichError, match_arg


def combn(items, m: int) -> list[tuple]:
    """Combinations of ``m`` items, in the order of ``utils::combn``."""
    return list(itertools.combinations(list(items), m))


def matrixinverse(x: np.ndarray, tol: float | None = None) -> np.ndarray:
    x = np.asarray(x, dtype=float)
    if x.shape == (1, 1):
        return 1.0 / x
    if tol is None:
        tol = np.finfo(float).eps ** (1 / 1.3)
    try:
        return np.linalg.inv(x)
    except np.linalg.LinAlgError:
        u, d, vt = np.linalg.svd(x, full_matrices=False)
        ok = d > max(tol * d[0], 0)
        return vt.T[:, ok] @ ((1.0 / d[ok])[:, None] * u[:, ok].T)


def matrixpower(x: np.ndarray, power: float, symmetric=None, tol: float | None = None) -> np.ndarray:
    x = np.asarray(x, dtype=float)
    if x.shape == (1, 1):
        return x ** power
    if tol is None:
        tol = np.finfo(float).eps ** (1 / 1.3)
    if symmetric is None:
        symmetric = np.allclose(x, x.T)
    if symmetric:
        values, vectors = np.linalg.eigh(x)
    else:
        values, vectors = np.linalg.eig(x)
    if np.iscomplexobj(values):
        if np.any(np.abs(np.imag(values)) > tol):
            warnings.warn("complex eigen values of X", RuntimeWarning, stacklevel=2)
        values = np.real(values)
        vectors = np.real(vectors)
    values = np.asarray(values, dtype=float)
    values[values < tol] = 0
    if symmetric:
        return vectors @ ((values ** power)[:, None] * vectors.T)
    return vectors @ ((values ** power)[:, None] * matrixinverse(vectors))


def _cluster_frame(x: Fit, cluster, n: int) -> np.ndarray:
    if cluster is None:
        cluster = getattr(x, "cluster", None)
    if cluster is None:
        return np.arange(1, n + 1).reshape(-1, 1)
    if isinstance(cluster, Formula):
        text = cluster.text.split("~", 1)[-1]
        names = [piece.strip() for piece in text.split("+") if piece.strip()]
        columns = [np.asarray(x.data[name])[x.kept] for name in names]
        return np.column_stack(columns)
    array = np.asarray(cluster)
    if array.ndim == 1:
        array = array.reshape(-1, 1)
    if array.shape[0] != n and x.na_action is not None and array.shape[0] == len(x.kept):
        array = array[x.kept]
    if array.shape[0] != n:
        raise SandwichError("number of observations in 'cluster' and 'estfun()' do not match")
    if np.any(pd_na(array)):
        raise SandwichError("cannot handle NAs in 'cluster': either refit the model without the NA observations in 'cluster' or impute the NAs")
    return array


def pd_na(array: np.ndarray) -> np.ndarray:
    if array.dtype == object:
        return np.array([item is None or (isinstance(item, float) and np.isnan(item)) for item in array.ravel()]).reshape(array.shape)
    return ~np.isfinite(array.astype(float)) if np.issubdtype(array.dtype, np.number) else np.zeros(array.shape, dtype=bool)


def _group_count(column) -> int:
    return len(set(column.tolist()))


def _rowsum(values: np.ndarray, groups) -> np.ndarray:
    keys = []
    seen = set()
    for item in groups.tolist():
        if item not in seen:
            seen.add(item)
            keys.append(item)
    try:
        order = sorted(keys, key=lambda item: (0, float(item)))
    except (TypeError, ValueError):
        order = sorted(keys, key=lambda item: str(item))
    index = {key: i for i, key in enumerate(order)}
    out = np.zeros((len(order), values.shape[1]))
    for row, key in enumerate(groups.tolist()):
        out[index[key]] += values[row]
    return out


def meatCL(x: Fit, cluster=None, type=None, cadjust: bool = True, multi0: bool = False, **_kwargs) -> np.ndarray:
    scores = np.asarray(estfun(x), dtype=float)
    k = scores.shape[1]
    n = scores.shape[0]
    groups = _cluster_frame(x, cluster, n)
    p = groups.shape[1]
    if p > 1:
        patterns = []
        for size in range(1, p + 1):
            patterns.extend(combn(range(p), size))
        signs = [(-1) ** (len(pattern) + 1) for pattern in patterns]
        extra = []
        for pattern in patterns[p:]:
            pasted = ["_".join(str(item) for item in row) for row in groups[:, list(pattern)]]
            extra.append(pasted)
        if extra:
            groups = np.column_stack([groups, np.column_stack(extra)])
        if multi0:
            groups[:, -1] = np.arange(1, n + 1)
    else:
        patterns = [(0,)]
        signs = [1]
    counts = [_group_count(groups[:, i]) for i in range(len(patterns))]
    is_lm = x.klass[0] == "lm"
    is_glm = x.klass[0] == "glm"
    if type is None:
        type = "HC1" if is_lm else "HC0"
    type = match_arg(type, ["HC", "HC0", "HC1", "HC2", "HC3"])
    if type == "HC":
        type = "HC0"
    hats = None
    design = None
    xx_inv = None
    weights = None
    residuals = None
    if type in {"HC2", "HC3"}:
        if any(count == n for count in counts):
            hats = x.hatvalues()
        if not all(count == n for count in counts):
            if not (is_lm or is_glm):
                warnings.warn("clustered HC2/HC3 are only applicable to (generalized) linear regression models", RuntimeWarning, stacklevel=2)
            design = x.x
            weights = None if x.klass[0] != "glm" else np.asarray(x.working_weights, dtype=float)
            if x.klass[0] == "lm" and x.prior_weights is not None:
                weights = np.asarray(x.prior_weights, dtype=float)
            gram = design.T @ design if weights is None else (design * np.sqrt(weights)[:, None]).T @ (design * np.sqrt(weights)[:, None])
            xx_inv = np.linalg.inv(gram)
            residuals, _all0 = _residuals(scores, design)
    value = np.zeros((k, k))
    for i, pattern in enumerate(patterns):
        current = scores.copy()
        if multi0 and i == len(patterns) - 1:
            adj = (n - k) / (n - 1) if type == "HC1" else 1.0
        else:
            adj = counts[i] / (counts[i] - 1) if cadjust else 1.0
        if type in {"HC2", "HC3"}:
            if counts[i] == n:
                current = current / np.sqrt(1 - hats)[:, None] if type == "HC2" else current / (1 - x.hatvalues())[:, None]
            else:
                labels = groups[:, i]
                for label in dict.fromkeys(labels.tolist()):
                    rows = np.flatnonzero(labels == label)
                    block = design[rows]
                    middle = block @ xx_inv @ block.T
                    if weights is not None:
                        middle = middle @ np.diag(weights[rows])
                    eye = np.eye(len(rows))
                    transform = matrixpower(eye - middle, -0.5) if type == "HC2" else np.linalg.inv(eye - middle)
                    current[rows] = (transform @ residuals[rows])[:, None] * block
            current = np.sqrt((counts[i] - 1) / counts[i]) * current
        if counts[i] < n:
            current = _rowsum(current, groups[:, i])
        value = value + signs[i] * adj * (current.T @ current) / n
    if type == "HC1":
        value = (n - 1) / (n - k) * value
    return value


def _residuals(scores, design):
    with np.errstate(divide="ignore", invalid="ignore"):
        ratio = scores / design
    residuals = np.nanmean(ratio, axis=1)
    all0 = np.all(np.abs(scores) < np.finfo(float).eps, axis=1)
    residuals[all0] = 0.0
    return residuals, all0


def _fix_psd(value: np.ndarray) -> np.ndarray:
    values, vectors = np.linalg.eigh(value)
    values = np.maximum(values, 0)
    return (vectors * np.sqrt(values)) @ (vectors * np.sqrt(values)).T


def vcovCL(x: Fit, cluster=None, type=None, sandwich_=True, fix: bool = False, **kwargs) -> np.ndarray:
    meat = meatCL(x, cluster=cluster, type=type, **kwargs)
    value = sandwich(x, meat_=meat) if sandwich_ else meat
    if fix:
        values = np.linalg.eigvalsh(value)
        if np.any(values < 0):
            value = _fix_psd(value)
    return value
