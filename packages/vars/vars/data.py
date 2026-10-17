"""The Canada data set shipped with vars."""

from pathlib import Path

import numpy as np


class Frame(np.ndarray):
    """A numeric matrix that also carries column names."""

    def __new__(cls, values, columns):
        obj = np.asarray(values, dtype=float).view(cls)
        obj.columns = list(columns)
        return obj

    def __array_finalize__(self, obj):
        if obj is None:
            return
        self.columns = getattr(obj, "columns", None)


def Canada():
    """Quarterly Canadian series e, prod, rw, and U from vars."""
    path = Path(__file__).with_name("Canada.csv")
    raw = np.genfromtxt(path, delimiter=",", names=True)
    values = np.column_stack([raw[name] for name in raw.dtype.names])
    return Frame(values, raw.dtype.names)
