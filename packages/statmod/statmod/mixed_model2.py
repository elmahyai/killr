"""REML mixed linear model with two variance components (formula interface).

Translated from statmod 1.5.2 ``mixedModel2`` in ``R/mixedmodel.R``.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

import numpy as np

from statmod.mixed_model2_fit import mixed_model2_fit


def _split_formula(formula: str) -> tuple[str, str]:
    if "~" not in formula:
        raise ValueError("formula needs a '~'")
    left, right = formula.split("~", 1)
    return left.strip(), right.strip()


def _parse_rhs_terms(rhs: str) -> tuple[bool, list[str]]:
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


def _column_length(values: Any) -> int:
    if isinstance(values, str):
        return 1
    return len(list(values))


def _subset_mask(subset: Any, n: int) -> np.ndarray:
    if subset is None:
        return np.ones(n, dtype=bool)
    if isinstance(subset, (list, tuple, np.ndarray)):
        arr = np.asarray(subset)
        if arr.dtype == bool:
            if arr.size != n:
                raise ValueError("incorrect number of dimensions")
            return arr.astype(bool)
        return arr.astype(bool)
    raise TypeError("subset must be a logical vector")


def _as_list(values: Any) -> list[Any]:
    if isinstance(values, str):
        return [values]
    return list(values)


def _unique_random_levels(random: np.ndarray) -> np.ndarray:
    if random.dtype.kind in {"U", "S", "O"}:
        levels: list[Any] = []
        seen: set[Any] = set()
        for value in random:
            if value not in seen:
                seen.add(value)
                levels.append(value)
        return np.asarray(levels, dtype=object)
    _, idx = np.unique(random, return_index=True)
    return random[np.sort(idx)]


def _model_frame(
    formula: str,
    random: Any,
    data: Mapping[str, Any],
    *,
    weights: Any = None,
    subset: Any = None,
) -> dict[str, Any]:
    response, rhs = _split_formula(formula)
    intercept, terms = _parse_rhs_terms(rhs)
    if response not in data:
        raise ValueError(f"object '{response}' not found")
    for name in terms:
        if name not in data:
            raise ValueError(f"object '{name}' not found")

    n = _column_length(data[response])
    mask = _subset_mask(subset, n)
    indices = np.flatnonzero(mask)

    def take(name: str) -> list[Any]:
        col = _as_list(data[name])
        if len(col) != n:
            raise ValueError(f"variable lengths differ (found for '{name}')")
        return [col[i] for i in indices]

    frame: dict[str, Any] = {response: take(response)}
    for name in terms:
        frame[name] = take(name)

    random_values = random
    if isinstance(random, str):
        if random not in data:
            raise ValueError(f"object '{random}' not found")
        random_values = data[random]
    random_list = _as_list(random_values)
    if len(random_list) != n:
        raise ValueError("variable lengths differ (found for '(random)')")
    frame["(random)"] = [random_list[i] for i in indices]

    if weights is not None:
        weight_list = _as_list(weights)
        if len(weight_list) != n:
            raise ValueError("variable lengths differ (found for '(weights)')")
        frame["(weights)"] = [weight_list[i] for i in indices]

    return frame, intercept, terms


def _model_matrix(
    frame: Mapping[str, Any],
    formula: str,
    intercept: bool,
    terms: list[str],
    *,
    contrasts: Any = None,
) -> np.ndarray:
    response, _rhs = _split_formula(formula)
    y_list = frame[response]
    n = len(y_list)
    columns: list[np.ndarray] = []
    if intercept:
        columns.append(np.ones(n, dtype=float))
    for term in terms:
        col = frame[term]
        if _is_numeric_column(col):
            columns.append(np.asarray(col, dtype=float).reshape(-1))
        else:
            columns.extend(_factor_columns(col, term, contrasts))
    if not columns:
        raise ValueError("invalid model matrix")
    return np.column_stack(columns)


def _is_numeric_column(column: Sequence[Any]) -> bool:
    for value in column:
        if value is None or (isinstance(value, float) and np.isnan(value)):
            continue
        if isinstance(value, (bool, np.bool_)):
            return False
        if not isinstance(value, (int, float, np.integer, np.floating)):
            return False
    return True


def _factor_columns(
    column: Sequence[Any],
    term: str,
    contrasts: Any,
) -> list[np.ndarray]:
    values = np.asarray(column, dtype=object)
    levels = _unique_random_levels(values)
    if levels.size < 2:
        return [np.ones(len(values), dtype=float)]
    n = len(values)
    out: list[np.ndarray] = []
    for level in levels[1:]:
        out.append((values == level).astype(float))
    return out


def _model_response(frame: Mapping[str, Any], formula: str) -> np.ndarray:
    response, _ = _split_formula(formula)
    return np.asarray(frame[response], dtype=float).reshape(-1)


def _model_weights(frame: Mapping[str, Any]) -> np.ndarray | None:
    if "(weights)" not in frame:
        return None
    return np.asarray(frame["(weights)"], dtype=float).reshape(-1)


def _random_design(random: np.ndarray) -> np.ndarray:
    random = np.asarray(random)
    levels = _unique_random_levels(random)
    return (random.reshape(-1, 1) == levels.reshape(1, -1)).astype(float)


def mixed_model2(
    formula: str,
    random: Any,
    weights: Any = None,
    only_varcomp: bool = False,
    data: Mapping[str, Any] | None = None,
    subset: Any = None,
    contrasts: Any = None,
    tol: float = 1e-6,
    maxit: int = 50,
    trace: bool = False,
):
    """Fit a mixed linear model with residual and block variance components."""
    if data is None:
        data = {}
    frame, intercept, terms = _model_frame(
        formula,
        random,
        data,
        weights=weights,
        subset=subset,
    )
    y = _model_response(frame, formula)
    x = _model_matrix(frame, formula, intercept, terms, contrasts=contrasts)
    random_col = np.asarray(frame["(random)"])
    z = _random_design(random_col)
    w = _model_weights(frame)

    if np.any(np.isnan(y)) or np.any(np.isnan(x)):
        raise ValueError("Missing values not allowed")
    if any(value is None or (isinstance(value, float) and np.isnan(value)) for value in random_col):
        raise ValueError("Missing values not allowed")
    if w is not None and np.any(np.isnan(w)):
        raise ValueError("Missing values not allowed")

    return mixed_model2_fit(
        y,
        x,
        z,
        w=w,
        only_varcomp=only_varcomp,
        tol=tol,
        maxit=maxit,
        trace=trace,
    )
