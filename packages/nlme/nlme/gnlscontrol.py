"""Control values for ``gnls`` (nlme ``gnlsControl``)."""

from __future__ import annotations

import math
import sys
from collections.abc import Sequence

__all__ = ["gnlsControl"]

_OPT_CHOICES = ("nlminb", "optim")
_SIGMA_ERR = "Within-group std. dev. must be a positive numeric value"


def gnlsControl(
    maxIter: float = 50,
    nlsMaxIter: float = 7,
    msMaxIter: float = 50,
    minScale: float = 0.001,
    tolerance: float = 1e-6,
    nlsTol: float = 0.001,
    msTol: float = 1e-7,
    returnObject: bool = False,
    msVerbose: bool = False,
    apVar: bool = True,
    relStep: float | None = None,
    opt: str | Sequence[str] | None = None,
    optimMethod: str = "BFGS",
    minAbsParApVar: float = 0.05,
    sigma: float | None = None,
):
    """Set control values for iterations within ``gnls``."""
    if relStep is None:
        relStep = sys.float_info.epsilon ** (1.0 / 3.0)
    sigma_val = _sigma_value(sigma)
    opt_val = _resolve_opt(opt)
    control = _Control(
        maxIter=float(maxIter),
        nlsMaxIter=float(nlsMaxIter),
        msMaxIter=float(msMaxIter),
        minScale=float(minScale),
        tolerance=float(tolerance),
        nlsTol=float(nlsTol),
        msTol=float(msTol),
        returnObject=bool(returnObject),
        msVerbose=bool(msVerbose),
        apVar=bool(apVar),
        opt=opt_val,
        optimMethod=str(optimMethod),
        minAbsParApVar=float(minAbsParApVar),
        sigma=sigma_val,
    )
    control[".relStep"] = float(relStep)
    return control


class _Control(dict):
    """Named list returned by ``gnlsControl``."""

    __slots__ = ()


def _sigma_value(sigma):
    if sigma is None:
        return 0.0
    if isinstance(sigma, (list, tuple)):
        if len(sigma) != 1:
            raise ValueError(_SIGMA_ERR)
        sigma = sigma[0]
    else:
        try:
            import numpy as np

            array = np.asarray(sigma, dtype=np.float64)
            if array.size != 1:
                raise ValueError(_SIGMA_ERR)
            sigma = float(array.reshape(-1)[0])
        except (TypeError, ValueError):
            if not isinstance(sigma, (int, float, bool)):
                raise ValueError(_SIGMA_ERR) from None
    value = float(sigma)
    if not math.isfinite(value) or value < 0:
        raise ValueError(_SIGMA_ERR)
    return value


def _resolve_opt(opt):
    if opt is None:
        return _OPT_CHOICES[0]
    if isinstance(opt, str):
        return _match_arg(opt, _OPT_CHOICES)
    if isinstance(opt, (list, tuple)):
        if len(opt) == 0:
            return _OPT_CHOICES[0]
        if len(opt) > 1:
            return _match_arg(str(opt[0]), _OPT_CHOICES)
        return _match_arg(str(opt[0]), _OPT_CHOICES)
    return _match_arg(str(opt), _OPT_CHOICES)


def _match_arg(value: str, choices: Sequence[str]) -> str:
    if value in choices:
        return value
    hits = [choice for choice in choices if choice.startswith(value)]
    if len(hits) == 1:
        return hits[0]
    if len(hits) > 1:
        raise ValueError(f"'{value}' is abbreviated")
    shown = ", ".join(f'"{choice}"' for choice in choices)
    raise ValueError(f"'arg' should be one of {shown}")
