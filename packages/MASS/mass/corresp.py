"""Simple correspondence analysis (MASS corresp)."""

from __future__ import annotations

import warnings
from typing import Any, Mapping, Sequence

import numpy as np

from mass.errors import MassError

_INT_TOL = 10.0 * np.sqrt(np.finfo(float).eps)


def _as_matrix_table(x: Any) -> tuple[np.ndarray, list[str] | None, list[str] | None, list[str] | None]:
    """Coerce a table-like object to a numeric matrix with optional dimnames."""
    row_names: list[str] | None = None
    col_names: list[str] | None = None
    dim_name: list[str] | None = None
    if isinstance(x, np.ndarray):
        arr = np.asarray(x, dtype=float)
        if arr.ndim != 2:
            raise MassError("invalid table specification")
        dn = getattr(x, "_dimnames", None) or getattr(x, "dimnames", None)
        if dn is not None:
            if isinstance(dn, (list, tuple)) and len(dn) >= 2:
                row_names = [str(v) for v in dn[0]] if dn[0] is not None else None
                col_names = [str(v) for v in dn[1]] if dn[1] is not None else None
                if len(dn) >= 3 and dn[2] is not None:
                    dim_name = [str(v) for v in dn[2]]
        return arr, row_names, col_names, dim_name
    if isinstance(x, Mapping):
        raise MassError("invalid table specification")
    if hasattr(x, "values") and hasattr(x, "shape"):
        arr = np.asarray(x.values, dtype=float)
        if arr.ndim != 2:
            raise MassError("invalid table specification")
        return arr, row_names, col_names, dim_name
    mat = np.asarray(x, dtype=float)
    if mat.ndim != 2:
        raise MassError("invalid table specification")
    return mat, row_names, col_names, dim_name


def _r_table(x: Sequence[Any], y: Sequence[Any]) -> tuple[np.ndarray, list[str], list[str]]:
    """Two-way frequency table like base ``table``."""
    xs = [x[i] for i in range(len(x))]
    ys = [y[i] for i in range(len(y))]
    if len(xs) != len(ys):
        raise MassError("invalid table specification")

    def _levels(values: list[Any]) -> list[str]:
        seen: dict[str, None] = {}
        for item in values:
            key = str(item)
            if key not in seen:
                seen[key] = None
        return sorted(seen.keys())

    row_levels = _levels(xs)
    col_levels = _levels(ys)
    row_index = {name: i for i, name in enumerate(row_levels)}
    col_index = {name: i for i, name in enumerate(col_levels)}
    tab = np.zeros((len(row_levels), len(col_levels)), dtype=float)
    for a, b in zip(xs, ys):
        tab[row_index[str(a)], col_index[str(b)]] += 1.0
    return tab, row_levels, col_levels


def _corresp_matrix(
    x: np.ndarray,
    nf: int = 1,
    *,
    row_names: list[str] | None = None,
    col_names: list[str] | None = None,
    dim_name: list[str] | None = None,
) -> dict[str, Any]:
    arr = np.asarray(x, dtype=float)
    if arr.ndim != 2:
        raise MassError("invalid table specification")
    if np.any(arr < 0) or np.any(arr % 1.0 > _INT_TOL):
        warnings.warn("negative or non-integer entries in table", stacklevel=3)
    total = float(arr.sum())
    if total == 0.0:
        raise MassError("all frequencies are zero")
    dr = arr @ (np.ones(arr.shape[1], dtype=float) / total)
    dc = (np.ones(arr.shape[0], dtype=float) / total) @ arr
    if np.any(dr == 0.0) or np.any(dc == 0.0):
        raise MassError("empty row or column in table")
    x1 = arr / total - np.outer(dr, dc)
    dr = 1.0 / np.sqrt(dr)
    dc = 1.0 / np.sqrt(dc)
    svd_input = ((x1 * dr[:, None]).T * dc[:, None]).T
    u, singular, vh = np.linalg.svd(svd_input, full_matrices=True)
    v = vh.T
    nf = int(nf)
    if nf < 1:
        raise MassError("'nf' must be at least 1")
    cor = singular[:nf]
    rscore = u[:, :nf] * dr[:, None]
    cscore = v[:, :nf] * dc[:, None]
    freq = np.array(arr, dtype=float, copy=True)
    nrows, ncols = freq.shape
    if row_names is None:
        row_names = [f"R{i}" for i in range(1, nrows + 1)]
    if col_names is None:
        col_names = [f"C{j}" for j in range(1, ncols + 1)]
    if dim_name is None:
        dim_name = ["Row", "Column"]
    return {
        "cor": cor,
        "rscore": rscore,
        "cscore": cscore,
        "Freq": freq,
        "_rownames": row_names,
        "_colnames": col_names,
        "_dimnames": dim_name,
    }


def _parse_two_way_formula(formula: str) -> tuple[str, str]:
    text = formula.strip()
    if not text.startswith("~"):
        raise MassError("invalid table specification")
    rhs = text[1:].strip()
    if not rhs:
        raise MassError("higher-way table requested.  Only 2-way allowed")
    parts = [part.strip() for part in rhs.split("+") if part.strip()]
    if len(parts) != 2:
        raise MassError("higher-way table requested.  Only 2-way allowed")
    return parts[0], parts[1]


def _resolve_column(name: str, data: Mapping[str, Sequence[Any]]) -> Sequence[Any]:
    if name not in data:
        raise MassError(f"object '{name}' not found")
    return data[name]


def corresp(
    x: Any,
    y: Sequence[Any] | None = None,
    *,
    nf: int = 1,
    data: Mapping[str, Sequence[Any]] | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    """Correspondence analysis of a two-way contingency table (MASS ``corresp``)."""
    del kwargs
    if isinstance(x, str):
        if x.strip().startswith("~"):
            left, right = _parse_two_way_formula(x)
            if data is None:
                raise MassError("'data' is required for formula interface")
            tab, row_names, col_names = _r_table(_resolve_column(left, data), _resolve_column(right, data))
            return _corresp_matrix(tab, nf=nf, row_names=row_names, col_names=col_names, dim_name=[left, right])
        raise MassError("invalid table specification")

    if y is not None:
        tab, row_names, col_names = _r_table(x, y)
        return _corresp_matrix(tab, nf=nf, row_names=row_names, col_names=col_names)

    classes = getattr(x, "__class__", type(x)).__name__
    if classes == "DataFrame" or (isinstance(x, Mapping) and not isinstance(x, np.ndarray)):
        if isinstance(x, Mapping):
            keys = list(x.keys())
            if not keys:
                raise MassError("invalid table specification")
            mat = np.column_stack([np.asarray(x[k], dtype=float).reshape(-1) for k in keys])
        else:
            mat = np.asarray(x, dtype=float)
        return _corresp_matrix(mat, nf=nf)

    if classes == "xtabs" or (hasattr(x, "class") and "xtabs" in getattr(x, "class", ())):
        arr, row_names, col_names, dim_name = _as_matrix_table(x)
        return _corresp_matrix(arr, nf=nf, row_names=row_names, col_names=col_names, dim_name=dim_name)

    if isinstance(x, np.ndarray) or (hasattr(x, "shape") and hasattr(x, "__array__")):
        arr, row_names, col_names, dim_name = _as_matrix_table(x)
        return _corresp_matrix(arr, nf=nf, row_names=row_names, col_names=col_names, dim_name=dim_name)

    raise MassError("invalid table specification")
