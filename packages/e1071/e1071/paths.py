"""Floyd shortest paths. Missing and positive infinite edges are unreachable."""

from __future__ import annotations

import math
import sys


def all_shortest_paths(x):
    n = len(x)
    if any(len(row) != n for row in x):
        raise ValueError("x is not a square matrix")
    huge = sys.float_info.max
    cost = []
    for row in x:
        stored = []
        for value in row:
            if value is None or (isinstance(value, float) and (math.isnan(value) or math.isinf(value) and value > 0)):
                stored.append(huge)
            else:
                stored.append(float(value))
        cost.append(stored)
    length = [row[:] for row in cost]
    middle = [[-1] * n for _ in range(n)]
    for i in range(n):
        length[i][i] = 0.0
    for k in range(n):
        for i in range(n):
            for j in range(n):
                candidate = length[i][k] + length[k][j]
                if candidate < length[i][j]:
                    length[i][j] = candidate
                    middle[i][j] = k
    shown = []
    points = []
    for i in range(n):
        shown.append([None if length[i][j] >= huge else length[i][j] for j in range(n)])
        points.append([middle[i][j] + 1 for j in range(n)])
    return {"length": shown, "middle_points": points}


def extract_path(obj, start, end):
    middle = obj["middle_points"]
    found = []

    def path(i, j):
        k = middle[i - 1][j - 1]
        if k != 0:
            path(i, k)
            found.append(k)
            path(k, j)

    path(start, end)
    return [start, *found, end]
