"""Weighting helper for nonlinear least squares (``wfct``)."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Mapping

import numpy as np

_RE_ERROR = re.compile("error")
_RE_FITTED = re.compile("fitted")
_RE_RESID = re.compile("resid")


@dataclass(frozen=True)
class Wfct:
    """Deferred weighting expression, as returned by :func:`wfct`."""

    expr: str

    def evaluate(
        self,
        *,
        formula: str,
        data: Mapping[str, Any],
        start: Mapping[str, float],
    ) -> np.ndarray:
        """Evaluate the weighting scheme with explicit ``nlsLM`` call data."""
        return _compute_weights(self.expr, formula=formula, data=data, start=start)


def wfct(expr: str | Wfct) -> Wfct:
    """Build a weight vector expression for ``nls_lm`` / ``nlsLM`` ``weights=``."""
    if isinstance(expr, Wfct):
        return expr
    return Wfct(_as_expr_str(expr))


def wfct_eval(
    expr: str,
    *,
    formula: str,
    data: Mapping[str, Any],
    start: Mapping[str, float],
) -> np.ndarray:
    """Evaluate ``wfct(expr)`` with an explicit formula, data, and start."""
    return wfct(expr).evaluate(formula=formula, data=data, start=start)


def puromycin_treated() -> dict[str, np.ndarray]:
    """``Puromycin[Puromycin$state == 'treated', ]`` as plain arrays."""
    return {
        "conc": np.array(
            [0.02, 0.02, 0.06, 0.06, 0.11, 0.11, 0.22, 0.22, 0.56, 0.56, 1.1, 1.1],
            dtype=float,
        ),
        "rate": np.array(
            [76.0, 47.0, 97.0, 107.0, 123.0, 139.0, 159.0, 152.0, 191.0, 201.0, 207.0, 200.0],
            dtype=float,
        ),
    }


def _as_expr_str(expr: str) -> str:
    text = str(expr).strip()
    if not text:
        raise ValueError("expr must be a non-empty weighting expression")
    return text


def _compute_weights(
    expr: str,
    *,
    formula: str,
    data: Mapping[str, Any],
    start: Mapping[str, float],
) -> np.ndarray:
    env: dict[str, Any] = {}
    for name, values in data.items():
        env[name] = np.asarray(values, dtype=float)

    resp, predictors = _formula_vars(formula)
    pred_names = _predictors_in_data(predictors, env)

    py_expr = expr.replace("^", "**")

    if _RE_ERROR.search(expr):
        y = env[resp]
        x = env[pred_names[0]]
        if not np.any(np.diff(np.sort(x)) == 0):
            raise ValueError("No replicates available to calculate error from!")
        error = _replicate_error(y, x)
        env["error"] = error

    if _RE_FITTED.search(expr) or _RE_RESID.search(expr):
        fitted, resid = _nls_lm_unweighted(formula, data, start)
        env["fitted"] = fitted
        env["resid"] = resid

    namespace = {**env, "sqrt": np.sqrt}
    out = eval(py_expr, {"__builtins__": {}}, namespace)
    return np.asarray(out, dtype=float).reshape(-1)


def _formula_vars(formula: str) -> tuple[str, list[str]]:
    lhs, rhs = formula.split("~", 1)
    resp = lhs.strip().split()[0]
    rhs_tokens = re.findall(r"[A-Za-z_][A-Za-z0-9_.]*", rhs)
    return resp, rhs_tokens


def _predictors_in_data(rhs_names: list[str], data: Mapping[str, Any]) -> list[str]:
    names = list(data.keys())
    matched = [name for name in rhs_names if name in names]
    return matched


def _replicate_error(y: np.ndarray, x: np.ndarray) -> np.ndarray:
    y = np.asarray(y, dtype=float)
    x = np.asarray(x, dtype=float)
    order = np.argsort(x, kind="mergesort")
    x_sorted = x[order]
    y_sorted = y[order]
    uniq, starts = np.unique(x_sorted, return_index=True)
    ends = np.append(starts[1:], y_sorted.size)
    per_level = []
    for begin, end in zip(starts, ends):
        group = y_sorted[begin:end]
        if group.size == 1:
            per_level.append(np.nan)
        else:
            per_level.append(float(np.nanvar(group, ddof=1)))
    sd = np.sqrt(np.asarray(per_level, dtype=float))
    counts = np.diff(np.append(starts, y_sorted.size))
    return np.repeat(sd, counts)


def _nls_lm_unweighted(
    formula: str,
    data: Mapping[str, Any],
    start: Mapping[str, float],
) -> tuple[np.ndarray, np.ndarray]:
    """Unweighted ``nlsLM`` fit, as ``wfct`` does before refitting with weights."""
    from minpacklm.nlsLM import nlsLM

    fit = nlsLM(formula, data=data, start=start)
    fitted = np.asarray(fit.fitted, dtype=float)
    resid = np.asarray(fit.residuals, dtype=float)
    return fitted, resid
