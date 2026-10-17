"""Approximate sequence membership from stringdist ``seq_ain``."""

from __future__ import annotations

import math

from stringdist._amatch import _coerce_nomatch
from stringdist.seq_dist import (
    _distance,
    _ensure_int_list,
    _match_seq_method,
    _sequence_missing,
)
from stringdist.stringdist import _is_num, _num_list

__all__ = ["seq_ain"]


def _validate_seq_amatch(method, weight, q, p, nthread, match_na):
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


def _seq_amatch(
    x,
    table,
    nomatch=0,
    matchNA=True,
    method=None,
    weight=(1.0, 1.0, 1.0, 1.0),
    maxDist=0.1,
    q=1,
    p=0,
    bt=0,
    nthread=1,
):
    """Internal ``seq_amatch`` (not exported); used only by ``seq_ain``."""
    xs = _ensure_int_list(x)
    tabs = _ensure_int_list(table)
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
    method = _match_seq_method(method)
    _validate_seq_amatch(method, weight, q, p, nthread, matchNA)
    if method in ("osa", "dl") and len(weight) < 4:
        raise ValueError("length(weight) >= 4 is not TRUE")
    if method in ("lv", "jw") and len(weight) < 3:
        raise ValueError("length(weight) >= 3 is not TRUE")
    raw_weight = list(weight)
    pair_weight = list(raw_weight)
    if method == "jw":
        pair_weight = [raw_weight[1], raw_weight[0], raw_weight[2]]
    no_match = _coerce_nomatch(nomatch)
    thread_count = int(nthread[0])
    q_size = int(q[0])
    prefix = float(p[0])
    boost = float(bt[0])
    out = []
    for xi in xs:
        index = no_match
        best = math.inf
        for j, tj in enumerate(tabs):
            if _sequence_missing(xi) and _sequence_missing(tj):
                index = (j + 1) if matchNA else no_match
                break
            if _sequence_missing(xi) or _sequence_missing(tj):
                continue
            dist = _distance(
                xi,
                tj,
                method,
                pair_weight,
                raw_weight,
                q_size,
                prefix,
                boost,
                thread_count,
            )
            if dist is None:
                continue
            if dist <= max_dist and dist < best:
                index = j + 1
                if abs(dist) < 1e-14:
                    break
                best = dist
        out.append(index)
    return out


def seq_ain(
    x,
    table,
    matchNA=True,
    method=None,
    weight=(1.0, 1.0, 1.0, 1.0),
    maxDist=0.1,
    q=1,
    p=0,
    bt=0,
    nthread=1,
):
    """Whether each sequence in ``x`` has an approximate match in ``table``."""
    positions = _seq_amatch(
        x,
        table,
        matchNA=matchNA,
        method=method,
        weight=weight,
        maxDist=maxDist,
        q=q,
        p=p,
        bt=bt,
        nthread=nthread,
    )
    out = []
    for pos in positions:
        if pos is None:
            out.append(None)
        else:
            out.append(pos > 0)
    return out
