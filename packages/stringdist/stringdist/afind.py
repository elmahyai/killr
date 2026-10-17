"""Sliding-window fuzzy search from stringdist ``afind``."""

from __future__ import annotations

import math

from stringdist.stringdist import (
    _METHODS,
    _as_character,
    _codes,
    _is_num,
    _num_list,
    _pair,
)

__all__ = ["afind"]

_AFIND_METHODS = _METHODS + ("running_cosine",)


def _match_afind(method):
    if method is None:
        return _AFIND_METHODS[0]
    if isinstance(method, (list, tuple)):
        if list(method) == list(_AFIND_METHODS):
            return _AFIND_METHODS[0]
        if len(method) != 1:
            raise ValueError("'method' must be of length 1")
        method = method[0]
    if not isinstance(method, str):
        raise ValueError("'method' must be NULL or a character vector")
    if method in _AFIND_METHODS:
        return method
    hits = [choice for choice in _AFIND_METHODS if choice.startswith(method)]
    if len(hits) == 1:
        return hits[0]
    shown = ", ".join(repr(choice) for choice in _AFIND_METHODS)
    if not hits:
        raise ValueError(f"'{method}' should be one of {shown}")
    raise ValueError(f"'{method}' matches more than one of {shown}")


def _method_tokens(method):
    if method is None:
        return list(_AFIND_METHODS)
    if isinstance(method, (list, tuple)):
        return list(method)
    return [method]


def _validate_afind(method, weight, q, p, use_bytes, nthread, window, value):
    if any(not math.isfinite(item) for item in weight):
        raise ValueError("all(is.finite(weight)) is not TRUE")
    if any(item <= 0 for item in weight):
        raise ValueError("all(weight > 0) is not TRUE")
    if any(item > 1 for item in weight):
        raise ValueError("all(weight <= 1) is not TRUE")
    if window is not None:
        widths = _num_list(window, "window")
        if len(widths) != 1:
            raise ValueError("is.null(window) || window >= 1 is not TRUE")
        if widths[0] < 1:
            raise ValueError("is.null(window) || window >= 1 is not TRUE")
    if not q or any(item < 0 for item in q):
        raise ValueError("q >= 0 is not TRUE")
    if not p or any(item > 0.25 for item in p):
        raise ValueError("p <= 0.25 is not TRUE")
    if any(item < 0 for item in p):
        raise ValueError("p >= 0 is not TRUE")
    if not isinstance(use_bytes, bool):
        raise ValueError("is.logical(useBytes) is not TRUE")
    if not isinstance(value, bool):
        raise ValueError("is.logical(value) is not TRUE")
    tokens = _method_tokens(method)
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


def _nchar(text, use_bytes):
    if text is None:
        return 0
    if use_bytes:
        return len(text.encode("utf-8"))
    return len(text)


def _substr(text, start, end, use_bytes):
    if text is None or start is None or end is None:
        return None
    start = int(start)
    end = int(end)
    if start < 1 or end < start:
        return None
    if use_bytes:
        data = text.encode("utf-8")
        piece = data[start - 1 : end]
        return piece.decode("utf-8", "surrogateescape")
    return text[start - 1 : end]


def _window_codes(text, start, width, use_bytes):
    end = start + width - 1
    if use_bytes:
        raw = text.encode("utf-8")
        return list(raw[start - 1 : end])
    return _codes(_substr(text, start, end, use_bytes), False)


def _scan_one(text, pattern, width, method, weight, q, p, bt, use_bytes):
    if text is None or pattern is None:
        return None, None
    if use_bytes:
        n = len(text.encode("utf-8"))
    else:
        n = len(text)
    if n == 0:
        return 1, _afind_distance_codes(
            _codes(pattern, use_bytes), [], method, weight, q, p, bt
        )
    if width < 1:
        width = 1
    if n >= width:
        last = n - width + 1
    else:
        last = 1
    best_loc = 1
    best_dist = math.inf
    pattern_codes = _codes(pattern, use_bytes)
    for start in range(1, last + 1):
        dist = _afind_distance_codes(
            pattern_codes,
            _window_codes(text, start, width, use_bytes),
            method,
            weight,
            q,
            p,
            bt,
        )
        if dist is None:
            continue
        if dist < best_dist:
            best_dist = dist
            best_loc = start
    if best_dist is math.inf:
        best_dist = _afind_distance_codes(
            pattern_codes,
            _window_codes(text, 1, width, use_bytes),
            method,
            weight,
            q,
            p,
            bt,
        )
    return best_loc, best_dist


def _afind_distance_codes(pattern_codes, window_codes, method, weight, q, p, bt):
    if pattern_codes is None:
        return None
    dist_method = "cosine" if method == "running_cosine" else method
    return _pair(
        window_codes,
        pattern_codes,
        dist_method,
        weight,
        int(q),
        float(p),
        float(bt),
    )


def afind(
    x,
    pattern,
    window=None,
    value=True,
    method=None,
    useBytes=False,
    weight=(1.0, 1.0, 1.0, 1.0),
    q=1,
    p=0,
    bt=0,
    nthread=1,
):
    """Best sliding-window match of each pattern in each string."""
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
    _validate_afind(method, weight, q, p, useBytes, nthread, window, value)
    warn = [False]
    xs = _as_character(x, warn)
    patterns = _as_character(pattern, warn)
    if not useBytes:
        xs = [None if item is None else item for item in xs]
        patterns = [None if item is None else item for item in patterns]
    if len(xs) == 0:
        return []
    method = _match_afind(method)
    if method in ("osa", "dl") and len(weight) < 4:
        raise ValueError("length(weight) >= 4 is not TRUE")
    if method in ("lv", "jw") and len(weight) < 3:
        raise ValueError("length(weight) >= 3 is not TRUE")
    if method == "jw":
        weight = [weight[1], weight[0], weight[2]]
    if window is None:
        widths = [_nchar(item, useBytes) for item in patterns]
    else:
        widths = [_num_list(window, "window")[0]] * len(patterns)
    q_size = int(q[0])
    prefix = float(p[0])
    boost = float(bt[0])
    nrow = len(xs)
    ncol = len(patterns)
    location = [[None] * ncol for _ in range(nrow)]
    distance = [[None] * ncol for _ in range(nrow)]
    for i, text in enumerate(xs):
        for j, pat in enumerate(patterns):
            loc, dist = _scan_one(
                text, pat, int(widths[j]), method, weight, q_size, prefix, boost, useBytes
            )
            location[i][j] = loc
            distance[i][j] = dist
    out = {"location": location, "distance": distance}
    if value:
        match = [[None] * ncol for _ in range(nrow)]
        explicit_scalar = window is not None
        scalar_w = int(_num_list(window, "window")[0]) if explicit_scalar else None
        for j in range(ncol):
            if explicit_scalar:
                if j > 0:
                    continue
                width_for_match = scalar_w
            else:
                width_for_match = int(widths[j])
            for i in range(nrow):
                start = location[i][j]
                if start is None:
                    match[i][j] = None
                else:
                    match[i][j] = _substr(
                        xs[i], start, start + width_for_match - 1, useBytes
                    )
        out["match"] = match
    return out
