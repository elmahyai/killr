"""One- and two-dimensional interpolation, splines, and piecewise polynomials."""

from __future__ import annotations

import warnings

import numpy as np

from pracma._util import PracmaError
from pracma.arrays import Diag, finds, zeros
from pracma.interp_poly import polyval
from pracma.interp_sort import is_sorted
from pracma.interp_support import (
    approx,
    find_interval,
    is_numeric_value,
    is_r_matrix,
    is_r_vector,
    match_arg,
    nelder_mead,
    r_colon,
    r_get,
    r_set,
    stopifnot,
    which_index,
)


def _splineslopes(h, delta):
    n = h.size + 1
    a = np.zeros(n - 1)
    b = np.zeros(n - 1)
    cc = np.zeros(n - 1)
    rhs = np.zeros(n - 1)
    a[: n - 2] = h[1 : n - 1]
    a[n - 2] = h[n - 3] + h[n - 2]
    b[0] = h[1]
    b[1 : n - 1] = 2 * (h[1 : n - 1] + h[: n - 2])
    b = np.concatenate([b, np.array([h[n - 3]])])
    cc[0] = h[0] + h[1]
    cc[1 : n - 1] = h[: n - 2]
    rhs[0] = ((h[0] + 2 * cc[0]) * h[1] * delta[0] + h[0] ** 2 * delta[1]) / cc[0]
    rhs[1 : n - 1] = 3 * (h[1 : n - 1] * delta[: n - 2] + h[: n - 2] * delta[1 : n - 1])
    last = (h[n - 2] ** 2 * delta[n - 3] + (2 * a[n - 2] + h[n - 2]) * h[n - 3] * delta[n - 2]) / a[n - 2]
    rhs = np.concatenate([rhs, np.array([last])])
    return _tridiagonal(a, b, cc, rhs)


def _tridiagonal(a, b, cc, d):
    x = np.array(d, dtype=float, copy=True)
    diagonal = np.array(b, dtype=float, copy=True)
    n = x.size
    for j in range(n - 1):
        mu = a[j] / diagonal[j]
        diagonal[j + 1] = diagonal[j + 1] - mu * cc[j]
        x[j + 1] = x[j + 1] - mu * x[j]
    x[n - 1] = x[n - 1] / diagonal[n - 1]
    for j in range(n - 2, -1, -1):
        x[j] = (x[j] - cc[j] * x[j + 1]) / diagonal[j]
    return x


def _ml_spline(x, y, xi):
    nodes = np.asarray(x, dtype=float).reshape(-1)
    values = np.asarray(y, dtype=float).reshape(-1)
    points = np.asarray(xi, dtype=float).reshape(-1)
    n = nodes.size
    if values.size != n:
        raise PracmaError("Arguments 'x', 'y' must have the same length.")
    if n < 3:
        raise PracmaError("spline routine: requires at least 3 points")
    steps = np.diff(nodes)
    delta = np.diff(values) / steps
    slopes = _splineslopes(steps, delta)
    cubic = (3 * delta - 2 * slopes[: n - 1] - slopes[1:n]) / steps
    quartic = (slopes[: n - 1] - 2 * delta + slopes[1:n]) / steps**2
    interval = np.ones(points.size, dtype=int)
    for j in range(1, n - 1):
        interval[nodes[j] <= points] = j + 1
    chosen = interval - 1
    shift = points - nodes[chosen]
    return values[chosen] + shift * (slopes[chosen] + shift * (cubic[chosen] + shift * quartic[chosen]))


def _pchip_end(h1, h2, del1, del2):
    slope = ((2 * h1 + h2) * del1 - h1 * del2) / (h1 + h2)
    if np.sign(slope) != np.sign(del1):
        slope = 0.0
    elif np.sign(del1) != np.sign(del2) and abs(slope) > abs(3 * del1):
        slope = 3 * del1
    return slope


def _pchip_slopes(h, delta):
    n = h.size + 1
    slopes = np.zeros(h.size)
    same = np.sign(delta[: n - 2]) * np.sign(delta[1 : n - 1]) > 0
    k = which_index(same) + 1
    if k.size:
        w1 = 2 * h[k - 1] + h[k - 2]
        w2 = h[k - 1] + 2 * h[k - 2]
        slopes = r_set(slopes, k, (w1 + w2) / (w1 / delta[k - 2] + w2 / delta[k - 1]))
    slopes = r_set(slopes, [1], _pchip_end(h[0], h[1], delta[0], delta[1]))
    slopes = r_set(slopes, [n], _pchip_end(h[n - 2], h[n - 3], delta[n - 2], delta[n - 3]))
    return slopes


def pchip(xi, yi, x):
    stopifnot(is_numeric_value(xi), "is.numeric(xi)")
    stopifnot(is_numeric_value(yi), "is.numeric(yi)")
    stopifnot(is_numeric_value(x), "is.numeric(x)")
    nodes = np.asarray(xi, dtype=float).reshape(-1)
    values = np.asarray(yi, dtype=float).reshape(-1)
    points = np.asarray(x, dtype=float).reshape(-1)
    if not bool(is_sorted(nodes)[0] == 1):
        raise PracmaError("Argument 'xi' must be a sorted vector of real numbers.")
    n = nodes.size
    if values.size != n:
        raise PracmaError("Arguments 'xi', 'yi' must be vectors of equal length.")
    if n <= 2:
        raise PracmaError("At least three points needed for cubic interpolation.")
    steps = np.diff(nodes)
    delta = np.diff(values) / steps
    slopes = _pchip_slopes(steps, delta)
    cubic = (3 * delta - 2 * slopes[: n - 1] - slopes[1:n]) / steps
    quartic = (slopes[: n - 1] - 2 * delta + slopes[1:n]) / steps**2
    interval = np.ones(points.size, dtype=int)
    for j in range(1, n - 1):
        interval[nodes[j] <= points] = j + 1
    chosen = interval - 1
    shift = points - nodes[chosen]
    return values[chosen] + shift * (slopes[chosen] + shift * (cubic[chosen] + shift * quartic[chosen]))


def pchipfun(xi, yi):
    stopifnot(is_numeric_value(xi), "is.numeric(xi)")
    stopifnot(is_numeric_value(yi), "is.numeric(yi)")
    nodes = np.asarray(xi, dtype=float).reshape(-1)
    values = np.asarray(yi, dtype=float).reshape(-1)
    if not bool(is_sorted(nodes)[0] == 1):
        raise PracmaError("Argument 'xi' must be a sorted vector of real numbers.")
    if values.size != nodes.size:
        raise PracmaError("Arguments 'xi', 'yi' must be vectors of equal length.")
    if nodes.size <= 2:
        raise PracmaError("At least three points needed for cubic interpolation.")

    def interpolate(x):
        return pchip(nodes, values, x)

    return interpolate


def interp1(x, y, xi=None, method="linear"):
    if not (is_r_vector(x) and is_numeric_value(x) and is_r_vector(y) and is_numeric_value(y)):
        raise PracmaError("Arguments 'x' and 'y' must be numeric vectors.")
    nodes = np.asarray(x, dtype=float).reshape(-1)
    values = np.asarray(y, dtype=float).reshape(-1)
    if xi is None:
        xi = nodes
    points = np.asarray(xi, dtype=float).reshape(-1)
    if values.size != nodes.size:
        raise PracmaError("Arguments 'x' and 'y' must be vectors of the same length.")
    if nodes.size <= 1:
        raise PracmaError("Arguments 'x', 'y' must have at least a length >= 2.")
    if np.min(points) < np.min(nodes) or np.max(points) > np.max(nodes):
        raise PracmaError("Points 'xi' outside of range of argument 'x'.")
    try:
        method = match_arg(method, ["linear", "constant", "nearest", "spline", "cubic"])
    except PracmaError:
        warnings.warn("Unknown method: will use 'linear' interpolation.", stacklevel=2)
        method = "linear"
    if bool(is_sorted(nodes)[0] != 1):
        warnings.warn("Points in argument in 'x' unsorted; will be sorted.", stacklevel=2)
        order = np.argsort(nodes, kind="mergesort")
        nodes = nodes[order]
        values = values[order]
    if np.unique(nodes).size != nodes.size:
        warnings.warn("There are duplicated values in 'x'; mean will be tried.", stacklevel=2)
    if method in ("constant", "linear"):
        return approx(nodes, values, points, method=method)
    if method == "nearest":
        n = nodes.size
        expanded_x = np.concatenate([nodes[:1], (nodes[1:] + nodes[:-1]) / 2, nodes[-1:]])
        expanded_y = np.concatenate([values, values[-1:]])
        return approx(expanded_x, expanded_y, points, method="constant")
    if method == "spline":
        return _ml_spline(nodes, values, points)
    if method == "cubic":
        return pchip(nodes, values, points)
    raise PracmaError(f"Method {method} not yet implemented.")


def interp2(x, y, Z, xp, yp, method="linear"):
    stopifnot(is_numeric_value(x), "is.numeric(x)")
    stopifnot(is_numeric_value(y), "is.numeric(y)")
    stopifnot(is_numeric_value(Z), "is.numeric(Z)")
    stopifnot(is_numeric_value(xp), "is.numeric(xp)")
    stopifnot(is_numeric_value(yp), "is.numeric(yp)")
    stopifnot(is_r_matrix(Z), "is.matrix(Z)")
    x_nodes = np.asarray(x, dtype=float).reshape(-1)
    y_nodes = np.asarray(y, dtype=float).reshape(-1)
    grid = np.asarray(Z, dtype=float)
    x_points = np.asarray(xp, dtype=float).reshape(-1)
    y_points = np.asarray(yp, dtype=float).reshape(-1)
    if grid.shape[1] != x_nodes.size or grid.shape[0] != y_nodes.size:
        raise PracmaError("Required: 'length(x) = ncol(Z)' and 'length(y) = nrow(Z)'.")
    if y_points.size != x_points.size:
        raise PracmaError("Length of vectors 'xp' and 'yp' must be the same.")
    method = match_arg(method, ["linear", "nearest", "constant"])
    surface = grid.T
    values = np.zeros(x_points.size)
    x_index = find_interval(x_points, x_nodes)
    y_index = find_interval(y_points, y_nodes)
    outside = (x_points < np.min(x_nodes)) | (x_points > np.max(x_nodes)) | (y_points < np.min(y_nodes)) | (
        y_points > np.max(y_nodes)
    )
    x_count = x_nodes.size
    y_count = y_nodes.size
    for k in range(x_points.size):
        if outside[k]:
            values[k] = np.nan
            continue
        i = int(x_index[k])
        j = int(y_index[k])
        if method == "linear":
            if i == x_count:
                i -= 1
            if j == y_count:
                j -= 1
            design = np.array(
                [
                    [1, x_nodes[i - 1], y_nodes[j - 1], x_nodes[i - 1] * y_nodes[j - 1]],
                    [1, x_nodes[i - 1], y_nodes[j], x_nodes[i - 1] * y_nodes[j]],
                    [1, x_nodes[i], y_nodes[j - 1], x_nodes[i] * y_nodes[j - 1]],
                    [1, x_nodes[i], y_nodes[j], x_nodes[i] * y_nodes[j]],
                ]
            )
            sample = np.array(
                [
                    surface[i - 1, j - 1],
                    surface[i - 1, j],
                    surface[i, j - 1],
                    surface[i, j],
                ]
            )
            weights = np.linalg.solve(design, sample)
            query = np.array([1, x_points[k], y_points[k], x_points[k] * y_points[k]])
            values[k] = np.sum(weights * query)
        elif method == "constant":
            values[k] = surface[i - 1, j - 1]
        else:
            if i == x_count:
                i -= 1
            if j == y_count:
                j -= 1
            if x_points[k] <= (x_nodes[i - 1] + x_nodes[i]) / 2:
                values[k] = surface[i - 1, j - 1] if y_points[k] <= (y_nodes[j - 1] + y_nodes[j]) / 2 else surface[i - 1, j]
            else:
                values[k] = surface[i, j - 1] if y_points[k] <= (y_nodes[j - 1] + y_nodes[j]) / 2 else surface[i, j]
    return values


def spinterp(x, y, xp):
    stopifnot(is_numeric_value(x), "is.numeric(x)")
    stopifnot(is_numeric_value(y), "is.numeric(y)")
    stopifnot(is_numeric_value(xp), "is.numeric(xp)")
    stopifnot(is_r_vector(x), "is.vector(x)")
    stopifnot(is_r_vector(y), "is.vector(y)")
    stopifnot(is_r_vector(xp), "is.vector(xp)")
    nodes = np.asarray(x, dtype=float).reshape(-1)
    values = np.asarray(y, dtype=float).reshape(-1)
    points = np.asarray(xp, dtype=float).reshape(-1)
    n = nodes.size
    if n <= 3:
        raise PracmaError("Length of arguments 'x', 'y' must be greater than 3.")
    if values.size != n:
        raise PracmaError("Arguments 'x', 'y' must be vectors of the same length.")
    if np.any(np.isnan(values)):
        raise PracmaError("NAs are not allowed in argument 'y'.")
    steps = np.diff(nodes)
    changes = np.diff(values)
    if np.any(steps <= 0):
        raise PracmaError("Argument 'x' must be a sorted list af real values.")
    if np.any(changes < 0):
        raise PracmaError("Argument 'y' must be monotonically increasing.")
    delta = changes / steps
    second = np.diff(delta)
    convex = bool(np.all(second > 0))
    slopes = np.full(n, np.nan)
    slopes[0] = delta[0]
    slopes[n - 1] = delta[n - 2]
    for j in range(1, n - 1):
        if convex:
            slopes[j] = (steps[j] + steps[j - 1]) / (steps[j] / delta[j - 1] + steps[j - 1] / delta[j])
        else:
            slopes[j] = (delta[j - 1] ** steps[j] * delta[j] ** steps[j - 1]) ** (1 / (steps[j - 1] + steps[j]))
    ratio = np.full(n - 1, 3.0)
    nonzero = which_index(delta != 0)
    if nonzero.size:
        ratio[nonzero - 1] = (slopes[nonzero - 1] + slopes[nonzero]) / delta[nonzero - 1]
    result = np.full(points.size, np.nan)
    intervals = find_interval(points, nodes)
    for j, i in enumerate(intervals):
        if i < n:
            theta = (points[j] - nodes[i - 1]) / steps[i - 1]
            numerator = (
                values[i] * theta**3
                + (ratio[i - 1] * values[i] - steps[i - 1] * slopes[i]) * theta**2 * (1 - theta)
                + (ratio[i - 1] * values[i - 1] + steps[i - 1] * slopes[i - 1]) * theta * (1 - theta) ** 2
                + values[i - 1] * (1 - theta) ** 3
            )
            denominator = 1 + (ratio[i - 1] - 3) * theta * (1 - theta)
            result[j] = numerator / denominator
        else:
            result[j] = values[n - 1]
    return result


def akimaInterp(x, y, xi):
    stopifnot(is_numeric_value(x), "is.numeric(x)")
    stopifnot(is_numeric_value(y), "is.numeric(y)")
    stopifnot(is_numeric_value(xi), "is.numeric(xi)")
    stopifnot(is_r_vector(x), "is.vector(x)")
    stopifnot(is_r_vector(y), "is.vector(y)")
    stopifnot(is_r_vector(xi), "is.vector(xi)")
    nodes = np.asarray(x, dtype=float).reshape(-1)
    values = np.asarray(y, dtype=float).reshape(-1)
    points = np.asarray(xi, dtype=float).reshape(-1)
    n = nodes.size
    if values.size != n:
        raise PracmaError("Vectors 'x' and 'y' must be of the same length.")
    steps = np.diff(nodes)
    if np.any(steps <= 0):
        raise PracmaError("Argument 'x' must be an in strictly ascending order.")
    if np.any(points < nodes[0]) or np.any(points > nodes[n - 1]):
        raise PracmaError("All points in 'xi' must lie between x[1] and x[n].")
    slopes = np.diff(values) / steps
    left = 2 * slopes[0] - slopes[1]
    left2 = 2 * left - slopes[0]
    right = 2 * slopes[n - 2] - slopes[n - 3]
    right2 = 2 * right - slopes[n - 2]
    extended = np.concatenate([np.array([left2, left]), slopes, np.array([right, right2])])
    differences = np.abs(np.diff(extended))
    f1 = r_get(differences, r_colon(3, n + 2))
    f2 = r_get(differences, r_colon(1, n))
    total = f1 + f2
    selected = which_index(total > 1e-8 * np.max(total))
    weights = r_get(extended, r_colon(2, n) + 1)
    if selected.size:
        update = (f1[selected - 1] * r_get(extended, selected + 1) + f2[selected - 1] * r_get(extended, selected + 2)) / total[
            selected - 1
        ]
        weights = r_set(weights, selected, update)
    left_w = r_get(weights, r_colon(1, n) - 1)
    right_w = r_get(weights, r_colon(2, n))
    cubic = (3 * slopes - 2 * left_w - right_w) / steps
    quartic = (left_w + right_w - 2 * slopes) / steps**2
    bins = np.minimum(find_interval(points, nodes), n - 1)
    shift = points - nodes[bins - 1]
    return ((shift * quartic[bins - 1] + cubic[bins - 1]) * shift + weights[bins - 1]) * shift + values[bins - 1]


def mkpp(x, P):
    stopifnot(is_numeric_value(x), "is.numeric(x)")
    stopifnot(is_numeric_value(P), "is.numeric(P)")
    breaks = np.asarray(x, dtype=float).reshape(-1)
    if not is_r_vector(x) or not bool(is_sorted(breaks)[0] == 1):
        raise PracmaError("Argument 'x' must be a sorted, finite numeric vector.")
    coefs = np.asarray(P, dtype=float)
    if coefs.ndim == 1:
        coefs = coefs.reshape(1, -1)
    pieces = coefs.shape[0]
    if breaks.size != pieces + 1:
        raise PracmaError("Length of 'x' must be equal to 'nrow(P)+1'.")
    return {
        "breaks": breaks,
        "coefs": coefs,
        "pieces": np.array([pieces]),
        "order": np.array([coefs.shape[1]]),
        "dim": np.array([1.0]),
        "class": "pp",
    }


def ppval(pp, xx):
    stopifnot(is_numeric_value(xx), "is.numeric(xx)")
    points = np.asarray(xx, dtype=float).reshape(-1)
    stopifnot(np.any(~np.isnan(points)), "any(!is.na(xx))")
    if not isinstance(pp, dict) or pp.get("class") != "pp":
        raise PracmaError("Argument 'pp' must be piecewise polynomial structure.")
    result = np.full(points.size, np.nan)
    breaks = np.asarray(pp["breaks"], dtype=float).reshape(-1)
    intervals = find_interval(points, breaks)
    intervals[intervals == 0] = 1
    intervals[intervals == breaks.size] = breaks.size - 1
    coefs = np.asarray(pp["coefs"], dtype=float)
    for i in range(breaks.size - 1):
        chosen = np.where(intervals == i + 1)[0]
        if chosen.size == 0:
            continue
        result[chosen] = polyval(coefs[i, :], points[chosen] - breaks[i])
    return result


def cubicspline(x, y, xi=None, endp2nd=False, der=None):
    nodes = np.asarray(x, dtype=float).reshape(-1)
    values = np.asarray(y, dtype=float).reshape(-1)
    if der is None:
        der = np.array([0.0, 0.0])
    ends = np.asarray(der, dtype=float).reshape(-1)
    n = nodes.size
    steps = nodes[1:] - nodes[:-1]
    diagonal = 2 * np.concatenate([steps[:1], steps[:-1] + steps[1:], steps[-1:]])
    system = Diag(diagonal) + Diag(steps, -1) + Diag(steps, 1)
    divided = (values[1:] - values[:-1]) / steps
    rhs = 3 * (divided[1:] - divided[:-1])
    if endp2nd:
        system[0, 0] = 2 * steps[0]
        system[0, 1] = steps[0]
        system[n - 1, n - 1] = 2 * steps[n - 2]
        system[n - 2, n - 3] = steps[n - 2]
        rhs = np.concatenate([np.array([3 * (divided[0] - ends[0])]), rhs, np.array([3 * (ends[1] - divided[n - 2])])])
    else:
        system[0, :] = 0
        system[0, 0] = 1
        system[n - 1, :] = 0
        system[n - 1, n - 1] = 1
        rhs = np.concatenate([np.array([ends[0]]), rhs, np.array([ends[1]])])
    sheet = zeros(n, 4)
    sheet[:, 2] = np.linalg.solve(system, rhs)
    for m in range(n - 1):
        sheet[m, 3] = (sheet[m + 1, 2] - sheet[m, 2]) / 3 / steps[m]
        sheet[m, 1] = divided[m] - steps[m] / 3 * (sheet[m + 1, 2] + 2 * sheet[m, 2])
        sheet[m, 0] = values[m]
    coefs = sheet[: n - 1, ::-1]
    piece = mkpp(nodes, coefs)
    if xi is None:
        return piece
    return ppval(piece, xi)


def ppfit(x, y, xi, method="linear"):
    stopifnot(is_numeric_value(x), "is.numeric(x)")
    stopifnot(is_numeric_value(y), "is.numeric(y)")
    stopifnot(is_numeric_value(xi), "is.numeric(xi)")
    nodes = np.asarray(x, dtype=float).reshape(-1)
    values = np.asarray(y, dtype=float).reshape(-1)
    breaks = np.asarray(xi, dtype=float).reshape(-1)
    if nodes.size != values.size or nodes.size <= 1:
        raise PracmaError("Length of 'x' and 'y' must be equal and greater than 1.")
    method = match_arg(method, ["linear", "cubic"])
    start = interp1(nodes, values, breaks, method=method)
    inside = finds((nodes >= breaks[0]) & (nodes <= breaks[-1]))

    def objective(yi):
        return float(np.sum((interp1(breaks, yi, nodes[inside.astype(int) - 1], method) - values[inside.astype(int) - 1]) ** 2))

    fitted = nelder_mead(objective, start)
    pieces = breaks.size - 1
    if method == "linear":
        coefs = np.full((pieces, 2), np.nan)
        for i in range(pieces):
            coefs[i, :] = [
                (fitted[i + 1] - fitted[i]) / (breaks[i + 1] - breaks[i]),
                fitted[i],
            ]
        return mkpp(breaks, coefs)
    if method == "cubic":
        return cubicspline(breaks, fitted)
    raise PracmaError("Unknown method: must be 'linear' or 'cubic'.")
