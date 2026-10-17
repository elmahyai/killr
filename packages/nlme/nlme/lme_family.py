"""Linear and nonlinear mixed-effects fits (nlme ``lme`` and ``nlme.formula``).

``lme.formula`` maximises the REML or ML criterion through the ``nlmemixed``
kernels (``mixed_em``, ``mixed_loglik``, ``mixed_decomp``, ``mixed_estimate``,
``inner_perc_table``). ``nlme.formula`` alternates that step with ``fit_nlme``.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

import numpy as np
from scipy.stats import chi2, f as f_dist

import nlme_mixedem
import nlme_pdsymm
import nlmemixed
from nlminb_port import nlminb_port

from nlme.fdhess import fdHess
from nlme.getcovariate import getCovariate
from nlme.asoneformula import _all_vars
from nlme.getcovariateformula import getCovariateFormula
from nlme.linpack_qr import r_mean
from nlme.lmecontrol import lmeControl
from nlme.lmlistformula import LmList, coef as lmlist_coef
from nlme.matrix_assign import matrix_assign
from nlme.nlmecontrol import nlmeControl
from nlme.pdmat import PdMat
from nlme.pdmatrix import pdMatrix
from nlme.pdnatural import pdNatural
from nlme.var_ident import (
    _as_frame,
    coef as _var_ident_coef,
    initialize as _var_ident_initialize,
)
from nlme.var_power import (
    _get_covariate as _var_covariate,
    coef as _var_power_coef,
    initialize as _var_power_initialize,
)
from nlme.varconstpower import _get_groups_formula
from nlme.varexp import initialize as _varexp_initialize
from nlme.varfunc import varFunc

# Variance functions with parameters that lme fits as a varStruct (R lmeStruct).
_GENERAL_VARIANCE_CLASSES = ("varPower", "varExp", "varIdent", "varConstPower")

_PD_CODE = {"pdSymm": 0, "pdDiag": 1, "pdIdent": 2, "pdCompSymm": 3, "pdLogChol": 4}
_MAD_CONSTANT = 1.4826


def _block_factor(block: PdMat, pdims: list[int], pd_code: list[int], parameters: Any) -> list[float]:
    """Flat factor of one random block, as the ``mixed_loglik`` Delta input.

    pdSymm uses R's ``matrixLog_pd`` (``nlme_pdsymm``, EISPACK ``rs``). The other
    classes keep the ``nlmemixed`` factor from parameters.
    """
    values = np.asarray(parameters, dtype=np.float64).ravel()
    if block.pd_class == "pdSymm":
        return list(nlme_pdsymm.matrix_log_pd(values.tolist()))
    return list(nlmemixed.factor_from_parameters(pdims, pd_code, values.tolist()))


@dataclass(slots=True)
class LmeFixDF:
    """Denominator degrees of freedom for fixed effects and terms."""

    x: np.ndarray
    x_names: tuple[str, ...]
    terms: np.ndarray
    term_names: tuple[str, ...]
    assign: dict[str, np.ndarray]
    var_fix_factor: np.ndarray | None = None


@dataclass(slots=True)
class LmeResult:
    """Fitted ``lme`` object. Numeric fields follow the R component names."""

    fixed: np.ndarray
    fixed_names: tuple[str, ...]
    random: dict[str, np.ndarray]
    random_rows: dict[str, tuple[str, ...]]
    random_columns: dict[str, tuple[str, ...]]
    sigma: float
    loglik: float
    var_fix: np.ndarray
    fitted: np.ndarray
    residuals: np.ndarray
    method: str
    fix_df: LmeFixDF
    dims: dict[str, Any]
    groups: dict[str, list[Any]]
    ap_var: np.ndarray | str
    ap_var_pars: np.ndarray | None
    num_iter: int | None
    formula: str
    coefficients_random_names: tuple[str, ...]
    model_parameters: np.ndarray
    pd_class: str
    classes: tuple[str, ...] = ("lme",)
    optimizer: dict[str, Any] | None = None
    # Variance-function parameters and final weights (R coef(modelStruct$varStruct)); None unless
    # weights is a varPower, varExp, varIdent, or varConstPower object.
    variance: dict[str, Any] | None = None

    @property
    def coefficients(self) -> dict[str, Any]:
        return {"fixed": self.fixed, "random": self.random}


@dataclass(slots=True)
class AnovaLme:
    """``anova.lme`` table for one Wald test or a likelihood-ratio comparison."""

    columns: dict[str, np.ndarray]
    row_names: tuple[str, ...]
    rt: int
    label: str | None = None
    classes: tuple[str, ...] = ("anova.lme", "data.frame")


@dataclass(slots=True)
class NlmeResult:
    """Fitted ``nlme`` object reduced to the values the proof compares."""

    fixed: np.ndarray
    fixed_names: tuple[str, ...]
    random: dict[str, np.ndarray]
    sigma: float
    loglik: float
    method: str
    classes: tuple[str, ...] = ("nlme",)


def lme(
    fixed: Any,
    data: Any = None,
    random: Any = None,
    correlation: Any = None,
    weights: Any = None,
    subset: Any = None,
    method: str = "REML",
    na_action: Any = None,
    control: Any = None,
    contrasts: Any = None,
    keep_data: bool = True,
) -> LmeResult:
    """Fit a linear mixed-effects model, dispatching on the first argument."""
    classes = tuple(getattr(fixed, "classes", ()))
    if isinstance(fixed, LmList) or "lmList" in classes:
        return lme_lmList(
            fixed, data, random, correlation, weights, subset, method, na_action, control, contrasts, keep_data
        )
    if "groupedData" in classes and not _looks_like_formula(fixed):
        formula = _grouped_fixed_formula(fixed)
        return lme_formula(
            formula, fixed, random, correlation, weights, subset, method, na_action, control, contrasts, keep_data
        )
    if data is None:
        raise ValueError("'data' is required when 'fixed' is a formula")
    return lme_formula(
        fixed, data, random, correlation, weights, subset, method, na_action, control, contrasts, keep_data
    )


def lme_formula(
    fixed: Any,
    data: Any,
    random: Any = None,
    correlation: Any = None,
    weights: Any = None,
    subset: Any = None,
    method: str = "REML",
    na_action: Any = None,
    control: Any = None,
    contrasts: Any = None,
    keep_data: bool = True,
) -> LmeResult:
    """Fit ``lme`` from a fixed-effects formula.

    ``weights`` is a ``varFixed`` object or its one-sided formula, or one of
    the variance functions with parameters (``varPower``, ``varExp``,
    ``varIdent``, ``varConstPower``) with an explicit covariate.
    """
    del na_action, contrasts, keep_data
    if correlation is not None:
        raise NotImplementedError("lme correlation is waiting on corStruct")
    weight_form, weight_var = _weight_spec(weights)
    if subset is not None:
        raise NotImplementedError("subset is not implemented for lme")
    control_vals = _merge_control(lmeControl(), control)
    method = _match_method(method, ("REML", "ML"))
    reml = method == "REML"
    formula = _formula_text(fixed)
    response, rhs = _split_fixed(formula)
    columns = _columns(data)
    group_name, group_values, group_levels = _grouping(data, random, columns)
    covariate = _covariate_text(random, rhs)
    pd_class = _pd_class_of(random)
    n = len(columns[response])
    y = np.asarray(columns[response], dtype=np.float64)
    x_matrix, x_names = _design(rhs, columns, n)
    z_matrix, z_names = _design(covariate, columns, n)
    codes, levels = _factor_codes(group_values, group_levels)
    order = np.argsort(codes, kind="stable")
    inverse = np.empty(n, dtype=np.int64)
    inverse[order] = np.arange(n)
    z_sorted = z_matrix[order]
    x_sorted = x_matrix[order]
    y_sorted = y[order]
    codes_sorted = codes[order]
    level_names = _level_names(codes_sorted, levels)
    ncols = np.array([z_sorted.shape[1], x_sorted.shape[1], 1], dtype=np.int32)
    dims = _medims([codes_sorted], ncols)
    xy = np.column_stack([z_sorted, x_sorted, y_sorted[:, None]])
    block = PdMat(
        values=np.array([], dtype=np.float64),
        formula=f"~{covariate}",
        names=tuple(z_names),
        pd_class=pd_class,
    )
    if _random_is_initialized(random):
        block = _copy_initialized(random, block)
    con = _ConLin(xy=xy, dims=dims, log_lik=0.0, sigma=float(control_vals["sigma"]))
    # R initializes the reStruct on the unweighted condensed model (Initialize.lmeStruct).
    block, parameters = _initialize_random(block, con, int(control_vals["niterEM"]), reml)
    old_xy = con.xy.copy()
    old_dims = _copy_dims(con.dims)
    model_parameters: np.ndarray | None = None
    variance: dict[str, Any] | None = None
    estimates: dict[str, Any] | None = None
    num_iter: int | None = None
    var_state: _VarStruct | None = None
    var_pars: np.ndarray | None = None
    var_con: _ConLin | None = None
    if weight_form is None and weight_var is None:
        offset = 0.0
        _decompose(con)
        parameters, optimizer = _optimize_variance_fit(parameters, con, block, control_vals, reml)
        fit_con = con
    elif weight_form is not None:
        # varFixed: recalc() scales every column of the condensed model by the weights and
        # adds sum(log(w)) to logLik. A varStruct makes lmeSt longer than one, so R does not
        # decompose the model, and each objective call starts from the weighted raw model.
        weight_sorted = _fixed_weights(columns, weight_form, order)
        offset = _weight_log_sum(weight_sorted)
        fit_con = _ConLin(
            xy=xy * weight_sorted[:, None],
            dims=_copy_dims(con.dims),
            log_lik=0.0,
            sigma=float(control_vals["sigma"]),
        )
        parameters, optimizer = _optimize_variance_weighted(parameters, fit_con, block, control_vals, reml, offset)
    else:
        # General varStruct: the nlminb vector is the reStruct parameters followed by the
        # variance-function parameters (coef(lmeSt)). Each objective call applies the
        # weights of its variance parameters to the raw condensed model (recalc).
        state = _var_struct_state(weight_var, _sorted_frame(columns, order))
        raw_con = _ConLin(xy=xy, dims=_copy_dims(con.dims), log_lik=0.0, sigma=float(control_vals["sigma"]))
        if state.needs_update:
            # R Initialize.lmeStruct: MEestimate on the unit weights, then update the covariate.
            initial = _estimate(raw_con, block, parameters, reml)
            state.covariate = _fitted_covariate(raw_con.xy, raw_con.dims, initial, z_names)
        var_fit = _fit_variance_struct(raw_con, block, parameters, state, control_vals, reml, z_names)
        n_re = int(parameters.size)
        full = var_fit.par
        model_parameters = full
        var_weights = var_fit.weights
        offset = var_fit.offset
        fit_con = var_fit.fit_con
        estimates = var_fit.estimates
        optimizer = var_fit.optimizer
        num_iter = var_fit.num_iter if state.needs_update else None
        parameters = full[:n_re].copy()
        variance = {
            "classes": tuple(weight_var.classes),
            "coef": full[n_re:].copy(),
            "weights": var_weights,
        }
        var_state = state
        var_pars = full[n_re:].copy()
        var_con = raw_con
    if estimates is None:
        estimates = _estimate(fit_con, block, parameters, reml, offset)
    # fitted.lmeStruct reads attr(lmeSt, "conLin"), which is never weighted, so the fit is unweighted.
    fitted_sorted = _fitted_sorted(old_xy, old_dims, estimates, z_names)
    fitted = fitted_sorted[inverse]
    residuals = y[:, None] - fitted
    fix_df = _fix_df(x_sorted, x_names, [codes_sorted], dims, estimates)
    # apVar of a varStruct model uses the raw condensed model and the covariate after the last
    # update (R lmeApVar: conLin is not decomposed when a varStruct is present).
    ap_var, ap_pars = _ap_var(
        fit_con if var_state is None else var_con,
        block,
        parameters,
        estimates,
        control_vals,
        reml,
        old_xy,
        old_dims,
        offset,
        state=var_state,
        var_pars=var_pars,
    )
    saved_dims = {
        "N": int(dims["N"]),
        "Q": int(dims["Q"]),
        "qvec": np.array(dims["qvec"], dtype=np.int32),
        "ngrps": np.array(dims["ngrps"], dtype=np.int32),
        "ncol": np.array(dims["ncol"], dtype=np.int32),
    }
    return LmeResult(
        fixed=estimates["beta"],
        fixed_names=tuple(x_names),
        random={group_name: estimates["b"]},
        random_rows={group_name: tuple(level_names)},
        random_columns={group_name: tuple(z_names)},
        sigma=estimates["sigma"],
        loglik=estimates["loglik"],
        var_fix=estimates["var_fix"],
        fitted=fitted,
        residuals=residuals,
        method=method,
        fix_df=fix_df,
        dims=saved_dims,
        groups={group_name: [levels[int(code)] for code in codes]},
        ap_var=ap_var,
        ap_var_pars=ap_pars,
        num_iter=num_iter,
        formula=formula,
        coefficients_random_names=(group_name,),
        model_parameters=parameters if model_parameters is None else model_parameters,
        pd_class=pd_class,
        optimizer=optimizer,
        variance=variance,
    )


def lme_lmList(
    fixed: LmList,
    data: Any = None,
    random: Any = None,
    correlation: Any = None,
    weights: Any = None,
    subset: Any = None,
    method: str = "REML",
    na_action: Any = None,
    control: Any = None,
    contrasts: Any = None,
    keep_data: bool = True,
) -> LmeResult:
    """Fit ``lme`` starting from per-group ``lmList`` coefficients."""
    if data is None:
        data = getattr(fixed, "data", None)
    if data is None:
        raise ValueError("'lme.lmList' needs the data used to fit the lmList")
    formula = _infer_lmlist_formula(fixed, data)
    group = fixed.groups_form.split("~", 1)[1].strip()
    if random is None:
        _, rhs = _split_fixed(formula)
        random = f"~{rhs} | {group}"
    table = lmlist_coef(fixed)
    if table is None:
        raise ValueError("lmList has no coefficients")
    kept = np.isfinite(table.values).all(axis=1)
    values = table.values[kept]
    response, rhs = _split_fixed(formula)
    columns = _columns(data)
    resid = _lmlist_residuals(formula, columns, fixed, table)
    mad_res = _mad(resid)
    init = np.zeros((values.shape[1], values.shape[1]), dtype=np.float64)
    for index, name in enumerate(table.colnames):
        init[index, index] = (_mad(values[:, index]) / mad_res) ** 2
    z_names = list(table.colnames)
    block = matrix_assign(
        PdMat(values=np.zeros(1), formula=f"~{rhs}", names=tuple(z_names), pd_class="pdLogChol"),
        init,
    )
    return lme_formula(
        formula,
        data,
        _InitializedRandom(block, group),
        correlation,
        weights,
        subset,
        method,
        na_action,
        control,
        contrasts,
        keep_data,
    )


def anova_lme(
    object: LmeResult,
    *others: Any,
    test: bool = True,
    type: str = "sequential",
    adjustSigma: bool = True,
    Terms: Any = None,
    L: Any = None,
    verbose: bool = False,
) -> AnovaLme:
    """Wald F tests for one ``lme`` fit, or a likelihood-ratio table for several."""
    del verbose
    if others:
        return _anova_several(object, others, test)
    if not isinstance(object, LmeResult):
        raise TypeError("object must inherit from class \"lme\"")
    if Terms is not None or L is not None:
        raise NotImplementedError("anova.lme Terms and L contrasts are not in this proof")
    kind = _match_method(type, ("sequential", "marginal"))
    factor = object.fix_df.var_fix_factor
    if factor is None:
        raise ValueError("fixed-effect factor is missing")
    v_fix = np.array(factor, dtype=np.float64, copy=True)
    if adjustSigma and object.method == "ML":
        n = int(object.dims["N"])
        v_fix *= math.sqrt(n / (n - v_fix.shape[1]))
    transformed = np.linalg.solve(v_fix.T, object.fixed)
    rows: dict[str, list[float]] = {"numDF": [], "denDF": [], "F-value": [], "p-value": []}
    names = []
    for name in object.fix_df.term_names:
        columns = object.fix_df.assign[name]
        n_df = int(columns.size)
        d_df = float(object.fix_df.terms[object.fix_df.term_names.index(name)])
        if kind == "sequential":
            piece = transformed[columns]
        else:
            design = v_fix[:, columns]
            qty = np.linalg.qr(design, mode="reduced").Q.T @ transformed
            piece = qty[:n_df]
        f_value = float(np.sum(piece**2) / n_df)
        p_value = float(f_dist.sf(f_value, n_df, d_df))
        rows["numDF"].append(n_df)
        rows["denDF"].append(d_df)
        rows["F-value"].append(f_value)
        rows["p-value"].append(p_value)
        names.append(name)
    columns_out = {key: np.asarray(value, dtype=np.float64) for key, value in rows.items()}
    return AnovaLme(columns=columns_out, row_names=tuple(names), rt=1)


def nlme_formula(
    model: str,
    data: Any,
    fixed: Any,
    random: Any = None,
    groups: Any = None,
    start: Any = None,
    correlation: Any = None,
    weights: Any = None,
    subset: Any = None,
    method: str = "ML",
    na_action: Any = None,
    naPattern: Any = None,
    control: Any = None,
    verbose: bool = False,
) -> NlmeResult:
    """Fit a nonlinear mixed-effects model with ``fit_nlme`` and ``scipy.optimize``."""
    del na_action, naPattern, verbose
    if correlation is not None:
        raise NotImplementedError("nlme correlation is waiting on corStruct")
    if weights is not None:
        raise NotImplementedError("nlme weights are waiting on varFunc")
    if subset is not None:
        raise NotImplementedError("subset is not implemented for nlme")
    control_vals = _merge_control(nlmeControl(), control)
    method = _match_method(method, ("ML", "REML"))
    reml = method == "REML"
    response, expression = _split_fixed(_formula_text(model))
    columns = _columns(data)
    y = np.asarray(columns[response], dtype=np.float64)
    fixed_map = _nlme_fixed_map(fixed)
    if random is None:
        random = fixed
    random_map = _nlme_random_map(random)
    group_name, group_values, group_levels = _grouping(data, groups if groups is not None else random, columns)
    if isinstance(groups, str) and "~" in groups and "|" not in str(random):
        group_name, group_values, group_levels = _grouping(data, groups, columns)
    codes, levels = _factor_codes(group_values, group_levels)
    order = np.argsort(codes, kind="stable")
    inverse = np.empty(len(y), dtype=np.int64)
    inverse[order] = np.arange(len(y))
    codes_sorted = codes[order]
    level_names = _level_names(codes_sorted, levels)
    n_group = len(level_names)
    fixed_names = list(fixed_map)
    random_names = list(random_map)
    if len(random_names) != 1 or random_map[random_names[0]] != ("(Intercept)",):
        raise NotImplementedError("nlme.formula in this translation fits one random intercept")
    start_fixed = _start_fixed(start, fixed_names)
    theta = np.concatenate([np.zeros(n_group, dtype=np.float64), start_fixed])
    ages = np.asarray(columns[_expression_input(expression)], dtype=np.float64)[order]
    y_sorted = y[order]
    group_index = _group_index(codes_sorted)
    evaluator = _self_start(expression)

    def model_callback(pars: list[float]) -> list[float]:
        vector = np.asarray(pars, dtype=np.float64)
        return _nlme_working(evaluator, ages, y_sorted, group_index, vector, fixed_names, random_names[0]).tolist()

    z_width = 1
    x_width = len(fixed_names)
    p_len = z_width + x_width
    n = len(y_sorted)
    ncols = np.array([z_width, x_width, 1], dtype=np.int32)
    dims = _medims([codes_sorted], ncols)
    first = _nlme_working(evaluator, ages, y_sorted, group_index, theta, fixed_names, random_names[0])
    zx = first[: n * p_len].reshape(n, p_len, order="F")
    residual = first[n * p_len :]
    working = residual + zx[:, z_width:] @ theta[n_group:]
    for slot, group in enumerate(group_index):
        working[slot] += zx[slot, 0] * theta[group]
    xy = np.column_stack([zx, working])
    block = PdMat(
        values=np.array([], dtype=np.float64),
        formula=f"~1",
        names=("(Intercept)",),
        pd_class="pdLogChol",
    )
    con = _ConLin(xy=xy, dims=dims, log_lik=0.0, sigma=float(control_vals["sigma"]))
    block, parameters = _initialize_random(block, con, int(control_vals["niterEM"]), reml)
    settings = np.array(
        [float(control_vals["pnlsMaxIter"]), float(control_vals["minScale"]), float(control_vals["pnlsTol"]), 0.0, 0.0, 0.0],
        dtype=np.float64,
    )
    max_iter = int(control_vals["maxIter"])
    tolerance = float(control_vals["tolerance"])
    for _iteration in range(max_iter):
        old_fixed = theta[n_group:].copy()
        old_random = theta[:n_group].copy()
        parameters = _optimize_variance(parameters, con, block, _lme_control_from_nlme(control_vals), reml)
        estimates = _estimate(con, block, parameters, reml)
        pdims = _flatten_dims(con.dims)
        pd_code = [_PD_CODE[block.pd_class]]
        factor = nlmemixed.factor_from_parameters(pdims, pd_code, parameters.tolist())
        additional = np.zeros(n * (p_len + 1), dtype=np.float64)
        groups = np.repeat(np.arange(n_group, dtype=np.int32), np.diff(np.concatenate([[0], np.flatnonzero(np.diff(group_index)) + 1, [n]])))
        theta_out, factor_out, _groups, settings, additional = nlmemixed.fit_nlme(
            theta.tolist(),
            factor,
            groups.astype(np.int32).tolist(),
            pdims,
            pd_code,
            [],
            [],
            [],
            list(settings),
            additional.tolist(),
            0,
            0,
            float(control_vals["sigma"]),
            model_callback,
        )
        theta = np.asarray(theta_out, dtype=np.float64)
        factor_mat = np.asarray(factor_out, dtype=np.float64).reshape(1, 1, order="F")
        precision = factor_mat.T @ factor_mat
        block = matrix_assign(block, precision)
        parameters = np.asarray(block.values, dtype=np.float64).copy()
        first = np.asarray(additional, dtype=np.float64)
        zx = first[: n * p_len].reshape(n, p_len, order="F")
        residual = first[n * p_len : n * p_len + n]
        working = residual + zx[:, z_width:] @ theta[n_group:]
        for slot, group in enumerate(group_index):
            working[slot] += zx[slot, 0] * theta[group]
        con.xy = np.column_stack([zx, working])
        con.dims = _copy_dims(dims)
        con.log_lik = 0.0
        change = np.concatenate([theta[n_group:] - old_fixed, parameters])
        base = np.concatenate([theta[n_group:], parameters])
        scale = np.where(np.abs(base) < tolerance, 1.0, np.abs(base))
        criterion = float(np.max(np.abs(np.concatenate([theta[:n_group] - old_random, theta[n_group:] - old_fixed])) / np.maximum(np.abs(theta), tolerance)))
        del change, scale
        fixed_change = float(np.max(np.abs(theta[n_group:] - old_fixed) / np.maximum(np.abs(theta[n_group:]), tolerance)))
        if criterion <= tolerance or fixed_change <= tolerance:
            break
    estimates = _estimate(con, block, parameters, reml)
    return NlmeResult(
        fixed=theta[n_group:],
        fixed_names=tuple(fixed_names),
        random={group_name: theta[:n_group].reshape(-1, 1)},
        sigma=estimates["sigma"],
        loglik=estimates["loglik"],
        method=method,
    )


def numeric_lme(fit: LmeResult) -> np.ndarray:
    """Column-major fingerprint of an ``lme`` fit for the proof scripts."""
    parts = [
        fit.fixed,
        np.array([fit.sigma, fit.loglik], dtype=np.float64),
        fit.var_fix.reshape(-1, order="F"),
    ]
    for name in fit.coefficients_random_names:
        parts.append(fit.random[name].reshape(-1, order="F"))
    parts.append(fit.fitted.reshape(-1, order="F"))
    parts.append(fit.residuals.reshape(-1, order="F"))
    if isinstance(fit.ap_var, np.ndarray):
        parts.append(fit.ap_var.reshape(-1, order="F"))
    return np.concatenate(parts)


def numeric_anova(table: AnovaLme) -> np.ndarray:
    """``numDF``, ``denDF``, ``F-value``, and ``p-value`` stacked by column."""
    return np.concatenate(
        [table.columns["numDF"], table.columns["denDF"], table.columns["F-value"], table.columns["p-value"]]
    )


def numeric_nlme(fit: NlmeResult) -> np.ndarray:
    """Fixed effects, sigma, log-likelihood, and random intercepts."""
    random = next(iter(fit.random.values())).reshape(-1)
    return np.concatenate([fit.fixed, np.array([fit.sigma, fit.loglik]), random])


@dataclass(slots=True)
class _ConLin:
    xy: np.ndarray
    dims: dict[str, Any]
    log_lik: float
    sigma: float


@dataclass(slots=True)
class _InitializedRandom:
    block: PdMat
    group: str


def _initialize_random(block: PdMat, con: _ConLin, n_iter: int, reml: bool) -> tuple[PdMat, np.ndarray]:
    q = len(block.names)
    qsum = int(con.dims["qvec"][0])
    z_part = con.xy[:, :qsum]
    n_groups = float(con.dims["ngrps"][0])
    # R's colSums accumulates in long double; match it row by row.
    squares = z_part**2
    column_sums = np.zeros(squares.shape[1], dtype=np.longdouble)
    for row in squares:
        column_sums += row
    variances = (0.375**2) * column_sums.astype(np.float64) / n_groups
    pdims = _flatten_dims(con.dims)
    pd_code = [_PD_CODE[block.pd_class]]
    if block.values.size == 0 and block.pd_class == "pdSymm":
        # R: matrix(object) <- diag(variances), then pdFactor(object) on the pdSymm parameters.
        start = matrix_assign(block, np.diag(variances))
        flat = np.asarray(_block_factor(start, pdims, pd_code, start.values), dtype=np.float64)
    else:
        if block.values.size == 0:
            factor = np.diag(np.sqrt(variances))
        else:
            covariance = _covariance_from_block(block, con)
            precision = np.linalg.inv(covariance)
            factor = np.linalg.cholesky(precision).T
        flat = np.asfortranarray(factor).reshape(-1, order="F")
    updated, _lik, _ra, _lrss = nlme_mixedem.mixed_em(
        np.asfortranarray(con.xy).reshape(-1, order="F").tolist(),
        pdims,
        flat.tolist(),
        n_iter,
        pd_code,
        int(reml),
        con.sigma,
    )
    if block.pd_class == "pdSymm":
        # R: matrix(object) <- crossprod(matrix(zz[block], ncol = q)), then the pdSymm
        # parameters from chol() and svd() (nlme_mixedem.pdsymm_from_block, bit-exact).
        q = len(block.names)
        dm_off = int(pdims[5 + 2 * (int(pdims[3]) + 2)])
        parameters = np.asarray(
            nlme_mixedem.pdsymm_from_block(list(updated[dm_off : dm_off + q * q]), q),
            dtype=np.float64,
        )
    else:
        parameters = np.asarray(
            nlmemixed.parameters_from_factor(pdims, pd_code, list(updated)),
            dtype=np.float64,
        )
    block = PdMat(values=parameters.copy(), formula=block.formula, names=block.names, pd_class=block.pd_class)
    return block, parameters


def _dogleg(gradient: np.ndarray, hessian: np.ndarray, radius: float) -> np.ndarray:
    try:
        newton = -np.linalg.solve(hessian, gradient)
    except np.linalg.LinAlgError:
        newton = -gradient
    if float(np.linalg.norm(newton)) <= radius:
        return newton
    curvature = float(gradient @ hessian @ gradient)
    if curvature <= 0.0:
        direction = -gradient
        return radius * direction / np.linalg.norm(direction)
    cauchy = -(float(gradient @ gradient) / curvature) * gradient
    if float(np.linalg.norm(cauchy)) >= radius:
        direction = -gradient
        return radius * direction / np.linalg.norm(direction)
    diff = newton - cauchy
    aa = float(diff @ diff)
    bb = 2.0 * float(cauchy @ diff)
    cc = float(cauchy @ cauchy) - radius * radius
    disc = max(bb * bb - 4.0 * aa * cc, 0.0)
    tau = (-bb + math.sqrt(disc)) / (2.0 * aa)
    return cauchy + tau * diff


def _optimize_variance_fit(
    start: np.ndarray, con: _ConLin, block: PdMat, control: dict[str, Any], reml: bool
) -> tuple[np.ndarray, dict[str, Any]]:
    """Maximise ``logLik`` with R's ``lme`` call to ``nlminb`` (no gradient).

    R calls ``nlminb(par, function(p) -logLik(lmeSt, p), control = list(iter.max =
    msMaxIter, eval.max = msMaxEval, trace = msVerbose))``. The objective is the
    Koshal intercept computed inside ``mixed_loglik`` (``gradHess = 1``), and
    PORT (``nlminb_port``) runs unchanged.
    """
    pdims = _flatten_dims(con.dims)
    pd_code = [_PD_CODE[block.pd_class]]
    # R's logLik.lmeStructInt settings for a single reStruct: REML, asDelta = 0
    # (Delta built from the parameters), gradHess = 1 (Koshal intercept).
    settings = [int(reml), 0, 1, *pd_code]
    xy = np.asfortranarray(con.xy).reshape(-1, order="F").tolist()
    sigma = float(con.sigma)

    def objective(point) -> float:
        vals, _lrss = nlme_mixedem.mixed_loglik(
            xy, pdims, np.asarray(point, dtype=np.float64).tolist(), settings, sigma
        )
        return -float(np.asarray(vals, dtype=np.float64)[0])

    nlminb_control = {
        "iter.max": int(control.get("msMaxIter", 50)),
        "eval.max": int(control.get("msMaxEval", 200)),
    }
    fit = nlminb_port(objective, [float(v) for v in np.asarray(start, dtype=np.float64)], control=nlminb_control)
    par = np.asarray(fit["par"], dtype=np.float64)
    info = {
        "par": par,
        "objective": float(fit["objective"]),
        "convergence": int(fit["convergence"]),
        "iterations": int(fit["iterations"]),
        "evaluations": {"function": int(fit["evaluations"]["function"]), "gradient": int(fit["evaluations"]["gradient"])},
        "message": str(fit["message"]),
    }
    return par, info


def _optimize_variance(start: np.ndarray, con: _ConLin, block: PdMat, control: dict[str, Any], reml: bool) -> np.ndarray:
    """Variance parameters at the ``nlminb`` solution (see ``_optimize_variance_fit``)."""
    return _optimize_variance_fit(start, con, block, control, reml)[0]


def _optimize_variance_weighted(
    start: np.ndarray,
    con: _ConLin,
    block: PdMat,
    control: dict[str, Any],
    reml: bool,
    offset: float,
) -> tuple[np.ndarray, dict[str, Any]]:
    """Maximise the weighted ``logLik`` with R's ``nlminb`` call (``logLik.lmeStruct``).

    ``con.xy`` is already multiplied by the weights and ``offset`` is ``sum(log(w))``.
    Each call uses the factor built from the parameters with ``asDelta = 1``, as
    ``logLik.reStruct`` does, and adds ``offset`` to the kernel value.
    """
    pdims = _flatten_dims(con.dims)
    pd_code = [_PD_CODE[block.pd_class]]
    settings = [int(reml), 1, 0, *pd_code]
    xy = np.asfortranarray(con.xy).reshape(-1, order="F").tolist()
    sigma = float(con.sigma)

    def objective(point) -> float:
        factor = _block_factor(block, pdims, pd_code, np.asarray(point, dtype=np.float64))
        vals, _lrss = nlmemixed.mixed_loglik(xy, pdims, list(factor), settings, sigma)
        return -(float(offset) + float(np.asarray(vals, dtype=np.float64)[0]))

    nlminb_control = {
        "iter.max": int(control.get("msMaxIter", 50)),
        "eval.max": int(control.get("msMaxEval", 200)),
    }
    fit = nlminb_port(objective, [float(v) for v in np.asarray(start, dtype=np.float64)], control=nlminb_control)
    par = np.asarray(fit["par"], dtype=np.float64)
    info = {
        "par": par,
        "objective": float(fit["objective"]),
        "convergence": int(fit["convergence"]),
        "iterations": int(fit["iterations"]),
        "evaluations": {"function": int(fit["evaluations"]["function"]), "gradient": int(fit["evaluations"]["gradient"])},
        "message": str(fit["message"]),
    }
    return par, info


def _weight_spec(weights: Any) -> tuple[str | None, Any]:
    """Split a ``weights`` argument into a ``varFixed`` formula or a general ``varFunc`` object.

    Returns ``(None, None)`` for no weights, ``(formula, None)`` for ``varFixed``
    (a formula or string is ``varFixed``), and ``(None, object)`` for a
    variance function with parameters. Other classes raise.
    """
    if weights is None:
        return None, None
    var = varFunc(weights)
    classes = tuple(getattr(var, "classes", ()))
    if "varFixed" in classes:
        return str(var.formula), None
    if any(name in classes for name in _GENERAL_VARIANCE_CLASSES):
        return None, var
    label = classes[0] if classes else type(var).__name__
    raise NotImplementedError(f"lme weights of class {label} are not translated")


@dataclass(slots=True)
class _VarStruct:
    """One variance-function structure in the sorted row order (R varStruct inside lmeStruct).

    ``covariate`` is the variance covariate. ``index`` gives each row's position in the
    natural parameter vector (``None`` for varIdent without strata). ``start`` holds the
    unconstrained starting parameters. ``rows`` is the number of observations.
    """

    kind: str
    start: np.ndarray
    rows: int
    covariate: np.ndarray | None = None
    index: np.ndarray | None = None
    # True when the covariate is fitted(.) and is replaced after each lme pass (R needUpdate).
    needs_update: bool = False
    # Fixed natural value of a single-stratum varPower/varExp (R whichFix); no free parameters.
    fixed: float | None = None

    @property
    def size(self) -> int:
        return int(self.start.size)


def _is_fitted_covariate(form: str) -> bool:
    """True for the default covariate ``~fitted(.)`` (R ``varPower()``, ``varExp()``, ``varConstPower()``)."""
    return getCovariateFormula(form).text.replace(" ", "") == "~fitted(.)"


def _fitted_covariate(xy: np.ndarray, dims: dict[str, Any], estimates: dict[str, Any], z_names: list[str]) -> np.ndarray:
    """Level-Q fitted values in the sorted row order (R ``fitted(.)`` inside ``update.varFunc``)."""
    return np.array(_fitted_sorted(xy, dims, estimates, z_names)[:, 1], dtype=np.float64)


def _sorted_frame(columns: dict[str, Any], order: np.ndarray) -> dict[str, Any]:
    """Columns in the group-sorted row order that lme uses for the variance functions."""
    return {str(name): np.asarray(values)[order] for name, values in columns.items()}


def _var_struct_state(var: Any, frame: dict[str, Any]) -> _VarStruct:
    """Initialize a variance function on the sorted data (R ``Initialize.varStruct``).

    The translated ``initialize`` functions give the covariate, the strata, and the
    starting parameters. Fixed parameters and covariates that need ``fitted(.)`` are
    not translated for lme yet.
    """
    classes = tuple(var.classes)
    kind = next(name for name in classes if name in _GENERAL_VARIANCE_CLASSES)
    rows = len(next(iter(frame.values())))
    if any(getattr(var, name, None) is not None for name in ("const_fixed", "power_fixed")):
        raise NotImplementedError("fixed varConstPower parameters are not in lme yet")
    if getattr(var, "fixed", None) is not None:
        return _fixed_power_state(kind, var, frame, rows)
    if kind == "varConstPower":
        return _const_power_state(var, frame, rows)
    init = {
        "varPower": _var_power_initialize,
        "varExp": _varexp_initialize,
        "varIdent": _var_ident_initialize,
    }[kind]
    obj = init(var, frame)
    needs_update = bool(obj.need_update)
    if needs_update and not _is_fitted_covariate(var.formula):
        raise NotImplementedError("a variance covariate other than fitted(.) is waiting on lme update")
    if kind == "varIdent":
        if obj.groups is None:
            return _VarStruct(kind, np.zeros(0), rows)
        start = np.asarray(_var_ident_coef(obj, unconstrained=True, allCoef=False).values, dtype=np.float64)
        names = list(obj.group_names or ())
        index = np.array([names.index(str(group)) for group in obj.groups], dtype=np.intp)
        return _VarStruct(kind, start.copy(), rows, None, index)
    if kind == "varPower":
        start = np.asarray(_var_power_coef(obj, allCoef=False).values, dtype=np.float64)
    else:
        start = np.asarray(obj.values, dtype=np.float64).reshape(-1)
    if start.size == 0:
        raise NotImplementedError("a single-stratum variance function without a starting value is not translated")
    covariate = None if needs_update else np.asarray(obj.covariate, dtype=np.float64).reshape(-1)
    if obj.groups is None:
        index = np.zeros(rows, dtype=np.intp)
    else:
        names = list(obj.group_names or ())
        index = np.array([names.index(str(group)) for group in obj.groups], dtype=np.intp)
    return _VarStruct(kind, start.copy(), rows, covariate, index, needs_update)


def _fixed_power_state(kind: str, var: Any, frame: dict[str, Any], rows: int) -> _VarStruct:
    """varPower or varExp with its single parameter fixed (R ``Initialize`` with ``whichFix``).

    The weights come from the data covariate and the fixed value, so the variance
    function adds no free parameter to the lme optimisation (R ``object <- numeric(0)``).
    """
    if kind not in ("varPower", "varExp"):
        raise NotImplementedError(f"fixed {kind} parameters are not in lme yet")
    form = var.formula
    if _get_groups_formula(form) is not None:
        raise NotImplementedError(f"grouped fixed {kind} is not translated")
    if _is_fitted_covariate(form) or any(name not in frame for name in _all_vars(getCovariateFormula(form).text)):
        raise NotImplementedError("a fixed variance function on a fitted(.) covariate is not translated")
    fixed = float(np.asarray(var.fixed, dtype=np.float64).reshape(-1)[0])
    if fixed == 0.0 and kind == "varPower":
        raise NotImplementedError("varPower(fixed=0) reduces to varIdent and is not translated")
    covariate = np.asarray(_var_covariate(_as_frame(frame), form), dtype=np.float64).reshape(-1)
    return _VarStruct(
        kind, np.zeros(0), rows, covariate, np.zeros(rows, dtype=np.intp), fixed=fixed
    )


def _const_power_state(var: Any, frame: dict[str, Any], rows: int) -> _VarStruct:
    """varConstPower on one stratum: start at ``log(0.1)`` and ``0`` unless given (R Initialize)."""
    form = var.formula
    if _get_groups_formula(form) is not None:
        raise NotImplementedError("grouped varConstPower is not translated")
    needs_update = any(name not in frame for name in _all_vars(getCovariateFormula(form).text))
    if needs_update and not _is_fitted_covariate(form):
        raise NotImplementedError("a variance covariate other than fitted(.) is waiting on lme update")
    covariate = None
    if not needs_update:
        covariate = np.asarray(_var_covariate(_as_frame(frame), form), dtype=np.float64).reshape(-1)
    const = float(var.const[0]) if np.asarray(var.const).size else math.log(0.1)
    power = float(var.power[0]) if np.asarray(var.power).size else 0.0
    return _VarStruct(
        "varConstPower", np.array([const, power], dtype=np.float64), rows, covariate, None, needs_update
    )


def _r_pow(base: np.ndarray, exponent: np.ndarray) -> np.ndarray:
    """R ``abs(base)^exponent`` as R computes it on x86-64.

    R's ``^`` calls ``powl`` (extended precision) and rounds to double, which differs
    from the double ``pow`` by one ulp in some cases. ``numpy.longdouble`` power is
    the same ``powl`` call, so the weights match R bit for bit.
    """
    magnitude = np.abs(np.asarray(base, dtype=np.float64)).astype(np.longdouble)
    expo = np.broadcast_to(np.asarray(exponent, dtype=np.float64), magnitude.shape).astype(np.longdouble)
    return np.power(magnitude, expo).astype(np.float64)


def _var_struct_weights(state: _VarStruct, params: np.ndarray) -> tuple[np.ndarray, float]:
    """Variance weights and ``sum(log(w))`` at the unconstrained parameters (R ``coef<-`` and ``recalc``)."""
    params = np.asarray(params, dtype=np.float64).reshape(-1)
    if state.kind == "varConstPower":
        const = math.exp(float(params[0]))
        weights = 1.0 / (const + _r_pow(state.covariate, float(params[1])))
    elif state.kind == "varIdent":
        if state.index is None:
            weights = np.ones(state.rows, dtype=np.float64)
        else:
            natural = np.concatenate([[1.0], np.array([math.exp(float(v)) for v in params])])
            weights = 1.0 / natural[state.index]
    else:
        if state.fixed is not None:
            rows_par = np.full(state.rows, state.fixed, dtype=np.float64)
        else:
            rows_par = params[state.index]
        if state.kind == "varPower":
            weights = _r_pow(state.covariate, -rows_par)
        else:
            weights = np.array(
                [math.exp(-a * c) for a, c in zip(rows_par.tolist(), state.covariate.tolist())],
                dtype=np.float64,
            )
    return weights, _weight_log_sum(weights)


def _optimize_variance_struct(
    start: np.ndarray,
    con: _ConLin,
    block: PdMat,
    state: _VarStruct,
    control: dict[str, Any],
    reml: bool,
) -> tuple[np.ndarray, dict[str, Any]]:
    """Maximise the weighted ``logLik`` over reStruct and variance parameters (``nlminb``).

    ``con.xy`` is the raw condensed model. Each call scales it by the weights of the
    variance parameters (``recalc.varFunc``), adds their ``sum(log(w))``, and runs the
    kernel with the reStruct factor (``asDelta = 1``), as ``logLik.lmeStruct`` does.
    """
    pdims = _flatten_dims(con.dims)
    pd_code = [_PD_CODE[block.pd_class]]
    settings = [int(reml), 1, 0, *pd_code]
    xy = np.asarray(con.xy, dtype=np.float64)
    sigma = float(con.sigma)
    n_re = int(len(start) - state.size)

    def objective(point) -> float:
        point = np.asarray(point, dtype=np.float64)
        weights, offset = _var_struct_weights(state, point[n_re:])
        scaled = np.asfortranarray(xy * weights[:, None]).reshape(-1, order="F").tolist()
        factor = _block_factor(block, pdims, pd_code, point[:n_re])
        vals, _lrss = nlmemixed.mixed_loglik(scaled, pdims, list(factor), settings, sigma)
        return -(float(offset) + float(np.asarray(vals, dtype=np.float64)[0]))

    nlminb_control = {
        "iter.max": int(control.get("msMaxIter", 50)),
        "eval.max": int(control.get("msMaxEval", 200)),
    }
    fit = nlminb_port(objective, [float(v) for v in np.asarray(start, dtype=np.float64)], control=nlminb_control)
    par = np.asarray(fit["par"], dtype=np.float64)
    info = {
        "par": par,
        "objective": float(fit["objective"]),
        "convergence": int(fit["convergence"]),
        "iterations": int(fit["iterations"]),
        "evaluations": {"function": int(fit["evaluations"]["function"]), "gradient": int(fit["evaluations"]["gradient"])},
        "message": str(fit["message"]),
    }
    return par, info


@dataclass(slots=True)
class _VarStructFit:
    """Result of the lme pass loop for a varStruct (see ``_fit_variance_struct``)."""

    par: np.ndarray
    optimizer: dict[str, Any]
    estimates: dict[str, Any]
    fit_con: _ConLin
    offset: float
    weights: np.ndarray
    num_iter: int


def _fit_variance_struct(
    raw_con: _ConLin,
    block: PdMat,
    parameters: np.ndarray,
    state: _VarStruct,
    control: dict[str, Any],
    reml: bool,
    z_names: list[str],
) -> _VarStructFit:
    """The repeat loop of ``lme.formula`` for a varStruct (R ``lme.R``).

    Each pass runs ``nlminb`` from the current ``coef(lmeSt)``. The objective applies the
    weights of the current covariate, which ``coef<-`` sets. The pass then estimates the
    effects at the new point (``MEestimate``). A covariate that needs ``fitted(.)`` is
    replaced by the level-Q fitted values, and the loop stops when the relative change
    of ``coef(lmeSt)`` is within ``tolerance``. Without such a covariate there is one pass.
    """
    n_re = int(parameters.size)
    par = np.concatenate([np.asarray(parameters, dtype=np.float64), state.start])
    tolerance = float(control.get("tolerance", 1e-6))
    max_iter = int(control.get("maxIter", 50))
    num_iter = 0
    while True:
        old = par.copy()
        par, optimizer = _optimize_variance_struct(par, raw_con, block, state, control, reml)
        weights, offset = _var_struct_weights(state, par[n_re:])
        fit_con = _ConLin(
            xy=raw_con.xy * weights[:, None],
            dims=_copy_dims(raw_con.dims),
            log_lik=0.0,
            sigma=raw_con.sigma,
        )
        estimates = _estimate(fit_con, block, par[:n_re], reml, offset)
        if not state.needs_update:
            break
        num_iter += 1
        state.covariate = _fitted_covariate(raw_con.xy, raw_con.dims, estimates, z_names)
        conv = np.abs((old - par) / np.where(par == 0.0, 1.0, par))
        if float(np.max(conv)) <= tolerance:
            break
        if num_iter > max_iter:
            if control.get("returnObject", False):
                break
            raise RuntimeError("maximum number of iterations (lmeControl(maxIter)) reached without convergence")
    return _VarStructFit(par, optimizer, estimates, fit_con, offset, weights, num_iter)


def _fixed_weights(columns: dict[str, Any], form: str, order: np.ndarray) -> np.ndarray:
    """``varWeights`` of ``varFixed``: ``1 / sqrt(abs(covariate))``, in the sorted row order."""
    covariate = np.asarray(getCovariate(columns, form), dtype=np.float64).reshape(-1)
    return (1.0 / np.sqrt(np.abs(covariate)))[order]


def _weight_log_sum(weights: np.ndarray) -> float:
    """``sum(log(w))`` as R accumulates it: libm ``log`` values summed in long double."""
    total = np.longdouble(0.0)
    for value in weights:
        total += math.log(float(value))
    return float(total)


def _estimate(con: _ConLin, block: PdMat, parameters: np.ndarray, reml: bool, offset: float = 0.0) -> dict[str, Any]:
    pdims = _flatten_dims(con.dims)
    pd_code = [_PD_CODE[block.pd_class]]
    factor = _block_factor(block, pdims, pd_code, parameters)
    xy = np.asfortranarray(con.xy).reshape(-1, order="F").tolist()
    settings = [int(reml), 1, 0, *pd_code]
    profile, _lrss = nlmemixed.mixed_loglik(xy, pdims, list(factor), settings, con.sigma)
    _lik, dc = nlmemixed.mixed_estimate(xy, pdims, list(factor), int(reml), 0, con.sigma)
    str_rows = int(con.dims["StrRows"])
    zx_cols = int(con.dims["ZXcols"])
    estimates = np.asarray(dc, dtype=np.float64).reshape(str_rows, zx_cols, order="F")
    p = int(con.dims["ncol"][1])
    resp = estimates[:, -1]
    beta = resp[str_rows - p - 1 : str_rows - 1].copy()
    n_used = int(con.dims["N"]) - int(reml) * p
    sigma = abs(float(resp[-1])) / math.sqrt(n_used)
    loglik = (n_used * (math.log(n_used) - (1.0 + math.log(2.0 * math.pi)))) / 2.0 + (float(offset) + float(profile[0]))
    block_r = estimates[str_rows - p - 1 : str_rows - 1, zx_cols - p - 1 : zx_cols - 1]
    var_factor = sigma * np.linalg.inv(block_r).T
    var_fix = var_factor.T @ var_factor
    nc = int(con.dims["ncol"][0])
    offsets = con.dims["SToff"][0]
    random = np.vstack([resp[int(offset) : int(offset) + nc] for offset in offsets])
    return {
        "beta": beta,
        "sigma": sigma,
        "loglik": loglik,
        "var_fix": var_fix,
        "var_factor": var_factor,
        "b": random,
        "profile": float(profile[0]),
    }


def _fitted_sorted(xy: np.ndarray, dims: dict[str, Any], estimates: dict[str, Any], z_names: list[str]) -> np.ndarray:
    q = 1
    nc = [int(value) for value in dims["ncol"]]
    n = int(dims["N"])
    fitted = np.zeros((n, q + 1), dtype=np.float64)
    zx_start = list(reversed(np.cumsum([1, *nc[:q]]).tolist()))
    zx_end = list(reversed(np.cumsum(nc[: q + 1]).tolist()))
    if zx_start[0] <= zx_end[0]:
        sl = slice(zx_start[0] - 1, zx_end[0])
        fitted[:, 0] = xy[:, sl] @ estimates["beta"]
    lengths = dims["ZXlen"][q - 1]
    counts = int(dims["ngrps"][q - 1])
    sl = slice(zx_start[1] - 1, zx_end[1])
    repeated = np.repeat(estimates["b"], lengths.astype(int), axis=0)
    fitted[:, 1] = fitted[:, 0] + np.sum(xy[:, sl] * repeated, axis=1)
    del z_names, counts
    return fitted


def _decompose(con: _ConLin) -> None:
    if int(con.dims["StrRows"]) >= int(con.dims["ZXrows"]):
        return
    pdims = _flatten_dims(con.dims)
    flat = np.asfortranarray(con.xy).reshape(-1, order="F")
    out = np.asarray(nlmemixed.mixed_decomp(flat.tolist(), pdims), dtype=np.float64)
    str_rows = int(con.dims["StrRows"])
    zx_cols = int(con.dims["ZXcols"])
    con.xy = out[: str_rows * zx_cols].reshape(str_rows, zx_cols, order="F")
    con.dims["ZXrows"] = str_rows
    con.dims["ZXoff"] = [np.array(part, dtype=np.int32) for part in con.dims["DecOff"]]
    con.dims["ZXlen"] = [np.array(part, dtype=np.int32) for part in con.dims["DecLen"]]


def _fix_df(x_matrix: np.ndarray, names: list[str], group_codes: list[np.ndarray], dims: dict[str, Any], estimates: dict[str, Any]) -> LmeFixDF:
    n, p = x_matrix.shape
    q = len(group_codes)
    const = np.array([_is_constant(x_matrix[:, j]) for j in range(p)])
    not_int = ~const
    n_groups = list(reversed([int(value) for value in dims["ngrps"]]))[2:]
    strat = [f"g{index}" for index in range(q)] + ["Residual"]
    base = np.array(n_groups + [n], dtype=np.float64) - np.array([0, *n_groups], dtype=np.float64)
    df_x = base.copy()
    df_terms = base.copy()
    assign = _term_assign(names)
    if np.any(not_int):
        flat_x = np.asfortranarray(x_matrix).reshape(-1, order="F")
        flat_g = np.concatenate(group_codes).astype(np.int32)
        table = np.asarray(nlmemixed.inner_perc_table(flat_x.tolist(), flat_g.tolist(), p, q, n), dtype=np.float64)
        table = table.reshape(p, q, order="F")
        inner = np.column_stack([np.ones(p), table])
        strata = []
        for row in inner:
            positive = np.flatnonzero(row > 0)
            strata.append(int(positive.max()) if positive.size else 0)
        term_strata = []
        for name, columns in assign.items():
            if np.any(not_int[columns]):
                term_strata.append(max(strata[int(col)] for col in columns))
            else:
                term_strata.append(None)
        for column, stratum in enumerate(strata):
            if not_int[column]:
                df_x[stratum] -= 1
        if np.any(~not_int):
            df_x[0] -= 1
        else:
            df_x[1:] += 1
        values_x = np.zeros(p, dtype=np.float64)
        values_x[not_int] = df_x[[strata[j] for j in range(p) if not_int[j]]]
        for index, (name, columns) in enumerate(assign.items()):
            if term_strata[index] is None:
                continue
            df_terms[term_strata[index]] -= len(columns)
        if any(item is None for item in term_strata):
            df_terms[0] -= 1
        else:
            df_terms[1:] += 1
        values_terms = np.zeros(len(assign), dtype=np.float64)
        for index, stratum in enumerate(term_strata):
            if stratum is not None:
                values_terms[index] = df_terms[stratum]
        if np.any(~not_int):
            values_x[~not_int] = np.max(df_x)
            for index, stratum in enumerate(term_strata):
                if stratum is None:
                    values_terms[index] = np.max(df_terms)
    else:
        values_x = np.full(p, np.max(df_x))
        values_terms = np.full(len(assign), np.max(df_terms))
    return LmeFixDF(
        x=values_x,
        x_names=tuple(names),
        terms=values_terms,
        term_names=tuple(assign),
        assign=assign,
        var_fix_factor=estimates["var_factor"],
    )


def _natural_upper_factor(params: np.ndarray, ncol: int) -> np.ndarray:
    """Upper square-root factor of a pdNatural matrix (R ``pdFactor.pdNatural``, C ``natural_pd``).

    The matrix has variances ``exp(2 * log sd)`` and correlations ``(e - 1) / (e + 1)`` from the
    generalized logits, filled in the order of the C loop. Its upper Cholesky factor is returned.
    """
    values = np.asarray(params, dtype=np.float64).ravel()
    std = np.exp(values[:ncol])
    corr_logits = values[ncol:]
    matrix = np.zeros((ncol, ncol), dtype=np.float64)
    k = 0
    for i in range(ncol):
        matrix[i, i] = std[i] * std[i]
        for j in range(i + 1, ncol):
            e = math.exp(float(corr_logits[k]))
            corr = (e - 1.0) / (e + 1.0)
            matrix[i, j] = matrix[j, i] = std[i] * std[j] * corr
            k += 1
    return np.linalg.cholesky(matrix).T


def _natural_inverse_factor(values: np.ndarray, ncol: int) -> np.ndarray:
    """Upper factor of the inverse of a pdNatural matrix (R ``solve.pdNatural`` then ``pdFactor``).

    The inverse's natural parameters are the log standard deviations and the generalized
    logits of its correlations, as R's ``solve.pdNatural`` computes them. A one-column
    matrix only negates its parameter.
    """
    params = np.asarray(values, dtype=np.float64).ravel()
    if ncol == 1:
        inverse_params = -params
    else:
        inv_factor = np.linalg.solve(_natural_upper_factor(params, ncol), np.eye(ncol))
        val = inv_factor @ inv_factor.T
        std_dev = np.sqrt(np.diag(val))
        corr = val / np.outer(std_dev, std_dev)
        lower = np.array([corr[row, col] for col in range(ncol) for row in range(col + 1, ncol)])
        inverse_params = np.concatenate([np.log(std_dev), np.log((lower + 1.0) / (1.0 - lower))])
    return _natural_upper_factor(inverse_params, ncol)


def _ap_var(
    con,
    block,
    parameters,
    estimates,
    control,
    reml,
    original_xy,
    original_dims,
    offset=0.0,
    state: _VarStruct | None = None,
    var_pars: np.ndarray | None = None,
):
    if not control.get("apVar", True):
        return "Approximate variance-covariance matrix not available", None
    try:
        return _ap_var_matrix(
            con, block, parameters, estimates, control, reml, original_xy, original_dims, offset, state, var_pars
        )
    except NotImplementedError:
        return "Approximate variance-covariance matrix not available", None


def _ap_var_matrix(
    con,
    block,
    parameters,
    estimates,
    control,
    reml,
    original_xy,
    original_dims,
    offset=0.0,
    state: _VarStruct | None = None,
    var_pars: np.ndarray | None = None,
):
    """Approximate covariance (R ``lmeApVar``) of the reStruct, variance, and log(sigma) parameters.

    With a varStruct, ``con`` is the raw condensed model. Each Hessian point sets the
    variance weights from ``var_pars`` (``coef<-``) and adds their ``sum(log(w))``.
    The covariate is the one ``state`` holds at the call (after the last update).
    """
    sigma = estimates["sigma"]
    factor = _block_factor(block, _flatten_dims(con.dims), [_PD_CODE[block.pd_class]], parameters)
    q = len(block.names)
    precision = np.asarray(factor, dtype=np.float64).reshape(q, q, order="F")
    covariance = np.linalg.inv(precision.T @ precision) * sigma * sigma
    natural = pdNatural(covariance)
    n_nat = int(np.asarray(natural.values).size)
    var_start = np.zeros(0, dtype=np.float64) if state is None else np.asarray(var_pars, dtype=np.float64)
    pars = np.concatenate(
        [np.asarray(natural.values, dtype=np.float64), var_start, [math.log(sigma)]]
    )

    def criterion(point, *_args):
        point = np.asarray(point, dtype=np.float64)
        local_sigma = math.exp(float(point[-1]))
        # lmeApVar.fullLmeLogLik: sigma * pdFactor(solve(object$reStruct)).
        inverse_factor = _natural_inverse_factor(point[:n_nat], q)
        flat = np.asfortranarray(local_sigma * inverse_factor).reshape(-1, order="F")
        pdims = _flatten_dims(con.dims)
        settings = [int(reml), 1, 0, _PD_CODE[block.pd_class]]
        if state is None:
            xy = np.asfortranarray(con.xy).reshape(-1, order="F").tolist()
            offset_now = float(offset)
        else:
            weights, offset_now = _var_struct_weights(state, point[n_nat:-1])
            xy = np.asfortranarray(con.xy * weights[:, None]).reshape(-1, order="F").tolist()
        val, lrss = nlmemixed.mixed_loglik(xy, pdims, flat.tolist(), settings, 0.0)
        n_used = int(original_dims["N"]) - int(reml) * int(original_dims["ncol"][1])
        aux = (math.exp(float(lrss)) / local_sigma) ** 2
        # lmeApVar.fullLmeLogLik: conLin$logLik (the varStruct term) + kernel value + Laplace term.
        return (offset_now + float(val[0])) + (n_used * math.log(aux) - aux) / 2.0

    hess = fdHess(pars, criterion, relStep=control.get(".relStep"), minAbsPar=control.get("minAbsParApVar", 0.05))
    matrix = hess["Hessian"]
    eigvals = np.linalg.eigvalsh(matrix)
    if np.all(eigvals < 0):
        solved = np.linalg.inv(-matrix)
        return solved, pars
    return "Non-positive definite approximate variance-covariance", pars


def _medims(group_codes: list[np.ndarray], ncols: np.ndarray) -> dict[str, Any]:
    q = len(group_codes)
    n = int(group_codes[0].shape[0])
    is_last = np.zeros((n, q + 2), dtype=bool)
    for index, codes in enumerate(group_codes):
        column = q - index - 1
        change = np.zeros(n, dtype=bool)
        change[:-1] = codes[1:] != codes[:-1]
        change[-1] = True
        is_last[:, column] = change
    is_last[-1, :] = True
    last_row = [np.flatnonzero(is_last[:, column]) + 1 for column in range(q + 2)]
    transposed = is_last.T.astype(np.float64)
    scaled = transposed * ncols.astype(np.float64)[:, None]
    cumulative = np.cumsum(scaled.reshape(-1, order="F")).reshape(scaled.shape, order="F")
    str_sizes = cumulative * transposed
    last_str = []
    for column in range(q + 2):
        values = str_sizes.T[:, column]
        last_str.append(values[values != 0.0])
    str_rows = float(np.max(last_str[-1]))
    last_block = []
    for index in range(q):
        last_block.append(np.concatenate([str_sizes[index, :-1], [str_rows]]))
    if last_block:
        max_str = np.maximum.reduce(last_block)
        for index in range(q):
            mask = last_block[index] != 0
            last_block[index] = max_str[mask]
    last_block.extend([np.array([str_rows]), np.array([str_rows])])
    qvec = ncols.astype(np.float64) * np.array([1] * q + [0, 0], dtype=np.float64)
    return {
        "N": n,
        "ZXrows": n,
        "ZXcols": int(np.sum(ncols)),
        "Q": q,
        "StrRows": str_rows,
        "qvec": qvec,
        "ngrps": np.array([len(rows) for rows in last_row], dtype=np.int32),
        "DmOff": np.concatenate([[0], np.cumsum(ncols.astype(np.int64) ** 2)])[: q + 2],
        "ncol": ncols.astype(np.int32),
        "nrot": _nrot(ncols),
        "ZXoff": _offsets(n, ncols, last_row, False),
        "ZXlen": [_lengths(rows) for rows in last_row],
        "SToff": _offsets(str_rows, ncols, last_str, True),
        "DecOff": _offsets(str_rows, ncols, last_block, False),
        "DecLen": [_lengths(rows) for rows in last_block],
    }


def _flatten_dims(dims: dict[str, Any]) -> list[int]:
    values = [
        int(dims["N"]),
        int(dims["ZXrows"]),
        int(dims["ZXcols"]),
        int(dims["Q"]),
        int(dims["StrRows"]),
    ]
    for key in ("qvec", "ngrps", "DmOff", "ncol", "nrot"):
        values.extend(int(part) for part in np.asarray(dims[key]).reshape(-1))
    for key in ("ZXoff", "ZXlen", "SToff", "DecOff", "DecLen"):
        for part in dims[key]:
            values.extend(int(item) for item in np.asarray(part).reshape(-1))
    return values


def _offsets(width: float, ncols: np.ndarray, rows: list[np.ndarray], triangle: bool) -> list[np.ndarray]:
    cstart = np.concatenate([[0], np.cumsum(width * ncols.astype(np.float64))])
    out = []
    for index, ends in enumerate(rows):
        ends = np.asarray(ends, dtype=np.float64)
        if triangle:
            shifted = ends - float(ncols[index])
        else:
            shifted = np.concatenate([[0.0], ends[:-1]]) if ends.size else ends
        out.append(cstart[index] + shifted)
    return out


def _lengths(ends: np.ndarray) -> np.ndarray:
    ends = np.asarray(ends, dtype=np.float64)
    if ends.size == 0:
        return ends
    return np.diff(np.concatenate([[0.0], ends]))


def _nrot(ncols: np.ndarray) -> np.ndarray:
    rev = ncols[::-1].astype(np.float64)
    folded = np.concatenate([[0.0], np.cumsum(rev)])
    return folded[::-1][1:]


def _design(rhs: str, columns: dict[str, Any], n: int) -> tuple[np.ndarray, list[str]]:
    intercept = True
    names: list[str] = []
    data = []
    for term in _split_terms(rhs):
        if term in {"0", "-1"}:
            intercept = False
            continue
        if term == "1":
            intercept = True
            continue
        data.append(np.asarray(columns[term], dtype=np.float64))
        names.append(term)
    if intercept:
        data.insert(0, np.ones(n, dtype=np.float64))
        names.insert(0, "(Intercept)")
    if not data:
        return np.zeros((n, 0), dtype=np.float64), []
    return np.column_stack(data), names


def _term_assign(names: list[str]) -> dict[str, np.ndarray]:
    return {name: np.array([index], dtype=np.int64) for index, name in enumerate(names)}


def _is_constant(column: np.ndarray) -> bool:
    if column.size == 0:
        return True
    scale = 1.0 if column[0] == 0.0 else column[0]
    return bool(np.all(np.abs(column / scale - 1.0) < math.sqrt(np.finfo(float).eps)))


def _covariance_from_block(block: PdMat, con: _ConLin) -> np.ndarray:
    pdims = _flatten_dims(con.dims)
    factor = np.asarray(
        _block_factor(block, pdims, [_PD_CODE[block.pd_class]], block.values),
        dtype=np.float64,
    )
    q = len(block.names)
    matrix = factor.reshape(q, q, order="F")
    gram = matrix.T @ matrix
    return gram


def _copy_initialized(random: _InitializedRandom, block: PdMat) -> PdMat:
    return PdMat(
        values=np.asarray(random.block.values, dtype=np.float64).copy(),
        formula=block.formula,
        names=block.names,
        pd_class=random.block.pd_class,
    )


def _random_is_initialized(random: Any) -> bool:
    return isinstance(random, _InitializedRandom)


def _copy_dims(dims: dict[str, Any]) -> dict[str, Any]:
    copied = {}
    for key, value in dims.items():
        if isinstance(value, list):
            copied[key] = [np.array(part, copy=True) for part in value]
        elif isinstance(value, np.ndarray):
            copied[key] = value.copy()
        else:
            copied[key] = value
    return copied


def _columns(data: Any) -> dict[str, Any]:
    if hasattr(data, "columns") and isinstance(data.columns, dict):
        return data.columns
    if isinstance(data, dict):
        return data
    raise TypeError("data must expose a columns mapping")


def _grouping(data: Any, random: Any, columns: dict[str, Any]) -> tuple[str, Any, tuple[str, ...] | None]:
    if isinstance(random, _InitializedRandom):
        name = random.group
        return name, columns[name], getattr(data, "group_levels", None)
    text = _formula_text(random) if _looks_like_formula(random) else ""
    if text.startswith("~") and "|" not in text:
        name = text.lstrip("~").strip()
        if name in columns:
            return name, columns[name], getattr(data, "group_levels", None)
    if "|" in text:
        name = text.split("|", 1)[1].strip().split("/")[0].strip()
        return name, columns[name], getattr(data, "group_levels", None)
    formula = getattr(data, "formula", None)
    if formula and "|" in str(formula):
        name = str(formula).split("|", 1)[1].strip()
        return name, columns[name], getattr(data, "group_levels", None)
    levels = getattr(data, "group_levels", None)
    if "Subject" in columns:
        return "Subject", columns["Subject"], levels
    raise ValueError("could not find a grouping factor")


def _factor_codes(values: Any, levels: tuple[str, ...] | None) -> tuple[np.ndarray, tuple[str, ...]]:
    if hasattr(values, "codes") and hasattr(values, "levels"):
        return np.asarray(values.codes, dtype=np.int32), tuple(values.levels)
    texts = [str(value) for value in values]
    if levels is None:
        seen: list[str] = []
        for text in texts:
            if text not in seen:
                seen.append(text)
        levels = tuple(seen)
    index = {level: pos for pos, level in enumerate(levels)}
    return np.array([index[text] for text in texts], dtype=np.int32), tuple(levels)


def _level_names(codes: np.ndarray, levels: tuple[str, ...]) -> list[str]:
    names = []
    seen = set()
    for code in codes:
        name = levels[int(code)]
        if name not in seen:
            seen.add(name)
            names.append(name)
    return names


def _formula_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    formula = getattr(value, "formula", None)
    if isinstance(formula, str):
        return formula.strip()
    return str(value).strip()


def _looks_like_formula(value: Any) -> bool:
    text = _formula_text(value)
    return "~" in text


def _split_fixed(formula: str) -> tuple[str, str]:
    lhs, rhs = formula.split("~", 1)
    rhs = rhs.split("|", 1)[0].strip()
    return lhs.strip(), rhs.strip()


def _covariate_text(random: Any, rhs: str) -> str:
    if isinstance(random, _InitializedRandom):
        text = random.block.formula or f"~{rhs}"
        return text.split("~", 1)[-1].split("|", 1)[0].strip()
    if _looks_like_formula(random):
        text = _formula_text(random)
        if "~" in text:
            text = text.split("~", 1)[1]
        return text.split("|", 1)[0].strip()
    return rhs


def _pd_class_of(random: Any) -> str:
    if isinstance(random, _InitializedRandom):
        return random.block.pd_class
    if _looks_like_formula(random) and "|" in _formula_text(random):
        return "pdLogChol"
    return "pdSymm"


def _split_terms(rhs: str) -> list[str]:
    return [part.strip() for part in rhs.split("+") if part.strip()]


def _grouped_fixed_formula(data: Any) -> str:
    formula = _formula_text(data)
    response, rhs = _split_fixed(formula)
    covariate = rhs.split("|", 1)[0].strip()
    return f"{response} ~ {covariate}"


def _infer_lmlist_formula(fit: LmList, data: Any) -> str:
    stored = getattr(fit, "formula", None)
    if isinstance(stored, str) and "~" in stored:
        lhs, rhs = stored.split("~", 1)
        rhs = rhs.split("|", 1)[0].strip()
        return f"{lhs.strip()} ~ {rhs}"
    table = lmlist_coef(fit)
    covariates = [name for name in (table.colnames if table is not None else ()) if name != "(Intercept)"]
    group = fit.groups_form.split("~", 1)[1].strip()
    columns = _columns(data)
    response = next(name for name in columns if name not in covariates and name != group)
    rhs = " + ".join(covariates) if covariates else "1"
    return f"{response} ~ {rhs}"


def _lmlist_residuals(formula: str, columns: dict[str, Any], fit: LmList, table) -> np.ndarray:
    """Residuals of the per-group ``lm`` fits, as ``resid(lmList)`` stacks them.

    ``mad`` only sees the sorted values, so the row order of the stack does not matter.
    """
    del formula, columns, table
    parts = []
    for _name, entry in fit.entries:
        if isinstance(entry, BaseException) or entry.residuals is None:
            raise ValueError("lmList residuals need the lm fits")
        parts.append(np.asarray(entry.residuals, dtype=np.float64))
    return np.concatenate(parts)


def _mad(values: np.ndarray) -> float:
    """R ``mad(x, na.rm = TRUE)``: ``1.4826 * median(abs(x - median(x)))``."""
    values = np.asarray(values, dtype=np.float64)
    values = values[np.isfinite(values)]
    center = _r_median(values)
    return _MAD_CONSTANT * _r_median(np.abs(values - center))


def _r_median(values: np.ndarray) -> float:
    """R ``median.default``: the middle value, or ``mean`` of the two middle values."""
    x = np.sort(np.asarray(values, dtype=np.float64))
    n = x.size
    half = (n + 1) // 2
    if n % 2 == 1:
        return float(x[half - 1])
    return r_mean(x[half - 1 : half + 1])


def _merge_control(base: dict[str, Any], control: Any) -> dict[str, Any]:
    merged = dict(base)
    if control:
        merged.update(control)
    return merged


def _match_method(value: str, choices: tuple[str, ...]) -> str:
    text = str(value)
    if isinstance(value, (list, tuple)):
        text = str(value[0])
    for choice in choices:
        if choice.lower().startswith(text.lower()):
            return choice
    raise ValueError(f"'{text}' does not match {choices}")


def _anova_several(first: LmeResult, others: tuple[Any, ...], test: bool) -> AnovaLme:
    models = [first, *others]
    if any(not isinstance(model, (LmeResult, NlmeResult)) for model in models):
        raise NotImplementedError("anova.lme of mixed classes is waiting on gls")
    methods = {model.method for model in models}
    if len(methods) != 1:
        raise ValueError("all fitted objects must have the same estimation method")
    logliks = []
    dfs = []
    aics = []
    bics = []
    for model in models:
        if isinstance(model, LmeResult):
            p = int(model.fixed.size)
            n = int(model.dims["N"])
            reml = model.method == "REML"
            nobs = n - (p if reml else 0)
            df = p + int(model.model_parameters.size) + 1
            ll = model.loglik
        else:
            p = int(model.fixed.size)
            nobs = int(next(iter(model.random.values())).shape[0])
            df = p + 2
            ll = model.loglik
        logliks.append(ll)
        dfs.append(df)
        aics.append(-2.0 * ll + 2.0 * df)
        bics.append(-2.0 * ll + math.log(nobs) * df)
    columns = {
        "df": np.asarray(dfs, dtype=np.float64),
        "AIC": np.asarray(aics, dtype=np.float64),
        "BIC": np.asarray(bics, dtype=np.float64),
        "logLik": np.asarray(logliks, dtype=np.float64),
    }
    if test:
        ratios = [math.nan]
        p_values = [math.nan]
        for left, right, df_left, df_right in zip(logliks, logliks[1:], dfs, dfs[1:]):
            diff = df_right - df_left
            if diff == 0:
                ratios.append(math.nan)
                p_values.append(math.nan)
            else:
                stat = 2.0 * abs(right - left)
                ratios.append(stat)
                p_values.append(float(chi2.sf(stat, abs(diff))))
        columns["L.Ratio"] = np.asarray(ratios, dtype=np.float64)
        columns["p-value"] = np.asarray(p_values, dtype=np.float64)
    return AnovaLme(columns=columns, row_names=tuple(f"model{index + 1}" for index in range(len(models))), rt=len(models))


def _nlme_fixed_map(fixed: Any) -> dict[str, tuple[str, ...]]:
    text = _formula_text(fixed)
    if "~" not in text and "+" in text:
        text = text.replace("+", "~")
    if "~" not in text:
        raise ValueError("fixed must name parameters")
    lhs, rhs = text.split("~", 1)
    names = [part.strip() for part in lhs.replace("+", " ").split() if part.strip() not in {"+", "~"}]
    if "+" in lhs:
        names = [part.strip() for part in lhs.split("+")]
    covariate = tuple(_design(rhs.strip(), {}, 0)[1]) if False else ("(Intercept)",)
    if rhs.strip() not in {"1", ""}:
        covariate = tuple(_split_terms(rhs))
        if "1" not in rhs and "-1" not in rhs and "0" not in rhs:
            covariate = ("(Intercept)", *covariate)
    return {name: covariate for name in names}


def _nlme_random_map(random: Any) -> dict[str, tuple[str, ...]]:
    text = _formula_text(random)
    if "|" in text:
        text = text.split("|", 1)[0]
    if "~" not in text and "+" not in text:
        text = f"{text} ~ 1"
    return _nlme_fixed_map(text)


def _start_fixed(start: Any, names: list[str]) -> np.ndarray:
    if isinstance(start, dict):
        values = start.get("fixed", start)
        if isinstance(values, dict):
            return np.array([float(values[name]) for name in names], dtype=np.float64)
    array = np.asarray(start, dtype=np.float64).reshape(-1)
    if array.size != len(names):
        raise ValueError("starting values for the fixed component are not the correct length")
    return array


def _expression_input(expression: str) -> str:
    inside = expression[expression.find("(") + 1 : expression.rfind(")")]
    return inside.split(",")[0].strip()


def _self_start(expression: str):
    if expression.startswith("SSasymp("):
        return _ssasymp
    if expression.startswith("SSasympOff("):
        return _ssasymp_off
    if expression.startswith("SSlogis("):
        return _sslogis
    raise NotImplementedError(f"nlme model '{expression}' is not translated")


def _ssasymp_off(x: np.ndarray, asym: np.ndarray, lrc: np.ndarray, c0: np.ndarray):
    """``SSasympOff(input, Asym, lrc, c0)`` and its gradient in (Asym, lrc, c0)."""
    rate = np.exp(lrc)
    expo = np.exp(-rate * (x - c0))
    mean = asym * (1.0 - expo)
    grad = np.column_stack([
        1.0 - expo,
        asym * (expo * ((x - c0) * rate)),
        -(asym * (expo * rate)),
    ])
    return mean, grad


def _ssasymp(x: np.ndarray, asym: np.ndarray, r0: np.ndarray, lrc: np.ndarray):
    expo = np.exp(-np.exp(lrc) * x)
    mean = asym + (r0 - asym) * expo
    grad = np.column_stack([
        1.0 - expo,
        expo,
        (r0 - asym) * expo * (-x) * np.exp(lrc),
    ])
    return mean, grad


def _sslogis(x: np.ndarray, asym: np.ndarray, xmid: np.ndarray, scal: np.ndarray):
    expo = np.exp((xmid - x) / scal)
    mean = asym / (1.0 + expo)
    grad = np.column_stack([
        1.0 / (1.0 + expo),
        mean * expo / (scal * (1.0 + expo)),
        mean * expo * (x - xmid) / (scal**2 * (1.0 + expo)),
    ])
    return mean, grad


def _group_index(codes: np.ndarray) -> np.ndarray:
    index = np.zeros(codes.shape[0], dtype=np.int64)
    current = 0
    for pos in range(1, codes.shape[0]):
        if codes[pos] != codes[pos - 1]:
            current += 1
        index[pos] = current
    return index


def _nlme_working(evaluator, x, y, groups, theta, fixed_names, random_name) -> np.ndarray:
    n_group = int(groups.max()) + 1
    fixed = theta[n_group:]
    values = {name: np.full(len(y), fixed[index]) for index, name in enumerate(fixed_names)}
    if random_name in values:
        values[random_name] = values[random_name] + theta[groups]
    ordered = [values[name] for name in fixed_names]
    mean, grad = evaluator(x, *ordered)
    residual = y - mean
    design = grad
    z = design[:, fixed_names.index(random_name) : fixed_names.index(random_name) + 1]
    packed = np.column_stack([z, design, residual]).reshape(-1, order="F")
    return packed


def _lme_control_from_nlme(control: dict[str, Any]) -> dict[str, Any]:
    mapped = lmeControl()
    mapped["msMaxIter"] = control.get("msMaxIter", mapped["msMaxIter"])
    mapped["niterEM"] = control.get("niterEM", mapped["niterEM"])
    mapped["msTol"] = control.get("msTol", mapped["msTol"])
    mapped["apVar"] = False
    return mapped
