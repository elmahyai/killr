"""Multilinear interpolation on an array (e1071::interpolate)."""

from __future__ import annotations

import math

from e1071.patterns import bincombinations, element


def _pmatch(value, choices):
    if isinstance(value, str):
        lower = value.lower()
        for i, choice in enumerate(choices):
            if choice.lower().startswith(lower):
                return i + 1
    return None


def _as_matrix(x):
    if not x:
        return [[]]
    if isinstance(x[0], (list, tuple)):
        return [list(row) for row in x]
    return [list(x)]


def _array_data(a):
    if isinstance(a, dict) and "data" in a and "dim" in a:
        return list(a["data"]), tuple(a["dim"])
    if hasattr(a, "shape"):
        import numpy as np

        arr = np.asarray(a, order="F")
        return arr.ravel(order="F").tolist(), tuple(int(d) for d in arr.shape)
    if isinstance(a, list):
        if not a:
            raise ValueError("a is not an array")
        if isinstance(a[0], list):
            nrow = len(a)
            ncol = len(a[0])
            flat = []
            for c in range(ncol):
                for r in range(nrow):
                    flat.append(a[r][c])
            return flat, (nrow, ncol)
        return list(a), (len(a),)
    raise ValueError("a is not an array")


def _default_adims(a, adims):
    if adims is not None:
        return adims
    if isinstance(a, dict) and "dimnames" in a:
        dn = a["dimnames"]
        if dn is None:
            raise ValueError("adims required when a has no dimnames")
        out = []
        for name in dn:
            if name is None:
                raise ValueError("adims required when a has no dimnames")
            out.append([float(v) for v in name])
        return out
    raise ValueError("adims must be supplied")


def _convexcoeff(xabstand, y):
    out = list(xabstand)
    for k, yk in enumerate(y):
        if yk > 0:
            out[k] = yk - out[k]
    return out


def interpolate(x, a, adims=None, method="linear"):
    x_mat = _as_matrix(x)
    flat, dim = _array_data(a)
    ad = len(dim)
    adims = _default_adims(a, adims)

    method_code = _pmatch(method, ["linear", "constant"])
    if method_code is None:
        raise ValueError("invalid interpolation method")

    for coords in adims:
        for j in range(len(coords) - 1):
            if coords[j + 1] - coords[j] < 0:
                raise ValueError("dimensions of a not ordered")

    bincombi = bincombinations(ad)
    retval = [0.0] * len(x_mat)

    for n, row in enumerate(x_mat):
        leftidx = [0] * ad
        xabstand = [0.0] * ad
        aabstand = [0.0] * ad

        for k in range(ad):
            coords = adims[k]
            xnk = row[k]
            if xnk < min(coords) or xnk > max(coords):
                raise ValueError("No extrapolation allowed")
            idx_candidates = [i + 1 for i, v in enumerate(coords) if v <= xnk]
            leftidx[k] = max(idx_candidates)
            if leftidx[k] == len(coords):
                leftidx[k] -= 1
            xabstand[k] = xnk - coords[leftidx[k] - 1]
            aabstand[k] = coords[leftidx[k]] - coords[leftidx[k] - 1]

        if method_code == 1:
            total = 0.0
            n_corners = 1 << ad
            for k in range(n_corners):
                corner = bincombi[k]
                sub = [leftidx[j] + corner[j] for j in range(ad)]
                coeff = element(flat, dim, sub)
                y_vec = [aabstand[j] * corner[j] for j in range(ad)]
                cc_vec = _convexcoeff(xabstand, y_vec)
                factors = [(aabstand[j] - cc_vec[j]) / aabstand[j] for j in range(ad)]
                total += coeff * math.prod(factors)
            retval[n] = total
        else:
            retval[n] = element(flat, dim, leftidx)

    return retval
