"""Default diagnostics method when the object is not deSolve (``diagnostics.default``)."""

from __future__ import annotations

import warnings
from typing import Any

import numpy as np

from deSolve.rk4 import DeSolveMatrix


def _class_vector(obj: Any) -> tuple[str, ...]:
    classes = getattr(obj, "classes", None)
    if classes:
        return tuple(str(name) for name in classes)
    if isinstance(obj, DeSolveMatrix):
        return ("deSolve", "matrix")
    if isinstance(obj, np.ndarray):
        if obj.dtype.kind == "i":
            return ("integer",)
        if obj.dtype.kind == "f":
            return ("numeric",)
        if obj.dtype.kind == "b":
            return ("logical",)
        return ("array",)
    if isinstance(obj, (list, tuple)):
        if not obj:
            return ("NULL",)
        return ("list",)
    if isinstance(obj, (int, np.integer)):
        return ("integer",)
    if isinstance(obj, (float, np.floating)):
        return ("numeric",)
    if isinstance(obj, bool):
        return ("logical",)
    name = type(obj).__name__
    return (name,)


def diagnostics_default(obj, **kwargs):
    """Warn that no diagnostics exist for this object's class."""
    del kwargs
    class_text = "".join(_class_vector(obj))
    warnings.warn(f"No diagnostics available for class '{class_text}'")
    return None
