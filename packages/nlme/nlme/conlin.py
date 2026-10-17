"""Condensed linear model passed through ``recalc``, ``glsEstimate``, and ``glsApVar``.

R keeps this as the list ``conLin`` with ``Xy``, ``dims``, ``logLik``, ``sigma``,
and ``fixedSigma``. The ``names`` field holds ``colnames(Xy)`` so that the
coefficient names of ``glsEstimate`` can be reported.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

import numpy as np

__all__ = ["ConLin"]


@dataclass(slots=True)
class ConLin:
    """``conLin`` list: ``Xy`` is column-major ``N`` by ``p + 1`` (response last)."""

    Xy: np.ndarray
    dims: Mapping[str, int]
    logLik: float = 0.0
    sigma: float = 0.0
    fixedSigma: bool = False
    names: tuple[str, ...] | None = None
