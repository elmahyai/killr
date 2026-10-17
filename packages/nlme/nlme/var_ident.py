"""Different standard deviation per stratum (nlme varIdent)."""

from __future__ import annotations

import warnings
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field, replace
from typing import Any

import numpy as np

from nlme.getcovariateformula import _deparse, _parse_bar, _tokenize
from nlme.varcomb import VarFunc
from nlme.varconstpower import _as_one_sided_formula, _get_groups_formula
from nlme.varexp import _combine_names, _unlist_named


@dataclass(slots=True)
class VarIdent(VarFunc):
    """Storage for varIdent parameters and metadata."""

    values: np.ndarray = field(default_factory=lambda: np.array([], dtype=np.float64))
    formula: str = "~1"
    fixed: np.ndarray | None = None
    fixed_names: tuple[str, ...] | None = None
    group_names: tuple[str, ...] | None = None
    which_fix: np.ndarray | None = None
    groups: np.ndarray | None = None
    weights: np.ndarray | None = None
    log_lik: float | None = None
    need_update: bool = False
    struct_name: str | None = None
    summary_class: tuple[str, ...] | None = None

    @property
    def classes(self) -> tuple[str, ...]:
        if self.summary_class is not None:
            return self.summary_class
        return ("varIdent", "varFunc")


@dataclass(frozen=True, slots=True)
class _CoefVector:
    values: np.ndarray
    names: tuple[str | None, ...]


@dataclass(slots=True)
class _NlmeFrame:
    """Minimal data.frame stand-in for Initialize.varIdent."""

    columns: dict[str, np.ndarray | list[Any]]

    def nrow(self) -> int:
        first = next(iter(self.columns.values()))
        return len(first)


def varIdent(
    value: float | Sequence[float] | Mapping[str, float] | np.ndarray = (),
    form: str = "~1",
    fixed: float | Sequence[float] | Mapping[str, float] | np.ndarray | None = None,
) -> VarIdent:
    """Construct a varIdent object (different standard deviations per stratum)."""
    form_str = _as_one_sided_formula(form)
    val_arr, grp_names = _unlist_named(value)

    if _get_groups_formula(form_str) is None:
        if val_arr.size > 0:
            warnings.warn("ignoring initial values (no grouping factor)", stacklevel=2)
        return VarIdent(formula=form_str)

    if val_arr.size > 0:
        if val_arr.size > 1 and grp_names is None:
            raise ValueError("initial values must have group names in 'varIdent'")
        if np.any(val_arr <= 0):
            raise ValueError("initial values for 'varIdent' must be > 0")
        val_arr = np.log(val_arr)

    fix_arr = np.array([], dtype=np.float64)
    fix_names: tuple[str, ...] | None = None
    if fixed is not None:
        fix_arr, fix_names = _unlist_named(fixed)
        if fix_arr.size > 0:
            if fix_names is None:
                raise ValueError("fixed parameters must have names in 'varIdent'")
            fix_arr = np.log(fix_arr)

    group_names = grp_names
    if fix_names is not None and grp_names is not None:
        group_names = _combine_names(grp_names, fix_names)
    elif fix_names is not None:
        group_names = fix_names

    return VarIdent(
        val_arr,
        form_str,
        fix_arr if fix_arr.size else None,
        fix_names,
        group_names,
    )


def coef(
    object: VarIdent,
    unconstrained: bool = True,
    allCoef: bool = False,
    **_ignored,
) -> _CoefVector:
    """Extract coefficients from a varIdent object."""
    if _get_groups_formula(object.formula) is None or object.which_fix is None:
        return _CoefVector(np.array([], dtype=np.float64), ())
    w_par = object.which_fix
    if unconstrained and not allCoef:
        return _CoefVector(np.asarray(object.values, dtype=np.float64).reshape(-1), ())

    val = np.zeros(len(w_par), dtype=np.float64)
    if np.any(w_par):
        val[w_par] = np.asarray(object.fixed, dtype=np.float64).reshape(-1)
    if np.any(~w_par):
        val[~w_par] = np.asarray(object.values, dtype=np.float64).reshape(-1)

    if unconstrained:
        names = tuple(object.group_names[1:]) if object.group_names else (None,) * len(val)
        return _CoefVector(val, names)

    if object.group_names is None:
        raise ValueError('do not know how to get coefficients for "varIdent" object')
    natural = np.concatenate(([1.0], np.exp(val)))
    names = tuple(object.group_names)
    if not allCoef:
        keep = np.concatenate(([False], ~w_par))
        natural = natural[keep]
        names = tuple(name for name, flag in zip(names, keep, strict=True) if flag)
    return _CoefVector(natural, names)


def var_weights(object: VarIdent) -> np.ndarray | None:
    """Return variance weights stored on a varIdent object."""
    return object.weights


def need_update(object: VarIdent) -> bool:
    """varIdent structures never need a covariate update."""
    del object
    return False


def summary(object: VarIdent, struct_name: str | None = None) -> VarIdent:
    """Return a summary.varFunc stand-in."""
    if struct_name is None:
        if _get_groups_formula(object.formula) is None:
            struct_name = "Constant variance"
        else:
            struct_name = "Different standard deviations per stratum"
    return replace(
        object,
        struct_name=struct_name,
        summary_class=("summary.varFunc",),
    )


def recalc(object: VarIdent, con_lin: Any, **_ignored) -> Any:
    """Apply varIdent weights to a consolidated linear object."""
    if object.formula is None:
        return con_lin
    weights = object.weights
    if weights is None:
        raise ValueError("varIdent object has no weights")
    xy = np.asarray(con_lin.xy, dtype=np.float64)
    con_lin.xy = xy * weights
    if object.log_lik is not None:
        con_lin.log_lik = float(con_lin.log_lik) + float(object.log_lik)
    return con_lin


def initialize(object: VarIdent, data: _NlmeFrame | Mapping[str, Any], **_ignored) -> VarIdent:
    """Initialize a varIdent object using grouped data."""
    frame = _as_frame(data)
    form_str = object.formula
    grp_form = _get_groups_formula(form_str)
    if grp_form is None:
        return _initialize_var_func(object, frame)

    unconstrained = coef(object, unconstrained=True, allCoef=False).values
    if unconstrained.size > 0:
        return object

    strat = _get_groups(frame, form_str)
    u_strat = _unique_preserve(strat)
    if len(u_strat) == 1:
        return initialize(varIdent(), data)

    fix = object.fixed
    fix_names = object.fixed_names
    if fix is not None and fix_names is not None:
        fix_name_list = list(fix_names)
        if any(name not in u_strat for name in fix_name_list):
            raise ValueError("fixed parameter names in 'varIdent' must be a subset of group names")
        u_strat_var = [level for level in u_strat if level not in fix_name_list]
        u_strat = u_strat_var + fix_name_list
    else:
        u_strat_var = list(u_strat)

    n_strat_var = len(u_strat_var)
    if n_strat_var == 0:
        raise ValueError("cannot fix variances in all groups")

    values = np.asarray(object.values, dtype=np.float64).reshape(-1)
    group_names = object.group_names
    if n_strat_var > 1:
        if values.size <= 1:
            old = object
            if values.size > 0:
                values = np.repeat(values, n_strat_var - 1)
            else:
                values = np.zeros(n_strat_var - 1, dtype=np.float64)
            object = replace(old, values=values)
            group_names = tuple(u_strat)
        else:
            expected = n_strat_var - 1
            if values.size != expected:
                raise ValueError(
                    f'initial value for "varIdent" should be of length {expected}'
                )
            if group_names is not None:
                st_n = list(group_names)
                miss_strat = [level for level in u_strat if level not in st_n]
                if len(miss_strat) != 1:
                    raise ValueError(
                        'names of starting value for "varIdent" object must contain all but one of the stratum levels'
                    )
                st_n = miss_strat + st_n
                if len(st_n) != len(u_strat) or sorted(st_n) != sorted(u_strat):
                    raise ValueError("nonexistent group names for initial values in 'varIdent'")
                group_names = tuple(st_n)
            else:
                group_names = tuple(u_strat)
    else:
        object = replace(object, values=np.array([], dtype=np.float64))
        group_names = tuple(u_strat)

    which_fix = np.array(
        [name in (fix_names or ()) for name in (group_names[1:] if group_names else ())],
        dtype=bool,
    )
    object = replace(object, group_names=group_names, which_fix=which_fix)

    if np.all(which_fix):
        if fix is not None and np.all(np.asarray(fix, dtype=np.float64) == 0):
            return initialize(varIdent(), data)
        object = replace(object, values=np.array([], dtype=np.float64))

    natural = coef(object, unconstrained=False, allCoef=True).values
    strat_index = {name: index for index, name in enumerate(object.group_names or ())}
    sd = natural[[strat_index[level] for level in strat]]
    weights = 1.0 / sd
    log_lik = float(np.sum(np.log(weights)))
    return replace(
        object,
        groups=np.asarray(strat, dtype=np.dtype("O")),
        weights=weights,
        log_lik=log_lik,
        need_update=False,
    )


def proof_values(object: VarIdent) -> np.ndarray:
    """Numeric summary of an initialized varIdent object for R comparison."""
    parts = [
        coef(object, unconstrained=True, allCoef=False).values,
        coef(object, unconstrained=False, allCoef=True).values,
        np.asarray(var_weights(object), dtype=np.float64).reshape(-1),
    ]
    return np.concatenate(parts)


def _initialize_var_func(object: VarIdent, frame: _NlmeFrame) -> VarIdent:
    weights = object.weights
    if weights is None:
        weights = np.ones(frame.nrow(), dtype=np.float64)
    log_lik = object.log_lik
    if log_lik is None:
        log_lik = 0.0
    which_fix = np.array([True], dtype=bool)
    return replace(
        object,
        weights=weights,
        log_lik=log_lik,
        which_fix=which_fix,
        need_update=False,
    )


def _as_frame(data: _NlmeFrame | Mapping[str, Any]) -> _NlmeFrame:
    if isinstance(data, _NlmeFrame):
        return data
    columns = {str(key): np.asarray(val) for key, val in data.items()}
    return _NlmeFrame(columns)


def _group_var_name(form_str: str) -> str:
    text = form_str.strip()
    if text.startswith("~"):
        text = text[1:].strip()
    tokens = _tokenize(text)
    tree, pos = _parse_bar(tokens, 0)
    if pos != len(tokens):
        raise ValueError("invalid formula")
    if tree[0] != "|":
        raise ValueError("formula has no grouping factor")
    group_side = _deparse(tree[2]).strip()
    vars_in_group = _all_vars_simple(group_side)
    if len(vars_in_group) != 1:
        raise ValueError("invalid formula for groups")
    return vars_in_group[0]


def _all_vars_simple(text: str) -> list[str]:
    tokens = _tokenize(text)
    names: list[str] = []
    for token in tokens:
        if token[0] == "name":
            names.append(token[1])
    return names


def _get_groups(frame: _NlmeFrame, form_str: str) -> list[str]:
    var_name = _group_var_name(form_str)
    if var_name not in frame.columns:
        raise ValueError(f"column {var_name!r} is not in data")
    column = frame.columns[var_name]
    return [str(item) for item in np.asarray(column).reshape(-1)]


def _unique_preserve(values: list[str]) -> list[str]:
    seen: list[str] = []
    for value in values:
        if value not in seen:
            seen.append(value)
    return seen
