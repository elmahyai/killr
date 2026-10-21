"""clmm for ordinal 2026.7-26: cumulative link mixed models with one simple random effect.

Ports the single-term ``(1 | g)`` path of clmm(): the formula split (clmm.formulae,
getREterms with ssr = TRUE), set.AGQ with gauss.hermite, rho.clm2clmm.ssr,
clmm.fit.ssr, nllBase.uC, update.uC, getNLA.ssr, getNAGQ.ssr, getNGHQ.ssr,
clmm.finalize, and deriv12 for the gradient and Hessian.

The inner Newton-Raphson for the random-effect modes and the quadrature sums run
in crates/ordinal_clmm (C from ordinal src/utilityFuns.c). The outer optimizer is
nlminb_port (crates/nlminb_port, R's PORT library without a gradient). The
fixed-effect starting values come from clm_fit, the clm.fit port.

Not yet ported: more than one random-effect term, slopes, and nested or crossed
factors. Those use the sparse Matrix path, and Matrix is not in registry.json.
Also not ported: useMatrix = TRUE, method = "ucminf", offset(), flexible links,
and clmm2.

Data is a mapping from column name to a sequence of values, as in clm(). The
grouping factor's levels are sorted as strings unless ``levels`` gives them.
"""

from __future__ import annotations

import math
import re
import warnings
from typing import Any, Mapping, Sequence

import numpy as np
from nlminb_port import nlminb_port
import ordinal_clmm as _kern

from ordinal.clm import _split_response, _strip_tilde
from ordinal.clm_fit import clm_fit, clm_newrho, make_thresholds
from ordinal.clm_frames import _is_na, design_matrix, formula_variables, is_factor_values
from ordinal.control import clmm_control
from ordinal.drop_coef import _linpack_qr, drop_coef

_LINK_CODE = {"logit": 1, "probit": 2, "cloglog": 3, "loglog": 4, "cauchit": 5}
_BAR_TERM = re.compile(r"\(\s*1\s*\|\s*([A-Za-z_.][A-Za-z0-9_.]*)\s*\)")
_MESSAGES = {
    1: "max|gradient| < tol, so current iterate is probably solution",
    0: "Non finite negative log-likelihood",
    -1: "iteration limit reached when updating the random effects",
    -2: "step factor reduced below minimum when updating the random effects",
}


def _split_random(rhs: str) -> tuple[str, str]:
    """Fixed-effects right-hand side and the grouping variable of (1 | g)."""
    found = list(_BAR_TERM.finditer(rhs))
    if not found:
        if "|" in rhs:
            raise NotImplementedError(
                "only a single (1 | g) random-effect term is ported; other random-effect terms need the Matrix path"
            )
        raise ValueError("No random effects terms specified in formula")
    if len(found) != 1 or rhs.count("|") != 1:
        raise NotImplementedError(
            "only a single (1 | g) random-effect term is ported; several terms, slopes, and "
            "nested or crossed factors need the sparse Matrix path, which is not in registry.json"
        )
    m = found[0]
    fixed = f"{rhs[: m.start()]} {rhs[m.end():]}".strip()
    fixed = re.sub(r"\+\s*\+", "+", fixed)
    fixed = re.sub(r"^\s*\+\s*|\s*\+\s*$", "", fixed).strip()
    return (fixed or "1"), m.group(1)


def gauss_hermite(n: int) -> tuple[np.ndarray, np.ndarray]:
    """gauss.hermite(n): nodes (ascending) and weights from the Jacobi matrix.

    eigen(A, symmetric = TRUE) runs through the LAPACK dsyevr call in the
    ordinal_clmm crate, so the nodes and weights round as R's do.
    """
    n = int(n)
    if n < 0:
        raise ValueError("need non-negative number of nodes")
    if n == 0:
        return np.zeros(0), np.zeros(0)
    A = np.zeros((n, n))
    for k in range(1, n):
        b = math.sqrt(k / 2.0)
        A[k, k - 1] = b
        A[k - 1, k] = b
    values, vectors = _kern.eigen_sym(A.ravel(order="F").tolist(), n)
    first_row = np.asarray(vectors, dtype=float)[0::n]
    weights = np.array([math.sqrt(math.pi) * (w * w) for w in first_row])
    return np.asarray(values, dtype=float), weights


def _deriv12(fun, x: np.ndarray, delta: float = 1e-4) -> tuple[np.ndarray, np.ndarray]:
    """deriv12: central-difference gradient and Hessian."""
    nx = len(x)
    fx = fun(x)
    H = np.empty((nx, nx))
    g = np.zeros(nx)
    for j in range(nx):
        xadd = x.copy()
        xsub = x.copy()
        xadd[j] = x[j] + delta
        xsub[j] = x[j] - delta
        fadd = fun(xadd)
        fsub = fun(xsub)
        H[j, j] = (fadd - 2 * fx + fsub) / delta**2
        g[j] = (fadd - fsub) / (2 * delta)
        for i in range(j):
            xaa = x.copy()
            xas = x.copy()
            xsa = x.copy()
            xss = x.copy()
            xaa[[i, j]] = x[[i, j]] + np.array([delta, delta])
            xas[[i, j]] = x[[i, j]] + np.array([delta, -delta])
            xsa[[i, j]] = x[[i, j]] + np.array([-delta, delta])
            xss[[i, j]] = x[[i, j]] - np.array([delta, delta])
            H[i, j] = H[j, i] = (fun(xaa) - fun(xas) - fun(xsa) + fun(xss)) / (4 * delta**2)
    return g, H


def _grad_ctr(fun, x: np.ndarray, delta: float = 1e-4) -> np.ndarray:
    """grad.ctr: central-difference gradient."""
    out = np.zeros(len(x))
    for i in range(len(x)):
        xadd = x.copy()
        xsub = x.copy()
        xadd[i] = x[i] + delta
        xsub[i] = x[i] - delta
        out[i] = (fun(xadd) - fun(xsub)) / (2 * delta)
    return out


class _Ssr:
    """The rho environment for the single-term path (rho.clm2clmm.ssr)."""

    def __init__(self, *, B1, B2, o1, o2, wts, grFac, nalpha, nbeta, nrandom, ctrl, link):
        self.B1 = B1
        self.B2 = B2
        # Column-major copies, so B %*% par runs through the same dgemv as R.
        self.B1_flat = np.asarray(B1, dtype=float).ravel(order="F").tolist()
        self.B2_flat = np.asarray(B2, dtype=float).ravel(order="F").tolist()
        self.nrow = len(wts)
        self.o1 = o1
        self.o2 = o2
        self.wts = wts
        self.grFac = grFac
        self.sigma = np.ones(len(wts))
        self.nalpha = nalpha
        self.nbeta = nbeta
        self.ntau = 1
        self.nrandom = nrandom
        self.uStart = np.zeros(nrandom)
        self.u = np.zeros(nrandom)
        self.ctrl = ctrl
        self.linkInt = _LINK_CODE[link]
        self.lambda_ = 0.0
        self.Niter = 0
        self.neval = 0
        self.par = np.zeros(nalpha + nbeta + 1)
        self.tau = 1.0
        self.D = np.ones(nrandom)
        self.fitted = np.zeros(len(wts))
        self.negLogLik = math.inf
        self.gradient = np.zeros(nrandom)
        self.nAGQ = 1
        self.ghqns = np.zeros(0)
        self.ghqws = np.zeros(0)

    def set_agq(self, nAGQ: int) -> None:
        self.nAGQ = nAGQ
        if nAGQ in (0, 1):
            return
        nodes, weights = gauss_hermite(abs(nAGQ))
        self.ghqns = nodes
        self.ghqws = weights if nAGQ > 0 else np.log(weights) + nodes**2 / 2


def _nll_base(rho: _Ssr) -> None:
    """nllBase.uC: tau, eta1Fix and eta2Fix for the current par."""
    npsi = rho.nalpha + rho.nbeta
    rho.tau = math.exp(rho.par[npsi])
    head = rho.par[:npsi].tolist()
    rho.eta1Fix = np.asarray(_kern.matvec(rho.B1_flat, rho.nrow, npsi, head))
    rho.eta2Fix = np.asarray(_kern.matvec(rho.B2_flat, rho.nrow, npsi, head))


def _update_uC(rho: _Ssr) -> bool:
    """update.uC: inner Newton-Raphson for the modes of u (NRalgv3)."""
    _nll_base(rho)
    c = rho.ctrl["ctrl"]
    u, fitted, fun, grad, hess, max_grad, conv, niter = _kern.nr_inner(
        int(c["trace"]),
        int(c["maxIter"]),
        float(c["gradTol"]),
        int(c["maxLineIter"]),
        rho.grFac.tolist(),
        float(rho.tau),
        rho.o1.tolist(),
        rho.o2.tolist(),
        rho.eta1Fix.tolist(),
        rho.eta2Fix.tolist(),
        rho.sigma.tolist(),
        rho.linkInt,
        rho.wts.tolist(),
        rho.uStart.tolist(),
        rho.lambda_,
        int(rho.Niter),
    )
    message = _MESSAGES.get(conv, "unknown convergence code")
    if conv != 1 and rho.ctrl["ctrl"]["innerCtrl"] == "warnOnly":
        warnings.warn(f"{message}\n  at iteration {rho.Niter}", stacklevel=3)
    elif conv != 1 and rho.ctrl["ctrl"]["innerCtrl"] == "giveError":
        raise RuntimeError(f"{message}\n  at iteration {rho.Niter}")
    rho.Niter = niter
    rho.fitted = np.asarray(fitted)
    rho.u = np.asarray(u)
    rho.D = np.asarray(hess)
    rho.gradient = np.asarray(grad)
    rho.negLogLik = float(fun)
    return bool(math.isfinite(rho.negLogLik))


def _set_par(rho: _Ssr, par: np.ndarray) -> None:
    par = np.asarray(par, dtype=float)
    if not np.all(np.isfinite(par)):
        raise ValueError(f"Non-finite parameters occured: {par}")
    rho.par = par.copy()
    rho.neval += 1


def _get_nla(rho: _Ssr, par: np.ndarray) -> float:
    """getNLA.ssr: Laplace approximation to the negative log-likelihood."""
    _set_par(rho, par)
    if not _update_uC(rho):
        return math.inf
    if np.any(rho.D <= 0):
        return math.inf
    logdetD = _kern.sum_log(rho.D.tolist())
    return rho.negLogLik - rho.nrandom * math.log(2 * math.pi) / 2 + logdetD / 2


def _get_nagq(rho: _Ssr, par: np.ndarray) -> float:
    """getNAGQ.ssr: adaptive Gauss-Hermite negative log-likelihood."""
    _set_par(rho, par)
    if not _update_uC(rho):
        return math.inf
    if np.any(rho.D < 0):
        return math.inf
    return _kern.nagq(
        rho.grFac.tolist(),
        float(rho.tau),
        rho.eta1Fix.tolist(),
        rho.eta2Fix.tolist(),
        rho.o1.tolist(),
        rho.o2.tolist(),
        rho.sigma.tolist(),
        rho.wts.tolist(),
        rho.ghqns.tolist(),
        [math.log(x) for x in rho.ghqws.tolist()],
        (rho.ghqns**2).tolist(),
        rho.u.tolist(),
        rho.D.tolist(),
        int(abs(rho.nAGQ)),
        rho.linkInt,
        rho.lambda_,
    )


def _get_nghq(rho: _Ssr, par: np.ndarray) -> float:
    """getNGHQ.ssr: standard Gauss-Hermite negative log-likelihood."""
    _set_par(rho, par)
    _nll_base(rho)
    return _kern.ghq(
        rho.grFac.tolist(),
        float(rho.tau),
        rho.eta1Fix.tolist(),
        rho.eta2Fix.tolist(),
        rho.o1.tolist(),
        rho.o2.tolist(),
        rho.sigma.tolist(),
        rho.wts.tolist(),
        int(rho.nrandom),
        rho.ghqns.tolist(),
        rho.ghqws.tolist(),
        int(abs(rho.nAGQ)),
        rho.linkInt,
        (rho.ghqns * rho.tau).tolist(),
        rho.lambda_,
    )


def _check_ranef(q: int, n: int, all_ones: bool, mode: str) -> None:
    """test_no_ranef: random effects should be fewer than observations."""
    if q > n or (all_ones and q == n):
        msg = f"no. random effects (={q}) >= no. observations (={n}) for term: (1 | g)"
        if mode == "error":
            raise ValueError(msg)
        if mode == "message":
            print(msg)
        else:
            warnings.warn(msg, stacklevel=3)


def clmm(
    formula: str,
    data: Mapping[str, Sequence[Any]],
    *,
    weights: Sequence[float] | None = None,
    levels: Mapping[str, Sequence[str]] | None = None,
    link: str = "logit",
    threshold: str = "flexible",
    start: Sequence[float] | None = None,
    nAGQ: int = 1,
    control: dict[str, Any] | None = None,
    Hess: bool = True,
    do_fit: bool = True,
) -> dict[str, Any] | _Ssr:
    """clmm(formula, data, weights, start, link, threshold, nAGQ, control, Hess).

    formula: "response ~ fixed terms + (1 | group)". Returns a dict with the
    coefficients, the random-effect standard deviation ST, logLik, ranef, condVar,
    gradient and Hessian, as clmm() does.
    """
    if link in ("Aranda-Ordaz", "log-gamma"):
        raise NotImplementedError("flexible links need nlminb with bounds, which is not ported yet")
    if link not in _LINK_CODE:
        raise ValueError(f"unknown link: {link}")
    ctrl = clmm_control() if control is None else control
    if ctrl["method"] != "nlminb":
        raise NotImplementedError(f"method {ctrl['method']} is not ported yet; use nlminb")
    if ctrl["useMatrix"]:
        raise NotImplementedError("useMatrix = TRUE needs the sparse Matrix path, which is not in registry.json")
    nAGQ = int(round(nAGQ))

    resp, rhs = _split_response(formula)
    rhs = _strip_tilde(rhs)
    if "offset(" in rhs:
        raise NotImplementedError("offset() terms are not ported yet")
    fixed_rhs, group = _split_random(rhs)
    fixed_rhs = _strip_tilde(fixed_rhs)

    n = len(data[resp])
    needed = list(dict.fromkeys([resp] + formula_variables(fixed_rhs) + [group]))
    keep = np.ones(n, dtype=bool)
    for var in needed:
        keep &= np.array([not _is_na(v) for v in data[var]], dtype=bool)
    if weights is not None:
        w_all = np.asarray(weights, dtype=float)
        keep &= ~np.isnan(w_all)
        w_kept = w_all[keep]
    else:
        w_kept = np.ones(int(keep.sum()))
    sub = {var: [data[var][i] for i in range(n) if keep[i]] for var in needed}

    # wts > 0 only, as clmm() works on fullmf[wts > 0, ].
    pos = w_kept > 0
    w = w_kept[pos]
    sub = {var: [v for v, p in zip(vals, pos) if p] for var, vals in sub.items()}
    if not w.size:
        raise ValueError("no observations with positive weight")

    if not is_factor_values(sub[resp]):
        raise ValueError("response needs to be a factor")

    def observed_levels(var: str) -> list[str]:
        return sorted({str(v) for v in sub[var] if not _is_na(v)})

    def ordered_levels(var: str) -> list[str]:
        observed = {str(v) for v in sub[var] if not _is_na(v)}
        base = [str(v) for v in levels[var]] if levels and var in levels else sorted(observed)
        return [lev for lev in base if lev in observed]

    y_levels = ordered_levels(resp)
    code_of = {lev: j + 1 for j, lev in enumerate(y_levels)}
    y_codes = np.array([code_of[str(v)] for v in sub[resp]], dtype=int)

    group_levels = ordered_levels(group)
    group_code = {lev: j + 1 for j, lev in enumerate(group_levels)}
    gr_fac = np.array([group_code[str(v)] for v in sub[group]], dtype=int)
    q = len(group_levels)
    _check_ranef(q, len(w), bool(np.all(w == 1)), ctrl["checkRanef"])

    factor_levels = {
        v: ordered_levels(v) for v in formula_variables(fixed_rhs) if is_factor_values(sub[v])
    }
    X, X_names = design_matrix(fixed_rhs, sub, factor_levels)
    pivot, rank = _linpack_qr(X, tol=1e-7)
    if rank < X.shape[1]:
        # drop.coef keeps the pivoted columns, so the names follow that order.
        X_names = [X_names[i] for i in (pivot[:rank] - 1)]
    X = drop_coef(X, silent=False)
    ths = make_thresholds(y_levels, threshold)
    rho = clm_newrho(
        y_codes,
        X,
        NOM=None,
        S=None,
        weights=w,
        offset=np.zeros(len(w)),
        S_offset=None,
        tJac=ths["tJac"],
        # clmm() calls clm.newRho with clm.control() defaults: sign.location "negative".
        sign_location="negative",
        sign_nominal="positive",
        link=link,
    )
    nalpha = int(ths["nalpha"])
    nbeta = X.shape[1] - 1
    alpha_names = list(ths["alpha.names"])
    beta_names = X_names[1:]
    rho_ssr = _Ssr(
        B1=rho.b1,
        B2=rho.b2,
        o1=rho.o1,
        o2=rho.o2,
        wts=w,
        grFac=gr_fac,
        nalpha=nalpha,
        nbeta=nbeta,
        nrandom=q,
        ctrl=ctrl,
        link=link,
    )
    rho_ssr.set_agq(nAGQ)

    if start is None:
        fe = clm_fit(
            y=[sub[resp][i] for i in range(len(w))],
            X=X,
            levels=y_levels,
            X_names=X_names,
            weights=w,
            link=link,
            threshold=threshold,
        )
        fe_par = np.asarray(fe["coefficients"], dtype=float).reshape(-1)
        start_par = np.concatenate([fe_par[: nalpha + nbeta], [0.0]])
    else:
        start_par = np.asarray(start, dtype=float).reshape(-1)
        if start_par.size != nalpha + nbeta + 1:
            raise ValueError("start must have length nalpha + nbeta + ntau")
    rho_ssr.par = start_par.copy()

    if not do_fit:
        return rho_ssr

    if nAGQ < 0:
        objective = _get_nghq
    elif nAGQ > 1:
        objective = _get_nagq
    else:
        objective = _get_nla

    init_val = objective(rho_ssr, rho_ssr.par)
    if not math.isfinite(init_val):
        raise ValueError(f"non-finite likelihood at starting value ({init_val:g})")

    optctrl = {k: v for k, v in ctrl["optCtrl"].items() if k not in ("grad", "grtol")}
    fit = nlminb_port(
        lambda x: objective(rho_ssr, np.asarray(x, dtype=float)),
        [float(v) for v in start_par],
        control=optctrl,
    )
    par_hat = np.asarray(fit["par"], dtype=float)
    value = float(fit["objective"])

    # Random-effect modes and the variance at the optimum.
    rho_ssr.par = par_hat.copy()
    _nll_base(rho_ssr)
    _update_uC(rho_ssr)
    tau = rho_ssr.tau
    ranef = rho_ssr.u * tau
    condvar = 1.0 / rho_ssr.D * tau**2

    def obj_fun(par: np.ndarray) -> float:
        return objective(rho_ssr, par)

    if Hess:
        gradient, hessian = _deriv12(obj_fun, par_hat)
    else:
        gradient = _grad_ctr(obj_fun, par_hat)
        hessian = None

    nfepar = nalpha + nbeta
    coef_names = alpha_names + beta_names
    coefficients = par_hat[:nfepar]
    res = {
        "coefficients": coefficients,
        "coef.names": coef_names,
        "alpha": coefficients[:nalpha],
        "beta": coefficients[nalpha:],
        "ST": tau,
        "ST.name": group,
        # clmm() keeps ST as a named list of matrices, one per random-effect
        # term; the sd list is what ranef/VarCorr/print read.
        "ST.matrices": {group: np.array([[tau]])},
        "ST.colnames": [["(Intercept)"]],
        "gfList": {group: list(group_levels)},
        "assign": np.array([1]),
        "dims": {
            "n": int(len(w)),
            "nlev.re": np.array([q]),
            "nlev.gf": np.array([q]),
            "qi": np.array([1]),
            "nretrms": 1,
            "ngf": 1,
            "nbeta": int(nbeta),
            "nalpha": int(nalpha),
            "nfepar": int(nfepar),
        },
        "logLik": -value,
        "AIC": -2 * (-value) + 2 * (nfepar + 1),
        "edf": nfepar + 1,
        "nobs": float(np.sum(w)),
        "ranef": ranef,
        "condVar": condvar,
        "group.levels": group_levels,
        "u": rho_ssr.u,
        "fitted.values": rho_ssr.fitted,
        "gradient": gradient,
        "Hessian": hessian,
        "Niter": rho_ssr.Niter,
        "neval": rho_ssr.neval,
        "nAGQ": nAGQ,
        "link": link,
        "threshold": threshold,
        "y.levels": y_levels,
        "optRes": {
            "par": par_hat,
            "objective": value,
            "convergence": fit["convergence"],
            "message": fit["message"],
            "iterations": fit["iterations"],
            "evaluations": fit["evaluations"],
        },
    }
    return res
