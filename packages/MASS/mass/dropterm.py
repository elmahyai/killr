"""Try all one-term deletions from a model (MASS dropterm, glm and lm methods)."""

from __future__ import annotations

import math
import warnings

from mass.addterm import (
    AddtermTable,
    GlmFit,
    LmFit,
    _extract_aic_glm,
    _glm_fit,
    _lm_fit,
    _match_arg,
    _model_matrix,
    _parse_rhs_terms,
    _safe_pf,
    _safe_pchisq,
    _split_formula,
    _update_formula,
)
from mass.errors import MassError


def _sorted_term_label(term: str) -> str:
    return ":".join(sorted(term.split(":")))


def _remove_term(formula: str, term: str) -> str:
    resp, rhs = _split_formula(formula)
    intercept, terms = _parse_rhs_terms(rhs)
    st = _sorted_term_label(term)
    new_terms = [t for t in terms if _sorted_term_label(t) != st]
    rhs_out = " + ".join(new_terms)
    if intercept:
        rhs_out = ("1 + " + rhs_out) if rhs_out else "1"
    elif not rhs_out:
        rhs_out = "0"
    return f"{resp} ~ {rhs_out}"


def _resolve_drop_scope(object_formula: str, scope) -> list[str]:
    _, cur_rhs = _split_formula(object_formula)
    _int, cur_terms = _parse_rhs_terms(cur_rhs)
    cur_labels = {_sorted_term_label(t) for t in cur_terms}

    if scope is None:
        scope_terms = list(cur_terms)
    elif isinstance(scope, str):
        if scope.startswith("~"):
            updated = _update_formula(object_formula, scope)
            _, rhs = _split_formula(updated)
            _int, scope_terms = _parse_rhs_terms(rhs)
        else:
            scope_terms = [scope]
    elif isinstance(scope, (list, tuple)):
        scope_terms = [str(item) for item in scope]
    else:
        raise MassError("scope must be a formula string or a list of term names")

    if not scope_terms:
        raise MassError("no terms in scope")
    for tt in scope_terms:
        if _sorted_term_label(tt) not in cur_labels:
            raise MassError("scope is not a subset of term labels")
    return scope_terms


def dropterm(
    object,
    scope=None,
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
        return _dropterm_lm(
            object, scope, scale=scale, test=test, k=k, sorted_results=sorted_results
        )
    if isinstance(object, GlmFit):
        return _dropterm_glm(
            object,
            scope,
            scale=scale,
            test=test,
            k=k,
            sorted_results=sorted_results,
            trace=trace,
        )
    raise MassError("dropterm is implemented for glm and lm fits built by mass.addterm")


def _dropterm_glm(
    object: GlmFit,
    scope,
    *,
    scale: float = 0,
    test: str = "Chisq",
    k: float = 2,
    sorted_results: bool = False,
    trace: bool = False,
) -> AddtermTable:
    scope_terms = _resolve_drop_scope(object.formula, scope)
    _, cur_rhs = _split_formula(object.formula)
    _int, o_terms = _parse_rhs_terms(cur_rhs)
    o_labels = {_sorted_term_label(t) for t in o_terms}

    x, y, _names, term_labels = _model_matrix(object.data, object.formula)
    n = x.shape[0]
    wt = object.prior_weights
    offset = object.offset
    fam = object.family.lower()
    base_cols = [
        i
        for i, label in enumerate(term_labels)
        if _sorted_term_label(label) in o_labels or label == "(Intercept)"
    ]

    dfs: dict[str, float] = {"<none>": float(object.rank)}
    dev: dict[str, float] = {"<none>": float(object.deviance)}

    for tt in scope_terms:
        if trace:
            warnings.warn(f"trying - {tt}", stacklevel=2)
        stt = _sorted_term_label(tt)
        cols = [i for i in base_cols if _sorted_term_label(term_labels[i]) != stt]
        _c, _m, dev_i, rank_i, _ = _glm_fit(x[:, cols], y, family=fam, weights=wt, offset=offset)
        dfs[tt] = float(rank_i)
        dev[tt] = float(dev_i)

    dispersion = object.dispersion if scale == 0 else scale
    if fam == "gaussian":
        loglik = (
            {key: val / scale - n for key, val in dev.items()}
            if scale > 0
            else {key: n * math.log(val / n) for key, val in dev.items()}
        )
    else:
        loglik = {key: val / dispersion for key, val in dev.items()}

    aic = {key: loglik[key] + k * dfs[key] for key in dfs}
    baseline = _extract_aic_glm(object, k)[1]
    aic = {key: val + (baseline - aic["<none>"]) for key, val in aic.items()}

    row_names = ["<none>"] + list(scope_terms)
    df_change = {name: (math.nan if name == "<none>" else dfs["<none>"] - dfs[name]) for name in row_names}

    columns = ["Df", "Deviance", "AIC"]
    values: dict[tuple[str, str], float] = {}
    for name in row_names:
        values[(name, "Df")] = df_change[name]
        values[(name, "Deviance")] = dev[name]
        values[(name, "AIC")] = aic[name]

    test = _match_arg(test, ["none", "Chisq", "F"])
    lrt_name = "LRT" if dispersion == 1.0 else "scaled dev."
    if test == "Chisq":
        lrt = {name: max(0.0, loglik[name] - loglik["<none>"]) for name in row_names}
        lrt["<none>"] = math.nan
        columns.extend([lrt_name, "Pr(Chi)"])
        for name in row_names:
            values[(name, lrt_name)] = lrt[name]
            df_val = df_change[name]
            if name == "<none>" or (isinstance(df_val, float) and math.isnan(df_val)):
                values[(name, "Pr(Chi)")] = math.nan
            else:
                values[(name, "Pr(Chi)")] = _safe_pchisq(lrt[name], df_val, lower_tail=False)
    elif test == "F":
        if fam in {"binomial", "poisson"}:
            warnings.warn(f"F test assumes 'quasi{fam}' family", stacklevel=2)
        rdf = float(object.df_residual)
        dev0 = dev["<none>"]
        rms = dev0 / rdf
        columns.extend(["F value", "Pr(F)"])
        for name in row_names:
            if name == "<none>":
                values[(name, "F value")] = math.nan
                values[(name, "Pr(F)")] = math.nan
            else:
                dev_drop = max(0.0, dev[name] - dev0)
                df_val = df_change[name]
                if isinstance(df_val, float) and df_val < 1e-4:
                    values[(name, "F value")] = math.nan
                    values[(name, "Pr(F)")] = math.nan
                else:
                    f_val = (dev_drop / df_val) / rms
                    values[(name, "F value")] = f_val
                    values[(name, "Pr(F)")] = _safe_pf(f_val, df_val, rdf, lower_tail=False)

    order = (
        sorted(range(len(row_names)), key=lambda i: aic[row_names[i]])
        if sorted_results
        else list(range(len(row_names)))
    )
    ordered_rows = [row_names[i] for i in order]
    head = ["Single term deletions", "\nModel:", object.formula.replace(" ", "")]
    if scale > 0:
        head.append(f"\nscale: {scale}\n")
    return AddtermTable(columns=columns, rows=ordered_rows, values=values, heading=head)


def _dropterm_lm(
    object: LmFit,
    scope,
    *,
    scale: float = 0,
    test: str = "Chisq",
    k: float = 2,
    sorted_results: bool = False,
) -> AddtermTable:
    scope_terms = _resolve_drop_scope(object.formula, scope)
    x_base, y, _names, _labels = _model_matrix(object.data, object.formula)
    rss0, _ = _lm_fit(x_base, y)
    n = object.nobs
    row_names = ["<none>"] + scope_terms
    df_vals: dict[str, float] = {"<none>": math.nan}
    ss_vals: dict[str, float] = {"<none>": math.nan}
    rss_vals: dict[str, float] = {"<none>": rss0}
    for tt in scope_terms:
        formula = _remove_term(object.formula, tt)
        x_new, y_new, _, _ = _model_matrix(object.data, formula)
        rss, _rank = _lm_fit(x_new, y_new)
        df_vals[tt] = float(x_base.shape[1] - x_new.shape[1])
        ss_vals[tt] = rss - rss0
        rss_vals[tt] = rss

    dfs = {name: (object.rank if name == "<none>" else object.rank - df_vals[name]) for name in row_names}
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
    head = ["Single term deletions", "\nModel:", object.formula.replace(" ", "")]
    if scale > 0:
        head.append(f"\nscale: {scale}\n")
    return AddtermTable(columns=columns, rows=ordered_rows, values=values, heading=head)
