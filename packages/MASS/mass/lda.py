"""Linear discriminant analysis (MASS lda)."""

from __future__ import annotations

import warnings
import math
from dataclasses import dataclass
from typing import Any

import numpy as np

from mass.errors import MassError


def _match_arg(value: str | None, choices: tuple[str, ...]) -> str:
    if value is None:
        return choices[0]
    text = str(value)
    exact = [item for item in choices if item == text]
    if len(exact) == 1:
        return exact[0]
    hits = [item for item in choices if item.startswith(text)]
    if len(hits) == 1:
        return hits[0]
    if not hits:
        raise MassError("'arg' should be one of " + ", ".join(repr(item) for item in choices))
    raise MassError("'arg' matched more than one choice: " + ", ".join(hits))


def _as_factor(grouping: Any) -> tuple[np.ndarray, list[str]]:
    arr = np.asarray(grouping)
    if arr.dtype.kind in {"U", "S", "O"}:
        levels = []
        codes = np.empty(arr.shape[0], dtype=int)
        lookup: dict[Any, int] = {}
        for i, val in enumerate(arr):
            if val not in lookup:
                lookup[val] = len(levels)
                levels.append(str(val))
            codes[i] = lookup[val]
        return codes, levels
    raise MassError("grouping must be a factor or character vector")


def _svd_v_d(x: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    _u, s, vh = np.linalg.svd(x, full_matrices=False)
    return s, vh.T


def _column_var(mat: np.ndarray) -> np.ndarray:
    n = mat.shape[0]
    if n <= 1:
        return np.zeros(mat.shape[1])
    centered = mat - mat.mean(axis=0)
    return (centered * centered).sum(axis=0) / (n - 1)


def _group_means(x: np.ndarray, codes: np.ndarray, ng: int) -> np.ndarray:
    p = x.shape[1]
    means = np.zeros((ng, p))
    for k in range(ng):
        mask = codes == k
        if np.any(mask):
            means[k] = x[mask].mean(axis=0)
    return means


def _weighted_group_means(x: np.ndarray, w: np.ndarray, codes: np.ndarray, ng: int) -> np.ndarray:
    p = x.shape[1]
    means = np.zeros((ng, p))
    for k in range(ng):
        mask = codes == k
        sw = w[mask].sum()
        if sw > 0:
            means[k] = (w[mask, None] * x[mask]).sum(axis=0) / sw
    return means


@dataclass
class Lda:
    prior: np.ndarray
    counts: np.ndarray
    means: np.ndarray
    scaling: np.ndarray
    lev: list[str]
    svd: np.ndarray
    N: int
    call: Any = None
    terms: Any = None
    contrasts: Any = None
    xlevels: Any = None
    na_action: Any = None


@dataclass
class LdaCv:
    class_: np.ndarray
    posterior: np.ndarray
    lev: list[str]


def _lda_default(
    x: np.ndarray,
    codes: np.ndarray,
    lev: list[str],
    *,
    prior_input: np.ndarray | None,
    tol: float,
    method: str,
    cv: bool,
    nu: float,
) -> Lda | LdaCv:
    n, p = x.shape
    ng_full = len(lev)
    counts_full = np.bincount(codes, minlength=ng_full)
    lev1 = lev
    codes_work = codes.copy()
    counts = counts_full.copy()
    prior = None

    if prior_input is not None:
        prior_arr = np.asarray(prior_input, dtype=float).reshape(-1)
        if np.any(prior_arr < 0) or round(float(prior_arr.sum()), 5) != 1.0:
            raise MassError("invalid 'prior'")
        if prior_arr.shape[0] != ng_full:
            raise MassError("'prior' is of incorrect length")
        prior = prior_arr[counts > 0]

    if np.any(counts == 0):
        empty = [lev[i] for i in range(ng_full) if counts[i] == 0]
        if len(empty) == 1:
            msg = f"group {empty[0]} is empty"
        else:
            msg = f"groups {' '.join(empty)} are empty"
        warnings.warn(msg, stacklevel=3)
        keep = counts > 0
        lev1 = [lev[i] for i in range(ng_full) if keep[i]]
        remap = np.cumsum(keep) - 1
        codes_work = remap[codes]
        counts = counts[keep]
        ng = int(counts.shape[0])
    else:
        ng = ng_full

    proportions = counts / n
    if prior is None:
        prior = proportions.copy()
    names_prior = {lev1[i]: float(prior[i]) for i in range(ng)}
    names_counts = {lev1[i]: int(counts[i]) for i in range(ng)}

    method = _match_arg(method, ("moment", "mle", "mve", "t"))
    if cv and method not in ("moment", "mle"):
        raise MassError(f"cannot use leave-one-out CV with method {method!r}")

    group_means = _group_means(x, codes_work, ng)
    centered = x - group_means[codes_work]
    f1 = np.sqrt(_column_var(centered))
    if np.any(f1 < tol):
        const = np.where(f1 < tol)[0] + 1
        if len(const) == 1:
            raise MassError(f"variable {const[0]} appears to be constant within groups")
        raise MassError(f"variables {' '.join(str(c) for c in const)} appear to be constant within groups")

    scaling = np.diag(1.0 / f1)

    if method == "mve":
        resid = centered @ scaling
        cov = (n / (n - ng)) * _cov_rob(resid)["cov"]
        s_d, s_v = _svd_v_d(cov)
        rank = int(np.sum(s_d > tol**2))
        if rank == 0:
            raise MassError("rank = 0: variables are numerically constant")
        if rank < p:
            warnings.warn("variables are collinear", stacklevel=3)
        scaling = scaling @ s_v[:, :rank] @ np.diag(np.sqrt(1.0 / s_d[:rank]))
    elif method == "t":
        if nu <= 2:
            raise MassError("'nu' must exceed 2")
        w = np.ones(n)
        while True:
            w0 = w.copy()
            x_c = x - group_means[codes_work]
            s_d, s_v = _svd_v_d(np.sqrt((1 + p / nu) * w / n)[:, None] * x_c)
            x_proj = x_c @ s_v @ np.diag(1.0 / s_d)
            w = 1.0 / (1.0 + (x_proj**2).sum(axis=1) / nu)
            group_means = _weighted_group_means(x, w, codes_work, ng)
            if np.all(np.abs(w - w0) < 1e-2):
                break
        x_c = x - group_means[codes_work]
        factor = np.sqrt(nu / (nu - 2) * (1 + p / nu) / n * w)
        x_s, s_v = _svd_v_d(factor[:, None] * x_c @ scaling)
        rank = int(np.sum(x_s > tol))
        if rank == 0:
            raise MassError("rank = 0: variables are numerically constant")
        if rank < p:
            warnings.warn("variables are collinear", stacklevel=3)
        scaling = scaling @ s_v[:, :rank] @ np.diag(1.0 / x_s[:rank])
    else:
        fac = 1.0 / (n - ng) if method == "moment" else 1.0 / n
        x_s, s_v = _svd_v_d(np.sqrt(fac) * centered @ scaling)
        rank = int(np.sum(x_s > tol))
        if rank == 0:
            raise MassError("rank = 0: variables are numerically constant")
        if rank < p:
            warnings.warn("variables are collinear", stacklevel=3)
        scaling = scaling @ s_v[:, :rank] @ np.diag(1.0 / x_s[:rank])

    if cv:
        x_s = x @ scaling
        dm = group_means @ scaling
        k = ng if method == "moment" else 0
        dist = np.zeros((n, ng))
        for i in range(ng):
            dev = x_s - dm[i]
            dist[:, i] = np.sum(dev * dev, axis=1)
        dist2 = dist.copy()
        nc = counts[codes_work]
        cc = nc / ((nc - 1) * (n - k))
        ind_row = np.arange(n)
        ind_col = codes_work
        for i in range(ng):
            dev = x_s - dm[i]
            dev2 = x_s - dm[codes_work]
            tmp = np.sum(dev * dev2, axis=1)
            dist[:, i] = (n - 1 - k) / (n - k) * (
                dist2[:, i] + cc * tmp**2 / (1 - cc * dist2[ind_row, ind_col])
            )
        dist[ind_row, ind_col] = (
            dist2[ind_row, ind_col]
            * (n - 1 - k)
            / (n - k)
            * (nc / (nc - 1)) ** 2
            / (1 - cc * dist2[ind_row, ind_col])
        )
        dist = 0.5 * dist - np.log(prior)[None, :]
        dist = np.exp(-(dist - np.min(dist, axis=1, keepdims=True)))
        cl_idx = np.argmax(dist, axis=1)
        cl = np.array([lev1[i] for i in cl_idx], dtype=object)
        posterior = dist / dist.sum(axis=1, keepdims=True)
        return LdaCv(class_=cl, posterior=posterior, lev=lev)

    xbar = prior @ group_means
    fac = 1.0 / ng if method == "mle" else 1.0 / (ng - 1)
    gm_centered = group_means - xbar
    x_s, s_v = _svd_v_d(np.sqrt(n * prior * fac)[:, None] * gm_centered @ scaling)
    rank = int(np.sum(x_s > tol * x_s[0]))
    if rank == 0:
        raise MassError("group means are numerically identical")
    scaling = scaling @ s_v[:, :rank]

    obj = Lda(
        prior=np.array([names_prior[k] for k in lev1]),
        counts=np.array([names_counts[k] for k in lev1]),
        means=group_means,
        scaling=scaling,
        lev=list(lev),
        svd=x_s[:rank],
        N=n,
    )
    return obj


def lda(
    x=None,
    grouping=None,
    *,
    formula: str | None = None,
    data: dict[str, Any] | None = None,
    prior=None,
    tol: float = 1.0e-4,
    method: str | None = None,
    CV: bool = False,
    nu: float = 5,
    subset=None,
    na_action=None,
    **kwargs,
):
    """Linear discriminant analysis."""
    if kwargs:
        raise MassError(f"unused arguments: {', '.join(sorted(kwargs))}")
    if formula is not None:
        if data is None:
            raise MassError("'data' must be supplied")
        return _lda_formula(formula, data, prior=prior, tol=tol, method=method, CV=CV, nu=nu, subset=subset, na_action=na_action)
    if x is None:
        raise MassError("x must be supplied")
    if isinstance(x, dict):
        return _lda_data_frame(x, grouping, prior=prior, tol=tol, method=method, CV=CV, nu=nu, subset=subset, na_action=na_action)
    arr = np.asarray(x, dtype=float)
    if arr.ndim == 1:
        raise MassError("'x' is not a matrix")
    if arr.ndim == 2 and grouping is not None:
        return _lda_matrix(arr, grouping, prior=prior, tol=tol, method=method, CV=CV, nu=nu, subset=subset, na_action=na_action)
    raise MassError("'x' is not a matrix")


def _apply_subset_na(x, grouping, subset, na_action):
    if subset is not None:
        idx = np.asarray(subset, dtype=int) - 1
        x = x[idx, :]
        grouping = np.asarray(grouping)[idx]
    if na_action is not None:
        raise MassError("na.action is not implemented")
    return x, grouping


def _lda_matrix(x, grouping, **opts):
    x = np.asmatrix(x) if not isinstance(x, np.ndarray) else np.array(x, dtype=float, copy=True)
    if x.ndim != 2:
        raise MassError("'x' is not a matrix")
    if not np.all(np.isfinite(x)):
        raise MassError("infinite, NA or NaN values in 'x'")
    if x.shape[0] != len(grouping):
        raise MassError("nrow(x) and length(grouping) are different")
    x, grouping = _apply_subset_na(x, grouping, opts.pop("subset", None), opts.pop("na_action", None))
    codes, lev = _as_factor(grouping)
    res = _lda_default(x, codes, lev, prior_input=opts.get("prior"), tol=opts["tol"], method=opts.get("method") or "moment", cv=opts["CV"], nu=opts["nu"])
    return res


def _lda_data_frame(x_dict, grouping, **opts):
    keys = list(x_dict.keys())
    mat = np.column_stack([np.asarray(x_dict[k], dtype=float).reshape(-1) for k in keys])
    return _lda_matrix(mat, grouping, **opts)


def _split_formula(formula: str) -> tuple[str, str]:
    if "~" not in formula:
        raise MassError("formula needs a '~'")
    left, right = formula.split("~", 1)
    return left.strip(), right.strip()


def _lda_formula(formula, data, **opts):
    resp, rhs = _split_formula(formula)
    if resp not in data:
        raise MassError(f"object '{resp}' not found")
    grouping = data[resp]
    n = len(np.asarray(grouping).reshape(-1))
    intercept = True
    terms: list[str] = []
    for raw in rhs.split("+"):
        piece = raw.strip()
        if not piece:
            continue
        if piece == ".":
            terms.extend(k for k in data if k != resp)
            continue
        if piece in {"1", ""}:
            continue
        if piece in {"0", "-1"}:
            intercept = False
            continue
        terms.append(piece)
    columns: list[np.ndarray] = []
    if intercept:
        pass
    for term in terms:
        if term not in data:
            raise MassError(f"object '{term}' not found")
        col = np.asarray(data[term], dtype=float).reshape(-1)
        if col.shape[0] != n:
            raise MassError(f"column '{term}' has length {col.shape[0]}, not {n}")
        columns.append(col)
    if not columns:
        raise MassError("no discriminators in formula")
    mat = np.column_stack(columns)
    res = _lda_matrix(mat, grouping, **opts)
    if isinstance(res, Lda):
        res.terms = formula
    return res


def _qchisq(p: float, df: float) -> float:
    if df <= 0 or p <= 0 or p >= 1:
        return math.nan
    lo, hi = 0.0, df + 10.0 * math.sqrt(2.0 * df)
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        # pchisq via gamma: P(X <= q) = pgamma(q/2, df/2)
        x = mid / 2.0
        a = df / 2.0
        # lower incomplete gamma ratio via series
        term = 1.0 / a
        total = term
        for k in range(1, 10000):
            term *= x / (a + k)
            total += term
            if abs(term) < abs(total) * 1e-16:
                break
        cdf = math.exp(-x + a * math.log(x)) * total / math.gamma(a) if x > 0 else 0.0
        if cdf < p:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def _cov_rob(x: np.ndarray) -> dict[str, np.ndarray]:
    """Minimum-volume ellipsoid covariance (MASS cov.rob, method mve)."""
    x = np.asarray(x, dtype=float)
    if x.ndim != 2:
        x = np.atleast_2d(x)
    if not np.all(np.isfinite(x)):
        raise MassError("missing or infinite values are not allowed")
    n, p = x.shape
    if n < p + 1:
        raise MassError(f"at least {p + 1} cases are needed")
    quan = (n + p + 1) // 2
    if quan < p + 1:
        raise MassError(f"'quantile' must be at least {p + 1}")
    if quan > n - 1:
        raise MassError(f"'quantile' must be at most {n - 1}")
    divisor = np.subtract.reduce(np.percentile(x, 75, axis=0), np.percentile(x, 25, axis=0))
    if np.any(divisor == 0):
        raise MassError("at least one column has IQR 0")
    xs = x / divisor
    ps = p + 1
    nexact = math.comb(n, ps)
    nsamp: int | str = "exact" if nexact < 5000 else "sample"
    sample = nsamp != "exact"
    if sample:
        nsamp = min(500 * ps, 3000)
    else:
        nsamp = nexact
    bestone = np.zeros(n, dtype=bool)
    best = float("inf")
    sing = 0
    rng = np.random.default_rng(1)

    def do_one(which: np.ndarray) -> tuple[bool, float, np.ndarray]:
        sub = xs[which]
        nn, pp = sub.shape
        means = sub.mean(axis=0)
        centered = sub - means
        _q, r = np.linalg.qr(centered, mode="reduced")
        rank = int(np.sum(np.abs(np.diag(r)) > 1e-7 * np.max(np.abs(r))))
        if rank < pp:
            return True, 0.0, np.zeros(n)
        det = float(np.sum(np.log(np.abs(np.diag(r)))))
        inv_cov = np.linalg.inv(r.T @ r) * (nn - 1)
        d2 = np.sum((xs - means) @ inv_cov * (xs - means), axis=1)
        return False, det, d2

    if sample:
        for _ in range(int(nsamp)):
            which = rng.choice(n, size=ps, replace=False)
            this_sing, det, d2 = do_one(which)
            if this_sing:
                sing += 1
                continue
            lim = np.partition(d2, quan - 1)[quan - 1]
            thiscrit = p * math.log(lim) + 2 * det
            if thiscrit < best:
                best = thiscrit
                bestone = d2 <= lim
    else:
        from itertools import combinations

        for which in combinations(range(n), ps):
            this_sing, det, d2 = do_one(np.array(which))
            if this_sing:
                sing += 1
                continue
            lim = np.partition(d2.copy(), quan - 1)[quan - 1]
            thiscrit = p * math.log(lim) + 2 * det
            if thiscrit < best:
                best = thiscrit
                bestone = d2 <= lim

    if not np.any(bestone):
        raise MassError("'x' is probably collinear")
    best_idx = np.where(bestone)[0]
    means = xs[best_idx].mean(axis=0) * divisor
    rcov = np.cov(xs[best_idx].T, ddof=1) * (1 + 15 / (n - p)) ** 2
    dist = np.sum((xs - xs[best_idx].mean(axis=0)) @ np.linalg.inv(rcov) * (xs - xs[best_idx].mean(axis=0)), axis=1)
    cut = _qchisq(0.975, p) * np.quantile(dist, quan / n) / _qchisq(quan / n, p)
    mask = dist < cut
    cov = (divisor[:, None] * np.cov(xs[mask].T, ddof=1) * divisor[None, :])
    return {"cov": cov, "center": xs[mask].mean(axis=0) * divisor}


def _flatten_lda(obj: Lda) -> np.ndarray:
    parts = [
        obj.prior.ravel(),
        obj.counts.ravel(),
        obj.means.ravel(order="F"),
        obj.scaling.ravel(order="F"),
        obj.svd.ravel(),
        np.array([obj.N], dtype=float),
    ]
    return np.concatenate(parts)
