"""Logistic sigmoid and its first two derivatives."""

from __future__ import annotations

import math


def sigmoid(x):
    return 1 / (1 + math.exp(-x))


def dsigmoid(x):
    value = sigmoid(x)
    return value * (1 - value)


def d2sigmoid(x):
    return dsigmoid(x) * (1 - 2 * sigmoid(x))
