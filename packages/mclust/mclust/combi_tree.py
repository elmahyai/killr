"""Dendrogram of the cluster-combination hierarchy (``combiTree``)."""

from __future__ import annotations

from typing import Any, Mapping

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from scipy.cluster.hierarchy import dendrogram

__all__ = ["combiTree"]


def combiTree(
    object: Any,
    type: str = "triangle",
    yaxis: str = "entropy",
    edgePar: Mapping[str, Any] | None = None,
    **kwargs,
):
    """Plot the combination tree for a ``clustCombi`` object."""
    if not _is_clust_combi(object):
        raise ValueError("object not of class 'clustCombi'")
    yaxis = _match_arg(yaxis, ("entropy", "step"))
    type = _match_arg(type, ("triangle", "rectangle"))

    g = int(_field(object, "MclustOutput")["G"])
    combi_m = _field(object, "combiM")

    curr = np.arange(1, g + 1, dtype=int)
    merged = -np.arange(1, g + 1, dtype=int)
    merge = np.full((g - 1, 2), np.nan, dtype=float)
    for k in range(1, g):
        kp = g - k + 1
        m = combi_m[kp - 1]
        ones = np.ones(kp, dtype=float)
        row_sums = m @ ones
        l1_idx = np.flatnonzero(row_sums != 1.0)
        if l1_idx.size != 1:
            raise ValueError("expected exactly one non-unit row sum in combination matrix")
        l1 = int(l1_idx[0]) + 1
        l2 = int((m @ curr)[l1 - 1] - curr[l1 - 1])
        drop = max(l1, l2)
        curr = curr[curr != drop]
        merge[k - 1, 0] = merged[l1 - 1]
        merge[k - 1, 1] = merged[l2 - 1]
        step = k
        mask = (merged == merged[l1 - 1]) | (merged == merged[l2 - 1])
        merged[mask] = step

    def _sel(x: int) -> list[int]:
        if x < 0:
            return [abs(x)]
        row = int(x) - 1
        return _sel(int(merge[row, 0])) + _sel(int(merge[row, 1]))

    ord_leaves = np.abs(
        np.array(_sel(int(merge[g - 2, 0])) + _sel(int(merge[g - 2, 1])), dtype=int)
    )

    if yaxis == "step":
        h = np.arange(1, g, dtype=float)
        ylab = "Steps"
    else:
        combiz = _field(object, "combiz")
        ks = sorted(combiz.keys(), reverse=True)
        entropy = np.array([-_sum_xlog(np.asarray(combiz[k], dtype=float)) for k in ks])
        h = entropy.copy()
        h = 1.0 - (h - h.min()) / (h.max() - h.min())
        h = h[1:]
        ylab = "1 - normalised entropy"

    hc = {
        "merge": merge,
        "height": h,
        "order": ord_leaves,
        "labels": list(range(1, g + 1)),
    }
    linkage = _hclust_to_linkage(hc)
    edge_par = dict(edgePar or {"col": "darkgray", "lwd": 2})
    color = edge_par.get("col", "darkgray")
    lw = edge_par.get("lwd", 2)
    fig, ax = plt.subplots()
    dendrogram(
        linkage,
        labels=hc["labels"],
        orientation="top",
        above_threshold_color=color,
        color_threshold=0 if type == "triangle" else -1,
        ax=ax,
    )
    for line in ax.lines:
        line.set_color(color)
        line.set_linewidth(lw)
    ax.set_ylabel(ylab)
    plt.close(fig)
    return hc


def _hclust_to_linkage(hc: Mapping[str, Any]) -> np.ndarray:
    merge = np.asarray(hc["merge"], dtype=float)
    height = np.asarray(hc["height"], dtype=float)
    n = merge.shape[0] + 1
    z = np.zeros((n - 1, 4), dtype=float)
    for i in range(n - 1):
        left = merge[i, 0]
        right = merge[i, 1]
        if left < 0:
            left = -left - 1
        else:
            left = n + int(left) - 1
        if right < 0:
            right = -right - 1
        else:
            right = n + int(right) - 1
        z[i, 0] = left
        z[i, 1] = right
        z[i, 2] = height[i]
        z[i, 3] = 1.0
    return z


def _sum_xlog(x: np.ndarray) -> float:
    flat = np.asarray(x, dtype=float).ravel()
    return float(np.sum(np.where(flat == 0.0, 0.0, flat * np.log(flat))))


def _match_arg(value: str, choices: tuple[str, ...]) -> str:
    if value not in choices:
        raise ValueError(f"'{value}' is not a valid choice")
    return value


def _is_clust_combi(obj: Any) -> bool:
    if isinstance(obj, Mapping):
        return "combiM" in obj and "MclustOutput" in obj and "combiz" in obj
    return hasattr(obj, "combiM") and hasattr(obj, "MclustOutput")


def _field(obj: Any, name: str):
    if isinstance(obj, Mapping):
        return obj[name]
    return getattr(obj, name)
