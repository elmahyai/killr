"""Names of nlme objects and their assignment (nlme ``Names`` and ``Names<-``).

``Names`` dispatches on the Python stand-in for the R class: formulas,
``listForm`` lists, ``pdMat`` objects, and ``reStruct`` objects. ``set_names``
is the ``Names<-`` generic and returns the updated object, because Python
assignment syntax does not change the caller's binding.
"""

from __future__ import annotations

import re
from dataclasses import replace
from typing import Any, Mapping, Sequence

import numpy as np

from nlme.getcovariateformula import getCovariateFormula
from nlme.pdmat import Dim as pd_mat_dim
from nlme.pdmat import PdMat
from nlme.restruct import PdMatElement, ReStruct, _names_formula

__all__ = ["ListForm", "Names", "set_names"]

_NO_INTERCEPT = re.compile(r"(?<![\w.])0(?![\w.])|-\s*1(?![\w.])")
_VARIABLE = re.compile(r"(?<![A-Za-z0-9._])([A-Za-z.][A-Za-z0-9._]*)(\s*\()?")


class ListForm(list):
    """A list of one-sided or two-sided formulas, the R class ``listForm``."""


def Names(
    object: Any,
    data: Mapping[str, Sequence[Any]] | None = None,
    exclude: Sequence[str] = ("pi", "."),
) -> Any:
    """Extract the names of a ``pdMat``, ``reStruct``, formula, or ``listForm`` object."""
    if isinstance(object, ReStruct):
        return [Names(element) for _, element in object.blocks]
    if isinstance(object, (PdMat, PdMatElement)):
        return tuple(object.names)
    if isinstance(object, ListForm):
        return _names_list_form(object, data, exclude)
    if _is_formula_like(object):
        return _names_formula_method(object, data, exclude)
    raise TypeError(f"no applicable method for 'Names' applied to {type(object).__name__}")


def set_names(object: Any, value: Sequence[Any] | None) -> Any:
    """Assign names to a ``pdMat``, ``pdMat`` element, or ``reStruct`` object.

    Returns the updated object. The input is not modified.
    """
    if isinstance(object, ReStruct):
        if len(object.blocks) != len(value):
            raise ValueError("incompatible lengths for object names")
        blocks = [
            (name, _set_pd_names(element, value[index]))
            for index, (name, element) in enumerate(object.blocks)
        ]
        return ReStruct(blocks, object.settings.copy(), object.plen)
    if isinstance(object, (PdMat, PdMatElement)):
        return _set_pd_names(object, value)
    raise TypeError(f"no applicable method for 'Names<-' applied to {type(object).__name__}")


def _is_formula_like(object: Any) -> bool:
    if isinstance(object, str):
        return "~" in object
    return type(object).__name__ in ("CovariateFormula", "Formula")


def _formula_text(object: Any) -> str:
    if isinstance(object, str):
        return object.strip()
    if hasattr(object, "text"):
        return str(object.text)
    return str(object)


def _names_formula_method(
    object: Any,
    data: Mapping[str, Sequence[Any]] | None,
    exclude: Sequence[str],
) -> tuple[str, ...] | None:
    """``Names.formula``: model-matrix column names, or ``(Intercept)`` for no variables."""
    frame: Mapping[str, Sequence[Any]] = data if data is not None else {}
    text = _formula_text(object)
    rhs = text.split("~", 1)[-1]
    all_vars = [name for name in _all_vars(text) if name not in exclude]
    if not all_vars:
        return ("(Intercept)",) if _has_intercept(rhs) else None
    if any(name not in frame for name in all_vars):
        return None
    return tuple(_names_formula(text, frame))


def _names_list_form(
    object: ListForm,
    data: Mapping[str, Sequence[Any]] | None,
    exclude: Sequence[str],
) -> list[str] | None:
    """``Names.listForm``: paste each response name onto the names of its covariate formula."""
    pnames = [_first_argument(_formula_text(element)) for element in object]
    nams = [_names_formula_method(getCovariateFormula(element), data, exclude) for element in object]
    if not nams or nams[0] is None:
        return None
    values: list[str] = []
    for pname, nam in zip(pnames, nams):
        if not nam or (len(nam) == 1 and nam[0] == "(Intercept)"):
            values.append(pname)
        else:
            values.extend(f"{pname}.{part}" for part in nam)
    return values


def _all_vars(text: str) -> list[str]:
    """Variable names in a formula, excluding function names, in first-appearance order."""
    found: list[str] = []
    for match in _VARIABLE.finditer(text):
        if match.group(2):
            continue
        name = match.group(1)
        if name not in found:
            found.append(name)
    return found


def _has_intercept(rhs: str) -> bool:
    return _NO_INTERCEPT.search(rhs) is None


def _first_argument(text: str) -> str:
    """The first argument of ``~`` in a formula: the response for two-sided formulas."""
    parts = text.split("~", 1)
    if len(parts) == 2 and parts[0].strip():
        return parts[0].strip()
    return parts[-1].strip()


def _initialized(object: PdMat | PdMatElement) -> bool:
    return int(len(object.values)) > 0


def _side(object: PdMat | PdMatElement) -> int:
    if isinstance(object, PdMat):
        return pd_mat_dim(object)[1]
    return len(object.names)


def _set_pd_names(object: PdMat | PdMatElement, value: Sequence[Any] | None) -> Any:
    """``Names<-.pdMat``: set the names, allowing the nlme ``(Intercept)`` spellings."""
    if value is None:
        return replace(object, names=())
    new_names = [str(item) for item in value]
    dn = tuple(object.names)
    if len(dn) == 0:
        if _initialized(object):
            aux = _side(object)
            if len(new_names) != aux:
                raise ValueError(f"Length of names should be {aux}")
        return replace(object, names=tuple(new_names))
    if len(dn) != len(new_names):
        raise ValueError(f"Length of names should be {len(dn)}")

    err = False
    value_copy = list(new_names)
    no_match = [name not in dn for name in new_names]
    if any(no_match):
        err = True
        ind_no_match = [index for index, flag in enumerate(no_match) if flag]
        nam1 = [new_names[index] for index in ind_no_match]
        if any(len(name) > 12 for name in nam1):
            wch1 = [name.endswith("(Intercept)") for name in nam1]
            if any(wch1):
                for position, flag in enumerate(wch1):
                    if flag:
                        index = ind_no_match[position]
                        value_copy[index] = nam1[position][: len(nam1[position]) - 12]
                        no_match[index] = False
                ind_no_match = [index for position, index in enumerate(ind_no_match) if not wch1[position]]
        if any(no_match):
            for index in ind_no_match:
                value_copy[index] = f"{value_copy[index]}.(Intercept)"

        ind_match = [dn.index(name) if name in dn else None for name in value_copy]
        if all(position is not None for position in ind_match):
            if len(ind_match) > 1 and _any_not_consecutive(ind_match) and _initialized(object):
                from nlme.matrix_assign import matrix_assign
                from nlme.pdmatrix import pdMatrix
                from nlme.pdconstruct import pdConstruct

                order = [int(position) for position in ind_match]
                matrix = pdMatrix(object)
                reordered = matrix[np.ix_(order, order)]
                try:
                    return pdConstruct(object, reordered, nam=new_names)
                except NotImplementedError:
                    return replace(matrix_assign(object, reordered), names=tuple(new_names))
            return replace(object, names=tuple(new_names))

    if err:
        raise ValueError("names being assigned do not correspond to a permutation of previous names")

    ind_match = [dn.index(name) for name in new_names]
    if len(ind_match) == 1 or not _any_not_consecutive(ind_match):
        return object
    if _initialized(object):
        from nlme.matrix_assign import matrix_assign
        from nlme.pdmatrix import pdMatrix
        from nlme.pdconstruct import pdConstruct

        reordered = pdMatrix(object)[np.ix_(ind_match, ind_match)]
        try:
            return pdConstruct(object, reordered, nam=new_names)
        except NotImplementedError:
            return replace(matrix_assign(object, reordered), names=tuple(new_names))
    return replace(object, names=tuple(new_names))


def _any_not_consecutive(indices: Sequence[int]) -> bool:
    return any(indices[index + 1] - indices[index] != 1 for index in range(len(indices) - 1))
