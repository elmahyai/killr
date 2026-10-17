"""Translation of ``plot.clustCombi``, ``combiPlot`` and ``entPlot`` (mclust 6.1.3).

``combiPlot`` draws one classification: ``clPairs`` for more than two
columns, the two-dimensional ``mclust2Dplot`` classification for two, and
the one-dimensional ``mclust1Dplot`` classification for one. The 2-D and
1-D classification drawing is written here; it is not wrapped in a
killplot function (the drawing is Matplotlib-level).

``plot.clustCombi`` with ``what = "tree"`` draws the dendrogram of the
combination hierarchy. The layout follows ``plot.dendrogram`` (triangle
edges, midpoints from ``as.dendrogram``), which the translated
``combiTree`` in ``combi_tree.py`` does not do: that module uses SciPy's
layout. The merge order and heights here follow ``combiTree`` in R.

The private helpers ``pcws2_reg`` and ``pcws3_reg`` are not translated in
their own files; they are the segmented regressions ``entPlot`` uses.
"""

from __future__ import annotations

from typing import Any, Sequence

import numpy as np

from mclust._plot_common import Canvas, _range, cl_pairs, class_colors
from mclust.clust_combi import _comb_mat
from mclust.mclust_options import mclust_options

__all__ = ["plot_clust_combi", "combi_plot", "ent_plot", "combi_tree_plot"]

_LETTERS = [chr(ord("A") + i) for i in range(26)]


def _field(obj: Any, name: str) -> Any:
    if isinstance(obj, dict):
        return obj[name]
    return getattr(obj, name)


def _xlog(x: Any) -> np.ndarray:
    a = np.asarray(x, dtype=float)
    return np.where(a == 0.0, 0.0, a * np.log(np.where(a == 0.0, 1.0, a)))


def _extendrange_r(lo: float, hi: float, f: float) -> tuple[float, float]:
    d = hi - lo
    return lo - f * d, hi + f * d


# ---------------------------------------------------------------------------
# Segmented regressions used by entPlot (pcws2_reg and pcws3_reg in R)
# ---------------------------------------------------------------------------

def _line_fit(x: np.ndarray, y: np.ndarray) -> tuple[float, float]:
    mx, my = x.mean(), y.mean()
    a = np.sum((x - mx) * (y - my)) / np.sum((x - mx) ** 2)
    return float(a), float(-a * mx + my)


def pcws2_reg(x: Any, y: Any) -> dict[str, Any]:
    """Two-piece linear regression with the change point that minimises the SSE."""
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    C = x.size
    ss_best = np.inf
    best: dict[str, Any] = {}
    for c in range(2, C):
        x1, y1 = x[0:c], y[0:c]
        x2, y2 = x[c - 1:C], y[c - 1:C]
        a1, b1 = _line_fit(x1, y1)
        a2, b2 = _line_fit(x2, y2)
        ss = np.sum((a1 * x1 + b1 - y1) ** 2) + np.sum((a2 * x2 + b2 - y2) ** 2)
        if ss < ss_best:
            ss_best = ss
            best = {"c": c, "a1": a1, "b1": b1, "a2": a2, "b2": b2}
    return best


def pcws3_reg(x: Any, y: Any) -> dict[str, Any]:
    """Three-piece linear regression with the two change points that minimise the SSE."""
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    C = x.size
    ss_best = np.inf
    best: dict[str, Any] = {}
    for c1 in range(2, C - 1):
        for c2 in range(c1 + 1, C):
            x1, y1 = x[0:c1], y[0:c1]
            x2, y2 = x[c1 - 1:c2], y[c1 - 1:c2]
            x3, y3 = x[c2 - 1:C], y[c2 - 1:C]
            a1, b1 = _line_fit(x1, y1)
            a2, b2 = _line_fit(x2, y2)
            a3, b3 = _line_fit(x3, y3)
            ss = (np.sum((a1 * x1 + b1 - y1) ** 2) + np.sum((a2 * x2 + b2 - y2) ** 2)
                  + np.sum((a3 * x3 + b3 - y3) ** 2))
            if ss < ss_best:
                ss_best = ss
                best = {"c1": c1, "c2": c2, "a1": a1, "b1": b1,
                        "a2": a2, "b2": b2, "a3": a3, "b3": b3}
    return best


# ---------------------------------------------------------------------------
# Entropy and merge counts (entPlot)
# ---------------------------------------------------------------------------

def entropy_path(z: Any, combi_m: dict[int, Any]) -> tuple[np.ndarray, np.ndarray]:
    """Entropy of each K-cluster solution, and the merged-observation counts.

    ``ent[K]`` is the entropy of the K-cluster solution (index K-1).
    ``mergedn[K]`` counts the observations that fall in one of the two
    clusters merged to go from K+1 to K clusters (index K-1).
    """
    z = np.asarray(z, dtype=float)
    G = z.shape[1]
    ent = np.zeros(G)
    z0 = z
    for K in range(G, 0, -1):
        z0 = z0 @ np.asarray(combi_m[K], dtype=float).T
        ent[K - 1] = -np.sum(_xlog(z0))

    mergedn = np.zeros(max(G - 1, 0))
    z0 = z
    for K in range(G - 1, 0, -1):
        z0 = z0 @ np.asarray(combi_m[K + 1], dtype=float).T
        M = np.asarray(combi_m[K], dtype=float)
        sub = M[M.sum(axis=1) == 2, :]
        w = np.flatnonzero(sub.ravel(order="F") != 0) + 1
        labels = _map_rows(z0)
        mergedn[K - 1] = np.sum(np.isin(labels, w))
    return ent, mergedn


def ent_plot(z: Any, combi_m: dict[int, Any], abc: Sequence[str] = ("standard", "normalized"),
             reg: Sequence[int] | None = (2,), fig: Any = None,
             canvas: Canvas | None = None) -> Canvas:
    """``entPlot``: the entropy by number of clusters, and the entropy by merged count.

    Each ``abc`` choice is a row of two panels (entropy, then its difference or
    its normalised difference), as ``par(mfrow = c(1, 2))`` lays them out in R.
    """
    canvas = canvas or Canvas()
    z = np.asarray(z, dtype=float)
    Kmax = z.shape[1]
    ent, mergedn = entropy_path(z, combi_m)
    if Kmax == 2:
        reg = None
    xs = np.arange(1, Kmax + 1, dtype=float)
    groups = [g for g in ("standard", "normalized") if g in abc]
    if fig is not None and groups:
        axes = list(fig.subplots(len(groups), 2, squeeze=False).ravel())
    else:
        axes = [None] * (2 * len(groups))

    if "standard" in abc:
        ax1, ax2 = axes[2 * groups.index("standard")], axes[2 * groups.index("standard") + 1]
        canvas.window(ax1, _range(xs), _range(ent))
        canvas.xy(ax1, xs, ent, type="p")
        if reg is not None and 2 in reg:
            fit = pcws2_reg(xs, ent)
            c = fit["c"]
            canvas.lines(ax1, xs[:c], fit["a1"] * xs[:c] + fit["b1"], col="red")
            canvas.lines(ax1, xs[c - 1:], fit["a2"] * xs[c - 1:] + fit["b2"], col="red")
        if reg is not None and 3 in reg:
            fit = pcws3_reg(xs, ent)
            c1, c2 = fit["c1"], fit["c2"]
            canvas.lines(ax1, xs[:c1], fit["a1"] * xs[:c1] + fit["b1"], col="blue")
            canvas.lines(ax1, xs[c1 - 1:c2], fit["a2"] * xs[c1 - 1:c2] + fit["b2"], col="blue")
            canvas.lines(ax1, xs[c2 - 1:], fit["a3"] * xs[c2 - 1:] + fit["b3"], col="blue")
        d_idx = np.arange(1, Kmax, dtype=float)
        dent = ent[1:] - ent[:-1]
        canvas.window(ax2, _range(d_idx), _range(dent))
        canvas.xy(ax2, d_idx, dent, type="p")

    if "normalized" in abc:
        ax1, ax2 = axes[2 * groups.index("normalized")], axes[2 * groups.index("normalized") + 1]
        X = np.concatenate([[0.0], np.cumsum(mergedn)])
        canvas.window(ax1, _range(X), _range(ent))
        canvas.xy(ax1, X, ent, type="p")
        if reg is not None and 2 in reg:
            fit = pcws2_reg(X, ent)
            c = fit["c"]
            canvas.lines(ax1, X[:c], fit["a1"] * X[:c] + fit["b1"], col="red")
            canvas.lines(ax1, X[c - 1:], fit["a2"] * X[c - 1:] + fit["b2"], col="red")
        if reg is not None and 3 in reg:
            fit = pcws3_reg(X, ent)
            c1, c2 = fit["c1"], fit["c2"]
            canvas.lines(ax1, X[:c1], fit["a1"] * X[:c1] + fit["b1"], col="blue")
            canvas.lines(ax1, X[c1 - 1:c2], fit["a2"] * X[c1 - 1:c2] + fit["b2"], col="blue")
            canvas.lines(ax1, X[c2 - 1:], fit["a3"] * X[c2 - 1:] + fit["b3"], col="blue")
        d_idx = np.arange(1, Kmax, dtype=float)
        dn = (ent[1:] - ent[:-1]) / mergedn
        canvas.window(ax2, _range(d_idx), _range(dn))
        canvas.xy(ax2, d_idx, dn, type="p")
    return canvas


# ---------------------------------------------------------------------------
# combiPlot: one classification
# ---------------------------------------------------------------------------

def _map_rows(z: np.ndarray) -> np.ndarray:
    """``map(z)`` as a vectorised row argmax: one-based, first column on a tie."""
    return np.argmax(np.asarray(z, dtype=float), axis=1) + 1


def _classes_of(z: np.ndarray, combi_m: Any) -> np.ndarray:
    return _map_rows(z @ np.asarray(combi_m, dtype=float).T)


def _mclust2d_classification(canvas: Canvas, data: np.ndarray, classification: np.ndarray,
                             ax: Any = None) -> None:
    labels = np.asarray(classification).astype(str)
    U = sorted(set(labels.tolist()))
    L = len(U)
    opt_sym = mclust_options("classPlotSymbols")
    if L <= len(opt_sym):
        symbols = list(opt_sym[:L])
    elif L <= 9:
        symbols = [str(i + 1) for i in range(9)]
    elif L <= 26:
        symbols = _LETTERS[:L]
    else:
        raise ValueError("too many classes for mclust2Dplot")
    colors = class_colors(L, mclust_options("classPlotColors"))
    xlim = _range(data[:, 0])
    ylim = _range(data[:, 1])
    canvas.window(ax, xlim, ylim)
    for k in range(L):
        sel = labels == U[k]
        canvas.points(ax, data[sel, 0], data[sel, 1], pch=symbols[k], col=colors[k])


def _mclust1d_classification(canvas: Canvas, data: np.ndarray, classification: np.ndarray,
                             ax: Any = None) -> None:
    labels = np.asarray(classification).astype(str)
    M = len(set(labels.tolist()))
    xlim = _range(data)
    ylim = _extendrange_r(0.0, float(M), 0.1)
    canvas.window(ax, xlim, ylim)
    # The default symbol is "|", drawn with vpoints (symbols()), which is not a
    # plot.xy call, so nothing else is logged.


def combi_plot(data: Any, z: Any, combi_m: Any, fig: Any = None,
               canvas: Canvas | None = None) -> Canvas:
    """``combiPlot``: the classification given by ``map(t(combiM %*% t(z)))``."""
    canvas = canvas or Canvas()
    x = np.asarray(data, dtype=float)
    if x.ndim == 1:
        x = x.reshape(-1, 1)
    p = x.shape[1]
    classification = _classes_of(np.asarray(z, dtype=float), combi_m)
    ax = fig.add_subplot(111) if fig is not None else None
    if p > 2:
        cl_pairs(canvas, fig, x[:, :min(5, p)], classification)
    elif p == 2:
        _mclust2d_classification(canvas, x, classification, ax=ax)
    else:
        _mclust1d_classification(canvas, x[:, 0], classification, ax=ax)
    return canvas


# ---------------------------------------------------------------------------
# plot.clustCombi: the classification sequence, the entropy plot and the tree
# ---------------------------------------------------------------------------

def _merge_order(combi_m: dict[int, Any], G: int) -> tuple[list[int], list[int]]:
    """Permutation of the z columns and the merge sequence, as ``plot.clustCombi`` builds them.

    Returns ``(j, i)`` as 1-based lists of length G (index 0 holds the R
    ``1`` and ``0`` placeholders).
    """
    curr = np.arange(1, G + 1, dtype=float)
    i_list: list[float] = []
    j_list: list[float] = []
    for K in range(G, 1, -1):
        M = np.asarray(combi_m[K - 1], dtype=float)
        rs = M.sum(axis=1)
        l1 = int(np.flatnonzero(rs != 1)[0]) + 1
        mc = M @ curr
        l2 = mc[l1 - 1] - curr[l1 - 1]
        i_list.insert(0, curr[l1 - 1])
        j_list.insert(0, l2)
        vec = np.zeros(K - 1)
        vec[l1 - 1] = 1.0
        curr = mc - l2 * vec
    j = [1.0] + j_list
    i = [0.0] + i_list
    return j, i


def _combi_merge(combi_m: dict[int, Any], G: int) -> tuple[np.ndarray, np.ndarray]:
    """The merge matrix and merge heights of ``combiTree`` (before the entropy step)."""
    curr = np.arange(1, G + 1, dtype=int)
    merged = -np.arange(1, G + 1, dtype=int)
    merge = np.zeros((G - 1, 2), dtype=int)
    for k in range(1, G):
        Kp = G - k + 1
        M = np.asarray(combi_m[Kp - 1], dtype=float)
        rs = M.sum(axis=1)
        l1 = int(np.flatnonzero(rs != 1)[0]) + 1
        mc = M @ curr
        l2 = int(mc[l1 - 1] - curr[l1 - 1])
        drop = max(l1, l2)
        curr = curr[curr != drop]
        m1, m2 = merged[l1 - 1], merged[l2 - 1]
        merge[k - 1] = [m1, m2]
        mask = (merged == m1) | (merged == m2)
        merged[mask] = k
    return merge, merged


def _combi_heights(combiz: dict[int, Any], G: int, yaxis: str) -> np.ndarray:
    if yaxis == "step":
        return np.arange(1, G, dtype=float)
    ks = sorted(combiz.keys(), reverse=True)
    h = np.array([-np.sum(_xlog(np.asarray(combiz[k], dtype=float))) for k in ks])
    h = 1.0 - (h - h.min()) / (h.max() - h.min())
    return h[1:]


class _Node:
    __slots__ = ("leaf", "height", "members", "midpoint", "children")

    def __init__(self, leaf: bool, height: float, members: int, midpoint: float,
                 children: list["_Node"]) -> None:
        self.leaf = leaf
        self.height = height
        self.members = members
        self.midpoint = midpoint
        self.children = children


def _mid(node: _Node) -> float:
    return 0.0 if node.leaf else node.midpoint


def _as_dendrogram(merge: np.ndarray, heights: np.ndarray, G: int) -> _Node:
    """``as.dendrogram`` for the merge matrix (hang = -1: leaves at height 0)."""
    cache: dict[int, _Node] = {}

    def build(x: int) -> _Node:
        if x < 0:
            return _Node(True, 0.0, 1, 0.0, [])
        if x in cache:
            return cache[x]
        left = build(int(merge[x - 1, 0]))
        right = build(int(merge[x - 1, 1]))
        members = left.members + right.members
        midpoint = (left.members + _mid(left) + _mid(right)) / 2.0
        node = _Node(False, float(heights[x - 1]), members, midpoint, [left, right])
        cache[x] = node
        return node

    return build(G - 1)


def _plot_node(canvas: Canvas, ax: Any, x1: float, x2: float, node: _Node) -> None:
    """``plotNode`` for type "triangle": edges to the children, then each child in turn."""
    if node.leaf:
        return
    inner = x1 != x2
    limits = [x1]
    acc = x1
    for child in node.children:
        acc += child.members
        limits.append(acc)
    x_top = x1 + node.midpoint
    y_top = node.height
    if inner:
        for k, child in enumerate(node.children):
            x_bot = limits[k] + _mid(child)
            y_bot = child.height if not child.leaf else 0.0
            canvas.segments(ax, x_top, y_top, x_bot, y_bot)
    for k, child in enumerate(node.children):
        _plot_node(canvas, ax, limits[k], limits[k + 1], child)


def _combi_tree_data(object_: Any, yaxis: str = "entropy") -> tuple[np.ndarray, np.ndarray, _Node]:
    G = int(_field(_field(object_, "MclustOutput"), "G"))
    combi_m = _field(object_, "combiM")
    merge, _ = _combi_merge(combi_m, G)
    heights = _combi_heights(_field(object_, "combiz"), G, yaxis)
    root = _as_dendrogram(merge, heights, G)
    return merge, heights, root


def combi_tree_plot(object_: Any, type_: str = "triangle", yaxis: str = "entropy",
                    fig: Any = None, canvas: Canvas | None = None) -> tuple[Canvas, np.ndarray, np.ndarray]:
    """``combiTree``: the dendrogram of the combination hierarchy (triangle edges)."""
    canvas = canvas or Canvas()
    if type_ not in ("triangle", "rectangle"):
        raise ValueError("type must be 'triangle' or 'rectangle'")
    if type_ != "triangle":
        raise NotImplementedError("only the triangle layout is translated")
    merge, heights, root = _combi_tree_data(object_, yaxis)
    G = int(_field(_field(object_, "MclustOutput"), "G"))
    ax = fig.add_subplot(111) if fig is not None else None
    canvas.window(ax, (0.5, G + 0.5), (0.0, root.height))
    _plot_node(canvas, ax, 1.0, float(G), root)
    return canvas, merge, heights


def plot_clust_combi(object_: Any, what: Sequence[str] = ("classification", "entropy", "tree"),
                     fig: Any = None, canvas: Canvas | None = None) -> Canvas:
    """``plot.clustCombi``: the classification sequence, then the entropy plot, then the tree.

    The three plots run in that order whatever the order of ``what``. For
    each K from G to 1 the classification is drawn with the z columns
    permuted so that the two clusters merged at each step are adjacent.
    With ``fig``, each page is cleared first, so the figure ends on the last
    page drawn (as R's ``par(ask = TRUE)`` shows one page at a time).
    """
    canvas = canvas or Canvas()
    if not _has_clust_combi(object_):
        raise ValueError("object not of class 'clustCombi'")
    output = _field(object_, "MclustOutput")
    data = np.asarray(_field(output, "data"), dtype=float)
    if data.ndim == 1:
        data = data.reshape(-1, 1)
    z = np.asarray(_field(output, "z"), dtype=float)
    G = int(_field(output, "G"))
    combi_m = _field(object_, "combiM")
    what = list(what)

    def new_page() -> None:
        if fig is not None:
            fig.clear()

    if "classification" in what:
        j, i = _merge_order(combi_m, G)
        permut_z = z[:, [int(v) - 1 for v in j]]
        cm = np.eye(G)
        for K in range(G, 0, -1):
            new_page()
            combi_plot(data, permut_z, cm, fig=fig, canvas=canvas)
            hits = np.flatnonzero(np.asarray(j) == i[K - 1]) + 1
            l1 = int(hits[0]) if hits.size else 0
            cm = _comb_mat(K, l1, K) @ cm

    if "entropy" in what:
        new_page()
        ent_plot(z, combi_m, fig=fig, canvas=canvas)

    if "tree" in what:
        new_page()
        combi_tree_plot(object_, fig=fig, canvas=canvas)
    return canvas


def _has_clust_combi(obj: Any) -> bool:
    if isinstance(obj, dict):
        return "combiM" in obj and "MclustOutput" in obj and "combiz" in obj
    return hasattr(obj, "combiM") and hasattr(obj, "MclustOutput")
