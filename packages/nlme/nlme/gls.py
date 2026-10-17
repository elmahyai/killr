"""Fit a linear model with correlated errors and/or heteroscedasticity (nlme ``gls``).

Translated path: no ``correlation`` and no ``weights``, which are the defaults.
With no parameter to optimize, R's ``gls`` calls ``glsEstimate`` once and the
approximate variance-covariance is ``NULL``. That path matches R within 1e-8.

Structure path (``correlation`` or ``weights`` given): R minimizes the negative
log-likelihood over the structure parameters with ``nlminb``, which runs the
PORT library. This module runs that outer loop with ``nlminb_port`` (crate
``crates/nlminb_port``, R 4.5.0 ``portsrc.f`` without a gradient), the same
driver R's ``nlminb`` uses, so the iterates follow R's.
"""

from __future__ import annotations

import copy
import math
from dataclasses import dataclass, replace
from typing import Any

import formulaic
import numpy as np
import nlmegls
from nlminb_port import nlminb_port
from nlme.conlin import ConLin
from nlme.corar1 import CorAR1
from nlme.corstruct import _group_var_name
from nlme.cornatural import CorNatural
from nlme.corsymm import CorSymm
from nlme.glscontrol import glsControl
from nlme.getcovariateformula import getCovariateFormula
from nlme.glsapvar import (
    GlsApVarMatrix,
    coef_vector,
    glsApVar,
    parameter_map,
    set_coef as set_structure_coef,
)
from nlme.glsestimate import GlsEstimate, glsEstimate
from nlme.glsstruct import GlsStruct
from nlme.initialize import Initialize
from nlme.recalc import recalc
from nlme.varconstpower import _get_groups_formula
from nlme.var_power import VarPower

__all__ = ["GlsObject", "gls"]


@dataclass(slots=True)
class GlsObject:
    """The ``gls`` object: the fields of R's list plus the ``modelStruct`` attributes."""

    modelStruct: GlsStruct
    dims: dict
    coefficients: np.ndarray
    coef_names: tuple[str, ...]
    varBeta: np.ndarray
    sigma: float
    apVar: GlsApVarMatrix | str | None
    logLik: float
    numIter: int
    fitted: np.ndarray
    residuals: np.ndarray
    method: str
    fixedSigma: bool


@dataclass(slots=True)
class _StructureInputs:
    """Sorted data, initialized structure, and condensed linear model for a structure fit."""

    gls_st: GlsStruct
    con_lin: ConLin
    order: np.ndarray
    names: tuple[str, ...]
    n: int
    p: int
    reml: int
    fixed_sigma: bool


def _r_column_name(name: str) -> str:
    """formulaic names ``Sex[T.Female]``; R names the same column ``SexFemale``."""
    if name == "Intercept":
        return "(Intercept)"
    if name.endswith("]") and "[T." in name:
        base, level = name[:-1].split("[T.", 1)
        return base + level
    return name


def _model_matrices(model: str, data: Any) -> tuple[np.ndarray, np.ndarray, tuple[str, ...], str]:
    """``model.frame`` and ``model.matrix``: response, design, names, and response name."""
    mm = formulaic.model_matrix(model, data, na_action="raise")
    lhs = mm.lhs
    rhs = mm.rhs
    if lhs is None or len(lhs.columns) != 1:
        raise ValueError('model must be a formula of the form "resp ~ pred"')
    y = np.asarray(lhs, dtype=np.float64).reshape(-1)
    x = np.asarray(rhs, dtype=np.float64)
    names = tuple(_r_column_name(str(c)) for c in rhs.columns)
    return y, x, names, str(lhs.columns[0])


def _group_name(form: Any) -> str | None:
    """Group variable of a structure formula ``~ 1 | g``, or ``None`` when ungrouped."""
    grp = _get_groups_formula(str(form))
    return None if grp is None else _group_var_name(grp)


def _group_order(frame: Any, name: str) -> np.ndarray:
    """Stable row order by group, as R's ``order(grps)``.

    The keys are the sorted unique labels, the same order the Python ``Dim``
    computation uses for the group blocks, so row blocks and ``Dim`` agree.
    """
    values = np.asarray(frame[name], dtype=object)
    _, codes = np.unique(values, return_inverse=True)
    return np.argsort(codes, kind="stable")


def _initialized_components(
    correlation: Any, weights: Any, frame: dict[str, Any], n: int
) -> dict[str, Any]:
    """``glsStruct(corStruct, varStruct)`` with each non-NULL component initialized on the column mapping ``frame``."""
    components: dict[str, Any] = {}
    if correlation is not None:
        if not isinstance(correlation, (CorAR1, CorNatural, CorSymm)):
            raise NotImplementedError(
                f"gls correlation {type(correlation).__name__} is not translated; "
                "the structure path covers corAR1, corNatural and corSymm"
            )
        components["corStruct"] = Initialize(copy.copy(correlation), frame)
    if weights is not None:
        if not isinstance(weights, VarPower):
            raise NotImplementedError(
                f"gls weights {type(weights).__name__} is not translated; the structure path covers varPower"
            )
        init = Initialize(copy.copy(weights), frame)
        if init.need_update:
            # R: Initialize.varPower takes NextMethod(), so Initialize.varFunc sets
            # weights rep(1, N) and logLik 0 until update() supplies the covariate.
            init = replace(init, weights=np.ones(n, dtype=np.float64), log_lik=0.0)
        components["varStruct"] = init
    return components


def _need_update(gls_st: GlsStruct) -> bool:
    """``needUpdate(glsSt)``: a varPower whose covariate is fitted(.) stays TRUE after Initialize."""
    return any(
        isinstance(comp, VarPower) and bool(comp.need_update) for comp in gls_st.components.values()
    )


def _update_structure(gls_st: GlsStruct, fitted: np.ndarray) -> GlsStruct:
    """``update(glsSt, data)``: a fitted(.) covariate takes the fitted values, in sorted-row order.

    R's ``update.varPower`` only sets the covariate; the weights are recomputed by
    the next ``coef<-``, so they stay as they were until then.
    """
    components = dict(gls_st.components)
    for name, comp in gls_st.components.items():
        if isinstance(comp, VarPower) and comp.need_update:
            rhs = getCovariateFormula(comp.formula).text.lstrip("~").replace(" ", "")
            if rhs != "fitted(.)":
                raise NotImplementedError(
                    f"gls update() of varPower covariate {rhs!r} is not translated; only fitted(.)"
                )
            components[name] = replace(
                comp, covariate=np.asarray(fitted, dtype=np.float64).reshape(-1).copy()
            )
    return replace(gls_st, components=components)


def _structure_inputs(
    model: str,
    data: Any,
    correlation: Any,
    weights: Any,
    reml: bool,
    controlvals: dict,
) -> _StructureInputs:
    """R's ``gls`` setup before the optimizer: sort by group, build X and y, initialize the structure."""
    if not hasattr(data, "iloc"):
        raise TypeError("gls with a correlation or weights structure needs a pandas DataFrame as data")
    order = np.arange(len(data))
    group_name = _group_name(correlation.formula) if correlation is not None else None
    if group_name is not None:
        order = _group_order(data, group_name)
    frame = data.iloc[order].reset_index(drop=True)
    y, x, names, response = _model_matrices(model, frame)
    n, p = x.shape
    if p == 0:
        raise ValueError("no coefficients to fit")
    sigma_ctrl = float(controlvals["sigma"])
    fixed_sigma = sigma_ctrl > 0
    columns = {str(c): np.asarray(frame[c]) for c in frame.columns}
    gls_st = GlsStruct(
        components=_initialized_components(correlation, weights, columns, n),
        fixedSigma=fixed_sigma,
    )
    con_lin = ConLin(
        Xy=np.column_stack([x, y]),
        dims={"N": n, "p": p, "REML": int(reml)},
        logLik=0.0,
        sigma=sigma_ctrl,
        fixedSigma=fixed_sigma,
        names=names + (response,),
    )
    return _StructureInputs(gls_st, con_lin, order, names, n, p, int(reml), fixed_sigma)


def _optimize_once(
    gls_st: GlsStruct, inputs: _StructureInputs, controlvals: dict
) -> tuple[GlsStruct, int, str]:
    """One ``nlminb(coef(glsSt), -logLik(glsSt, glsPars), control = list(iter.max = msMaxIter))``.

    ``logLik.glsStruct`` passes the recalculated ``conLin$logLik`` into the kernel
    as its starting value, so the subtraction order matches R's. Parameters are
    the unconstrained ``coef(glsSt)``, with the same start values R uses. Returns
    the new structure with the convergence code and message; R checks the code
    only once the structure needs no update.
    """
    start = coef_vector(gls_st)
    sigma = float(inputs.con_lin.sigma)

    def neg_log_lik(pars) -> float:
        trial = set_structure_coef(gls_st, np.asarray(pars, dtype=np.float64))
        con = recalc(trial, inputs.con_lin)
        xy = np.asarray(con.Xy, dtype=np.float64).reshape(-1, order="F")
        log_lik, _lrss = nlmegls.gls_loglik(
            xy.tolist(), int(inputs.n), int(inputs.p), int(inputs.reml), float(con.logLik), 0.0, sigma
        )
        return -float(log_lik)

    fit = nlminb_port(
        neg_log_lik,
        [float(v) for v in start],
        control={"iter.max": int(controlvals["msMaxIter"])},
    )
    new_st = set_structure_coef(gls_st, np.asarray(fit["par"], dtype=np.float64))
    return new_st, int(fit["convergence"]), str(fit["message"])


def _fit_structure(
    inputs: _StructureInputs, controlvals: dict
) -> tuple[GlsStruct, GlsEstimate, int]:
    """R's ``gls`` setup and repeat loop: Initialize, then optimize until no update is needed or converged.

    Returns the structure, its last ``glsEstimate``, and ``numIter``. ``numIter`` is
    reported only while the structure still needs an update, as R does.
    """
    singular_ok = bool(controlvals["singular.ok"])
    p = inputs.p
    gls_st = inputs.gls_st
    # Initialize.glsStruct: glsEstimate on the initialized plug-ins, then update() if needed.
    gls_fit = glsEstimate(gls_st, inputs.con_lin, singular_ok=singular_ok)
    if _need_update(gls_st):
        gls_st = _update_structure(gls_st, gls_fit.fitted)
    num_iter = 0
    while True:
        old_pars = np.concatenate([np.asarray(gls_fit.beta, dtype=np.float64), coef_vector(gls_st)])
        if coef_vector(gls_st).size:
            gls_st, conv_code, message = _optimize_once(gls_st, inputs, controlvals)
        else:
            conv_code, message = 0, ""
        gls_fit = glsEstimate(gls_st, inputs.con_lin, singular_ok=singular_ok)
        if not _need_update(gls_st):
            if conv_code != 0:
                raise RuntimeError(message)
            break
        num_iter += 1
        gls_st = _update_structure(gls_st, gls_fit.fitted)
        new_pars = np.concatenate([np.asarray(gls_fit.beta, dtype=np.float64), coef_vector(gls_st)])
        denom = np.where(new_pars == 0, 1.0, new_pars)
        conv = np.abs((old_pars - new_pars) / denom)
        a_conv = [float(np.max(conv[:p]))]
        rest = conv[p:]
        pmap = parameter_map(gls_st)
        for col in range(pmap.shape[1]):
            mask = pmap[:, col]
            if np.any(mask):
                a_conv.append(float(np.max(rest[mask])))
        if max(a_conv) <= float(controlvals["tolerance"]):
            break
        if num_iter > float(controlvals["maxIter"]):
            raise RuntimeError("maximum number of iterations reached without convergence")
    return gls_st, gls_fit, (num_iter if _need_update(gls_st) else 0)


def _gls_structure(
    model: str,
    data: Any,
    correlation: Any,
    weights: Any,
    reml: bool,
    controlvals: dict,
) -> GlsObject:
    """``gls`` with a correlation and/or weights structure, using ``nlminb_port`` for the outer loop."""
    if controlvals["opt"] != "nlminb":
        raise NotImplementedError('gls control opt="optim" is not translated; only nlminb is translated')
    inputs = _structure_inputs(model, data, correlation, weights, reml, controlvals)
    gls_st, gls_fit, num_iter = _fit_structure(inputs, controlvals)
    n, p = inputs.n, inputs.p
    sigma_out = float(inputs.con_lin.sigma) if inputs.fixed_sigma else gls_fit.sigma
    # R: varBetaFact <- sigma * varBeta * sqrt((N - REML * p) / (N - p)); varBeta <- crossprod(varBetaFact)
    fact = (gls_fit.sigma * gls_fit.varBeta) * math.sqrt((n - inputs.reml * p) / (n - p))
    var_beta = np.asarray(fact.T @ fact, dtype=np.float64)
    # R sorts the rows by group, then restores the original order for fitted and residuals.
    back = np.argsort(inputs.order)
    fitted = np.asarray(gls_fit.fitted, dtype=np.float64)[back]
    resid = np.asarray(gls_fit.resid, dtype=np.float64)[back]
    if controlvals["apVar"]:
        ap_var = glsApVar(
            gls_st,
            gls_fit.sigma,
            inputs.con_lin,
            relStep=controlvals[".relStep"],
            minAbsPar=controlvals["minAbsParApVar"],
            natural=controlvals["natural"],
        )
    else:
        ap_var = "Approximate variance-covariance matrix not available"
    return GlsObject(
        modelStruct=gls_st,
        dims={"N": n, "p": p, "REML": inputs.reml},
        coefficients=gls_fit.beta,
        coef_names=gls_fit.names,
        varBeta=var_beta,
        sigma=sigma_out,
        apVar=ap_var,
        logLik=gls_fit.logLik,
        numIter=num_iter,
        fitted=fitted,
        residuals=resid,
        method="REML" if inputs.reml else "ML",
        fixedSigma=inputs.fixed_sigma,
    )


def gls(
    model: str,
    data: Any,
    correlation: Any = None,
    weights: Any = None,
    subset: Any = None,
    method: str = "REML",
    na_action: str = "fail",
    control: dict | None = None,
    verbose: bool = False,
) -> GlsObject:
    """Fit ``model`` by generalized least squares.

    The no-structure path is translated. A ``correlation`` (corAR1, corNatural) or
    ``weights`` (varPower) is fitted with ``nlminb_port``; see the module docstring.
    """
    del verbose
    if subset is not None:
        raise NotImplementedError("gls subset= is not translated")
    if na_action != "fail":
        raise NotImplementedError("gls na.action other than na.fail is not translated")
    if method not in ("REML", "ML"):
        raise ValueError("method must be REML or ML")
    reml = method == "REML"
    controlvals = glsControl(**(control or {}))
    if correlation is not None or weights is not None:
        return _gls_structure(model, data, correlation, weights, reml, controlvals)
    sigma_ctrl = float(controlvals["sigma"])
    y, x, names, response = _model_matrices(model, data)
    n, p = x.shape
    if p == 0:
        raise ValueError("no coefficients to fit")
    fixed_sigma = sigma_ctrl > 0
    con_lin = ConLin(
        Xy=np.column_stack([x, y]),
        dims={"N": n, "p": p, "REML": int(reml)},
        logLik=0.0,
        sigma=sigma_ctrl,
        fixedSigma=fixed_sigma,
        names=names + (response,),
    )
    gls_st = GlsStruct(components={}, fixedSigma=fixed_sigma)
    gls_fit = glsEstimate(gls_st, con_lin, singular_ok=bool(controlvals["singular.ok"]))
    sigma_out = sigma_ctrl if fixed_sigma else gls_fit.sigma
    # R: varBetaFact <- sigma * varBeta * sqrt((N - REML * p) / (N - p)); varBeta <- crossprod(varBetaFact)
    fact = (gls_fit.sigma * gls_fit.varBeta) * math.sqrt((n - int(reml) * p) / (n - p))
    var_beta = np.asarray(fact.T @ fact, dtype=np.float64)
    fitted = gls_fit.fitted
    resid = y - fitted
    if controlvals["apVar"]:
        ap_var = glsApVar(
            gls_st,
            gls_fit.sigma,
            con_lin,
            relStep=controlvals[".relStep"],
            minAbsPar=controlvals["minAbsParApVar"],
            natural=controlvals["natural"],
        )
    else:
        ap_var = "Approximate variance-covariance matrix not available"
    return GlsObject(
        modelStruct=gls_st,
        dims={"N": n, "p": p, "REML": int(reml)},
        coefficients=gls_fit.beta,
        coef_names=gls_fit.names,
        varBeta=var_beta,
        sigma=float(sigma_out),
        apVar=ap_var,
        logLik=gls_fit.logLik,
        numIter=0,
        fitted=fitted,
        residuals=resid,
        method=method,
        fixedSigma=fixed_sigma,
    )
