"""logLik method for Mclust objects (``logLik.Mclust``)."""

from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path
from typing import Any, Mapping

import numpy as np

__all__ = ["logLik_Mclust", "MclustLogLik"]


class MclustLogLik:
    """Scalar log-likelihood with ``df`` and ``nobs`` like R ``logLik``."""

    __slots__ = ("value", "df", "nobs")

    def __init__(self, value: float, df: int, nobs: int) -> None:
        self.value = float(value)
        self.df = int(df)
        self.nobs = int(nobs)

    def __float__(self) -> float:
        return self.value

    def __array__(self, dtype=None):
        return np.asarray(self.value, dtype=dtype)


def logLik_Mclust(object: Mapping[str, Any], **kwargs: Any) -> MclustLogLik:
    """Return log-likelihood, degrees of freedom, and observation count for an Mclust fit."""
    _ = kwargs
    loglik = object.get("loglik")
    if loglik is None:
        l = float(_sum_dens(object))
    else:
        l = float(loglik)

    df = object.get("df")
    if df is None:
        hypvol = object.get("hypvol")
        if hypvol is None:
            noise = False
        else:
            noise = not (isinstance(hypvol, float) and np.isnan(hypvol))
        equal_pro = _equal_pro_from_bic(object.get("BIC"))
        df = _n_mclust_params(
            str(object["modelName"]),
            int(object["d"]),
            int(object["G"]),
            noise=noise,
            equal_pro=equal_pro,
        )
    else:
        df = int(df)

    nobs = int(object["n"])
    return MclustLogLik(l, df, nobs)


def _equal_pro_from_bic(bic: Any) -> bool:
    if bic is None:
        return False
    if isinstance(bic, Mapping):
        control = bic.get("control")
    else:
        control = getattr(bic, "control", None)
    if isinstance(control, Mapping):
        return bool(control.get("equalPro", False))
    return False


_MUTILS: Any | None = None
_EM: Any | None = None


def _n_mclust_params(*args: Any, **kwargs: Any) -> int:
    global _MUTILS
    if _MUTILS is None:
        path = Path(__file__).with_name("_mclust_mutils.py")
        spec = importlib.util.spec_from_file_location("_mclust_mutils_ll", path)
        if spec is None or spec.loader is None:
            raise ImportError("_mclust_mutils.py not found")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        _MUTILS = mod
    return int(_MUTILS.n_mclust_params(*args, **kwargs))


def _load_em() -> Any:
    global _EM
    if _EM is not None:
        return _EM
    root = Path(__file__).resolve().parent
    spec_u = importlib.util.spec_from_file_location("_mclust_mutils_em", root / "_mclust_mutils.py")
    if spec_u is None or spec_u.loader is None:
        raise ImportError("_mclust_mutils.py not found")
    utils = importlib.util.module_from_spec(spec_u)
    spec_u.loader.exec_module(utils)
    pkg = types.ModuleType("mclust")
    sys.modules.setdefault("mclust", pkg)
    sys.modules["mclust._mclust_mutils"] = utils
    spec = importlib.util.spec_from_file_location("_mclust_em_for_ssc_ll", root / "_mclust_em_for_ssc.py")
    if spec is None or spec.loader is None:
        raise ImportError("_mclust_em_for_ssc.py not found")
    em = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(em)
    _EM = em
    return em


_CDENS_ES: dict[str, str] = {
    "EII": "eseii",
    "VII": "esvii",
    "EEI": "eseei",
    "VEI": "esvei",
    "EVI": "esevi",
    "VVI": "esvvi",
}


def _sum_dens(object: Mapping[str, Any]) -> float:
    data = np.asarray(object["data"], dtype=float)
    model_name = str(object["modelName"])
    parameters = object["parameters"]
    logden = _dens(data, model_name, parameters, logarithm=True)
    return float(np.sum(logden))


def _dens(
    data: np.ndarray,
    model_name: str,
    parameters: Mapping[str, Any],
    *,
    logarithm: bool,
) -> np.ndarray:
    alias = {"X": "E", "XII": "EII", "XXI": "EEI", "XXX": "EEE"}
    model_name = alias.get(model_name, model_name)
    log_cden = _cdens(data, model_name, parameters, logarithm=True)
    pro = parameters.get("pro")
    if pro is None:
        raise ValueError("mixing proportions must be supplied")
    pro = np.asarray(pro, dtype=float)
    noise = parameters.get("Vinv") is not None
    if noise:
        pro_noise = float(pro[-1])
        pro = pro[:-1]
        log_cden = np.asarray(log_cden, dtype=float)
        if log_cden.ndim == 1:
            log_cden = log_cden.reshape(-1, 1)
    else:
        pro_noise = None
    proz = pro == 0
    if np.any(proz):
        pro = pro[~proz]
        log_cden = log_cden[:, ~proz]
    em = _load_em()
    logden = em._logsumexp_fortran(np.asarray(log_cden, dtype=float), np.log(pro))
    if noise:
        logden = np.log(np.exp(logden) + pro_noise * float(parameters["Vinv"]))
    return logden if logarithm else np.exp(logden)


def _cdens(
    data: np.ndarray,
    model_name: str,
    parameters: Mapping[str, Any],
    *,
    logarithm: bool,
) -> np.ndarray:
    if model_name == "EEE":
        em = _load_em()
        z = em._cdens_eee(data, dict(parameters), logarithm=logarithm, warn=False)
        return z
    spec = _CDENS_ES.get(model_name)
    if spec is None:
        # Models outside the local table (for example E, the univariate
        # equal-variance model) go through the translated cdens dispatcher.
        from mclust.cdens import cdens as _cdens_dispatch

        out = _cdens_dispatch(data, model_name, dict(parameters),
                              logarithm=logarithm, warn=False)
        # Some cdens functions return the n x G matrix itself, others a dict with "z".
        z = out["z"] if isinstance(out, Mapping) else out
        return np.asarray(z, dtype=float)
    em = _load_em()
    z, _ = em._estep_es(model_name, spec, data, dict(parameters), warn=False, cdens_only=True)
    if not logarithm:
        z = np.exp(z)
    return z
