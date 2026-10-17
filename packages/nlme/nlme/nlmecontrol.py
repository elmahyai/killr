"""Control values for nlme iterations (nlme ``nlmeControl``)."""

from __future__ import annotations

import math
import sys
from typing import Any, Sequence

__all__ = ["nlmeControl"]

_OPT_CHOICES = ("nlminb", "nlm")
_SIGMA_ERR = "Within-group std. dev. must be a positive numeric value"


def nlmeControl(
    maxIter: float = 50,
    pnlsMaxIter: float = 7,
    msMaxIter: float = 50,
    minScale: float = 0.001,
    tolerance: float = 1e-5,
    niterEM: float = 25,
    pnlsTol: float = 0.001,
    msTol: float = 0.000001,
    returnObject: bool = False,
    msVerbose: bool = False,
    msWarnNoConv: bool = True,
    gradHess: bool = True,
    apVar: bool = True,
    relStep: float | None = None,
    minAbsParApVar: float = 0.05,
    opt: str | Sequence[str] | None = None,
    natural: bool = True,
    sigma: float | Sequence[float] | None = None,
    **extra: Any,
) -> dict[str, Any]:
    """Set control values for iterations within ``nlme``.

    Returns an ordered mapping with the same element names and order as the R
    list. Extra keyword arguments are appended after ``sigma``, as R's ``...``.
    """
    if relStep is None:
        relStep = sys.float_info.epsilon ** (1.0 / 3.0)
    sigma_val = 0.0 if sigma is None else _sigma_value(sigma)
    control: dict[str, Any] = {
        "maxIter": float(maxIter),
        "pnlsMaxIter": float(pnlsMaxIter),
        "msMaxIter": float(msMaxIter),
        "minScale": float(minScale),
        "tolerance": float(tolerance),
        "niterEM": float(niterEM),
        "pnlsTol": float(pnlsTol),
        "msTol": float(msTol),
        "returnObject": bool(returnObject),
        "msVerbose": bool(msVerbose),
        "msWarnNoConv": bool(msWarnNoConv),
        "gradHess": bool(gradHess),
        "apVar": bool(apVar),
        ".relStep": float(relStep),
        "minAbsParApVar": float(minAbsParApVar),
        "opt": _match_arg_opt(opt),
        "natural": bool(natural),
        "sigma": sigma_val,
    }
    control.update(extra)
    return control


def _sigma_value(sigma: Any) -> float:
    """Validate ``sigma`` like the R check ``!is.finite(sigma) || length != 1 || sigma < 0``."""
    if isinstance(sigma, (list, tuple)):
        if len(sigma) != 1:
            raise ValueError(_SIGMA_ERR)
        sigma = sigma[0]
    try:
        value = float(sigma)
    except (TypeError, ValueError):
        raise ValueError(_SIGMA_ERR) from None
    if not math.isfinite(value) or value < 0:
        raise ValueError(_SIGMA_ERR)
    return value


def _match_arg_opt(opt: str | Sequence[str] | None) -> str:
    """Emulate ``match.arg(opt)`` with choices ``c("nlminb", "nlm")``."""
    if opt is None:
        return _OPT_CHOICES[0]
    if isinstance(opt, str):
        return _match_one(opt)
    values = list(opt)
    if len(values) == 0:
        return _OPT_CHOICES[0]
    if tuple(values) == _OPT_CHOICES:
        return _OPT_CHOICES[0]
    if len(values) > 1:
        raise ValueError("'arg' must be of length 1")
    return _match_one(str(values[0]))


def _match_one(value: str) -> str:
    if value in _OPT_CHOICES:
        return value
    hits = [choice for choice in _OPT_CHOICES if choice.startswith(value)]
    if len(hits) == 1 and value != "":
        return hits[0]
    shown = ", ".join(f'"{choice}"' for choice in _OPT_CHOICES)
    raise ValueError(f"'arg' should be one of {shown}")
