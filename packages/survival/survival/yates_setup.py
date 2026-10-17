"""Prediction hooks for yates (survival::yates_setup).

R dispatches on the class of the fit. Python keeps the three methods as
ordinary functions and a small dispatcher that picks one by class.

The coxph method's predict = "survival" branch calls survfit(fit, censor = FALSE)
for the fit's default curve (no newdata, no strata, no weights or offset). That
curve is built from coxsurv_fit, which needs the fit's stored x matrix. The
survival prediction returns a dict with "predict" and "summary", as R's list does.
"""

from __future__ import annotations

import warnings
from statistics import NormalDist
from typing import Any, Callable

import numpy as np

from survival._yates_mm import YatesError, _match_arg
from survival.coxsurv_fit import coxsurv_fit
from survival.survfit_confint import survfit_confint

_CTYPE = {"exact": 1, "breslow": 1, "efron": 2}


def _component(obj: Any, name: str) -> Any:
    if isinstance(obj, dict):
        return obj.get(name)
    return getattr(obj, name, None)


def _classes(fit: Any) -> list[str]:
    klass = _component(fit, "class")
    if klass is None:
        klass = _component(fit, "class_")
    if klass is None:
        return []
    if isinstance(klass, str):
        return [klass]
    return [str(k) for k in klass]


def _first_class(fit: Any) -> str:
    classes = _classes(fit)
    return classes[0] if classes else "default"


def _has_special(fit: Any, name: str) -> bool:
    specials = _component(_component(fit, "terms"), "specials")
    return bool(specials) and bool(_component(specials, name))


def _keep_events(curve: dict[str, Any], keep: np.ndarray) -> dict[str, Any]:
    """survfit's censor = FALSE step: keep rows with n.event > 0 in every vector and matrix."""
    out: dict[str, Any] = {}
    for key, value in curve.items():
        arr = np.asarray(value)
        if arr.ndim == 2 or (arr.ndim == 1 and arr.size == keep.size):
            out[key] = arr[keep]
        else:
            out[key] = value
    return out


def _coxph_baseline(fit: Any) -> dict[str, Any]:
    """survfit(fit, censor = FALSE) for a coxph fit with no newdata (survfit.coxph default path)."""
    if _has_special(fit, "strata"):
        raise YatesError("stratified models not yet supported")
    if _component(fit, "weights") is not None or _has_special(fit, "offset"):
        raise NotImplementedError("weights and offsets in the coxph survival branch are not translated")
    x = _component(fit, "x")
    if x is None:
        raise NotImplementedError("the coxph survival branch needs the stored x matrix (fit with x = TRUE)")
    means = _component(fit, "means")
    means = np.zeros(0) if means is None else np.asarray(means, dtype=float).reshape(-1)
    if means.size == 0:
        raise NotImplementedError("the coxph survival branch for a model with no covariates is not translated")
    y = np.asarray(_component(fit, "y"), dtype=float)
    X = np.asarray(x, dtype=float).reshape(y.shape[0], -1)
    coef = _component(fit, "coefficients")
    coef = np.asarray(list(coef.values()) if isinstance(coef, dict) else coef, dtype=float).reshape(-1)
    beta = np.where(np.isnan(coef), 0.0, coef)
    xcenter = float(np.sum(means * beta))
    risk = np.exp(X @ beta - xcenter)
    varmat = np.asarray(_component(fit, "var"), dtype=float)
    ctype = _CTYPE[str(_component(fit, "method"))]
    curve = coxsurv_fit(
        ctype=ctype,
        stype=2,
        se_fit=True,
        varmat=varmat,
        cluster=None,
        y=y,
        x=X,
        wt=None,
        risk=risk,
        x2=means.reshape(1, -1),
        risk2=np.array([1.0]),
    )
    keep = np.asarray(curve["n.event"]) > 0
    out = _keep_events(curve, keep)
    ci = survfit_confint(out["surv"], out["std.err"], logse=True, conf_type="log", conf_int=0.95)
    out["lower"] = ci["lower"]
    out["upper"] = ci["upper"]
    out["conf.type"] = "log"
    out["conf.int"] = 0.95
    return out


def _coxph_survival(fit: Any, options: Any) -> dict[str, Any]:
    """The predict = "survival" closures: mean survival and survival at each eta."""
    baseline = _coxph_baseline(fit)
    time = np.asarray(baseline["time"], dtype=float)
    rmean = _component(options, "rmean")
    if rmean is None:
        rmean = float(np.max(time))
    cumhaz = np.concatenate([[0.0], np.asarray(baseline["cumhaz"], dtype=float)])
    tt = np.concatenate([np.diff(np.concatenate([[0.0], np.minimum(rmean, time)])), [0.0]])
    conf_int = float(baseline["conf.int"])

    def predict(eta: Any, *args: Any, **kwargs: Any) -> np.ndarray:
        eta_arr = np.asarray(eta, dtype=float).reshape(-1)
        c2 = np.outer(np.exp(eta_arr), cumhaz)
        surv = np.exp(-c2)
        meansurv = np.sum(surv * tt[np.newaxis, :], axis=1)
        return np.column_stack([meansurv, surv])

    def summary(surv: Any, var: Any) -> dict[str, Any]:
        surv_arr = np.asarray(surv, dtype=float)
        var_arr = np.asarray(var, dtype=float)
        bsurv = surv_arr[:, 1:].T
        std = np.sqrt(var_arr[:, 1:]).T
        chaz = -np.log(bsurv)
        zstat = -NormalDist().inv_cdf((1 - conf_int) / 2)
        out = dict(baseline)
        out["lower"] = np.exp(-(chaz + zstat * std))
        out["upper"] = np.exp(-(chaz - zstat * std))
        out["surv"] = bsurv
        out["std.err"] = std / bsurv
        return out

    return {"predict": predict, "summary": summary}


def yates_setup_coxph(fit: Any, predict: str | None = "lp", options: Any = None, **kwargs: Any) -> Any:
    """coxph method: linear predictor, risk score, or the survival prediction."""
    choice = _match_arg(predict, ["lp", "risk", "expected", "terms", "survival", "linear"])
    if choice in ("lp", "linear"):
        return None
    if choice == "risk":

        def _risk(eta: Any, X: Any = None) -> np.ndarray:
            return np.exp(np.asarray(eta, dtype=float))

        return _risk
    if choice == "survival":
        return _coxph_survival(fit, options)
    raise YatesError("type expected is not supported")


def _family_linkinv(fit: Any) -> Callable[[np.ndarray], np.ndarray]:
    family = _component(fit, "family")
    linkinv = _component(family, "linkinv") if family is not None else None
    if linkinv is None:
        raise YatesError("the glm fit has no family linkinv")
    return linkinv


def yates_setup_glm(fit: Any, predict: str | None = "link", options: Any = None, **kwargs: Any) -> Any:
    """glm method: linear predictor or the response through the family's inverse link."""
    choice = _match_arg(predict, ["link", "response", "terms", "linear"])
    if choice in ("link", "linear"):
        return None
    if choice == "response":
        linkinv = _family_linkinv(fit)

        def _response(eta: Any, X: Any = None) -> Any:
            return linkinv(np.asarray(eta, dtype=float))

        return _response
    raise YatesError("type terms not yet supported")


def yates_setup_default(fit: Any, type: str | None = None, **kwargs: Any) -> None:
    """default method: always the linear predictor, with a warning for other types."""
    if type is not None and type not in ("linear", "link"):
        warnings.warn(
            f"no yates_setup method exists for a model of class {_first_class(fit)} "
            f"and estimate type {type}, linear predictor estimate used by default",
            stacklevel=2,
        )
    return None


def yates_setup(fit: Any, *args: Any, **kwargs: Any) -> Any:
    """Dispatch to the method for the fit's class, as R's UseMethod does."""
    for klass in _classes(fit):
        if klass == "coxph":
            return yates_setup_coxph(fit, *args, **kwargs)
        if klass == "glm":
            return yates_setup_glm(fit, *args, **kwargs)
    return yates_setup_default(fit, *args, **kwargs)


__all__ = [
    "yates_setup",
    "yates_setup_coxph",
    "yates_setup_glm",
    "yates_setup_default",
]
