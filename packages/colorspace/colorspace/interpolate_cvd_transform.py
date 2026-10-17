"""Interpolate Machado color-vision-deficiency matrices (colorspace 2.1-4)."""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence

import numpy as np


def interpolate_cvd_transform(cvd, severity=1) -> np.ndarray:
    """Blend the eleven severity matrices at ``severity`` in ``[0, 1]``.

    Severity ``0`` returns the first matrix and severity ``1`` the last.
    Between those, ``10 * severity`` selects the surrounding tables. An exact
    tenth returns that table.
    """
    tables = _severity_tables(cvd)
    level = float(severity)
    if level <= 0.0:
        return tables[0].copy()
    if level >= 1.0:
        return tables[10].copy()
    slot = 10.0 * level
    low = math.floor(slot)
    high = math.ceil(slot)
    if low == high:
        return tables[low].copy()
    return (high - slot) * tables[low] + (slot - low) * tables[high]


def _severity_tables(cvd) -> list[np.ndarray]:
    if isinstance(cvd, Mapping):
        keys = list(cvd.keys())
        if keys and all(str(key).lstrip("-").isdigit() for key in keys):
            keys = sorted(keys, key=lambda key: int(key))
        matrices = [np.asarray(cvd[key], dtype=np.float64) for key in keys]
    elif isinstance(cvd, Sequence) and not isinstance(cvd, (str, bytes)):
        matrices = [np.asarray(item, dtype=np.float64) for item in cvd]
    else:
        raise ValueError("cvd must be the list of 11 severity matrices")
    if len(matrices) != 11 or any(matrix.shape != (3, 3) for matrix in matrices):
        raise ValueError("cvd must be the list of 11 severity matrices")
    return matrices
