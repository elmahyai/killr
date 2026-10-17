"""Printing and summary methods for discriminant-coordinate objects."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import numpy as np

__all__ = [
    "print_crimcoords",
    "summary_crimcoords",
    "print_summary_crimcoords",
]


def _get(value: Any, name: str, default: Any = None) -> Any:
    if isinstance(value, Mapping):
        return value.get(name, default)
    return getattr(value, name, default)


def _as_matrix(value: Any) -> np.ndarray:
    return np.asarray(value, dtype=float)


def _r_num(value: float, digits: int) -> str:
    if np.isnan(value):
        return "NA"
    if np.isposinf(value):
        return "Inf"
    if np.isneginf(value):
        return "-Inf"
    return f"{value:.{digits}g}"


def _matrix_text(
    value: Any,
    row_names: list[str] | None = None,
    col_names: list[str] | None = None,
    digits: int = 5,
) -> str:
    matrix = np.atleast_2d(_as_matrix(value))
    nrow, ncol = matrix.shape
    if col_names is None:
        col_names = [str(i + 1) for i in range(ncol)]
    if row_names is None:
        row_names = [str(i + 1) for i in range(nrow)]
    labels = [str(item) for item in col_names]
    width = max(7, *(len(item) for item in labels))
    header_prefix = 12 if row_names and row_names[0] == "Eigenvalues" else 9
    lines = [" " * header_prefix + " ".join(labels)]
    for i, row in enumerate(matrix):
        label = row_names[i] if i < len(row_names) else str(i + 1)
        if row_names and row_names[0] == "Eigenvalues" and i == 0:
            cumulative = matrix[1] if matrix.shape[0] > 1 else ()
            rendered = [
                f"{float(item):.3f}" if j < len(cumulative)
                and not float(cumulative[j]).is_integer()
                else _r_num(float(item), digits)
                for j, item in enumerate(row)
            ]
        elif row_names and row_names[0] == "Eigenvalues" and i == 1:
            rendered = [
                f"{float(item):.3f}".rstrip("0").rstrip(".") for item in row
            ]
        else:
            rendered = [_r_num(float(item), digits) for item in row]
        if len(rendered) == 1:
            lines.append(f"{label:<12}{rendered[0]:>7}")
        else:
            if row_names and row_names[0] == "Eigenvalues":
                first_start = 18 if i == 0 else 17
            else:
                first_start = 19
            lines.append(f"{label:<{first_start}}{rendered[0]:>1}" +
                         "".join(f"{item:>12}" for item in rendered[1:]))
    return "\n".join(lines)


def print_crimcoords(x: Any, digits: int | None = None, **_: Any) -> None:
    """Print the compact R ``print.crimcoords`` representation."""
    _ = digits
    keys = ("means", "B", "W", "evalues", "basis", "projection", "classification")
    present = [key for key in keys if _get(x, key) is not None]
    print("'crimcoords' object:")
    print(f"List of {len(present)}")
    for key in present:
        value = _get(x, key)
        if isinstance(value, Mapping):
            kind = "list"
        else:
            array = np.asarray(value)
            type_name = "int" if np.issubdtype(array.dtype, np.integer) else "num"
            if array.ndim == 2:
                kind = f"{type_name} [1:{array.shape[0]}, 1:{array.shape[1]}]"
            elif array.ndim == 1:
                kind = f"{type_name} [1:{array.size}]"
            else:
                kind = type_name
        preview = ""
        if not isinstance(value, Mapping):
            array = np.asarray(value)
            flat = array.reshape(-1, order="F")
            if flat.size:
                shown = flat[:10]
                preview = " " + " ".join(
                    str(int(item)) if np.issubdtype(array.dtype, np.integer)
                    else _r_num(float(item), 7)
                    for item in shown
                )
                if flat.size > 10:
                    preview += " ..."
        separator = "" if len(key) >= 14 else " "
        print(f"${' ' + key}{separator}: {kind}{preview}")


def summary_crimcoords(object: Any, numdir: int | None = None, **_: Any) -> dict[str, Any]:
    """Return the R ``summary.crimcoords`` representation."""
    projection = _as_matrix(_get(object, "projection"))
    basis = _as_matrix(_get(object, "basis"))
    evalues = np.asarray(_get(object, "evalues"), dtype=float).reshape(-1)
    if numdir is None:
        numdir = min(projection.shape[1], int(np.sum(evalues > np.sqrt(np.finfo(float).eps))))
    numdir = int(numdir)
    basis = basis[:, :numdir]
    values = evalues[:numdir]
    total = float(np.sum(values))
    cumulative = np.cumsum(values) / total * 100.0
    return {
        "basis": basis,
        "evalues": values,
        "evalues.cumperc": cumulative,
    }


def print_summary_crimcoords(
    x: Any, digits: int | None = None, **_: Any
) -> None:
    """Print a summary of discriminant coordinates."""
    if digits is None:
        digits = 5
    title = "Discriminant coordinates (crimcoords)"
    line = "-" * len(title)
    print(line, end=" \n")
    print(title, end=" \n")
    print(line, end=" \n")
    print()
    print("Estimated basis vectors: ", end="\n")
    basis = _as_matrix(_get(x, "basis"))
    columns = [f"crimcoords{i + 1}" for i in range(basis.shape[1])]
    rows = ["Length", "Left", "Right", "Bottom", "Top", "Diagonal"]
    row_names = rows[: basis.shape[0]]
    print(_matrix_text(basis, row_names, columns, int(digits)))
    print()
    values = np.vstack([
        np.asarray(_get(x, "evalues"), dtype=float),
        np.asarray(_get(x, "evalues.cumperc"), dtype=float),
    ])
    print(_matrix_text(values, ["Eigenvalues", "Cum. %"], columns, int(digits)))
