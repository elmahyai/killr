"""R-style simplify2array for pbsapply."""

from __future__ import annotations

from typing import Any, Sequence

import numpy as np


def simplify2array(x: Sequence[Any], *, higher: bool = True) -> Any:
    """Minimal simplify2array matching base R for pbsapply proof cases."""
    if len(x) == 0:
        return np.array([], dtype=float)
    if not _all_same_length(x):
        return list(x)
    lengths = [len(_as_vector(elem)) for elem in x]
    if len(set(lengths)) != 1:
        return list(x)
    sample = _as_vector(x[0])
    if len(sample) == 1:
        flat = [_as_vector(elem)[0] for elem in x]
        if higher:
            return np.array(flat)
        return np.array(flat)
    rows = [_as_vector(elem) for elem in x]
    return np.array(rows)


def _all_same_length(x: Sequence[Any]) -> bool:
    lengths = {len(_as_vector(elem)) for elem in x}
    return len(lengths) == 1


def _as_vector(value: Any) -> np.ndarray:
    if value is None:
        return np.array([], dtype=float)
    arr = np.asarray(value)
    if arr.ndim == 0:
        return np.array([arr.item()])
    return arr.reshape(-1)
