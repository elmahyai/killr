"""Discrete distribution on a finite set of values."""

from __future__ import annotations

import random


def _check(probs, values):
    if values is None:
        values = list(range(1, len(probs) + 1))
    if len(probs) != len(values):
        raise ValueError("probs and values must have the same length.")
    if any(value < 0 for value in probs):
        raise ValueError("probs must not contain negative values.")
    return list(values), [float(value) for value in probs]


def ddiscrete(x, probs, values=None):
    values, probs = _check(probs, values)
    total = sum(probs)
    weights = [value / total for value in probs]
    out = []
    for item in x:
        found = 0.0
        for value, weight in zip(values, weights):
            if value == item:
                found = weight
                break
        out.append(found)
    return out


def pdiscrete(q, probs, values=None):
    values, probs = _check(probs, values)
    total = sum(probs)
    weights = [value / total for value in probs]
    out = []
    for item in q:
        out.append(sum(weight for value, weight in zip(values, weights) if value <= item))
    return out


def qdiscrete(p, probs, values=None):
    values, probs = _check(probs, values)
    total = sum(probs)
    cdf = []
    running = 0.0
    for value in probs:
        running += value
        cdf.append(running / total)
    out = []
    for item in p:
        index = len(values) - sum(item <= knot for knot in cdf) + 1
        out.append(values[index - 1])
    return out


def rdiscrete(n, probs, values=None):
    values, probs = _check(probs, values)
    return random.choices(values, weights=probs, k=n)
