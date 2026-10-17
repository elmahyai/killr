"""``nlme.formula`` with general random structures on one or more nested levels.

``lme_family.nlme_formula`` fits one random intercept on one level. This
module follows the same ``nlme.formula`` loop for:

- a covariate design in the random formula (``random = Asym ~ age``),
- several random parameters on one level (``pdDiag(Asym + R0 ~ 1)``,
  ``pdSymm(Asym + R0 ~ 1)``),
- nested grouping (``groups = ~ Dog/Side`` with one random formula per level).

Levels are kept in R's internal order, innermost first. The random columns
are ``[Z_inner | Z_outer | X | residual]``, the same packing as ``fit_nlme``.
The variance-parameter step is ``_optimize_variance_counted``: R's ``nlminb``
(PORT, ``crates/nlminb_port``) on ``-logLik``, with R's iteration count.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from typing import Any

import numpy as np

import nlmemixed
from nlminb_port import nlminb_port

from nlme.lme_family import (
    _PD_CODE,
    _ConLin,
    _columns,
    _copy_dims,
    _decompose,
    _design,
    _expression_input,
    _factor_codes,
    _flatten_dims,
    _formula_text,
    _group_index,
    _lme_control_from_nlme,
    _match_method,
    _medims,
    _merge_control,
    _nlme_fixed_map,
    _self_start,
    _split_fixed,
    _start_fixed,
)
from nlme.nlmecontrol import nlmeControl
from nlme.matrix_assign import matrix_assign
from nlme.pdmat import PdMat

__all__ = ["NlmeRandomResult", "nlme_random_formula", "random_is_intercept_only"]

_PD_WRAPPER = re.compile(r"^\s*(pdLogChol|pdSymm|pdDiag)\s*\((.*)\)\s*$", re.DOTALL)


@dataclass(slots=True)
class NlmeRandomResult:
    """Fitted ``nlme`` object with general random structures, reduced to the proof values."""

    fixed: np.ndarray
    fixed_names: tuple[str, ...]
    covariances: dict[str, np.ndarray]
    sigma: float
    loglik: float
    num_iter: int
    method: str
    classes: tuple[str, ...] = ("nlme",)


@dataclass(slots=True)
class _Term:
    """One random parameter on a level: its fixed-parameter index and its design."""

    param: str
    param_index: int
    design: np.ndarray
    design_names: list[str]


@dataclass(slots=True)
class _Level:
    """One grouping level, stored innermost first as R does."""

    name: str
    pd_class: str
    terms: list[_Term]
    codes: np.ndarray
    n_groups: int
    group_index: np.ndarray
    offset: int = 0

    @property
    def q(self) -> int:
        return int(sum(term.design.shape[1] for term in self.terms))


def _split_group_names(groups: Any) -> list[str]:
    """``~ Dog/Side`` gives ``["Dog", "Side"]`` (outermost first)."""
    text = _formula_text(groups)
    if "|" in text:
        text = text.split("|", 1)[1]
    text = text.lstrip("~").strip()
    names = [part.strip() for part in text.split("/") if part.strip()]
    if not names:
        raise ValueError("'groups' must name at least one grouping factor")
    return names


def _random_spec(text: Any) -> tuple[str, list[tuple[str, str]]]:
    """Return ``(pd_class, [(parameter, covariate rhs), ...])`` for one random formula."""
    body = _formula_text(text)
    if "|" in body:
        body = body.split("|", 1)[0]
    pd_class = "pdLogChol"
    wrapped = _PD_WRAPPER.match(body)
    if wrapped:
        pd_class = wrapped.group(1)
        body = wrapped.group(2)
    if "~" not in body:
        raise ValueError("'random' must be a formula of the form \"parameter ~ expr\"")
    lhs, rhs = body.split("~", 1)
    names = [part.strip() for part in lhs.split("+") if part.strip()]
    if not names:
        raise ValueError("'random' must name at least one parameter")
    return pd_class, [(name, rhs.strip()) for name in names]


def random_is_intercept_only(random: Any) -> bool:
    """True when ``random`` is the plain pdLogChol intercept case that ``nlme_formula`` covers.

    One parameter, an intercept-only design, and no pd wrapper. Anything else
    goes to ``nlme_random_formula``.
    """
    if isinstance(random, dict):
        return False
    text = _formula_text(random)
    if _PD_WRAPPER.match(text.split("|", 1)[0]):
        return False
    try:
        pd_class, terms = _random_spec(random)
    except (ValueError, NotImplementedError):
        return True
    return pd_class == "pdLogChol" and len(terms) == 1 and terms[0][1] in {"1", ""}


def _level_columns(level: _Level) -> int:
    return level.q


def _working(evaluator, x, y, levels, n_random, theta, args, fixed_names, perm):
    """Packed ``[Z | X | residual]``, column-major, as ``fit_nlme`` expects."""
    n = len(y)
    fixed = theta[n_random:]
    values: list[Any] = [None] * len(args)
    for k, name in enumerate(fixed_names):
        values[args.index(name)] = np.full(n, fixed[k], dtype=np.float64)
    for level in levels:
        b = theta[level.offset : level.offset + level.n_groups * level.q].reshape(level.n_groups, level.q)
        col = 0
        for term in level.terms:
            width = term.design.shape[1]
            contrib = np.sum(term.design * b[level.group_index, col : col + width], axis=1)
            values[term.param_index] = values[term.param_index] + contrib
            col += width
    mean, grad = evaluator(x, *values)
    residual = y - mean
    columns = []
    for level in levels:
        for term in level.terms:
            columns.append(grad[:, term.param_index : term.param_index + 1] * term.design)
    columns.append(grad[:, perm])
    columns.append(residual[:, None])
    return np.column_stack(columns).reshape(-1, order="F")


def _working_xy(zx: np.ndarray, residual: np.ndarray, theta: np.ndarray, levels, n_random: int) -> np.ndarray:
    """``w = residual + X sfix + sum_levels Z b`` for the current ``theta``."""
    q_cols = sum(level.q for level in levels)
    w = residual + zx[:, q_cols:] @ theta[n_random:]
    col = 0
    for level in levels:
        b = theta[level.offset : level.offset + level.n_groups * level.q].reshape(level.n_groups, level.q)
        w = w + np.sum(zx[:, col : col + level.q] * b[level.group_index], axis=1)
        col += level.q
    return w


def _optimize_variance_counted(start: np.ndarray, xy_flat, pdims, pd_codes, control, reml, sigma):
    """R's ``nlme.formula`` LME step: ``nlminb(coef, -logLik(nlmeSt, pars))`` on PORT.

    The objective is the ``logLik.reStruct`` value: ``mixed_loglik`` with
    asDelta = 1 on ``pdFactor(pars)``. Control is R's default plus
    ``iter.max = msMaxIter``. Returns the parameters and PORT's iteration count
    (R's ``convIter``).
    """
    settings = [int(reml), 1, 0, *pd_codes]

    def objective(point) -> float:
        factor = nlmemixed.factor_from_parameters(pdims, pd_codes, np.asarray(point, dtype=np.float64).tolist())
        vals, _lrss = nlmemixed.mixed_loglik(xy_flat, pdims, list(factor), settings, sigma)
        return -float(np.asarray(vals, dtype=np.float64)[0])

    nlminb_control = {"iter.max": int(control.get("msMaxIter", 50))}
    fit = nlminb_port(objective, [float(v) for v in np.asarray(start, dtype=np.float64)], control=nlminb_control)
    par = np.asarray(fit["par"], dtype=np.float64)
    return par, int(fit["iterations"])


def _initialize_levels(xy, levels, pdims, pd_codes, reml, sigma, n_iter):
    """R's ``Initialize.reStruct``: ``matrix<-`` of ``diag(0.375^2 * colSums(Z^2) / ngrps)``
    on each uninitialized level, then ``MEEM`` and ``matrix<-`` of ``crossprod`` of the EM factor.
    """
    starts = []
    col = 0
    for level in levels:
        z = xy[:, col : col + level.q]
        # R's colSums accumulates in long double; match it row by row.
        squares = z**2
        column_sums = np.zeros(squares.shape[1], dtype=np.longdouble)
        for row in squares:
            column_sums += row
        variances = (0.375**2) * column_sums.astype(np.float64) / level.n_groups
        pd_block = PdMat(values=np.array([], dtype=np.float64), formula=None, names=(), pd_class=level.pd_class)
        starts.append(np.asarray(matrix_assign(pd_block, np.diag(variances)).values, dtype=np.float64))
        col += level.q
    start_params = np.concatenate(starts)
    flat = np.asarray(nlmemixed.factor_from_parameters(pdims, pd_codes, start_params.tolist()), dtype=np.float64)
    updated, _lik, _ra, _lrss = nlmemixed.mixed_em(
        np.asfortranarray(xy).reshape(-1, order="F").tolist(),
        pdims,
        flat.tolist(),
        n_iter,
        pd_codes,
        int(reml),
        sigma,
    )
    updated = np.asarray(updated, dtype=np.float64)
    new_pd = []
    offset = 0
    for level in levels:
        size = level.q * level.q
        factor = updated[offset : offset + size].reshape(level.q, level.q, order="F")
        offset += size
        pd_block = PdMat(values=np.array([], dtype=np.float64), formula=None, names=(), pd_class=level.pd_class)
        new_pd.append(np.asarray(matrix_assign(pd_block, factor.T @ factor).values, dtype=np.float64))
    return np.concatenate(new_pd)


def _estimate_levels(xy, dims, pdims, parameters, pd_codes, reml, sigma):
    """``sigma`` and ``logLik`` at the current variance parameters (as ``_estimate``)."""
    factor = nlmemixed.factor_from_parameters(pdims, pd_codes, parameters.tolist())
    xy_flat = np.asfortranarray(xy).reshape(-1, order="F").tolist()
    profile, _lrss = nlmemixed.mixed_loglik(xy_flat, pdims, list(factor), [int(reml), 1, 0, *pd_codes], sigma)
    _lik, dc = nlmemixed.mixed_estimate(xy_flat, pdims, list(factor), int(reml), 0, sigma)
    str_rows = int(dims["StrRows"])
    zx_cols = int(dims["ZXcols"])
    estimates = np.asarray(dc, dtype=np.float64).reshape(str_rows, zx_cols, order="F")
    p = int(dims["ncol"][-2])
    resp = estimates[:, -1]
    n_used = int(dims["N"]) - int(reml) * p
    fitted_sigma = abs(float(resp[-1])) / math.sqrt(n_used)
    loglik = (n_used * (math.log(n_used) - (1.0 + math.log(2.0 * math.pi)))) / 2.0 + float(profile[0])
    return fitted_sigma, loglik


def nlme_random_formula(
    model: str,
    data: Any,
    fixed: Any,
    random: Any = None,
    groups: Any = None,
    start: Any = None,
    method: str = "ML",
    control: Any = None,
) -> NlmeRandomResult:
    """Fit ``model`` with general random structures on one or more nested grouping levels.

    ``groups`` is a formula such as ``"~ Dog/Side"``. ``random`` is one formula
    (one level, optionally wrapped in ``pdDiag``, ``pdSymm``, or ``pdLogChol``) or
    a dict of formulas keyed by level name, outermost first.
    """
    control_vals = _merge_control(nlmeControl(), control)
    method = _match_method(method, ("ML", "REML"))
    reml = method == "REML"
    response, expression = _split_fixed(_formula_text(model))
    columns = _columns(data)
    y_all = np.asarray(columns[response], dtype=np.float64)
    n = int(y_all.shape[0])

    fixed_map = _nlme_fixed_map(fixed)
    fixed_names = list(fixed_map)
    if random is None:
        random = fixed
    group_names = _split_group_names(groups)
    if isinstance(random, dict):
        formulas = dict(random)
        if list(formulas) != group_names:
            raise ValueError("names of 'random' must match the grouping factors, outermost first")
    else:
        if len(group_names) != 1:
            raise ValueError("a single 'random' formula needs a single grouping factor")
        formulas = {group_names[0]: random}

    # Sort by outer key, then inner key (stable), as R's order(grps).
    raw_codes = {}
    for name in group_names:
        codes, _levels = _factor_codes(columns[name], getattr(data, "group_levels", None) if name == group_names[0] else None)
        raw_codes[name] = codes
    key = np.zeros(n, dtype=np.int64)
    for name in group_names:
        key = key * (int(raw_codes[name].max()) + 1) + raw_codes[name].astype(np.int64)
    order = np.argsort(key, kind="stable")
    sorted_codes = {name: raw_codes[name][order] for name in group_names}

    # Dense codes per level, outermost first (nlme's grps columns).
    cumulative = np.zeros(n, dtype=np.int64)
    level_codes_outer_to_inner = []
    for name in group_names:
        cumulative = cumulative * (int(sorted_codes[name].max()) + 1) + sorted_codes[name]
        _unique, dense = np.unique(cumulative, return_inverse=True)
        level_codes_outer_to_inner.append(dense.astype(np.int64))

    y = y_all[order]
    x_input = np.asarray(columns[_expression_input(expression)], dtype=np.float64)[order]
    args = [part.strip() for part in expression[expression.find("(") + 1 : expression.rfind(")")].split(",")[1:]]
    evaluator = _self_start(expression)
    p = len(fixed_names)
    perm = np.array([args.index(name) for name in fixed_names], dtype=np.int64)

    # Levels, innermost first.
    levels: list[_Level] = []
    for depth in range(len(group_names) - 1, -1, -1):
        name = group_names[depth]
        pd_class, specs = _random_spec(formulas[name])
        terms = []
        for param, rhs in specs:
            if param not in fixed_names:
                raise ValueError(f"random parameter '{param}' is not a fixed parameter")
            design_all, design_names = _design(rhs, columns, n)
            terms.append(
                _Term(
                    param=param,
                    param_index=args.index(param),
                    design=design_all[order],
                    design_names=design_names,
                )
            )
        codes = level_codes_outer_to_inner[depth]
        group_index = _group_index(codes)
        levels.append(
            _Level(
                name=name,
                pd_class=pd_class,
                terms=terms,
                codes=codes,
                n_groups=int(group_index[-1]) + 1,
                group_index=group_index,
            )
        )
    n_random = 0
    for level in levels:
        level.offset = n_random
        n_random += level.n_groups * level.q
    q_cols = sum(level.q for level in levels)
    p_len = q_cols + p

    start_fixed = _start_fixed(start, fixed_names)
    theta = np.concatenate([np.zeros(n_random, dtype=np.float64), start_fixed])

    # Kernel groups: innermost level first, each a length-n block.
    group_list = np.concatenate([level.codes for level in levels]).astype(np.int32).tolist()
    ncols = np.array([level.q for level in levels] + [p, 1], dtype=np.int32)
    dims = _medims([level_codes_outer_to_inner[d] for d in range(len(group_names))], ncols)
    pdims = _flatten_dims(dims)
    pd_codes = [_PD_CODE[level.pd_class] for level in levels]

    def callback(pars: list[float]) -> list[float]:
        return _working(
            evaluator, x_input, y, levels, n_random, np.asarray(pars, dtype=np.float64), args, fixed_names, perm
        ).tolist()

    first = _working(evaluator, x_input, y, levels, n_random, theta, args, fixed_names, perm)
    zx = first[: n * p_len].reshape(n, p_len, order="F")
    residual = first[n * p_len :]
    working = _working_xy(zx, residual, theta, levels, n_random)
    xy = np.column_stack([zx, working])

    sigma_fixed = float(control_vals["sigma"])
    con = _ConLin(xy=xy, dims=dims, log_lik=0.0, sigma=sigma_fixed)
    parameters = _initialize_levels(con.xy, levels, pdims, pd_codes, reml, sigma_fixed, int(control_vals["niterEM"]))

    pnls_settings = [
        float(control_vals["pnlsMaxIter"]),
        float(control_vals["minScale"]),
        float(control_vals["pnlsTol"]),
        0.0,
        0.0,
        0.0,
    ]
    max_iter = int(control_vals["maxIter"])
    tolerance = float(control_vals["tolerance"])
    control_ms = _lme_control_from_nlme(control_vals)
    level_sizes = [level.q * level.q for level in levels]
    precisions: list[np.ndarray] = []
    num_iter = 0
    while True:
        num_iter += 1
        old_pd = parameters.copy()
        old_fixed = theta[n_random:].copy()
        # R's MEdecomp(oldConLin): a single reStruct decomposes the condensed model before
        # logLik.reStruct, from the raw model each outer step. The PNLS step keeps the raw dims.
        decomposed = _ConLin(xy=con.xy.copy(), dims=_copy_dims(dims), log_lik=0.0, sigma=sigma_fixed)
        _decompose(decomposed)
        xy_flat = np.asfortranarray(decomposed.xy).reshape(-1, order="F").tolist()
        parameters, conv_iter = _optimize_variance_counted(
            parameters, xy_flat, _flatten_dims(decomposed.dims), pd_codes, control_ms, reml, sigma_fixed
        )
        factor = nlmemixed.factor_from_parameters(pdims, pd_codes, parameters.tolist())
        additional = np.zeros(n * (p_len + 1), dtype=np.float64)
        theta_out, factor_out, _groups, _settings_out, additional = nlmemixed.fit_nlme(
            theta.tolist(),
            factor,
            group_list,
            pdims,
            pd_codes,
            [],
            [],
            [],
            list(pnls_settings),
            additional.tolist(),
            0,
            0,
            sigma_fixed,
            callback,
        )
        theta = np.asarray(theta_out, dtype=np.float64)
        factor_flat = np.asarray(factor_out, dtype=np.float64)
        precisions = []
        new_pd = []
        offset = 0
        for level, size in zip(levels, level_sizes):
            f_mat = factor_flat[offset : offset + size].reshape(level.q, level.q, order="F")
            offset += size
            precision = f_mat.T @ f_mat
            precisions.append(precision)
            pd_block = PdMat(
                values=np.array([], dtype=np.float64),
                formula=None,
                names=tuple(name for term in level.terms for name in term.design_names),
                pd_class=level.pd_class,
            )
            new_pd.append(np.asarray(matrix_assign(pd_block, precision).values, dtype=np.float64))
        parameters = np.concatenate(new_pd)
        first = np.asarray(additional, dtype=np.float64)
        zx = first[: n * p_len].reshape(n, p_len, order="F")
        residual = first[n * p_len : n * p_len + n]
        working = _working_xy(zx, residual, theta, levels, n_random)
        con.xy = np.column_stack([zx, working])

        new_fixed = theta[n_random:]
        conv_fixed = float(np.max(np.abs((old_fixed - new_fixed) / np.where(np.abs(new_fixed) < tolerance, 1.0, new_fixed))))
        conv_pd = float(np.max(np.abs((old_pd - parameters) / np.where(np.abs(parameters) < tolerance, 1.0, parameters))))
        if max(conv_fixed, conv_pd) <= tolerance or (conv_fixed <= tolerance and conv_iter == 1):
            break
        if num_iter >= max_iter:
            raise RuntimeError(f"maximum number of iterations (maxIter = {max_iter}) reached without convergence")

    sigma, loglik = _estimate_levels(con.xy, dims, pdims, parameters, pd_codes, reml, sigma_fixed)
    covariances = {}
    for level, precision in zip(levels, precisions):
        covariances[level.name] = sigma * sigma * np.linalg.inv(precision)
    return NlmeRandomResult(
        fixed=theta[n_random:].copy(),
        fixed_names=tuple(fixed_names),
        covariances=covariances,
        sigma=float(sigma),
        loglik=float(loglik),
        num_iter=num_iter,
        method=method,
    )
