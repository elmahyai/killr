"""Pairwise string distance matrices (``stringdistmatrix``)."""

from __future__ import annotations

import warnings

from stringdist.stringdist import (
    _LIST_WARNING,
    _SOUNDEX_WARNING,
    _as_character,
    _codes,
    _is_num,
    _match_arg,
    _num_list,
    _pair,
    _validate,
    stringdist,
)

__all__ = ["Dist", "stringdistmatrix"]

_USE_NAMES = ("none", "strings", "names")


class Dist(list):
    """Lower-triangle dissimilarities in ``stats::dist`` order."""

    def __init__(self, values, size, labels=None, method=None):
        super().__init__(values)
        self.size = size
        self.labels = labels
        self.method = method


def _match_use_names(use_names):
    if use_names is False:
        use_names = "none"
    if use_names is True:
        use_names = "strings"
    if isinstance(use_names, (list, tuple)):
        if len(use_names) != 1:
            raise ValueError("'useNames' must be of length 1")
        use_names = use_names[0]
    if not isinstance(use_names, str):
        raise ValueError("'useNames' must be NULL or a character vector")
    if use_names in _USE_NAMES:
        return use_names
    hits = [choice for choice in _USE_NAMES if choice.startswith(use_names)]
    if len(hits) == 1:
        return hits[0]
    shown = ", ".join(repr(choice) for choice in _USE_NAMES)
    if not hits:
        raise ValueError(f"'{use_names}' should be one of {shown}")
    raise ValueError(f"'{use_names}' matches more than one of {shown}")


def _vector_names(value):
    if isinstance(value, dict):
        return list(value.keys())
    names = getattr(value, "names", None)
    if names is None:
        return None
    return list(names)


def _vector_values(value):
    if isinstance(value, dict):
        return list(value.values())
    return value


def _prepare_weight(method, weight):
    weight = list(weight)
    if method == "jw":
        weight = [weight[1], weight[0], weight[2]]
    return weight


def _pair_distance(first, second, method, weight, q_size, prefix, boost, use_bytes):
    """Match ``R_stringdist(first, second)`` (``stringdist`` swaps user args)."""
    if first is None or second is None:
        return None
    return _pair(
        _codes(second, use_bytes),
        _codes(first, use_bytes),
        method,
        weight,
        q_size,
        prefix,
        boost,
    )


def _lower_triangle(items, method, weight, q_size, prefix, boost, use_bytes):
    n = len(items)
    out = []
    for j in range(n):
        for i in range(j + 1, n):
            out.append(
                _pair_distance(
                    items[i],
                    items[j],
                    method,
                    weight,
                    q_size,
                    prefix,
                    boost,
                    use_bytes,
                )
            )
    return out


def stringdistmatrix(
    a,
    b=None,
    method=None,
    useBytes=False,
    weight=(1.0, 1.0, 1.0, 1.0),
    q=1,
    p=0,
    bt=0,
    useNames="none",
    nthread=1,
):
    """Distance matrix with rows from ``a`` and columns from ``b``.

    With only ``a``, returns a ``Dist`` object (lower triangle, ``stats::dist``
    order). With both arguments, returns a list of rows filled column-wise via
    ``stringdist``.
    """
    warn = [False]
    if isinstance(a, (list, tuple)) and a and isinstance(a[0], (list, tuple)):
        warn[0] = True
    if b is not None and isinstance(b, (list, tuple)) and b and isinstance(b[0], (list, tuple)):
        warn[0] = True
    if warn[0]:
        warnings.warn(
            _LIST_WARNING.replace("stringdist", "stringdistmatrix").replace(
                "seq_dist", "seq_distmatrix"
            ),
            stacklevel=2,
        )

    use_names = _match_use_names(useNames)
    weight = _num_list(weight, "weight")
    q = _num_list(q, "q")
    p = _num_list(p, "p")
    bt = _num_list(bt, "bt")
    if _is_num(nthread):
        nthread = [nthread]
    elif isinstance(nthread, str) or nthread is None:
        nthread = [nthread]
    else:
        try:
            nthread = list(nthread)
        except TypeError:
            nthread = [nthread]
    _validate(method, weight, q, p, useBytes, nthread)
    method = _match_arg(method)
    raw_weight = tuple(weight)
    weight = _prepare_weight(method, weight)
    q_size = int(q[0])
    prefix = float(p[0])
    boost = float(bt[0])

    if b is None:
        row_names = None
        if use_names == "names":
            row_names = _vector_names(a)
            items = _as_character(_vector_values(a), [False])
        else:
            items = _as_character(_vector_values(a), [False])
        labels = None
        if use_names == "strings":
            labels = list(items)
        elif use_names == "names":
            labels = row_names
        values = _lower_triangle(
            items, method, weight, q_size, prefix, boost, useBytes
        )
        return Dist(values, size=len(items), labels=labels, method=method)

    row_names = col_names = None
    if use_names == "names":
        row_names = _vector_names(a)
        col_names = _vector_names(b)

    a_items = _as_character(_vector_values(a), [False])
    b_items = _as_character(_vector_values(b), [False])

    if use_names == "strings":
        row_names = list(a_items)
        col_names = list(b_items)

    if not a_items or not b_items:
        return []

    nrow = len(a_items)
    ncol = len(b_items)
    matrix = [[None] * ncol for _ in range(nrow)]
    dist_kwargs = dict(
        method=method,
        useBytes=useBytes,
        weight=raw_weight,
        q=q[0],
        p=p[0],
        bt=bt[0],
        nthread=nthread[0],
    )
    for j, right in enumerate(b_items):
        column = stringdist(a_items, right, **dist_kwargs)
        for i, value in enumerate(column):
            matrix[i][j] = value

    return matrix
