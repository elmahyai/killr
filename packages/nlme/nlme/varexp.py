"""Exponential variance function constructor (nlme varExp)."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field, replace
from typing import Any

import numpy as np

from nlme.asoneformula import _all_vars
from nlme.getcovariateformula import getCovariateFormula
from nlme.varcomb import VarFunc
from nlme.varconstpower import _as_one_sided_formula, _get_groups_formula


@dataclass(slots=True)
class VarExp(VarFunc):
    """Storage for varExp parameters and metadata."""

    values: np.ndarray = field(default_factory=lambda: np.array([], dtype=np.float64))
    formula: str = "~fitted(.)"
    fixed: np.ndarray | None = None
    fixed_names: tuple[str, ...] | None = None
    value_names: tuple[str, ...] | None = None
    which_fix: np.ndarray | None = None
    group_names: tuple[str, ...] | None = None
    covariate: np.ndarray | None = None
    groups: np.ndarray | None = None
    weights: np.ndarray | None = None
    log_lik: float | None = None
    need_update: bool = False

    @property
    def classes(self) -> tuple[str, ...]:
        return ("varExp", "varFunc")

    def __len__(self) -> int:
        if self.which_fix is None:
            return int(self.values.size)
        return int(np.sum(~self.which_fix))


def varExp(
    value: float | Sequence[float] | Mapping[str, float] | np.ndarray = (),
    form: str = "~ fitted(.)",
    fixed: float | Sequence[float] | Mapping[str, float] | np.ndarray | None = None,
) -> VarExp:
    """Construct a varExp object (exponential variance structure)."""
    val_arr, val_names = _unlist_named(value)
    fix_arr, fix_names = _unlist_named(fixed)

    form_str = _as_one_sided_formula(form)
    if len(_all_vars(getCovariateFormula(form_str).text)) == 0:
        raise ValueError("'form' must have a covariate")

    which_fix: np.ndarray | None
    group_names: tuple[str, ...] | None
    if _get_groups_formula(form_str) is not None:
        if val_arr.size > 1 and val_names is None:
            raise ValueError("initial values must have group names in 'varExp'")
        if fix_arr.size > 0 and fix_names is None:
            raise ValueError("fixed parameters must have group names in 'varExp'")
        group_names = _combine_names(val_names, fix_names)
        which_fix = None
    else:
        which_fix = np.array([fixed is not None], dtype=bool)
        group_names = None

    return VarExp(
        val_arr,
        form_str,
        fix_arr if fix_arr.size else None,
        fix_names,
        val_names,
        which_fix,
        group_names,
    )


def initialize(object: VarExp, data: Any, **_ignored) -> VarExp:
    """Initialize a varExp object on data (R ``Initialize.varExp``).

    The grouping and fixed-value bookkeeping is the varPower logic with the
    weights ``exp(-coef * covariate)`` in place of ``|covariate^(-coef)|``.
    """
    from nlme.var_ident import _as_frame
    from nlme.var_power import _get_covariate, _initialize_grouped, _initialize_single_stratum, coef

    frame = _as_frame(data)
    form_str = object.formula
    cov_vars = _all_vars(getCovariateFormula(form_str).text)
    if all(name in frame.columns for name in cov_vars):
        covariate = _get_covariate(frame, form_str)
        object = replace(object, need_update=False, covariate=covariate)
    else:
        object = replace(object, need_update=True)

    grp_form = _get_groups_formula(form_str)
    if grp_form is not None:
        object = _initialize_grouped(object, frame, form_str)
    else:
        object = _initialize_single_stratum(object, frame)

    covariate = object.covariate
    if covariate is not None:
        nat_par = coef(object, allCoef=True).values
        groups = object.groups
        if groups is not None:
            group_names = list(object.group_names or ())
            nat_par = nat_par[[group_names.index(str(g)) for g in groups]]
        weights = np.exp(-nat_par * np.asarray(covariate, dtype=np.float64))
        log_lik = float(np.sum(np.log(weights)))
        return replace(object, weights=weights, log_lik=log_lik)
    return object


def proof_values(object: VarExp) -> np.ndarray:
    """Numeric summary of a varExp object for R comparison."""
    parts = [np.asarray(object.values, dtype=np.float64).reshape(-1)]
    parts.append(np.array([sum(map(ord, object.formula))], dtype=np.float64))
    return np.concatenate(parts) if parts else np.array([], dtype=np.float64)


def _unlist_named(value) -> tuple[np.ndarray, tuple[str, ...] | None]:
    if value is None:
        return np.array([], dtype=np.float64), None
    if isinstance(value, Mapping):
        names = tuple(str(key) for key in value)
        arr = np.asarray([float(value[key]) for key in value], dtype=np.float64)
        return arr, names if names else None
    if isinstance(value, (int, float)):
        return np.array([float(value)], dtype=np.float64), None
    arr = np.asarray(value, dtype=np.float64).reshape(-1)
    names: tuple[str, ...] | None = None
    if hasattr(value, "dtype") and getattr(value.dtype, "names", None):
        names = tuple(str(name) for name in value.dtype.names)
    elif getattr(arr, "names", None):
        raw = arr.names
        if raw is not None:
            names = tuple(str(name) for name in raw)
    return arr, names


def _combine_names(
    value_names: tuple[str, ...] | None,
    fixed_names: tuple[str, ...] | None,
) -> tuple[str, ...] | None:
    parts: list[str] = []
    if value_names:
        parts.extend(value_names)
    if fixed_names:
        parts.extend(fixed_names)
    return tuple(parts) if parts else None
