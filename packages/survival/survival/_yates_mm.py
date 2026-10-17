"""Design matrices for survival::yates (R model.matrix, treatment contrasts)."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any

import numpy as np


class YatesError(Exception):
    pass


def _match_arg(value: str | None, choices: list[str]) -> str:
    if value is None:
        return choices[0]
    text = str(value)
    exact = [c for c in choices if c == text]
    if len(exact) == 1:
        return exact[0]
    hits = [c for c in choices if c.startswith(text)]
    if len(hits) == 1:
        return hits[0]
    if not hits:
        raise YatesError("'arg' should be one of " + ", ".join(repr(c) for c in choices))
    raise YatesError("'arg' matched more than one choice: " + ", ".join(hits))


def _split_formula(text: str) -> tuple[str, str]:
    if "~" not in text:
        raise YatesError("formula needs a '~'")
    left, right = text.split("~", 1)
    return left.strip(), right.strip()


def _parse_rhs(rhs: str) -> tuple[bool, list[str]]:
    intercept = True
    terms: list[str] = []
    for raw in rhs.split("+"):
        piece = raw.strip()
        if not piece:
            continue
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


def _term_labels_from_rhs(rhs: str) -> tuple[bool, list[str]]:
    """Match R term.labels: main effects in sum order, then deferred * interactions."""
    intercept, terms = _parse_rhs(rhs)
    mains: list[str] = []
    interactions: list[str] = []

    def _add_main(name: str) -> None:
        if name not in mains:
            mains.append(name)

    for term in terms:
        if "*" in term:
            parts = [p.strip() for p in term.split("*") if p.strip()]
            for part in parts:
                _add_main(part)
            if len(parts) >= 2:
                inter = ":".join(parts)
                if inter not in interactions:
                    interactions.append(inter)
        elif ":" in term:
            if term not in interactions:
                interactions.append(term)
        else:
            _add_main(term)
    return intercept, mains + interactions


@dataclass
class Terms:
    formula: str
    response: str
    intercept: bool
    term_labels: list[str]
    variables: list[str]
    data_classes: dict[str, str]
    factors: np.ndarray
    predvars: list[Any] = field(default_factory=list)


def _data_class(name: str, values: Any) -> str:
    if isinstance(values, np.ndarray):
        if values.dtype.kind in {"U", "S", "O"}:
            return "factor"
        return "numeric"
    if isinstance(values, list) and values and isinstance(values[0], str):
        return "factor"
    return "numeric"


def _factor_levels(values: Any, xlevels: dict[str, list[str]] | None, name: str) -> list[str]:
    if xlevels and name in xlevels:
        return list(xlevels[name])
    seen: list[str] = []
    for item in values:
        if item is None or (isinstance(item, float) and math.isnan(item)):
            continue
        text = str(item).strip()
        if text not in seen:
            seen.append(text)
    return seen


def build_terms(formula: str, data: dict[str, Any], xlevels: dict[str, list[str]] | None = None) -> Terms:
    response, rhs = _split_formula(formula)
    intercept, term_labels = _term_labels_from_rhs(rhs)
    variables = [response]
    for label in term_labels:
        if ":" in label:
            for part in label.split(":"):
                if part not in variables:
                    variables.append(part)
        elif label not in variables:
            variables.append(label)
    data_classes = {response: _data_class(response, data[response])}
    for name in variables[1:]:
        data_classes[name] = _data_class(name, data[name])
    pred_vars = variables[1:]
    factors = np.zeros((len(pred_vars), len(term_labels)), dtype=int)
    for j, label in enumerate(term_labels):
        if ":" in label:
            for part in label.split(":"):
                i = pred_vars.index(part)
                factors[i, j] = 1
        else:
            i = pred_vars.index(label)
            factors[i, j] = 1
    return Terms(
        formula=formula,
        response=response,
        intercept=intercept,
        term_labels=term_labels,
        variables=variables,
        data_classes=data_classes,
        factors=factors,
    )


def _column_values(data: dict[str, Any], name: str, n: int) -> list[Any]:
    if name not in data:
        raise YatesError(f"object '{name}' not found")
    col = data[name]
    if isinstance(col, np.ndarray):
        col = col.tolist()
    if len(col) != n:
        raise YatesError(f"variable lengths differ")
    return list(col)


def model_matrix(
    terms: Terms,
    data: dict[str, Any],
    *,
    xlevels: dict[str, list[str]] | None = None,
    contrasts: dict[str, str] | None = None,
) -> tuple[np.ndarray, list[str], list[int]]:
    n = len(data[terms.response])
    columns: list[np.ndarray] = []
    names: list[str] = []
    assign: list[int] = []
    term_cols: dict[str, list[np.ndarray]] = {}
    term_names: dict[str, list[str]] = {}

    if terms.intercept:
        columns.append(np.ones(n, dtype=float))
        names.append("(Intercept)")
        assign.append(0)

    for tidx, label in enumerate(terms.term_labels, start=1):
        if ":" in label:
            parts = label.split(":")
            acc = None
            acc_names: list[str] = []
            for part_index, part in enumerate(parts):
                values = _column_values(data, part, n)
                kind = terms.data_classes.get(part, "numeric")
                if kind == "factor":
                    levels = _factor_levels(values, xlevels, part)
                    start = 1
                    if len(parts) == 2:
                        other = parts[1 - part_index]
                        if terms.data_classes.get(other, "numeric") == "numeric":
                            start = 0
                        elif terms.data_classes.get(other) == "factor" and part_index == 0:
                            start = 0
                    part_cols = []
                    part_nms = []
                    for lev in levels[start:]:
                        part_cols.append(
                            np.array([1.0 if str(v).strip() == lev else 0.0 for v in values], dtype=float)
                        )
                        part_nms.append(f"{part}{lev}")
                else:
                    part_cols = [np.asarray(values, dtype=float)]
                    part_nms = [part]
                if acc is None:
                    acc = part_cols
                    acc_names = part_nms
                else:
                    new_cols = []
                    new_names = []
                    for c1, n1 in zip(acc, acc_names):
                        for c2, n2 in zip(part_cols, part_nms):
                            new_cols.append(c1 * c2)
                            new_names.append(f"{n1}:{n2}")
                    acc = new_cols
                    acc_names = new_names
            for col, nm in zip(acc or [], acc_names):
                columns.append(np.asarray(col, dtype=float))
                names.append(nm)
                assign.append(tidx)
            continue

        values = _column_values(data, label, n)
        kind = terms.data_classes.get(label, "numeric")
        if kind == "factor":
            levels = _factor_levels(values, xlevels, label)
            if len(levels) < 2:
                term_cols[label] = []
                term_names[label] = []
                continue
            cols = []
            nms = []
            for lev in levels[1:]:
                col = np.array([1.0 if str(v).strip() == lev else 0.0 for v in values], dtype=float)
                cols.append(col)
                nms.append(f"{label}{lev}")
            term_cols[label] = cols
            term_names[label] = nms
            for col, nm in zip(cols, nms):
                columns.append(col)
                names.append(nm)
                assign.append(tidx)
        else:
            col = np.asarray(values, dtype=float)
            term_cols[label] = [col]
            term_names[label] = [label]
            columns.append(col)
            names.append(label)
            assign.append(tidx)

    if not columns:
        raise YatesError("model matrix has no columns")
    return np.column_stack(columns), names, assign


def lm_fit(formula: str, data: dict[str, Any]) -> dict[str, Any]:
    terms = build_terms(formula, data)
    xlevels = {}
    for name in terms.variables[1:]:
        if terms.data_classes[name] == "factor":
            xlevels[name] = _factor_levels(data[name], None, name)
    x, names, assign = model_matrix(terms, data, xlevels=xlevels)
    y = np.asarray(data[terms.response], dtype=float)
    keep = np.isfinite(y) & np.all(np.isfinite(x), axis=1)
    xk = x[keep]
    yk = y[keep]
    coef, _res, rank, _s = np.linalg.lstsq(xk, yk, rcond=None)
    fitted = xk @ coef
    resid = yk - fitted
    n = xk.shape[0]
    p = xk.shape[1]
    df_res = max(n - rank, 1)
    rss = float(np.sum(resid**2))
    sigma = math.sqrt(rss / df_res)
    xtx_inv = np.linalg.inv(xk.T @ xk)
    vcov = sigma**2 * xtx_inv
    model = {terms.response: y[keep]}
    for name in terms.variables[1:]:
        col = _column_values(data, name, len(y))
        model[name] = np.asarray([col[i] for i in range(len(col)) if keep[i]], dtype=object if terms.data_classes[name] == "factor" else float)
    return {
        "class": ["lm"],
        "coefficients": dict(zip(names, coef)),
        "coef": coef,
        "coef_names": names,
        "vcov": vcov,
        "model": model,
        "terms": terms,
        "xlevels": xlevels,
        "contrasts": {k: "contr.treatment" for k in xlevels},
        "assign": assign,
        "sigma": sigma,
        "formula": formula,
        "x": x[keep],
        "rank": rank,
    }
