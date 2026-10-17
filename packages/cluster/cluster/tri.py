"""Index maps between the two triangle orders in cluster."""

from __future__ import annotations


def lower_to_upper_tri_inds(n):
    """1-based indexes that reorder a lower triangle into the upper order."""
    n = int(n)
    n1 = n - 1
    if n1 < 1:
        raise ValueError("'n' must be >= 2")
    if n1 == 1:
        return [1]
    base = []
    for value in range(1, n1 + 1):
        base.extend([value] * value)
    extra = [0]
    for k in range(2, n1 + 1):
        running = 0
        series = [0] + list(range(n - 2, n - k - 1, -1))
        for item in series:
            running += item
            extra.append(running)
    return [left + right for left, right in zip(base, extra)]


def upper_to_lower_tri_inds(n):
    """1-based indexes that reorder an upper triangle into the lower order."""
    n = int(n)
    n2 = n - 2
    if n2 < 0:
        raise ValueError("'n' must be >= 2")
    steps = list(range(0, n2 + 1))
    running = 0
    heads = []
    for step in steps:
        running += step
        heads.append(1 + running)
    repeats = list(range(n - 1, 0, -1))
    left = []
    for head, count in zip(heads, repeats):
        left.extend([head] * count)
    right = []
    for k in range(0, n2 + 1):
        total = 0
        for item in range(k, n2 + 1):
            total += item
            right.append(total)
    return [a + b for a, b in zip(left, right)]
