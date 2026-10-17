"""A sequence across the range of a vector."""

from __future__ import annotations

import math

from modelr.frame import is_na
from modelr.pretty import seq_by, seq_length
from modelr.quantile import quantile


def seq_range(x, n=None, by=None, trim=None, expand=None, pretty=False):
    if n is not None and by is not None:
        raise ValueError("May only specify one of `n` and `by`")
    values = [float(value) for value in x if not is_na(value)]
    if trim is not None:
        low, high = quantile(values, [trim / 2, 1 - trim / 2], type=7, na_rm=True)
    else:
        low, high = min(values), max(values)
    if expand is not None:
        span = high - low
        low = low - expand / 2 * span
        high = high + expand / 2 * span
    if by is None:
        if pretty:
            from modelr.pretty import pretty as pretty_breaks

            return pretty_breaks([low, high], n)
        return seq_length(low, high, n)
    if pretty:
        low = math.floor(low / by) * by
        high = math.ceil(high / by) * by
    return seq_by(low, high, by)
