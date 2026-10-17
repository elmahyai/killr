"""Construction of ``pdMat`` objects (nlme ``pdConstruct`` and ``pdConstruct.pdMat``).

R dispatches ``pdConstruct`` on the class of ``object``. Python keeps the same
fields on ``PdMat`` and dispatches on ``pd_class``. The ``value`` argument is
read the way R reads it:

- empty -> an uninitialized object that keeps its names and formula;
- character vector -> names;
- square matrix -> the upper Cholesky factor of its symmetric part;
- numeric vector -> unconstrained parameters;
- one-sided formula -> names from the model matrix columns.

Not translated: two-sided and list-of-formula values, matrices with dimnames,
and factor variables in ``data``. Each raises ``NotImplementedError``.
"""

from __future__ import annotations

import re
import warnings
from dataclasses import dataclass
from typing import Any

import numpy as np

from nlme.pdmat import PdMat, is_initialized

_MISSING: Any = object()


@dataclass(slots=True)
class Resolved:
    """Result of reading ``value``, ``form``, and ``nam`` for a ``pdMat`` constructor."""

    kind: str  # "empty", "numeric", or "matrix"
    names: tuple[str, ...]
    formula: str | None
    values: np.ndarray | None = None
    chol: np.ndarray | None = None


def pdConstruct(
    object: Any,
    value: Any = (),
    form: Any = _MISSING,
    nam: Any = _MISSING,
    data: Any = None,
) -> Any:
    """Construct or re-initialize a ``pdMat`` object, dispatching on its class.

    When ``form`` or ``nam`` is omitted, the object's own formula and names are
    used, as R does with ``formula(object)`` and ``Names(object)``.
    """
    from nlme.pdblocked import construct_pd_blocked
    from nlme.pdfactor import PdBlocked

    if isinstance(object, PdBlocked):
        if form is _MISSING:
            form = None
        if nam is _MISSING:
            nam = [list(names) for names in object.names_list]
        return construct_pd_blocked(object, value, form, nam, data)

    if form is _MISSING:
        form = object.formula
    if nam is _MISSING:
        nam = object.names

    cls = object.pd_class
    if cls == "pdDiag":
        from nlme.pddiag import construct_pd_diag

        return construct_pd_diag(object, value, form, nam, data)
    if cls == "pdIdent":
        from nlme.pdident import construct_pd_ident

        return construct_pd_ident(object, value, form, nam, data)
    if cls == "pdCompSymm":
        from nlme.pdcompsymm import construct_pd_comp_symm

        return construct_pd_comp_symm(object, value, form, nam, data)
    if cls == "pdLogChol":
        from nlme.pdlogchol import construct_pd_log_chol

        return construct_pd_log_chol(object, value, form, nam, data)
    if cls == "pdSymm":
        return _construct_pd_symm(object, value, form, nam, data)
    raise NotImplementedError(f"pdConstruct for class {cls!r} is not translated")


def resolve_value(value: Any, form: Any, nam: Any, data: Any) -> Resolved:
    """Read ``value``, ``form``, and ``nam`` as ``pdConstruct.pdMat`` does."""
    names = _as_names(nam)
    formula = None

    if isinstance(value, PdMat):
        if form is None:
            form = value.formula
        if not names:
            names = value.names
        if is_initialized(value):
            from nlme.pdmatrix import pdMatrix

            value = pdMatrix(value)
        else:
            value = ()

    if _is_formula_text(value):
        if form is not None:
            warnings.warn("ignoring argument 'form'", stacklevel=3)
        form = value
        value = ()
    elif _is_character(value):
        if names:
            warnings.warn("ignoring argument 'nam'", stacklevel=3)
        names = tuple(str(item) for item in value)
        value = ()

    if _is_empty(value):
        kind = "empty"
        values = None
        chol = None
    elif _is_matrix(value):
        mat = np.asarray(value, dtype=np.float64)
        if mat.shape[0] != mat.shape[1]:
            raise ValueError("'value' must be a square matrix")
        try:
            chol = np.linalg.cholesky((mat + mat.T) / 2.0).T
        except np.linalg.LinAlgError as exc:
            raise ValueError("the matrix is not positive definite") from exc
        kind = "matrix"
        values = None
    elif _is_numeric(value):
        kind = "numeric"
        values = np.asarray(value, dtype=np.float64).ravel()
        chol = None
    else:
        raise NotImplementedError(
            "list-of-formula and other pdMat value types are not translated"
        )

    if form is not None:
        formula = _form_text(form)
        names_form = _names_from_formula(formula, data)
        if names_form:
            if not names:
                names = names_form
            elif not _names_consistent(names, names_form):
                raise ValueError("'form' not consistent with 'nam'")

    if kind == "matrix" and names and len(names) != chol.shape[1]:
        raise ValueError("length of 'nam' not consistent with dimensions of initial value")

    return Resolved(kind=kind, names=names, formula=formula, values=values, chol=chol)


def _construct_pd_symm(object: PdMat, value: Any, form: Any, nam: Any, data: Any) -> PdMat:
    res = resolve_value(value, form, nam, data)
    if res.kind == "empty":
        return PdMat(values=np.empty(0), formula=res.formula, names=res.names, pd_class="pdSymm")
    if res.kind == "matrix":
        raise NotImplementedError("pdSymm from a matrix is not translated")
    n = res.values.size
    ncol = _pd_symm_ncol(n)
    if n != ncol * (ncol + 1) // 2:
        raise ValueError(
            f"an object of length {n} does not match the required parameter size"
        )
    return PdMat(values=res.values, formula=res.formula, names=res.names, pd_class="pdSymm")


def _as_names(nam: Any) -> tuple[str, ...]:
    if nam is None:
        return ()
    if isinstance(nam, str):
        return (nam,)
    return tuple(str(item) for item in nam)


def _is_formula_text(value: Any) -> bool:
    return isinstance(value, str) and "~" in value


def _is_character(value: Any) -> bool:
    if isinstance(value, str):
        return True
    if isinstance(value, (list, tuple, np.ndarray)) and len(value) > 0:
        return all(isinstance(item, str) for item in value)
    return False


def _is_empty(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, (list, tuple, np.ndarray)):
        return len(value) == 0
    return False


def _is_matrix(value: Any) -> bool:
    if isinstance(value, np.ndarray):
        return value.ndim == 2
    if isinstance(value, (list, tuple)) and value:
        return all(isinstance(row, (list, tuple, np.ndarray)) for row in value)
    return False


def _is_numeric(value: Any) -> bool:
    if isinstance(value, (bool, str)):
        return False
    if isinstance(value, (int, float, np.number)):
        return True
    if isinstance(value, np.ndarray):
        return value.dtype.kind in "biuf"
    if isinstance(value, (list, tuple)):
        return all(isinstance(item, (int, float, np.number)) for item in value)
    return False


def _form_text(form: Any) -> str:
    if isinstance(form, str):
        return form.strip()
    raise NotImplementedError("list-of-formula 'form' is not translated")


_TOKEN = re.compile(r"[+-]|[A-Za-z.][A-Za-z0-9._]*|[0-9]+")


def _names_from_formula(text: str, data: Any) -> tuple[str, ...]:
    """Column names of the model matrix of a one-sided formula, as ``Names.formula``.

    Names are empty when ``data`` is missing a variable, as R returns ``NULL``.
    """
    if "~" not in text:
        raise ValueError("'form' can only be a formula or a list of formulae")
    lhs, rhs = text.split("~", 1)
    if lhs.strip():
        raise NotImplementedError("two-sided formulas are not translated for pdMat names")
    rhs = rhs.strip()
    tokens = _TOKEN.findall(rhs)
    if "".join(tokens) != re.sub(r"\s+", "", rhs):
        raise NotImplementedError("only additive terms are translated for pdMat formulas")
    intercept = True
    variables: list[str] = []
    sign = "+"
    for token in tokens:
        if token in ("+", "-"):
            sign = token
            continue
        if token in ("0", "1"):
            if token == "0" or sign == "-":
                intercept = False
            else:
                intercept = True
        else:
            if sign == "-":
                raise NotImplementedError("removing a variable from a pdMat formula is not translated")
            variables.append(token)
        sign = "+"
    if not variables:
        return ("(Intercept)",) if intercept else ()
    if not isinstance(data, dict):
        return ()
    if any(name not in data for name in variables):
        return ()
    for name in variables:
        if np.asarray(data[name]).dtype.kind not in "biuf":
            raise NotImplementedError("factor variables in pdMat formulas are not translated")
    columns = ["(Intercept)"] if intercept else []
    return tuple(columns + variables)


def _names_consistent(names: tuple[str, ...], names_form: tuple[str, ...]) -> bool:
    """Check ``nam`` against formula names, allowing the ``.(Intercept)`` suffix as R does."""
    no_match = [name not in names_form for name in names]
    if not any(no_match):
        return True
    copy = list(names)
    for index, name in enumerate(names):
        if no_match[index] and len(name) > 12 and name.endswith("(Intercept)"):
            copy[index] = name[:-12]
            no_match[index] = False
    for index in range(len(names)):
        if no_match[index]:
            copy[index] = copy[index] + ".(Intercept)"
    return all(name in names_form for name in copy)


def _pd_symm_ncol(length: int) -> int:
    return int(round((np.sqrt(8 * length + 1) - 1) / 2))
