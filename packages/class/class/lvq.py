"""Learning vector quantization from class.

The updates are the C routines. The row order is R's sample, drawn with
boot's generator so set.seed and set_seed pick the same rows.
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

_knn = importlib.import_module("class.knn")
_codes = _knn._codes
_rows = _knn._rows
knn_cv = _knn.knn_cv


def _rng():
    try:
        from boot import rng as module
    except ImportError:
        sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "boot"))
        from boot import rng as module
    return module


def _sample(values, size, replace=False):
    picks = _rng().sample_int(len(values), size, replace)
    return [values[index - 1] for index in picks]


def lvqinit(x, cl, size=None, prior=None, k=5):
    """Codebook of rows that classify themselves under leave-one-out."""
    rows = _rows(x)
    labels = list(cl)
    n = len(rows)
    if len(labels) != n:
        raise ValueError("'x' and 'cl' have different lengths")
    levels, codes = _codes(labels)
    counts = [codes.count(code) for code in range(1, len(levels) + 1)]
    prop = [count / n for count in counts]
    if prior is None:
        prior = prop
    elif any(value < 0 for value in prior) or round(sum(prior), 5) != 1:
        raise ValueError("invalid 'prior'")
    if len(prior) != len(levels):
        raise ValueError("'prior' is of incorrect length")
    width = len(rows[0]) if rows else 0
    if size is None:
        size = min(round(0.4 * len(levels) * (len(levels) - 1 + width / 2)), n)
    inside = [str(left) == str(right) for left, right in zip(knn_cv(rows, labels, k=k), labels)]
    selected = []
    for code, weight in enumerate(prior, start=1):
        pool = [index for index, (item, ok) in enumerate(zip(codes, inside)) if item == code and ok]
        if len(pool) > 1:
            pool = _sample(pool, min(len(pool), round(size * weight)))
        selected.extend(pool)
    return {"x": [rows[index] for index in selected], "cl": [labels[index] for index in selected]}


def _nearest(point, codes):
    best_at = 0
    best = float("inf")
    for index, code in enumerate(codes):
        gap = sum((a - b) ** 2 for a, b in zip(point, code))
        if gap < best:
            best = gap
            best_at = index
    return best_at


def _two_nearest(point, codes):
    first = 0
    second = 0
    best = float("inf")
    nxt = float("inf")
    for index, code in enumerate(codes):
        gap = sum((a - b) ** 2 for a, b in zip(point, code))
        if gap < best:
            nxt = best
            second = first
            best = gap
            first = index
        elif gap < nxt:
            nxt = gap
            second = index
    return first, second, best, nxt


def _pull(codes, index, point, step):
    codes[index] = [value + step * (src - value) for value, src in zip(codes[index], point)]


def olvq1(x, cl, codebk, niter=None, alpha=0.3):
    """Optimized LVQ1. Each code keeps its own step size."""
    rows = _rows(x)
    labels = list(cl)
    codes = [list(row) for row in _rows(codebk["x"])]
    if niter is None:
        niter = 40 * len(codes)
    _, train_codes = _codes(labels)
    _, book_codes = _codes(list(codebk["cl"]))
    steps = [float(alpha)] * len(codes)
    order = _rng().sample_int(len(rows), int(niter), replace=True)
    for npat in order:
        point = rows[npat - 1]
        index = _nearest(point, codes)
        sign = 1 if book_codes[index] == train_codes[npat - 1] else -1
        _pull(codes, index, point, sign * steps[index])
        steps[index] = min(float(alpha), steps[index] / (1 + sign * steps[index]))
    return {"x": codes, "cl": list(codebk["cl"])}


def lvq1(x, cl, codebk, niter=None, alpha=0.03):
    """LVQ1 with a step that shrinks across the run."""
    rows = _rows(x)
    labels = list(cl)
    codes = [list(row) for row in _rows(codebk["x"])]
    if niter is None:
        niter = 100 * len(codes)
    niter = int(niter)
    _, train_codes = _codes(labels)
    _, book_codes = _codes(list(codebk["cl"]))
    order = _rng().sample_int(len(rows), niter, replace=True)
    for step, npat in enumerate(order):
        point = rows[npat - 1]
        index = _nearest(point, codes)
        sign = 1 if book_codes[index] == train_codes[npat - 1] else -1
        rate = float(alpha) * (niter - step) / niter
        _pull(codes, index, point, sign * rate)
    return {"x": codes, "cl": list(codebk["cl"])}


def _lvq23(x, cl, codebk, niter, alpha, win, epsilon):
    rows = _rows(x)
    labels = list(cl)
    codes = [list(row) for row in _rows(codebk["x"])]
    niter = int(niter)
    _, train_codes = _codes(labels)
    _, book_codes = _codes(list(codebk["cl"]))
    order = _rng().sample_int(len(rows), niter, replace=True)
    gate = (1 - win) / (1 + win)
    for step, npat in enumerate(order):
        point = rows[npat - 1]
        first, second, best, nxt = _two_nearest(point, codes)
        rate = float(alpha) * (niter - step) / niter
        if book_codes[first] != book_codes[second]:
            if (book_codes[first] == train_codes[npat - 1] or book_codes[second] == train_codes[npat - 1]) and best / nxt > gate:
                if book_codes[second] == train_codes[npat - 1]:
                    first, second = second, first
                _pull(codes, first, point, rate)
                _pull(codes, second, point, -rate)
        elif epsilon is not None and book_codes[first] == train_codes[npat - 1]:
            _pull(codes, first, point, epsilon * rate)
            _pull(codes, second, point, epsilon * rate)
    return {"x": codes, "cl": list(codebk["cl"])}


def lvq2(x, cl, codebk, niter=None, alpha=0.03, win=0.3):
    """LVQ2 moves the two nearest codes when they disagree and sit in the window."""
    if niter is None:
        niter = 100 * len(_rows(codebk["x"]))
    return _lvq23(x, cl, codebk, niter, alpha, win, None)


def lvq3(x, cl, codebk, niter=None, alpha=0.03, win=0.3, epsilon=0.1):
    """LVQ3 also nudges two agreeing codes toward the row."""
    if niter is None:
        niter = 100 * len(_rows(codebk["x"]))
    return _lvq23(x, cl, codebk, niter, alpha, win, epsilon)


def lvqtest(codebk, test):
    """Label rows by the nearest codebook vector."""
    return _knn.knn1(codebk["x"], test, codebk["cl"])
