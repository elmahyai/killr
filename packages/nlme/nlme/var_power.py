"""Power-of-covariate variance function (nlme varPower)."""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass, field, replace
from typing import Any

import numpy as np

from nlme.asoneformula import _all_vars
from nlme.getcovariateformula import (
    _deparse,
    _parse_bar,
    _tokenize,
    getCovariateFormula,
)
from nlme.varcomb import VarFunc
from nlme.varconstpower import _as_one_sided_formula, _get_groups_formula
from nlme.var_ident import (
    _NlmeFrame,
    _as_frame,
    _get_groups,
    _unique_preserve,
    initialize as initialize_var_ident,
    varIdent,
)
from nlme.varexp import _combine_names, _unlist_named


@dataclass(slots=True)
class VarPower(VarFunc):
    """Storage for varPower parameters and metadata."""

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
    struct_name: str | None = None
    summary_class: tuple[str, ...] | None = None

    @property
    def classes(self) -> tuple[str, ...]:
        if self.summary_class is not None:
            return self.summary_class
        return ("varPower", "varFunc")

    def __len__(self) -> int:
        if self.which_fix is None:
            return int(self.values.size)
        return int(np.sum(~self.which_fix))


@dataclass(frozen=True, slots=True)
class _CoefVector:
    values: np.ndarray
    names: tuple[str | None, ...]


def varPower(
    value: float | Mapping[str, float] | np.ndarray = (),
    form: str = "~ fitted(.)",
    fixed: float | Mapping[str, float] | np.ndarray | None = None,
) -> VarPower:
    """Construct a varPower object (variance proportional to covariate power)."""
    val_arr, val_names = _unlist_named(value)
    fix_arr, fix_names = _unlist_named(fixed)

    form_str = _as_one_sided_formula(form)
    if len(_all_vars(getCovariateFormula(form_str).text)) == 0:
        raise ValueError("'form' must have a covariate")

    which_fix: np.ndarray | None
    group_names: tuple[str, ...] | None
    if _get_groups_formula(form_str) is not None:
        if val_arr.size > 1 and val_names is None:
            raise ValueError("initial values must have group names in 'varPower'")
        if fix_arr.size > 0 and fix_names is None:
            raise ValueError("fixed parameters must have group names in 'varPower'")
        group_names = _combine_names(val_names, fix_names)
        which_fix = None
    else:
        which_fix = np.array([fixed is not None], dtype=bool)
        group_names = None

    return VarPower(
        val_arr,
        form_str,
        fix_arr if fix_arr.size else None,
        fix_names,
        val_names,
        which_fix,
        group_names,
    )


def coef(
    object: VarPower,
    unconstrained: bool = True,
    allCoef: bool = False,
    **_ignored,
) -> _CoefVector:
    """Extract coefficients from a varPower object."""
    del unconstrained
    if (
        (object.values.size == 0 and (not allCoef or object.fixed is None))
        or object.which_fix is None
    ):
        return _CoefVector(np.array([], dtype=np.float64), ())

    w_par = object.which_fix
    val = np.zeros(len(w_par), dtype=np.float64)
    if np.any(w_par):
        val[w_par] = np.asarray(object.fixed, dtype=np.float64).reshape(-1)
    if np.any(~w_par):
        val[~w_par] = np.asarray(object.values, dtype=np.float64).reshape(-1)

    if object.group_names is not None:
        names = tuple(object.group_names)
    else:
        names = ("power",) * len(val)

    if not allCoef:
        keep = ~w_par
        val = val[keep]
        names = tuple(name for name, flag in zip(names, keep, strict=True) if flag)
    return _CoefVector(val, names)


def var_weights(object: VarPower) -> np.ndarray | None:
    """Return variance weights stored on a varPower object."""
    return object.weights


def summary(object: VarPower, structName: str = "Power of variance covariate") -> VarPower:
    """Return a summary.varFunc stand-in."""
    if _get_groups_formula(object.formula) is not None:
        structName = f"{structName}, different strata"
    return replace(
        object,
        struct_name=structName,
        summary_class=("summary.varFunc",),
    )


def initialize(object: VarPower, data: _NlmeFrame | Mapping[str, Any], **_ignored) -> VarPower:
    """Initialize a varPower object using covariate values from data."""
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
        powered = _r_weights(covariate, nat_par)
        log_lik = _r_sum(_r_log(powered))
        return replace(object, weights=powered, log_lik=log_lik)
    return object


def set_coef(object: VarPower, value) -> VarPower:
    """Assign unconstrained parameters (R ``coef<-.varPower``)."""
    if len(object) <= 0:
        raise ValueError(
            "cannot change coefficients before initialization or when all parameters are fixed"
        )
    val = np.asarray(value, dtype=np.float64).ravel()
    if val.size != len(object):
        raise ValueError('cannot change the length of the "varStruct" parameter after initialization')
    object = replace(object, values=val.copy())
    if object.covariate is None:
        return object
    nat_par = coef(object, unconstrained=True, allCoef=True).values
    groups = object.groups
    if groups is not None:
        group_names = list(object.group_names or ())
        nat_par = nat_par[[group_names.index(str(group)) for group in groups]]
    covariate = np.asarray(object.covariate, dtype=np.float64)
    weights = _r_weights(covariate, nat_par)
    log_lik = _r_sum(_r_log(weights))
    return replace(object, weights=weights, log_lik=log_lik)


def _r_weights(covariate, nat_par) -> np.ndarray:
    """R's ``abs(covariate)^(-natPar)``, each power by libm ``pow`` as R's ``R_pow`` calls it.

    numpy's power differs from libm by an ulp on about one input in ten, and the
    ulp reaches the PORT path.
    """
    cov = np.abs(np.asarray(covariate, dtype=np.float64).reshape(-1))
    expo = np.broadcast_to(-np.asarray(nat_par, dtype=np.float64).reshape(-1), cov.shape)
    try:
        return np.abs(np.array(list(map(math.pow, cov.tolist(), expo.tolist())), dtype=np.float64))
    except (ValueError, OverflowError):
        return np.abs(np.power(cov, expo))


def _r_log(values) -> np.ndarray:
    """R's ``log()`` by libm; numpy's SIMD log differs by an ulp."""
    vals = np.asarray(values, dtype=np.float64).reshape(-1)
    try:
        return np.array(list(map(math.log, vals.tolist())), dtype=np.float64)
    except ValueError:
        return np.log(vals)


def _r_sum(values) -> float:
    """R's ``sum()`` on doubles: a sequential long double accumulator, as R's ``rsum``.

    ``add.accumulate`` adds in order, so the last element is R's running total.
    numpy's pairwise sum differs by an ulp here, and the ulp reaches the PORT path.
    """
    vals = np.asarray(values, dtype=np.float64).reshape(-1)
    if vals.size == 0:
        return 0.0
    return float(np.add.accumulate(vals.astype(np.longdouble))[-1])


def proof_values(object: VarPower) -> np.ndarray:
    """Numeric summary of an initialized varPower object for R comparison."""
    parts = [
        coef(object, unconstrained=True, allCoef=False).values,
        coef(object, unconstrained=True, allCoef=True).values,
        np.asarray(var_weights(object), dtype=np.float64).reshape(-1),
    ]
    return np.concatenate(parts)


def _initialize_grouped(object: VarPower, frame: _NlmeFrame, form_str: str) -> VarPower:
    strat = _get_groups(frame, form_str)
    u_strat = _unique_preserve(strat)
    if len(u_strat) > 1:
        object = replace(object, groups=np.asarray(strat, dtype=np.dtype("O")))
        fix = object.fixed
        fix_names = object.fixed_names
        if fix is not None:
            if fix_names is None:
                raise ValueError("fixed parameters must have group names")
            if any(name not in u_strat for name in fix_names):
                raise ValueError("mismatch between group names and fixed values names")
            fix_name_list = list(fix_names)
        else:
            fix_name_list = []

        u_strat_var = [level for level in u_strat if level not in fix_name_list]
        n_strat_var = len(u_strat_var)
        which_fix = np.array([name in fix_name_list for name in u_strat], dtype=bool)
        object = replace(object, which_fix=which_fix)

        if n_strat_var > 0:
            values = np.asarray(object.values, dtype=np.float64).reshape(-1)
            group_names = object.group_names
            if values.size <= 1:
                if values.size > 0:
                    values = np.repeat(values, n_strat_var)
                else:
                    values = np.zeros(n_strat_var, dtype=np.float64)
                object = replace(object, values=values, group_names=tuple(u_strat))
            else:
                if values.size != n_strat_var:
                    raise ValueError(
                        f'initial value for "varPower" should be of length {n_strat_var}'
                    )
                if group_names is None:
                    raise ValueError(
                        'nonexistent group names for initial values in "varPower"'
                    )
                st_n = list(group_names)
                if len(st_n) != len(u_strat) or sorted(st_n) != sorted(u_strat):
                    raise ValueError(
                        'nonexistent group names for initial values in "varPower"'
                    )
        else:
            if fix is not None and np.all(np.asarray(fix, dtype=np.float64) == 0):
                return initialize_var_ident(varIdent(), frame)
            object = replace(object, values=np.array([], dtype=np.float64), group_names=tuple(u_strat))
    else:
        cov_form = getCovariateFormula(form_str).text
        object = replace(
            object,
            formula=cov_form,
            which_fix=np.array([object.fixed is not None], dtype=bool),
        )
    return object


def _initialize_single_stratum(object: VarPower, frame: _NlmeFrame) -> VarPower:
    which_fix = object.which_fix
    if which_fix is None:
        return object
    if which_fix[0]:
        if object.fixed is not None and float(np.asarray(object.fixed).reshape(-1)[0]) == 0:
            return initialize_var_ident(varIdent(), frame)
        object = replace(object, values=np.array([], dtype=np.float64))
    else:
        values = np.asarray(object.values, dtype=np.float64).reshape(-1)
        if values.size == 0:
            object = replace(object, values=np.array([0.0], dtype=np.float64))
        elif values.size > 1:
            raise ValueError('initial value for "varPower" should be of length 1')
    return object


def _get_covariate(frame: _NlmeFrame, form_str: str) -> np.ndarray:
    cov_text = getCovariateFormula(form_str).text
    rhs = cov_text.lstrip("~").strip()
    tokens = _tokenize(rhs)
    tree, pos = _parse_bar(tokens, 0)
    if pos != len(tokens):
        raise ValueError("invalid formula")
    values = _eval_expr(tree, frame)
    return np.asarray(values, dtype=np.float64).reshape(-1)


def _eval_expr(node, frame: _NlmeFrame) -> np.ndarray:
    kind = node[0]
    if kind == "name":
        name = node[1]
        if name not in frame.columns:
            raise ValueError(f"column {name!r} is not in data")
        return np.asarray(frame.columns[name], dtype=np.float64).reshape(-1)
    if kind == "num":
        return np.full(frame.nrow(), float(node[1]), dtype=np.float64)
    if kind == "paren":
        return _eval_expr(node[1], frame)
    if kind == "call":
        name = node[1]
        args = node[2]
        if name == "fitted" and len(args) == 1 and args[0][0] == "name" and args[0][1] == ".":
            raise ValueError("fitted(.) covariate is not available from data alone")
        raise ValueError(f"unsupported function {name!r} in covariate formula")
    if kind == "u-":
        return -_eval_expr(node[2], frame)
    if kind in ("+", "-", "*", "/", "^", ":"):
        left = _eval_expr(node[1], frame)
        right = _eval_expr(node[2], frame)
        if kind == "+":
            return left + right
        if kind == "-":
            return left - right
        if kind == "*":
            return left * right
        if kind == "/":
            return left / right
        if kind == "^":
            return left**right
        if kind == ":":
            return left * right
    raise ValueError("invalid covariate expression")
