"""Formulas for the grouping factors of a model (nlme ``getGroupsFormula``)."""

from __future__ import annotations

from typing import Any

from nlme.getcovariateformula import _deparse, _parse_bar, _tokenize
from nlme.lmlistformula import LmList
from nlme.restruct import ReStruct


def getGroupsFormula(object: Any, asList: bool = False, sep: str = "/"):
    """Return the grouping formula, or a list of ``(name, formula)`` pairs when ``asList``.

    The result is ``None`` when the object has no grouping (R ``NULL``).
    """
    if isinstance(object, ReStruct):
        return _restruct_groups(object, asList)
    if isinstance(object, LmList):
        return _lmlist_groups(object, asList, sep)
    model = getattr(object, "modelStruct", None)
    if model is not None:
        rstruct = getattr(model, "reStruct", None)
        if rstruct is not None:
            return getGroupsFormula(rstruct, asList)
        cstruct = getattr(model, "corStruct", None)
        if cstruct is None:
            return None
        return getGroupsFormula(cstruct, asList)
    return _default_groups(object, asList, sep)


def _restruct_groups(object: ReStruct, asList: bool):
    """``getGroupsFormula.reStruct``: the block names are reversed, as ``rev(formula(object))``."""
    names = [name for name in reversed(object.names) if name]
    if not names:
        return None
    if asList:
        return [(name, f"~{name}") for name in names]
    return f"~{'/'.join(names)}"


def _lmlist_groups(object: LmList, asList: bool, sep: str):
    """``getGroupsFormula.lmList``: the stored ``~Group`` becomes ``~1 | Group``."""
    group = object.groups_form.split("~", 1)[1].strip()
    return _groups_from_tree(_rhs_tree(f"~1 | {group}"), asList, sep)


def _default_groups(object: Any, asList: bool, sep: str):
    """``getGroupsFormula.default``: the groups are the right side of a top-level ``|``."""
    text = _formula_text(object)
    if text is None:
        raise ValueError("'form' argument must be a formula")
    return _groups_from_tree(_rhs_tree(text), asList, sep)


def _groups_from_tree(tree, asList: bool, sep: str):
    if tree[0] != "|":
        return None
    right = tree[2]
    if not asList:
        return f"~{_deparse_groups(right, sep)}"
    levels = _flatten(right, sep)
    return [(_deparse_groups(level, sep), f"~{_deparse_groups(level, sep)}") for level in levels]


def _flatten(node, sep: str) -> list:
    if node[0] == sep:
        return _flatten(node[1], sep) + _flatten(node[2], sep)
    return [node]


def _deparse_groups(node, sep: str) -> str:
    if node[0] == sep:
        return f"{_deparse_groups(node[1], sep)}{sep}{_deparse_groups(node[2], sep)}"
    return _deparse(node)


def _rhs_tree(text: str):
    if "~" not in text:
        raise ValueError("'form' argument must be a formula")
    rhs = text.split("~", 1)[1].strip()
    tokens = _tokenize(rhs)
    tree, pos = _parse_bar(tokens, 0)
    if pos != len(tokens):
        raise ValueError("invalid formula")
    return tree


def _formula_text(object: Any) -> str | None:
    if isinstance(object, str):
        return object.strip() if "~" in object else None
    value = getattr(object, "formula", None)
    if isinstance(value, str) and "~" in value:
        return value.strip()
    return None
