"""Conversion of an mclust ``hc`` result to an hclust-shaped mapping."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import numpy as np


def _field(obj: Any, name: str, default: Any = None) -> Any:
    if isinstance(obj, Mapping):
        return obj.get(name, default)
    return getattr(obj, name, default)


def _merge_order(pairs: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Reproduce mclust's mergeOrder() for a two-column hc merge matrix."""
    hc = np.asarray(pairs, dtype=float)
    if hc.shape[0] == 2 and hc.shape[1] != 2:
        hc = hc.T
    hc = hc.reshape(-1, 2)
    converted = np.empty_like(hc)
    merged: list[list[int]] = [hc[0].astype(int).tolist()]
    converted[0] = -hc[0]
    for i in range(1, len(hc)):
        row = hc[i].astype(int)
        hits = [j for j, group in enumerate(merged) if any(v in group for v in row)]
        if not hits:
            merged.append(row.tolist())
            converted[i] = np.sort(-row)
        elif len(hits) == 1:
            j = hits[0]
            old = merged[j]
            other = row[[v not in old for v in row]].tolist()
            merged.append(old + other)
            merged[j] = []
            converted[i] = np.sort(np.asarray([-v for v in other] + [j + 1]))
        else:
            merged.append([v for j in hits for v in merged[j]])
            for j in hits:
                merged[j] = []
            converted[i] = np.asarray(hits, dtype=float) + 1
    return converted.astype(int), np.asarray(merged[-1], dtype=int)


def _ldend_height(cloglik: Any, maxG: int | None = None) -> np.ndarray:
    """``ldend`` trimming and heights (mbahc.R) for a classification log-likelihood.

    ``cloglik`` is ``cloglik.hc``: one value per level, with missing values
    (NaN) past the last level that can be fitted. Levels past the cut are set to
    the value at the cut, so their heights are 0. The cut is the first
    decrease (among the non-missing differences), else the first missing value,
    else ``maxG``. Heights run from the top level down, as R's ``rev`` does.
    """
    cll = np.asarray(cloglik, dtype=float).reshape(-1)
    n_levels = cll.size
    max_g = n_levels if maxG is None else min(int(maxG), n_levels)
    trimmed = cll.copy()
    diffs = np.diff(cll)
    diffs = diffs[~np.isnan(diffs)]
    neg = diffs < 0
    if neg.any():
        m = int(np.flatnonzero(neg)[0]) + 1  # which(neg)[1], 1-based
        k = min(max_g, m)
    elif np.isnan(cll).any():
        m = int(np.flatnonzero(np.isnan(cll))[0])  # which(na)[1] - 1
        k = min(max_g, m)
    else:
        k = max_g
    if k < 1:
        raise ValueError("no level before the first missing value")
    if neg.any() or np.isnan(cll).any():
        fill = trimmed[k - 1]  # CLL[min(maxG, m)]
    else:
        fill = np.max(trimmed[:max_g])  # max(CLL[1:maxG])
    trimmed[k:] = fill  # CLL[-(1:k)] <- CLLmax
    height = trimmed[:-1]
    if height.size == 0:
        return height
    return (-height + np.max(height))[::-1]


def as_hclust_hc(
    x: Any,
    what: str = "loglik",
    maxG: int | None = None,
    labels: bool = False,
    **_: Any,
) -> dict[str, Any]:
    """Convert an ``hc`` object to the fields returned by ``hclust``.

    ``x`` may be the two-column merge array or a mapping containing ``pairs``
    (or ``merge``) and mclust's ``hc`` attributes.
    """
    pairs = _field(x, "pairs", _field(x, "merge", x))
    pairs = np.asarray(pairs, dtype=float)
    if pairs.ndim == 2 and pairs.shape[0] == 2 and pairs.shape[1] != 2:
        pairs = pairs.T
    if pairs.ndim != 2 or pairs.shape[1] != 2:
        raise ValueError("x must contain a two-column hc merge matrix")
    if maxG is not None and maxG < 2:
        raise ValueError("maxG < 2")
    n = pairs.shape[0] + 1
    max_g = n if maxG is None else min(int(maxG), n)
    merge, order = _merge_order(pairs)
    data = _field(x, "data")
    if labels:
        if data is not None and getattr(data, "index", None) is not None:
            leaf_labels = [str(v) for v in data.index]
        else:
            leaf_labels = [str(i) for i in range(1, n + 1)]
    else:
        leaf_labels = [""] * n
    method = _field(x, "model", _field(x, "modelName"))
    result: dict[str, Any] = {
        "merge": merge,
        "order": order,
        "labels": leaf_labels,
        "method": method,
        "call": _field(x, "call"),
        "dist.method": None,
    }
    if str(what).lower() == "merge":
        result["height"] = np.r_[np.zeros(max(0, n - max_g)), np.arange(1, max_g)]
        result["nclus"] = np.arange(max_g, 0, -1)
    elif str(what).lower() == "loglik":
        cloglik = _field(x, "cloglik", _field(x, "loglik"))
        if cloglik is None:
            raise ValueError("hc object has no cloglik values")
        cloglik = np.asarray(cloglik, dtype=float).reshape(-1)
        result["height"] = _ldend_height(cloglik, maxG)
        result["cloglik"] = cloglik
    else:
        raise ValueError("unrecognized what option")
    return result


__all__ = ["as_hclust_hc"]
