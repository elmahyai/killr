"""Grouped data frames (nlme ``groupedData``, ``nfGroupedData``, ``nmGroupedData``).

The R data frame is a plain list of columns with a class vector and attributes.
This module keeps the same fields in ``DataFrame``; a ``Factor`` stands in for an
R factor (integer codes into ``levels``, with an ``ordered`` flag).
"""

from __future__ import annotations

import math
import re
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from typing import Any

import numpy as np

__all__ = [
    "DataFrame",
    "Factor",
    "get_groups",
    "group_terms",
    "groupedData",
    "max_na_rm",
    "parse_formula",
]

_FUNCTIONS: dict[str, Any] = {
    "log": np.log,
    "exp": np.exp,
    "sqrt": np.sqrt,
    "abs": np.abs,
    "sin": np.sin,
    "cos": np.cos,
    "tan": np.tan,
    "pi": math.pi,
}
_IDENT = re.compile(r"(?<![0-9A-Za-z_.])[A-Za-z_.][A-Za-z0-9_.]*")
_OUTER_SEP = "\x07"


@dataclass(frozen=True, slots=True)
class Factor:
    """R factor: 0-based ``codes`` into ``levels``."""

    codes: np.ndarray
    levels: tuple[str, ...]
    ordered: bool = False

    def __len__(self) -> int:
        return int(self.codes.shape[0])

    def texts(self) -> list[str]:
        return [self.levels[int(code)] for code in self.codes]

    def subset(self, rows: np.ndarray) -> Factor:
        return Factor(self.codes[rows], self.levels, self.ordered)

    @classmethod
    def from_values(cls, values, levels=None, ordered: bool = False) -> Factor:
        """``factor(values, levels=levels)``; default levels are the sorted unique values."""
        items = list(values)
        if levels is None:
            if items and all(_is_number(v) for v in items):
                uniq = sorted({float(v) for v in items})
                levels = tuple(_number_text(v) for v in uniq)
            else:
                levels = tuple(sorted({_text(v) for v in items}))
        else:
            levels = tuple(str(level) for level in levels)
        index = {level: pos for pos, level in enumerate(levels)}
        texts = [_text(v) for v in items]
        codes = np.array([index[text] for text in texts], dtype=np.int64)
        return cls(codes, levels, ordered)


@dataclass(slots=True)
class DataFrame:
    """``data.frame`` with class vector and attributes (``formula``, ``labels``, ...)."""

    columns: dict[str, Any]
    attributes: dict[str, Any] = field(default_factory=dict)
    classes: tuple[str, ...] = ("data.frame",)

    @property
    def nrow(self) -> int:
        if not self.columns:
            return 0
        return len(next(iter(self.columns.values())))

    @property
    def names(self) -> tuple[str, ...]:
        return tuple(self.columns)

    @property
    def formula(self) -> str | None:
        return self.attributes.get("formula")

    def __getitem__(self, name: str) -> Any:
        return self.columns[name]


def max_na_rm(x) -> float:
    """``function(x) max(x, na.rm = TRUE)``."""
    values = np.asarray(x, dtype=np.float64)
    values = values[~np.isnan(values)]
    if values.size == 0:
        return -math.inf
    return float(np.max(values))


def parse_formula(text: str) -> tuple[str, str, tuple[str, ...]]:
    """Split ``lhs ~ cov | g1/g2`` into ``(lhs, cov, (g1, g2))``.

    Without a ``|``, the whole right-hand side is the grouping formula.
    """
    if not isinstance(text, str) or "~" not in text:
        raise ValueError("'form' must be a formula")
    lhs, rhs = text.split("~", 1)
    lhs = lhs.strip()
    rhs = rhs.strip()
    if "(" in rhs or ")" in rhs:
        raise NotImplementedError("nested conditional expressions are not supported")
    if "|" in rhs:
        cov, groups = rhs.split("|", 1)
        cov = cov.strip()
    else:
        cov, groups = "", rhs
    terms = tuple(part.strip() for part in groups.split("/") if part.strip())
    return lhs, cov, terms


def group_terms(form) -> tuple[str, ...]:
    """Grouping names of ``formula(object)``, as ``getGroupsFormula(asList = TRUE)``."""
    text = _formula_text(form)
    _, _, terms = parse_formula(text)
    if not terms:
        raise ValueError("right-hand side of formula must be a conditional expression")
    return terms


def eval_expr(expr: str, columns: Mapping[str, Any], nrow: int):
    """Evaluate a column expression such as ``log(conc)`` or ``sin(2 * pi * Time)``.

    A bare column name returns the stored column (possibly a ``Factor``).
    """
    text = expr.strip()
    if not text:
        return np.ones(nrow, dtype=np.float64)
    if _IDENT.fullmatch(text):
        if text not in columns:
            raise KeyError(f"object '{text}' not found")
        return columns[text]
    names = {}
    for name in set(_IDENT.findall(text)):
        if name in _FUNCTIONS:
            continue
        if name not in columns:
            raise KeyError(f"object '{name}' not found")
        column = columns[name]
        if isinstance(column, Factor):
            raise TypeError(f"non-numeric argument '{name}' in expression")
        names[name] = np.asarray(column, dtype=np.float64)
    value = eval(text.replace("^", "**"), {"__builtins__": {}}, {**_FUNCTIONS, **names})
    return np.broadcast_to(np.asarray(value, dtype=np.float64), (nrow,)).copy()


def get_groups(object: DataFrame, form, level: int | None = None) -> Factor:
    """``getGroups.data.frame(object, form, level)`` for a formula with ``|`` groups."""
    text = _formula_text(form)
    _, _, terms = parse_formula(text)
    if not terms:
        raise ValueError("invalid formula for groups")
    if level is None:
        level = len(terms)
    level = int(level)
    if level < 1 or level > len(terms):
        raise ValueError(f"level of {level} does not match formula")
    nrow = object.nrow
    vectors = [_as_factor(eval_expr(term, object.columns, nrow)) for term in terms[:level]]
    if level == 1:
        return vectors[0]
    texts = list(zip(*[vec.texts() for vec in vectors]))
    pasted = ["/".join(parts) for parts in texts]
    if vectors[0].ordered:
        order = np.lexsort([vec.codes for vec in reversed(vectors)])
        levels = tuple(dict.fromkeys(pasted[i] for i in order))
    else:
        levels = tuple(dict.fromkeys(pasted))
    index = {level_text: pos for pos, level_text in enumerate(levels)}
    codes = np.array([index[text] for text in pasted], dtype=np.int64)
    return Factor(codes, levels, ordered=True)


def groupedData(
    formula,
    data=None,
    order_groups: bool = True,
    FUN: Callable[[np.ndarray], float] | None = None,
    outer=None,
    inner=None,
    labels: Mapping[str, str] | None = None,
    units: Mapping[str, str] | None = None,
) -> DataFrame:
    """Constructor for the groupedData class (``groupedData``).

    One grouping level gives ``nffGroupedData`` or ``nfnGroupedData``; several levels
    give ``nmGroupedData``.
    """
    text = _formula_text(formula)
    lhs, cov, terms = parse_formula(text)
    if "|" not in text.split("~", 1)[1] or not terms:
        raise ValueError("right-hand side of first argument must be a conditional expression")
    if not lhs:
        raise ValueError("first argument to 'groupedData' must be a two-sided formula")
    if data is None:
        raise ValueError("'data' must be a data frame")
    frame = _as_frame(data)
    if len(terms) == 1:
        return _nf_grouped(
            text, lhs, cov, terms[0], frame, order_groups, FUN, outer, inner, labels, units
        )
    return _nm_grouped(text, lhs, cov, terms, frame, order_groups, FUN, outer, inner, labels, units)


def _nf_grouped(
    text, lhs, cov, group_name, frame, order_groups, FUN, outer, inner, labels, units
) -> DataFrame:
    nrow = frame.nrow
    response = eval_expr(lhs, frame.columns, nrow)
    primary = _covariate(cov, frame.columns, nrow)
    groups = _as_factor(eval_expr(group_name, frame.columns, nrow))
    fun = max_na_rm if FUN is None else FUN
    if order_groups and not groups.ordered:
        if outer is None:
            levs = _order_levels(response, groups, fun)
        else:
            levs = _order_levels_outer(response, groups, fun, outer, frame.columns, nrow)
        if len(set(levs)) != len(levs):
            dup = next(level for level in levs if levs.count(level) > 1)
            raise ValueError(f"factor level [{levs.index(dup) + 1}] is duplicated")
        groups = Factor.from_values(groups.texts(), levels=levs, ordered=True)
    columns = dict(frame.columns)
    columns[group_name] = groups
    no_vars = not _identifiers(cov)
    if no_vars or isinstance(primary, Factor) or not np.issubdtype(np.asarray(primary).dtype, np.number):
        cls = "nffGroupedData"
    else:
        cls = "nfnGroupedData"
    attributes = _attributes(text, labels, units, outer, inner, fun, order_groups)
    return DataFrame(
        columns=columns,
        attributes=attributes,
        classes=(cls, "nfGroupedData", "groupedData", "data.frame"),
    )


def _nm_grouped(
    text, lhs, cov, terms, frame, order_groups, FUN, outer, inner, labels, units
) -> DataFrame:
    nrow = frame.nrow
    eval_expr(lhs, frame.columns, nrow)
    _covariate(cov, frame.columns, nrow)
    for term in terms:
        eval_expr(term, frame.columns, nrow)
    attributes = _attributes(text, labels, units, outer, inner, FUN or max_na_rm, order_groups)
    attributes["formulaList"] = terms
    attributes["order.groups"] = {term: bool(order_groups) for term in terms}
    return DataFrame(
        columns=dict(frame.columns),
        attributes=attributes,
        classes=("nmGroupedData", "groupedData", "data.frame"),
    )


def _attributes(text, labels, units, outer, inner, fun, order_groups) -> dict[str, Any]:
    attributes: dict[str, Any] = {
        "formula": text,
        "FUN": fun,
        "order.groups": bool(order_groups),
    }
    if labels is not None:
        attributes["labels"] = dict(labels)
    if units is not None:
        attributes["units"] = dict(units)
    if outer is not None:
        attributes["outer"] = _formula_text(outer)
    if inner is not None:
        attributes["inner"] = _formula_text(inner)
    return attributes


def _order_levels(response: np.ndarray, groups: Factor, fun) -> list[str]:
    """``names(sort(tapply(response, groups, FUN)))``: stable sort by summary value."""
    summaries: list[tuple[str, float]] = []
    for code, level in enumerate(groups.levels):
        rows = np.nonzero(groups.codes == code)[0]
        if rows.size == 0:
            continue
        value = float(fun(response[rows]))
        if not math.isnan(value):
            summaries.append((level, value))
    summaries.sort(key=lambda item: item[1])
    return [level for level, _ in summaries]


def _order_levels_outer(response, groups, fun, outer, columns, nrow) -> list[str]:
    outer_text = _formula_text(outer)
    outer_expr = outer_text.split("~", 1)[1].strip()
    outer_names = _identifiers(outer_expr)
    if not outer_names:
        return _order_levels(response, groups, fun)
    texts = [_text_column(columns[name], nrow) for name in outer_names]
    combined = [_OUTER_SEP.join(row) for row in zip(*texts)]
    levs: list[str] = []
    for key in sorted(set(combined)):
        rows = np.array([i for i, value in enumerate(combined) if value == key], dtype=np.int64)
        levs.extend(_order_levels(response[rows], groups.subset(rows), fun))
    return levs


def _covariate(cov: str, columns: Mapping[str, Any], nrow: int):
    if not _identifiers(cov):
        return np.ones(nrow, dtype=np.float64)
    return eval_expr(cov, columns, nrow)


def _identifiers(expr: str) -> list[str]:
    return [name for name in _IDENT.findall(expr or "") if name not in _FUNCTIONS]


def _text_column(column, nrow: int) -> list[str]:
    if isinstance(column, Factor):
        return column.texts()
    return [_text(v) for v in np.asarray(column)]


def _as_factor(value) -> Factor:
    """``as.factor(value)[drop = TRUE]``."""
    if isinstance(value, Factor):
        used = sorted(set(int(code) for code in value.codes))
        remap = {old: new for new, old in enumerate(used)}
        levels = tuple(value.levels[i] for i in used)
        codes = np.array([remap[int(code)] for code in value.codes], dtype=np.int64)
        return Factor(codes, levels, value.ordered)
    return Factor.from_values(value)


def _as_frame(data) -> DataFrame:
    if isinstance(data, DataFrame):
        return DataFrame(columns=dict(data.columns), attributes=dict(data.attributes), classes=data.classes)
    if isinstance(data, Mapping):
        columns = {}
        for name, column in data.items():
            if isinstance(column, Factor):
                columns[name] = column
            elif all(_is_number(v) for v in column):
                columns[name] = np.asarray(column, dtype=np.float64)
            else:
                columns[name] = np.asarray([_text(v) for v in column], dtype=object)
        return DataFrame(columns=columns)
    raise TypeError("second argument to 'groupedData' must inherit from data.frame")


def _formula_text(form) -> str:
    if isinstance(form, str):
        return form.strip()
    if isinstance(form, DataFrame) and form.formula:
        return form.formula.strip()
    raise ValueError("'form' must be a formula")


def _is_number(value) -> bool:
    return isinstance(value, (int, float, np.integer, np.floating)) and not isinstance(value, bool)


def _number_text(value: float) -> str:
    if float(value).is_integer():
        return str(int(value))
    return repr(float(value))


def _text(value) -> str:
    if _is_number(value):
        return _number_text(float(value))
    return str(value)
