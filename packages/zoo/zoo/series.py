"""Ordered observations.

The constructor arguments stay stable: data, index, frequency, regular.
NumPy holds the values. A numeric matrix is stored in Fortran order, matching R.
"""

from __future__ import annotations

from typing import Any

import numpy as np


class Zoo:
    """An ordered series. ``data`` aligns with ``index`` along the first dimension."""

    def __init__(
        self,
        data: Any,
        index: Any,
        frequency: float | None = None,
        regular: bool = False,
    ) -> None:
        if isinstance(data, np.ndarray):
            if data.ndim >= 2 and not data.flags.f_contiguous:
                self.data = np.array(data, order="F", copy=True)
            else:
                self.data = data
        else:
            self.data = np.array(data, order="F")
        self.index = index
        self.frequency = frequency
        self.regular = regular
        self.colnames = None
        self.logical = False
        self.extra = {}

    def __len__(self) -> int:
        if self.data.ndim == 0:
            return 1
        return int(self.data.shape[0])
