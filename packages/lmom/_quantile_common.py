"""Shared validation and array handling for lmom quantile functions."""

from __future__ import annotations

import numpy as np


def probabilities(f) -> np.ndarray:
    values = np.asarray(f, dtype=np.float64)
    if np.any((values < 0) | (values > 1)):
        raise ValueError("probabilities must be between 0 and 1")
    return values


def parameters(para, length: int) -> np.ndarray:
    values = np.asarray(para, dtype=np.float64)
    if values.size != length:
        raise ValueError("parameter vector has wrong length")
    if np.any(np.isnan(values)):
        raise ValueError("missing values in parameter vector")
    return values
