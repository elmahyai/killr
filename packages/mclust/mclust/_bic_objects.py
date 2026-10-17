"""Helpers for the R mclustBIC-style objects used by the BIC functions.

A BIC object is a dict with the matrix under ``"values"`` (rows are G,
columns are model names) and the R attributes under their R names, such as
``"n"``, ``"d"``, ``"class"``, ``"criterion"``, and ``"noise"``. A bare 2-D
numpy array is accepted as a matrix with no attributes.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import numpy as np

__all__ = ["matrix_parts", "has_class", "label", "HcPairs", "with_initial_partition"]


class HcPairs(np.ndarray):
    """A two-row ``hc`` merge matrix that carries R's ``initialPartition`` attribute."""


def with_initial_partition(pairs: Any, partition: Any) -> HcPairs:
    """Attach ``initialPartition`` to the merge pairs, as R's ``hc`` does."""
    out = np.asarray(pairs, dtype=float).view(HcPairs)
    out.initialPartition = np.asarray(partition, dtype=int).reshape(-1)
    return out


def label(value: Any) -> str:
    """R's ``as.character`` for a G or model label."""
    if isinstance(value, (float, np.floating)) and float(value).is_integer():
        return str(int(value))
    return str(value)


def matrix_parts(x: Any):
    """Return ``(values, rownames, colnames, attrs)`` or ``None`` if ``x`` is not a matrix."""
    if isinstance(x, Mapping):
        raw = x.get("values")
        attrs = dict(x)
    elif isinstance(x, np.ndarray):
        raw = x
        attrs = {}
    else:
        return None
    if raw is None:
        return None
    values = np.asarray(raw, dtype=float)
    if values.ndim != 2:
        return None
    rows = attrs.get("G")
    cols = attrs.get("modelNames")
    rownames = (
        [label(v) for v in rows] if rows is not None
        else [str(i + 1) for i in range(values.shape[0])]
    )
    colnames = (
        [str(v) for v in cols] if cols is not None
        else [str(j + 1) for j in range(values.shape[1])]
    )
    return values, rownames, colnames, attrs


def has_class(x: Any, classes: tuple[str, ...]) -> bool:
    """R's ``inherits(x, classes)`` for any of ``classes``."""
    if not isinstance(x, Mapping):
        return False
    cls = x.get("class")
    if cls is None:
        return False
    if isinstance(cls, str):
        cls = [cls]
    return any(c in classes for c in cls)
