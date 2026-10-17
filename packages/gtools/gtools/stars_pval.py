"""Significance stars from p-values (gtools 3.9.5 ``stars.pval``)."""

from __future__ import annotations

import numpy as np

__all__ = ["stars_pval"]

_CUTPOINTS = np.array([0.0, 0.001, 0.01, 0.05, 0.1, 1.0])
_SYMBOLS = ("***", "**", "*", ".", " ")
_EPS = 1e-5
_RANGE_MSG = "'x' must be between 0 and 1"
_LEGEND = (
    "0 \u2018***\u2019 0.001 \u2018**\u2019 0.01 \u2018*\u2019 "
    "0.05 \u2018.\u2019 0.1 \u2018 \u2019 1"
)


class StarsPval:
    """Character stars per p-value, with R ``legend`` attribute."""

    __slots__ = ("legend", "values")

    def __init__(self, values: np.ndarray):
        self.values = values
        self.legend = _LEGEND

    def __iter__(self):
        return iter(self.values.ravel(order="F"))

    def __len__(self):
        return self.values.size

    def __repr__(self):
        flat = self.values.ravel(order="F")
        body = " ".join(f'"{item}"' for item in flat)
        return f"[{body}]\nlegend: {self.legend!r}"


def stars_pval(p_value):
    """Map p-values to ``***/**/*/./ `` symbols like R ``stats::symnum``."""
    values = np.asarray(p_value, dtype=float)
    if values.size == 0:
        return StarsPval(np.array([], dtype=str).reshape(values.shape))

    flat = values.ravel(order="F")
    finite = flat[~np.isnan(flat)]
    if finite.size:
        minc = float(_CUTPOINTS[0])
        maxc = float(_CUTPOINTS[-1])
        if np.any(finite < minc - _EPS):
            raise ValueError(_RANGE_MSG)
        if np.any(finite > maxc + _EPS):
            raise ValueError(_RANGE_MSG)

    indices = _symnum_indices(flat)
    symbols = np.empty(flat.shape, dtype=object)
    symbols[:] = ""
    ok = ~np.isnan(flat)
    symbols[ok] = [_SYMBOLS[i - 1] for i in indices[ok]]
    shaped = symbols.reshape(values.shape, order="F")
    return StarsPval(shaped.astype(str))


def _symnum_indices(flat: np.ndarray) -> np.ndarray:
    inner = _CUTPOINTS[1:]
    out = np.searchsorted(inner, flat, side="left") + 1
    minc = float(_CUTPOINTS[0])
    near = (~np.isnan(flat)) & (np.abs(flat - minc) < _EPS)
    out[near] = 1
    return out
