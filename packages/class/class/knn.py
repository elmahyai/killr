"""Nearest-neighbor classification from class.

The search is the C routine in class.c. A distance tie uses the same
relative band (1e-4). A tied vote keeps the smallest class code. The C
routine draws that vote with R's uniform generator, so a tie is not the
same draw.
"""

from __future__ import annotations

import sys

_EPS = 1e-4
_MAX_TIES = 1000
_FENCE = 0.99 * sys.float_info.max


def _rows(values):
    if isinstance(values, (str, bytes)):
        raise ValueError("train and test must be numeric")
    try:
        rows = list(values)
    except TypeError as exc:
        raise ValueError("train and test must be numeric") from exc
    if not rows:
        return []
    if isinstance(rows[0], (str, bytes)) or not isinstance(rows[0], (list, tuple)):
        return [[float(item)] for item in rows]
    return [[float(item) for item in row] for row in rows]


def _codes(labels):
    levels = []
    codes = []
    for label in labels:
        text = str(label)
        if text not in levels:
            levels.append(text)
        codes.append(levels.index(text) + 1)
    return levels, codes


def _squared(left, right):
    total = 0.0
    for a, b in zip(left, right):
        delta = a - b
        total += delta * delta
    return total


def _missing(rows):
    for row in rows:
        for value in row:
            if value != value:
                return True
    return False


def _search(train, query, k, skip):
    kn = k
    distances = [_FENCE] * _MAX_TIES
    where = [0] * _MAX_TIES
    for index, row in enumerate(train):
        if skip is not None and index == skip:
            continue
        gap = _squared(query, row)
        if gap <= distances[k - 1] * (1.0 + _EPS):
            for slot in range(kn + 1):
                if gap < distances[slot]:
                    for shift in range(kn, slot, -1):
                        distances[shift] = distances[shift - 1]
                        where[shift] = where[shift - 1]
                    distances[slot] = gap
                    where[slot] = index
                    if distances[kn] <= distances[k - 1]:
                        kn += 1
                        if kn == _MAX_TIES - 1:
                            raise RuntimeError("too many ties in knn")
                    break
        distances[kn] = _FENCE
    return distances, where, kn


def _votes(train_codes, distances, where, k, kn, nc, use_all, minimum):
    votes = [0] * (nc + 1)
    extras = 0
    if use_all:
        for slot in range(k):
            votes[train_codes[where[slot]]] += 1
        for slot in range(k, kn):
            if distances[slot] > distances[k - 1] * (1.0 + _EPS):
                break
            extras += 1
            votes[train_codes[where[slot]]] += 1
    else:
        slot = 0
        while slot < k and not (distances[slot] >= distances[k - 1] * (1.0 - _EPS)):
            votes[train_codes[where[slot]]] += 1
            slot += 1
        if slot == k - 1:
            votes[train_codes[where[slot]]] += 1
        else:
            needed = k - slot
            for offset in range(needed):
                votes[train_codes[where[slot + offset]]] += 1
    threshold = (minimum - 1 + extras) if minimum > 0 else 0
    chosen = 0
    best = threshold
    for code in range(1, nc + 1):
        if votes[code] > best:
            chosen = code
            best = votes[code]
    return chosen, best / (k + extras)


def knn1(train, test, cl):
    """Label each test row by its nearest training row."""
    train_rows = _rows(train)
    test_rows = _rows(test)
    labels = list(cl)
    if _missing(train_rows) or _missing(test_rows) or any(item != item for item in labels if isinstance(item, float)):
        raise ValueError("no missing values are allowed")
    if len(labels) != len(train_rows):
        raise ValueError("'train' and 'class' have different lengths")
    width = len(train_rows[0]) if train_rows else 0
    if any(len(row) != width for row in test_rows):
        raise ValueError("dims of 'test' and 'train' differ")
    levels, codes = _codes(labels)
    nc = max(codes) if codes else 0
    out = []
    for query in test_rows:
        best = sys.float_info.max
        tied = []
        for index, row in enumerate(train_rows):
            gap = _squared(query, row)
            if gap <= best * (1.0 + _EPS):
                if gap < best * (1.0 - _EPS):
                    tied = [index]
                else:
                    tied.append(index)
                best = gap
        if len(tied) == 1:
            out.append(levels[codes[tied[0]] - 1])
            continue
        votes = [0] * (nc + 1)
        for index in tied:
            votes[codes[index]] += 1
        chosen = 1
        best_vote = votes[1] if nc else 0
        for code in range(2, nc + 1):
            if votes[code] > best_vote:
                chosen = code
                best_vote = votes[code]
        out.append(levels[chosen - 1])
    return out


def knn(train, test, cl, k=1, l=0, prob=False, use_all=True):
    """Label each test row from the majority of its k nearest training rows."""
    train_rows = _rows(train)
    test_rows = _rows(test)
    labels = list(cl)
    if _missing(train_rows) or _missing(test_rows):
        raise ValueError("no missing values are allowed")
    if len(labels) != len(train_rows):
        raise ValueError("'train' and 'class' have different lengths")
    k = int(k)
    if len(train_rows) < k:
        k = len(train_rows)
    if k < 1:
        raise ValueError("k must be at least 1")
    width = len(train_rows[0]) if train_rows else 0
    if any(len(row) != width for row in test_rows):
        raise ValueError("dims of 'test' and 'train' differ")
    levels, codes = _codes(labels)
    nc = max(codes) if codes else 0
    out = []
    probabilities = []
    for query in test_rows:
        distances, where, kn = _search(train_rows, query, k, None)
        code, chance = _votes(codes, distances, where, k, kn, nc, use_all, int(l))
        out.append(levels[code - 1] if code else None)
        probabilities.append(chance)
    if prob:
        return out, probabilities
    return out


def knn_cv(train, cl, k=1, l=0, prob=False, use_all=True):
    """Leave-one-out labels for the training rows."""
    train_rows = _rows(train)
    labels = list(cl)
    if _missing(train_rows):
        raise ValueError("no missing values are allowed")
    if len(labels) != len(train_rows):
        raise ValueError("'train' and 'class' have different lengths")
    k = int(k)
    if len(train_rows) - 1 < k:
        k = len(train_rows) - 1
    if k < 1:
        raise ValueError("k must be at least 1")
    levels, codes = _codes(labels)
    nc = max(codes) if codes else 0
    out = []
    probabilities = []
    for index, query in enumerate(train_rows):
        distances, where, kn = _search(train_rows, query, k, index)
        code, chance = _votes(codes, distances, where, k, kn, nc, use_all, int(l))
        out.append(levels[code - 1] if code else None)
        probabilities.append(chance)
    if prob:
        return out, probabilities
    return out
