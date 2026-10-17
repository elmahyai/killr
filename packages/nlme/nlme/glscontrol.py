"""Control values for ``gls`` fits (nlme ``glsControl``)."""

from __future__ import annotations

import math
import sys
from collections.abc import Sequence

__all__ = ["glsControl"]

_OPT_CHOICES = ("nlminb", "optim")
_SIGMA_ERR = "Within-group std. dev. must be a positive numeric value"


def glsControl(
    maxIter: float = 50,
    msMaxIter: float = 200,
    tolerance: float = 1e-6,
    msTol: float = 1e-7,
    msVerbose: bool = False,
    singular_ok: bool = False,
    returnObject: bool = False,
    apVar: bool = True,
    relStep: float | None = None,
    opt: str | Sequence[str] | None = None,
    optimMethod: str = "BFGS",
    minAbsParApVar: float = 0.05,
    natural: bool = True,
    sigma: float | None = None,
) -> dict:
    """Control parameters for ``gls``; keys use the R list names.

    R's ``singular.ok`` is ``singular_ok`` and R's ``.relStep`` is ``relStep``.
    """
    if relStep is None:
        relStep = sys.float_info.epsilon ** (1.0 / 3.0)
    return {
        "maxIter": maxIter,
        "msMaxIter": msMaxIter,
        "tolerance": tolerance,
        "msTol": msTol,
        "msVerbose": msVerbose,
        "singular.ok": singular_ok,
        "returnObject": returnObject,
        "apVar": apVar,
        "minAbsParApVar": minAbsParApVar,
        ".relStep": float(relStep),
        "opt": _resolve_opt(opt),
        "optimMethod": optimMethod,
        "natural": natural,
        "sigma": _sigma_value(sigma),
    }


def _sigma_value(sigma) -> float:
    if sigma is None:
        return 0.0
    if isinstance(sigma, (list, tuple)):
        if len(sigma) != 1:
            raise ValueError(_SIGMA_ERR)
        sigma = sigma[0]
    if isinstance(sigma, bool) or not isinstance(sigma, (int, float)):
        raise ValueError(_SIGMA_ERR)
    value = float(sigma)
    if not math.isfinite(value) or value < 0:
        raise ValueError(_SIGMA_ERR)
    return value


def _resolve_opt(opt) -> str:
    """``match.arg(opt)`` with the default ``c("nlminb", "optim")``."""
    if opt is None:
        return _OPT_CHOICES[0]
    if isinstance(opt, (list, tuple)):
        if len(opt) == 0 or tuple(opt) == _OPT_CHOICES:
            return _OPT_CHOICES[0]
        if len(opt) != 1:
            raise ValueError("'arg' must be of length 1")
        opt = opt[0]
    value = str(opt)
    if value in _OPT_CHOICES:
        return value
    hits = [choice for choice in _OPT_CHOICES if choice.startswith(value)]
    if len(hits) == 1:
        return hits[0]
    shown = ", ".join(f'"{choice}"' for choice in _OPT_CHOICES)
    raise ValueError(f"'arg' should be one of {shown}")
