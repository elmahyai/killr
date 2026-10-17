"""Pairwise distances between integer sequences (stringdist ``seq_dist``)."""

from __future__ import annotations

import math
import warnings

from stringdist.stringdist import (
    _RECYCLE,
    _is_num,
    _num_list,
    _pair,
    _validate,
    stringdist,
)

__all__ = ["seq_dist"]

_SEQ_METHODS = (
    "osa",
    "lv",
    "dl",
    "hamming",
    "lcs",
    "qgram",
    "cosine",
    "jaccard",
    "jw",
)


def _match_seq_method(method):
    if method is None:
        return _SEQ_METHODS[0]
    if isinstance(method, (list, tuple)):
        if list(method) == list(_SEQ_METHODS):
            return _SEQ_METHODS[0]
        if len(method) != 1:
            raise ValueError("'method' must be of length 1")
        method = method[0]
    if not isinstance(method, str):
        raise ValueError("'method' must be NULL or a character vector")
    if method in _SEQ_METHODS:
        return method
    hits = [choice for choice in _SEQ_METHODS if choice.startswith(method)]
    if len(hits) == 1:
        return hits[0]
    shown = ", ".join(repr(choice) for choice in _SEQ_METHODS)
    if not hits:
        raise ValueError(f"'{method}' should be one of {shown}")
    raise ValueError(f"'{method}' matches more than one of {shown}")


def _to_int(value):
    if value is None:
        return None
    if isinstance(value, float) and math.isnan(value):
        return None
    if isinstance(value, bool):
        raise TypeError("argument must be 'list', 'integer' or 'numeric'")
    if not _is_num(value):
        raise TypeError("argument must be 'list', 'integer' or 'numeric'")
    return int(value)


def _vec_to_int(values):
    return [_to_int(item) for item in values]


def _sequence_missing(seq):
    return seq is None or (isinstance(seq, float) and math.isnan(seq))


def _ensure_int_list(value):
    if _is_num(value):
        return [[_to_int(value)]]
    try:
        import numpy as np

        if isinstance(value, np.ndarray) and value.ndim == 1:
            return [_vec_to_int(value.tolist())]
    except ImportError:
        pass
    if isinstance(value, (list, tuple)):
        if not value:
            return []
        if all(_is_num(item) for item in value):
            return [_vec_to_int(value)]
        out = []
        for item in value:
            if _sequence_missing(item):
                out.append(None)
            elif isinstance(item, (list, tuple)):
                out.append(_vec_to_int(item))
            elif _is_num(item):
                out.append([_to_int(item)])
            else:
                raise TypeError("argument must be 'list', 'integer' or 'numeric'")
        return out
    raise TypeError("argument must be 'list', 'integer' or 'numeric'")


def _codes_to_str(codes):
    return "".join(chr(code) for code in codes)


def _distance(
    source,
    target,
    method,
    pair_weight,
    raw_weight,
    q_size,
    prefix,
    boost,
    nthread,
):
    if any(code is None for code in source) or any(code is None for code in target):
        return _pair(source, target, method, pair_weight, q_size, prefix, boost)
    pair = stringdist(
        _codes_to_str(target),
        _codes_to_str(source),
        method=method,
        weight=tuple(raw_weight),
        q=q_size,
        p=prefix,
        bt=boost,
        nthread=nthread,
    )
    return pair[0]


def seq_dist(
    a,
    b,
    method=None,
    weight=(1.0, 1.0, 1.0, 1.0),
    q=1,
    p=0,
    bt=0,
    nthread=1,
):
    """Distances between integer sequences in ``a`` and ``b``.

    The shorter argument is recycled. A missing sequence (``NA``) makes that
    pair missing.
    """
    left = _ensure_int_list(a)
    right = _ensure_int_list(b)
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
    if not left or not right:
        return []
    if max(len(left), len(right)) % min(len(left), len(right)) != 0:
        warnings.warn(_RECYCLE, stacklevel=2)
    method = _match_seq_method(method)
    if method in ("osa", "dl") and len(weight) < 4:
        raise ValueError("length(weight) >= 4 is not TRUE")
    if method in ("lv", "jw") and len(weight) < 3:
        raise ValueError("length(weight) >= 3 is not TRUE")
    raw_weight = list(weight)
    pair_weight = list(raw_weight)
    if method == "jw":
        pair_weight = [raw_weight[1], raw_weight[0], raw_weight[2]]
    thread_count = int(nthread[0])
    q_size = int(q[0])
    prefix = float(p[0])
    boost = float(bt[0])
    size = max(len(left), len(right))
    out = []
    for index in range(size):
        source = right[index % len(right)]
        target = left[index % len(left)]
        if _sequence_missing(source) or _sequence_missing(target):
            out.append(None)
            continue
        out.append(
            _distance(
                source,
                target,
                method,
                pair_weight,
                raw_weight,
                q_size,
                prefix,
                boost,
                thread_count,
            )
        )
    return out
