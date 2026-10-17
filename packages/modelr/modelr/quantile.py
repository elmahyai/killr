"""stats::quantile types 1 and 7, matching R 4.5.

Type 7 is the default. Its index is ``1 + (n - 1) * p`` and the fuzz is 0.
Type 1 is the inverse empirical cdf, which typical() uses for integers.
"""

from __future__ import annotations

import math

from modelr.frame import is_na


def quantile(x, probs, type=7, na_rm=False):
    """Quantiles of one numeric vector. ``probs`` is a sequence in [0, 1]."""
    probabilities = [float(p) for p in probs]
    if na_rm:
        values = [float(v) for v in x if not is_na(v)]
    else:
        values = []
        for value in x:
            if is_na(value):
                return [float("nan")] * len(probabilities)
            values.append(float(value))
    if not values or not probabilities:
        return [float("nan")] * len(probabilities)
    ordered = sorted(values)
    n = len(ordered)
    if type == 7:
        return [_type7(ordered, n, p) for p in probabilities]
    if type == 1:
        return [_type1(ordered, n, p) for p in probabilities]
    raise ValueError("quantile type must be 1 or 7")


def _type7(ordered, n, prob):
    index = 1.0 + max(n - 1, 0) * prob
    lo = math.floor(index)
    hi = math.ceil(index)
    left = ordered[lo - 1]
    if index <= lo or hi == lo:
        return float(left)
    right = ordered[hi - 1]
    if left == right:
        return float(left)
    weight = index - lo
    return (1.0 - weight) * left + weight * right


def _type1(ordered, n, prob):
    """Inverse empirical cdf. The index fuzz is 0, as in R 4.5."""
    nppm = n * prob
    j = math.floor(nppm)
    # h is 1 when the index is strictly above an integer.
    if nppm > j:
        pick = j + 1
    else:
        pick = j
    # The same padded ends as stats::quantile: two copies on each side.
    if pick < 1:
        return float(ordered[0])
    if pick > n:
        return float(ordered[-1])
    return float(ordered[pick - 1])
