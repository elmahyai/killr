"""Naive Bayes classifier (e1071 ``naiveBayes``, not ``predict``)."""

from __future__ import annotations

import math
from typing import Any, Mapping, Sequence

import numpy as np


def _is_na(value: Any) -> bool:
    return value is None or (isinstance(value, float) and math.isnan(value))


def _as_data_frame(x: Any) -> dict[str, list[Any]]:
    if isinstance(x, Mapping):
        columns = {str(key): list(values) for key, values in x.items()}
    elif isinstance(x, np.ndarray):
        if x.ndim == 1:
            columns = {"V1": list(x)}
        elif x.ndim == 2:
            columns = {f"V{i + 1}": list(x[:, i]) for i in range(x.shape[1])}
        else:
            raise ValueError("x must be a data frame or a matrix")
    else:
        rows = list(x)
        if not rows:
            return {}
        if isinstance(rows[0], Mapping):
            names = list(rows[0].keys())
            columns = {name: [row[name] for row in rows] for name in names}
        elif isinstance(rows[0], (list, tuple)):
            width = len(rows[0])
            columns = {f"V{i + 1}": [row[i] for row in rows] for i in range(width)}
        else:
            columns = {"V1": list(rows)}
    lengths = {len(values) for values in columns.values()}
    if len(lengths) > 1:
        raise ValueError("arguments imply differing number of rows")
    return columns


def _y_labels(y: Sequence[Any]) -> tuple[list[str], list[str]]:
    if all(isinstance(item, bool) for item in y):
        labels = ["FALSE" if item else "TRUE" for item in y]
        return labels, ["FALSE", "TRUE"]
    labels = [str(item) for item in y]
    levels = sorted({label for label in labels})
    return labels, levels


def _var_levels(values: Sequence[Any]) -> tuple[list[str], list[str]]:
    if all(isinstance(item, bool) for item in values if not _is_na(item)):
        labels = []
        for item in values:
            if _is_na(item):
                labels.append(None)
            else:
                labels.append("FALSE" if item is False else "TRUE")
        return labels, ["FALSE", "TRUE"]
    labels = []
    seen: set[str] = set()
    for item in values:
        if _is_na(item):
            labels.append(None)
            continue
        text = str(item)
        labels.append(text)
        seen.add(text)
    return labels, sorted(seen)


def _mean_na(values: Sequence[float]) -> float:
    present = [float(v) for v in values if not _is_na(v)]
    if not present:
        return float("nan")
    return sum(present) / len(present)


def _sd_na(values: Sequence[float]) -> float:
    present = [float(v) for v in values if not _is_na(v)]
    n = len(present)
    if n < 2:
        return float("nan")
    mean = sum(present) / n
    return math.sqrt(sum((value - mean) ** 2 for value in present) / (n - 1))


def _table_two(y_labels: Sequence[str], var_labels: Sequence[str | None], y_levels: list[str], var_levels: list[str]) -> list[list[float]]:
    counts = [[0.0] * len(var_levels) for _ in y_levels]
    y_index = {name: index for index, name in enumerate(y_levels)}
    v_index = {name: index for index, name in enumerate(var_levels)}
    for y_val, v_val in zip(y_labels, var_labels, strict=True):
        if v_val is None or v_val not in v_index:
            continue
        counts[y_index[y_val]][v_index[v_val]] += 1.0
    return counts


def _est_var(var: Sequence[Any], y_labels: Sequence[str], y_levels: list[str], laplace: float) -> list[list[float]]:
    if all(isinstance(item, (int, float)) and not isinstance(item, bool) for item in var if not _is_na(item)):
        rows = []
        for level in y_levels:
            group = [float(var[i]) for i, y_val in enumerate(y_labels) if y_val == level]
            rows.append([_mean_na(group), _sd_na(group)])
        return rows
    logical = all(isinstance(item, bool) for item in var if not _is_na(item))
    var_labels, var_levels = _var_levels(var)
    tab = _table_two(y_labels, var_labels, y_levels, var_levels)
    out = []
    n_levels = len(var_levels) if logical else 0
    for row_index, _level in enumerate(y_levels):
        row = tab[row_index]
        row_sum = sum(row)
        denom = row_sum + laplace * n_levels
        if denom == 0.0:
            out.append([float("nan")] * len(row))
        else:
            out.append([(cell + laplace) / denom for cell in row])
    return out


def _naive_bayes_default(x: Any, y: Sequence[Any], laplace: float, y_name: str) -> dict[str, Any]:
    frame = _as_data_frame(x)
    y_labels, y_levels = _y_labels(y)
    if len(y_labels) != len(next(iter(frame.values()), [])):
        raise ValueError("response and predictors have different lengths")
    apriori = {level: y_labels.count(level) for level in y_levels}
    tables: dict[str, list[list[float]]] = {}
    isnumeric: dict[str, bool] = {}
    for name, column in frame.items():
        numeric = all(isinstance(item, (int, float)) and not isinstance(item, bool) for item in column if not _is_na(item))
        if not column:
            numeric = False
        isnumeric[name] = bool(numeric)
        table = _est_var(column, y_labels, y_levels, laplace)
        if numeric:
            tables[name] = {
                "matrix": table,
                "rownames": y_levels,
                "colnames": None,
                "dimnames": [y_name, name],
            }
        else:
            _, var_levels = _var_levels(column)
            tables[name] = {
                "matrix": table,
                "rownames": y_levels,
                "colnames": var_levels,
                "dimnames": [y_name, name],
            }
    return {
        "apriori": apriori,
        "tables": tables,
        "levels": y_levels,
        "isnumeric": isnumeric,
        "call": None,
    }


def _split_formula(formula: str) -> tuple[str, list[str]]:
    if "~" not in formula:
        raise ValueError("invalid formula")
    lhs, rhs = formula.split("~", 1)
    response = lhs.strip().strip("`")
    terms: list[str] = []
    for piece in rhs.split("+"):
        piece = piece.strip()
        if not piece or piece in ("1", "0"):
            continue
        if ":" in piece:
            raise ValueError("naiveBayes cannot handle interaction terms")
        terms.append(piece.strip("`"))
    return response, terms


def _apply_subset(data: Mapping[str, Sequence[Any]], subset: Sequence[Any] | None) -> dict[str, list[Any]]:
    if subset is None:
        return {key: list(values) for key, values in data.items()}
    indices = [index for index, keep in enumerate(subset) if keep]
    return {key: [values[index] for index in indices] for key, values in data.items()}


def _naive_bayes_formula(
    formula: str,
    data: Any,
    laplace: float,
    subset: Sequence[Any] | None = None,
) -> dict[str, Any]:
    y_name, predictors = _split_formula(formula)
    if isinstance(data, np.ndarray):
        if data.ndim < 2:
            raise ValueError("naiveBayes formula interface handles data frames or arrays only")
        dimnames = getattr(data, "dimnames", None) or [f"Dim{i + 1}" for i in range(data.ndim)]
        nam = list(dimnames)
        try:
            y_ind = nam.index(y_name)
        except ValueError as exc:
            raise ValueError(f"response '{y_name}' not found in dimnames") from exc
        if predictors == ["."]:
            v_ind = [index for index in range(len(nam)) if index != y_ind]
        else:
            v_ind = [nam.index(name) for name in predictors]
        array = np.asarray(data)
        apriori_counts = np.sum(array, axis=tuple(index for index in range(array.ndim) if index != y_ind))
        levels = list(getattr(apriori_counts, "names", None) or [str(i + 1) for i in range(apriori_counts.shape[0])])
        apriori = {level: float(apriori_counts.flat[i]) for i, level in enumerate(levels)}
        tables: dict[str, list[list[float]]] = {}
        isnumeric: dict[str, bool] = {}
        for index in v_ind:
            margins = tuple(sorted({y_ind, index}))
            margin = np.sum(array, axis=tuple(axis for axis in range(array.ndim) if axis not in margins))
            var_name = nam[index]
            var_levels = list(getattr(margin, "names", None) or [str(i + 1) for i in range(margin.shape[-1])])
            matrix = []
            for row in range(margin.shape[0]):
                row_sum = float(np.sum(margin[row, ...]))
                denom = row_sum + laplace * len(var_levels)
                matrix.append([(float(margin[row, col]) + laplace) / denom for col in range(margin.shape[-1])])
            tables[var_name] = {
                "matrix": matrix,
                "rownames": levels,
                "colnames": var_levels,
                "dimnames": [y_name, var_name],
            }
            isnumeric[var_name] = False
        return {
            "apriori": apriori,
            "tables": tables,
            "levels": levels,
            "isnumeric": isnumeric,
            "call": None,
        }

    if not isinstance(data, Mapping):
        raise ValueError("naiveBayes formula interface handles data frames or arrays only")
    frame = _apply_subset(data, subset)
    if y_name not in frame:
        raise ValueError(f"variable '{y_name}' not found")
    y = frame[y_name]
    columns = {name: frame[name] for name in predictors if name in frame}
    missing = [name for name in predictors if name not in frame]
    if missing:
        raise ValueError(f"variable '{missing[0]}' not found")
    return _naive_bayes_default(columns, y, laplace, y_name)


def naive_bayes(x: Any, y: Any = None, *, laplace: float = 0, subset: Sequence[Any] | None = None, data: Any = None) -> dict[str, Any]:
    """Fit a naive Bayes model (``naiveBayes.default`` and ``naiveBayes.formula``)."""
    if y is None and data is not None:
        return _naive_bayes_formula(str(x), data, float(laplace), subset=subset)
    if y is None:
        raise TypeError("y must be supplied for the default interface")
    return _naive_bayes_default(x, y, float(laplace), "y")


def flatten_naive_bayes(model: Mapping[str, Any], column_order: Sequence[str]) -> list[float]:
    """Column-major numeric flattening for proofs."""
    out = [float(model["apriori"][level]) for level in model["levels"]]
    for name in column_order:
        matrix = model["tables"][name]["matrix"]
        nrows = len(matrix)
        ncols = len(matrix[0]) if matrix else 0
        for col in range(ncols):
            for row in range(nrows):
                out.append(float(matrix[row][col]))
    for name in column_order:
        out.append(1.0 if model["isnumeric"][name] else 0.0)
    return out
