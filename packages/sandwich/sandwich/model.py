"""Linear and generalized linear fits used by the sandwich estimators."""

from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np

_DATA = Path(__file__).resolve().parent / "data"


class SandwichError(Exception):
    """An error whose message matches the R stop text."""


def as_1d(values) -> np.ndarray:
    array = np.asarray(values, dtype=float)
    return np.ravel(array)


def as_2d(values) -> np.ndarray:
    array = np.asarray(values, dtype=float)
    if array.ndim == 0:
        return array.reshape(1, 1)
    if array.ndim == 1:
        return array.reshape(-1, 1)
    return array


def match_arg(arg, choices: list[str]) -> str:
    if arg is None:
        return choices[0]
    text = str(arg)
    exact = [item for item in choices if item == text]
    if len(exact) == 1:
        return exact[0]
    hits = [item for item in choices if item.startswith(text)]
    if len(hits) == 1:
        return hits[0]
    if not hits:
        raise SandwichError("'arg' should be one of " + ", ".join(repr(item) for item in choices))
    raise SandwichError("'arg' matched more than one choice: " + ", ".join(hits))


def r_seq(start: float, end: float, by: float) -> np.ndarray:
    if by == 0:
        raise SandwichError("step must not be zero")
    count = int(math.floor((end - start) / by + 1e-8)) + 1
    if count < 1:
        return np.array([], dtype=float)
    return start + by * np.arange(count, dtype=float)


class Formula:
    """A one-sided or two-sided R formula stored as text, such as ``y ~ x``."""

    def __init__(self, text: str):
        self.text = text.strip()

    def __repr__(self) -> str:
        return f"formula('{self.text}')"


def formula(text: str) -> Formula:
    return Formula(text)


def _split_terms(rhs: str) -> tuple[bool, list[str]]:
    intercept = True
    terms: list[str] = []
    for raw in rhs.split("+"):
        piece = raw.strip()
        if piece in {"1", ""}:
            continue
        if piece in {"0", "-1"}:
            intercept = False
            continue
        if piece.startswith("-"):
            name = piece[1:].strip()
            if name == "1":
                intercept = False
            continue
        terms.append(piece)
    return intercept, terms


def _column(data: dict, name: str, n: int | None = None) -> np.ndarray:
    if name not in data:
        raise SandwichError(f"object '{name}' not found")
    values = data[name]
    if isinstance(values, np.ndarray) and values.dtype != object:
        array = np.asarray(values, dtype=float)
    else:
        array = np.array(list(values), dtype=object)
    if n is not None and len(array) != n:
        raise SandwichError(f"column '{name}' has length {len(array)}, not {n}")
    return array


def _design(data: dict, text: str) -> tuple[np.ndarray, np.ndarray | None, list[str], np.ndarray]:
    if "~" not in text:
        raise SandwichError("formula needs a '~'")
    left, right = text.split("~", 1)
    left = left.strip()
    intercept, terms = _split_terms(right.strip())
    n = None
    pieces: list[np.ndarray] = []
    names: list[str] = []
    if intercept:
        n_guess = None
        for name in terms:
            n_guess = len(data[name])
            break
        if left:
            n_guess = len(data[left]) if left in data else n_guess
        if n_guess is None:
            raise SandwichError("formula has no columns")
        pieces.append(np.ones(n_guess))
        names.append("(Intercept)")
        n = n_guess
    response = None
    if left:
        if left not in data:
            raise SandwichError(f"object '{left}' not found")
        response = _column(data, left)
        n = len(response)
        if intercept and (not pieces or len(pieces[0]) != n):
            pieces = [np.ones(n)]
            names = ["(Intercept)"]
    for name in terms:
        column = _column(data, name, n)
        if column.dtype == object:
            levels = []
            for item in column:
                if item is None or (isinstance(item, float) and math.isnan(item)):
                    continue
                if item not in levels:
                    levels.append(item)
            for level in levels[1:]:
                pieces.append(np.array([1.0 if item == level else 0.0 for item in column]))
                names.append(f"{name}{level}")
        else:
            pieces.append(np.asarray(column, dtype=float))
            names.append(name)
        if n is None:
            n = len(pieces[-1])
    if not pieces:
        raise SandwichError("model matrix has no columns")
    design = np.column_stack(pieces)
    keep = np.ones(design.shape[0], dtype=bool)
    if response is not None:
        keep &= np.isfinite(np.asarray(response, dtype=float))
    keep &= np.all(np.isfinite(design), axis=1)
    return design, None if response is None else np.asarray(response, dtype=float), names, keep


def _qr_coef(x: np.ndarray, y: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    q, r = np.linalg.qr(x, mode="reduced")
    if y.ndim == 1:
        coef = np.linalg.solve(r, q.T @ y)
    else:
        coef = np.linalg.solve(r, q.T @ y)
    return coef, q, r


def _xtx_inv(x: np.ndarray, weights: np.ndarray | None = None) -> np.ndarray:
    if weights is None:
        gram = x.T @ x
    else:
        gram = x.T @ (weights[:, None] * x)
    return np.linalg.inv(gram)


class Fit:
    """A fitted lm, glm, or mlm, with the slots the estimators read."""

    def __init__(self, **slots):
        self.__dict__.update(slots)

    @property
    def nobs(self) -> int:
        return int(self.x.shape[0])

    def hatvalues(self) -> np.ndarray:
        weights = getattr(self, "working_weights", None)
        design = self.x
        if weights is not None:
            scale = np.sqrt(np.asarray(weights, dtype=float))
            design = design * scale[:, None]
        q, _r = np.linalg.qr(design, mode="reduced")
        return np.sum(q * q, axis=1)

    def cov_unscaled(self) -> np.ndarray:
        weights = getattr(self, "working_weights", None)
        if self.klass[0] == "lm" and getattr(self, "prior_weights", None) is not None:
            if weights is None:
                weights = self.prior_weights
        return _xtx_inv(self.x, None if weights is None else np.asarray(weights, dtype=float))

    def subset(self, indices: np.ndarray, weights=None):
        indices = np.asarray(indices, dtype=int)
        design = self.x[indices]
        y = self.y[indices] if self.y.ndim == 1 else self.y[indices]
        prior = None
        if getattr(self, "prior_weights", None) is not None:
            prior = np.asarray(self.prior_weights, dtype=float)[indices]
        if weights is not None:
            extra = np.asarray(weights, dtype=float)
            prior = extra if prior is None else prior * extra
        offset = getattr(self, "offset", None)
        if offset is not None:
            offset = np.asarray(offset, dtype=float)[indices]
        if self.klass[0] == "glm":
            return glm_fit(design, y, self.coef_names, family=self.family, weights=prior, offset=offset)
        return lm_fit(design, y, self.coef_names, weights=prior, offset=offset, responses=getattr(self, "response_names", None))


def lm_fit(x, y, names: list[str], weights=None, offset=None, responses=None) -> Fit:
    design = as_2d(x)
    response = np.asarray(y, dtype=float)
    if offset is not None:
        response = response - np.asarray(offset, dtype=float).reshape(response.shape)
    scale = None
    if weights is not None:
        scale = np.sqrt(np.asarray(weights, dtype=float))
        design_w = design * scale[:, None]
        response_w = response * scale if response.ndim == 1 else response * scale[:, None]
    else:
        design_w = design
        response_w = response
    coef, _q, _r = _qr_coef(design_w, response_w)
    if response.ndim == 1:
        fitted = design @ coef
        if offset is not None:
            fitted = fitted + np.asarray(offset, dtype=float)
        resid = np.asarray(y, dtype=float) - fitted
        klass = ("lm",)
    else:
        fitted = design @ coef
        resid = response - fitted if offset is None else np.asarray(y, dtype=float) - (fitted + np.asarray(offset, dtype=float).reshape(response.shape))
        klass = ("mlm",)
    return Fit(
        klass=klass,
        x=design,
        y=np.asarray(y, dtype=float),
        coefficients=coef,
        coef_names=list(names),
        residuals=resid,
        fitted=fitted,
        prior_weights=None if weights is None else np.asarray(weights, dtype=float),
        working_weights=None if weights is None else np.asarray(weights, dtype=float),
        working_residuals=resid,
        family=None,
        offset=None if offset is None else np.asarray(offset, dtype=float),
        response_names=responses,
        data=None,
        omitted=np.array([], dtype=int),
        na_action=None,
    )


def _family_specs(family: str):
    name = family.lower()
    if name in {"gaussian", "gaussian()"}:
        return "gaussian", False
    if name in {"binomial", "binomial()", "quasibinomial"}:
        return "binomial", name != "quasibinomial"
    if name in {"poisson", "poisson()", "quasipoisson"}:
        return "poisson", name != "quasipoisson"
    raise SandwichError(f"family '{family}' is not supported")


def glm_fit(x, y, names: list[str], family: str = "gaussian", weights=None, offset=None, maxit: int = 25, epsilon: float = 1e-8) -> Fit:
    kind, fixed_dispersion = _family_specs(family)
    design = as_2d(x)
    response = as_1d(y)
    n = design.shape[0]
    prior = np.ones(n) if weights is None else np.asarray(weights, dtype=float)
    off = np.zeros(n) if offset is None else np.asarray(offset, dtype=float)
    if kind == "binomial":
        mu = (prior * response + 0.5) / (prior + 1.0)
    elif kind == "poisson":
        mu = response + 0.1
    else:
        mu = response.copy()
    coef = np.zeros(design.shape[1])
    dev = math.inf
    working_weights = prior.copy()
    working = response - mu
    for _ in range(maxit):
        if kind == "binomial":
            mu = np.clip(mu, 1e-12, 1 - 1e-12)
            mu_eta = mu * (1 - mu)
            variance = mu * (1 - mu)
        elif kind == "poisson":
            mu = np.clip(mu, 1e-12, None)
            mu_eta = mu
            variance = mu
        else:
            mu_eta = np.ones(n)
            variance = np.ones(n)
        working_weights = prior * (mu_eta ** 2) / variance
        working = (response - mu) / mu_eta
        z = (off if kind == "gaussian" else np.log(mu / (1 - mu)) if kind == "binomial" else np.log(mu)) + working
        # eta currently, then z = eta + working, and the design includes no offset column
        if kind == "binomial":
            eta = np.log(mu / (1.0 - mu))
        elif kind == "poisson":
            eta = np.log(mu)
        else:
            eta = mu.copy()
        z = eta - off + working
        scale = np.sqrt(working_weights)
        coef, _q, _r = _qr_coef(design * scale[:, None], z * scale)
        eta = design @ coef + off
        if kind == "binomial":
            mu = 1.0 / (1.0 + np.exp(-eta))
            dev_new = float(np.sum(prior * _binomial_deviance(response, mu)))
        elif kind == "poisson":
            mu = np.exp(eta)
            dev_new = float(np.sum(prior * _poisson_deviance(response, mu)))
        else:
            mu = eta
            dev_new = float(np.sum(prior * (response - mu) ** 2))
        if abs(dev - dev_new) / (0.1 + abs(dev_new)) < epsilon:
            dev = dev_new
            break
        dev = dev_new
    # R keeps the weights from the iteration that produced the final
    # coefficients, and refreshes the working residuals from the final mean.
    if kind == "binomial":
        mu_eta = np.clip(mu, 1e-12, 1 - 1e-12) * (1 - np.clip(mu, 1e-12, 1 - 1e-12))
    elif kind == "poisson":
        mu_eta = np.clip(mu, 1e-12, None)
    else:
        mu_eta = np.ones(n)
    working = (response - mu) / mu_eta
    return Fit(
        klass=("glm", "lm"),
        x=design,
        y=response,
        coefficients=coef,
        coef_names=list(names),
        residuals=response - mu,
        fitted=mu,
        prior_weights=prior,
        working_weights=working_weights,
        working_residuals=working,
        family=kind,
        fixed_dispersion=fixed_dispersion,
        offset=off,
        response_names=None,
        data=None,
        omitted=np.array([], dtype=int),
        na_action=None,
    )


def _poisson_deviance(y, mu) -> np.ndarray:
    term = np.zeros_like(y)
    positive = y > 0
    term[positive] = y[positive] * np.log(y[positive] / mu[positive])
    return 2 * (term - (y - mu))


def _binomial_deviance(y, mu) -> np.ndarray:
    mu = np.clip(mu, 1e-12, 1 - 1e-12)
    term = np.zeros_like(y)
    positive = y > 0
    less = y < 1
    term[positive] += y[positive] * np.log(y[positive] / mu[positive])
    term[less] += (1 - y[less]) * np.log((1 - y[less]) / (1 - mu[less]))
    return 2 * term


def _attach_frame(fit: Fit, data: dict, keep: np.ndarray, omitted: np.ndarray) -> Fit:
    fit.data = data
    fit.omitted = omitted
    fit.na_action = omitted if len(omitted) else None
    fit.kept = keep
    return fit


def lm(formula_text, data: dict, weights=None) -> Fit:
    if isinstance(formula_text, Formula):
        formula_text = formula_text.text
    design, response, names, keep = _design(data, formula_text)
    if response is None:
        raise SandwichError("lm() needs a response")
    if response.ndim != 1:
        raise SandwichError("lm() response must be a column")
    prior = None if weights is None else np.asarray(weights, dtype=float)[keep]
    fit = lm_fit(design[keep], response[keep], names, weights=prior)
    return _attach_frame(fit, data, keep, np.flatnonzero(~keep))


def glm(formula_text, data: dict, family: str = "gaussian", weights=None) -> Fit:
    if isinstance(formula_text, Formula):
        formula_text = formula_text.text
    design, response, names, keep = _design(data, formula_text)
    if response is None:
        raise SandwichError("glm() needs a response")
    prior = None if weights is None else np.asarray(weights, dtype=float)[keep]
    fit = glm_fit(design[keep], response[keep], names, family=family, weights=prior)
    return _attach_frame(fit, data, keep, np.flatnonzero(~keep))


def mlm(formula_text, data: dict, responses: list[str]) -> Fit:
    if isinstance(formula_text, Formula):
        formula_text = formula_text.text
    base = formula_text.split("~", 1)[1]
    design, _response, names, keep = _design(data, f"{responses[0]} ~ {base}")
    columns = []
    for name in responses:
        column = np.asarray(data[name], dtype=float)
        columns.append(column)
    response = np.column_stack(columns)
    keep = keep & np.all(np.isfinite(response), axis=1)
    fit = lm_fit(design[keep], response[keep], names, responses=responses)
    return _attach_frame(fit, data, keep, np.flatnonzero(~keep))


def _decode_column(values):
    if not isinstance(values, list):
        return values
    if any(isinstance(item, str) for item in values):
        return [np.nan if item is None else item for item in values]
    return np.array([np.nan if item is None else float(item) for item in values], dtype=float)


def load_dataset(name: str) -> dict:
    payload = json.loads((_DATA / f"{name}.json").read_text())
    columns = {key: _decode_column(value) for key, value in payload["columns"].items()}
    columns["__rownames__"] = payload.get("rownames") or []
    start = payload.get("start")
    frequency = payload.get("frequency")
    if isinstance(start, dict):
        start = None
    if isinstance(frequency, dict):
        frequency = None
    columns["__start__"] = start
    columns["__frequency__"] = frequency
    return columns


def Investment() -> dict:
    return load_dataset("Investment")


def InstInnovation() -> dict:
    return load_dataset("InstInnovation")


def PetersenCL() -> dict:
    return load_dataset("PetersenCL")


def PublicSchools() -> dict:
    return load_dataset("PublicSchools")
