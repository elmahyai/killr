"""Internal approximate match used by ``ain`` (R ``amatch`` semantics)."""

from __future__ import annotations

import math

from stringdist.stringdist import (
    _as_character,
    _codes,
    _is_num,
    _match_arg,
    _num_list,
    _pair,
)

__all__ = ["amatch"]


def _validate_amatch(method, weight, q, p, use_bytes, nthread, max_dist, match_na):
    if any(not math.isfinite(item) for item in weight):
        raise ValueError("all(is.finite(weight)) is not TRUE")
    if any(item <= 0 for item in weight):
        raise ValueError("all(weight > 0) is not TRUE")
    if any(item > 1 for item in weight):
        raise ValueError("all(weight <= 1) is not TRUE")
    if not q or any(item < 0 for item in q):
        raise ValueError("q >= 0 is not TRUE")
    if not p or any(item > 0.25 for item in p):
        raise ValueError("p <= 0.25 is not TRUE")
    if any(item < 0 for item in p):
        raise ValueError("p >= 0 is not TRUE")
    if match_na not in (True, False):
        raise ValueError("matchNA %in% c(TRUE,FALSE) is not TRUE")
    if not (max_dist > 0):
        raise ValueError("maxDist > 0 is not TRUE")
    if not isinstance(use_bytes, bool):
        raise ValueError("is.logical(useBytes) is not TRUE")
    tokens = [method]
    if any(token in ("osa", "dl") and len(weight) < 4 for token in tokens):
        raise ValueError(
            'ifelse(method %in% c("osa", "dl"), length(weight) >= 4, TRUE) are not all TRUE'
        )
    if any(token in ("lv", "jw") and len(weight) < 3 for token in tokens):
        raise ValueError(
            'ifelse(method %in% c("lv", "jw"), length(weight) >= 3, TRUE) are not all TRUE'
        )
    if len(nthread) != 1:
        raise ValueError("length(nthread) == 1 is not TRUE")
    if not _is_num(nthread[0]) or not math.isfinite(nthread[0]) or not nthread[0] > 0:
        raise ValueError("nthread > 0 is not TRUE")


def _coerce_nomatch(nomatch):
    if nomatch is None:
        return None
    if isinstance(nomatch, bool):
        raise ValueError("nomatch must be coercible to integer")
    if _is_num(nomatch):
        if not math.isfinite(nomatch):
            return None
        return int(nomatch)
    try:
        values = list(nomatch)
    except TypeError as exc:
        raise ValueError("nomatch must be coercible to integer") from exc
    if len(values) != 1:
        raise ValueError("nomatch must be coercible to integer")
    item = values[0]
    if item is None:
        return None
    if not _is_num(item) or not math.isfinite(item):
        return None
    return int(item)


def _distance(xi, tj, method, weight, q, p, bt, use_bytes):
    return _pair(
        _codes(tj, use_bytes),
        _codes(xi, use_bytes),
        method,
        weight,
        q,
        p,
        bt,
    )


def amatch(
    x,
    table,
    nomatch=None,
    matchNA=True,
    method=None,
    useBytes=False,
    weight=(1.0, 1.0, 1.0, 1.0),
    maxDist=0.1,
    q=1,
    p=0,
    bt=0,
    nthread=1,
):
    """Position of the closest match of each ``x`` in ``table`` (1-based)."""
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
    if _is_num(maxDist):
        max_dist = float(maxDist)
    else:
        max_dist = float(_num_list(maxDist, "maxDist")[0])
    method = _match_arg(method)
    _validate_amatch(method, weight, q, p, useBytes, nthread, max_dist, matchNA)
    no_match = _coerce_nomatch(nomatch)
    if method in ("osa", "dl") and len(weight) < 4:
        raise ValueError("length(weight) >= 4 is not TRUE")
    if method in ("lv", "jw") and len(weight) < 3:
        raise ValueError("length(weight) >= 3 is not TRUE")
    if method == "jw":
        weight = [weight[1], weight[0], weight[2]]
    warn = [False]
    xs = _as_character(x, warn)
    tabs = _as_character(table, warn)
    q_size = int(q[0])
    prefix = float(p[0])
    boost = float(bt[0])
    out = []
    for xi in xs:
        index = no_match
        best = math.inf
        for j, tj in enumerate(tabs):
            if xi is None and tj is None:
                index = (j + 1) if matchNA else no_match
                break
            if xi is None or tj is None:
                continue
            dist = _distance(xi, tj, method, weight, q_size, prefix, boost, useBytes)
            if dist is None:
                continue
            if dist <= max_dist and dist < best:
                index = j + 1
                if abs(dist) < 1e-14:
                    break
                best = dist
        out.append(index)
    return out
