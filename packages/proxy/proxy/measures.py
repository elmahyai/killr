"""Pairwise measures from proxy 0.4-29.

Matrix methods that the package runs in C are the C formulas: missing
pairs are skipped, and Euclidean, Manhattan, Canberra, and Minkowski
scale the sum by the share of columns that remain. The other measures
are the R functions. ``min`` and ``max`` in Wave and Soergel are the
scalar reductions, and Kullback is applied as ``f(row i, row j)`` with
``i > j`` in the stored triangle.
"""

from __future__ import annotations

import math
import sys

DBL_MIN = sys.float_info.min


class Measure:
    def __init__(self, names, distance, convert, kind):
        self.names = tuple(names)
        self.distance = bool(distance)
        # simil2dist, dist2simil, or one_minus. Used when dist() is given
        # a similarity, when simil() is given a distance, and by as.dist
        # and as.simil.
        self.convert = convert
        self.kind = kind

    @property
    def canonical(self):
        return self.names[0]


def _missing(value):
    return value is None or (isinstance(value, float) and math.isnan(value))


def _as_bool(value):
    if _missing(value):
        return None
    if isinstance(value, bool):
        return value
    return value != 0


def r_div(left, right):
    """Float division. This Python raises on a zero divisor; R returns NaN or Inf."""
    left = float(left)
    right = float(right)
    try:
        return left / right
    except ZeroDivisionError:
        if math.isnan(left) or math.isnan(right) or left == 0.0:
            return float("nan")
        return math.copysign(float("inf"), left)


def r_log(value):
    if value == 0:
        return float("-inf")
    if value < 0 or (isinstance(value, float) and math.isnan(value)):
        return float("nan")
    return math.log(value)


def r_sqrt(value):
    try:
        if value < 0:
            return float("nan")
    except TypeError:
        return float("nan")
    try:
        return math.sqrt(value)
    except ValueError:
        return float("nan")


def r_acos(value):
    if value < -1.0 or value > 1.0 or (isinstance(value, float) and math.isnan(value)):
        return float("nan")
    return math.acos(value)


def r_min(values):
    found = None
    for value in values:
        if _missing(value):
            return float("nan")
        if found is None or value < found:
            found = value
    return found


def r_max(values):
    found = None
    for value in values:
        if _missing(value):
            return float("nan")
        if found is None or value > found:
            found = value
    return found


def _dot(left, right):
    total = 0.0
    for a, b in zip(left, right):
        total += a * b
    return total


def _scale(total, count, width):
    if count == 0:
        return None
    if count != width:
        total = total / (count / float(width))
    return total


def euclidean(left, right):
    total = 0.0
    count = 0
    width = len(left)
    for a, b in zip(left, right):
        if _missing(a) or _missing(b):
            continue
        dev = a - b
        if _missing(dev):
            continue
        total += dev * dev
        count += 1
    scaled = _scale(total, count, width)
    if scaled is None:
        return float("nan")
    return math.sqrt(scaled)


def manhattan(left, right):
    total = 0.0
    count = 0
    width = len(left)
    for a, b in zip(left, right):
        if _missing(a) or _missing(b):
            continue
        dev = abs(a - b)
        if _missing(dev):
            continue
        total += dev
        count += 1
    scaled = _scale(total, count, width)
    if scaled is None:
        return float("nan")
    return scaled


def supremum(left, right):
    found = None
    for a, b in zip(left, right):
        if _missing(a) or _missing(b):
            continue
        dev = abs(a - b)
        if _missing(dev):
            continue
        if found is None or dev > found:
            found = dev
    if found is None:
        return float("nan")
    return found


def minkowski(left, right, power):
    total = 0.0
    count = 0
    width = len(left)
    for a, b in zip(left, right):
        if _missing(a) or _missing(b):
            continue
        dev = a - b
        if _missing(dev):
            continue
        total += math.pow(abs(dev), power)
        count += 1
    scaled = _scale(total, count, width)
    if scaled is None:
        return float("nan")
    return math.pow(scaled, 1.0 / power)


def canberra(left, right):
    total = 0.0
    count = 0
    width = len(left)
    for a, b in zip(left, right):
        if _missing(a) or _missing(b):
            continue
        sm = abs(a + b)
        diff = abs(a - b)
        if sm > DBL_MIN or diff > DBL_MIN:
            dev = diff / sm if sm != 0.0 else float("inf")
            if math.isnan(dev):
                if (not math.isfinite(diff)) and diff == sm:
                    dev = 1.0
                else:
                    continue
            total += dev
            count += 1
    scaled = _scale(total, count, width)
    if scaled is None:
        return float("nan")
    return scaled


def jaccard(left, right):
    """C binary distance, then one minus that value."""
    total = 0
    count = 0
    mismatch = 0
    for a, b in zip(left, right):
        fa, fb = _as_bool(a), _as_bool(b)
        if fa is None or fb is None:
            continue
        total += 1
        if fa or fb:
            count += 1
            if not (fa and fb):
                mismatch += 1
    if total == 0:
        return float("nan")
    if count == 0:
        return 1.0
    return 1.0 - (mismatch / count)


def fuzzy_jaccard(left, right):
    """C fuzzy Jaccard, already a distance: 1 - sum(min) / sum(max)."""
    small = 0.0
    large = 0.0
    count = 0
    for a, b in zip(left, right):
        if not (math.isfinite(a) and math.isfinite(b)):
            continue
        if a > b:
            large += a
            small += b
        else:
            large += b
            small += a
        count += 1
    if count == 0:
        return float("nan")
    if not math.isfinite(small):
        return float("nan")
    if large == 0.0:
        ratio = float("nan")
    else:
        ratio = small / large
    if math.isnan(ratio):
        return 0.0
    return 1.0 - ratio


def cosine(left, right):
    xy = xx = yy = 0.0
    count = 0
    for a, b in zip(left, right):
        if _missing(a) or _missing(b):
            continue
        prod = a * b
        if _missing(prod):
            continue
        xy += prod
        xx += a * a
        yy += b * b
        count += 1
    if count == 0 or not math.isfinite(xy):
        return float("nan")
    result = r_div(xy, math.sqrt(xx) * math.sqrt(yy))
    if math.isnan(result):
        if xx < DBL_MIN and yy < DBL_MIN:
            return 1.0
        if xx < DBL_MIN or yy < DBL_MIN:
            return 0.0
        return float("nan")
    return result


def extended_binary(left, right, divisor):
    total = 0.0
    xy = 0.0
    count = 0
    for a, b in zip(left, right):
        if _missing(a) or _missing(b):
            continue
        dev = a - b
        prod = a * b
        if _missing(dev) or _missing(prod):
            continue
        total += dev * dev
        xy += prod
        count += 1
    if count == 0 or not math.isfinite(xy):
        return float("nan")
    total = total / divisor + xy
    result = r_div(xy, total)
    if math.isnan(result):
        if total < DBL_MIN:
            return 1.0
        return float("nan")
    return result


def abcd(left, right):
    both = left_only = right_only = used = 0
    for a, b in zip(left, right):
        fa, fb = _as_bool(a), _as_bool(b)
        if fa is None or fb is None:
            continue
        used += 1
        if fa and fb:
            both += 1
        elif fa and not fb:
            left_only += 1
        elif (not fa) and fb:
            right_only += 1
    neither = 0 if used == 0 else used - both - left_only - right_only
    return both, left_only, right_only, neither, used


def kulczynski1(a, b, c, d, n):
    return r_div(a, b + c)


def kulczynski2(a, b, c, d, n):
    return (r_div(a, a + b) + r_div(a, a + c)) / 2.0


def mountford(a, b, c, d, n):
    return r_div(2 * a, a * (b + c) + 2 * b * c)


def fager(a, b, c, d, n):
    return r_div(a, math.sqrt((a + b) * (a + c))) - math.sqrt(a + c) / 2.0


def russel(a, b, c, d, n):
    return r_div(a, n)


def simple_matching(a, b, c, d, n):
    return r_div(a + d, n)


def hamman(a, b, c, d, n):
    return r_div(a + d - b - c, n)


def faith(a, b, c, d, n):
    return r_div(a + d / 2.0, n)


def tanimoto(a, b, c, d, n):
    return r_div(a + d, a + 2 * (b + c) + d)


def dice(a, b, c, d, n):
    return r_div(2 * a, 2 * a + b + c)


def phi(a, b, c, d, n):
    num = a * d - b * c
    den = (
        math.sqrt(a + b)
        * math.sqrt(c + d)
        * math.sqrt(a + c)
        * math.sqrt(b + d)
    )
    return r_div(num, den)


def stiles(a, b, c, d, n):
    return (
        r_log(n)
        + 2.0 * r_log(abs(a * d - b * c) - 0.5 * n)
        - r_log(a + b)
        - r_log(c + d)
        - r_log(a + c)
        - r_log(b + d)
    )


def michael(a, b, c, d, n):
    return r_div(
        4 * (a * d - b * c),
        (a + d) * (a + d) + (b + c) * (b + c),
    )


def mozley(a, b, c, d, n):
    return r_div(a * n, (a + b) * (a + c))


def yule(a, b, c, d, n):
    ad = a * d
    bc = b * c
    return r_div(ad - bc, ad + bc)


def yule2(a, b, c, d, n):
    ad = a * d
    bc = b * c
    return r_div(math.sqrt(ad) - math.sqrt(bc), math.sqrt(ad) + math.sqrt(bc))


def ochiai(a, b, c, d, n):
    return r_div(a, math.sqrt((a + b) * (a + c)))


def simpson(a, b, c, d, n):
    return r_div(a, min(a + b, a + c))


def braun_blanquet(a, b, c, d, n):
    return r_div(a, max(a + b, a + c))


def angular(left, right):
    xy = _dot(left, right)
    xx = _dot(left, left)
    yy = _dot(right, right)
    return 1.0 - r_acos(r_div(xy, math.sqrt(xx * yy))) / math.pi


def correlation(left, right):
    mx = sum(left) / len(left)
    my = sum(right) / len(right)
    xs = [a - mx for a in left]
    ys = [b - my for b in right]
    return r_div(_dot(xs, ys), math.sqrt(_dot(xs, xs) * _dot(ys, ys)))


def _counts(left, right):
    xs = sorted({value for value in left if not _missing(value)})
    ys = sorted({value for value in right if not _missing(value)})
    if not xs or not ys:
        return None
    xi = {value: index for index, value in enumerate(xs)}
    yi = {value: index for index, value in enumerate(ys)}
    table = [[0 for _ in ys] for _ in xs]
    for a, b in zip(left, right):
        if _missing(a) or _missing(b):
            continue
        table[xi[a]][yi[b]] += 1
    return table


def _chi_stat(table):
    nrow = len(table)
    ncol = len(table[0])
    row_sums = [float(sum(row)) for row in table]
    col_sums = [float(sum(table[i][j] for i in range(nrow))) for j in range(ncol)]
    total_n = float(sum(row_sums))
    chi = 0.0
    for j in range(ncol):
        for i in range(nrow):
            expected = r_div(row_sums[i] * col_sums[j], total_n)
            diff = table[i][j] - expected
            chi += r_div(diff * diff, expected)
    return chi, total_n, nrow, ncol


def chi_squared(left, right):
    table = _counts(left, right)
    if table is None:
        return float("nan")
    chi, _n, _nr, _nc = _chi_stat(table)
    return chi


def phi_squared(left, right):
    table = _counts(left, right)
    if table is None:
        return float("nan")
    chi, total_n, _nr, _nc = _chi_stat(table)
    return r_div(chi, total_n)


def tschuprow(left, right):
    table = _counts(left, right)
    if table is None:
        return float("nan")
    chi, total_n, nrow, ncol = _chi_stat(table)
    return r_sqrt(r_div(r_div(chi, total_n), math.sqrt((nrow - 1) * (ncol - 1))))


def cramer(left, right):
    table = _counts(left, right)
    if table is None:
        return float("nan")
    chi, total_n, nrow, ncol = _chi_stat(table)
    return r_sqrt(r_div(r_div(chi, total_n), min(nrow - 1, ncol - 1)))


def pearson(left, right):
    table = _counts(left, right)
    if table is None:
        return float("nan")
    chi, total_n, _nr, _nc = _chi_stat(table)
    return r_sqrt(r_div(chi, total_n + chi))


def bhattacharyya(left, right):
    total = 0.0
    for a, b in zip(left, right):
        dev = math.sqrt(a) - math.sqrt(b)
        total += dev * dev
    return math.sqrt(total)


def wave(left, right):
    values = list(left) + list(right)
    return 1.0 - r_div(r_min(values), r_max(values))


def divergence(left, right):
    total = 0.0
    for a, b in zip(left, right):
        value = r_div(math.pow(a - b, 2), math.pow(a + b, 2))
        if not math.isnan(value):
            total += value
    return total


def kullback(left, right):
    sum_left = sum(left)
    sum_right = sum(right)
    total = 0.0
    for a, b in zip(left, right):
        p = r_div(a, sum_left)
        q = r_div(b, sum_right)
        total += p * r_log(r_div(p, q))
    return total


def bray(left, right):
    num = 0.0
    den = 0.0
    for a, b in zip(left, right):
        num += abs(a - b)
        den += a + b
    return r_div(num, den)


def soergel(left, right):
    num = 0.0
    for a, b in zip(left, right):
        num += abs(a - b)
    return r_div(num, r_max(list(left) + list(right)))


def podani(left, right):
    agree = reverse = tied = mixed = 0
    n = len(left)
    for i in range(n - 1):
        for j in range(i + 1, n):
            agree += (left[i] < left[j] and right[i] < right[j]) or (
                left[i] > left[j] and right[i] > right[j]
            )
            reverse += (left[i] < left[j] and right[i] > right[j]) or (
                left[i] > left[j] and right[i] < right[j]
            )
            same = left[i] == left[j] and right[i] == right[j]
            zeros = left[i] == 0 and right[i] == 0
            positive = left[i] > 0 and right[i] > 0
            tied += same and (zeros or positive)
            zeros_among = (
                (left[i] == 0)
                + (left[j] == 0)
                + (right[i] == 0)
                + (right[j] == 0)
            )
            mixed += (left[i] == left[j] or right[i] == right[j]) and 0 < zeros_among < 4
    return 1.0 - r_div(2.0 * (agree - reverse + tied - mixed), n * (n - 1))


def chord(left, right):
    xy = _dot(left, right)
    xx = _dot(left, left)
    yy = _dot(right, right)
    return r_sqrt(2.0 * (1.0 - r_div(xy, math.sqrt(xx * yy))))


def geodesic(left, right):
    xy = _dot(left, right)
    xx = _dot(left, left)
    yy = _dot(right, right)
    return r_acos(r_div(xy, math.sqrt(xx * yy)))


def whittaker(left, right):
    sum_left = sum(left)
    sum_right = sum(right)
    total = 0.0
    for a, b in zip(left, right):
        total += abs(r_div(a, sum_left) - r_div(b, sum_right))
    return total / 2.0


def hellinger(left, right):
    sum_left = sum(left)
    sum_right = sum(right)
    total = 0.0
    for a, b in zip(left, right):
        dev = r_sqrt(r_div(a, sum_left)) - r_sqrt(r_div(b, sum_right))
        total += dev * dev
    return math.sqrt(total)


def gower_pair(left, right, weights, logical):
    num = 0.0
    den = 0.0
    for a, b, weight in zip(left, right, weights):
        if logical:
            if _missing(a) or _missing(b):
                continue
            fa, fb = bool(a), bool(b)
            if not fa and not fb:
                continue
            score = 1.0 if fa and fb else 0.0
        else:
            score = 1.0 - abs(a - b)
            if math.isnan(score):
                continue
        num += score * weight
        den += weight
    return r_div(num, den)


def mahalanobis_pair(left, right, inverse):
    diff = [a - b for a, b in zip(left, right)]
    width = len(diff)
    mixed = [
        sum(inverse[i][k] * diff[k] for k in range(width))
        for i in range(width)
    ]
    total = sum(mixed[i] * diff[i] for i in range(width))
    return math.sqrt(total)


def _column_covariance(rows):
    n = len(rows)
    if n < 2:
        raise ValueError("covariance needs at least two rows")
    width = len(rows[0])
    means = [0.0] * width
    for row in rows:
        for j, value in enumerate(row):
            means[j] += value
    means = [value / n for value in means]
    cov = [[0.0] * width for _ in range(width)]
    for row in rows:
        dev = [row[j] - means[j] for j in range(width)]
        for i in range(width):
            for j in range(width):
                cov[i][j] += dev[i] * dev[j]
    scale = n - 1
    return [[cov[i][j] / scale for j in range(width)] for i in range(width)]


def _invert(matrix):
    # Gaussian elimination on a copy. Diagonal covariances stay exact.
    # A pivot at machine epsilon times the matrix scale is the case R's
    # solve() reports as computationally singular.
    n = len(matrix)
    scale0 = 0.0
    for row in matrix:
        for value in row:
            scale0 = max(scale0, abs(float(value)))
    if scale0 == 0.0:
        raise ValueError("covariance matrix is singular")
    limit = sys.float_info.epsilon * scale0 * n
    aug = [list(map(float, row)) + [1.0 if i == j else 0.0 for j in range(n)] for i, row in enumerate(matrix)]
    for col in range(n):
        pivot = max(range(col, n), key=lambda r: abs(aug[r][col]))
        if abs(aug[pivot][col]) <= limit:
            raise ValueError("covariance matrix is singular")
        if pivot != col:
            aug[col], aug[pivot] = aug[pivot], aug[col]
        scale = aug[col][col]
        for j in range(2 * n):
            aug[col][j] /= scale
        for row in range(n):
            if row == col:
                continue
            factor = aug[row][col]
            if factor == 0.0:
                continue
            for j in range(2 * n):
                aug[row][j] -= factor * aug[col][j]
    return [row[n:] for row in aug]


def gower_scale(rows, other, weights, ranges, minimum):
    logical = bool(rows) and all(isinstance(value, bool) for row in rows for value in row)
    if logical:
        scaled = rows
        if other is not None:
            other_scaled = other
        else:
            other_scaled = None
        used = _recycle(weights, len(rows[0]) if rows else 0)
        return scaled, other_scaled, used, True

    rows = [[float(value) for value in row] for row in rows]
    if other is not None:
        other = [[float(value) for value in row] for row in other]
    width = len(rows[0]) if rows else 0
    if ranges is None or minimum is None:
        mins, maxs = _range_of(rows, other)
    else:
        mins = maxs = None
    if ranges is None:
        span = []
        for lo, hi in zip(mins, maxs):
            gap = hi - lo
            span.append(1.0 if gap == 0.0 else gap)
    else:
        span = _recycle(ranges, width)
    if minimum is None:
        base = mins
    else:
        base = _recycle(minimum, width)

    def _scale(block):
        return [
            [(value - base[j]) / span[j] for j, value in enumerate(row)]
            for row in block
        ]

    return _scale(rows), None if other is None else _scale(other), _recycle(weights, width), False


def _range_of(rows, other):
    width = len(rows[0])
    mins = [float("inf")] * width
    maxs = [float("-inf")] * width
    blocks = [rows] if other is None else [rows, other]
    for block in blocks:
        for row in block:
            for j, value in enumerate(row):
                if _missing(value):
                    continue
                if value < mins[j]:
                    mins[j] = value
                if value > maxs[j]:
                    maxs[j] = value
    return mins, maxs


def _recycle(values, width):
    if values is None:
        return [1.0] * width
    if isinstance(values, (int, float)) and not isinstance(values, bool):
        values = [float(values)]
    values = [float(value) for value in values]
    if not values:
        raise ValueError("replacement has length zero")
    return [values[i % len(values)] for i in range(width)]


def check_unit_interval(rows, label):
    for row in rows:
        for value in row:
            if _missing(value):
                continue
            number = float(value) if not isinstance(value, bool) else (1.0 if value else 0.0)
            if number < 0.0 or number > 1.0:
                raise ValueError(f"Valid range for fuzzy measure: 0 <= {label} <= 1")


BINARY = {
    "Kulczynski1": kulczynski1,
    "Kulczynski2": kulczynski2,
    "Mountford": mountford,
    "Fager": fager,
    "Russel": russel,
    "simple matching": simple_matching,
    "Hamman": hamman,
    "Faith": faith,
    "Tanimoto": tanimoto,
    "Dice": dice,
    "Phi": phi,
    "Stiles": stiles,
    "Michael": michael,
    "Mozley": mozley,
    "Yule": yule,
    "Yule2": yule2,
    "Ochiai": ochiai,
    "Simpson": simpson,
    "Braun-Blanquet": braun_blanquet,
}

VECTOR = {
    "angular": angular,
    "correlation": correlation,
    "Chi-squared": chi_squared,
    "Phi-squared": phi_squared,
    "Tschuprow": tschuprow,
    "Cramer": cramer,
    "Pearson": pearson,
    "Bhjattacharyya": bhattacharyya,
    "Wave": wave,
    "divergence": divergence,
    "Kullback": kullback,
    "Bray": bray,
    "Soergel": soergel,
    "Podani": podani,
    "Chord": chord,
    "Geodesic": geodesic,
    "Whittaker": whittaker,
    "Hellinger": hellinger,
}


def _build():
    s2d = "simil2dist"
    d2s = "dist2simil"
    one = "one_minus"
    rows = [
        (("Jaccard", "binary", "Reyssac", "Roux"), False, s2d, "jaccard"),
        (("Kulczynski1",), False, s2d, "binary"),
        (("Kulczynski2",), False, s2d, "binary"),
        (("Mountford",), False, s2d, "binary"),
        (("Fager", "McGowan"), False, s2d, "binary"),
        (("Russel", "Rao"), False, s2d, "binary"),
        (("simple matching", "Sokal/Michener"), False, s2d, "binary"),
        (("Hamman",), False, s2d, "binary"),
        (("Faith",), False, s2d, "binary"),
        (("Tanimoto", "Rogers"), False, s2d, "binary"),
        (("Dice", "Czekanowski", "Sorensen"), False, s2d, "binary"),
        (("Phi",), False, s2d, "binary"),
        (("Stiles",), False, s2d, "binary"),
        (("Michael",), False, s2d, "binary"),
        (("Mozley", "Margalef"), False, s2d, "binary"),
        (("Yule",), False, s2d, "binary"),
        (("Yule2",), False, s2d, "binary"),
        (("Ochiai",), False, s2d, "binary"),
        (("Simpson",), False, s2d, "binary"),
        (("Braun-Blanquet",), False, s2d, "binary"),
        (("cosine",), False, one, "cosine"),
        (("angular",), False, one, "vector"),
        (("eJaccard", "extended_Jaccard"), False, s2d, "ejaccard"),
        (("eDice", "extended_Dice", "eSorensen"), False, s2d, "edice"),
        (("correlation",), False, s2d, "vector"),
        (("Chi-squared",), False, s2d, "vector"),
        (("Phi-squared",), False, s2d, "vector"),
        (("Tschuprow",), False, s2d, "vector"),
        (("Cramer",), False, s2d, "vector"),
        (("Pearson", "contingency"), False, s2d, "vector"),
        (("Gower",), False, s2d, "gower"),
        (("Euclidean", "L2"), True, d2s, "euclidean"),
        (("Mahalanobis",), True, d2s, "mahalanobis"),
        (("Bhjattacharyya",), True, d2s, "vector"),
        (("Manhattan", "City-Block", "L1", "taxi"), True, d2s, "manhattan"),
        (("supremum", "max", "maximum", "Tschebyscheff", "Chebyshev"), True, d2s, "supremum"),
        (("Minkowski", "Lp"), True, d2s, "minkowski"),
        (("Canberra",), True, d2s, "canberra"),
        (("Wave", "Hedges"), True, d2s, "vector"),
        (("divergence",), True, d2s, "vector"),
        (("Kullback", "Leibler"), True, d2s, "vector"),
        (("Bray", "Curtis"), True, d2s, "vector"),
        (("Soergel",), True, d2s, "vector"),
        (("Levenshtein",), True, d2s, "levenshtein"),
        (("Podani", "discordance"), True, d2s, "vector"),
        (("Chord",), True, d2s, "vector"),
        (("Geodesic",), True, d2s, "vector"),
        (("Whittaker",), True, d2s, "vector"),
        (("Hellinger",), True, d2s, "vector"),
        (("fJaccard", "fuzzy_Jaccard"), True, d2s, "fuzzy"),
    ]
    return [Measure(names, distance, convert, kind) for names, distance, convert, kind in rows]


MEASURES = _build()
_BY_ALIAS = {}
for _measure in MEASURES:
    for _alias in _measure.names:
        _BY_ALIAS.setdefault(_alias.upper(), _measure)


def find_measure(name):
    if name is None:
        return None
    return _BY_ALIAS.get(str(name).strip().upper())


class Registry:
    """Names and distance flags for the sealed proximity registry."""

    def get_entry_names(self):
        return [measure.canonical for measure in MEASURES]

    def get_field_entries(self, field):
        if field == "distance":
            return [measure.distance for measure in MEASURES]
        if field == "names":
            return [list(measure.names) for measure in MEASURES]
        raise ValueError(f"Field {field!r} not in registry.")

    def get_entry(self, name, stop_if_missing=True):
        found = find_measure(name)
        if found is None:
            if stop_if_missing:
                raise ValueError(f"Entry {name!r} not in registry.")
            return None
        return {
            "names": list(found.names),
            "distance": found.distance,
        }

    def entry_exists(self, name):
        return find_measure(name) is not None

    def __len__(self):
        return len(MEASURES)


pr_DB = Registry()
