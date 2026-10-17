"""Distances and similarities from proxy.

One matrix returns the lower triangle in ``stats::dist`` order. Two
matrices return one row per row of ``x`` and one column per row of ``y``.
"""

from __future__ import annotations

import math

from proxy.measures import (
    BINARY,
    VECTOR,
    abcd,
    canberra,
    check_unit_interval,
    cosine,
    euclidean,
    extended_binary,
    find_measure,
    fuzzy_jaccard,
    gower_pair,
    gower_scale,
    jaccard,
    mahalanobis_pair,
    manhattan,
    minkowski,
    pr_DB,
    supremum,
    _column_covariance,
    _invert,
)

__all__ = [
    "dist",
    "simil",
    "as_dist",
    "as_simil",
    "as_matrix",
    "pr_simil2dist",
    "pr_dist2simil",
    "row_dist",
    "col_dist",
    "rowSums_dist",
    "colSums_dist",
    "rowMeans_dist",
    "colMeans_dist",
    "pr_DB",
]


class Proximity(list):
    """Lower triangle of an auto-distance or auto-similarity."""

    def __init__(self, values, size, method=None, kind="dist", diag=False, upper=False):
        super().__init__(values)
        self.size = size
        self.method = method
        self.kind = kind
        self.diag = diag
        self.upper = upper


class CrossProximity(list):
    """Rows of x by rows of y."""

    def __init__(self, rows, method=None, kind="dist"):
        super().__init__(rows)
        self.method = method
        self.kind = kind


class PairProximity(list):
    """One value per paired row. Not a dist triangle."""

    def __init__(self, values, method=None, kind="dist"):
        super().__init__(values)
        self.method = method
        self.kind = kind


def _cell(value):
    if isinstance(value, bool):
        return value
    if value is None:
        return float("nan")
    return float(value)


def _prepare(values):
    if values is None:
        return None
    if isinstance(values, (str, bytes)):
        raise ValueError("Can only handle data frames, vectors, matrices, and lists!")
    try:
        import numpy as np

        if isinstance(values, np.ndarray):
            if values.ndim == 1:
                values = values.reshape(-1, 1)
            if values.ndim != 2:
                raise ValueError("Can only handle data frames, vectors, matrices, and lists!")
            if values.dtype == bool:
                return [[bool(item) for item in row] for row in values.tolist()]
            return [[float(item) for item in row] for row in values.tolist()]
    except ImportError:
        pass
    rows = list(values)
    if not rows:
        return []
    first = rows[0]
    if isinstance(first, (str, bytes)) or not isinstance(first, (list, tuple)):
        return [[_cell(item)] for item in rows]
    return [[_cell(item) for item in row] for row in rows]


def _is_logical(rows):
    return bool(rows) and all(isinstance(value, bool) for row in rows for value in row)


def _as_float_rows(rows):
    out = []
    for row in rows:
        converted = []
        for value in row:
            if isinstance(value, bool):
                converted.append(1.0 if value else 0.0)
            else:
                converted.append(float(value))
        out.append(converted)
    return out


def _transpose(rows):
    if not rows:
        return []
    width = len(rows[0])
    return [[rows[i][j] for i in range(len(rows))] for j in range(width)]


def _same_width(rows, width, message):
    if any(len(row) != width for row in rows):
        raise ValueError(message)


def _power(value):
    if value is None:
        raise ValueError("Argument 'p' mandatory!")
    if isinstance(value, (list, tuple)):
        if len(value) < 1:
            raise ValueError("Argument 'p' mandatory!")
        value = value[0]
    try:
        value = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("Argument 'p' mandatory!") from exc
    if value <= 0:
        raise ValueError("'p' must not be smaller than 0.")
    return value


def _pair_function(entry, rows_x, rows_y, p, cov, weights, ranges, minimum):
    kind = entry.kind
    if kind == "levenshtein":
        raise RuntimeError("Need package 'cba'!")
    if kind == "minkowski":
        power = _power(p)
        return lambda left, right: minkowski(left, right, power), False
    if kind == "euclidean":
        return euclidean, False
    if kind == "manhattan":
        return manhattan, False
    if kind == "supremum":
        return supremum, False
    if kind == "canberra":
        return canberra, False
    if kind == "jaccard":
        return jaccard, False
    if kind == "fuzzy":
        check_unit_interval(rows_x, "x")
        if rows_y is not None:
            check_unit_interval(rows_y, "y")
        floated_x = _as_float_rows(rows_x)
        floated_y = None if rows_y is None else _as_float_rows(rows_y)
        return fuzzy_jaccard, False, floated_x, floated_y
    if kind == "cosine":
        return cosine, False
    if kind == "ejaccard":
        return lambda left, right: extended_binary(left, right, 1.0), False
    if kind == "edice":
        return lambda left, right: extended_binary(left, right, 2.0), False
    if kind == "binary":
        formula = BINARY[entry.canonical]

        def _binary(left, right, formula=formula):
            return formula(*abcd(left, right))

        return _binary, False
    if kind == "gower":
        scaled_x, scaled_y, used, logical = gower_scale(rows_x, rows_y, weights, ranges, minimum)

        def _gower(left, right, used=used, logical=logical):
            return gower_pair(left, right, used, logical)

        return _gower, False, scaled_x, scaled_y
    if kind == "mahalanobis":
        matrix = cov
        if matrix is None:
            source = rows_x if rows_y is None else rows_x
            if rows_y is not None and len(rows_y) != len(rows_x):
                raise ValueError("covariance of x and y needs the same number of rows")
            matrix = _column_covariance(_as_float_rows(source if rows_y is None else rows_x))
            if rows_y is not None and cov is None:
                # cov(x, y) when both are supplied and no cov was passed.
                # Same column count: column cross-covariance of paired rows.
                if len(rows_y) == len(rows_x):
                    matrix = _cross_covariance(rows_x, rows_y)
        inverse = _invert(matrix)

        def _mahal(left, right, inverse=inverse):
            return mahalanobis_pair(left, right, inverse)

        return _mahal, False
    if kind == "vector":
        return VECTOR[entry.canonical], False
    raise ValueError(f"distance method {entry.canonical} is not translated")


def _cross_covariance(rows_x, rows_y):
    """Column covariance of paired rows, the R cov(x, y) matrix."""
    n = len(rows_x)
    if n < 2:
        raise ValueError("covariance needs at least two rows")
    width = len(rows_x[0])
    left = _as_float_rows(rows_x)
    right = _as_float_rows(rows_y)
    mean_x = [0.0] * width
    mean_y = [0.0] * width
    for row in left:
        for j, value in enumerate(row):
            mean_x[j] += value
    for row in right:
        for j, value in enumerate(row):
            mean_y[j] += value
    mean_x = [value / n for value in mean_x]
    mean_y = [value / n for value in mean_y]
    cov = [[0.0] * width for _ in range(width)]
    for rx, ry in zip(left, right):
        dx = [rx[j] - mean_x[j] for j in range(width)]
        dy = [ry[j] - mean_y[j] for j in range(width)]
        for i in range(width):
            for j in range(width):
                cov[i][j] += dx[i] * dy[j]
    scale = n - 1
    return [[cov[i][j] / scale for j in range(width)] for i in range(width)]


def _loop(rows_x, rows_y, fn, pairwise):
    if not rows_x:
        return [], "auto", 0
    if rows_y is None:
        n = len(rows_x)
        out = []
        for j in range(n):
            for i in range(j + 1, n):
                out.append(fn(rows_x[i], rows_x[j]))
        return out, "auto", n
    if pairwise:
        if len(rows_x) != len(rows_y):
            raise ValueError("invalid number of rows for pairwise mode")
        return [fn(a, b) for a, b in zip(rows_x, rows_y)], "pair", len(rows_x)
    return [[fn(a, b) for b in rows_y] for a in rows_x], "cross", len(rows_x)


_CONVERT = {
    "simil2dist": lambda value: 1.0 - abs(value),
    "dist2simil": lambda value: _safe_recip(1.0 + value),
    "one_minus": lambda value: 1.0 - value,
}


def _map_values(obj, fn):
    if isinstance(obj, Proximity):
        return Proximity(
            [fn(value) for value in obj],
            size=obj.size,
            method=obj.method,
            kind=obj.kind,
            diag=obj.diag,
            upper=obj.upper,
        )
    if isinstance(obj, CrossProximity):
        return CrossProximity(
            [[fn(value) for value in row] for row in obj],
            method=obj.method,
            kind=obj.kind,
        )
    if isinstance(obj, PairProximity):
        return PairProximity([fn(value) for value in obj], method=obj.method, kind=obj.kind)
    if isinstance(obj, list):
        if obj and isinstance(obj[0], list):
            return [[fn(value) for value in row] for row in obj]
        return [fn(value) for value in obj]
    return fn(obj)


def _apply_mode(obj, mode):
    if mode not in _CONVERT:
        raise ValueError(f"unknown conversion {mode}")
    return _map_values(obj, _CONVERT[mode])


def _wrap(raw, shape, size, method, kind, diag, upper):
    if shape == "auto":
        return Proximity(raw, size=size, method=method, kind=kind, diag=diag, upper=upper)
    if shape == "cross":
        return CrossProximity(raw, method=method, kind=kind)
    return PairProximity(raw, method=method, kind=kind)


def _set_kind(obj, kind):
    obj.kind = kind
    return obj


def dist(
    x,
    y=None,
    method=None,
    diag=False,
    upper=False,
    pairwise=False,
    by_rows=True,
    convert_similarities=True,
    auto_convert_data_frames=True,
    p=None,
    cov=None,
    weights=None,
    ranges=None,
    **extra,
):
    """Pairwise proximity. Similarities are converted unless asked not to."""
    del auto_convert_data_frames
    if method is None and (callable(y) or isinstance(y, str)):
        method = y
        y = None
    minimum = extra.pop("min", None)

    rows_x = _prepare(x)
    rows_y = _prepare(y)
    logical = _is_logical(rows_x)
    if method is None:
        method = "Jaccard" if logical else "Euclidean"

    if callable(method):
        entry = None
        canonical = getattr(method, "__name__", "custom")

        def fn(left, right, method=method):
            return method(left, right)

        replaced = None
    else:
        if str(method).strip().lower() == "levenshtein":
            raise RuntimeError("Need package 'cba'!")
        entry = find_measure(method)
        if entry is None:
            raise ValueError(f"Entry {method!r} not in registry.")
        canonical = entry.canonical
        if not by_rows and entry.kind != "gower":
            rows_x = _transpose(rows_x)
            if rows_y is not None:
                rows_y = _transpose(rows_y)
        if not rows_x:
            return _wrap([], "auto" if rows_y is None else "cross", 0, canonical, "dist", diag, upper)
        width = len(rows_x[0])
        _same_width(rows_x, width, "rows must have the same length")
        if rows_y is not None:
            if not rows_y:
                raise ValueError("x and y must be conform in columns.")
            if len(rows_y[0]) != width:
                message = "x and y must be conform in columns." if by_rows else "x and y must be conform in rows."
                raise ValueError(message)
            _same_width(rows_y, width, message if False else "x and y must be conform in columns.")
        built = _pair_function(entry, rows_x, rows_y, p, cov, weights, ranges, minimum)
        if len(built) == 4:
            fn, _keep, rows_x, rows_y = built
        else:
            fn, _keep = built
        if entry.kind not in ("binary", "jaccard", "gower", "fuzzy"):
            if _is_logical(rows_x):
                rows_x = _as_float_rows(rows_x)
            elif rows_x and isinstance(rows_x[0][0], bool):
                rows_x = _as_float_rows(rows_x)
            if rows_y is not None and rows_y and isinstance(rows_y[0][0], bool):
                rows_y = _as_float_rows(rows_y)
        replaced = True

    if callable(method) and replaced is None:
        if not by_rows:
            rows_x = _transpose(rows_x)
            if rows_y is not None:
                rows_y = _transpose(rows_y)
        if rows_x and isinstance(rows_x[0][0], bool):
            rows_x = _as_float_rows(rows_x)
        if rows_y is not None and rows_y and isinstance(rows_y[0][0], bool):
            rows_y = _as_float_rows(rows_y)

    if not rows_x:
        shape = "auto" if rows_y is None else "cross"
        return _wrap([], shape, 0, canonical, "dist", diag, upper)

    raw, shape, size = _loop(rows_x, rows_y, fn, pairwise and rows_y is not None)
    result = _wrap(raw, shape, size, canonical, "dist", diag, upper)
    if entry is not None and not entry.distance and convert_similarities is not False:
        result = _convert_with(result, convert_similarities, entry.convert)
        _set_kind(result, "dist")
    return result


def _convert_with(obj, flag, mode):
    if flag is False:
        return obj
    if callable(flag):
        return flag(obj)
    return _apply_mode(obj, mode)


def simil(
    x,
    y=None,
    method=None,
    diag=False,
    upper=False,
    pairwise=False,
    by_rows=True,
    convert_distances=True,
    auto_convert_data_frames=True,
    p=None,
    cov=None,
    weights=None,
    ranges=None,
    **extra,
):
    """Pairwise similarity. Distances are converted unless asked not to."""
    if method is None and (callable(y) or isinstance(y, str)):
        method = y
        y = None
    if method is None:
        rows = _prepare(x)
        method = "Jaccard" if _is_logical(rows) else "correlation"
    result = dist(
        x,
        y,
        method,
        diag=diag,
        upper=upper,
        pairwise=pairwise,
        by_rows=by_rows,
        convert_similarities=False,
        auto_convert_data_frames=auto_convert_data_frames,
        p=p,
        cov=cov,
        weights=weights,
        ranges=ranges,
        **extra,
    )
    entry = None if result.method is None else find_measure(result.method)
    if entry is not None and entry.distance and convert_distances is not False:
        result = _convert_with(result, convert_distances, entry.convert or "dist2simil")
    _set_kind(result, "simil")
    return result


def pr_simil2dist(x):
    """``1 - abs(x)``, keeping the proximity class."""
    return _map_values(x, lambda value: 1.0 - abs(value))


def _safe_recip(value):
    try:
        return 1.0 / value
    except ZeroDivisionError:
        if value == 0.0:
            return float("inf")
        return float("nan")


def pr_dist2simil(x):
    """``1 / (1 + x)``, keeping the proximity class."""
    return _map_values(x, lambda value: _safe_recip(1.0 + value))


def _lower_triangle(matrix):
    n = len(matrix)
    if any(len(row) != n for row in matrix):
        raise ValueError("non-square matrix")
    out = []
    for j in range(n):
        for i in range(j + 1, n):
            out.append(matrix[i][j])
    return out, n


def as_dist(x, FUN=None):
    """Distance from a similarity, a dist, or the lower triangle of a matrix."""
    if isinstance(x, (Proximity, CrossProximity, PairProximity)) and x.kind == "dist":
        return x
    if isinstance(x, (Proximity, CrossProximity, PairProximity)) and x.kind == "simil":
        _set_kind(x, "dist")
        if FUN is not None:
            return FUN(x)
        entry = find_measure(x.method) if x.method else None
        mode = entry.convert if entry is not None and entry.convert else "simil2dist"
        return _apply_mode(x, mode)
    rows = _prepare(x)
    if rows and isinstance(rows[0][0], (list, tuple)):
        raise ValueError("as.dist expects a square matrix or a proximity")
    if rows and not isinstance(rows[0], list):
        raise ValueError("as.dist expects a square matrix or a proximity")
    # _prepare already returns rows. A square numeric matrix is a list of rows.
    if rows and isinstance(rows[0], list) and not isinstance(rows[0][0], (list, tuple)):
        # Could be a matrix. If every row has the same length equal to the
        # number of rows, take the lower triangle. A Proximity was handled.
        if len(rows) == len(rows[0]):
            values, size = _lower_triangle(rows)
            return Proximity(values, size=size, method=None, kind="dist")
    raise ValueError("as.dist expects a square matrix or a proximity")


def as_simil(x, FUN=None):
    """Similarity from a dist, a similarity, or the lower triangle of a matrix."""
    if isinstance(x, (Proximity, CrossProximity, PairProximity)) and x.kind == "simil":
        return x
    if isinstance(x, (Proximity, CrossProximity, PairProximity)) and x.kind == "dist":
        _set_kind(x, "simil")
        if FUN is not None:
            return FUN(x)
        entry = find_measure(x.method) if x.method else None
        mode = entry.convert if entry is not None and entry.convert else "dist2simil"
        return _apply_mode(x, mode)
    rows = _prepare(x)
    if not rows or not isinstance(rows[0], list):
        raise ValueError("as.simil expects a square matrix or a proximity")
    if len(rows) != len(rows[0]):
        raise ValueError("non-square matrix")
    values, size = _lower_triangle(rows)
    return Proximity(values, size=size, method=None, kind="simil")


def _expand(values, size, diag):
    matrix = [[0.0 for _ in range(size)] for _ in range(size)]
    cursor = 0
    for j in range(size):
        for i in range(j + 1, size):
            matrix[i][j] = values[cursor]
            matrix[j][i] = values[cursor]
            cursor += 1
    diagonal = _recycle_diag(diag, size)
    for i in range(size):
        matrix[i][i] = diagonal[i]
    return matrix


def _recycle_diag(diag, size):
    if isinstance(diag, (list, tuple)):
        if not diag:
            raise ValueError("replacement diagonal has length zero")
        return [diag[i % len(diag)] for i in range(size)]
    return [diag] * size


def as_matrix(x, diag=None, **kwargs):
    """Expand a dist or simil triangle. A cross-proximity is already a matrix."""
    if isinstance(x, Proximity):
        if diag is None:
            diag = float("nan") if x.kind == "simil" else 0.0
        return _expand(list(x), x.size, diag)
    if isinstance(x, CrossProximity):
        return [list(row) for row in x]
    if isinstance(x, PairProximity):
        return [[value] for value in x]
    rows = _prepare(x)
    if rows and isinstance(rows[0], list):
        return rows
    return [[value] for value in rows]


def _triangle(x):
    if isinstance(x, Proximity):
        n = x.size
        values = list(x)
        if n * (n - 1) // 2 != len(values):
            raise ValueError("'x' invalid length")
        return n, values
    if isinstance(x, (list, tuple)) and (not x or not isinstance(x[0], (list, tuple))):
        length = len(x)
        n = int(math.sqrt(2 * length)) + 1
        if n * (n - 1) // 2 != length:
            raise ValueError("'x' invalid length")
        return n, list(x)
    raise ValueError("'x' not of class dist")


def row_dist(x):
    """1-based row index of each stored lower-triangle entry."""
    n, _values = _triangle(x)
    out = []
    for j in range(1, n):
        for i in range(j + 1, n + 1):
            out.append(i)
    return out


def col_dist(x):
    """1-based column index of each stored lower-triangle entry."""
    n, _values = _triangle(x)
    out = []
    for j in range(1, n):
        for i in range(j + 1, n + 1):
            out.append(j)
    return out


def _flag(name, default, kwargs):
    if name in kwargs:
        return kwargs[name]
    dotted = name.replace("_", ".")
    if dotted in kwargs:
        return kwargs[dotted]
    return default


def rowSums_dist(x, na_rm=False, **kwargs):
    """Row sums of a dist triangle. A non-finite value stops that row."""
    na_rm = _flag("na_rm", na_rm, kwargs)
    n, values = _triangle(x)
    sums = [0.0] * n
    cursor = 0
    for i in range(n - 1):
        for j in range(i + 1, n):
            z = values[cursor]
            cursor += 1
            if not math.isfinite(z):
                if math.isnan(z):
                    if na_rm:
                        continue
                    sums[i] = float("nan")
                    sums[j] = float("nan")
                else:
                    sums[i] = z
                    sums[j] = z
                break
            sums[i] += z
            sums[j] += z
    return sums


def colSums_dist(x, na_rm=False, **kwargs):
    """Column sums. The triangle is symmetric, so this matches the row sums."""
    return rowSums_dist(x, na_rm=na_rm, **kwargs)


def rowMeans_dist(x, na_rm=False, diag=True, **kwargs):
    """Row means of a dist triangle. ``diag`` counts the zero diagonal."""
    na_rm = _flag("na_rm", na_rm, kwargs)
    if "diag" in kwargs:
        diag = kwargs["diag"]
    if not isinstance(diag, bool):
        raise ValueError("'diag' not of type logical")
    n, values = _triangle(x)
    sums = rowSums_dist(values if not isinstance(x, Proximity) else x, na_rm=na_rm)
    # rowSums on a plain list infers size. Passing values loses nothing.
    if not isinstance(x, Proximity):
        sums = rowSums_dist(values, na_rm=na_rm)
    else:
        sums = rowSums_dist(x, na_rm=na_rm)
    if na_rm:
        replaced = [value if math.isnan(value) else 1.0 for value in values]
        counts = rowSums_dist(replaced, na_rm=True)
        extra = 1.0 if diag else 0.0
        return [sums[i] / (counts[i] + extra) for i in range(n)]
    denom = n - (0.0 if diag else 1.0)
    return [value / denom for value in sums]


def colMeans_dist(x, na_rm=False, diag=True, **kwargs):
    """Column means. The triangle is symmetric, so this matches the row means."""
    return rowMeans_dist(x, na_rm=na_rm, diag=diag, **kwargs)
