"""Primary covariate of a model component or data frame (nlme ``getCovariate``)."""

from __future__ import annotations

from typing import Any

import numpy as np

from nlme.dim import _CORSTRUCT_TYPES, _SPATIAL_TYPES
from nlme.getcovariateformula import _parse_bar, _tokenize, getCovariateFormula
from nlme.getgroups import GroupedDataFrame, GroupFactor, getGroups
from nlme.getgroupsformula import getGroupsFormula
from nlme.varcomb import _is_var_func

_FUNCTIONS = {
    "log": np.log,
    "exp": np.exp,
    "sqrt": np.sqrt,
    "abs": np.abs,
    "sin": np.sin,
    "cos": np.cos,
}


def getCovariate(object: Any, form: str | None = None, data: Any = None):
    """Return the primary covariate of ``object`` (varFunc, corStruct, or data frame)."""
    if _is_var_func(object):
        return getattr(object, "covariate", None)
    if isinstance(object, _SPATIAL_TYPES):
        return _cor_spatial(object, data)
    if isinstance(object, _CORSTRUCT_TYPES):
        return _cor_struct(object, data)
    if isinstance(object, (dict, GroupedDataFrame)):
        return _data_frame(object, form)
    raise TypeError(f"no applicable method for 'getCovariate' applied to {type(object)!r}")


def _data_frame(object: Any, form: str | None) -> np.ndarray:
    """``getCovariate.data.frame``: evaluate the covariate expression, or ones when there is none."""
    text = form if form is not None else getattr(object, "formula", None)
    if not isinstance(text, str) or "~" not in text:
        raise ValueError("'form' must be a formula")
    columns = _columns(object)
    cov_text = getCovariateFormula(text).text
    if not _leaf_names(_rhs_tree(cov_text)):
        return np.ones(_nrow(columns), dtype=np.float64)
    return _eval_node(_rhs_tree(cov_text), columns, _nrow(columns))


def _cor_struct(object: Any, data: Any):
    """``getCovariate.corStruct``: an attribute if present, else computed from ``data``."""
    covariate = getattr(object, "covariate", None)
    if covariate is not None:
        return covariate
    if data is None:
        raise ValueError('need data to calculate covariate of "corStruct" object')
    form = object.formula
    frame = _as_frame(data)
    nrow = _nrow(frame.columns)
    cov_text = getCovariateFormula(form).text
    grouped = getGroupsFormula(form) is not None
    names = _leaf_names(_rhs_tree(cov_text))
    values = _eval_node(_rhs_tree(cov_text), frame.columns, nrow) if names else None
    if not grouped:
        return values if values is not None else np.arange(1, nrow + 1, dtype=np.int64)
    levels, index = _group_index(getGroups(frame, form=form))
    parts = []
    for position in range(len(levels)):
        rows = np.flatnonzero(index == position)
        if values is not None:
            parts.append(values[rows])
        else:
            parts.append(np.arange(1, rows.size + 1, dtype=np.int64))
    return parts


def _cor_spatial(object: Any, data: Any):
    """``getCovariate.corSpatial``: distances between covariate rows, optionally by group."""
    covariate = getattr(object, "covariate", None)
    if covariate is not None:
        return covariate
    if data is None:
        raise ValueError("need data to calculate covariate")
    form = object.formula
    frame = _as_frame(data)
    nrow = _nrow(frame.columns)
    cov_text = getCovariateFormula(form).text
    tree = _rhs_tree(cov_text)
    covar = _model_matrix(tree, frame.columns, nrow) if _leaf_names(tree) else None
    metric = object.metric
    if getGroupsFormula(form) is not None:
        levels, index = _group_index(getGroups(frame, form=form))
        parts = []
        for position in range(len(levels)):
            rows = np.flatnonzero(index == position)
            if covar is None:
                distances = _distances(np.arange(1, rows.size + 1, dtype=np.float64).reshape(-1, 1), "euclidean")
            elif rows.size > 1:
                distances = _distances(covar[rows], metric)
            else:
                distances = np.empty(0, dtype=np.float64)
            if distances.size > 0:
                parts.append(distances)
        result = parts
    elif covar is None:
        result = _distances(np.arange(1, nrow + 1, dtype=np.float64).reshape(-1, 1), "euclidean")
    else:
        result = _distances(covar, metric)
    flat = np.concatenate(result) if isinstance(result, list) and result else np.asarray(result)
    if np.any(flat == 0):
        raise ValueError('cannot have zero distances in "corSpatial"')
    return result


def _distances(points: np.ndarray, metric: str) -> np.ndarray:
    """``dist``: pairwise distances in R's column-major lower-triangle order."""
    matrix = np.asarray(points, dtype=np.float64)
    if matrix.ndim == 1:
        matrix = matrix.reshape(-1, 1)
    count = matrix.shape[0]
    out = []
    for column in range(count):
        for row in range(column + 1, count):
            diff = np.abs(matrix[row] - matrix[column])
            if metric == "euclidean":
                out.append(float(np.sqrt(np.sum(diff * diff))))
            elif metric == "manhattan":
                out.append(float(np.sum(diff)))
            elif metric == "maximum":
                out.append(float(np.max(diff)))
            else:
                raise ValueError(f"unknown metric {metric!r}")
    return np.asarray(out, dtype=np.float64)


def _model_matrix(tree, columns: dict[str, Any], nrow: int) -> np.ndarray:
    """Numeric model matrix for the covariate terms, the intercept removed as in corSpatial."""
    terms = _plus_terms(tree)
    return np.column_stack([_eval_node(term, columns, nrow) for term in terms])


def _plus_terms(node) -> list:
    if node[0] == "+":
        return _plus_terms(node[1]) + _plus_terms(node[2])
    return [node]


def _eval_node(node, columns: dict[str, Any], nrow: int) -> np.ndarray:
    """Evaluate a parsed covariate expression on the columns of a data frame."""
    kind = node[0]
    if kind == "name":
        name = node[1]
        if name not in columns:
            raise ValueError(f"object '{name}' not found")
        return np.asarray(columns[name], dtype=np.float64).reshape(-1)
    if kind == "num":
        return np.full(nrow, float(node[1]), dtype=np.float64)
    if kind == "paren":
        return _eval_node(node[1], columns, nrow)
    if kind == "u-":
        return -_eval_node(node[2], columns, nrow)
    if kind == "call":
        if node[1] not in _FUNCTIONS:
            raise NotImplementedError(f"function {node[1]!r} is not implemented in covariates")
        if len(node[2]) != 1:
            raise ValueError("one argument expected in covariate function")
        return _FUNCTIONS[node[1]](_eval_node(node[2][0], columns, nrow))
    left = _eval_node(node[1], columns, nrow)
    right = _eval_node(node[2], columns, nrow)
    if kind == "+":
        return left + right
    if kind == "*":
        return left * right
    if kind == "/":
        return left / right
    if kind == "^":
        return np.power(left, right)
    raise NotImplementedError(f"operator {kind!r} is not implemented in covariates")


def _leaf_names(node) -> list[str]:
    if node is None:
        return []
    kind = node[0]
    if kind == "name":
        return [node[1]]
    if kind == "num":
        return []
    if kind == "call":
        out: list[str] = []
        for arg in node[2]:
            out.extend(_leaf_names(arg))
        return out
    if kind == "paren":
        return _leaf_names(node[1])
    if kind == "u-":
        return _leaf_names(node[2])
    return _leaf_names(node[1]) + _leaf_names(node[2])


def _rhs_tree(text: str):
    rhs = text.split("~", 1)[1].strip()
    tree, pos = _parse_bar(_tokenize(rhs), 0)
    if pos != len(_tokenize(rhs)):
        raise ValueError("invalid formula")
    return tree


def _as_frame(data: Any) -> GroupedDataFrame:
    if isinstance(data, GroupedDataFrame):
        return data
    if isinstance(data, dict):
        return GroupedDataFrame(columns=dict(data))
    raise TypeError("data must be a data frame stand-in")


def _columns(object: Any) -> dict[str, Any]:
    if isinstance(object, GroupedDataFrame):
        return object.columns
    return dict(object)


def _nrow(columns: dict[str, Any]) -> int:
    return len(np.asarray(next(iter(columns.values()))).reshape(-1))


def _group_index(groups: Any) -> tuple[tuple[str, ...], np.ndarray]:
    """Factor levels and a zero-based level index per row, in ``split`` order."""
    if isinstance(groups, GroupFactor):
        index = np.asarray(groups.codes, dtype=np.float64).astype(np.int64) - 1
        return tuple(groups.levels), index
    values = [str(item) for item in np.asarray(groups, dtype=object).reshape(-1)]
    levels = tuple(sorted(set(values)))
    lookup = {name: position for position, name in enumerate(levels)}
    return levels, np.asarray([lookup[item] for item in values], dtype=np.int64)
