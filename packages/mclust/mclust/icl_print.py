"""Printing and summaries for ``mclustICL`` criterion objects."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import numpy as np


def _get(obj: Any, name: str, default: Any = None) -> Any:
    if isinstance(obj, Mapping):
        return obj.get(name, default)
    return getattr(obj, name, default)


def _values(obj: Any) -> np.ndarray:
    value = _get(obj, "values", obj)
    array = np.asarray(value, dtype=float)
    return np.atleast_2d(array)


def _labels(obj: Any, name: str, size: int) -> list[str]:
    value = _get(obj, name)
    if value is None:
        return [str(i) for i in range(1, size + 1)]
    return [str(item) for item in value]


def _r_number(value: float) -> str:
    if np.isnan(value):
        return "NA"
    if np.isposinf(value):
        return "Inf"
    if np.isneginf(value):
        return "-Inf"
    if float(value).is_integer():
        return str(int(value))
    return f"{value:.7g}"


def _pick(values: np.ndarray, rows: list[str], cols: list[str], pick: int) -> tuple[list[str], np.ndarray]:
    flat = values.ravel(order="F")
    finite = np.isfinite(flat)
    indices = np.flatnonzero(finite)
    indices = indices[np.argsort(-flat[indices], kind="stable")][: max(0, int(pick))]
    names = [f"{cols[index // values.shape[0]]},{rows[index % values.shape[0]]}" for index in indices]
    return names, flat[indices]


def _matrix_lines(values: np.ndarray, rows: list[str], cols: list[str]) -> list[str]:
    rendered = [[_r_number(float(item)) for item in row] for row in values]
    width = max(3, *(len(item) for row in rendered for item in row))
    header = " " * (max(len(row) for row in rows) + 1)
    header += " ".join(f"{col:>{max(width, len(col))}}" for col in cols)
    lines = [header]
    for row_name, row in zip(rows, rendered):
        lines.append(f"{row_name:>{max(len(item) for item in rows)}} " +
                     " ".join(f"{item:>{max(width, len(item))}}" for item in row))
    return lines


def print_mclust_icl(x: Any, pick: int = 3, **_: Any) -> Any:
    """Print an ICL matrix and its best models, returning ``x``."""
    values = _values(x)
    rows = _labels(x, "G", values.shape[0])
    cols = _labels(x, "modelNames", values.shape[1])
    names, best = _pick(values, rows, cols, pick)
    print("Integrated Complete-data Likelihood (ICL) criterion: ")
    print("\n".join(_matrix_lines(values, rows, cols)))
    print()
    print(f"Top {pick} models based on the ICL criterion: ")
    print(" ".join(names) + " ")
    if len(best):
        print(" " * 3 + _r_number(float(best[0])) +
              "".join(f"{_r_number(float(value)):>6}" for value in best[1:]) + " ")
    else:
        print(" ")
    return x


def summary_mclust_icl(
    object_: Any, G: Any = None, model_names: Any = None, **_: Any
) -> dict[str, Any]:
    """Return the top ICL values as a Python representation of the R result."""
    values = _values(object_)
    rows = _labels(object_, "G", values.shape[0])
    cols = _labels(object_, "modelNames", values.shape[1])
    if G is not None:
        wanted = {str(item) for item in np.atleast_1d(G)}
        keep = [index for index, row in enumerate(rows) if row in wanted]
        values, rows = values[keep, :], [rows[index] for index in keep]
    if model_names is not None:
        wanted = {str(item) for item in np.atleast_1d(model_names)}
        keep = [index for index, col in enumerate(cols) if col in wanted]
        values, cols = values[:, keep], [cols[index] for index in keep]
    names, best = _pick(values, rows, cols, 3)
    return {"values": best, "names": names, "class": "summary.mclustICL"}


def print_summary_mclust_icl(
    x: Any, digits: int | None = None, **_: Any
) -> Any:
    """Print a ``summary.mclustICL`` object and return it."""
    values = np.asarray(_get(x, "values", x), dtype=float).reshape(-1)
    names = _get(x, "names")
    if names is None:
        names = [f"[,{index + 1}]" for index in range(values.size)]
    names = [str(item) for item in names]
    maximum = np.nanmax(values) if values.size else np.nan
    differences = values - maximum
    number = lambda value: _r_number(float(value))
    print("Best ICL values:")
    print(" " * (9 if names and names[0].startswith("[,") else 9) +
          " ".join(names))
    if len(values) == 1:
        print("ICL" + " " * 8 + number(values[0]))
        print("ICL diff" + " " * 4 + number(differences[0]))
    else:
        print("ICL" + " " * 9 +
              number(values[0]) +
              "".join(f"{number(value):>7}" for value in values[1:]))
        print("ICL diff" + " " * 5 +
              number(differences[0]) +
              "".join(f"{number(value):>6}" for value in differences[1:]))
    return x


__all__ = ["print_mclust_icl", "summary_mclust_icl", "print_summary_mclust_icl"]
