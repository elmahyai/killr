"""Printing and summary methods for mclust criterion objects.

The R methods operate on matrices with attributes.  Python callers commonly
represent those objects as dictionaries, so these functions accept mappings,
NumPy arrays, or objects exposing equivalent attributes.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import numpy as np

__all__ = [
    "print_mclust_bic",
    "summary_mclust_bic",
    "print_mclust_icl",
    "summary_mclust_icl",
    "print_summary_mclust_icl",
    "print_mclust_loglik",
    "print_mclust_bootstrap_lrt",
]


def _get(x: Any, name: str, default: Any = None) -> Any:
    if isinstance(x, Mapping):
        return x.get(name, default)
    return getattr(x, name, default)


def _matrix(x: Any) -> np.ndarray:
    value = _get(x, "values", x)
    return np.asarray(value, dtype=float)


def _names(x: Any, name: str, size: int, prefix: str) -> list[str]:
    value = _get(x, name)
    if value is None:
        return [f"{prefix}{i}" for i in range(size)]
    return [str(v) for v in value]


def _fmt(v: float, digits: int = 6) -> str:
    if np.isnan(v):
        return "NA"
    if np.isposinf(v):
        return "Inf"
    if np.isneginf(v):
        return "-Inf"
    return f"{v:.{digits}g}"


def _matrix_text(values: np.ndarray, rows: list[str], cols: list[str], digits: int = 6) -> str:
    values = np.atleast_2d(values)
    lines = ["        " + " ".join(f"{c:>{max(7, len(c))}}" for c in cols)]
    for i, row in enumerate(values):
        label = rows[i] if i < len(rows) else str(i + 1)
        lines.append(f"{label:>6} " + " ".join(f"{_fmt(float(v), digits):>7}" for v in row))
    return "\n".join(lines)


def _pick(values: np.ndarray, rows: list[str], cols: list[str], pick: int) -> dict[str, Any]:
    finite = np.isfinite(values)
    if not np.any(finite):
        return {"modelName": [], "G": [], "criterion": []}
    flat = np.where(finite, values, -np.inf).ravel()
    order = np.argsort(-flat, kind="stable")[: max(0, int(pick))]
    result = {"modelName": [], "G": [], "criterion": []}
    for index in order:
        i, j = np.unravel_index(index, values.shape)
        result["modelName"].append(cols[j])
        result["G"].append(rows[i])
        result["criterion"].append(float(values[i, j]))
    return result


def _criterion_summary(object: Any, criterion: str, G: Any = None, model_names: Any = None) -> dict[str, Any]:
    values = _matrix(object)
    rows = _names(object, "G", values.shape[0], "")
    cols = _names(object, "modelNames", values.shape[1], "")
    if G is not None:
        wanted = {str(v) for v in np.atleast_1d(G)}
        keep = [i for i, value in enumerate(rows) if value in wanted]
        values, rows = values[keep, :], [rows[i] for i in keep]
    if model_names is not None:
        wanted = {str(v) for v in np.atleast_1d(model_names)}
        keep = [i for i, value in enumerate(cols) if value in wanted]
        values, cols = values[:, keep], [cols[i] for i in keep]
    best = _pick(values, rows, cols, 1)
    if not best["criterion"]:
        return {"values": values, "criterion": criterion, "modelName": None, "G": None}
    return {
        "values": values,
        "criterion": criterion,
        "modelName": best["modelName"][0],
        "G": int(best["G"][0]) if best["G"][0].lstrip("-").isdigit() else best["G"][0],
        "bic" if criterion == "BIC" else "icl": best["criterion"][0],
    }


def summary_mclust_bic(object: Any, data: Any = None, G: Any = None, model_names: Any = None, **kwargs: Any) -> dict[str, Any]:
    """Select the maximum BIC model, preserving the R method's core result."""
    _ = data, kwargs
    return _criterion_summary(object, "BIC", G, model_names)


def summary_mclust_icl(object: Any, G: Any = None, model_names: Any = None, **kwargs: Any) -> dict[str, Any]:
    """Select the maximum ICL model."""
    _ = kwargs
    return _criterion_summary(object, "ICL", G, model_names)


def print_summary_mclust_icl(x: Any, digits: int = 6, **kwargs: Any) -> str:
    """Render the summary ICL values and their differences from the maximum."""
    _ = kwargs
    values = _matrix(x).reshape(-1)
    maximum = np.nanmax(values) if values.size else np.nan
    return "Best ICL values:\n" + _matrix_text(
        np.vstack([values, values - maximum]),
        ["ICL", "ICL diff"],
        [""],
        digits,
    )


def _print_criterion(x: Any, criterion: str, pick: int = 3, digits: int = 6) -> str:
    values = _matrix(x)
    rows = _names(x, "G", values.shape[0], "")
    cols = _names(x, "modelNames", values.shape[1], "")
    selected = _pick(values, rows, cols, pick)
    title = "Bayesian Information Criterion (BIC)" if criterion == "BIC" else "Integrated Complete-data Likelihood (ICL) criterion"
    lines = [title + ":", _matrix_text(values, rows, cols, digits), "", f"Top {pick} models based on the {criterion} criterion:"]
    for g, model, value in zip(selected["G"], selected["modelName"], selected["criterion"]):
        lines.append(f"{g} {model} {_fmt(value, digits)}")
    return "\n".join(lines)


def print_mclust_bic(x: Any, pick: int = 3, digits: int = 6, **kwargs: Any) -> str:
    _ = kwargs
    return _print_criterion(x, "BIC", pick, digits)


def print_mclust_icl(x: Any, pick: int = 3, digits: int = 6, **kwargs: Any) -> str:
    _ = kwargs
    return _print_criterion(x, "ICL", pick, digits)


def print_mclust_loglik(x: Any, digits: int = 6, **kwargs: Any) -> str:
    _ = kwargs
    value = _get(x, "value", _get(x, "loglik", x))
    df = _get(x, "df")
    nobs = _get(x, "nobs")
    text = f"'log Lik.' {_fmt(float(value), digits)}"
    if df is not None:
        text += f" (df={int(df)})"
    if nobs is not None:
        text += f"\n(n = {int(nobs)})"
    return text


def print_mclust_bootstrap_lrt(x: Any, digits: int = 6, **kwargs: Any) -> str:
    _ = kwargs
    if isinstance(x, Mapping):
        rows = ["Bootstrap sequential likelihood ratio test:"]
        for key in ("observed", "pvalues", "p.value", "nboot", "modelName"):
            if key in x:
                rows.append(f"{key}: {x[key]}")
        return "\n".join(rows)
    return str(x)
