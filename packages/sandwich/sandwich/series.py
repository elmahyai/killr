"""The zoo and ts operations sandwich actually calls.

``coredata`` of a plain array is the array. A zoo value keeps that array
together with its index, which ``estfun`` copies onto the result.
"""

from __future__ import annotations

import numpy as np


class Zoo:
    """A matrix or vector with an ordered index, as ``zoo`` stores it."""

    def __init__(self, data, index=None, frequency=None):
        self.data = np.asarray(data, dtype=float)
        if self.data.ndim == 1:
            self.data = self.data.reshape(-1, 1)
        n = self.data.shape[0]
        self.index = np.arange(n) if index is None else np.asarray(index)
        self.frequency = frequency

    def __repr__(self) -> str:
        return f"zoo({self.data.shape[0]} x {self.data.shape[1]})"


def is_zoo(value) -> bool:
    return isinstance(value, Zoo)


def coredata(value):
    if isinstance(value, Zoo):
        data = value.data
        return data.ravel() if data.shape[1] == 1 else data
    return value


def zoo(data, index=None, frequency=None) -> Zoo:
    return Zoo(data, index, frequency)


def index(value):
    if isinstance(value, Zoo):
        return value.index
    raise TypeError("index() needs a zoo object")
