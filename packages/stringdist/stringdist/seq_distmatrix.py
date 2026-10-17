"""Pairwise distance matrices for integer sequences (``seq_distmatrix``)."""

from __future__ import annotations

from stringdist.seq_dist import _ensure_int_list, _match_seq_method, seq_dist
from stringdist.stringdist import _is_num, _num_list, _validate
from stringdist.stringdistmatrix import Dist

__all__ = ["seq_distmatrix"]

_USE_NAMES = ("names", "none")


def _match_use_names(use_names):
    if use_names is False:
        use_names = "none"
    if use_names is True:
        use_names = "names"
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


def _sequence_pair_distance(first, second, dist_kwargs):
    if first is None or second is None:
        return None
    return seq_dist([first], [second], **dist_kwargs)[0]


def _lower_triangle(items, dist_kwargs):
    n = len(items)
    out = []
    for j in range(n):
        for i in range(j + 1, n):
            out.append(_sequence_pair_distance(items[i], items[j], dist_kwargs))
    return out


def seq_distmatrix(
    a,
    b=None,
    method=None,
    weight=(1.0, 1.0, 1.0, 1.0),
    q=1,
    p=0,
    bt=0,
    useNames="names",
    nthread=1,
):
    """Distance matrix with rows from ``a`` and columns from ``b``.

    With only ``a``, returns a ``Dist`` object (lower triangle, ``stats::dist``
    order). With both arguments, returns a list of rows filled column-wise via
    ``seq_dist``.
    """
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
    _validate(method, weight, q, p, False, nthread)
    method = _match_seq_method(method)
    if method in ("osa", "dl") and len(weight) < 4:
        raise ValueError("length(weight) >= 4 is not TRUE")
    if method in ("lv", "jw") and len(weight) < 3:
        raise ValueError("length(weight) >= 3 is not TRUE")

    raw_a = _vector_values(a)
    a_items = _ensure_int_list(raw_a)
    dist_kwargs = dict(
        method=method,
        weight=tuple(weight),
        q=q[0],
        p=p[0],
        bt=bt[0],
        nthread=nthread[0],
    )

    if b is None:
        labels = None
        if use_names == "names":
            labels = _vector_names(a)
        values = _lower_triangle(a_items, dist_kwargs)
        return Dist(values, size=len(a_items), labels=labels, method=method)

    b_items = _ensure_int_list(_vector_values(b))

    if not a_items or not b_items:
        return []

    nrow = len(a_items)
    ncol = len(b_items)
    matrix = [[None] * ncol for _ in range(nrow)]
    for j, source in enumerate(b_items):
        column = seq_dist(a_items, [source], **dist_kwargs)
        for i, value in enumerate(column):
            matrix[i][j] = value

    return matrix
