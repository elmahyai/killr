"""Ridge lambda diagnostics (MASS ``select`` for ``ridgelm``)."""

from __future__ import annotations

import io
import sys
from typing import Any

import numpy as np

from mass.errors import MassError
from mass.lm_ridge import Ridgelm
from mass.misc import format_numeric


def _format_value(value: float) -> str:
    return format_numeric([float(value)])[0]


def select_ridgelm(obj: Ridgelm, *, file: Any = None) -> None:
    """Print HKB, L-W, and GCV-minimizing lambdas (``select.ridgelm``)."""
    out = sys.stdout if file is None else file
    print(f"modified HKB estimator is {_format_value(obj.kHKB)} ", file=out)
    print(f"modified L-W estimator is {_format_value(obj.kLW)} ", file=out)
    gcv = np.asarray(obj.GCV, dtype=float).reshape(-1)
    if gcv.size:
        minimum = float(np.min(gcv))
        indices = np.flatnonzero(gcv == minimum) + 1
        lam = np.asarray(obj.lambda_, dtype=float).reshape(-1)[indices - 1]
        formatted = " ".join(format_numeric(lam))
        print(f"smallest value of GCV  at {formatted} ", file=out)


def select(obj: Ridgelm, *, file: Any = None) -> None:
    """Generic ``select``; only ``ridgelm`` objects are supported."""
    if isinstance(obj, Ridgelm):
        select_ridgelm(obj, file=file)
        return
    raise MassError(f"no applicable method for 'select' applied to an object of class {type(obj).__name__}")


def select_lines(obj: Ridgelm) -> list[str]:
    """Return ``select.ridgelm`` output lines without trailing newlines."""
    buffer = io.StringIO()
    select_ridgelm(obj, file=buffer)
    text = buffer.getvalue()
    if not text:
        return []
    return text.splitlines()
