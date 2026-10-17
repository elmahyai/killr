"""Try all one-term additions to a model (MASS addterm, glm and lm methods)."""

from __future__ import annotations

import math
import warnings
from dataclasses import dataclass, field

import numpy as np

from mass.errors import MassError


def _match_arg(value: str, choices: list[str]) -> str:
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


def _pnorm(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def _gamma(a: float) -> float:
    return math.gamma(a)


def _upper_incomplete_gamma(x: float, a: float) -> float:
    if x <= 0:
        return _gamma(a)
    log_pref = -x + a * math.log(x)
    if x < a + 1.0:
        term = 1.0 / a
        total = term
        for k in range(1, 10000):
            term *= x / (a + k)
            total += term
            if abs(term) < abs(total) * 1e-16:
                break
        lower = math.exp(log_pref) * total
        return _gamma(a) - lower
    tiny = 1e-30
    b = x + 1.0 - a
    c = 1.0 / tiny
    d = 1.0 / b
    h = d
    for i in range(1, 10000):
        an = -i * (i - a)
        b += 2.0
        d = an * d + b
        if abs(d) < tiny:
            d = tiny
        c = b + an / c
        if abs(c) < tiny:
            c = tiny
        d = 1.0 / d
        delta = d * c
        h *= delta
        if abs(delta - 1.0) < 1e-15:
            break
    return math.exp(log_pref) * h


def _pgamma(q: float, shape: float, scale: float = 1.0, *, lower_tail: bool = True) -> float:
    x = q / scale
    a = shape
    if x <= 0:
        return 0.0 if lower_tail else 1.0
    upper = _upper_incomplete_gamma(x, a)
    if lower_tail:
        return 1.0 - upper / _gamma(a)
    return upper / _gamma(a)


def _pchisq(q: float, df: float, *, lower_tail: bool = True) -> float:
    if math.isnan(q) or math.isnan(df) or df <= 0:
        return math.nan
    if df == 1.0:
        root = math.sqrt(max(q, 0.0))
        if lower_tail:
            return 2.0 * _pnorm(root) - 1.0
        return 2.0 * (1.0 - _pnorm(root))
    return _pgamma(q, shape=df / 2.0, scale=2.0, lower_tail=lower_tail)


def _safe_pchisq(q: float, df: float, *, lower_tail: bool = False) -> float:
    if df <= 0:
        return math.nan
    return _pchisq(q, df, lower_tail=lower_tail)


def _safe_pf(q: float, df1: float, df2: float, *, lower_tail: bool = False) -> float:
    if df1 <= 0:
        return math.nan
    # F upper tail via regularized incomplete beta (df2 even shortcut when needed).
    x = df2 / (df2 + df1 * q)
    return _pf_upper(q, df1, df2) if not lower_tail else 1.0 - _pf_upper(q, df1, df2)


def _pf_upper(q: float, df1: float, df2: float) -> float:
    if q <= 0:
        return 1.0
    z = df1 * q / (df1 * q + df2)
    return _pbeta_upper(z, df1 / 2.0, df2 / 2.0)


def _pbeta_upper(x: float, a: float, b: float) -> float:
    if x <= 0:
        return 1.0
    if x >= 1:
        return 0.0
    # Symmetry for stable continued fraction (Numerical Recipes style).
    ln_beta = math.lgamma(a) + math.lgamma(b) - math.lgamma(a + b)
    front = math.exp(a * math.log(x) + b * math.log(1.0 - x) - ln_beta) / a
    if x < (a + 1.0) / (a + b + 2.0):
        return front * _betacf(x, a, b)
    return front * _betacf(1.0 - x, b, a) * (1.0 - x) / x


def _betacf(x: float, a: float, b: float) -> float:
    qab = a + b
    qap = a + 1.0
    qam = a - 1.0
    c = 1.0
    d = 1.0 - qab * x / qap
    if abs(d) < 1e-30:
        d = 1e-30
    d = 1.0 / d
    h = d
    for m in range(1, 10001):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1.0 + aa * d
        if abs(d) < 1e-30:
            d = 1e-30
        c = 1.0 + aa / c
        if abs(c) < 1e-30:
            c = 1e-30
        d = 1.0 / d
        h *= d * c
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1.0 + aa * d
        if abs(d) < 1e-30:
            d = 1e-30
        c = 1.0 + aa / c
        if abs(c) < 1e-30:
            c = 1e-30
        d = 1.0 / d
        delta = d * c
        h *= delta
        if abs(delta - 1.0) < 1e-10:
            break
    return h


def _split_formula(text: str) -> tuple[str, str]:
    if "~" not in text:
        raise MassError("formula needs a '~'")
    left, right = text.split("~", 1)
    return left.strip(), right.strip()


def _parse_rhs_terms(rhs: str) -> tuple[bool, list[str]]:
    intercept = True
    terms: list[str] = []
    for raw in rhs.split("+"):
        piece = raw.strip()
        if not piece:
            continue
        if piece in {"1", ""}:
            continue
        if piece in {"0", "-1"}:
            intercept = False
            continue
        if piece.startswith("-"):
            name = piece[1:].strip()
            if name == "1":
                intercept = False
            continue
        terms.append(piece)
    return intercept, terms


def _update_formula(current: str, update: str) -> str:
    resp, rhs = _split_formula(current)
    _, upd_rhs = _split_formula(update if "~" in update else f"~ {update}")
    intercept, cur_terms = _parse_rhs_terms(rhs)
    upd_intercept, upd_terms = _parse_rhs_terms(upd_rhs)
    if not upd_intercept:
        intercept = False
    new_terms = list(cur_terms)
    for piece in upd_rhs.replace(".", " ").split("+"):
        token = piece.strip()
        if not token or token == ".":
            continue
        if token not in new_terms:
            new_terms.append(token)
    rhs_out = " + ".join(new_terms)
    if intercept:
        rhs_out = ("1 + " + rhs_out) if rhs_out else "1"
    elif not rhs_out:
        rhs_out = "0"
    return f"{resp} ~ {rhs_out}"


def _add_scope(current_formula: str, maximal_formula: str) -> list[str]:
    _, cur_rhs = _split_formula(current_formula)
    _, max_rhs = _split_formula(maximal_formula)
    _i, cur_terms = _parse_rhs_terms(cur_rhs)
    _i, max_terms = _parse_rhs_terms(max_rhs)
    cur_set = set(cur_terms)
    return [term for term in max_terms if term not in cur_set]


def _model_matrix(data: dict, formula: str) -> tuple[np.ndarray, np.ndarray, list[str], list[str]]:
    resp, rhs = _split_formula(formula)
    intercept, terms = _parse_rhs_terms(rhs)
    y = np.asarray(data[resp], dtype=float)
    n = y.shape[0]
    columns: list[np.ndarray] = []
    names: list[str] = []
    term_labels: list[str] = []
    if intercept:
        columns.append(np.ones(n))
        names.append("(Intercept)")
        term_labels.append("(Intercept)")
    for term in terms:
        if term not in data:
            raise MassError(f"object '{term}' not found")
        col = np.asarray(data[term], dtype=float).reshape(-1)
        if col.shape[0] != n:
            raise MassError(f"column '{term}' has length {col.shape[0]}, not {n}")
        columns.append(col)
        names.append(term)
        term_labels.append(term)
    x = np.column_stack(columns)
    return x, y, names, term_labels


def _qr_coef(x: np.ndarray, y: np.ndarray) -> tuple[np.ndarray, int]:
    q, r = np.linalg.qr(x, mode="reduced")
    coef = np.linalg.solve(r, q.T @ y)
    rank = int(np.sum(np.abs(np.diag(r)) > np.max(x.shape) * np.finfo(float).eps))
    return coef, rank


def _poisson_deviance(y: np.ndarray, mu: np.ndarray) -> np.ndarray:
    term = np.zeros_like(y, dtype=float)
    positive = y > 0
    term[positive] = y[positive] * np.log(y[positive] / mu[positive])
    return 2.0 * (term - (y - mu))


def _binomial_deviance(y: np.ndarray, mu: np.ndarray) -> np.ndarray:
    mu = np.clip(mu, 1e-12, 1 - 1e-12)
    term = np.zeros_like(y, dtype=float)
    positive = y > 0
    less = y < 1
    term[positive] += y[positive] * np.log(y[positive] / mu[positive])
    term[less] += (1.0 - y[less]) * np.log((1.0 - y[less]) / (1.0 - mu[less]))
    return 2.0 * term


def _glm_fit(
    x: np.ndarray,
    y: np.ndarray,
    *,
    family: str,
    weights: np.ndarray | None = None,
    offset: np.ndarray | None = None,
    maxit: int = 25,
    epsilon: float = 1e-8,
) -> tuple[np.ndarray, np.ndarray, float, int, np.ndarray]:
    n = x.shape[0]
    prior = np.ones(n) if weights is None else np.asarray(weights, dtype=float)
    off = np.zeros(n) if offset is None else np.asarray(offset, dtype=float)
    kind = family.lower()
    if kind == "binomial":
        mu = (prior * y + 0.5) / (prior + 1.0)
    elif kind == "poisson":
        mu = y + 0.1
    else:
        mu = y.copy()
    coef = np.zeros(x.shape[1])
    dev = math.inf
    for _ in range(maxit):
        if kind == "binomial":
            mu = np.clip(mu, 1e-12, 1 - 1e-12)
            mu_eta = mu * (1.0 - mu)
            variance = mu * (1.0 - mu)
        elif kind == "poisson":
            mu = np.clip(mu, 1e-12, None)
            mu_eta = mu
            variance = mu
        else:
            mu_eta = np.ones(n)
            variance = np.ones(n)
        working_weights = prior * (mu_eta**2) / variance
        working = (y - mu) / mu_eta
        if kind == "binomial":
            eta = np.log(mu / (1.0 - mu))
        elif kind == "poisson":
            eta = np.log(mu)
        else:
            eta = mu.copy()
        z = eta - off + working
        scale = np.sqrt(working_weights)
        coef, rank = _qr_coef(x * scale[:, None], z * scale)
        eta = x @ coef + off
        if kind == "binomial":
            mu = 1.0 / (1.0 + np.exp(-eta))
            dev_new = float(np.sum(prior * _binomial_deviance(y, mu)))
        elif kind == "poisson":
            mu = np.exp(eta)
            dev_new = float(np.sum(prior * _poisson_deviance(y, mu)))
        else:
            mu = eta
            dev_new = float(np.sum(prior * (y - mu) ** 2))
        if abs(dev - dev_new) / (0.1 + abs(dev_new)) < epsilon:
            dev = dev_new
            break
        dev = dev_new
    _, rank = _qr_coef(x * np.sqrt(working_weights)[:, None], z * np.sqrt(working_weights))
    return coef, mu, dev, rank, prior


def _lm_fit(x: np.ndarray, y: np.ndarray, weights: np.ndarray | None = None) -> tuple[float, int]:
    if weights is not None:
        scale = np.sqrt(weights)
        xw = x * scale[:, None]
        yw = y * scale
    else:
        xw = x
        yw = y
    coef, rank = _qr_coef(xw, yw)
    resid = y - x @ coef
    rss = float(np.sum(resid**2))
    return rss, rank


@dataclass
class GlmFit:
    formula: str
    data: dict
    family: str
    y: np.ndarray
    rank: int
    deviance: float
    df_residual: int
    nobs: int
    prior_weights: np.ndarray
    offset: np.ndarray | None = None
    dispersion: float = 1.0


@dataclass
class LmFit:
    formula: str
    data: dict
    y: np.ndarray
    rank: int
    df_residual: int
    nobs: int
    rss: float


def glm(formula: str, data: dict, *, family: str = "poisson", weights=None) -> GlmFit:
    x, y, _names, _labels = _model_matrix(data, formula)
    prior = None if weights is None else np.asarray(weights, dtype=float)
    _coef, _mu, dev, rank, prior_w = _glm_fit(x, y, family=family, weights=prior)
    n = y.shape[0]
    df_res = n - rank
    disp = 1.0 if family.lower() in {"poisson", "binomial"} else dev / max(df_res, 1)
    return GlmFit(
        formula=formula,
        data=data,
        family=family,
        y=y,
        rank=rank,
        deviance=dev,
        df_residual=df_res,
        nobs=n,
        prior_weights=prior_w,
        dispersion=disp,
    )


def lm(formula: str, data: dict, *, weights=None) -> LmFit:
    x, y, _names, _labels = _model_matrix(data, formula)
    prior = None if weights is None else np.asarray(weights, dtype=float)
    rss, rank = _lm_fit(x, y, prior)
    n = y.shape[0]
    return LmFit(
        formula=formula,
        data=data,
        y=y,
        rank=rank,
        df_residual=n - rank,
        nobs=n,
        rss=rss,
    )


@dataclass
class AddtermTable:
    columns: list[str]
    rows: list[str]
    values: dict[tuple[str, str], float]
    heading: list[str] = field(default_factory=list)

    def flatten_numeric(self) -> list[float]:
        out: list[float] = []
        for row in self.rows:
            for col in self.columns:
                value = self.values.get((row, col), math.nan)
                out.append(float(value) if value is not None and not (isinstance(value, float) and math.isnan(value)) else math.nan)
        return out

    def as_matrix(self) -> np.ndarray:
        rows = len(self.rows)
        cols = len(self.columns)
        mat = np.full((rows, cols), np.nan)
        for i, row in enumerate(self.rows):
            for j, col in enumerate(self.columns):
                mat[i, j] = self.values.get((row, col), math.nan)
        return mat


def _glm_loglik(fit: GlmFit, mu: np.ndarray | None = None) -> float:
    y = fit.y
    fam = fit.family.lower()
    if mu is None:
        x, y, _, _ = _model_matrix(fit.data, fit.formula)
        _c, mu, _d, _r, w = _glm_fit(x, y, family=fam, weights=fit.prior_weights, offset=fit.offset)
    w = fit.prior_weights
    if fam == "poisson":
        mu = np.clip(mu, 1e-12, None)
        terms = y * np.log(mu) - mu - np.array([math.lgamma(v + 1.0) for v in y])
        return float(np.sum(w * terms))
    if fam == "binomial":
        mu = np.clip(mu, 1e-12, 1 - 1e-12)
        terms = y * np.log(mu) + (1.0 - y) * np.log(1.0 - mu)
        return float(np.sum(w * terms))
    mu = np.asarray(mu, dtype=float)
    n = y.size
    rss = float(np.sum(w * (y - mu) ** 2))
    return float(-0.5 * n * (math.log(2 * math.pi) + math.log(rss / n)))


def _extract_aic_glm(fit: GlmFit, k: float) -> tuple[float, float]:
    ll = _glm_loglik(fit)
    aic = -2.0 * ll + k * fit.rank
    return float(fit.rank), float(aic)


def addterm(
    object,
    scope,
    *,
    scale: float = 0,
    test: str = "Chisq",
    k: float = 2,
    sorted_results: bool = False,
    trace: bool = False,
    **kwargs,
):
    if "sorted" in kwargs:
        sorted_results = bool(kwargs.pop("sorted"))
    if kwargs:
        raise MassError(f"unused arguments: {', '.join(sorted(kwargs))}")
    if isinstance(object, LmFit):
        return _addterm_lm(object, scope, scale=scale, test=test, k=k, sorted_results=sorted_results)
    if isinstance(object, GlmFit):
        return _addterm_glm(
            object, scope, scale=scale, test=test, k=k, sorted_results=sorted_results, trace=trace
        )
    raise MassError("addterm is implemented for glm and lm fits built by mass.addterm")


def _resolve_scope(object_formula: str, scope) -> list[str]:
    if scope is None:
        raise MassError("no terms in scope")
    if isinstance(scope, str):
        if scope.startswith("~"):
            maximal = _update_formula(object_formula, scope)
        else:
            maximal = _update_formula(object_formula, f"~ . + {scope}")
        terms = _add_scope(object_formula, maximal)
    elif isinstance(scope, (list, tuple)):
        terms = [str(item) for item in scope]
    else:
        raise MassError("scope must be a formula string or a list of term names")
    if not terms:
        raise MassError("no terms in scope for adding to object")
    return terms


def _addterm_glm(
    object: GlmFit,
    scope,
    *,
    scale: float = 0,
    test: str = "Chisq",
    k: float = 2,
    sorted_results: bool = False,
    trace: bool = False,
) -> AddtermTable:
    scope_terms = _resolve_scope(object.formula, scope)
    _, cur_rhs = _split_formula(object.formula)
    _int, o_terms = _parse_rhs_terms(cur_rhs)
    add_rhs = " + ".join(scope_terms)
    maximal = _update_formula(object.formula, f"~ . + {add_rhs}")
    x, y, _names, term_labels = _model_matrix(object.data, maximal)
    n = x.shape[0]
    wt = object.prior_weights
    offset = object.offset
    fam = object.family.lower()

    def sorted_term_label(term: str) -> str:
        return ":".join(sorted(term.split(":")))

    s_terms = [sorted_term_label(label) for label in term_labels]
    o_sorted = {sorted_term_label(t) for t in o_terms}

    base_cols = [i for i, label in enumerate(term_labels) if sorted_term_label(label) in o_sorted or label == "(Intercept)"]
    z_coef, _mu, dev0, rank0, _w = _glm_fit(
        x[:, base_cols],
        y,
        family=fam,
        weights=wt,
        offset=offset,
    )
    del z_coef
    dfs: dict[str, float] = {"<none>": float(rank0)}
    dev: dict[str, float] = {"<none>": float(dev0)}
    for tt in scope_terms:
        if trace:
            warnings.warn(f"trying + {tt}", stacklevel=2)
        stt = sorted_term_label(tt)
        usex = [i for i, label in enumerate(term_labels) if sorted_term_label(label) == stt]
        cols = sorted(set(base_cols) | set(usex))
        _c, _m, dev_i, rank_i, _ = _glm_fit(x[:, cols], y, family=fam, weights=wt, offset=offset)
        dfs[tt] = float(rank_i)
        dev[tt] = float(dev_i)

    if scale == 0:
        dispersion = object.dispersion
    else:
        dispersion = scale

    if fam == "gaussian":
        if scale > 0:
            loglik = {key: val / scale - n for key, val in dev.items()}
        else:
            loglik = {key: n * math.log(val / n) for key, val in dev.items()}
    else:
        loglik = {key: val / dispersion for key, val in dev.items()}

    aic = {key: loglik[key] + k * dfs[key] for key in dfs}
    baseline = _extract_aic_glm(object, k)[1]
    shift = baseline - aic["<none>"]
    aic = {key: val + shift for key, val in aic.items()}

    row_names = ["<none>"] + scope_terms
    df_change = {name: (math.nan if name == "<none>" else dfs[name] - dfs["<none>"]) for name in row_names}

    columns = ["Df", "Deviance", "AIC"]
    values: dict[tuple[str, str], float] = {}
    for name in row_names:
        values[(name, "Df")] = df_change[name]
        values[(name, "Deviance")] = dev[name]
        values[(name, "AIC")] = aic[name]

    test = _match_arg(test, ["none", "Chisq", "F"])
    if test == "Chisq":
        lrt = {name: max(0.0, loglik["<none>"] - loglik[name]) for name in row_names}
        lrt["<none>"] = math.nan
        columns.extend(["LRT", "Pr(Chi)"])
        for name in row_names:
            values[(name, "LRT")] = lrt[name]
            df_val = df_change[name]
            if name == "<none>" or (isinstance(df_val, float) and math.isnan(df_val)):
                values[(name, "Pr(Chi)")] = math.nan
            else:
                values[(name, "Pr(Chi)")] = _safe_pchisq(lrt[name], df_val, lower_tail=False)

    order = (
        sorted(range(len(row_names)), key=lambda i: aic[row_names[i]])
        if sorted_results
        else list(range(len(row_names)))
    )
    ordered_rows = [row_names[i] for i in order]
    head = ["Single term additions", "\nModel:", object.formula.replace(" ", "")]
    if scale > 0:
        head.append(f"\nscale: {scale}\n")
    return AddtermTable(columns=columns, rows=ordered_rows, values=values, heading=head)


def _addterm_lm(
    object: LmFit,
    scope,
    *,
    scale: float = 0,
    test: str = "Chisq",
    k: float = 2,
    sorted_results: bool = False,
) -> AddtermTable:
    scope_terms = _resolve_scope(object.formula, scope)
    x_base, y, _names, _labels = _model_matrix(object.data, object.formula)
    rss0, _ = _lm_fit(x_base, y)
    n = object.nobs
    row_names = ["<none>"] + scope_terms
    df_vals: dict[str, float] = {"<none>": math.nan}
    ss_vals: dict[str, float] = {"<none>": math.nan}
    rss_vals: dict[str, float] = {"<none>": rss0}
    for tt in scope_terms:
        formula = _update_formula(object.formula, f"~ . + {tt}")
        x_new, y_new, _, _ = _model_matrix(object.data, formula)
        rss, _rank = _lm_fit(x_new, y_new)
        df_vals[tt] = float(x_new.shape[1] - x_base.shape[1])
        ss_vals[tt] = rss0 - rss
        rss_vals[tt] = rss

    dfs = {name: (object.rank if name == "<none>" else object.rank + df_vals[name]) for name in row_names}
    if scale > 0:
        aic = {name: rss_vals[name] / scale - n + k * dfs[name] for name in row_names}
        columns = ["Df", "Sum of Sq", "RSS", "Cp"]
    else:
        aic = {name: n * math.log(rss_vals[name] / n) + k * dfs[name] for name in row_names}
        columns = ["Df", "Sum of Sq", "RSS", "AIC"]

    values: dict[tuple[str, str], float] = {}
    for name in row_names:
        values[(name, "Df")] = df_vals[name] if name != "<none>" else math.nan
        values[(name, "Sum of Sq")] = ss_vals[name]
        values[(name, "RSS")] = rss_vals[name]
        values[(name, columns[3])] = aic[name]

    test = _match_arg(test, ["none", "Chisq", "F"])
    if test == "Chisq":
        if scale == 0:
            dev_base = n * math.log(rss0 / n)
            dev = {name: n * math.log(rss_vals[name] / n) for name in row_names}
            chisq = {name: dev_base - dev[name] for name in row_names}
        else:
            chisq = {name: ss_vals[name] / scale for name in row_names}
        chisq["<none>"] = math.nan
        columns.append("Pr(Chi)")
        for name in row_names:
            if name == "<none>":
                values[(name, "Pr(Chi)")] = math.nan
            else:
                values[(name, "Pr(Chi)")] = _safe_pchisq(chisq[name], df_vals[name], lower_tail=False)
    elif test == "F":
        rdf = object.df_residual
        columns.extend(["F Value", "Pr(F)"])
        for name in row_names:
            if name == "<none>":
                values[(name, "F Value")] = math.nan
                values[(name, "Pr(F)")] = math.nan
            else:
                df1 = df_vals[name]
                ms_reg = ss_vals[name] / df1
                ms_res = (rss0 - ss_vals[name]) / (rdf - df1)
                f_val = ms_reg / ms_res
                values[(name, "F Value")] = f_val
                values[(name, "Pr(F)")] = _safe_pf(f_val, df1, rdf - df1, lower_tail=False)

    order = (
        sorted(range(len(row_names)), key=lambda i: aic[row_names[i]])
        if sorted_results
        else list(range(len(row_names)))
    )
    ordered_rows = [row_names[i] for i in order]
    head = ["Single term additions", "\nModel:", object.formula.replace(" ", "")]
    if scale > 0:
        head.append(f"\nscale: {scale}\n")
    return AddtermTable(columns=columns, rows=ordered_rows, values=values, heading=head)
