"""Distance indexing shared by the partition routines.

``ind_2`` is the 1-based map used by pam, clara, and twins. The stored
order is the lower triangle read by rows, with a leading zero at index 0.
"""

from __future__ import annotations

import math

import numpy as np

from cluster.daisy import meanabsdev
from cluster.tri import lower_to_upper_tri_inds


def ind_2(left, right):
    """Index of d(left, right) in the twins/pam distance vector. 1-based."""
    if left == right:
        return 0
    if left > right:
        major, minor = left, right
    else:
        major, minor = right, left
    if major <= 46342:
        return (major - 2) * (major - 1) // 2 + minor
    return int((major - 2.0) * (major - 1) / 2.0 + minor)


def as_matrix(values):
    data = np.asarray(values, dtype=float)
    if data.ndim != 2:
        raise ValueError("x is not a numeric dataframe or matrix.")
    return data


def stand_matrix(data):
    """``scale(x, scale = apply(x, 2, meanabsdev))``."""
    center = np.nanmean(data, axis=0)
    scale = np.array([meanabsdev(data[:, j]) for j in range(data.shape[1])], dtype=float)
    return (data - center) / scale


def prepare_diss(values):
    """Reorder an R dissimilarity (dist order) into the C vector with a leading 0."""
    raw = [float(v) for v in np.asarray(values, dtype=float).reshape(-1)]
    n = size_from_length(len(raw))
    order = lower_to_upper_tri_inds(n)
    dys = [0.0] * (1 + len(raw))
    for slot, index in enumerate(order, start=1):
        dys[slot] = raw[index - 1]
    return n, dys


def size_from_length(length):
    discr = 1 + 8 * length
    root = int(round(math.sqrt(discr)))
    if root * root != discr:
        raise ValueError("'x' is not and cannot be converted to class \"dissimilarity\"")
    return (1 + root) // 2


def dysta(data, ndyst, jtmd=None, valmd=None):
    """Distances from a matrix. ``ndyst`` 1 is Euclidean, 2 is Manhattan."""
    n, p = data.shape
    dys = [0.0] * (1 + n * (n - 1) // 2)
    if jtmd is None:
        jtmd = [0] * (p + 1)
    if valmd is None:
        valmd = [0.0] * (p + 1)
    nlk = 0
    jhalt = 0
    pp = float(p)
    for left in range(2, n + 1):
        for right in range(1, left):
            clk = 0.0
            nlk += 1
            present = 0
            for column in range(1, p + 1):
                a = data[left - 1, column - 1]
                b = data[right - 1, column - 1]
                if jtmd[column] < 0 and (a == valmd[column] or b == valmd[column]):
                    continue
                present += 1
                diff = a - b
                if ndyst == 1:
                    clk += diff * diff
                else:
                    clk += abs(diff)
            if present == 0:
                jhalt = 1
                dys[nlk] = -1.0
            elif ndyst == 1:
                dys[nlk] = math.sqrt(clk * (pp / present))
            else:
                dys[nlk] = clk * (pp / present)
    return dys, jhalt


def dysta3(data, ndyst, jtmd=None, valmd=None):
    """fanny distances, upper triangle by rows, no leading zero."""
    n, p = data.shape
    length = n * (n - 1) // 2
    dys = [0.0] * length
    if jtmd is None:
        jtmd = [0] * p
    if valmd is None:
        valmd = [0.0] * p
    nlk = 0
    jhalt = 0
    pp = float(p)
    for left in range(n - 1):
        for right in range(left + 1, n):
            clk = 0.0
            present = 0
            for column in range(p):
                a = data[left, column]
                b = data[right, column]
                if jtmd[column] < 0 and (a == valmd[column] or b == valmd[column]):
                    continue
                present += 1
                diff = a - b
                if ndyst != 2:
                    clk += diff * diff
                else:
                    clk += abs(diff)
            if present == 0:
                dys[nlk] = -1.0
                jhalt = 1
            else:
                clk *= pp / present
                dys[nlk] = math.sqrt(clk) if ndyst == 1 else clk
            nlk += 1
    return dys, jhalt


def fanny_index(left, right, n):
    """0-based index into a fanny distance vector."""
    minor = left if left < right else right
    major = right if left < right else left
    return minor * n - (minor + 1) * (minor + 2) // 2 + major


def missing_code(data):
    """Replace NA with the sentinel used by the C routines. Returns data, jtmd, valmd, any_missing."""
    mask = np.isnan(data)
    if not mask.any():
        return data, None, None, False
    finite = data[~mask]
    sentinel = 1.1 * max(abs(float(finite.min())), abs(float(finite.max()))) if finite.size else 0.0
    jtmd = [0] * (data.shape[1] + 1)
    for column in range(data.shape[1]):
        if mask[:, column].any():
            jtmd[column + 1] = -1
    filled = data.copy()
    filled[mask] = sentinel
    valmd = [sentinel] * (data.shape[1] + 1)
    return filled, jtmd, valmd, True
