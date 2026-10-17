"""Stepwise model selection by AIC (MASS stepAIC, glm and lm)."""

from __future__ import annotations

import math
import warnings
from dataclasses import dataclass

from mass.addterm import (
    AddtermTable,
    GlmFit,
    LmFit,
    _add_scope,
    _extract_aic_glm,
    _glm_fit,
    _match_arg,
    _model_matrix,
    _parse_rhs_terms,
    _safe_pchisq,
    _split_formula,
    _update_formula,
    addterm,
    glm,
)
from mass.errors import MassError


def _sorted_term_label(term: str) -> str:
    return ":".join(sorted(term.split(":")))


def _current_terms(formula: str) -> list[str]:
    _, rhs = _split_formula(formula)
    _int, terms = _parse_rhs_terms(rhs)
    return terms


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


def _formula_from_scope(object_formula: str, scope_rhs: str) -> str:
    resp, _ = _split_formula(object_formula)
    text = str(scope_rhs).strip()
    if text.startswith("~"):
        _, rhs = _split_formula(text)
    else:
        rhs = text
    return f"{resp} ~ {rhs}"


def _scope_terms(scope_arg, object_formula: str) -> tuple[list[str], list[str]]:
    """Main-effect drop/add lists matching factor.scope for our formulas."""
    cur = _current_terms(object_formula)
    if scope_arg is None:
        return list(cur), []

    if isinstance(scope_arg, str):
        upper_formula = _formula_from_scope(object_formula, scope_arg)
        return list(cur), _add_scope(object_formula, upper_formula)

    if isinstance(scope_arg, dict):
        lower_terms: list[str] = []
        lower = scope_arg.get("lower")
        if lower is not None:
            lower_terms = _current_terms(_formula_from_scope(object_formula, lower))
        add: list[str] = []
        upper = scope_arg.get("upper")
        if upper is not None:
            add = _add_scope(object_formula, _formula_from_scope(object_formula, upper))
        drop = [t for t in cur if t not in lower_terms]
        return drop, add

    raise MassError("scope must be a formula string or a dict with upper and/or lower")


def _dropterm_glm(
    object: GlmFit,
    scope: list[str],
    *,
    scale: float = 0,
    k: float = 2,
    trace: bool = False,
) -> AddtermTable:
    if not scope:
        raise MassError("no terms in scope")
    _, cur_rhs = _split_formula(object.formula)
    _int, o_terms = _parse_rhs_terms(cur_rhs)
    o_labels = {_sorted_term_label(t) for t in o_terms}
    for tt in scope:
        if _sorted_term_label(tt) not in o_labels:
            raise MassError("scope is not a subset of term labels")

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

    for tt in scope:
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

    row_names = ["<none>"] + list(scope)
    df_change = {name: (math.nan if name == "<none>" else dfs["<none>"] - dfs[name]) for name in row_names}

    columns = ["Df", "Deviance", "AIC"]
    values: dict[tuple[str, str], float] = {}
    for name in row_names:
        values[(name, "Df")] = df_change[name]
        values[(name, "Deviance")] = dev[name]
        values[(name, "AIC")] = aic[name]

    dev_lrt = {name: max(0.0, loglik["<none>"] - loglik[name]) for name in row_names}
    dev_lrt["<none>"] = math.nan
    columns.extend(["LRT", "Pr(Chi)"])
    for name in row_names:
        values[(name, "LRT")] = dev_lrt[name]
        df_val = df_change[name]
        if name == "<none>" or (isinstance(df_val, float) and math.isnan(df_val)):
            values[(name, "Pr(Chi)")] = math.nan
        else:
            values[(name, "Pr(Chi)")] = _safe_pchisq(dev_lrt[name], df_val, lower_tail=False)

    head = ["Single term deletions", "\nModel:", object.formula.replace(" ", "")]
    return AddtermTable(columns=columns, rows=row_names, values=values, heading=head)


def _dropterm(object, scope: list[str], **kwargs) -> AddtermTable:
    if isinstance(object, GlmFit):
        return _dropterm_glm(object, scope, **kwargs)
    raise MassError("stepAIC dropterm is implemented for glm fits in this translation")


def _apply_change(formula: str, change: str) -> str:
    text = change.strip()
    if text.startswith("+"):
        return _update_formula(formula, f"~ . + {text[1:].strip()}")
    if text.startswith("-"):
        return _remove_term(formula, text[1:].strip())
    raise MassError(f"unknown model change {change!r}")


def _table_aic_key(table: AddtermTable) -> str:
    if "Cp" in table.columns:
        return "Cp"
    return "AIC"


def _label_rows(table: AddtermTable, prefix: str) -> list[str]:
    rows = list(table.rows)
    return [rows[0]] + [f"{prefix} {name}" for name in rows[1:]]


@dataclass
class StepAICResult:
    fit: GlmFit | LmFit
    anova: AddtermTable
    keep: object | None = None

    @property
    def deviance(self) -> float:
        if isinstance(self.fit, GlmFit):
            return self.fit.deviance
        return self.fit.rss

    @property
    def rank(self) -> int:
        return self.fit.rank


def _step_results(models: list[dict], fit, initial_formula: str, using_cp: bool) -> AddtermTable:
    rd = [m["deviance"] for m in models]
    dd = [math.nan] + [abs(rd[i] - rd[i - 1]) for i in range(1, len(rd))]
    rdf = [m["df.resid"] for m in models]
    ddf = [math.nan] + [abs(rdf[i] - rdf[i - 1]) for i in range(1, len(rdf))]
    aic_name = "Cp" if using_cp else "AIC"
    columns = ["Step", "Df", "Deviance", "Resid. Df", "Resid. Dev", aic_name]
    rows = [str(i + 1) for i in range(len(models))]
    values: dict[tuple[str, str], float | str] = {}
    for i, row in enumerate(rows):
        values[(row, "Step")] = models[i]["change"]
        values[(row, "Df")] = ddf[i]
        values[(row, "Deviance")] = dd[i]
        values[(row, "Resid. Df")] = float(rdf[i])
        values[(row, "Resid. Dev")] = float(rd[i])
        values[(row, aic_name)] = float(models[i]["AIC"])
    heading = [
        "Stepwise Model Path \nAnalysis of Deviance Table",
        "\nInitial Model:",
        initial_formula.replace(" ", ""),
        "\nFinal Model:",
        fit.formula.replace(" ", ""),
        "\n",
    ]
    return AddtermTable(columns=columns, rows=rows, values=values, heading=heading)


def stepAIC(
    object,
    scope=None,
    *,
    scale: float = 0,
    direction: str | None = None,
    trace: int = 1,
    keep=None,
    steps: int = 1000,
    use_start: bool = False,
    k: float = 2,
    **kwargs,
):
    if kwargs:
        raise MassError(f"unused arguments: {', '.join(sorted(kwargs))}")
    if use_start:
        warnings.warn("'use.start' cannot be used with R's version of 'glm'", stacklevel=2)
    if not isinstance(object, GlmFit):
        raise MassError("stepAIC is implemented for glm fits built by mass.addterm")

    direction_missing = direction is None
    direction = _match_arg(direction if direction is not None else "both", ["both", "backward", "forward"])
    backward = direction in {"both", "backward"}
    forward = direction in {"both", "forward"}

    initial_formula = object.formula
    _drop_seed, add_seed = _scope_terms(scope, object.formula)
    if scope is None and direction_missing:
        forward = False

    n = object.nobs
    fit = object
    edf, b_aic = _extract_aic_glm(fit, k)
    if math.isnan(b_aic):
        raise MassError("AIC is not defined for this model, so 'stepAIC' cannot proceed")
    if b_aic == -math.inf:
        raise MassError("AIC is -infinity for this model, so 'stepAIC' cannot proceed")

    if trace:
        print(f"Start:  AIC= {round(b_aic, 2):.2f}\n{fit.formula}\n\n")

    models = [
        {
            "deviance": float(fit.deviance),
            "df.resid": n - edf,
            "change": "",
            "AIC": b_aic,
        }
    ]
    using_cp = False

    while steps > 0:
        steps -= 1
        aic_prev = b_aic
        drop_scope, add_scope = _scope_terms(scope, fit.formula)
        if scope is None:
            add_scope = add_seed if forward else []
            drop_scope = _current_terms(fit.formula)

        aod: AddtermTable | None = None
        row_labels: list[str] = []
        change: str | None = None

        if backward and drop_scope:
            aod_drop = _dropterm(fit, drop_scope, scale=scale, trace=trace > 1, k=k)
            drop_labels = _label_rows(aod_drop, "-")
            rows = list(aod_drop.rows)
            nc = _table_aic_key(aod_drop)
            zdf_idx = [
                i
                for i, row in enumerate(rows)
                if i > 0 and aod_drop.values.get((row, "Df")) == 0
            ]
            if zdf_idx:
                base = aod_drop.values.get((rows[0], nc))
                ch_flags = []
                for i in zdf_idx:
                    row_aic = aod_drop.values.get((rows[i], nc))
                    ch_flags.append(
                        row_aic is not None
                        and base is not None
                        and abs(row_aic - base) > 0.01
                    )
                if any(ch_flags):
                    warnings.warn("0 df terms are changing AIC", stacklevel=2)
                    zdf_idx = [i for i, flag in zip(zdf_idx, ch_flags) if not flag]
                if zdf_idx:
                    change = drop_labels[zdf_idx[-1]]
            aod = aod_drop
            row_labels = drop_labels

        if change is None:
            if forward and add_scope:
                aod_fwd = addterm(fit, add_scope, scale=scale, trace=trace > 1, k=k)
                fwd_labels = _label_rows(aod_fwd, "+")
                if aod is None:
                    aod = aod_fwd
                    row_labels = fwd_labels
                else:
                    merged_rows = list(aod.rows) + list(aod_fwd.rows[1:])
                    values = dict(aod.values)
                    for row in aod_fwd.rows[1:]:
                        for col in aod_fwd.columns:
                            values[(row, col)] = aod_fwd.values[(row, col)]
                    aod = AddtermTable(columns=list(aod.columns), rows=merged_rows, values=values)
                    row_labels = row_labels + fwd_labels[1:]

            if aod is None or not aod.columns:
                break

            nc = _table_aic_key(aod)
            nzdf_rows: list[tuple[int, str]] = []
            for i, row in enumerate(aod.rows):
                df_val = aod.values.get((row, "Df"))
                if df_val == 0 and not (isinstance(df_val, float) and math.isnan(df_val)):
                    continue
                nzdf_rows.append((i, row))

            if not nzdf_rows:
                break

            aic_order = sorted(
                nzdf_rows,
                key=lambda pair: float(aod.values.get((pair[1], nc)) or math.inf),
            )
            best_i, best_row = aic_order[0]
            if best_i == 0:
                break
            change = row_labels[best_i] if best_i < len(row_labels) else best_row
            if trace:
                ordered = aic_order
                print("term comparisons:")
                for i, row in ordered:
                    print(
                        f"  {row_labels[i] if i < len(row_labels) else row}: "
                        f"{aod.values.get((row, nc))}"
                    )

        using_cp = aod is not None and "Cp" in aod.columns
        new_formula = _apply_change(fit.formula, change)
        fit = glm(new_formula, fit.data, family=fit.family)
        edf, b_aic = _extract_aic_glm(fit, k)
        if trace:
            print(f"\nStep:  AIC= {round(b_aic, 2):.2f}\n{fit.formula}\n\n")
        if b_aic >= aic_prev + 1e-7:
            break
        models.append(
            {
                "deviance": float(fit.deviance),
                "df.resid": n - edf,
                "change": change.strip(),
                "AIC": b_aic,
            }
        )

    anova = _step_results(models, fit, initial_formula, using_cp)
    return StepAICResult(fit=fit, anova=anova, keep=keep)
