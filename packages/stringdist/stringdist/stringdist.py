"""Pairwise string distances from stringdist.

The R wrapper passes the source in the first C argument and the target in
the second, so deletion is charged to ``b``. Jaro-Winkler reorders the
weights to positions 2, 1, 3 before that swap.
"""

from __future__ import annotations

import math
import numbers
import warnings

__all__ = ["stringdist"]

_METHODS = (
    "osa",
    "lv",
    "dl",
    "hamming",
    "lcs",
    "qgram",
    "cosine",
    "jaccard",
    "jw",
    "soundex",
)

_PRINTABLE = set(
    "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
    "0123456789"
    " !\"#$%&'()*+,./:;<=>?@[\\]^_`{|}~-"
)

_RECYCLE = "longer object length is not a multiple of shorter object length"
_LIST_WARNING = (
    "\nYou are passing one or more arguments of type 'list' to\n"
    "'stringdist'. These arguments will be converted with 'as.character'\n"
    "which is likeley not to give what you want (did you mean to use 'seq_dist'?).\n"
    "This warning can be avoided by explicitly converting the argument(s).\n"
)
_SOUNDEX_WARNING = (
    "Non-printable ascii or non-ascii characters in soundex. "
    "Results may be unreliable. See ?printable_ascii."
)


def _is_num(value):
    return isinstance(value, numbers.Real) and not isinstance(value, bool)


def _num_list(value, name):
    if _is_num(value):
        values = [value]
    elif isinstance(value, str) or value is None:
        raise ValueError(f"{name} must be numeric")
    else:
        try:
            values = list(value)
        except TypeError as exc:
            raise ValueError(f"{name} must be numeric") from exc
    numbers_ = []
    for item in values:
        if not _is_num(item):
            raise ValueError(f"{name} must be numeric")
        numbers_.append(float(item))
    return numbers_


def _match_arg(method):
    if method is None:
        return _METHODS[0]
    if isinstance(method, (list, tuple)):
        if list(method) == list(_METHODS):
            return _METHODS[0]
        if len(method) != 1:
            raise ValueError("'method' must be of length 1")
        method = method[0]
    if not isinstance(method, str):
        raise ValueError("'method' must be NULL or a character vector")
    if method in _METHODS:
        return method
    hits = [choice for choice in _METHODS if choice.startswith(method)]
    if len(hits) == 1:
        return hits[0]
    shown = ", ".join(repr(choice) for choice in _METHODS)
    if not hits:
        raise ValueError(f"'{method}' should be one of {shown}")
    raise ValueError(f"'{method}' matches more than one of {shown}")


def _method_tokens(method):
    if method is None:
        return list(_METHODS)
    if isinstance(method, (list, tuple)):
        return list(method)
    return [method]


def _validate(method, weight, q, p, use_bytes, nthread):
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
    if not isinstance(use_bytes, bool):
        raise ValueError("is.logical(useBytes) is not TRUE")
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


def _as_character(value, warn):
    if isinstance(value, str):
        return [value]
    if value is None:
        return [None]
    if isinstance(value, (bytes, bytearray)):
        return [value.decode("utf-8", "surrogateescape")]
    if _is_num(value):
        if isinstance(value, float) and value.is_integer():
            return [str(int(value))]
        return [str(value)]
    if isinstance(value, bool):
        return ["TRUE" if value else "FALSE"]
    try:
        items = list(value)
    except TypeError:
        return [str(value)]
    out = []
    nested = False
    for item in items:
        if isinstance(item, (list, tuple)):
            nested = True
            out.append(str(item))
        elif item is None:
            out.append(None)
        elif isinstance(item, str):
            out.append(item)
        elif isinstance(item, bool):
            out.append("TRUE" if item else "FALSE")
        elif _is_num(item):
            if isinstance(item, float) and item.is_integer():
                out.append(str(int(item)))
            else:
                out.append(str(item))
        else:
            nested = True
            out.append(str(item))
    if nested:
        warn[0] = True
    return out


def _codes(text, use_bytes):
    if use_bytes:
        return list(text.encode("utf-8"))
    return [ord(ch) for ch in text]


def _printable(text):
    if text is None:
        return True
    return all(ch in _PRINTABLE for ch in text)


def _osa(a, b, weight):
    na = len(a)
    nb = len(b)
    if na == 0:
        return nb * weight[1]
    if nb == 0:
        return na * weight[0]
    width = na + 1
    scores = [0.0] * (width * (nb + 1))
    delete, insert, substitute, transpose = weight[0], weight[1], weight[2], weight[3]
    for i in range(width):
        scores[i] = i * delete
    for j in range(1, nb + 1):
        scores[j * width] = j * insert
    for i in range(1, na + 1):
        column = width
        previous = 0
        for j in range(1, nb + 1):
            if a[i - 1] == b[j - 1]:
                sub = 0.0
                tran = 0.0
            else:
                sub = substitute
                tran = transpose
            scores[i + column] = min(
                scores[i - 1 + column] + delete,
                scores[i + previous] + insert,
                scores[i - 1 + previous] + sub,
            )
            if i > 1 and j > 1 and a[i - 1] == b[j - 2] and a[i - 2] == b[j - 1]:
                scores[i + column] = min(
                    scores[i + column], scores[i - 2 + previous - width] + tran
                )
            column += width
            previous += width
    return scores[width * (nb + 1) - 1]


def _lv(a, b, weight):
    na = len(a)
    nb = len(b)
    if na == 0:
        return nb * weight[1]
    if nb == 0:
        return na * weight[0]
    width = na + 1
    scores = [0.0] * (width * (nb + 1))
    delete, insert, substitute = weight[0], weight[1], weight[2]
    for i in range(width):
        scores[i] = i * delete
    for j in range(1, nb + 1):
        scores[j * width] = j * insert
    for i in range(1, na + 1):
        column = width
        previous = 0
        for j in range(1, nb + 1):
            sub = 0.0 if a[i - 1] == b[j - 1] else substitute
            scores[i + column] = min(
                scores[i - 1 + column] + delete,
                scores[i + previous] + insert,
                scores[i - 1 + previous] + sub,
            )
            column += width
            previous += width
    return scores[width * (nb + 1) - 1]


def _dl(src, tgt, weight):
    x = len(src)
    y = len(tgt)
    delete, insert, substitute, transpose = weight[0], weight[1], weight[2], weight[3]
    if x == 0:
        return y * insert
    if y == 0:
        return x * delete
    src = list(src) + [0]
    tgt = list(tgt) + [0]
    width = y + 2
    scores = [0.0] * ((x + 3) * width)
    ceiling = float(x + y)
    scores[0] = ceiling
    scores[width] = delete
    scores[1] = insert
    scores[width + 1] = 0.0
    last = {}

    def push(key):
        if key not in last:
            last[key] = 0

    push(src[0])
    push(tgt[0])
    for i in range(1, x + 1):
        push(src[i])
        scores[(i + 1) * width + 1] = i * delete
        scores[(i + 1) * width] = ceiling
        swap_count = 0
        for j in range(1, y + 1):
            if i == 1:
                push(tgt[j])
                scores[width + (j + 1)] = j * insert
                scores[j + 1] = ceiling
            seen = last.get(tgt[j - 1], 0)
            swap_score = scores[seen * width + swap_count] + (
                i - seen - 1 + j - swap_count
            ) * transpose
            if src[i - 1] != tgt[j - 1]:
                sub_score = scores[i * width + j] + substitute
                ins_score = scores[(i + 1) * width + j] + insert
                del_score = scores[i * width + (j + 1)] + delete
                scores[(i + 1) * width + (j + 1)] = min(
                    swap_score, del_score, ins_score, sub_score
                )
            else:
                swap_count = j
                scores[(i + 1) * width + (j + 1)] = min(
                    scores[i * width + j], swap_score
                )
        last[src[i - 1]] = i
    return scores[(x + 1) * width + (y + 1)]


def _hamming(a, b):
    if len(a) != len(b):
        return math.inf
    return float(sum(left != right for left, right in zip(a, b)))


def _lcs(a, b):
    na = len(a)
    nb = len(b)
    if na == 0:
        return float(nb)
    if nb == 0:
        return float(na)
    width = na + 1
    scores = [0.0] * (width * (nb + 1))
    for i in range(width):
        scores[i] = float(i)
    for j in range(1, nb + 1):
        scores[j * width] = float(j)
    for i in range(1, na + 1):
        column = width
        previous = 0
        for j in range(1, nb + 1):
            if a[i - 1] == b[j - 1]:
                scores[i + column] = scores[i - 1 + previous]
            else:
                scores[i + column] = min(
                    scores[i - 1 + column] + 1.0, scores[i + previous] + 1.0
                )
            column += width
            previous += width
    return scores[width * (nb + 1) - 1]


def _qgram_counts(codes, q):
    counts = {}
    limit = len(codes) - q + 1
    for i in range(limit):
        gram = tuple(codes[i : i + q])
        counts[gram] = counts.get(gram, 0) + 1
    return counts


def _qgram(a, b, q, kind):
    if q == 0:
        return 0.0
    left = _qgram_counts(a, q)
    right = _qgram_counts(b, q)
    if not left and not right:
        return 0.0
    if kind == 0:
        total = 0.0
        for key in set(left) | set(right):
            total += abs(left.get(key, 0) - right.get(key, 0))
        return total
    if kind == 1:
        xy = xx = yy = 0.0
        for key in set(left) | set(right):
            na = left.get(key, 0)
            nb = right.get(key, 0)
            xy += na * nb
            xx += na * na
            yy += nb * nb
        if xy == xx and xy == yy:
            return 0.0
        denom = math.sqrt(xx) * math.sqrt(yy)
        if denom == 0.0:
            return math.nan
        return abs(1.0 - xy / denom)
    intersection = 0.0
    union = 0.0
    for key in set(left) | set(right):
        na = left.get(key, 0)
        nb = right.get(key, 0)
        if na > 0 and nb > 0:
            intersection += 1.0
        if na > 0 or nb > 0:
            union += 1.0
    return 1.0 - intersection / union


def _jaro(a, b, p, bt, weight):
    x = len(a)
    y = len(b)
    if x == 0 and y == 0:
        return 0.0
    match_a = [0] * x
    match_b = [0] * y
    matched = 0
    window = max(max(x, y) // 2 - 1, 0)
    for i in range(x):
        left = max(0, i - window)
        right = min(y - 1, i + window)
        for j in range(left, right + 1):
            if a[i] == b[j] and match_b[j] == 0:
                match_a[i] = i + 1
                match_b[j] = j + 1
                matched += 1
                break
    seq_a = [a[index - 1] for index in match_a if index]
    seq_b = [b[index - 1] for index in match_b if index]
    transpositions = 0.0
    for k in range(matched):
        if seq_a[k] != seq_b[k]:
            transpositions += 0.5
    if matched < 1:
        distance = 1.0
    else:
        distance = 1.0 - (1.0 / 3.0) * (
            weight[0] * matched / x
            + weight[1] * matched / y
            + weight[2] * (matched - transpositions) / matched
        )
    if p > 0 and distance > bt:
        prefix = min(x, y, 4)
        common = 0
        while common < prefix and a[common] == b[common]:
            common += 1
        distance = distance - common * p * distance
    return distance


def _soundex_code(code):
    if code in (98, 102, 112, 118, 66, 70, 80, 86):
        return 49
    if code in (
        99, 103, 106, 107, 113, 115, 120, 122,
        67, 71, 74, 75, 81, 83, 88, 90,
    ):
        return 50
    if code in (100, 116, 68, 84):
        return 51
    if code in (108, 76):
        return 52
    if code in (109, 110, 77, 78):
        return 53
    if code in (114, 82):
        return 54
    if code in (104, 119, 72, 87):
        return 104
    if code in (97, 101, 105, 111, 117, 121, 65, 69, 73, 79, 85, 89):
        return 97
    if code in (
        33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47,
        58, 59, 60, 61, 62, 63, 64, 91, 92, 93, 94, 95, 96, 123, 124,
        125, 126, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 32,
    ):
        return 104
    return 63


def _soundex(codes):
    result = [48, 48, 48, 48]
    if not codes:
        return result
    translated = _soundex_code(codes[0])
    if translated == 63:
        result[0] = codes[0]
    elif 97 <= codes[0] <= 122:
        result[0] = codes[0] - 32
    else:
        result[0] = codes[0]
    previous = translated
    placed = 0
    for code in codes[1:]:
        if placed >= 3:
            break
        current = _soundex_code(code)
        if current == 97:
            previous = current
        elif current != 104 and current != previous:
            placed += 1
            result[placed] = current
            previous = current
    return result


def _soundex_dist(a, b):
    left = _soundex(a)
    right = _soundex(b)
    for i in range(4):
        if left[i] != right[i]:
            return 1.0
    return 0.0


def _pair(a, b, method, weight, q, p, bt):
    if method == "osa":
        return _osa(a, b, weight)
    if method == "lv":
        return _lv(a, b, weight)
    if method == "dl":
        return _dl(a, b, weight)
    if method == "hamming":
        return _hamming(a, b)
    if method == "lcs":
        return _lcs(a, b)
    if method == "qgram":
        return _qgram(a, b, q, 0)
    if method == "cosine":
        return _qgram(a, b, q, 1)
    if method == "jaccard":
        return _qgram(a, b, q, 2)
    if method == "jw":
        return _jaro(a, b, p, bt, weight)
    return _soundex_dist(a, b)


def stringdist(
    a,
    b,
    method=None,
    useBytes=False,
    weight=(1.0, 1.0, 1.0, 1.0),
    q=1,
    p=0,
    bt=0,
    nthread=1,
):
    """Distances between the strings in ``a`` and ``b``.

    The shorter argument is recycled. A missing string makes that pair
    missing. Hamming distance of unequal lengths is infinite.
    """
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
    warn = [False]
    left = _as_character(a, warn)
    right = _as_character(b, warn)
    if warn[0]:
        warnings.warn(_LIST_WARNING, stacklevel=2)
    if not left or not right:
        return []
    if max(len(left), len(right)) % min(len(left), len(right)) != 0:
        warnings.warn(_RECYCLE, stacklevel=2)
    method = _match_arg(method)
    if method in ("osa", "dl") and len(weight) < 4:
        raise ValueError("length(weight) >= 4 is not TRUE")
    if method in ("lv", "jw") and len(weight) < 3:
        raise ValueError("length(weight) >= 3 is not TRUE")
    if method == "jw":
        weight = [weight[1], weight[0], weight[2]]
    if method == "soundex" and (
        any(not _printable(item) for item in left)
        or any(not _printable(item) for item in right)
    ):
        warnings.warn(_SOUNDEX_WARNING, stacklevel=2)
    q_size = int(q[0])
    prefix = float(p[0])
    boost = float(bt[0])
    size = max(len(left), len(right))
    out = []
    for index in range(size):
        source = right[index % len(right)]
        target = left[index % len(left)]
        if source is None or target is None:
            out.append(None)
            continue
        # C receives b then a.
        out.append(
            _pair(
                _codes(source, useBytes),
                _codes(target, useBytes),
                method,
                weight,
                q_size,
                prefix,
                boost,
            )
        )
    return out
