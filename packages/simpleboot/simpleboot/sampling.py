"""Draws that follow R's ``sample(..., replace=TRUE, prob=)``.

Equal weights still go through the probability sampler. ``sample.int``
without ``prob`` is a different stream.
"""

import math

from boot.rng import unif, unif_index


def _revsort(values, index):
    """R ``revsort``: heapsort into descending order, permuting ``index``."""
    n = len(values)
    if n <= 1:
        return
    a = [0.0] + list(values)
    ib = [0] + list(index)
    left = (n >> 1) + 1
    right = n
    while True:
        if left > 1:
            left -= 1
            ra = a[left]
            ii = ib[left]
        else:
            ra = a[right]
            ii = ib[right]
            a[right] = a[1]
            ib[right] = ib[1]
            right -= 1
            if right == 1:
                a[1] = ra
                ib[1] = ii
                values[:] = a[1:]
                index[:] = ib[1:]
                return
        i = left
        j = left << 1
        while j <= right:
            if j < right and a[j] > a[j + 1]:
                j += 1
            if ra > a[j]:
                a[i] = a[j]
                ib[i] = ib[j]
                i = j
                j += i
            else:
                j = right + 1
        a[i] = ra
        ib[i] = ii


def _normalize(prob):
    weights = [float(value) for value in prob]
    total = 0.0
    for weight in weights:
        if not math.isfinite(weight):
            raise ValueError("NA in probability vector")
        if weight < 0.0:
            raise ValueError("negative probability")
        if weight > 0.0:
            total += weight
    if total <= 0.0:
        raise ValueError("too few positive probabilities")
    return [weight / total for weight in weights]


def _prob_sample_replace(weights, size):
    n = len(weights)
    values = list(weights)
    perm = list(range(1, n + 1))
    _revsort(values, perm)
    for index in range(1, n):
        values[index] += values[index - 1]
    last = n - 1
    chosen = []
    for _ in range(size):
        draw = unif()
        slot = last
        for index in range(last):
            if draw <= values[index]:
                slot = index
                break
        chosen.append(perm[slot])
    return chosen


def _walker_sample_replace(weights, size):
    n = len(weights)
    q = [weight * n for weight in weights]
    labels = [0] * n
    small = 0
    large = n
    alias = [0] * n
    for index in range(n):
        if q[index] < 1.0:
            labels[small] = index
            small += 1
        else:
            large -= 1
            labels[large] = index
    if small > 0 and large < n:
        for step in range(n - 1):
            small_index = labels[step]
            large_index = labels[large]
            alias[small_index] = large_index
            q[large_index] += q[small_index] - 1.0
            if q[large_index] < 1.0:
                large += 1
            if large >= n:
                break
    for index in range(n):
        q[index] += index
    chosen = []
    for _ in range(size):
        slot = unif_index(n)
        proposal = slot + unif()
        if proposal < q[slot]:
            chosen.append(slot + 1)
        else:
            chosen.append(alias[slot] + 1)
    return chosen


def sample_replace(values, size, prob):
    """``sample(values, size, replace=TRUE, prob=prob)``.

    Returns the drawn values in draw order. Positions are 1-based inside
    the probability sampler, then used to index ``values``.
    """
    series = list(values)
    n = len(series)
    weights = _normalize(prob)
    if len(weights) != n:
        raise ValueError("incorrect number of probabilities")
    heavy = sum(1 for weight in weights if n * weight > 0.1)
    if heavy > 200:
        picks = _walker_sample_replace(weights, size)
    else:
        picks = _prob_sample_replace(weights, size)
    return [series[pick - 1] for pick in picks]


def sample_indices(n, size, prob):
    """``sample.int(n, size, replace=TRUE, prob=prob)``, 1-based."""
    return sample_replace(list(range(1, n + 1)), size, prob)
