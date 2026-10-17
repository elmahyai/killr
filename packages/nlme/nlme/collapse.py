"""Collapse grouping levels in groupedData (nlme ``collapse``)."""

from __future__ import annotations

import warnings
from dataclasses import dataclass
from typing import Any

import numpy as np

from nlme.getcovariateformula import _parse_bar, _tokenize


@dataclass(slots=True)
class GroupedDataFrame:
    """Minimal groupedData stand-in for ``collapse``."""

    columns: dict[str, np.ndarray]
    formula: str
    n_group_formula_levels: int | None = None

    @property
    def classes(self) -> tuple[str, ...]:
        return ("groupedData", "data.frame")

    def __getitem__(self, key: str) -> np.ndarray:
        return self.columns[key]

    def __getattr__(self, name: str) -> np.ndarray:
        try:
            return self.columns[name]
        except KeyError as exc:
            raise AttributeError(name) from exc


def collapse(
    object: GroupedDataFrame | Any,
    subset: Any = None,
    displayLevel: Any = None,
    collapseLevel: Any = None,
    outer: Any = None,
    inner: Any = None,
    preserve: Any = None,
    FUN: Any = None,
    **_ignored,
) -> GroupedDataFrame | Any:
    """Collapse inner grouping levels; single-level objects are returned unchanged."""
    form = _formula(object)
    grp_form = _get_groups_formula_list(form)
    q = len(grp_form)
    if q == 1:
        if subset is not None:
            warnings.warn("'subset' ignored with single grouping factor", stacklevel=2)
        return object
    raise NotImplementedError("collapse with multiple grouping levels is not implemented")


def proof_values_collapse() -> np.ndarray:
    """Numeric summary when collapsing single-level Orthodont groupedData."""
    import json

    _ORTHODONT_JSON = r"""{"distance":[26,25,29,31,21.5,22.5,23,26.5,23,22.5,24,27.5,25.5,27.5,26.5,27,20,23.5,22.5,26,24.5,25.5,27,28.5,22,22,24.5,26.5,24,21.5,24.5,25.5,23,20.5,31,26,27.5,28,31,31.5,23,23,23.5,25,21.5,23.5,24,28,17,24.5,26,29.5,22.5,25.5,25.5,26,23,24.5,26,30,22,21.5,23.5,25,21,20,21.5,23,21,21.5,24,25.5,20.5,24,24.5,26,23.5,24.5,25,26.5,21.5,23,22.5,23.5,20,21,21,22.5,21.5,22.5,23,25,23,23,23.5,24,20,21,22,21.5,16.5,19,19,19.5,24.5,25,28,28],"age":[8,10,12,14,8,10,12,14,8,10,12,14,8,10,12,14,8,10,12,14,8,10,12,14,8,10,12,14,8,10,12,14,8,10,12,14,8,10,12,14,8,10,12,14,8,10,12,14,8,10,12,14,8,10,12,14,8,10,12,14,8,10,12,14,8,10,12,14,8,10,12,14,8,10,12,14,8,10,12,14,8,10,12,14,8,10,12,14,8,10,12,14,8,10,12,14,8,10,12,14,8,10,12,14,8,10,12,14],"Subject":[15,15,15,15,3,3,3,3,7,7,7,7,14,14,14,14,2,2,2,2,13,13,13,13,5,5,5,5,6,6,6,6,11,11,11,11,16,16,16,16,4,4,4,4,8,8,8,8,9,9,9,9,10,10,10,10,12,12,12,12,1,1,1,1,20,20,20,20,23,23,23,23,25,25,25,25,26,26,26,26,21,21,21,21,19,19,19,19,22,22,22,22,24,24,24,24,18,18,18,18,17,17,17,17,27,27,27,27]}"""
    raw = json.loads(_ORTHODONT_JSON)
    frame = GroupedDataFrame(
        columns={
            "distance": np.asarray(raw["distance"], dtype=np.float64),
            "age": np.asarray(raw["age"], dtype=np.float64),
            "Subject": np.asarray(raw["Subject"], dtype=np.float64),
        },
        formula="distance ~ age | Subject",
    )
    out = collapse(frame)
    return np.concatenate(
        [
            np.asarray(out.distance, dtype=np.float64),
            np.asarray(out.age, dtype=np.float64),
            np.asarray(out.Subject, dtype=np.float64),
        ]
    )


def _formula(object: Any) -> str:
    if hasattr(object, "formula"):
        text = object.formula
        if isinstance(text, str) and "~" in text:
            return text.strip()
    raise ValueError("object must carry a groupedData formula")


def _get_groups_formula_list(formula: str) -> list[str]:
    _, rhs = formula.split("~", 1)
    tokens = _tokenize(rhs.strip())
    tree, pos = _parse_bar(tokens, 0)
    if pos != len(tokens):
        raise ValueError("invalid formula")
    parts: list[str] = []
    node = tree
    while node[0] == "|":
        parts.append(_deparse_expr(node[2]))
        node = node[1]
    return list(reversed(parts))


def _deparse_expr(node) -> str:
    kind = node[0]
    if kind == "name":
        return node[1]
    if kind == "num":
        return str(node[1])
    if kind == "paren":
        return f"({_deparse_expr(node[1])})"
    if kind == "call":
        args = ", ".join(_deparse_expr(arg) for arg in node[2])
        return f"{node[1]}({args})"
    if kind in ("+", "-", "*", "/", "^", ":"):
        left = _deparse_expr(node[1])
        right = _deparse_expr(node[2])
        return f"{left} {kind} {right}"
    if kind == "u-":
        return f"-{_deparse_expr(node[2])}"
    raise ValueError("invalid formula node")

