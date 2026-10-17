"""Translation of ``plot.hc`` (mclust 6.1.3).

``plot.hc`` takes an ``hc`` object. It converts it with ``as.hclust`` (what =
"loglik" or "merge"), builds the dendrogram with ``as.dendrogram`` (base
``stats``), draws the rectangle-type dendrogram, then resets the y limits and
sets the y axis ticks.

The helpers below are the parts of ``stats`` and ``mclust`` that ``plot.hc``
needs and that no translated module covers: ``cloglik.hc`` (the classification
log-likelihood of each level of the merge tree), ``ldend``/``mdend`` (the
hclust-shaped result), ``as.dendrogram.hclust``, and the rectangle layout of
``plotNode``/``plotNodeLimit``. The merge order comes from the translated
``as.hclust`` module; ``hclass`` and ``mvn`` come from their own modules.

Matplotlib draws the segments. The logged numbers are the data: the window,
each dendrogram segment in R's order, and the axis ticks.
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from typing import Any

import numpy as np

from ._plot_common import Canvas, pretty
from .as_hclust import _merge_order
from .hclass import hclass
from .mvn import mvn

__all__ = ["HcPairs", "as_hclust_loglik", "as_hclust_merge", "cloglik_hc",
           "as_dendrogram", "plot_hc"]


class HcPairs(np.ndarray):
    """A two-row merge matrix that carries ``initialPartition``, as the R attribute does."""

    initialPartition: Any = None


def _get(x: Any, name: str, default: Any = None) -> Any:
    if isinstance(x, Mapping):
        return x.get(name, default)
    return getattr(x, name, default)


def _pairs(x: Any) -> np.ndarray:
    """The hc merge matrix as two rows and one column per merge, as R stores it."""
    p = np.asarray(_get(x, "pairs", _get(x, "merge", x)), dtype=float)
    if p.ndim != 2:
        raise ValueError("x must contain a two-row hc merge matrix")
    if p.shape[0] != 2 and p.shape[1] == 2:
        p = p.T
    if p.shape[0] != 2:
        raise ValueError("x must contain a two-row hc merge matrix")
    return p


def _initial(x: Any, n_merge: int) -> np.ndarray:
    init = _get(x, "initialPartition")
    if init is None:
        return np.arange(1, n_merge + 2, dtype=int)
    return np.asarray(init, dtype=int).reshape(-1)


def _data(x: Any) -> np.ndarray:
    d = np.asarray(_get(x, "data"), dtype=float)
    return d.reshape(-1, 1) if d.ndim == 1 else d


def _model(x: Any) -> str:
    name = _get(x, "modelName")
    if name is None:
        name = _get(x, "model")
    return str(name)


def _mvn_loglik(model: str, x: np.ndarray) -> float:
    """Return ``mvn(model, x)$loglik`` as a float."""
    value = mvn(model, x).get("loglik")
    if value is None:
        return float("nan")
    return float(value)


def _unique_in_order(values: np.ndarray) -> list[Any]:
    seen: list[Any] = []
    for v in values.tolist():
        if v not in seen:
            seen.append(v)
    return seen


def cloglik_hc(x: Any) -> np.ndarray:
    """``cloglik.hc``: the classification log-likelihood at each level of the tree.

    Level ``j`` uses the partition with ``j`` clusters. Each cluster contributes
    its best log-likelihood over the models of the hc model's family. The first
    level with a missing value ends the sum; later levels are missing.
    """
    pairs = _pairs(x)
    n_merge = pairs.shape[1]
    n = n_merge + 1
    initial = _initial(x, n_merge)
    data = _data(x)
    model = _model(x)

    hcp = np.array(pairs, dtype=float).view(HcPairs)
    hcp.initialPartition = initial
    cl = np.asarray(hclass(hcp), dtype=float)
    cl = np.column_stack([np.ones(cl.shape[0]), cl])  # cbind(`1` = 1, cl)

    ll_levels: list[list[float] | None] = [None] * n
    for j in range(n):
        ll: list[float] = []
        llnew = float("nan")
        col = cl[:, j]
        for k in _unique_in_order(col):
            i = np.flatnonzero(col == k)
            llnew = _mvn_loglik(model, data[i, :])
            if model[1:2] != "I":
                llvii = _mvn_loglik("VII", data[i, :])
                if model[2:3] != "I":
                    llvvi = _mvn_loglik("VVI", data[i, :])
                    candidates = [llnew, llvvi, llvii]
                else:
                    candidates = [llnew, llvii]
                valid = [v for v in candidates if not math.isnan(v)]
                if valid:
                    llnew = valid[int(np.argmax(valid))]
            if math.isnan(llnew):
                break
            ll.append(llnew)
        if math.isnan(llnew):
            break
        ll_levels[j] = ll

    return np.array([math.nan if lv is None else float(np.sum(lv)) for lv in ll_levels])


def as_hclust_merge(x: Any, maxG: int | None = None, labels: bool = False) -> dict[str, Any]:
    """``as.hclust(x, what = "merge")``: ``mdend`` for an hc object."""
    pairs = _pairs(x)
    n_merge = pairs.shape[1]
    ni = int(np.unique(_initial(x, n_merge)).size)
    max_g = ni if maxG is None else min(int(maxG), ni)
    merge, order = _merge_order(pairs.T)
    j = ni - max_g
    height = np.concatenate([np.zeros(j), np.arange(1, n_merge - j + 1, dtype=float)])
    nclus = np.arange(max_g, 0, -1)
    return {"merge": merge, "order": order, "height": height, "nclus": nclus,
            "method": _model(x)}


def as_hclust_loglik(x: Any, maxG: int | None = None, labels: bool = False) -> dict[str, Any]:
    """``as.hclust(x, what = "loglik")``: ``ldend`` for an hc object.

    The result carries ``cloglik``, the raw classification log-likelihood by
    level, before it is trimmed to the heights.
    """
    cll = cloglik_hc(x)
    if maxG is not None and maxG < 2:
        raise ValueError("maxG < 2")
    cloglik = cll.copy()
    max_g = len(cll) if maxG is None else min(int(maxG), len(cll))
    cur = cll.copy()
    na = np.isnan(cur)
    d = np.diff(cur)
    dd = d[~np.isnan(d)]
    neg = dd < 0
    # The three branches of ldend. Indices follow R (1-based) through k and m.
    if neg.any():
        m = int(np.flatnonzero(neg)[0]) + 1  # which(neg)[1]
        k = min(max_g, m)
    elif na.any():
        m = int(np.flatnonzero(na)[0])  # which(na)[1] - 1
        k = min(max_g, m)
    else:
        m = None
        k = max_g
    if k < 1:
        raise ValueError("no level before the first missing value")
    if m is None:
        cur[k:] = np.max(cur[:max_g])
    else:
        cur[k:] = cur[k - 1]
    height = cur[:-1]
    height = (-height + np.max(height))[::-1]
    merge, order = _merge_order(_pairs(x).T)
    return {"merge": merge, "order": order, "height": height,
            "cloglik": cloglik, "method": _model(x)}


class _Node:
    """One node of the dendrogram: a leaf, or a list of two or more children."""

    __slots__ = ("leaf", "height", "members", "midpoint", "children")

    def __init__(self, leaf: bool, height: float | None, members: int,
                 midpoint: float | None, children: list["_Node"]) -> None:
        self.leaf = leaf
        self.height = height
        self.members = members
        self.midpoint = midpoint
        self.children = children


def _mid(node: _Node) -> float:
    """``.midDend``: the midpoint attribute, or 0 when it is missing."""
    return 0.0 if node.midpoint is None else node.midpoint


def _validity(hc: dict[str, Any], merge: np.ndarray) -> None:
    """``.validity.hclust`` (the checks ``as.dendrogram`` runs by default)."""
    n1 = merge.shape[0]
    n = n1 + 1
    if len(hc["height"]) != n1:
        raise ValueError("'height' is of wrong length")
    # R: identical(sort(as.integer(merge)), c(-(n:1L), +seq_len(n - 2L)))
    expected = sorted([-v for v in range(1, n + 1)] + list(range(1, n - 1)))
    if sorted(int(v) for v in merge.ravel()) != expected:
        raise ValueError("'merge' matrix has invalid contents")


def as_dendrogram(hc: dict[str, Any], hang: float = -1) -> _Node:
    """``as.dendrogram.hclust``: the nested node structure with members and midpoints."""
    merge = np.asarray(hc["merge"], dtype=int)
    o_hgt = np.asarray(hc["height"], dtype=float)
    _validity(hc, merge)
    n_merge = len(o_hgt)
    h_max = o_hgt[n_merge - 1]
    z: dict[int, _Node] = {}
    node: _Node | None = None
    for k in range(1, n_merge + 1):
        x = merge[k - 1]
        neg = x < 0
        h0 = 0.0
        if neg.any():
            h0 = 0.0 if hang < 0 else max(0.0, o_hgt[k - 1] - hang * h_max)
        if neg.all():
            leaves = [_Node(True, h0, 1, None, []) for _ in range(2)]
            node = _Node(False, o_hgt[k - 1], 2, 0.5, leaves)
        elif neg.any():
            is_l = bool(x[0] < 0)
            other = z[int(x[1])] if is_l else z[int(x[0])]
            leaf = _Node(True, h0, 1, None, [])
            children = [leaf, other] if is_l else [other, leaf]
            members = other.members + 1
            left_member = leaf.members if is_l else other.members
            other_key = int(x[1]) if is_l else int(x[0])
            midpoint = (left_member + _mid(other)) / 2.0
            node = _Node(False, o_hgt[k - 1], members, midpoint, children)
            del z[other_key]
        else:
            left, right = z[int(x[0])], z[int(x[1])]
            members = left.members + right.members
            midpoint = (left.members + _mid(left) + _mid(right)) / 2.0
            node = _Node(False, o_hgt[k - 1], members, midpoint, [left, right])
            del z[int(x[0])]
            del z[int(x[1])]
        z[k] = node
    if node is None:
        raise ValueError("hc result has no merges")
    return node


def _limit(x1: float, x2: float, sub: _Node) -> tuple[float, list[float]]:
    """``plotNodeLimit`` for rectangle layout with ``center = FALSE``."""
    inner = (not sub.leaf) and x1 != x2
    if inner:
        limit = [x1]
        xx1 = x1
        for child in sub.children:
            xx1 = xx1 + child.members
            limit.append(xx1)
    else:
        limit = [x1, x2]
    x = x1 + _mid(sub)
    return x, limit


def _plot_node(canvas: Canvas, ax: Any, x1: float, x2: float, root: _Node) -> None:
    """``plotNode``: the segments of each inner node, parents before children."""
    stack: list[tuple[float, float, _Node]] = [(x1, x2, root)]
    while stack:
        a, b, sub = stack.pop()
        inner = (not sub.leaf) and a != b
        if not inner:
            continue
        y_top = sub.height
        x_top, limit = _limit(a, b, sub)
        for k, child in enumerate(sub.children):
            y_bot = 0.0 if child.height is None else child.height
            x_bot = limit[k] + _mid(child)
            canvas.segments(ax, x_top, y_top, x_bot, y_top)
            canvas.segments(ax, x_bot, y_top, x_bot, y_bot)
        for k in range(len(sub.children) - 1, -1, -1):
            child = sub.children[k]
            if not child.leaf:
                stack.append((limit[k], limit[k + 1], child))


def plot_hc(x: Any, what: str = "loglik", maxG: int | None = None, labels: bool = False,
            hang: float = 0, ax: Any = None, canvas: Canvas | None = None
            ) -> tuple[dict[str, Any], tuple[float, float, float, float], Canvas]:
    """Plot the dendrogram of an hc object, as ``plot.hc``.

    Returns the hclust result that ``as.hclust`` gives (invisible in R), the
    final ``par("usr")`` box, and the canvas holding the drawing log. Pass
    ``ax`` to draw on Matplotlib axes.
    """
    canvas = canvas or Canvas()
    if what == "loglik":
        hier = as_hclust_loglik(x, maxG=maxG, labels=labels)
    elif what == "merge":
        hier = as_hclust_merge(x, maxG=maxG, labels=labels)
    else:
        raise ValueError("unrecognized what option")

    cloglik = hier.pop("cloglik", None)
    root = as_dendrogram(hier, hang=hang)
    hgt = root.height
    mem = float(root.members)
    usr = canvas.window(ax, (0.5, mem + 0.5), (0.0, hgt))
    _plot_node(canvas, ax, 1.0, mem, root)

    ybot_raw = usr[2]
    if what == "loglik":
        r = cloglik[~np.isnan(cloglik)]
        ybot = float(np.max(r)) - ybot_raw
        ytop = float(np.min(r)) + ybot_raw
    else:
        nclus = np.asarray(hier["nclus"], dtype=float)
        ybot = float(np.max(nclus)) - ybot_raw
        ytop = 1.0 + ybot_raw
    at = pretty(np.linspace(ybot, ytop, 100), n=5, min_n=5)
    canvas.value("axis2", at)
    final_usr = (usr[0], usr[1], ybot, ytop)
    if ax is not None:
        _label_axes(ax, what, hier, usr, (ybot, ytop), at)
    return hier, final_usr, canvas


def _label_axes(ax: Any, what: str, hier: dict[str, Any], usr: tuple[float, float, float, float],
                ylim: tuple[float, float], at: np.ndarray) -> None:
    """The figure only. R draws the dendrogram first and then resets the y usr, so the
    drawn segments keep their device position and the axis is relabelled. The tick
    at value ``t`` sits at the device fraction ``(t - ybot) / (ytop - ybot)``."""
    method = hier.get("method")
    if what == "loglik":
        ylab = f"Classification log-likelihood ({method} model)"
    else:
        ylab = f"Number of Clusters ({method} model)"
    ybot, ytop = ylim
    frac = (np.asarray(at, dtype=float) - ybot) / (ytop - ybot)
    positions = usr[2] + frac * (usr[3] - usr[2])
    ax.set_ylabel(ylab)
    ax.set_yticks(positions)
    ax.set_yticklabels([f"{v:g}" for v in at])
    ax.set_xticks([])
    for side in ("top", "right", "bottom"):
        ax.spines[side].set_visible(False)
