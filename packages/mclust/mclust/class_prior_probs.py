"""Iterative class prior probabilities for ``MclustDA`` (``classPriorProbs``)."""

from __future__ import annotations

import importlib.util
import math
import sys
import types
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import numpy as np

__all__ = ["classPriorProbs"]


def _predict_mclust_da(*args, **kwargs):
    pkg_name = "mclust"
    root = Path(__file__).resolve().parent
    if pkg_name not in sys.modules:
        pkg = types.ModuleType(pkg_name)
        pkg.__path__ = [str(root)]
        sys.modules[pkg_name] = pkg
    for stem in ("_mclust_mutils", "_mclust_eee", "predict_mclust_da"):
        full = f"{pkg_name}.{stem}"
        if full not in sys.modules:
            spec = importlib.util.spec_from_file_location(full, root / f"{stem}.py")
            mod = importlib.util.module_from_spec(spec)
            assert spec.loader is not None
            sys.modules[full] = mod
            spec.loader.exec_module(mod)
    fn = sys.modules[f"{pkg_name}.predict_mclust_da"].predict_mclust_da
    return fn(*args, **kwargs)


def classPriorProbs(
    object: Mapping[str, Any],
    newdata: Any | None = None,
    itmax: float = 1e3,
    eps: float | None = None,
):
    """Estimate class prior probabilities from a fitted ``MclustDA`` model."""
    if not _is_mclust_da(object):
        raise ValueError("object not of class 'MclustDA'")
    if newdata is None:
        newdata = object["data"]
    if eps is None:
        eps = math.sqrt(np.finfo(float).eps)
    z = np.asarray(_predict_mclust_da(object, newdata=newdata)["z"], dtype=float)
    class_names = list(object["models"].keys())
    prop_map = object["prop"]
    if isinstance(prop_map, Mapping):
        prop = np.array([float(prop_map[k]) for k in class_names], dtype=float)
    else:
        prop = np.asarray(prop_map, dtype=float)
    p = z.mean(axis=0)
    p0 = p + 1.0
    it = 0
    itmax_i = int(itmax)
    while np.any(np.abs(p - p0) > eps * (1.0 + np.abs(p))) and it < itmax_i:
        it += 1
        p0 = p.copy()
        z_upd = z * (p / prop)
        z_upd = z_upd / z_upd.sum(axis=1, keepdims=True)
        p = z_upd.mean(axis=0)
    return p


def _is_mclust_da(obj: Any) -> bool:
    if not isinstance(obj, Mapping):
        return False
    return "models" in obj and "prop" in obj and "data" in obj
