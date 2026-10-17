"""Python representation of the modeltools 0.2-25 interfaces.

The R package supplies a small model-environment abstraction and generic
hooks.  S4 dispatch is deliberately represented by ordinary Python classes
and functions, as required by the project translation rules.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import copy
import math
import re
from typing import Any, Callable, Mapping

import numpy as np


@dataclass
class FormulaParts:
    formula: dict[str, Any]


@dataclass
class ModelEnv:
    values: dict[str, Any] = field(default_factory=dict)
    hooks: dict[str, Any] = field(default_factory=dict)

    def get(self, which: str, data: Mapping[str, Any] | None = None) -> Any:
        if data is None:
            return self.values[which]
        old = self.values[which]
        if isinstance(data, Mapping) and isinstance(old, np.ndarray):
            names = getattr(old, "column_names", None)
            if names:
                return np.asarray([data[n] for n in names]).T
        return data

    def set(self, which: str | None = None, data: Any = None, **_: Any) -> None:
        if which is None:
            return
        self.values[which] = data

    def has(self, which: str) -> bool:
        return which in self.values

    def dimension(self, which: str) -> tuple[int, ...] | None:
        if which not in self.values:
            return None
        return np.asarray(self.values[which]).shape

    def empty(self) -> bool:
        return not self.values

    def clone(self, copydata: bool = True) -> "ModelEnv":
        return ModelEnv(copy.deepcopy(self.values) if copydata else {}, copy.deepcopy(self.hooks))

    def subset(self, indices: Any, clone: bool = True) -> "ModelEnv":
        z = self.clone() if clone else self
        for key, value in list(z.values.items()):
            a = np.asarray(value)
            if a.ndim:
                z.values[key] = a[indices]
        return z


def _columns(data: Mapping[str, Any] | Any) -> dict[str, np.ndarray]:
    if isinstance(data, Mapping):
        return {str(k): np.asarray(v) for k, v in data.items()}
    if hasattr(data, "columns"):
        return {str(k): np.asarray(data[k]) for k in data.columns}
    raise TypeError("data must be a mapping or dataframe-like object")


def ParseFormula(formula: str, data: Mapping[str, Any] | None = None) -> FormulaParts:
    """Split an R formula into response, input, and optional block formulas."""
    text = str(formula).strip()
    pieces = text.split("~", 1)
    if len(pieces) == 1:
        response, rhs = None, pieces[0].strip()
    else:
        response, rhs = pieces[0].strip() or None, pieces[1].strip()
    blocks = None
    if "|" in rhs:
        rhs, blocks = (x.strip() for x in rhs.split("|", 1))
    result = {}
    if response is not None:
        result["response"] = f"{response} ~ {response}"
    result["input"] = f"{rhs} ~ {rhs}"
    if blocks is not None:
        result["blocks"] = f"{blocks} ~ {blocks}"
    return FormulaParts(result)


def _terms(rhs: str, columns: Mapping[str, np.ndarray]) -> list[str]:
    rhs = rhs.strip()
    if rhs in ("", "1"):
        return []
    if rhs == ".":
        return list(columns)
    return [x.strip() for x in rhs.split("+") if x.strip() not in ("1", "0", "-1")]


def _design(rhs: str, data: Mapping[str, Any]) -> tuple[np.ndarray, list[str]]:
    cols = _columns(data)
    terms = _terms(rhs, cols)
    out, names = [np.ones(len(next(iter(cols.values()))))], ["(Intercept)"]
    if rhs.strip().startswith("0") or "-1" in rhs:
        out, names = [], []
    for term in terms:
        if term not in cols:
            raise KeyError(f"unknown formula term: {term}")
        x = cols[term]
        if x.dtype.kind in "OUS":
            levels = sorted({str(v) for v in x})
            for level in levels[1:]:
                out.append((x.astype(str) == level).astype(float))
                names.append(f"{term}{level}")
        else:
            out.append(x.astype(float))
            names.append(term)
    return np.column_stack(out) if out else np.empty((len(next(iter(cols.values()))), 0)), names


def ModelEnvFormula(formula: str, data: Mapping[str, Any] = None, subset=None,
                    na_action=None, other: Mapping[str, str] | None = None,
                    designMatrix: bool = True, responseMatrix: bool = True,
                    setHook=None, **kwargs: Any) -> ModelEnv:
    cols = _columns(data or {})
    lhs, rhs = (x.strip() for x in str(formula).split("~", 1))
    n = len(next(iter(cols.values()))) if cols else 0
    mask = np.ones(n, dtype=bool) if subset is None else np.asarray(subset, dtype=bool)
    names = _terms(rhs, cols)
    used = ([lhs] if lhs else []) + [x for x in names if x in cols]
    if na_action in (np.nan, "omit", "na.omit"):
        mask &= ~np.any([np.isnan(cols[x].astype(float)) for x in used if cols[x].dtype.kind not in "OUS"], axis=0)
    d = {k: v[mask] for k, v in cols.items()}
    env = ModelEnv()
    if lhs:
        env.values["response"] = np.asarray(d[lhs]).reshape(-1, 1)
        if responseMatrix:
            env.values["responseMatrix"] = env.values["response"].astype(float)
    env.values["input"] = {k: d[k] for k in names if k in d}
    if designMatrix:
        env.values["designMatrix"], env.values["design_names"] = _design(rhs, d)
    for key, formula2 in (other or {}).items():
        _, rhs2 = str(formula2).split("~", 1)
        env.values[key] = _design(rhs2, d)[0]
    if setHook is not None:
        env.hooks["set"] = setHook
    return env


def ModelEnvMatrix(designMatrix=None, responseMatrix=None, subset=None,
                   na_action=None, other: Mapping[str, Any] | None = None, **_: Any) -> ModelEnv:
    arrays = [np.asarray(x) for x in (designMatrix, responseMatrix) if x is not None]
    n = max((len(x) for x in arrays), default=0)
    idx = np.arange(n) if subset is None else np.asarray(subset)
    env = ModelEnv()
    if designMatrix is not None:
        env.values["designMatrix"] = np.asarray(designMatrix)[idx]
    if responseMatrix is not None:
        env.values["responseMatrix"] = np.asarray(responseMatrix)[idx]
    for key, value in (other or {}).items():
        env.values[key] = np.asarray(value)[idx]
    if na_action in ("omit", "na.omit"):
        good = np.ones(len(idx), dtype=bool)
        for value in env.values.values():
            a = np.asarray(value)
            good &= ~np.any(np.isnan(a.astype(float)), axis=tuple(range(1, a.ndim))) if a.dtype.kind not in "OUS" else True
        env = env.subset(good)
    return env


@dataclass
class FittedModel:
    coef: np.ndarray
    ModelEnv: ModelEnv
    family: str = "gaussian"
    statmodel: Any = None
    weights: np.ndarray | None = None

    def predict_response(self, newdata=None):
        x = self.ModelEnv.get("designMatrix") if newdata is None else _design_from_newdata(self, newdata)
        eta = np.asarray(x) @ self.coef
        return _link_inverse(eta, self.family)


def _design_from_newdata(model: FittedModel, newdata: Mapping[str, Any]) -> np.ndarray:
    names = model.ModelEnv.values.get("design_names", [])
    cols = _columns(newdata)
    result = [np.ones(len(next(iter(cols.values()))))] if names and names[0] == "(Intercept)" else []
    for name in names[len(result):]:
        result.append(np.asarray(cols[name], dtype=float))
    return np.column_stack(result)


def _link_inverse(x, family):
    if family in ("binomial", "logit"):
        return 1 / (1 + np.exp(-np.clip(x, -700, 700)))
    if family in ("poisson", "log"):
        return np.exp(np.clip(x, -700, 700))
    return x


def _fit(model, env: ModelEnv, family="gaussian", weights=None, **_: Any) -> FittedModel:
    x, y = np.asarray(env.get("designMatrix"), float), np.asarray(env.get("responseMatrix")).reshape(-1)
    if family == "gaussian":
        coef = np.linalg.lstsq(x, y, rcond=None)[0]
    else:
        coef = np.zeros(x.shape[1])
        for _ in range(100):
            mu = _link_inverse(x @ coef, family)
            var = np.maximum(mu * (1 - mu), 1e-12) if family == "binomial" else np.maximum(mu, 1e-12)
            z = x @ coef + (y - mu) / np.maximum(var, 1e-12)
            w = var
            new = np.linalg.lstsq(x * np.sqrt(w)[:, None], z * np.sqrt(w), rcond=None)[0]
            if np.max(np.abs(new - coef)) < 1e-10:
                coef = new
                break
            coef = new
    return FittedModel(coef, env, family, weights=weights)


@dataclass
class StatModel:
    name: str
    family: str = "gaussian"

    def dpp(self, formula, data=None, **kwargs):
        return ModelEnvFormula(formula, data, **kwargs)

    def fit(self, data, **kwargs):
        return _fit(self, data, self.family, **kwargs)

    def predict(self, object, newdata=None, **kwargs):
        return object.predict_response(newdata)


linearModel = StatModel("linear regression model")
glinearModel = StatModel("generalized linear regression model")
glinearModel.family = "gaussian"


@dataclass
class SurvRegModel:
    """Unfitted modeltools survival-regression model."""

    name: str = "survival regression"
    capabilities: Any = field(default_factory=dict)
    dpp: Callable[..., ModelEnv] = ModelEnvFormula
    fit: Callable[..., Any] | None = None
    predict: Callable[..., Any] | None = None

    def __post_init__(self):
        self.fit = _fit_survReg
        self.predict = _predict_survReg


def _fit_survReg(object: ModelEnv, weights=None, **kwargs):
    """Fit survival::survreg from a modeltools ModelEnv."""
    from survival.survreg import survreg
    import pandas as pd

    response = object.get("response")
    y = np.asarray(getattr(response, "columns", response), dtype=float)
    if y.ndim == 1:
        y = y.reshape(-1, 1)
    inputs = object.get("input")
    if inputs is None:
        inputs = {}
    if hasattr(inputs, "columns"):
        inputs = {str(k): np.asarray(inputs[k]) for k in inputs.columns}
    else:
        inputs = dict(inputs)
    frame = {f"__y{i}": y[:, i] for i in range(y.shape[1])}
    frame.update(inputs)
    lhs = f"Surv({', '.join(frame for frame in [f'__y{i}' for i in range(y.shape[1])])})"
    rhs = "1" + "".join(f" + {name}" for name in inputs)
    fit = survreg(f"{lhs} ~ {rhs}", data=pd.DataFrame(frame), weights=weights, **kwargs)
    fit["ModelEnv"] = object
    fit["weights"] = np.ones(y.shape[0]) if weights is None else np.asarray(weights)
    return fit


def _predict_survReg(object, newdata=None, **kwargs):
    if newdata is None:
        return np.asarray(object["linear.predictors"])
    raise NotImplementedError("newdata prediction is not translated")


def fitted_survReg(object, **kwargs):
    return _predict_survReg(object, **kwargs)


def weights_survReg(object, **kwargs):
    weights = object.get("weights")
    return np.ones(len(object["linear.predictors"])) if weights is None else weights


def logLik_survReg(object, **kwargs):
    value = np.asarray(object["loglik"]).reshape(-1)[-1]
    return {"value": float(value), "df": int(np.asarray(object["var"]).shape[1])}


survReg = SurvRegModel()


def Predict(object, *args, **kwargs):
    if hasattr(object, "predict_response"):
        return object.predict_response(*args, **kwargs)
    if hasattr(object, "predict"):
        return object.predict(*args, **kwargs)
    raise TypeError("object has no prediction method")


def _generic(object, name, *args, **kwargs):
    if isinstance(object, Mapping) and name in object:
        value = object[name]
        return value(*args, **kwargs) if callable(value) else value
    method = getattr(object, name, None)
    if callable(method):
        return method(*args, **kwargs)
    if hasattr(object, name):
        return getattr(object, name)
    raise NotImplementedError(f"{name} has no method for this object")


def ICL(object, *args, **kwargs): return _generic(object, "ICL", *args, **kwargs)
def KLdiv(object, *args, **kwargs): return _generic(object, "KLdiv", *args, **kwargs)
def Lapply(object, FUN, *args, **kwargs): return [FUN(x, *args, **kwargs) for x in object]
def clusters(object, newdata=None, *args, **kwargs): return _generic(object, "clusters", newdata, *args, **kwargs)
def getModel(object, *args, **kwargs): return _generic(object, "getModel", *args, **kwargs)
def parameters(object, *args, **kwargs): return _generic(object, "parameters", *args, **kwargs)
def posterior(object, newdata=None, *args, **kwargs): return _generic(object, "posterior", newdata, *args, **kwargs)
def prior(object, *args, **kwargs): return _generic(object, "prior", *args, **kwargs)
def refit(object, newdata=None, *args, **kwargs): return _generic(object, "refit", newdata, *args, **kwargs)
def relabel(object, by, *args, **kwargs): return _generic(object, "relabel", by, *args, **kwargs)


def info(object, which="help", *args, **kwargs):
    if isinstance(object, Mapping) and "info" in object:
        values = object["info"]
        return list(values) if which == "help" and isinstance(values, Mapping) else values[which]
    if which == "help":
        return list(getattr(object, "info", {}).keys()) if isinstance(getattr(object, "info", None), dict) else []
    if isinstance(getattr(object, "info", None), dict):
        return object.info[which]
    if hasattr(object, which):
        return getattr(object, which)
    raise KeyError(which)


def infoCheck(object, which, *args, **kwargs):
    try:
        info(object, which, *args, **kwargs)
        return True
    except (KeyError, NotImplementedError):
        return False

