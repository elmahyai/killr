"""Penalized quasi-likelihood GLMM (MASS ``glmmPQL``)."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Mapping, Sequence

import numpy as np

from mass.addterm import _binomial_deviance, _qr_coef, _split_formula
from mass.errors import MassError
from nlme.lme_family import lme as nlme_lme
from nlme.varfixed import varFixed

_DBL_EPS = float(np.finfo(np.float64).eps)


@dataclass
class GlmmPQL:
    """``glmmPQL`` fit: ``lme``-like object with class ``glmmPQL``."""

    coefficients: np.ndarray
    fitted_values: np.ndarray
    sigma: float
    re_sd: float
    fixef: np.ndarray
    fixef_names: list[str]
    family: str
    call: dict[str, Any]
    dims: dict[str, Any]
    model_struct: dict[str, float]
    have_offset: bool = False
    classes: tuple[str, ...] = ("glmmPQL", "lme")
    loglik: float = math.nan


def glmmPQL(
    fixed: str,
    random: str,
    *,
    family: str | Mapping[str, Any] = "binomial",
    data: Mapping[str, Sequence[Any]],
    correlation: Any = None,
    weights: Sequence[float] | None = None,
    control: Any = None,
    niter: int = 10,
    verbose: bool = True,
    **kwargs: Any,
) -> GlmmPQL:
    """Fit a GLMM by penalized quasi-likelihood (repeated weighted ``lme``)."""
    del kwargs, control
    if correlation is not None:
        raise NotImplementedError("correlation structures are not implemented for glmmPQL")
    fam = _as_family(family)
    if fam.name != "binomial":
        raise NotImplementedError("only binomial family is implemented for glmmPQL")

    mf = _model_frame_glmm(fixed, random, data)
    n = len(mf["_row_order"])
    wts = np.ones(n, dtype=float) if weights is None else np.asarray(weights, dtype=float)
    if wts.shape[0] != n:
        raise MassError(f"'weights' has length {wts.shape[0]}, not {n}")

    x0, y0, names0, _ = _model_matrix_mixed(mf, fixed)
    fit0 = _glm_binomial_fit(x0, y0, prior=wts)
    w = fit0.prior_weights
    eta = fit0.linear_predictors.copy()
    off = fit0.offset
    zz = eta + fit0.residuals - off
    wz = fit0.irls_weights.copy()

    group_col = _random_group_column(random)
    groups = np.asarray([str(mf[group_col][i]) for i in range(n)], dtype=object)

    x_lme, _y_dummy, fix_names, _ = _model_matrix_mixed(mf, fixed)

    call = {
        "fixed": fixed,
        "random": random,
        "family": fam.name,
        "data": data,
    }

    fit_lme: _LmeFit | None = None
    for iteration in range(int(niter)):
        if verbose:
            print(f"iteration {iteration + 1}")
        invwt = 1.0 / wz
        fit_lme = _lme_pql_fit(
            zz,
            x_lme,
            groups,
            invwt,
            fix_names,
        )
        etaold = eta.copy()
        eta = fit_lme.fitted + off
        if float(np.sum((eta - etaold) ** 2)) < 1e-6 * float(np.sum(eta**2)):
            break
        mu = _linkinv_binomial(eta)
        mu_eta = _mu_eta_binomial(eta)
        zz = eta + (fit0.y - mu) / mu_eta - off
        wz = w * (mu_eta**2) / (mu * (1.0 - mu))
    if fit_lme is None:
        raise MassError("glmmPQL failed to fit")

    dims = {
        "N": n,
        "Q": 1,
        "qvec": np.array([[1.0, 0.0, 0.0]]),
        "ngrps": np.array([len(np.unique(groups)), 1, 1]),
        "ncol": np.array([[1, x_lme.shape[1], 1]]),
    }
    return GlmmPQL(
        coefficients=fit_lme.random_effects,
        fitted_values=fit_lme.fitted,
        sigma=float(fit_lme.sigma),
        re_sd=float(fit_lme.re_sd),
        fixef=fit_lme.fixef,
        fixef_names=fix_names,
        family=fam.name,
        call=call,
        dims=dims,
        model_struct={"reStruct.ID": float(fit_lme.re_sd)},
        have_offset=bool(np.any(off != 0)),
    )


def fixef(object: GlmmPQL) -> np.ndarray:
    """Population fixed effects (``fixef.glmmPQL`` / ``fixef.lme``)."""
    return np.asarray(object.fixef, dtype=float)


def fitted(object: GlmmPQL) -> np.ndarray:
    """Fitted values on the link scale."""
    return np.asarray(object.fitted_values, dtype=float)


def coef_model_struct(object: GlmmPQL) -> dict[str, float]:
    """Random-effects standard deviation(s) (``coef(modelStruct)``)."""
    return dict(object.model_struct)


@dataclass
class _GlmBinomialFit:
    y: np.ndarray
    prior_weights: np.ndarray
    linear_predictors: np.ndarray
    residuals: np.ndarray
    irls_weights: np.ndarray
    offset: np.ndarray


@dataclass
class _LmeFit:
    fitted: np.ndarray
    fixef: np.ndarray
    sigma: float
    re_sd: float
    random_effects: np.ndarray


@dataclass
class _Family:
    name: str


def _as_family(family: str | Mapping[str, Any]) -> _Family:
    if isinstance(family, str):
        name = family
    elif isinstance(family, Mapping):
        name = str(family.get("family", family.get("name", "")))
    else:
        name = str(getattr(family, "family", family))
    if name != "binomial":
        raise MassError("'family' not recognized")
    return _Family(name=name)


def _random_group_column(random: str) -> str:
    text = random.strip()
    if "|" not in text:
        raise MassError("random formula must include '|'")
    rhs = text.split("|", 1)[1].strip()
    return rhs.split()[0]


def _model_frame_glmm(fixed: str, random: str, data: Mapping[str, Sequence[Any]]) -> dict[str, list[Any]]:
    vars_needed: set[str] = set()
    resp, rhs = _split_formula(fixed)
    vars_needed.add(resp)
    vars_needed.update(_all_vars_formula(rhs))
    vars_needed.update(_all_vars_formula(random.split("|", 1)[0]))
    if "|" in random:
        vars_needed.add(_random_group_column(random))
    mf: dict[str, list[Any]] = {}
    n: int | None = None
    for name in sorted(vars_needed):
        if name not in data:
            raise MassError(f"object '{name}' not found")
        col = data[name]
        if isinstance(col, Mapping) and "values" in col:
            col_list = list(col["values"])
            stored: Any = col
        elif isinstance(col, str):
            col_list = [col]
            stored = col_list
        else:
            col_list = list(col)
            stored = col_list
        if n is None:
            n = len(col_list)
        elif len(col_list) != n:
            raise MassError(f"variable '{name}' was created with size {len(col_list)}, not {n}")
        mf[name] = stored
    mf["_row_order"] = list(range(n or 0))
    return mf


def _all_vars_formula(rhs: str) -> list[str]:
    text = rhs.replace("~", " ").strip()
    out: list[str] = []
    token = ""
    depth = 0
    for ch in text:
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth = max(depth - 1, 0)
        elif ch in "+*" and depth == 0:
            name = token.strip()
            if name and not name.startswith("I("):
                out.extend(_vars_from_term(name))
            token = ""
            continue
        token += ch
    name = token.strip()
    if name and not name.startswith("I("):
        out.extend(_vars_from_term(name))
    else:
        inner = _i_inner(name)
        if inner:
            out.extend(_vars_from_token(inner))
    return out


def _vars_from_term(term: str) -> list[str]:
    return _vars_from_token(term)


def _vars_from_token(token: str) -> list[str]:
    for op in (">", "<", ":", "*", "-", "+", "="):
        if op in token:
            parts = [p.strip() for p in token.replace(">", " > ").replace("<", " < ").split()]
            return [p for p in parts if p.isidentifier()]
    return [token] if token.isidentifier() else []


def _i_inner(term: str) -> str | None:
    text = term.strip()
    if text.startswith("I(") and text.endswith(")"):
        return text[2:-1].strip()
    return None


def _model_matrix_mixed(
    mf: Mapping[str, Sequence[Any]],
    formula: str,
) -> tuple[np.ndarray, np.ndarray, list[str], list[str]]:
    resp, rhs = _split_formula(formula)
    if resp not in mf:
        raise MassError(f"object '{resp}' not found")
    y_raw = mf[resp]
    if isinstance(y_raw, str):
        y_raw = [y_raw]
    y_list = list(y_raw)
    n = len(y_list)
    if resp == "y":
        y = np.array([1.0 if str(v) in {"y", "1", "TRUE", "True", "true"} or v == 1 else 0.0 for v in y_list])
    else:
        y = np.asarray(y_list, dtype=float).reshape(-1)

    intercept = True
    terms: list[str] = []
    for raw in rhs.split("+"):
        piece = raw.strip()
        if not piece:
            continue
        if piece in {"0", "-1"}:
            intercept = False
        elif piece not in {"1"}:
            terms.append(piece)

    columns: list[np.ndarray] = []
    names: list[str] = []
    if intercept:
        columns.append(np.ones(n))
        names.append("(Intercept)")
    for term in terms:
        if term.startswith("I("):
            inner = _i_inner(term)
            if inner is None:
                raise MassError(f"could not parse {term}")
            col = _eval_i(inner, mf, n)
            columns.append(col)
            names.append(f"{term.replace(' ', '')}TRUE")
            continue
        col_list, levels = _column_as_list(mf, term)
        if all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in col_list):
            columns.append(np.asarray(col_list, dtype=float).reshape(-1))
            names.append(term)
        else:
            for level in levels[1:]:
                dummy = np.array([1.0 if str(col_list[i]) == level else 0.0 for i in range(n)])
                columns.append(dummy)
                names.append(f"{term}{level}")
    x = np.column_stack(columns) if columns else np.empty((n, 0))
    return x, y, names, terms


def _eval_i(inner: str, mf: Mapping[str, Sequence[Any]], n: int) -> np.ndarray:
    text = inner.replace(" ", "")
    if ">" in text:
        left, right = text.split(">", 1)
        a = np.asarray(mf[left.strip()], dtype=float).reshape(-1)
        b = float(right)
        return (a > b).astype(float)
    if "<" in text:
        left, right = text.split("<", 1)
        a = np.asarray(mf[left.strip()], dtype=float).reshape(-1)
        b = float(right)
        return (a < b).astype(float)
    raise MassError(f"unsupported I() expression: {inner}")


def _column_as_list(mf: Mapping[str, Sequence[Any]], name: str) -> tuple[list[Any], list[str]]:
    col_raw = mf[name]
    if isinstance(col_raw, Mapping) and "values" in col_raw:
        values = list(col_raw["values"])
        if "levels" in col_raw:
            levels = [str(v) for v in col_raw["levels"]]
        else:
            levels = _factor_levels([str(v) for v in values])
        return values, levels
    if isinstance(col_raw, str):
        col_raw = [col_raw]
    values = list(col_raw)
    return values, _factor_levels([str(v) for v in values])


def _factor_levels(values: list[str]) -> list[str]:
    seen: dict[str, None] = {}
    for item in values:
        seen[str(item)] = None
    return list(seen.keys())


def _glm_binomial_fit(x: np.ndarray, y: np.ndarray, *, prior: np.ndarray, maxit: int = 25) -> _GlmBinomialFit:
    n = x.shape[0]
    off = np.zeros(n)
    mu = (prior * y + 0.5) / (prior + 1.0)
    coef = np.zeros(x.shape[1])
    dev = math.inf
    irls_weights = np.ones(n)
    for _ in range(maxit):
        mu = np.clip(mu, 1e-12, 1 - 1e-12)
        mu_eta = mu * (1.0 - mu)
        variance = mu * (1.0 - mu)
        irls_weights = prior * (mu_eta**2) / variance
        working = (y - mu) / mu_eta
        eta = np.log(mu / (1.0 - mu))
        z = eta - off + working
        scale = np.sqrt(irls_weights)
        coef, _rank = _qr_coef(x * scale[:, None], z * scale)
        eta = x @ coef + off
        mu = 1.0 / (1.0 + np.exp(-eta))
        dev_new = float(np.sum(prior * _binomial_deviance(y, mu)))
        if abs(dev - dev_new) / (0.1 + abs(dev_new)) < 1e-8:
            dev = dev_new
            break
        dev = dev_new
    residuals = (y - mu) / np.clip(mu * (1.0 - mu), _DBL_EPS, None)
    return _GlmBinomialFit(
        y=y,
        prior_weights=prior,
        linear_predictors=eta,
        residuals=residuals,
        irls_weights=irls_weights,
        offset=off,
    )


def _linkinv_binomial(eta: np.ndarray) -> np.ndarray:
    """R's ``binomial()$linkinv`` (logit): ``x / (1 + x)`` with the eta cutoffs."""
    eta = np.asarray(eta, dtype=float)
    tmp = np.where(eta < -30.0, _DBL_EPS, np.where(eta > 30.0, 1.0 / _DBL_EPS, np.exp(eta)))
    return tmp / (1.0 + tmp)


def _mu_eta_binomial(eta: np.ndarray) -> np.ndarray:
    """R's ``binomial()$mu.eta`` (logit)."""
    eta = np.asarray(eta, dtype=float)
    opexp = 1.0 + np.exp(eta)
    return np.where((eta > 30.0) | (eta < -30.0), _DBL_EPS, np.exp(eta) / (opexp * opexp))


@dataclass
class _LmeWeightedFrame:
    """Minimal data object for ``nlme.lme_family.lme``: named columns and the group levels."""

    columns: dict[str, np.ndarray]
    group_levels: tuple[str, ...]


def _lme_pql_fit(
    zz: np.ndarray,
    x: np.ndarray,
    groups: np.ndarray,
    invwt: np.ndarray,
    fix_names: list[str],
) -> _LmeFit:
    """Inner ``lme(zz ~ -1 + X, random = ~1 | ID, weights = varFixed(~invwt), method = "ML")``.

    ``nlme.lme_family.lme`` takes the ``varFixed`` weights directly, as R's
    ``lme`` does, so the columns are passed unscaled.
    """
    del fix_names
    zz = np.asarray(zz, dtype=float).reshape(-1)
    invwt = np.asarray(invwt, dtype=float).reshape(-1)
    groups = np.asarray(groups, dtype=object)

    columns: dict[str, np.ndarray] = {
        "zz": zz,
        "invwt": invwt,
        "grp": groups,
    }
    fixed_terms: list[str] = []
    for j in range(x.shape[1]):
        name = f"xw{j}"
        columns[name] = x[:, j]
        fixed_terms.append(name)
    levels = tuple(sorted({str(g) for g in groups}))
    frame = _LmeWeightedFrame(columns=columns, group_levels=levels)
    fit = nlme_lme(
        f"zz ~ -1 + {' + '.join(fixed_terms)}",
        frame,
        random="~ 1 | grp",
        weights=varFixed("~invwt"),
        method="ML",
    )
    # fit.fitted has one column per level (level 0 = fixed part, level 1 = group).
    fitted = np.asarray(fit.fitted, dtype=float)[:, -1]
    random_effects = np.asarray(fit.random["grp"], dtype=float).reshape(-1)
    # nlme's lme stores the log-Cholesky parameter with the opposite sign to R's
    # coef(modelStruct), which is log(sd / sigma).
    re_sd = -float(np.asarray(fit.model_parameters, dtype=float).reshape(-1)[0])
    return _LmeFit(
        fitted=fitted,
        fixef=np.asarray(fit.fixed, dtype=float).reshape(-1),
        sigma=float(fit.sigma),
        re_sd=re_sd,
        random_effects=random_effects,
    )
