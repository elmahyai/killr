"""Least trimmed squares regression (MASS ltsreg compatibility wrapper)."""

from __future__ import annotations

from typing import Any

from mass.errors import MassError
from mass.lqs import LqsFit, lqs


def ltsreg(x, y=None, /, *, data: dict | None = None, **kwargs: Any) -> LqsFit:
    """Resistant regression with the least trimmed squares criterion."""
    if y is None and isinstance(x, str):
        if data is None:
            raise MassError("'data' must be supplied for a formula")
        from mass.lqs_formula import lqs_formula

        return lqs_formula(x, data, method="lts", **kwargs)
    if y is None:
        raise MassError("'y' is missing")
    return lqs(x, y, method="lts", **kwargs)
