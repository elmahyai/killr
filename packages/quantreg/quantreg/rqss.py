"""Sparse additive quantile smoothing splines: rqss, rqss.fit, qss, qss1 and qts1.

R/rqss.R of quantreg 6.1. The design matrices are scipy.sparse in place of
SparseM, and the fit is `rq_fit_sfn` (rq.fit.sfn). Univariate smoothers are
qss1 (penalty on the slope changes) and qts1 (penalty on the total variation).

Also here: fitted.rqss, resid.rqss, logLik.rqss, AIC.rqss, print.rqss and
print.summary.rqss (the last takes a summary-shaped mapping; summary.rqss is not
translated yet).

Constrained qss terms (constraint I, D, V, C, VI, VD, CI, CD) build R and r as
R does, and rqss fits them with rq_fit_sfnc. qss2 (the triogram) and
triogram_penalty are here too; the triangulation is interp's tri_mesh and
tri_sht2tri, and the penalty loop is crates/quantreg_penalty. Not translated
here: predict.qss2 and plot.qss2 (they need interp's tri.find, in.convex.hull,
interp and convex.hull), method "lasso" needs the lasso block, and weights in
rqss are not yet implemented.
"""

from __future__ import annotations

import ast
import math
import re
from dataclasses import dataclass, field

import numpy as np
import scipy.sparse as sp

from quantreg.sfn import rq_fit_sfn, rq_fit_sfnc

_NAME = re.compile(r"[A-Za-z.][A-Za-z0-9._]*")


@dataclass
class QSS:
    """A qss1 or qts1 structure: knots, fidelity block F, penalty A, constraints R and r."""

    knots: np.ndarray
    F: sp.csr_matrix
    lambda_: float
    A: sp.csr_matrix
    Dorder: int
    R: sp.csr_matrix | None = None
    r: np.ndarray | None = None

    @property
    def class_name(self):
        return "qss1" if self.Dorder == 1 else "qts1"


@dataclass
class QSSFit:
    """A fitted qss1 or qts1 component: xyz is the knot column with the fitted values."""

    xyz: np.ndarray
    Dorder: int
    dummies: object = None

    @property
    def class_name(self):
        return "qss1" if self.Dorder == 1 else "qts1"


def _qss_xyz(object):
    """Return the knot/value matrix accepted by predict.qss1."""
    if isinstance(object, dict):
        xyz = object.get("xyz")
    else:
        xyz = getattr(object, "xyz", None)
    if xyz is None:
        raise TypeError("object should contain an xyz matrix")
    xyz = np.asarray(xyz, dtype=float)
    if xyz.ndim != 2 or xyz.shape[1] < 2:
        raise ValueError("object$xyz should have at least two columns")
    return xyz[:, :2]


def predict_qss1(object, newdata, **kwargs):
    """predict.qss1: linearly interpolate a univariate qss1 fit.

    The returned ``D`` has the first interpolation column removed, matching
    SparseM's ``D[, -1]`` in the R method.
    """
    del kwargs
    xyz = _qss_xyz(object)
    knots, values = xyz[:, 0], xyz[:, 1]
    data = np.asarray(newdata, dtype=float)
    if data.ndim == 2:
        if data.shape[1] != 1:
            raise ValueError("newdata should have only one column for predict.qss1")
        data = data[:, 0]
    elif data.ndim != 1:
        raise ValueError("newdata should have only one column for predict.qss1")
    if np.any(np.diff(knots) < 0):
        raise ValueError("x coordinates in qss1 object not monotone")
    if data.size and (np.max(data) > np.max(knots) or np.min(data) < np.min(knots)):
        raise ValueError("no extrapolation allowed in predict.qss")
    if knots.size < 2:
        raise ValueError("qss1 object needs at least two knots")
    bins = np.searchsorted(knots, data, side="right") - 1
    bins = np.minimum(bins, knots.size - 2)
    h = knots[bins + 1] - knots[bins]
    left = (knots[bins + 1] - data) / h
    right = (data - knots[bins]) / h
    rows = np.repeat(np.arange(data.size), 2)
    cols = np.column_stack([bins, bins + 1]).ravel()
    vals = np.column_stack([left, right]).ravel()
    Dfull = sp.csr_matrix((vals, (rows, cols)), shape=(data.size, knots.size))
    return {"x": data, "y": np.asarray(Dfull @ values).reshape(-1), "D": Dfull[:, 1:]}


@dataclass
class Rqss:
    """The rqss object: the coefficients, residuals, fidelity and the qss components."""

    coef: np.ndarray
    coef_names: list
    resid: np.ndarray
    fidelity: float
    objective: float
    edf: int
    n: int
    tau: float
    qss: list = field(default_factory=list)
    lambdas: list = field(default_factory=list)
    qssnames: list = field(default_factory=list)
    nrA: np.ndarray | None = None
    ncA: np.ndarray | None = None
    method: str = "sfn"
    ierr: int = 0
    it: int = 0
    X: sp.csr_matrix | None = None
    y: np.ndarray | None = None
    formula: str | None = None


def _csr(a):
    design = sp.csr_matrix(a, dtype=float)
    design.sum_duplicates()
    design.sort_indices()
    return design


def _univariate(x, constraint, lambda_, Dorder):
    """The shared part of qss1 and qts1: knots, F, A, R and r."""
    x = np.asarray(x, dtype=float).reshape(-1)
    xun = np.unique(x)
    h = np.diff(xun)
    nh = h.shape[0]
    nx = x.shape[0]
    p = nh + 1
    # B: the slope of the piecewise linear fit, nh x (nh + 1)
    rows = np.repeat(np.arange(nh), 2)
    cols = np.column_stack([np.arange(nh), np.arange(1, nh + 1)]).ravel()
    vals = np.column_stack([-1.0 / h, 1.0 / h]).ravel()
    B = sp.csr_matrix((vals, (rows, cols)), shape=(nh, nh + 1))
    if Dorder == 1:
        # D: first differences of the slopes, (nh - 1) x nh, applied to B
        dr = np.repeat(np.arange(nh - 1), 2)
        dc = np.column_stack([np.arange(nh - 1), np.arange(1, nh)]).ravel()
        dv = np.tile([-1.0, 1.0], nh - 1)
        D = sp.csr_matrix((dv, (dr, dc)), shape=(nh - 1, nh))
        A = (D @ B).tocsr()
    else:
        A = B
    if xun.shape[0] == nx:
        rank = np.argsort(np.argsort(x, kind="stable"), kind="stable") + 1
        F = sp.csr_matrix((np.ones(nx), (np.arange(nx), rank - 1)), shape=(nx, nx))
    else:
        codes = np.searchsorted(xun, x) + 1
        F = sp.csr_matrix((np.ones(nx), (np.arange(nx), codes - 1)), shape=(nx, xun.shape[0]))
    R_full, r_rows = _constraint_rows(constraint, nh, A, Dorder)
    R = None if R_full is None else R_full[:, 1:].tocsr()
    r = None if r_rows is None else np.zeros(r_rows)
    return QSS(
        knots=xun,
        F=F[:, 1:].tocsr(),
        lambda_=float(lambda_),
        A=A[:, 1:].tocsr(),
        Dorder=Dorder,
        R=R,
        r=r,
    )


def _make_d(p):
    """R's makeD(p): p - 1 rows, each with -1 in column k and +1 in column k + 1."""
    rows = np.repeat(np.arange(p - 1), 2)
    cols = np.column_stack([np.arange(p - 1), np.arange(1, p)]).ravel()
    vals = np.tile([-1.0, 1.0], p - 1)
    return sp.csr_matrix((vals, (rows, cols)), shape=(p - 1, p))


def _constraint_rows(constraint, nh, A, Dorder):
    """The constraint block R and its row count, before the first column is dropped.

    Follows qss1 and qts1 in R/rqss.R. Returns (None, None) for constraint "N".
    The rows are R b >= r with r = 0. Here "V" is convex (R = A) and "C" is concave
    (R = -A), as in R. "I" is increasing and "D" is decreasing.
    """
    if constraint == "N":
        return None, None
    p = nh + 1
    makep = _make_d(p)
    if Dorder == 0:
        if constraint == "I":
            blocks = [makep]
        elif constraint == "D":
            blocks = [-makep]
        else:
            raise ValueError("This constraint not implemented for Dorder = 0")
    else:
        table = {
            "V": [A],
            "C": [-A],
            "I": [makep],
            "D": [-makep],
            "VI": [makep, A],
            "VD": [-makep, A],
            "CI": [makep, -A],
            "CD": [-makep, -A],
        }
        if constraint not in table:
            raise ValueError(f"constraint {constraint!r} is not implemented for qss1")
        blocks = table[constraint]
    R = sp.vstack(blocks, format="csr")
    return R, R.shape[0]


def qss1(x, constraint="N", lambda_=1.0, dummies=None, ndum=0, w=None):
    """qss1(x, constraint, lambda): the univariate smoother with a slope-change penalty."""
    return _univariate(x, constraint, lambda_, 1)


def qts1(x, constraint="N", lambda_=1.0, dummies=None, ndum=0, w=None):
    """qts1(x, constraint, lambda): the taut-string smoother with a total-variation penalty."""
    if constraint not in ("N", "I", "D"):
        raise ValueError("This constraint not implemented for Dorder = 0")
    return _univariate(x, constraint, lambda_, 0)


def qss(x, constraint="N", lambda_=1.0, ndum=0, dummies=None, Dorder=1, w=None):
    """qss(x, ...): dispatch on the shape of x and on Dorder."""
    arr = np.asarray(x)
    if arr.ndim == 2:
        if arr.shape[1] == 2:
            return qss2(arr, constraint=constraint, lambda_=lambda_, ndum=ndum, dummies=dummies, w=w)
        raise NotImplementedError("a one-column matrix x is not translated (R returns the qss function)")
    if Dorder == 1:
        return qss1(arr, constraint=constraint, lambda_=lambda_, dummies=dummies, ndum=ndum, w=w)
    if Dorder == 0:
        return qts1(arr, constraint=constraint, lambda_=lambda_, dummies=dummies, ndum=ndum, w=w)
    raise ValueError("Dorder must be either 0 or 1")


def rqss_fit(x, y, tau=0.5, method="sfn", rhs=None, control=None, R=None, r=None):
    """rqss.fit: the sparse fit of rq.fit.sfn, or of rq.fit.sfnc when constraints are given.

    With method "sfnc" (or whenever R is given), R and r are the constraint rows R b >= r
    and the fit is rq_fit_sfnc. When rhs is given, tau is set to 0.5, as in R.
    """
    design = _csr(x)
    y = np.asarray(y, dtype=float).reshape(-1)
    if rhs is None:
        rhs = (1.0 - float(tau)) * np.asarray(design.sum(axis=0), dtype=float).reshape(-1)
    else:
        tau = 0.5
    if method == "sfnc" or R is not None:
        if R is None or r is None:
            raise ValueError("method sfnc needs both the constraint matrix R and the rhs r")
        fit = rq_fit_sfnc(design, y, R, r, tau=tau, rhs=rhs, control=control)
    elif method == "sfn":
        fit = rq_fit_sfn(design, y, tau=tau, rhs=rhs, control=control)
    else:
        raise NotImplementedError(f"rqss.fit method {method!r} is not translated yet")
    fit["resid"] = y - design @ fit["coefficients"]
    fit["contrasts"] = None
    return fit


def _split_terms(text):
    terms, depth, current = [], 0, ""
    for ch in text:
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        if ch == "+" and depth == 0:
            terms.append(current)
            current = ""
        else:
            current += ch
    terms.append(current)
    return terms


def _parse_formula(formula):
    text = str(formula).replace(" ", "")
    if "~" not in text:
        raise ValueError("formula has no ~")
    response, right = text.split("~", 1)
    intercept = True
    if right.endswith("-1") or right.endswith("+0"):
        intercept = False
        right = right[:-2]
    parametric, smooths = [], []
    for term in _split_terms(right):
        if term in ("", "1"):
            continue
        if term == "0":
            intercept = False
            continue
        match = re.fullmatch(r"qss\((.*)\)", term)
        if match:
            inner = re.sub(r"\blambda=", "lambda_=", match.group(1))
            call = ast.parse(f"qss({inner})", mode="eval").body
            if not call.args or not isinstance(call.args[0], ast.Name) or len(call.args) != 1:
                raise NotImplementedError(f"qss term {term!r}: only qss(name, key=value, ...) is translated")
            kwargs = {}
            for kw in call.keywords:
                key = "lambda_" if kw.arg == "lambda" else kw.arg
                kwargs[key] = ast.literal_eval(kw.value)
            smooths.append((call.args[0].id, kwargs))
        elif _NAME.fullmatch(term):
            parametric.append(term)
        else:
            raise NotImplementedError(f"formula term {term!r} is not translated")
    return response, intercept, parametric, smooths


def rqss(formula, data, tau=0.5, weights=None, method="sfn", lambda_=None, ztol=1e-5, control=None):
    """rqss(formula, data, tau): quantile regression with qss(x) additive smoothing terms.

    `data` is a mapping from names to arrays. Rows with a missing value are
    dropped, as model.frame does by default.
    """
    if weights is not None:
        raise NotImplementedError("weights in rqss are not implemented yet")
    if method != "sfn":
        raise NotImplementedError(f"rqss method {method!r} is not translated yet")
    tau = float(tau)
    response, intercept, parametric, smooths = _parse_formula(formula)
    names = [response] + parametric + [name for name, _ in smooths]
    columns = {name: np.asarray(data[name], dtype=float).reshape(-1) for name in names}
    n_all = columns[response].shape[0]
    keep = np.ones(n_all, dtype=bool)
    for name in names:
        keep &= np.isfinite(columns[name])
    y = columns[response][keep]
    n = int(y.shape[0])
    parts, coef_names = [], []
    if intercept:
        parts.append(np.ones((n, 1)))
        coef_names.append("(Intercept)")
    for name in parametric:
        parts.append(columns[name][keep].reshape(-1, 1))
        coef_names.append(name)
    X_par = np.hstack(parts) if parts else np.zeros((n, 0))
    p = X_par.shape[1]

    qss_list = []
    qssnames = []
    for name, kwargs in smooths:
        xvar = columns[name][keep]
        qss_list.append(qss(xvar, **kwargs))
        qssnames.append(name)
    ncA = [0]
    nrA = [0]
    F = sp.csr_matrix(X_par)
    for item in qss_list:
        F = sp.hstack([F, item.F], format="csr")
        ncA.append(item.A.shape[1])
        nrA.append(item.A.shape[0])
    ncA = np.cumsum(ncA)
    nrA = np.cumsum(nrA)
    if len(qss_list):
        A_block = sp.block_diag([item.lambda_ * item.A for item in qss_list], format="csr")
    else:
        A_block = sp.csr_matrix((0, 0))
    A = sp.hstack([sp.csr_matrix((A_block.shape[0], p)), A_block], format="csr")
    X = sp.vstack([F, A], format="csr")
    Y = np.concatenate([y, np.zeros(A.shape[0])])
    rhs = (1.0 - tau) * np.asarray(F.sum(axis=0), dtype=float).reshape(-1) + 0.5 * np.asarray(
        A.sum(axis=0), dtype=float
    ).reshape(-1)
    R_con, r_con = None, None
    if any(item.R is not None for item in qss_list):
        # R is block diagonal over the qss terms, with p zero columns in front, as in R.
        blocks = [
            item.R if item.R is not None else sp.csr_matrix((0, item.A.shape[1]))
            for item in qss_list
        ]
        R_block = sp.block_diag(blocks, format="csr")
        R_con = sp.hstack([sp.csr_matrix((R_block.shape[0], p)), R_block], format="csr")
        r_con = np.concatenate([item.r if item.r is not None else np.zeros(0) for item in qss_list])
    if R_con is not None:
        fit = rqss_fit(X, Y, tau=tau, rhs=rhs, method="sfnc", control=control, R=R_con, r=r_con)
    else:
        fit = rqss_fit(X, Y, tau=tau, rhs=rhs, method="sfn", control=control)
    coef = np.asarray(fit["coefficients"], dtype=float)
    resid = np.asarray(fit["resid"], dtype=float)

    components = []
    all_names = list(coef_names)
    for i, item in enumerate(qss_list):
        nc = item.A.shape[1]
        start = p + int(ncA[i])
        block = coef[start : start + nc]
        xyz = np.column_stack([item.knots, np.concatenate([[0.0], block])])
        components.append(QSSFit(xyz=xyz, Dorder=item.Dorder))
        all_names += [f"{qssnames[i]}{k + 1}" for k in range(nc)]

    uhat = resid[:n]
    fidelity = float(np.sum(uhat * (tau - (uhat < 0))))
    edf = int(np.sum(np.abs(uhat) < ztol))
    objective = fidelity + float(np.sum(np.abs(resid[n:])))
    return Rqss(
        coef=coef,
        coef_names=all_names,
        resid=resid,
        fidelity=fidelity,
        objective=objective,
        edf=edf,
        n=n,
        tau=tau,
        qss=components,
        lambdas=[item.lambda_ for item in qss_list],
        qssnames=qssnames,
        nrA=nrA,
        ncA=np.concatenate([[p], p + np.cumsum([item.A.shape[1] for item in qss_list])]).astype(int),
        method=method,
        ierr=int(fit["ierr"]),
        it=int(fit["it"]),
        X=X,
        y=Y,
        formula=str(formula),
    )


def fitted_rqss(object):
    """fitted.rqss: the first n rows of X %*% coef, where X is the stacked design with the penalty rows."""
    values = np.asarray(object.X @ object.coef, dtype=float).reshape(-1)
    return values[: object.n]


def resid_rqss(object):
    """resid.rqss: the first n residuals, the data part without the penalty rows."""
    return np.asarray(object.resid, dtype=float)[: object.n]


def log_lik_rqss(object):
    """logLik.rqss: n * (log(tau * (1 - tau)) - 1 - log(fidelity / n)), with df = edf."""
    n = int(object.n)
    tau = float(object.tau)
    value = n * (math.log(tau * (1.0 - tau)) - 1.0 - math.log(float(object.fidelity) / n))
    return {"value": value, "n": n, "df": int(object.edf)}


def aic_rqss(object, k=2):
    """AIC.rqss: -2 * logLik + k * edf. As in R, only k < 0 means log(n)."""
    likelihood = log_lik_rqss(object)
    penalty = float(k)
    if penalty < 0:
        penalty = math.log(likelihood["n"])
    value = -2.0 * likelihood["value"] + penalty * likelihood["df"]
    return {"value": value, "edf": likelihood["df"]}


def print_rqss(x):
    """print.rqss: the formula, the fidelity and the model dimension.

    R calls summary(x) for the two numbers. summary.rqss is not translated yet, and
    its fidelity and edf are the object's own fidelity and edf, so they are read here.
    """
    print("Formula:")
    print(x.formula)
    print(f"Quantile fidelity at tau =  {float(x.tau):g} is {float(x.fidelity):.7g} ")
    print(f"Estimated Model Dimension is {int(x.edf)} ")
    return x


def _print_table(values, row_names, col_names, digits):
    """A plain table of numbers, one row per term. printCoefmat's layout is not copied."""
    width = max([len(str(name)) for name in row_names] + [4])
    print(" " * width + "".join(f"{name:>13}" for name in col_names))
    for name, row in zip(row_names, values):
        cells = "".join(f"{float(item):>13.{digits}g}" for item in row)
        print(f"{str(name):<{width}}{cells}")


def print_summary_rqss(x, digits=4):
    """print.summary.rqss for a summary.rqss object given as a mapping with R's field names.

    Fields: formula, coef (rows x 4) with coef_names, qsstab (rows x 5) with qsstab_names,
    fidelity, tau, edf, n. summary.rqss itself is not translated yet, so the caller builds x.
    """
    print("Formula:")
    print(x["formula"])
    coef = np.asarray(x["coef"], dtype=float)
    if coef.size:
        print("\nParametric coefficients:")
        _print_table(coef, x["coef_names"], ["Estimate", "Std. Error", "t value", "Pr(>|t|)"], digits)
    print()
    qsstab = x.get("qsstab")
    if qsstab is not None and np.size(qsstab):
        print("Approximate significance of qss terms:")
        _print_table(
            np.asarray(qsstab, dtype=float),
            x["qsstab_names"],
            ["EDF", "Lambda", "Penalty", "F value", "Pr(>F)"],
            digits,
        )
    print()
    print(f"  Quantile Fidelity at tau = {float(x['tau'])}  is  {float(x['fidelity']):11.6g}")
    print(f"  Effective Degrees of Freedom = {float(x['edf']):<8.5g}  Sample Size = {int(x['n'])}")
    return x



def _rounded_key(value):
    """The text R's paste() gives a double: 15 significant digits."""
    return format(float(value), ".15g")


def triogram_fidelity(x, y, ndum=0, dummies=None):
    """triogram.fidelity(x, y, ndum, dummies): the fidelity block of the triogram design.

    R returns a SparseM matrix.csr for F. Here F is a scipy.sparse CSR matrix (n x k),
    in place of SparseM. A repeated (x, y) point gets one column, and the returned x
    and y keep only the first copy, as R does. A dummies list with x and y adds zero
    columns to F.

    The random dummy vertices (ndum > 0 with no dummies) call interp::tri.mesh in R.
    The R package interp is not in registry.json, so that branch raises here.
    """
    x = np.asarray(x, dtype=float).reshape(-1)
    y = np.asarray(y, dtype=float).reshape(-1)
    n = x.shape[0]
    if y.shape[0] != n:
        raise ValueError("x and y must have the same length")
    dup = np.zeros(n, dtype=bool)
    seen = set()
    for i in range(n):
        key = (x[i], y[i])
        if key in seen:
            dup[i] = True
        else:
            seen.add(key)
    if dup.any():
        unique_rows = np.flatnonzero(~dup)
        position = {}
        for k, i in enumerate(unique_rows):
            position.setdefault((_rounded_key(x[i]), _rounded_key(y[i])), k)
        columns = np.array(
            [position[(_rounded_key(x[i]), _rounded_key(y[i]))] for i in range(n)], dtype=np.int64
        )
        fidelity = sp.csr_matrix(
            (np.ones(n), columns, np.arange(n + 1)), shape=(n, len(unique_rows))
        )
        x = x[unique_rows]
        y = y[unique_rows]
    else:
        fidelity = sp.identity(n, format="csr", dtype=float)
    if dummies is not None and len(dummies) > 0:
        if not isinstance(dummies, dict) or "x" not in dummies or "y" not in dummies:
            raise ValueError("dummies list lacking x and y elements")
        dummy_x = np.asarray(dummies["x"], dtype=float).reshape(-1)
        dummy_y = np.asarray(dummies["y"], dtype=float).reshape(-1)
        if dummy_x.shape[0] != dummy_y.shape[0]:
            raise ValueError("dummies x and y components differ in length")
        x = np.concatenate([x, dummy_x])
        y = np.concatenate([y, dummy_y])
        fidelity = sp.hstack([fidelity, sp.csr_matrix((n, dummy_x.shape[0]))], format="csr")
    elif ndum > 0:
        raise NotImplementedError(
            "triogram.fidelity with random dummy vertices needs interp::tri.mesh; "
            "interp is not in registry.json"
        )
    return {"x": x, "y": y, "F": fidelity, "dummies": dummies}


def triogram_penalty(x, y, eps=np.finfo(float).eps):
    """triogram.penalty(x, y, eps): the sparse penalty matrix of the triogram.

    R returns a SparseM matrix.csr with one row per Delaunay edge that is not a
    hull edge on both ends (ned rows, n columns, four entries per row). Here the
    result is a scipy.sparse CSR matrix of the same shape, with 0-based columns.
    The triangulation is interp's tri.mesh, triSht2tri and on.convex.hull; the
    edge loop is the Fortran penalty, in crates/quantreg_penalty.

    The R package interp is loaded from its Python package, interp, when this is
    called. A degenerate edge (collinear points) raises, as R's stop does.
    """
    from interp.on_convex_hull import on_convex_hull
    from interp.tri_mesh import tri_mesh
    from interp.tri_sht2tri import tri_sht2tri
    from quantreg_penalty_kernel import penalty as penalty_kernel

    x = np.asarray(x, dtype=float).reshape(-1)
    y = np.asarray(y, dtype=float).reshape(-1)
    n = x.shape[0]
    trinew = tri_mesh(x, y)
    tri = tri_sht2tri(trinew)
    bnd = np.asarray(on_convex_hull(trinew, x, y), dtype=np.int64)
    rax, jax, ned, ierr = penalty_kernel(
        n,
        13 * n,
        x,
        y,
        bnd,
        np.asarray(tri["tlist"], dtype=np.int64),
        np.asarray(tri["tlptr"], dtype=np.int64),
        np.asarray(tri["tlend"], dtype=np.int64),
        float(eps),
    )
    if ierr == 1:
        raise RuntimeError("collinearity in ggap")
    nnz = 4 * ned
    ra = np.asarray(rax[:nnz], dtype=float)
    ja = np.asarray(jax[:nnz], dtype=np.int64) - 1
    indptr = 4 * np.arange(ned + 1, dtype=np.int64)
    return sp.csr_matrix((ra, ja, indptr), shape=(ned, n))


def qss2(x, constraint="N", lambda_=1.0, ndum=0, dummies=None, w=None):
    """qss2(x, constraint, lambda, ndum, dummies): the bivariate triogram smoother.

    x is an n x 2 array of (x, y) points. The return is R's list with the names
    x, F, dummies, lambda, A, R and r. F and A drop their first column, as R does
    for identifiability. R and r are set for constraint "V" (R = A) and "C"
    (R = -A, with r = 0), and are None for "N". The weights w are not used, as in R.
    """
    x = np.asarray(x, dtype=float)
    if x.ndim != 2 or x.shape[1] != 2:
        raise ValueError("qss2 needs an n x 2 matrix x")
    f = triogram_fidelity(x[:, 0], x[:, 1], ndum=ndum, dummies=dummies)
    fidelity = f["F"]
    A = triogram_penalty(f["x"], f["y"])
    if constraint == "V":
        R = A
        r = np.zeros(A.shape[0])
    elif constraint == "C":
        R = -A
        r = np.zeros(A.shape[0])
    elif constraint == "N":
        R = None
        r = None
    else:
        raise ValueError("qss2 constraint must be N, V or C")
    return {
        "x": {"x": f["x"], "y": f["y"]},
        "F": fidelity[:, 1:],
        "dummies": f["dummies"],
        "lambda": lambda_,
        "A": A[:, 1:],
        "R": None if R is None else R[:, 1:],
        "r": r,
    }
