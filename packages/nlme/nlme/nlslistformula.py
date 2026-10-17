"""List of ``nls`` fits by group (nlme ``nlsList.formula``)."""

from __future__ import annotations

import math
import re
import warnings
from dataclasses import dataclass
from typing import Any

import numpy as np

from nlme.comparefits import NamedMatrix
from nlme.linpack_qr import (
    dgemv,
    ld_sum,
    lm_fit_coef,
    qr,
    qr_coef,
    qr_qty,
    qr_qy,
    qr_resid,
    r_mean,
)
from nlme.lmlistformula import na_fail

_MISSING = object()
_NLS_CONTROL = {"maxiter": 50, "tol": 1e-5, "minFactor": 1.0 / 1024}
_SS_ASYMP_OFF = re.compile(
    r"^\s*(\w+)\s*~\s*SSasympOff\s*\(\s*(\w+)\s*,\s*(\w+)\s*,\s*(\w+)\s*,\s*(\w+)\s*\)\s*$",
    re.IGNORECASE,
)


@dataclass(slots=True)
class NlsFit:
    """Minimal ``nls`` result for ``nlsList``."""

    coefficients: dict[str, float]
    sigma: float | None = None
    converged: bool = True
    fin_iter: int = 0
    fin_tol: float = float("nan")


@dataclass(slots=True)
class NlsList:
    """List of per-group ``nls`` fits with ``nlsList`` metadata."""

    entries: tuple[tuple[str, NlsFit | BaseException], ...]
    level: int
    pool: bool
    groups_form: str
    group_names: tuple[str, ...]
    labels: dict[str, str] | None = None
    units: dict[str, str] | None = None
    # The ``call`` attribute of the R object: the model formula and the data.
    formula: str | None = None
    data: Any = None

    def __iter__(self):
        return iter(self.entries)

    def __len__(self) -> int:
        return len(self.entries)


def nlsList_formula(
    model,
    data,
    start=None,
    control=_MISSING,
    level=_MISSING,
    subset=_MISSING,
    na_action=_MISSING,
    pool: bool = True,
    warn_nls=_MISSING,
) -> NlsList:
    """Fit ``nls`` separately for each level of the grouping factor in ``model``."""
    formula = _formula_text(model)
    frame = _as_data_frame(data)
    if subset is not _MISSING:
        raise NotImplementedError("subset is not implemented for nlsList.formula")
    if na_action is _MISSING:
        na_action = na_fail
    if warn_nls is _MISSING:
        warn_nls = True
    elif warn_nls is None or (isinstance(warn_nls, float) and np.isnan(warn_nls)):
        warn_nls = True
    frame = na_action(frame)
    grp_form = _get_groups_formula(formula, as_list=False)
    if grp_form is None:
        if _is_grouped_data(data):
            raise NotImplementedError(
                "nlsList.formula without groups in formula needs groupedData helpers"
            )
        raise ValueError(
            "'data' must be a \"groupedData\" object if 'formula' does not include groups"
        )
    grp_list = _get_groups_formula(formula, as_list=True)
    if level is _MISSING:
        level = len(grp_list)
    elif _length(level) > 1:
        raise ValueError("multiple levels not allowed")
    group_var = grp_list[level - 1].lstrip("~").strip()
    fit_model = _covariate_formula(formula)
    spec = _parse_ss_asymp_off(fit_model)
    groups = _get_groups(frame, group_var)
    group_levels = _group_level_order(data, groups)
    present = {str(value) for value in groups}
    group_levels = tuple(name for name in group_levels if name in present)
    controlvals = dict(_NLS_CONTROL)
    if control is not _MISSING and control is not None:
        if isinstance(control, dict):
            controlvals.update(control)
        else:
            raise TypeError("control must be a list or dict")
    val: list[tuple[str, NlsFit | BaseException]] = []
    for name in group_levels:
        rows = [index for index, group in enumerate(groups) if group == name]
        part = {column: [values[index] for index in rows] for column, values in frame.items()}
        try:
            fit = _nls_ss_asymp_off(part, spec, start, controlvals)
        except Exception as exc:
            fit = exc
        val.append((name, fit))
    val = _warn_err_list(val, warn=bool(warn_nls))
    labels = getattr(data, "labels", None)
    units = getattr(data, "units", None)
    return NlsList(
        entries=tuple(val),
        level=int(level),
        pool=bool(pool),
        groups_form=grp_form,
        group_names=tuple(name for name, _ in val),
        labels=labels,
        units=units,
        formula=formula,
        data=data,
    )


def coef(object: NlsList, aug_frame: bool = False, **_ignored) -> NamedMatrix | None:
    """Extract coefficients from an ``nlsList`` object as a named matrix."""
    del _ignored
    if aug_frame:
        raise NotImplementedError("augFrame is not implemented for coef.nlsList")
    coefs = []
    for _name, entry in object.entries:
        if isinstance(entry, BaseException):
            coefs.append(None)
        else:
            coefs.append(entry.coefficients)
    non_null = [item is not None for item in coefs]
    if not any(non_null):
        return None
    coef_names: list[str] = []
    for item in coefs:
        if item is None:
            continue
        for name in item:
            if name not in coef_names:
                coef_names.append(name)
    matrix = np.full((len(coefs), len(coef_names)), np.nan, dtype=np.float64)
    row_names = object.group_names
    for row, item in enumerate(coefs):
        if item is None:
            continue
        for col, name in enumerate(coef_names):
            if name in item:
                matrix[row, col] = item[name]
    return NamedMatrix(matrix, row_names, tuple(coef_names))


def _covariate_formula(formula: str) -> str:
    """Drop ``|`` groups from a model formula (like ``getCovariateFormula``)."""
    response, rhs = formula.split("~", 1)
    cov_side = _bar_lhs(rhs.strip())
    return f"{response.strip()} ~ {cov_side.strip()}"


def _bar_lhs(rhs: str) -> str:
    depth = 0
    end = len(rhs)
    for index, char in enumerate(rhs):
        if char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
        elif char == "|" and depth == 0:
            end = index
            break
    return rhs[:end].strip()


def _parse_ss_asymp_off(formula: str) -> tuple[str, str, tuple[str, ...]]:
    match = _SS_ASYMP_OFF.match(formula.replace("\n", " "))
    if not match:
        raise NotImplementedError("only SSasympOff nonlinear models are implemented")
    response, covariate, asym, lrc, c0 = match.groups()
    return response, covariate, (asym, lrc, c0)


_EPS = 2.0**-26  # .Machine$double.eps^(1/2), exact
_NLS_SINGULAR = "singular gradient"


def _sorted_xy_mean(x: np.ndarray, y: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """``sortedXyData``: mean of ``y`` at each distinct ``x``, in increasing ``x``.

    ``tapply`` names its groups with ``as.character`` (15 significant digits) and
    ``sortedXyData`` reads them back with ``as.numeric``, so ``x`` passes through that.
    """
    groups: dict[float, list[float]] = {}
    for xi, yi in zip(np.asarray(x, dtype=np.float64).tolist(), np.asarray(y, dtype=np.float64).tolist()):
        groups.setdefault(xi, []).append(yi)
    levels = sorted(groups)
    xvals = [float(f"{value:.15g}") for value in levels]
    means = [r_mean(groups[value]) for value in levels]
    order = sorted(range(len(xvals)), key=lambda index: xvals[index])
    return np.array([xvals[i] for i in order], dtype=np.float64), np.array(
        [means[i] for i in order], dtype=np.float64
    )


def _rt_asymptote(ys: np.ndarray) -> float:
    """``NLSstRtAsymptote.sortedXyData`` on the sorted mean responses."""
    lo = float(np.min(ys))
    hi = float(np.max(ys))
    last = float(ys[-1])
    last_dif = (abs(lo - last), abs(hi - last))
    spread = hi - lo
    # match(min(last.dif), last.dif) == 2 only when the second is strictly smaller
    if last_dif[1] < last_dif[0]:
        return hi + spread / 8.0
    return lo - spread / 8.0


def _ss_rhs_and_dx(x: list[float], lrc: float) -> tuple[list[float], list[float]]:
    """``exp(-exp(lrc) * x)`` and its forward-difference derivative in ``lrc`` (``numericDeriv``)."""
    expo = math.exp(lrc)
    g = [math.exp(-expo * xi) for xi in x]
    delta = abs(lrc) * _EPS if lrc != 0.0 else _EPS
    moved = lrc + delta
    expo_moved = math.exp(moved)
    gm = [math.exp(-expo_moved * xi) for xi in x]
    dg = [(b - a) / delta for a, b in zip(g, gm)]
    return g, dg


@dataclass(slots=True)
class _PlinearState:
    """``nlsModel.plinear`` at one value of ``lrc``."""

    lrc: float
    grad: np.ndarray  # (n, 2): the constant column has zero derivative
    qr: object
    lin: np.ndarray
    dev: float


def _plinear_at(lrc: float, x: list[float], y: np.ndarray) -> _PlinearState:
    n = len(x)
    g, dg = _ss_rhs_and_dx(x, lrc)
    rhs = np.empty((n, 2), dtype=np.float64, order="F")
    rhs[:, 0] = 1.0
    rhs[:, 1] = g
    grad = np.zeros((n, 2), dtype=np.float64, order="F")
    grad[:, 1] = dg
    qrobj = qr(rhs)
    if qrobj.rank < 2:
        raise ValueError(_NLS_SINGULAR)
    lin = qr_coef(qrobj, y)
    resid = qr_resid(qrobj, y)
    return _PlinearState(lrc=lrc, grad=grad, qr=qrobj, lin=lin, dev=ld_sum(resid * resid))


def _plinear_conv_incr(state: _PlinearState, y: np.ndarray, fac: float) -> tuple[float, float]:
    """``convCrit`` and ``incr`` of ``nlsModel.plinear`` (``p1 = 2``, one nonlinear parameter)."""
    qrobj = state.qr
    n = y.shape[0]
    cc = np.concatenate([np.zeros(2), qr_qty(qrobj, y)[2:]])
    rr = qr_qy(qrobj, cc)
    bvec = qr_qty(qrobj, dgemv(state.grad, state.lin))
    bvec = bvec.copy()
    bvec[0] = dgemv(state.grad[:, 0].reshape(1, n), rr)[0]
    bvec[1] = dgemv(state.grad[:, 1].reshape(1, n), rr)[0]
    rup = np.triu(qrobj.qr[:2, :2])
    low = rup.T
    x0 = bvec[0] / low[0, 0]
    b1 = bvec[1] - x0 * low[1, 0]
    x1 = b1 / low[1, 1]
    bvec[0] = x0
    bvec[1] = x1
    qb = qr(bvec.reshape(-1, 1))
    rr2 = qr_qty(qb, cc)
    s_top = ld_sum(rr2[:2] * rr2[:2])
    s_bottom = ld_sum(rr2[2:] * rr2[2:])
    conv = math.sqrt(fac * s_top / s_bottom)
    incr = float(qr_coef(qb, cc)[0])
    return conv, incr


def _lm_slope_lrc(xs: np.ndarray, ys: np.ndarray) -> float:
    """``log(-coef(lm(log(ydiff) ~ x))[[2]])`` for the start of ``lrc``."""
    design = np.empty((xs.shape[0], 2), dtype=np.float64, order="F")
    design[:, 0] = 1.0
    design[:, 1] = xs
    logy = np.array([math.log(v) for v in ys.tolist()], dtype=np.float64)
    slope = lm_fit_coef(design, logy)[1]
    return math.log(-slope)


def _ss_asymp_off_initial(x: np.ndarray, y: np.ndarray, tol: float = 1e-5, min_factor: float = 1.0 / 1024, maxiter: int = 50) -> dict[str, float]:
    """Starting values of ``SSasympOff`` (R's ``initial`` function), replayed step for step.

    ``sortedXyData``, ``NLSstRtAsymptote``, the ``lm`` slope for ``lrc``, then the
    ``plinear`` ``nls`` fit with the default control. That fit stops at R's
    convergence criterion, so its iterates are replayed as R takes them.
    """
    xs, ys = _sorted_xy_mean(np.asarray(x, dtype=np.float64), np.asarray(y, dtype=np.float64))
    rt = _rt_asymptote(ys)
    ydiff = np.abs(ys - rt)
    lrc0 = _lm_slope_lrc(xs, ydiff)
    fit = _plinear_fit(xs, ys, lrc0, tol=tol, min_factor=min_factor, maxiter=maxiter)
    lin = fit.lin
    asym = float(lin[0])
    c0 = math.exp(-fit.lrc) * math.log(-float(lin[1]) / asym)
    return {"Asym": asym, "lrc": float(fit.lrc), "c0": c0}


def _plinear_fit(
    xs: np.ndarray,
    ys: np.ndarray,
    lrc0: float,
    *,
    tol: float,
    min_factor: float,
    maxiter: int,
) -> _PlinearState:
    """``nls(..., algorithm = "plinear")``: the ``nls_iter`` loop of ``nls.c``."""
    x = [float(v) for v in xs.tolist()]
    n = len(x)
    fac_n = (n - 3) / 3.0
    state = _plinear_at(lrc0, x, ys)
    dev = state.dev
    fac = 1.0
    for _ in range(maxiter):
        conv, incr = _plinear_conv_incr(state, ys, fac_n)
        if conv <= tol:
            return state
        accepted = False
        while fac >= min_factor:
            trial = _plinear_at(state.lrc + fac * incr, x, ys)
            if trial.dev <= dev:
                dev = trial.dev
                state = trial
                fac = min(2.0 * fac, 1.0)
                accepted = True
                break
            fac /= 2.0
        if not accepted:
            break
    raise ValueError("number of iterations exceeded maximum of %d" % maxiter)


def _ss_asymp_off(x: np.ndarray, beta: np.ndarray) -> np.ndarray:
    """``SSasympOff`` value, in R's operation order."""
    asym, lrc, c0 = (float(v) for v in beta)
    expr1 = math.exp(lrc)
    out = np.empty(len(x), dtype=np.float64)
    for index, xi in enumerate(np.asarray(x, dtype=np.float64).tolist()):
        expr3 = xi - c0
        expr5 = math.exp((-expr1) * expr3)
        out[index] = asym * (1.0 - expr5)
    return out


def _ss_asymp_off_gradient(x: np.ndarray, beta: np.ndarray) -> np.ndarray:
    """``SSasympOff`` gradient columns ``(Asym, lrc, c0)``, in R's operation order."""
    asym, lrc, c0 = (float(v) for v in beta)
    expr1 = math.exp(lrc)
    out = np.empty((len(x), 3), dtype=np.float64)
    for index, xi in enumerate(np.asarray(x, dtype=np.float64).tolist()):
        expr3 = xi - c0
        expr5 = math.exp((-expr1) * expr3)
        expr6 = 1.0 - expr5
        out[index, 0] = expr6
        out[index, 1] = asym * (expr5 * (expr1 * expr3))
        out[index, 2] = -(asym * (expr5 * expr1))
    return out


@dataclass(slots=True)
class _NlsState:
    """``nlsModel`` at one parameter vector: residuals, deviance, and the QR of the gradient."""

    beta: np.ndarray
    resid: np.ndarray
    dev: float
    qr: object


def _nls_at(beta: np.ndarray, x: np.ndarray, y: np.ndarray) -> _NlsState:
    rhs = _ss_asymp_off(x, beta)
    gradient = _ss_asymp_off_gradient(x, beta)
    resid = y - rhs
    qrobj = qr(gradient)
    if qrobj.rank < 3:
        raise ValueError(_NLS_SINGULAR)
    return _NlsState(beta=beta.copy(), resid=resid, dev=ld_sum(resid * resid), qr=qrobj)


def _nls_iterate(
    x: np.ndarray,
    y: np.ndarray,
    start: np.ndarray,
    *,
    maxiter: int,
    tol: float,
    min_factor: float,
) -> tuple[_NlsState, int, float]:
    """``nls_iter`` for the ``SSasympOff`` model. Returns ``(state, finIter, finTol)``."""
    state = _nls_at(np.asarray(start, dtype=np.float64), x, y)
    dev = state.dev
    fac = 1.0
    conv_new = -1.0
    for iteration in range(maxiter):
        conv_new = _nls_conv(state)
        if conv_new <= tol:
            return state, iteration, conv_new
        incr = qr_coef(state.qr, state.resid)
        accepted = False
        while fac >= min_factor:
            trial = _nls_at(state.beta + fac * incr, x, y)
            if trial.dev <= dev:
                dev = trial.dev
                state = trial
                fac = min(2.0 * fac, 1.0)
                accepted = True
                break
            fac /= 2.0
        if not accepted:
            raise ValueError("step factor %g reduced below 'minFactor' of %g" % (fac, min_factor))
    raise ValueError("number of iterations exceeded maximum of %d" % maxiter)


def _nls_conv(state: _NlsState) -> float:
    """``convCrit`` of ``nlsModel``: rotated residuals, ``scaleOffset = 0``."""
    rr = qr_qty(state.qr, state.resid)
    return math.sqrt(ld_sum(rr[:3] * rr[:3]) / ld_sum(rr[3:] * rr[3:]))


def _nls_ss_asymp_off(
    data: dict[str, list[Any]],
    spec: tuple[str, str, tuple[str, ...]],
    start,
    control: dict[str, float | int],
) -> NlsFit:
    response, covariate, param_names = spec
    y = np.asarray(data[response], dtype=np.float64)
    x = np.asarray(data[covariate], dtype=np.float64)
    maxiter = int(control["maxiter"])
    tol = float(control["tol"])
    min_factor = float(control["minFactor"])
    if start is None:
        # No start: nls uses the selfStart initial function of SSasympOff on this group.
        init = _ss_asymp_off_initial(x, y, tol=1e-5, min_factor=1.0 / 1024, maxiter=50)
        start_map = {name: init[key] for name, key in zip(param_names, ("Asym", "lrc", "c0"))}
    elif isinstance(start, dict):
        start_map = {key: float(start[key]) for key in param_names}
    else:
        start_map = {name: float(value) for name, value in zip(param_names, start, strict=False)}
    beta0 = np.array([start_map[name] for name in param_names], dtype=np.float64)
    state, fin_iter, fin_tol = _nls_iterate(x, y, beta0, maxiter=maxiter, tol=tol, min_factor=min_factor)
    coefficients = {name: float(state.beta[index]) for index, name in enumerate(param_names)}
    rdf = y.shape[0] - 3
    sigma = math.sqrt(state.dev / rdf)
    return NlsFit(coefficients=coefficients, sigma=sigma, converged=True, fin_iter=fin_iter, fin_tol=fin_tol)


def _formula_text(object) -> str:
    if isinstance(object, str) and "~" in object:
        return object.strip()
    if hasattr(object, "formula"):
        value = object.formula
        if isinstance(value, str) and "~" in value:
            return value.strip()
    raise ValueError("model must be a two-sided formula")


def _as_data_frame(data) -> dict[str, list[Any]]:
    if hasattr(data, "columns") and isinstance(data.columns, dict):
        return {key: list(values) for key, values in data.columns.items()}
    if isinstance(data, dict):
        return {key: list(values) for key, values in data.items()}
    raise TypeError("data must be a data frame")


def _is_grouped_data(data) -> bool:
    classes = getattr(data, "classes", None)
    return bool(classes and "groupedData" in classes)


def _get_groups_formula(formula: str, *, as_list: bool) -> str | list[str] | None:
    if "|" not in formula.split("~", 1)[1]:
        return None
    rhs = formula.split("~", 1)[1]
    group_side = _bar_rhs(rhs)
    one_sided = f"~{group_side.strip()}"
    if not as_list:
        return one_sided
    return [one_sided]


def _bar_rhs(rhs: str) -> str:
    depth = 0
    start = 0
    for index, char in enumerate(rhs):
        if char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
        elif char == "|" and depth == 0:
            start = index + 1
    return rhs[start:].strip()


def _get_groups(frame: dict[str, list[Any]], group_var: str) -> list[str]:
    return [str(item) for item in frame[group_var]]


def _group_level_order(data, groups: list[str]) -> tuple[str, ...]:
    levels = getattr(data, "group_levels", None)
    if levels:
        return tuple(str(level) for level in levels)
    seen: list[str] = []
    for value in groups:
        text = str(value)
        if text not in seen:
            seen.append(text)
    return tuple(seen)


def _length(value) -> int:
    if isinstance(value, (list, tuple)):
        return len(value)
    return 1


def _warn_err_list(
    val: list[tuple[str, NlsFit | BaseException]],
    *,
    warn: bool,
) -> list[tuple[str, NlsFit | BaseException]]:
    errs = [index for index, (_name, item) in enumerate(val) if isinstance(item, BaseException)]
    if not errs:
        return val
    if warn:
        warnings.warn(
            f"{len(errs)} nls fit(s) errored; see nlsList element(s) {errs}",
            UserWarning,
            stacklevel=3,
        )
    return val
