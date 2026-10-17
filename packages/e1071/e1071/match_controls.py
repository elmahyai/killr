"""Matched control selection from e1071 ``matchControls``."""

from __future__ import annotations

import math
import re
import sys
from pathlib import Path
from typing import Any, Mapping, Sequence


def _cluster_daisy():
    try:
        from cluster.daisy import daisy as impl
    except ImportError:
        sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "cluster"))
        from cluster.daisy import daisy as impl
    return impl


def _proxy_as_matrix():
    try:
        from proxy.dist import Proximity, as_matrix
    except ImportError:
        sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "proxy"))
        from proxy.dist import Proximity, as_matrix
    return Proximity, as_matrix


def _boot_sample_int():
    try:
        from boot.rng import sample_int
    except ImportError:
        sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "boot"))
        from boot.rng import sample_int
    return sample_int


def _is_na(value: Any) -> bool:
    return value is None or (isinstance(value, float) and math.isnan(value))


def _column_len(column: Sequence[Any]) -> int:
    return len(column)


def _as_table(data: Mapping[str, Sequence[Any]]) -> dict[str, list[Any]]:
    if not data:
        return {}
    lengths = {_column_len(values) for values in data.values()}
    if len(lengths) != 1:
        raise ValueError("all variables must have the same length")
    return {key: list(values) for key, values in data.items()}


def _subset_indices(subset: Sequence[Any] | None, n: int) -> list[int]:
    if subset is None:
        return list(range(n))
    return [index for index, keep in enumerate(subset) if keep]


def _apply_indices(table: dict[str, list[Any]], indices: list[int]) -> dict[str, list[Any]]:
    return {key: [values[index] for index in indices] for key, values in table.items()}


def _split_formula(formula: str) -> tuple[str, list[str]]:
    text = str(formula)
    if "~" not in text:
        raise ValueError("invalid formula")
    lhs, rhs = text.split("~", 1)
    response = lhs.strip().strip("`")
    terms: list[str] = []
    for piece in rhs.split("+"):
        piece = piece.strip()
        if not piece or piece in ("1", "0"):
            continue
        terms.append(piece.strip("`"))
    return response, terms


def _factor_levels(values: Sequence[Any]) -> list[str]:
    labels = {str(value) for value in values if not _is_na(value)}
    return sorted(labels)


def _factor_codes(values: Sequence[Any], levels: list[str] | None = None) -> list[float]:
    if levels is None:
        levels = _factor_levels(values)
    codes: list[float] = []
    for value in values:
        if _is_na(value):
            codes.append(math.nan)
        else:
            codes.append(float(levels.index(str(value)) + 1))
    return codes


def _is_numeric_column(values: Sequence[Any]) -> bool:
    for value in values:
        if _is_na(value) or isinstance(value, bool):
            continue
        if not isinstance(value, (int, float)):
            return False
    return True


def _model_frame(
    formula: str,
    data: Mapping[str, Sequence[Any]],
    *,
    subset: Sequence[Any] | None = None,
    row_names: Sequence[str] | None = None,
) -> tuple[list[str], list[Any], list[list[float]], list[bool], list[str]]:
    response_name, terms = _split_formula(formula)
    table = _as_table(data)
    if response_name not in table:
        raise ValueError(f"variable '{response_name}' not found")
    for name in terms:
        if name not in table:
            raise ValueError(f"variable '{name}' not found")
    n = _column_len(table[response_name])
    full_rownames = list(row_names) if row_names is not None else [str(index + 1) for index in range(n)]
    if len(full_rownames) != n:
        raise ValueError("row names must match the number of observations")
    indices = _subset_indices(subset, n)
    rownames = [full_rownames[index] for index in indices]
    sub = _apply_indices(table, indices)

    response = list(sub[response_name])
    predictors: list[list[float]] = []
    numeric_flags: list[bool] = []
    for name in terms:
        column = list(sub[name])
        if _is_numeric_column(column):
            predictors.append([float(item) if not _is_na(item) else math.nan for item in column])
            numeric_flags.append(True)
        else:
            predictors.append(_factor_codes(column))
            numeric_flags.append(False)
    return rownames, response, predictors, numeric_flags, full_rownames


def _as_character(values: Sequence[Any]) -> list[str]:
    out: list[str] = []
    for value in values:
        if _is_na(value):
            out.append("NA")
        else:
            out.append(str(value))
    return out


def _grep_indices(pattern: str, values: Sequence[str]) -> list[int]:
    regex = re.compile(pattern)
    return [index for index, value in enumerate(values) if regex.search(value)]


def _match_labels(
    response: list[Any],
    rownames: list[str],
    *,
    contlabel: str,
    caselabel: str | Sequence[str] | None,
    dogrep: bool,
) -> tuple[list[str], list[str]]:
    values = _as_character(response)
    if dogrep:
        ok = set(_grep_indices(contlabel, values))
        controls = [rownames[index] for index in sorted(ok)]
        if caselabel is None:
            cases = [name for index, name in enumerate(rownames) if index not in ok]
        else:
            labels = [caselabel] if isinstance(caselabel, str) else list(caselabel)
            case_ok: set[int] = set()
            for label in labels:
                case_ok.update(_grep_indices(label, values))
            cases = [rownames[index] for index in sorted(case_ok)]
        return cases, controls
    controls = [rownames[index] for index, value in enumerate(values) if value == contlabel]
    if caselabel is None:
        cases = [name for index, name in enumerate(rownames) if values[index] != contlabel]
    else:
        labels = {caselabel} if isinstance(caselabel, str) else set(caselabel)
        cases = [rownames[index] for index, value in enumerate(values) if value in labels]
    return cases, controls


def _daisy_matrix(predictors: list[list[float]], numeric_flags: list[bool]) -> list[list[float]]:
    daisy = _cluster_daisy()
    Proximity, as_matrix = _proxy_as_matrix()
    if not predictors:
        raise ValueError("formula must include matching variables")
    rows = len(predictors[0])
    matrix = [[predictors[col][row] for col in range(len(predictors))] for row in range(rows)]
    metric = "euclidean" if all(numeric_flags) else "gower"
    dist = daisy(matrix, metric=metric)
    return as_matrix(Proximity(dist, size=len(matrix)))


def _which_is_min(values: Sequence[float]) -> int:
    sample_int = _boot_sample_int()
    finite = [value for value in values if not _is_na(value)]
    if not finite:
        return 0
    minimum = min(finite)
    candidates = [index for index, value in enumerate(values) if not _is_na(value) and value == minimum]
    if len(candidates) > 1:
        pick = sample_int(len(candidates), 1)[0] - 1
        return candidates[pick]
    return candidates[0]


def match_controls(
    formula,
    data=None,
    subset=None,
    contlabel="con",
    caselabel=None,
    dogrep=True,
    replace=False,
    row_names=None,
):
    """Match cases to nearest controls using ``cluster.daisy`` distances."""
    if data is None:
        data = {}
    if not isinstance(data, Mapping):
        raise ValueError("data must be a mapping of column names to vectors")
    full_table = _as_table(data)
    rownames, response, predictors, numeric_flags, full_rownames = _model_frame(
        str(formula),
        full_table,
        subset=subset,
        row_names=row_names,
    )
    cases, controls = _match_labels(
        response,
        rownames,
        contlabel=contlabel,
        caselabel=caselabel,
        dogrep=dogrep,
    )
    dist = _daisy_matrix(predictors, numeric_flags)
    name_to_index = {name: index for index, name in enumerate(rownames)}

    retval: list[str] = []
    available = list(controls)
    for case in cases:
        case_index = name_to_index[case]
        distances = [dist[case_index][name_to_index[name]] for name in available]
        chosen = available[_which_is_min(distances)]
        retval.append(chosen)
        if not replace:
            available = [name for name in available if name != chosen]

    factor: list[Any] = [math.nan] * len(full_rownames)
    case_set = set(cases)
    control_set = set(retval)
    for index, name in enumerate(full_rownames):
        if name in case_set:
            factor[index] = "case"
        elif name in control_set:
            factor[index] = "cont"
    return {"cases": cases, "controls": retval, "factor": factor, "levels": ["case", "cont"]}
