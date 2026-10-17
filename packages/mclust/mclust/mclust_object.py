"""``Mclust``: the fitted Gaussian mixture object (mclust 6.1.3, R/mclust.R).

R calls ``mclustBIC`` with the given ``G`` and ``modelNames`` (the default is
``G = 1:9``), takes the best entry through ``summary.mclustBIC``, then adds
``icl``, ``hypvol`` and ``df``. The ``call`` element is not kept, because it is
the R call object. The returned dictionary has the same fields in R's order.

``hypvol`` is ``1 / Vinv`` when the noise model is used, and NA otherwise.

``em`` is not used on this path. R's ``mclustBIC`` calls ``hc``, ``estep``
and ``me`` directly.
"""

from __future__ import annotations

from typing import Any

import numpy as np

from .bic_family import mclustBIC
from .em_control import em_control
from .mclust_options import mclust_options
from .model_metadata import nMclustParams
from .summary_mclust_bic import summaryMclustBIC, summaryMclustBICn

__all__ = ["Mclust", "checkDataMatrix", "icl_Mclust"]


def checkDataMatrix(x: Any) -> np.ndarray:
    """Return ``x`` as a matrix with incomplete rows and constant columns removed.

    Mirrors ``checkDataMatrix`` in ``R/util.R``. A vector becomes one column.
    """
    a = np.asarray(x, dtype=float)
    if a.ndim == 1:
        a = a.reshape(-1, 1)
    if a.ndim != 2:
        raise ValueError("data must be a vector or a matrix")
    a = a[~np.isnan(a).any(axis=1)]
    constant = np.flatnonzero(a.min(axis=0) == a.max(axis=0))
    if constant.size:
        a = np.delete(a, constant, axis=1)
    return a


def _equal_pro(control: Any) -> bool:
    if control is None:
        return False
    if isinstance(control, dict):
        return bool(control.get("equalPro", False))
    return bool(getattr(control, "equalPro", False))


def icl_Mclust(object_: dict[str, Any]) -> float:
    """``icl.Mclust``: BIC plus twice the sum of the classification log-densities."""
    z = np.asarray(object_["z"], dtype=float)
    if z.ndim == 1:
        z = z.reshape(-1, 1)
    n = z.shape[0]
    C = np.zeros_like(z)
    C[np.arange(n), np.argmax(z, axis=1)] = 1.0
    logz = np.where(z > 0, np.log(np.where(z > 0, z, 1.0)), 0.0)
    return float(object_["bic"] + 2.0 * np.sum(C * logz))


def Mclust(
    data: Any,
    G: Any = None,
    modelNames: Any = None,
    prior: Any = None,
    control: Any = None,
    initialization: Any = None,
    warn: Any = None,
    x: Any = None,
    verbose: bool = False,
    Vinv: Any = None,
    **kwargs: Any,
) -> dict[str, Any] | None:
    """Fit a Gaussian mixture and return the R ``Mclust`` fields.

    R passes every argument of the call on to ``mclustBIC``, so ``initialization``
    (``hcPairs``, ``subset``, ``noise``) and ``Vinv`` select the same starts here.
    When the BIC object has a noise component, the noise summary is used and
    ``hypvol`` is ``1 / Vinv``.
    """
    del kwargs
    if control is None:
        control = em_control()
    if warn is None:
        warn = mclust_options("warn")

    values = checkDataMatrix(data)
    n, d = values.shape

    # R: the G and modelNames of the BIC object are passed on to summary.
    BIC = mclustBIC(
        values, G=G, modelNames=modelNames, prior=prior, control=control,
        initialization=initialization, Vinv=Vinv, warn=warn, x=x, verbose=verbose,
    )
    G_all = BIC.get("G")
    model_names = BIC.get("modelNames")
    noise = (BIC.get("initialization") or {}).get("noise") is not None
    summarize = summaryMclustBICn if noise else summaryMclustBIC
    summary = summarize(BIC, values, G=G_all, modelNames=model_names)
    if summary.get("modelName") is None:
        # R: "no model(s) could be fitted", then return NULL.
        return None

    # R: Sumry$bic <- Sumry$bic[1]. With one component the bic is the top-3
    # vector, so its first entry is the best BIC; otherwise it is one value.
    summary = dict(summary)
    summary["bic"] = float(np.atleast_1d(summary["bic"])[0])
    summary["icl"] = icl_Mclust(summary)
    vinv_attr = BIC.get("Vinv")
    summary["hypvol"] = float("nan") if vinv_attr is None else 1.0 / float(vinv_attr)
    equal_pro = _equal_pro(control)
    model = str(summary["modelName"])
    G_fit = int(summary["G"])
    has_noise = not np.isnan(summary["hypvol"])
    df = nMclustParams(model, d, G_fit, noise=has_noise, equalPro=equal_pro)

    return {
        "data": values,
        "modelName": model,
        "n": n,
        # R: summaryMclustBICn sets d = ncol(data), which is NULL for a vector input,
        # so a noise fit on one-dimensional data reports d = NULL.
        "d": None if (noise and d == 1) else d,
        "G": G_fit,
        "BIC": BIC,
        "loglik": summary["loglik"],
        "df": df,
        "bic": summary["bic"],
        "icl": summary["icl"],
        "hypvol": summary["hypvol"],
        "parameters": summary["parameters"],
        "z": summary["z"],
        "classification": summary["classification"],
        "uncertainty": summary["uncertainty"],
    }
