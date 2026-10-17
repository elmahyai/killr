"""Panel HAC and panel-corrected covariances."""

from __future__ import annotations

import math

import numpy as np

from .cluster import _fix_psd
from .estfun import estfun, sandwich
from .hac import kweights
from .model import Fit, Formula, SandwichError, match_arg


def _lookup(x: Fit, value, n: int):
    if isinstance(value, Formula):
        names = [piece.strip() for piece in value.text.split("~", 1)[-1].split("+") if piece.strip()]
        columns = [np.asarray(x.data[name])[x.kept] for name in names]
        return columns[0] if len(columns) == 1 else np.column_stack(columns)
    array = np.asarray(value)
    if array.ndim > 1 and array.shape[1] == 1:
        array = array.ravel()
    if np.ndim(array) == 1 and len(array) != n and x.na_action is not None and len(array) == len(x.kept):
        array = array[x.kept]
    return array


def _panel_index(x: Fit, cluster, order_by, n: int):
    if cluster is None:
        cluster = getattr(x, "cluster", None)
    if isinstance(cluster, (list, tuple)) and not isinstance(cluster, Formula) and len(cluster) > 1 and order_by is None:
        order_by = cluster[1]
        cluster = cluster[0]
    if cluster is None and order_by is None:
        cluster = np.ones(n)
    if cluster is None:
        cluster = np.arange(1, n + 1)
    else:
        cluster = _lookup(x, cluster, n)
    if order_by is None:
        order_by = getattr(x, "order_by", None)
    if order_by is None:
        labels = []
        seen: dict = {}
        for item in np.asarray(cluster).tolist():
            seen[item] = seen.get(item, 0) + 1
            labels.append(seen[item])
        order_by = np.array(labels, dtype=int)
    else:
        order_by = np.asarray(_lookup(x, order_by, n)).ravel()
    if len(cluster) != n or len(order_by) != n:
        raise SandwichError("cannot handle NAs in 'cluster' or 'order.by': either refit the model without the NA observations or impute the NAs")
    return np.asarray(cluster), np.asarray(order_by)


def meatPL(x: Fit, cluster=None, order_by=None, kernel="Bartlett", lag="NW1987", bw=None, adjust: bool = True, aggregate: bool = True, **_kwargs) -> np.ndarray:
    scores = np.asarray(estfun(x), dtype=float)
    k = scores.shape[1]
    n = scores.shape[0]
    cluster, order_by = _panel_index(x, cluster, order_by, n)
    order = np.argsort(np.asarray(order_by), kind="mergesort")
    scores = scores[order]
    order_by = np.asarray(order_by)[order]
    cluster = np.asarray(cluster)[order]
    if aggregate:
        times = _unique(order_by)
        nt = len(times)
        if nt < n:
            if nt == 1:
                scores = np.sum(scores, axis=0, keepdims=True)
            else:
                scores = np.column_stack([_tapply_sum(scores[:, i], order_by) for i in range(k)])
        nt = scores.shape[0]
        nc = len(_unique(cluster))
    else:
        order_by = _as_factor_codes(order_by)
        cluster = _as_factor_codes(cluster)
        nt = int(order_by[-1])
        nc = int(cluster[-1])
    if isinstance(lag, str):
        if lag == "P2009":
            lag = "max"
        lag = match_arg(lag, ["max", "NW1987", "NW1994"])
        if lag == "max":
            lag = nt - 1
        elif lag == "NW1987":
            lag = math.floor(nt ** 0.25)
        else:
            lag = math.floor(4 * (nt / 100) ** (2 / 9))
    if lag is None and bw is None:
        lag = nt - 1
    if lag is not None and bw is None:
        bw = lag + 1
    weights = kweights(np.arange(nt) / bw, kernel=kernel)
    weights = weights[: int(np.max(np.flatnonzero(np.abs(weights) > 0))) + 1]
    value = 0.5 * (scores.T @ scores) * weights[0]
    if len(weights) > 1:
        for ii, weight in enumerate(weights[1:], start=2):
            if aggregate:
                piece = scores[: nt - ii + 1].T @ scores[ii - 1 :]
            else:
                ix1 = [f"{t}-{c}" for t in range(1, nt - ii + 2) for c in range(1, nc + 1)]
                ix2 = [f"{t}-{c}" for t in range(ii, nt + 1) for c in range(1, nc + 1)]
                names = [f"{int(order_by[i])}-{int(cluster[i])}" for i in range(len(order_by))]
                position = {name: i for i, name in enumerate(names)}
                left, right = [], []
                for a, b in zip(ix1, ix2):
                    if a in position and b in position:
                        left.append(position[a])
                        right.append(position[b])
                piece = scores[left].T @ scores[right]
            value = value + weight * piece
    value = value + value.T
    if adjust:
        value = n / (n - k) * value
    return value / n


def _unique(values):
    seen = []
    for item in np.asarray(values).tolist():
        if item not in seen:
            seen.append(item)
    return seen


def _as_factor_codes(values) -> np.ndarray:
    levels = _unique(values)
    index = {level: i + 1 for i, level in enumerate(levels)}
    return np.array([index[item] for item in np.asarray(values).tolist()])


def _tapply_sum(values, groups) -> np.ndarray:
    levels = _unique(groups)
    index = {level: i for i, level in enumerate(levels)}
    out = np.zeros(len(levels))
    for value, group in zip(values, np.asarray(groups).tolist()):
        out[index[group]] += value
    return out


def vcovPL(x: Fit, cluster=None, order_by=None, kernel="Bartlett", sandwich_=True, fix: bool = False, **kwargs) -> np.ndarray:
    meat = meatPL(x, cluster=cluster, order_by=order_by, kernel=kernel, **kwargs)
    value = sandwich(x, meat_=meat) if sandwich_ else meat
    if fix and np.any(np.linalg.eigvalsh(value) < 0):
        value = _fix_psd(value)
    return value


def _split_sum_blocks(design, cluster, sigma, count, periods, columns, nobs):
    levels = _unique(cluster)
    grouped = {level: [] for level in levels}
    for row, level in enumerate(np.asarray(cluster).tolist()):
        grouped[level].append(design[row])
    blocks = [np.array(grouped[level]).reshape(periods, columns) for level in levels]
    total = np.zeros((columns, columns))
    for j in range(count):
        for i in range(count):
            total = total + sigma[j, i] * blocks[j].T @ blocks[i] / nobs
    return total


def _meat_pc_unbalanced(design, residuals, cluster, order_by, pairwise: bool, kronecker: bool) -> np.ndarray:
    """Panel-corrected meat when some cluster/time cells are missing."""
    clusters = _unique(cluster)
    times = _unique(order_by)
    cells = {(c, t): i for i, (c, t) in enumerate(zip(np.asarray(cluster).tolist(), np.asarray(order_by).tolist()))}
    # merge(sort=TRUE) orders by cluster, then time.
    try:
        c_order = sorted(clusters, key=lambda item: (0, float(item)))
        t_order = sorted(times, key=lambda item: (0, float(item)))
    except (TypeError, ValueError):
        c_order = sorted(clusters, key=str)
        t_order = sorted(times, key=str)
    grid = [(c, t) for c in c_order for t in t_order]
    full_x = []
    full_res = []
    full_c = []
    for c, t in grid:
        full_c.append(c)
        if (c, t) in cells:
            row = cells[(c, t)]
            full_x.append(design[row])
            full_res.append(residuals[row])
        else:
            full_x.append(np.full(design.shape[1], np.nan))
            full_res.append(np.nan)
    pair_x = np.array(full_x, dtype=float)
    pair_res = np.array(full_res, dtype=float)
    pair_c = np.array(full_c)
    n_obs = design.shape[0]
    if not pairwise:
        present = pair_res[~np.isnan(pair_res)]
        # Drop time points that are missing anywhere, matching the NA sweep in meatPC.
        missing_times = {t for (c, t), value in zip(grid, pair_res) if np.isnan(value)}
        keep_time = np.array([t not in missing_times for _c, t in grid])
        used = pair_res[keep_time]
        used_c = pair_c[keep_time]
        levels = _unique(used_c)
        errors = np.column_stack([used[used_c == level] for level in levels])
        periods, count = errors.shape
        sigma = errors.T @ errors / periods
        tt = len(times)
        pair_filled = np.nan_to_num(pair_x, nan=0.0)
        if kronecker:
            omega = np.kron(sigma, np.eye(tt))
            return pair_filled.T @ omega @ pair_filled / n_obs
        return _split_sum_blocks(pair_filled, pair_c, sigma, count, tt, design.shape[1], n_obs)
    present_rows = ~np.isnan(pair_res)
    indicators = present_rows.astype(float).reshape(len(t_order), len(c_order), order="F")
    # expand.grid varies cluster fastest, then merge sorts by cluster then time,
    # so the grid above is cluster-major. Bailey-Katz fills cluster by time row-wise
    # after that sort. Use the sorted grid directly.
    indicators = present_rows.reshape(len(c_order), len(t_order)).T
    denoma = indicators.T @ indicators
    filled_x = np.nan_to_num(pair_x, nan=0.0)
    errors = np.nan_to_num(pair_res, nan=0.0).reshape(len(c_order), len(t_order)).T
    sigma = (errors.T @ errors) / denoma
    if kronecker:
        omega = np.kron(sigma, np.eye(errors.shape[0]))
        return filled_x.T @ omega @ filled_x / n_obs
    return _split_sum_blocks(filled_x, pair_c, sigma, len(c_order), len(t_order), design.shape[1], n_obs)


def meatPC(x: Fit, cluster=None, order_by=None, pairwise: bool = False, kronecker: bool = True, **_kwargs) -> np.ndarray:
    scores = np.asarray(estfun(x), dtype=float)
    n = scores.shape[0]
    cluster, order_by = _panel_index(x, cluster, order_by, n)
    design = x.x
    with np.errstate(divide="ignore", invalid="ignore"):
        residuals = np.nanmean(scores / design, axis=1)
    residuals[np.all(np.abs(scores) < np.finfo(float).eps, axis=1)] = 0.0
    table = {}
    for item_c, item_t in zip(np.asarray(cluster).tolist(), np.asarray(order_by).tolist()):
        table[(item_c, item_t)] = table.get((item_c, item_t), 0) + 1
    counts = [table.get((c, t), 0) for c in _unique(cluster) for t in _unique(order_by)]
    balanced = len(set(counts)) == 1 and counts[0] > 0
    if balanced and not pairwise:
        levels = _unique(cluster)
        buckets = {level: [] for level in levels}
        for residual, level in zip(residuals, np.asarray(cluster).tolist()):
            buckets[level].append(residual)
        errors = np.column_stack([buckets[level] for level in levels])
        periods, count = errors.shape
        sigma = errors.T @ errors / periods
        total = periods * count
        if kronecker:
            omega = np.kron(sigma, np.eye(periods))
            return design.T @ omega @ design / total
        return _split_sum_blocks(design, cluster, sigma, count, periods, design.shape[1], total)
    return _meat_pc_unbalanced(design, residuals, cluster, order_by, pairwise, kronecker)


def vcovPC(x: Fit, cluster=None, order_by=None, pairwise: bool = False, sandwich_=True, fix: bool = False, **kwargs) -> np.ndarray:
    meat = meatPC(x, cluster=cluster, order_by=order_by, pairwise=pairwise, **kwargs)
    value = sandwich(x, meat_=meat) if sandwich_ else meat
    if fix and np.any(np.linalg.eigvalsh(value) < 0):
        value = _fix_psd(value)
    return value
