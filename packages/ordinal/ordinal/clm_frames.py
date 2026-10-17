"""Model frames and design matrices for clm() (ordinal get_clm.mf, get_clmDesign, getThetamat).

Formulas are parsed and expanded by formulaic (agreed in native.json). Factor
levels are passed to formulaic as zero-padded position codes, because formulaic
sorts string levels; this keeps R's level order and treatment contrasts. Column
names are mapped back to R's style (Intercept -> (Intercept), x[T.lev] -> xlev).
"""

from __future__ import annotations

import itertools
import re
from typing import Any, Mapping, Sequence

import numpy as np
from formulaic import Formula, model_matrix

_CODE_WIDTH = 6
_TREAT = re.compile(r"([A-Za-z_.][A-Za-z0-9_.]*)\[T\.(\d{%d})\]" % _CODE_WIDTH)


def _is_na(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, (float, np.floating)):
        return bool(np.isnan(value))
    return False


def is_factor_values(values: Sequence[Any]) -> bool:
    """A column is a factor when any non-missing entry is a string."""
    return any(isinstance(v, str) for v in values if not _is_na(v))


def formula_variables(rhs: str) -> list[str]:
    """Variables used by a right-hand side formula, in formulaic's order."""
    return sorted(Formula(rhs).required_variables)


def encode_factor(values: Sequence[Any], levels: Sequence[str]) -> np.ndarray:
    """Factor values as strings whose sort order is the level order."""
    index = {lev: j for j, lev in enumerate(levels)}
    return np.array(
        [f"{index[str(v)]:0{_CODE_WIDTH}d}" if not _is_na(v) else "" for v in values],
        dtype=object,
    ).astype(str)


def _rename_column(name: str, factor_levels: Mapping[str, Sequence[str]]) -> str:
    if name == "Intercept":
        return "(Intercept)"

    def repl(match: re.Match) -> str:
        var = match.group(1)
        code = int(match.group(2))
        levels = factor_levels.get(var)
        return levels[code] if levels is not None else match.group(0)

    return _TREAT.sub(repl, name)


def design_matrix(
    rhs: str,
    columns: Mapping[str, Sequence[Any]],
    factor_levels: Mapping[str, Sequence[str]],
) -> tuple[np.ndarray, list[str]]:
    """Model matrix for an R-style right-hand side with R-style column names."""
    names = formula_variables(rhs)
    arrays = []
    for var in names:
        values = columns[var]
        if var in factor_levels:
            arrays.append(encode_factor(values, factor_levels[var]))
        else:
            arrays.append(np.asarray([np.nan if _is_na(v) else float(v) for v in values], dtype=float))
    rec = np.rec.fromarrays(arrays, names=names) if names else None
    if rec is None:
        n = len(next(iter(columns.values())))
        return np.ones((n, 1)), ["(Intercept)"]
    mm = model_matrix(rhs, rec)
    X = np.asarray(mm, dtype=float)
    raw = list(mm.columns)
    colnames = [_rename_column(str(c), factor_levels) for c in raw]
    return X, colnames


def nominal_grid_matrix(nom_info: Mapping[str, Any], sign_nominal: str) -> np.ndarray:
    """X for getThetamat: model matrix of the nominal terms on the grid of factor levels."""
    rhs = nom_info["rhs"]
    factors: Mapping[str, Sequence[str]] = nom_info["factors"]
    names = list(factors.keys())
    grid_levels = [list(factors[v]) for v in names]
    combos = list(itertools.product(*[range(len(l)) for l in grid_levels]))
    # expand.grid: first factor varies fastest
    combos = sorted(combos, key=lambda c: tuple(reversed(c)))
    columns = {
        var: [grid_levels[j][c[j]] for c in combos] for j, var in enumerate(names)
    }
    X, colnames = design_matrix(rhs, columns, factors)
    if "(Intercept)" not in colnames:
        X = np.column_stack([np.ones(X.shape[0]), X])
    if sign_nominal == "negative":
        X = X.copy()
        X[:, 1:] = -X[:, 1:]
    return X
