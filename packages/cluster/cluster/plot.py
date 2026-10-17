"""Numeric fields used by bannerplot, clusplot, and pltree."""

from __future__ import annotations

import math
import sys

import numpy as np

from cluster.ellipsoid import _cov_wt, _spannel, ellipsoid_points

_EPS = sys.float_info.epsilon
_DBL_MIN = sys.float_info.min
_DBL_MAX = sys.float_info.max
_ROUNDING_EPS = 1e-10


def _seq_length(start, stop, length_out):
    if length_out <= 0:
        return []
    if length_out == 1:
        return [float(start)]
    if start == stop:
        return [float(start)] * length_out
    step = (stop - start) / (length_out - 1)
    values = [float(start + i * step) for i in range(length_out)]
    values[0] = float(start)
    values[-1] = float(stop)
    return values


def _r_pretty(lo, up, ndiv, min_n, shrink_sml, high_u_fact, eps_correction, return_bounds):
    h, h5, f_min = high_u_fact
    lo_in = lo
    up_in = up
    span = up_in - lo_in
    if span == 0 and up_in == 0:
        cell = 1.0
        small = True
    else:
        cell = max(abs(lo_in), abs(up_in))
        unit_bound = 1 / (1 + h) if h5 >= 1.5 * h + 0.5 else 1.5 / (1 + h5)
        unit_bound = (1 + unit_bound) * max(1, ndiv) * _EPS
        small = span < cell * unit_bound * 3
    if small:
        if cell > 10:
            cell = 9 + cell / 10
        cell *= shrink_sml
        if min_n > 1:
            cell /= min_n
    else:
        cell = span
        if math.isfinite(span):
            if ndiv > 1:
                cell /= ndiv
        elif ndiv >= 2:
            cell = up_in / ndiv - lo_in / ndiv
    smallest = f_min * _DBL_MIN
    if smallest == 0:
        smallest = _DBL_MIN
    if cell < smallest:
        cell = smallest
    elif cell > _DBL_MAX / 1.25:
        cell = _DBL_MAX / 1.25
    base = 10.0 ** math.floor(math.log10(cell))
    unit = base
    candidate = 2 * base
    if candidate - cell < h * (cell - unit):
        unit = candidate
        candidate = 5 * base
        if candidate - cell < h5 * (cell - unit):
            unit = candidate
            candidate = 10 * base
            if candidate - cell < h * (cell - unit):
                unit = candidate
    ns = math.floor(lo_in / unit + _ROUNDING_EPS)
    nu = math.ceil(up_in / unit - _ROUNDING_EPS)
    if eps_correction and (eps_correction > 1 or not small):
        lo = lo * (1 - _EPS) if lo_in != 0 else -_DBL_MIN
        up = up * (1 + _EPS) if up_in != 0 else _DBL_MIN
    while ns * unit > lo + _ROUNDING_EPS * unit:
        ns -= 1
    while not math.isfinite(ns * unit):
        ns += 1
    while nu * unit < up - _ROUNDING_EPS * unit:
        nu += 1
    while not math.isfinite(nu * unit):
        nu -= 1
    intervals = int(0.5 + nu - ns)
    if intervals < min_n:
        extra = min_n - intervals
        if lo_in == 0 and ns == 0 and up_in != 0:
            nu += extra
        elif up_in == 0 and nu == 0 and lo_in != 0:
            ns -= extra
        elif ns >= 0:
            nu += extra // 2
            ns -= extra // 2 + extra % 2
        else:
            ns -= extra // 2
            nu += extra // 2 + extra % 2
        ndiv = min_n
    else:
        ndiv = intervals
    if return_bounds:
        if ns * unit < lo:
            lo = ns * unit
        if nu * unit > up:
            up = nu * unit
    else:
        lo = ns
        up = nu
    return lo, up, ndiv, unit


def _pretty(x, n=5):
    finite = [float(v) for v in np.asarray(x, dtype=float).reshape(-1) if math.isfinite(float(v))]
    if not finite:
        return []
    min_n = int(n) // 3
    high_u_bias = 1.5
    u5_bias = 0.5 + 1.5 * high_u_bias
    lo, up, ndiv, _unit = _r_pretty(
        min(finite),
        max(finite),
        int(n),
        min_n,
        0.75,
        (high_u_bias, u5_bias, 2**-20),
        0,
        True,
    )
    breaks = _seq_length(lo, up, ndiv + 1)
    if ndiv:
        delta = abs(up - lo) / ndiv
        breaks = [0.0 if abs(v) < 1e-14 * delta else v for v in breaks]
    return breaks


def _signif(x, digits):
    if x == 0 or not math.isfinite(x):
        return float(x)
    power = math.floor(math.log10(abs(x)))
    return float(round(x, int(digits - 1 - power)))


def pltree(x):
    """Merge, sorted height, and order that ``plot.hclust`` reads."""
    return {
        "merge": [list(map(int, row)) for row in x["merge"]],
        "height": sorted(float(v) for v in x["height"]),
        "order": [int(v) for v in x["order"]],
    }


def bannerplot(x, w=None, from_left=True, xax_pretty=True):
    """Bar widths and axis positions drawn by ``bannerplot``."""
    if w is None:
        w = list(reversed([float(v) for v in x["height"]]))
    else:
        w = [float(v) for v in np.asarray(w, dtype=float).reshape(-1)]
    m = max(w) if w else 0.0
    if xax_pretty:
        at = _pretty([0.0, *w])
        at = [v for v in at if v <= m]
        if at and at[-1] * 1.01 < m:
            labels = at + [_signif(m, 3)]
            at = at + [m]
        else:
            labels = list(at)
    else:
        floor_m = math.floor(m)
        at = _seq_length(0.0, floor_m, 11) + [m]
        labels = [float(round(v, 2)) for v in at]
    if from_left:
        bars = [w, [m - v for v in w]]
    else:
        bars = [[m - v for v in w], w]
        if xax_pretty:
            at = [m - v for v in reversed(at)]
            labels = list(reversed(labels))
    y_labels = list(reversed(x["order"])) if isinstance(x, dict) and "order" in x else None
    return {"w": bars, "at": at, "labels": labels, "m": m, "y": y_labels}


def _double_center(matrix):
    data = np.asarray(matrix, dtype=float).copy()
    row = data.mean(axis=1)
    col = data.mean(axis=0)
    return data - row[:, None] - col[None, :] + data.mean()


def _positive_first(vectors):
    signed = np.array(vectors, dtype=float, copy=True)
    for column in range(signed.shape[1]):
        entries = np.flatnonzero(np.abs(signed[:, column]) > 0)
        if entries.size and signed[entries[0], column] < 0:
            signed[:, column] *= -1
    return signed


def _cmdscale(dist, k=2, add=True):
    """Classical scaling. ``dist`` is a square matrix or a condensed vector."""
    raw = np.asarray(dist, dtype=float)
    if raw.ndim == 1:
        n = int(round((1 + math.sqrt(1 + 8 * raw.size)) / 2))
        square = np.zeros((n, n))
        cursor = 0
        for left in range(n):
            for right in range(left + 1, n):
                square[left, right] = square[right, left] = raw[cursor]
                cursor += 1
        raw = square
    n = raw.shape[0]
    squared = raw ** 2
    centered = _double_center(squared)
    add_c = 0.0
    if add:
        size = 2 * n
        block = np.zeros((size, size))
        index = np.arange(n)
        block[n + index, index] = -1.0
        block[:n, n:] = -centered
        block[n:, n:] = _double_center(2 * raw)
        values = np.linalg.eigvals(block)
        add_c = float(np.max(np.real(values)))
        adjusted = np.zeros((n, n))
        off = ~np.eye(n, dtype=bool)
        adjusted[off] = (raw[off] + add_c) ** 2
        centered = _double_center(adjusted)
    evals, evecs = np.linalg.eigh(-centered / 2.0)
    order = np.argsort(evals)[::-1]
    evals = evals[order]
    evecs = evecs[:, order]
    chosen = evals[:k]
    vectors = evecs[:, :k]
    keep = chosen > 0
    if not np.all(keep):
        chosen = chosen[keep]
        vectors = vectors[:, keep]
    vectors = _positive_first(vectors)
    points = vectors * np.sqrt(chosen)
    positive = np.maximum(evals, 0.0)
    gof = [
        float(np.sum(chosen) / np.sum(np.abs(evals))),
        float(np.sum(chosen) / np.sum(positive)) if np.sum(positive) else float("nan"),
    ]
    return points, add_c, gof


def _princomp_scores(x):
    data = np.asarray(x, dtype=float)
    n, p = data.shape
    center = data.mean(axis=0)
    centered = data - center
    cv = (centered.T @ centered) / n
    use_cor = p > 2
    if use_cor:
        scale = np.sqrt(np.diag(cv))
        cv = cv / np.outer(scale, scale)
    else:
        scale = np.ones(p)
    evals, evecs = np.linalg.eigh(cv)
    order = np.argsort(evals)[::-1]
    evals = np.maximum(evals[order], 0.0)
    evecs = _positive_first(evecs[:, order])
    scores = (centered / scale) @ evecs
    return scores, np.sqrt(evals)


def _sample_cov(x):
    data = np.asarray(x, dtype=float)
    count = data.shape[0]
    centered = data - data.mean(axis=0)
    return (centered.T @ centered) / (count - 1)


def _qr_rank(matrix, tol=0.001):
    data = np.asarray(matrix, dtype=float)
    _q, factor = np.linalg.qr(data)
    diag = np.abs(np.diag(factor))
    if diag.size == 0 or diag[0] == 0:
        return 0
    return int(np.sum(diag > tol * diag[0]))


def _scale_matrix(data):
    centered = data - data.mean(axis=0)
    count = data.shape[0]
    scale = np.sqrt(np.sum(centered ** 2, axis=0) / (count - 1))
    return centered / scale


def _prepare_plane(x, diss):
    data = np.asarray(x, dtype=float)
    if diss:
        points, _add, gof = _cmdscale(data, k=2, add=True)
        if _add < 0:
            points, _add, gof = _cmdscale(data, k=2, add=False)
        return points[:, :2], float(gof[1])
    if data.ndim != 2:
        raise ValueError("x is not a data matrix")
    n, p = data.shape
    if p <= 1:
        column = data.reshape(n)
        return np.column_stack([column, np.zeros(n)]), 1.0
    scores, sdev = _princomp_scores(data)
    variance = sdev ** 2
    share = np.cumsum(variance / variance.sum())
    return scores[:, :2], float(share[1])


def _mahalanobis(data, center, cov):
    diff = np.asarray(data, dtype=float) - center
    solved = np.linalg.solve(cov, diff.T).T
    return np.sum(diff * solved, axis=1)


def _shape_from_angle(a, b, q):
    rotation = np.array(
        [[math.cos(q), -math.sin(q)], [math.sin(q), math.cos(q)]],
        dtype=float,
    )
    diagonal = np.diag([a * a, b * b])
    return rotation @ diagonal @ rotation.T


def clusplot(x, clus=None, diss=False, stand=False, lines=2, span=True):
    """Distances and shading, plus the ellipse geometry the plot draws."""
    if clus is None and isinstance(x, dict) and "clustering" in x:
        if x.get("data") is None:
            raise ValueError("no diss nor data found for 'clusplot()'")
        return clusplot(x["data"], x["clustering"], diss=False, stand=stand, lines=lines, span=span)
    points, var_dec = _prepare_plane(x, diss)
    if stand:
        points = _scale_matrix(points)
    labels = [int(v) if float(v) == int(v) else v for v in np.asarray(clus).reshape(-1)]
    if len(labels) != len(points):
        raise ValueError("The clustering vector is of incorrect length")
    levels = sorted(set(labels))
    n_clusters = len(levels)
    span_x = float(np.ptp(points[:, 0]))
    span_y = float(np.ptp(points[:, 1]))
    shapes = []
    loc = np.zeros((n_clusters, 2))
    d2 = np.zeros(n_clusters)
    area = np.zeros(n_clusters)
    counts = np.zeros(n_clusters)
    for index, level in enumerate(levels):
        block = points[np.array([label == level for label in labels])]
        counts[index] = block.shape[0]
        center_i, radius, shape, cluster_area = _one_cluster(block, span, span_x, span_y)
        loc[index] = center_i
        d2[index] = radius
        shapes.append(shape)
        area[index] = cluster_area
    ellipses = [
        ellipsoid_points(shapes[i], d2[i], loc[i], n_half=201) for i in range(n_clusters)
    ]
    ratio = counts / area
    finite = ratio[ratio < 1e7]
    total = float(finite.sum()) if finite.size else 0.0
    if total == 0:
        total = 1.0
    density = 3 + (ratio * 37) / total
    density = np.minimum(density, 41)
    distances = _between(loc, shapes, d2, lines) if n_clusters > 1 and lines in (1, 2) else None
    shading = [None if value == 41 else float(value) for value in density]
    return {
        "distances": None if distances is None else distances.tolist(),
        "shading": shading,
        "x": points.tolist(),
        "var_dec": var_dec,
        "loc": loc.tolist(),
        "d2": d2.tolist(),
        "shape": [matrix.tolist() for matrix in shapes],
        "ellipses": [ellipse.tolist() for ellipse in ellipses],
    }


def _one_cluster(block, span, span_x, span_y):
    """Center, squared radius, shape, and area of one cluster ellipse."""
    cov = _sample_cov(np.vstack([block, np.zeros((1, 2))]) if block.shape[0] == 1 else block)
    x_lo, x_hi = float(block[:, 0].min()), float(block[:, 0].max())
    y_lo, y_hi = float(block[:, 1].min()), float(block[:, 1].max())
    deficient = _qr_rank(cov, tol=0.001) != 2
    if not span and deficient:
        if abs(x_hi - x_lo) > span_x / 70 or abs(y_hi - y_lo) > span_y / 50:
            center = np.array([x_lo + (x_hi - x_lo) / 2, y_lo + (y_hi - y_lo) / 2])
            a = 1.05 * math.hypot(center[0] - x_lo, center[1] - y_lo)
            if abs(x_hi - x_lo) > span_x / 70:
                high = int(np.argmax(block[:, 0]))
                low = int(np.argmin(block[:, 0]))
                q = math.atan((block[high, 1] - block[low, 1]) / (block[high, 0] - block[low, 0]))
                if span_y == 0:
                    b = 1.0
                elif abs(y_hi - y_lo) > span_y / 50:
                    b = (y_hi - y_lo) / 10
                else:
                    b = span_y / 40
            else:
                b = 1.0 if span_x == 0 else span_x / 40
                q = math.pi / 2
            shape = _shape_from_angle(a, b, q)
        else:
            a = span_x / 90
            b = span_y / 70
            if a == 0:
                a = 1.0
            if b == 0:
                b = 1.0
            shape = np.diag([a * a, b * b])
            center = block[0].astype(float)
        return center, 1.0, shape, math.pi * a * b
    if span and deficient:
        if np.any(block[:, 0] != block[0, 0]) or np.any(block[:, 1] != block[0, 1]):
            center = np.array([x_lo + (x_hi - x_lo) / 2, y_lo + (y_hi - y_lo) / 2])
            a = math.hypot(center[0] - x_lo, center[1] - y_lo)
            if np.any(block[:, 0] != block[0, 0]):
                high = int(np.argmax(block[:, 0]))
                low = int(np.argmin(block[:, 0]))
                q = math.atan((block[high, 1] - block[low, 1]) / (block[high, 0] - block[low, 0]))
            else:
                q = math.pi / 2
            b = 1e-7
            shape = _shape_from_angle(a, b, q)
        else:
            a = span_x / 90
            b = span_y / 70
            if a == 0:
                a = 1.0
            if b == 0:
                b = 1.0
            shape = np.diag([a * a, b * b])
            center = block[0].astype(float)
        return center, 1.0, shape, math.pi * a * b
    if not span:
        center = block.mean(axis=0)
        radius = float(np.max(_mahalanobis(block, center, cov)))
        cluster_area = math.pi * radius * math.sqrt(cov[0, 0] * cov[1, 1] - cov[0, 1] ** 2)
        return center, radius, cov, cluster_area
    sqdist, prob, _it, _ierr = _spannel(block, tol=0.01, maxit=5000)
    center, weighted, weights = _cov_wt(block, prob)
    shape = weighted * (1.0 - float(np.sum(weights ** 2)))
    radius = float(np.average(sqdist, weights=prob))
    det = shape[0, 0] * shape[1, 1] - shape[0, 1] ** 2
    cluster_area = math.pi * radius * math.sqrt(max(0.0, det))
    return center, radius, shape, cluster_area


def _safe_div(left, right):
    if right == 0:
        if left == 0:
            return float("nan")
        return math.copysign(float("inf"), left)
    return left / right


def _between(loc, shapes, d2, lines):
    n_clusters = loc.shape[0]
    afstand = np.zeros((n_clusters, n_clusters))
    missing = np.zeros((n_clusters, n_clusters), dtype=bool)

    def intersection(shape, radius, center, slope):
        s0 = shape[1, 1] - 2 * shape[0, 1] * slope + shape[0, 0] * slope * slope
        height = _safe_div((shape[0, 0] * shape[1, 1] - shape[0, 1] ** 2) * radius, s0)
        if not math.isfinite(height) or height < 0:
            root = float("nan")
        else:
            root = math.sqrt(height)
        signed = np.array([root, -root])
        return np.column_stack([center[0] + signed, center[1] + slope * signed])

    def choose(points, axis, left, right):
        for row in range(2):
            value = float(points[row, axis])
            if math.isnan(value):
                continue
            if loc[left, axis] <= value <= loc[right, axis]:
                return points[row]
        return np.array([math.nan, math.nan])

    for i in range(n_clusters - 1):
        for j in range(i + 1, n_clusters):
            slope = _safe_div(loc[j, 1] - loc[i, 1], loc[j, 0] - loc[i, 0])
            first = intersection(shapes[i], d2[i], loc[i], slope)
            second = intersection(shapes[j], d2[j], loc[j], slope)
            if loc[i, 0] != loc[j, 0]:
                if loc[i, 0] < loc[j, 0]:
                    punt1 = choose(first, 0, i, j)
                    punt2 = choose(second, 0, i, j)
                else:
                    punt1 = choose(first, 0, j, i)
                    punt2 = choose(second, 0, j, i)
            elif loc[i, 1] < loc[j, 1]:
                punt1 = choose(first, 1, i, j)
                punt2 = choose(second, 1, i, j)
            else:
                punt1 = choose(first, 1, j, i)
                punt2 = choose(second, 1, j, i)
            gap = math.hypot(loc[j, 0] - loc[i, 0], loc[j, 1] - loc[i, 1])
            reach = math.hypot(punt1[0] - loc[i, 0], punt1[1] - loc[i, 1]) + math.hypot(
                punt2[0] - loc[j, 0], punt2[1] - loc[j, 1]
            )
            if not math.isfinite(punt1[0]) or not math.isfinite(punt2[0]) or reach > gap:
                missing[i, j] = True
            elif lines == 1:
                afstand[i, j] = gap
            else:
                afstand[i, j] = math.hypot(punt1[0] - punt2[0], punt1[1] - punt2[1])
    filled = afstand + afstand.T
    filled[missing | missing.T] = np.nan
    return filled
