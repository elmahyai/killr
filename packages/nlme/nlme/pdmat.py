"""Positive-definite matrix constructor (nlme ``pdMat``)."""

from __future__ import annotations

import warnings
from dataclasses import dataclass, replace
from typing import Any, Mapping, Sequence

import numpy as np

from nlme.asoneformula import Formula


@dataclass(slots=True)
class PdMat:
    """Storage for an nlme ``pdMat`` object (unconstrained parameter vector plus metadata)."""

    values: np.ndarray
    formula: Any = None
    names: tuple[str, ...] = ()
    pd_class: str = "pdSymm"
    ncol: int | None = None

    @property
    def classes(self) -> tuple[str, ...]:
        if self.pd_class == "pdLogChol":
            return (self.pd_class, "pdSymm", "pdMat")
        return (self.pd_class, "pdMat")


def pdMat(
    value: Any = None,
    form: Any = None,
    nam: Sequence[str] | None = None,
    data: Mapping[str, Sequence[Any]] | None = None,
    pdClass: str = "pdSymm",
) -> PdMat:
    """Construct a ``pdMat`` object, dispatching on ``pdClass`` like R's generic constructor."""
    if value is None:
        value = np.array([], dtype=np.float64)
    if isinstance(value, PdMat):
        pdClass = value.pd_class
    return _pd_construct(value, form, nam, data, pdClass)


def is_initialized(object: PdMat) -> bool:
    """Return whether ``object`` has assigned parameters."""
    return int(object.values.size) > 0


def Dim(object: PdMat) -> tuple[int, int]:
    """Square dimension of a ``pdMat`` object."""
    if is_initialized(object):
        if object.pd_class == "pdDiag":
            side = int(object.values.size)
            return side, side
        if object.pd_class in ("pdIdent", "pdCompSymm") and object.ncol is not None:
            side = int(object.ncol)
            return side, side
        side = _pd_symm_ncol(int(object.values.size))
        return side, side
    if object.names:
        side = len(object.names)
        return side, side
    if object.ncol is not None:
        side = int(object.ncol)
        return side, side
    return 0, 0


def Names(object: PdMat | str, data: Mapping[str, Sequence[Any]] | None = None) -> tuple[str, ...]:
    """Row/column names for a ``pdMat`` object or formula."""
    if isinstance(object, PdMat):
        return object.names
    return _names_formula(_formula_text(object), data)


def _pd_construct(
    value: Any,
    form: Any,
    nam: Sequence[str] | None,
    data: Mapping[str, Sequence[Any]] | None,
    pd_class: str,
) -> PdMat:
    base = _pd_construct_pd_mat(value, form, nam, data, pd_class)
    dispatch = {
        "pdSymm": _finalize_pd_symm,
        "pdLogChol": _finalize_pd_log_chol,
        "pdDiag": _finalize_pd_diag,
        "pdIdent": _finalize_pd_ident,
        "pdCompSymm": _finalize_pd_comp_symm,
    }
    finalizer = dispatch.get(pd_class, _finalize_default)
    return finalizer(base)


def _pd_construct_pd_mat(
    value: Any,
    form: Any,
    nam: Sequence[str] | None,
    data: Mapping[str, Sequence[Any]] | None,
    pd_class: str,
) -> PdMat | np.ndarray:
    names = tuple(nam) if nam else ()
    formula_obj = form
    if isinstance(value, PdMat):
        if form is None:
            formula_obj = value.formula
        if not names:
            names = value.names
        if is_initialized(value):
            matrix_values = _as_matrix(value)
            return _pd_construct_pd_mat(matrix_values, formula_obj, names, data, pd_class)
        return _pd_construct_pd_mat(
            np.array([], dtype=np.float64),
            formula_obj,
            names,
            data,
            pd_class,
        )

    matrix_intermediate: np.ndarray | None = None
    values = np.array([], dtype=np.float64)

    if isinstance(value, np.ndarray) and value.size > 0:
        if value.ndim == 2:
            matrix_intermediate, names = _matrix_from_pd_matrix(value, names)
        elif value.ndim == 1:
            values = np.asarray(value, dtype=np.float64).ravel()
        else:
            raise ValueError(f"{value!r} is not a valid object for \"pdMat\"")
    elif isinstance(value, (list, tuple)) and value and all(_is_formula(item) for item in value):
        if form is not None:
            warnings.warn("ignoring argument 'form'", stacklevel=2)
        formula_obj = list(value)
    elif _is_formula(value):
        if form is not None:
            warnings.warn("ignoring argument 'form'", stacklevel=2)
        formula_obj = _formula_text(value)
    elif isinstance(value, (list, tuple)) and value and all(isinstance(item, str) for item in value):
        if names:
            warnings.warn("ignoring argument 'nam'", stacklevel=2)
        names = tuple(str(item) for item in value)
    elif isinstance(value, (int, float)) or (isinstance(value, np.ndarray) and value.size == 0):
        values = np.asarray(value, dtype=np.float64).ravel()
    elif isinstance(value, (list, tuple)) and value and not _is_formula(value[0]):
        values = np.asarray(value, dtype=np.float64).ravel()
    elif isinstance(value, (list, tuple)) and not value:
        values = np.array([], dtype=np.float64)
    elif value is None:
        values = np.array([], dtype=np.float64)
    else:
        raise ValueError(f"{value!r} is not a valid object for \"pdMat\"")

    names = _resolve_names(formula_obj, names, data)

    if matrix_intermediate is not None:
        if names and len(names) != matrix_intermediate.shape[1]:
            raise ValueError("length of 'nam' not consistent with dimensions of initial value")
        return PdMat(
            np.asarray(matrix_intermediate, dtype=np.float64),
            formula_obj,
            names,
            pd_class,
            None,
        )

    return PdMat(values, formula_obj, names, pd_class, None)


def _finalize_default(base: PdMat | np.ndarray) -> PdMat:
    if isinstance(base, PdMat):
        return base
    raise TypeError("unexpected matrix intermediate for pdMat class")


def _finalize_pd_diag(base: PdMat | np.ndarray) -> PdMat:
    if isinstance(base, PdMat):
        if not is_initialized(base):
            return base
        if base.values.ndim == 2:
            chol = base.values
            diag_vals = np.diag(chol @ chol.T)
            values = np.log(diag_vals) / 2.0
            return replace(base, values=np.asarray(values, dtype=np.float64).ravel())
        return _check_pd_diag_length(base)
    raise TypeError("unexpected matrix intermediate for pdDiag")


def _finalize_pd_symm(base: PdMat | np.ndarray) -> PdMat:
    if isinstance(base, PdMat):
        if not is_initialized(base):
            return replace(base, pd_class="pdSymm")
        if base.values.ndim == 2:
            sym = base.values
            u, s, vt = np.linalg.svd(sym, full_matrices=False)
            object_mat = vt.T @ (np.log(s)[:, None] * vt)
            values = object_mat[np.triu_indices(object_mat.shape[0])]
            return replace(base, values=np.asarray(values, dtype=np.float64).ravel(), pd_class="pdSymm")
        ncol = _pd_symm_ncol(int(base.values.size))
        expected = ncol * (ncol + 1) // 2
        if base.values.size != expected:
            raise ValueError(
                f"an object of length {base.values.size} does not match the required parameter size"
            )
        return replace(base, pd_class="pdSymm")
    raise TypeError("unexpected matrix intermediate for pdSymm")


def _finalize_pd_log_chol(base: PdMat | np.ndarray) -> PdMat:
    if isinstance(base, PdMat):
        if not is_initialized(base):
            return replace(base, pd_class="pdLogChol")
        if base.values.ndim == 2:
            chol = base.values
            diag = np.log(np.diag(chol))
            upper = chol[np.triu_indices(chol.shape[0], k=1)]
            values = np.concatenate([diag, upper])
            return replace(base, values=np.asarray(values, dtype=np.float64).ravel(), pd_class="pdLogChol")
        ncol = _pd_symm_ncol(int(base.values.size))
        expected = ncol * (ncol + 1) // 2
        if base.values.size != expected:
            raise ValueError(
                f"an object of length {base.values.size} does not match a Cholesky factor"
            )
        return replace(base, pd_class="pdLogChol")
    raise TypeError("unexpected matrix intermediate for pdLogChol")


def _finalize_pd_ident(base: PdMat | np.ndarray) -> PdMat:
    if isinstance(base, PdMat):
        if not is_initialized(base):
            ncol = len(base.names)
            return replace(base, ncol=ncol if ncol > 0 else None)
        if base.values.ndim == 2:
            chol = base.values
            value = float(np.log(np.mean(np.diag(chol @ chol.T))) / 2.0)
            ncol = chol.shape[1]
            return replace(
                base,
                values=np.array([value], dtype=np.float64),
                pd_class="pdIdent",
                ncol=ncol,
            )
        if base.values.size > 1:
            raise ValueError(
                f"an object of length {base.values.size} does not match the required parameter size"
            )
        ncol = len(base.names)
        if ncol == 0 and base.formula is None:
            raise ValueError('must give names when initializing "pdIdent" from parameter without a formula')
        return replace(base, pd_class="pdIdent", ncol=ncol if ncol > 0 else None)
    raise TypeError("unexpected matrix intermediate for pdIdent")


def _finalize_pd_comp_symm(base: PdMat | np.ndarray) -> PdMat:
    if isinstance(base, PdMat):
        if not is_initialized(base):
            ncol = len(base.names)
            return replace(base, ncol=ncol if ncol > 0 else None, pd_class="pdCompSymm")
        if base.values.ndim == 2:
            variance = base.values @ base.values.T
            ncol = variance.shape[0]
            sd = float(np.sqrt(np.mean(np.diag(variance))))
            off = variance[np.triu_indices(ncol, k=1)]
            rho = float(np.mean(off / (sd * sd))) if off.size else 0.0
            rho = min(max(rho, -1.0 + 1e-8), 1.0 - 1e-8)
            values = np.array([np.log(sd), np.arctanh(rho)], dtype=np.float64)
            return replace(base, values=values, pd_class="pdCompSymm", ncol=ncol)
        if base.values.size != 2:
            raise ValueError(
                f"an object of length {base.values.size} does not match the required parameter size"
            )
        return replace(base, pd_class="pdCompSymm", ncol=base.ncol)
    raise TypeError("unexpected matrix intermediate for pdCompSymm")


def _check_pd_diag_length(base: PdMat) -> PdMat:
    name_count = len(base.names)
    if name_count and name_count != base.values.size:
        raise ValueError(
            f"an object of length {base.values.size} does not match the required parameter size"
        )
    return base


def _matrix_from_pd_matrix(value: np.ndarray, names: Sequence[str]) -> tuple[np.ndarray, tuple[str, ...]]:
    array = np.asarray(value, dtype=np.float64)
    if array.ndim != 2 or array.shape[0] != array.shape[1]:
        raise ValueError("'value' must be a square matrix")
    resolved = tuple(names)
    vnam = _matrix_dimnames(array)
    if vnam is not None:
        if len(vnam) != array.shape[0]:
            raise ValueError("dimnames of 'value' must match or be NULL")
        if resolved:
            if not _names_match(resolved, vnam):
                raise ValueError("names of 'value' are not consistent with 'nam' argument")
            order = [_index_name(name, vnam) for name in resolved]
            array = array[np.ix_(order, order)]
        else:
            resolved = vnam
    chol = np.linalg.cholesky((array + array.T) / 2.0)
    return chol, resolved


def _matrix_dimnames(array: np.ndarray) -> tuple[str, ...] | None:
    if array.dtype.names:
        return tuple(array.dtype.names)
    return None


def _names_match(left: Sequence[str], right: Sequence[str]) -> bool:
    try:
        return all(left.index(name) >= 0 for name in right) and all(right.index(name) >= 0 for name in left)
    except ValueError:
        return False


def _index_name(name: str, names: Sequence[str]) -> int:
    return names.index(name)


def _resolve_names(
    form: Any,
    names: Sequence[str],
    data: Mapping[str, Sequence[Any]] | None,
) -> tuple[str, ...]:
    if form is None:
        return tuple(names)
    names_form = _names_from_form(form, data)
    if not names_form:
        return tuple(names)
    if not names:
        return names_form
    if not _form_consistent_with_names(tuple(names), names_form):
        raise ValueError("'form' not consistent with 'nam'")
    return tuple(names)


def _names_from_form(form: Any, data: Mapping[str, Sequence[Any]] | None) -> tuple[str, ...]:
    if isinstance(form, list):
        parts: list[str] = []
        for entry in form:
            parts.extend(_names_from_form(entry, data))
        return tuple(_unique(parts))
    text = _formula_text(form)
    if _formula_length(text) == 3:
        return _names_formula(_get_covariate_formula(text), data)
    return _names_formula(text, data)


def _form_consistent_with_names(names: tuple[str, ...], names_form: tuple[str, ...]) -> bool:
    if all(name in names_form for name in names):
        return True
    modified = list(names)
    for index, name in enumerate(names):
        if name.endswith(".(Intercept)"):
            modified[index] = name[: -len(".(Intercept)")]
        else:
            modified[index] = f"{name}.(Intercept)"
    return all(name in names_form for name in modified)


def _names_formula(form: str, data: Mapping[str, Sequence[Any]] | None) -> tuple[str, ...]:
    _, columns = _model_matrix(form, data or {})
    return tuple(columns)


def _model_matrix(form: str, data: Mapping[str, Sequence[Any]]) -> tuple[int, list[str]]:
    text = _formula_text(form)
    if not text.startswith("~"):
        raise ValueError("formula must be one-sided")
    rhs = text[1:].strip()
    if rhs in ("1", "0"):
        return _nrows(data), ["(Intercept)"]
    terms = _split_terms(rhs)
    columns: list[str] = ["(Intercept)"]
    for term in terms:
        if term == "1":
            continue
        if term in ("-1", "0"):
            columns = []
            continue
        if term not in data:
            raise KeyError(term)
        columns.append(term)
    if not columns:
        return _nrows(data), []
    return _nrows(data), columns


def _split_terms(rhs: str) -> list[str]:
    return [part.strip() for part in rhs.split("+") if part.strip()]


def _nrows(data: Mapping[str, Sequence[Any]]) -> int:
    for values in data.values():
        return len(values)
    return 0


def _formula_text(form: Any) -> str:
    if isinstance(form, Formula):
        return str(form)
    if hasattr(form, "formula"):
        return str(form.formula)
    text = str(form).strip()
    if not text.startswith("~") and "~" in text:
        return f"~{text.split('~', 1)[1].strip()}"
    return text


def _is_formula(form: Any) -> bool:
    if isinstance(form, Formula):
        return True
    text = str(form).strip()
    return text.startswith("~") or ("~" in text and "|" in text)


def _formula_length(text: str) -> int:
    if "~" not in text:
        return 1
    lhs, rhs = text.split("~", 1)
    if "|" in rhs:
        return 3
    return 3 if lhs.strip() else 2


def _get_covariate_formula(text: str) -> str:
    _, rhs = text.split("~", 1)
    if "|" in rhs:
        rhs = rhs.split("|", 1)[0]
    return f"~{rhs.strip()}"


def _pd_symm_ncol(length: int) -> int:
    return int(round((np.sqrt(8 * length + 1) - 1) / 2))


def _as_matrix(object: PdMat) -> np.ndarray:
    side = Dim(object)[0]
    if side == 0:
        raise ValueError("cannot access matrix of uninitialized object")
    if object.pd_class == "pdDiag":
        return np.diag(np.exp(2.0 * object.values))
    if object.pd_class == "pdIdent" and object.ncol is not None:
        scale = np.exp(2.0 * object.values[0])
        return scale * np.eye(object.ncol)
    if object.pd_class == "pdLogChol":
        return _matrix_from_log_chol(object.values)
    if object.pd_class == "pdSymm":
        return _matrix_from_pd_symm(object.values)
    if object.values.ndim == 2:
        return object.values @ object.values.T
    raise ValueError(f"cannot rebuild matrix for pd class {object.pd_class!r}")


def _matrix_from_log_chol(values: np.ndarray) -> np.ndarray:
    ncol = _pd_symm_ncol(int(values.size))
    chol = np.zeros((ncol, ncol), dtype=np.float64)
    chol[np.diag_indices(ncol)] = np.exp(values[:ncol])
    upper = values[ncol:]
    chol[np.triu_indices(ncol, k=1)] = upper
    return chol @ chol.T


def _matrix_from_pd_symm(values: np.ndarray) -> np.ndarray:
    ncol = _pd_symm_ncol(int(values.size))
    mat = np.zeros((ncol, ncol), dtype=np.float64)
    mat[np.triu_indices(ncol)] = values
    mat = mat + mat.T - np.diag(np.diag(mat))
    u, s, vt = np.linalg.svd(mat, full_matrices=False)
    return vt.T @ (np.exp(s)[:, None] * vt)


def _unique(names: Sequence[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for name in names:
        if name not in seen:
            seen.add(name)
            out.append(name)
    return out


def fingerprint_pd_mat(object: PdMat) -> np.ndarray:
    """Numeric summary aligned with the ``pdMat`` proof scripts."""
    dim = Dim(object)
    parts = [
        float(is_initialized(object)),
        float(dim[0]),
        float(dim[1]),
        float(len(Names(object))),
    ]
    parts.extend(float(value) for value in np.ravel(object.values))
    return np.asarray(parts, dtype=np.float64)
