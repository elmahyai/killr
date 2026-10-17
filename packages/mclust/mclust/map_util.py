"""Hard class assignment from posterior rows (``map``)."""

from __future__ import annotations

import importlib.util
import sys
import warnings
from pathlib import Path
from typing import Any

import numpy as np

__all__ = ["map"]

_WARN_DEFAULT: bool | None = None


def _default_warn() -> bool:
    global _WARN_DEFAULT
    if _WARN_DEFAULT is not None:
        return _WARN_DEFAULT
    parent = Path(__file__).resolve().parent
    pkg_root = parent.parent
    if str(pkg_root) not in sys.path:
        sys.path.insert(0, str(pkg_root))
    em_path = parent / "em_control.py"
    em_spec = importlib.util.spec_from_file_location("mclust.em_control", em_path)
    assert em_spec and em_spec.loader
    em_mod = importlib.util.module_from_spec(em_spec)
    sys.modules.setdefault("mclust", type(sys)("mclust"))
    sys.modules["mclust.em_control"] = em_mod
    em_spec.loader.exec_module(em_mod)
    opt_path = parent / "mclust_options.py"
    opt_spec = importlib.util.spec_from_file_location("mclust.mclust_options", opt_path)
    assert opt_spec and opt_spec.loader
    opt_mod = importlib.util.module_from_spec(opt_spec)
    opt_spec.loader.exec_module(opt_mod)
    _WARN_DEFAULT = bool(opt_mod.mclust_options("warn"))
    return _WARN_DEFAULT


def map(z: Any, warn: Any | None = None, **kwargs: Any) -> np.ndarray:
    """Assign each row of ``z`` to the first column attaining the row maximum (1-based)."""
    if warn is None:
        warn = _default_warn()
    mat = np.asarray(z, dtype=float)
    if mat.ndim == 1:
        mat = mat.reshape(1, -1)
    n, k = mat.shape
    cl = np.empty(n, dtype=float)
    for i in range(n):
        row = mat[i, :]
        mx = float(np.max(row))
        js = np.flatnonzero(row == mx) + 1
        cl[i] = float(js[0])
    if warn:
        assigned = np.sort(np.unique(cl.astype(int)))
        missing = [j for j in range(1, k + 1) if j not in set(assigned.tolist())]
        if missing:
            warnings.warn(
                f"no assignment to {','.join(str(j) for j in missing)}",
                RuntimeWarning,
                stacklevel=2,
            )
    return cl
