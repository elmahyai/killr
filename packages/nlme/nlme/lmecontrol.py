"""Control parameters for ``lme`` (nlme ``lmeControl``)."""

from __future__ import annotations

from typing import Any

import numpy as np

_DEFAULT_REL_STEP = float(np.finfo(np.float64).eps ** (1.0 / 3.0))


def lmeControl(
    maxIter: float = 50,
    msMaxIter: float = 50,
    tolerance: float = 1e-6,
    niterEM: float = 25,
    msMaxEval: float = 200,
    msTol: float = 1e-7,
    msVerbose: bool = False,
    returnObject: bool = False,
    gradHess: bool = True,
    apVar: bool = True,
    relStep: float = _DEFAULT_REL_STEP,
    minAbsParApVar: float = 0.05,
    opt: str = "nlminb",
    optimMethod: str = "BFGS",
    natural: bool = True,
    sigma: float | None = None,
    allow_n_lt_q: bool = False,
    **extra: Any,
) -> dict[str, Any]:
    """Return the ``lme`` control list as a dict with R's field names.

    ``relStep`` is stored as ``.relStep`` and ``allow_n_lt_q`` as
    ``allow.n.lt.q``.  Extra keyword arguments are appended, as R's ``...``.
    """
    if sigma is None:
        sigma_value = 0.0
    elif not np.isfinite(sigma) or sigma < 0:
        raise ValueError("Within-group std. dev. must be a positive numeric value")
    else:
        sigma_value = float(sigma)
    if opt not in ("nlminb", "optim"):
        raise ValueError("'opt' must be one of \"nlminb\" or \"optim\"")
    control: dict[str, Any] = {
        "maxIter": maxIter,
        "msMaxIter": msMaxIter,
        "tolerance": tolerance,
        "niterEM": niterEM,
        "msMaxEval": msMaxEval,
        "msTol": msTol,
        "msVerbose": msVerbose,
        "returnObject": returnObject,
        "gradHess": gradHess,
        "apVar": apVar,
        ".relStep": relStep,
        "opt": opt,
        "optimMethod": optimMethod,
        "minAbsParApVar": minAbsParApVar,
        "natural": natural,
        "sigma": sigma_value,
        "allow.n.lt.q": allow_n_lt_q,
    }
    control.update(extra)
    return control
