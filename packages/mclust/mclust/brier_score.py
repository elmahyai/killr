"""Brier score for probabilistic classifiers (``BrierScore``)."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any

import numpy as np

__all__ = ["BrierScore"]

_UNMAP = None


def _unmap(*args: Any, **kwargs: Any) -> np.ndarray:
    global _UNMAP
    if _UNMAP is None:
        path = Path(__file__).resolve().parent / "_mclust_mutils.py"
        spec = importlib.util.spec_from_file_location("mclust_mutils_local", path)
        assert spec and spec.loader
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        _UNMAP = mod.unmap
    return _UNMAP(*args, **kwargs)


def _is_r_factor(obj: Any) -> bool:
    return hasattr(obj, "levels") and hasattr(obj, "codes") and not isinstance(obj, (str, bytes))


def BrierScore(z: Any, class_: Any) -> float:
    """Mean squared error between row-normalized ``z`` and the one-hot ``unmap`` of ``class_``."""
    probs = np.asfortranarray(np.asarray(z, dtype=float))
    row_sums = probs.sum(axis=1, keepdims=True)
    probs = probs / row_sums

    if _is_r_factor(class_):
        groups = list(class_.levels)
        class_arr = np.asarray(class_.codes, dtype=int)
    else:
        raw = np.asarray(class_, dtype=object).ravel()
        if raw.size and all(isinstance(v, (int, np.integer, float, np.floating)) and not isinstance(v, (bool, np.bool_)) for v in raw):
            u = np.sort(np.unique(np.asarray(class_, dtype=float)))
            if np.all(u == np.round(u)):
                groups = [int(g) for g in u]
            else:
                groups = u.tolist()
        else:
            groups = sorted({str(v) for v in raw})
        if all(isinstance(g, int) for g in groups):
            class_arr = np.asarray(class_, dtype=int)
        else:
            class_arr = np.asarray(class_, dtype=object)

    cl = _unmap(class_arr, groups=groups)
    if cl.shape != probs.shape:
        raise ValueError("input arguments do not match!")
    return float(np.sum((cl - probs) ** 2) / (2 * cl.shape[0]))
