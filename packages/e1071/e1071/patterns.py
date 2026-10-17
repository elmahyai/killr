"""Binary patterns, array indexing, permutations, and class agreement."""

from __future__ import annotations

import math


def bincombinations(p):
    rows = 1 << p
    out = [[0 for _ in range(p)] for _ in range(rows)]
    for n in range(1, p + 1):
        block = rows // (1 << n)
        pattern = [0] * block + [1] * block
        for i in range(rows):
            out[i][n - 1] = pattern[i % len(pattern)]
    return out


def countpattern(x, matching=False):
    rows = [list(row) for row in x]
    nvar = len(rows[0])
    npat = 1 << nvar
    counts = [0] * npat
    matched = []
    for row in rows:
        code = 0
        for bit in row:
            code = 2 * code + int(bit)
        counts[code] += 1
        matched.append(code + 1)
    if matching:
        return counts, matched
    return counts


def element(x, shape, i):
    """Column-major element. `shape` is R's dim, `i` is 1-based."""
    if len(i) != len(shape):
        raise ValueError("Wrong number of subscripts")
    if len(i) == 1:
        return x[i[0] - 1]
    m1 = [i[0]] + [value - 1 for value in i[1:]]
    cum = []
    running = 1
    for size in shape[:-1]:
        running *= size
        cum.append(running)
    m2 = [1] + cum
    index = sum(left * right for left, right in zip(m1, m2))
    return x[index - 1]


def permutations(n):
    """All permutations. The column order follows R's `2:i - 1` loop."""
    if n == 1:
        return [[1]]
    if n < 2:
        raise ValueError("n must be a positive integer")
    z = [[1]]
    for i in range(2, n + 1):
        x = [row + [i] for row in z]
        a = list(range(1, i + 1)) + list(range(1, i))
        rows = [[0] * i for _ in range(i * len(x))]
        for r, row in enumerate(x):
            rows[r] = row[:]
        for j in range(1, i):
            columns = a[j : j + i]
            base = j * len(x)
            for r, row in enumerate(x):
                rows[base + r] = [row[column - 1] for column in columns]
        z = rows
    return z


def class_agreement(tab, match_names=False):
    rows = [list(row) for row in tab]
    n = sum(sum(row) for row in rows)
    ni = [sum(row) for row in rows]
    ncol = len(rows[0])
    nj = [sum(rows[r][c] for r in range(len(rows))) for c in range(ncol)]
    m = min(len(ni), ncol)
    p0 = sum(rows[i][i] for i in range(m)) / n
    pc = sum((ni[i] / n) * (nj[i] / n) for i in range(m))
    n2 = math.comb(int(n), 2)
    sum_sq = sum(value * value for row in rows for value in row)
    rand = 1 + (sum_sq - (sum(value * value for value in ni) + sum(value * value for value in nj)) / 2) / n2
    nis2 = sum(math.comb(int(value), 2) for value in ni if value > 1)
    njs2 = sum(math.comb(int(value), 2) for value in nj if value > 1)
    tabs2 = sum(math.comb(int(value), 2) for row in rows for value in row if value > 1)
    crand = (tabs2 - (nis2 * njs2) / n2) / ((nis2 + njs2) / 2 - (nis2 * njs2) / n2)
    kappa = (p0 - pc) / (1 - pc)
    return [p0, kappa, rand, crand]
