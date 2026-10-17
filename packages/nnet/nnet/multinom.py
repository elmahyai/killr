"""Multinomial log-linear models via a skip-layer network."""

from __future__ import annotations

import numpy as np

from nnet.design import _factor_of, model_parts, qr_rank
from nnet.engine import summ2
from nnet.fit import _indicators, _warn_empty, nnet_default


def _as_factor_response(parts):
    if parts["y_kind"] == "matrix":
        y = np.asarray(parts["y"], dtype=np.float64)
        return y, None, True
    if parts["y_kind"] == "factor":
        levels = list(parts["levels"])
        labels = list(parts["y"])
    else:
        factor = _factor_of(np.asarray(parts["y"]).reshape(-1))
        levels = list(factor.levels)
        labels = list(factor.values)
    counts = [labels.count(level) for level in levels]
    empty = [level for level, count in zip(levels, counts) if count == 0]
    if empty:
        _warn_empty(empty)
        levels = [level for level, count in zip(levels, counts) if count > 0]
    if len(levels) < 2:
        raise ValueError("need two or more classes to fit a multinom model")
    if len(levels) == 2:
        index = {level: position for position, level in enumerate(levels)}
        y = np.array([index[label] for label in labels], dtype=np.float64)
        return y, levels, False
    return _indicators(labels, levels), levels, True


def _summ1(x, y, w):
    y_mat = y.reshape(-1, 1) if np.asarray(y).ndim == 1 else np.asarray(y, dtype=np.float64)
    z = np.column_stack([np.asarray(x, dtype=np.float64), y_mat])
    scale = np.cumprod(z.max(axis=0) + 1.0)
    hashed = z @ scale
    order = np.argsort(hashed, kind="mergesort")
    ordered = hashed[order]
    first = np.ones(order.shape[0], dtype=bool)
    first[1:] = ordered[1:] != ordered[:-1]
    chosen = order[first]
    x = np.asarray(x, dtype=np.float64)[chosen]
    if np.asarray(y).ndim == 1:
        y = np.asarray(y, dtype=np.float64)[chosen]
    else:
        y = np.asarray(y, dtype=np.float64)[chosen]
    cumulative = np.concatenate([[0.0], np.cumsum(np.asarray(w, dtype=np.float64))])
    flag = np.concatenate([first, [True]])
    w = np.diff(cumulative[flag])
    return x, y, w


def _print_dim(x):
    print(f"[1] {x.shape[0]} {x.shape[1]}")


def multinom(
    formula,
    data,
    weights=None,
    subset=None,
    na_action="na.omit",
    contrasts=None,
    Hess=False,
    summ=0,
    censored=False,
    model=False,
    **kwargs,
):
    """Multinomial or binomial log-linear model. size is zero and links are skipped."""
    if Hess:
        raise NotImplementedError("multinomHess is not part of this translation")
    parts = model_parts(formula, data, weights=weights, subset=subset, na_action=na_action)
    x = np.asarray(parts["x"], dtype=np.float64)
    names = list(parts["names"])
    rank = qr_rank(x)
    y, levels, is_matrix = _as_factor_response(parts)
    w = np.asarray(parts["weights"], dtype=np.float64).reshape(-1)
    summ = int(summ)
    if summ == 1:
        x, y, w = _summ1(x, y, w)
        is_matrix = np.asarray(y).ndim == 2
        _print_dim(x)
    elif summ == 2:
        y_mat = y.reshape(-1, 1) if np.asarray(y).ndim == 1 else np.asarray(y, dtype=np.float64)
        grouped, summed = summ2(np.column_stack([x, y_mat]), w)
        p = x.shape[1]
        q = y_mat.shape[1]
        x = grouped[:, :p]
        y = grouped[:, p : p + q]
        w = summed.reshape(-1)
        is_matrix = True
        _print_dim(x)
    elif summ == 3:
        y_mat = y.reshape(-1, 1) if np.asarray(y).ndim == 1 else np.asarray(y, dtype=np.float64)
        grouped, summed = summ2(x, y_mat * w.reshape(-1, 1))
        x = grouped
        y = summed[:, : y_mat.shape[1]]
        w = np.ones(x.shape[0], dtype=np.float64)
        is_matrix = True
        _print_dim(x)
    offset = parts["offset"]
    r = x.shape[1]
    censored = bool(censored)
    if is_matrix:
        y = np.asarray(y, dtype=np.float64)
        p = y.shape[1]
        row_sum = y.sum(axis=1)
        if np.any(row_sum == 0):
            raise ValueError("some case has no observations")
        if not censored:
            y = y / row_sum.reshape(-1, 1)
            w = w * row_sum
        offset_cols = 0
        if offset is not None and np.size(offset) > 1:
            offset = np.asarray(offset, dtype=np.float64)
            if offset.ndim == 1:
                offset = offset.reshape(-1, 1)
            if offset.shape[1] != p:
                raise ValueError("ncol(offset) is wrong")
            mask = [0] * (r + 1 + p)
            pattern = [0] + [1] * r + [0] * p
            for _ in range(p - 1):
                mask.extend(pattern)
            x = np.column_stack([x, offset])
            names = names + [f"offset.{i + 1}" for i in range(p)]
            initial = np.zeros((r + 1 + p, p), dtype=np.float64)
            initial[r + 1 :, :] = np.eye(p)
            wts = initial.ravel(order="F")
            fit = nnet_default(
                x,
                y,
                w,
                Wts=wts,
                mask=mask,
                size=0,
                skip=True,
                softmax=True,
                censored=censored,
                rang=0,
                **kwargs,
            )
            offset_cols = p
        else:
            mask = [0] * (r + 1)
            pattern = [0] + [1] * r
            for _ in range(p - 1):
                mask.extend(pattern)
            fit = nnet_default(
                x,
                y,
                w,
                mask=mask,
                size=0,
                skip=True,
                softmax=True,
                censored=censored,
                rang=0,
                **kwargs,
            )
        if y.shape[1] > 0:
            fit["lab"] = levels if levels else list(range(1, y.shape[1] + 1))
        edf = (p - 1) * rank
    else:
        y = np.asarray(y, dtype=np.float64).reshape(-1)
        if offset is None or np.size(offset) <= 1:
            mask = [0] + [1] * r
            fit = nnet_default(
                x,
                y,
                w,
                mask=mask,
                size=0,
                skip=True,
                entropy=True,
                rang=0,
                **kwargs,
            )
        else:
            mask = [0] + [1] * r + [0]
            initial = [0.0] * (r + 1) + [1.0]
            offset = np.asarray(offset, dtype=np.float64).reshape(-1)
            x = np.column_stack([x, offset])
            names = names + ["offset"]
            fit = nnet_default(
                x,
                y,
                w,
                Wts=initial,
                mask=mask,
                size=0,
                skip=True,
                entropy=True,
                rang=0,
                **kwargs,
            )
        edf = rank
    fit["weights"] = np.asarray(w, dtype=np.float64)
    fit["lev"] = levels
    fit["deviance"] = 2 * fit["value"]
    fit["rank"] = int(rank)
    fit["coefnames"] = names
    fit["vcoefnames"] = names[:r]
    fit["contrasts"] = contrasts
    fit["edf"] = float(edf)
    fit["AIC"] = fit["deviance"] + 2 * edf
    if model:
        fit["model"] = data
    fit["class"] = ["multinom", "nnet"]
    return fit
