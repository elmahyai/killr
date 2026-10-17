"""Small mclust utilities used by cvMclustDA (unmap, folds, Brier, softmax)."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Sequence

import numpy as np

__all__ = [
    "unmap",
    "brier_score",
    "logsumexp_rows",
    "softmax_rows",
    "balanced_folds",
    "n_mclust_params",
    "mclust_bic",
    "as_factor",
    "factor_levels",
]


def _boot_unif():
    try:
        from boot.rng import unif
    except ImportError:
        sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "boot"))
        from boot.rng import unif
    return unif


def _boot_sample(x, size, replace=False):
    try:
        from boot.rng import sample_int
    except ImportError:
        sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "boot"))
        from boot.rng import sample_int
    n = len(x)
    idx = sample_int(n, size, replace=replace)
    return [x[i - 1] for i in idx]


def as_factor(values: Any) -> tuple[np.ndarray, list[str]]:
    arr = np.asarray(values, dtype=object)
    levels: list[str] = []
    for item in arr:
        text = str(item)
        if text not in levels:
            levels.append(text)
    codes = np.array([levels.index(str(v)) for v in arr], dtype=int)
    return codes, levels


def factor_levels(class_values: Any, levels: Sequence[str]) -> list[str]:
    return list(levels)


def unmap(
    classification: np.ndarray,
    groups: Sequence[str] | None = None,
    *,
    class_levels: Sequence[str] | None = None,
) -> np.ndarray:
    """R ``unmap`` with ``as.numeric(factor)`` class codes (1..K)."""
    classification = np.asarray(classification)
    if class_levels is None:
        if groups is not None:
            class_levels = list(groups)
        else:
            _, class_levels = as_factor(classification)
    class_levels = list(class_levels)
    level_to_code = {lev: i + 1 for i, lev in enumerate(class_levels)}
    if classification.dtype.kind in ("i", "u", "f") and np.all(classification >= 1):
        class_num = classification.astype(int)
    else:
        class_num = np.array([level_to_code[str(v)] for v in classification], dtype=int)
    k = len(class_levels)
    z = np.zeros((len(classification), k), dtype=float)
    for j in range(k):
        z[class_num == j + 1, j] = 1.0
    return z


def brier_score(z: np.ndarray, class_values: Any, levels: Sequence[str]) -> float:
    z = np.asarray(z, dtype=float)
    row_sums = z.sum(axis=1, keepdims=True)
    z = z / row_sums
    cl = unmap(np.asarray(class_values), groups=levels)
    if cl.shape != z.shape:
        raise ValueError("input arguments do not match!")
    return float(np.sum((cl - z) ** 2) / (2 * cl.shape[0]))


def logsumexp_rows(x: np.ndarray, v: np.ndarray | None = None) -> np.ndarray:
    x = np.atleast_2d(np.asarray(x, dtype=float))
    n, k = x.shape
    if v is None:
        v = np.zeros(k, dtype=float)
    else:
        v = np.asarray(v, dtype=float).ravel()
    out = np.empty(n, dtype=float)
    for i in range(n):
        xv = x[i, :] + v
        m = np.max(xv)
        out[i] = m + np.log(np.sum(np.exp(xv - m)))
    return out


def softmax_rows(x: np.ndarray, v: np.ndarray | None = None) -> np.ndarray:
    x = np.atleast_2d(np.asarray(x, dtype=float))
    lse = logsumexp_rows(x, v)
    if v is None:
        v = np.zeros(x.shape[1], dtype=float)
    else:
        v = np.asarray(v, dtype=float).ravel()
    z = np.exp(x + v - lse[:, None])
    return z


def permute_rows(x: np.ndarray) -> np.ndarray:
    x = np.asarray(x, dtype=float)
    n, p = x.shape
    unif = _boot_unif()
    mm = np.array([unif() for _ in range(n * p)], dtype=float) + np.repeat(
        np.arange(1, n + 1) * 10.0, p
    )
    tx = x.T.ravel(order="F")
    order = np.argsort(mm, kind="mergesort")
    return tx[order].reshape(n, p, order="C")


def balanced_folds(y: np.ndarray, nfolds: int | None = None) -> list[np.ndarray]:
    y = np.asarray(y, dtype=object)
    codes, _levels = as_factor(y)
    totals = np.array([np.sum(codes == i) for i in range(len(set(codes)))], dtype=int)
    fmax = int(totals.max())
    if nfolds is None:
        nfolds = min(int(totals.min()), 10)
    nfolds = min(nfolds, fmax)
    yids: dict[int, list[int]] = {}
    for idx, code in enumerate(codes):
        yids.setdefault(int(code), []).append(idx + 1)
    big_nrows = int(np.ceil(fmax / nfolds) * nfolds)
    nclass = len(totals)
    bigmat = np.full((big_nrows, nclass), np.nan, dtype=float)
    for i, tot in enumerate(totals):
        ids = yids[i]
        if tot == 1:
            bigmat[0, i] = float(ids[0])
        else:
            shuffled = _boot_sample(ids, len(ids), replace=False)
            bigmat[:tot, i] = np.asarray(shuffled, dtype=float)
    vec = bigmat.flatten(order="F")
    smallmat = vec.reshape(nfolds, -1, order="F")
    smallmat = permute_rows(smallmat.T)
    res: list[np.ndarray] = []
    for j in range(nfolds):
        col = smallmat[:, j]
        jj = ~np.isnan(col)
        res.append(col[jj].astype(int))
    return res


def n_var_params(model_name: str, d: int, g: int) -> int:
    name = {"X": "E", "XII": "EII", "XXI": "EEI", "XXX": "EEE"}.get(model_name, model_name)
    table = {
        "E": 1,
        "V": g,
        "EII": 1,
        "VII": g,
        "EEI": d,
        "VEI": g + (d - 1),
        "EVI": 1 + g * (d - 1),
        "VVI": g * d,
        "EEE": d * (d + 1) // 2,
        "EVE": 1 + g * (d - 1) + d * (d - 1) // 2,
        "VEE": g + (d - 1) + d * (d - 1) // 2,
        "VVE": g + g * (d - 1) + d * (d - 1) // 2,
        "EEV": 1 + (d - 1) + g * d * (d - 1) // 2,
        "VEV": g + (d - 1) + g * d * (d - 1) // 2,
        "EVV": 1 - g + g * d * (d + 1) // 2,
        "VVV": g * d * (d + 1) // 2,
    }
    if name not in table:
        raise ValueError("invalid model name")
    return table[name]


def n_mclust_params(
    model_name: str, d: int, g: int, *, noise: bool = False, equal_pro: bool = False
) -> int:
    name = {"X": "E", "XII": "EII", "XXI": "EEI", "XXX": "EEE"}.get(model_name, model_name)
    if g == 0:
        if not noise:
            raise ValueError("undefined model")
        return 1
    nparams = n_var_params(name, d, g) + g * d
    if not equal_pro:
        nparams += g - 1
    if noise:
        nparams += 2
    return nparams


def mclust_bic(
    model_name: str, loglik: float, n: int, d: int, g: int, *, equal_pro: bool = False
) -> float:
    nparams = n_mclust_params(model_name, d, g, equal_pro=equal_pro)
    return 2.0 * loglik - nparams * np.log(n)
