"""Generic diagnostics dispatcher (deSolve ``diagnostics``)."""

from __future__ import annotations

from typing import Any

from deSolve.diagnostics_default import _class_vector
from deSolve.rk4 import DeSolveMatrix


def diagnostics(obj, **kwargs):
    """Print or report integrator diagnostics for a solved model object."""
    classes = _class_vector(obj)
    if "deSolve" in classes or isinstance(obj, DeSolveMatrix):
        from deSolve.diagnostics_deSolve import diagnostics_deSolve

        return diagnostics_deSolve(obj, **kwargs)
    from deSolve.diagnostics_default import diagnostics_default

    return diagnostics_default(obj, **kwargs)
