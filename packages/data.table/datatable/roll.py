"""Rolling windows. The exact right-aligned pass is the datatable crate."""

from __future__ import annotations

import math

import datatable_core

from datatable._util import DataTableError, as_sequence, column_list, is_na


def _number(value):
    if is_na(value):
        return float("nan")
    return float(value)


def _windows(n):
    values = as_sequence(n)
    if len(values) == 0:
        raise DataTableError("n must be non 0 length")
    out = []
    for item in values:
        if is_na(item) or isinstance(item, bool) or not isinstance(item, (int, float)):
            raise DataTableError("n must be an integer vector or a list of integer vectors")
        if isinstance(item, float) and not item.is_integer():
            raise DataTableError("n must be an integer vector or a list of integer vectors")
        number = int(item)
        if number < 0:
            raise DataTableError("n must be non-negative")
        out.append(number)
    return out


def _align(values, k: int, align: str, fill: float):
    if align == "right" or k == 0:
        return values
    offset = (k - 1) if align == "left" else (k // 2)
    if offset <= 0:
        return values
    if offset >= len(values):
        return [fill] * len(values)
    return values[offset:] + [fill] * offset


def _present(values):
    return [None if isinstance(item, float) and math.isnan(item) else item for item in values]


def _one(kind: str, values, k: int, fill: float, na_rm: bool, align: str):
    raw = datatable_core.froll_right_py(kind, [_number(item) for item in values], k, fill, na_rm)
    shifted = _align(list(raw), k, align, fill)
    return _present(shifted)


def _froll(kind, x, n, fill=None, algo="fast", align="right", na_rm=False, adaptive=False, partial=False, give_names=False):
    if adaptive or partial or give_names:
        raise DataTableError("adaptive, partial, and give.names are not started")
    if algo not in ("fast", "exact"):
        raise DataTableError("algo must be one of fast, exact")
    if align not in ("right", "left", "center"):
        raise DataTableError("align must be one of right, left, center")
    if column_list(x):
        raise DataTableError("a list of columns is not started for froll")
    values = list(as_sequence(x))
    widths = _windows(n)
    fill_value = float("nan") if is_na(fill) else float(fill)
    pieces = [_one(kind, values, width, fill_value, na_rm, align) for width in widths]
    if len(pieces) == 1:
        return pieces[0]
    return pieces


def frollsum(x, n, fill=None, algo="fast", align="right", na_rm=False, has_nf=None, adaptive=False, partial=False, give_names=False, hasNA=None):
    """Rolling sum. Left and center are the right-aligned window, shifted."""
    del has_nf, hasNA
    return _froll("sum", x, n, fill, algo, align, na_rm, adaptive, partial, give_names)


def frollmean(x, n, fill=None, algo="fast", align="right", na_rm=False, has_nf=None, adaptive=False, partial=False, give_names=False, hasNA=None):
    """Rolling mean. An empty window after na.rm is missing."""
    del has_nf, hasNA
    return _froll("mean", x, n, fill, algo, align, na_rm, adaptive, partial, give_names)


def frollmax(x, n, fill=None, algo="fast", align="right", na_rm=False, has_nf=None, adaptive=False, partial=False, give_names=False, hasNA=None):
    del has_nf, hasNA
    return _froll("max", x, n, fill, algo, align, na_rm, adaptive, partial, give_names)


def frollmin(x, n, fill=None, algo="fast", align="right", na_rm=False, has_nf=None, adaptive=False, partial=False, give_names=False, hasNA=None):
    del has_nf, hasNA
    return _froll("min", x, n, fill, algo, align, na_rm, adaptive, partial, give_names)


def frollprod(x, n, fill=None, algo="fast", align="right", na_rm=False, has_nf=None, adaptive=False, partial=False, give_names=False, hasNA=None):
    del has_nf, hasNA
    return _froll("prod", x, n, fill, algo, align, na_rm, adaptive, partial, give_names)


def frollmedian(x, n, fill=None, algo="fast", align="right", na_rm=False, has_nf=None, adaptive=False, partial=False, give_names=False, hasNA=None):
    """Rolling median. An even window averages the two central values."""
    del has_nf, hasNA
    return _froll("median", x, n, fill, algo, align, na_rm, adaptive, partial, give_names)


def frollvar(x, n, fill=None, algo="fast", align="right", na_rm=False, has_nf=None, adaptive=False, partial=False, give_names=False, hasNA=None):
    """Rolling sample variance, divided by k - 1."""
    del has_nf, hasNA
    return _froll("var", x, n, fill, algo, align, na_rm, adaptive, partial, give_names)


def frollsd(x, n, fill=None, algo="fast", align="right", na_rm=False, has_nf=None, adaptive=False, partial=False, give_names=False, hasNA=None):
    """Square root of the rolling sample variance."""
    del has_nf, hasNA
    return _froll("sd", x, n, fill, algo, align, na_rm, adaptive, partial, give_names)
