"""General k-nearest neighbors.

Distances are proxy's. The vote is the class of the neighbors at or
inside the k-th distance. A unique majority is returned.
"""

from __future__ import annotations

import sys
from pathlib import Path


def _proxy_dist():
    try:
        from proxy import dist as impl
    except ImportError:
        sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "proxy"))
        from proxy import dist as impl
    return impl


def _rows(values):
    rows = list(values)
    if not rows:
        return []
    if isinstance(rows[0], (str, bytes)) or not isinstance(rows[0], (list, tuple)):
        return [[float(item)] for item in rows]
    return [[float(item) for item in row] for row in rows]


def _center_scale(rows, which):
    columns = list(zip(*rows))
    center = []
    scale = []
    scaled = []
    for index, column in enumerate(columns):
        if not which[index]:
            center.append(None)
            scale.append(None)
            scaled.append(list(column))
            continue
        count = len(column)
        mean = sum(column) / count
        variance = sum((value - mean) ** 2 for value in column) / (count - 1)
        spread = variance ** 0.5
        center.append(mean)
        scale.append(spread)
        scaled.append([(value - mean) / spread for value in column])
    return [list(row) for row in zip(*scaled)], center, scale


def gknn(x, y, k=1, method=None, scale=True, use_all=True):
    """Store the training rows and their labels."""
    rows = _rows(x)
    labels = list(y)
    flags = [bool(scale)] * len(rows[0]) if isinstance(scale, bool) else [bool(item) for item in scale]
    scaled = any(flags)
    center = None
    spread = None
    if scaled:
        rows, center, spread = _center_scale(rows, flags)
    levels = []
    for label in labels:
        if label not in levels:
            levels.append(label)
    return {
        "x": rows,
        "y": labels,
        "k": int(k),
        "method": method,
        "use_all": bool(use_all),
        "scaled": scaled,
        "scale": flags,
        "center": center,
        "spread": spread,
        "levels": levels,
    }


def predict_gknn(model, newdata):
    """Label each new row."""
    rows = _rows(newdata)
    if model["scaled"]:
        columns = list(zip(*rows))
        adjusted = []
        for index, column in enumerate(columns):
            if not model["scale"][index]:
                adjusted.append(list(column))
                continue
            mean = model["center"][index]
            spread = model["spread"][index]
            adjusted.append([(value - mean) / spread for value in column])
        rows = [list(row) for row in zip(*adjusted)]
    table = _proxy_dist()(model["x"], rows, method=model["method"])
    out = []
    for column in range(len(rows)):
        gaps = [table[row][column] for row in range(len(table))]
        order = sorted(range(len(gaps)), key=lambda index: gaps[index])
        kth = gaps[order[model["k"] - 1]]
        tied = [index for index, value in enumerate(gaps) if value == kth]
        chosen = order[: model["k"]][:-1] + tied
        counts = {}
        for index in chosen:
            label = model["y"][index]
            counts[label] = counts.get(label, 0) + 1
        best = max(counts.values())
        for label in model["levels"]:
            if counts.get(label, 0) == best:
                out.append(label)
                break
    return out
