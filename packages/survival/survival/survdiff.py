"""Log-rank and G-rho tests for survival curves (survival::survdiff)."""

from __future__ import annotations

import math
import re
from typing import Any, Mapping

import numpy as np
from scipy.special import chdtrc
from survdiff2 import survdiff2 as _survdiff2_kernel

from survival.fromtimeline import Categorical
from survival.pyears import _eval_expr, _has_interaction, _split_terms
from survival.strata import StrataFactor
from survival.surv import SurvObject, aeqSurv, is_Surv
from survival.surv_split import _apply_subset, _as_table

_STRATA_RE = re.compile(r"^strata\s*\((.*)\)$", re.DOTALL)
_OFFSET_RE = re.compile(r"^offset\s*\((.*)\)$", re.DOTALL)


def _split_args(text: str) -> list[str]:
    parts: list[str] = []
    depth = 0
    start = 0
    for i, ch in enumerate(text):
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        elif ch == "," and depth == 0:
            parts.append(text[start:i].strip())
            start = i + 1
    parts.append(text[start:].strip())
    return [part for part in parts if part]


def _is_missing(value: Any) -> bool:
    return value is None or (isinstance(value, float) and math.isnan(value))


def _plain(col: Any) -> tuple[list[Any], list[Any] | None]:
    """Return (values, levels). levels is None for a vector without factor levels."""
    if isinstance(col, StrataFactor):
        values = [None if code is None else col.levels[code - 1] for code in col.codes]
        return values, list(col.levels)
    if isinstance(col, Categorical):
        return list(col.values), list(col.levels)
    if isinstance(col, np.ndarray):
        return col.tolist(), None
    if isinstance(col, (list, tuple)):
        return list(col), None
    raise TypeError("unsupported variable type in survdiff")


def _sort_key(value: Any) -> tuple[int, str, float]:
    if isinstance(value, str):
        return (1, value, 0.0)
    return (0, "", float(value))


def _factor_codes(values: list[Any], levels: list[Any] | None) -> list[int]:
    """1-based codes, as R's as.numeric(factor(x)). Levels are sorted when not given."""
    ordered = list(levels) if levels is not None else sorted(set(values), key=_sort_key)
    index: dict[Any, int] = {}
    for code, level in enumerate(ordered, start=1):
        index.setdefault(level, code)
    return [index[value] for value in values]


def _combine(columns: list[list[int]]) -> list[int]:
    """Rank of each row's code tuple, as R's strata() over several variables."""
    tuples = list(zip(*columns))
    ordered = sorted(set(tuples))
    index = {tup: rank for rank, tup in enumerate(ordered, start=1)}
    return [index[tup] for tup in tuples]


def survdiff_fit(time, status, x, strat=None, rho: float = 0.0) -> dict[str, Any]:
    """Observed, expected, and variance for each group (survival::survdiff.fit).

    `x` holds 1-based group codes and `strat` holds 1-based stratum codes.
    """
    time = np.asarray(time, dtype=float).reshape(-1)
    status = np.asarray(status, dtype=int).reshape(-1)
    x = np.asarray(x, dtype=int).reshape(-1)
    n = x.shape[0]
    if strat is None:
        strat = np.ones(n, dtype=int)
    strat = np.asarray(strat, dtype=int).reshape(-1)
    if time.shape[0] != n or status.shape[0] != n or strat.shape[0] != n:
        raise ValueError("Data length mismatch")
    ngroup = int(np.unique(x).size)
    if ngroup < 2:
        raise ValueError("There is only 1 group")
    nstrat = int(np.unique(strat).size)

    order = np.lexsort((-status, time, strat))
    strat_sorted = strat[order]
    strat2 = np.append((np.diff(strat_sorted) != 0).astype(np.int32), 1)

    obs, exp, var = _survdiff2_kernel(
        float(rho),
        time[order].tolist(),
        status[order].tolist(),
        x[order].tolist(),
        strat2.tolist(),
        ngroup,
        nstrat,
    )
    observed = np.asarray(obs, dtype=float)
    expected = np.asarray(exp, dtype=float)
    variance = np.asarray(var, dtype=float).reshape((ngroup, ngroup), order="F")
    if nstrat > 1:
        observed = observed.reshape((ngroup, nstrat), order="F")
        expected = expected.reshape((ngroup, nstrat), order="F")
    return {"expected": expected, "observed": observed, "var": variance}


def survdiff(
    formula: str,
    data: Mapping[str, Any] | None = None,
    subset=None,
    na_action=None,
    rho: float = 0,
    timefix: bool = True,
) -> dict[str, Any]:
    """Test equality of survival curves with the log-rank (rho = 0) or G-rho test."""
    if na_action is not None:
        raise NotImplementedError("na.action is not supported yet")
    if formula is None or "~" not in formula:
        raise ValueError("A formula argument is required")
    if not isinstance(timefix, bool):
        raise ValueError("invalid value for timefix option")

    table, _ = _apply_subset(_as_table(data or {}), subset)
    env = dict(table)
    lhs, rhs = formula.split("~", 1)
    response = _eval_expr(lhs.strip(), env)
    if not is_Surv(response):
        raise ValueError("Response must be a survival object")

    group_terms: list[str] = []
    strata_terms: list[list[str]] = []
    offset_terms: list[str] = []
    for term in _split_terms(rhs.strip()):
        if term == "1":
            continue
        if term == ".":
            raise NotImplementedError("formula dot is not supported yet")
        if _has_interaction(term):
            raise NotImplementedError("interaction terms are not supported yet")
        match = _STRATA_RE.match(term)
        if match:
            strata_terms.append(_split_args(match.group(1)))
            continue
        match = _OFFSET_RE.match(term)
        if match:
            offset_terms.append(match.group(1).strip())
            continue
        group_terms.append(term)

    strata_vars: list[str] = []
    for args in strata_terms:
        for arg in args:
            if arg not in strata_vars:
                strata_vars.append(arg)

    if len(offset_terms) > 1:
        raise NotImplementedError("more than one offset term is not supported")

    if offset_terms and (group_terms or strata_terms):
        raise ValueError("Cannot have both an offset and groups")

    group_cols = [_plain(_eval_expr(term, env)) for term in group_terms]
    strata_cols = [_plain(_eval_expr(name, env)) for name in strata_vars]
    offset_col = _plain(_eval_expr(offset_terms[0], env)) if offset_terms else None

    keep = ~np.isnan(response.columns).any(axis=1)
    for values, _levels in [*group_cols, *strata_cols, *([offset_col] if offset_col else [])]:
        keep &= np.array([not _is_missing(value) for value in values], dtype=bool)

    def filtered(col: tuple[list[Any], list[Any] | None]) -> tuple[list[Any], list[Any] | None]:
        values, levels = col
        return [value for value, flag in zip(values, keep) if flag], levels

    y = SurvObject(response.columns[keep], response.type, response.states, response.clabel)
    kind = y.type
    if kind in ("mright", "mcounting"):
        raise ValueError("survdiff not defined for multi-state data")
    if kind == "counting":
        raise ValueError("survdiff not defined for counting process data")
    if kind != "right":
        raise ValueError("Right censored data only")

    if timefix:
        y = aeqSurv(y)
    n = len(y)
    status = y.columns[:, 1]

    if offset_col is not None:
        offset_values, _ = filtered(offset_col)
        offset = np.asarray(offset_values, dtype=float)
        if np.any((offset < 0) | (offset > 1)):
            raise ValueError("The offset must be a survival probability")
        expected = float(np.sum(-np.log(offset)))
        observed = float(np.sum(status))
        if rho != 0:
            num = float(np.sum(1 / rho - ((1 / rho + status) * offset**rho)))
            var = float(np.sum(1 - offset ** (2 * rho)) / (2 * rho))
        else:
            var = float(np.sum(-np.log(offset)))
            num = observed - var
        chi = num * num / var
        return {
            "n": n,
            "obs": observed,
            "exp": expected,
            "var": var,
            "chisq": chi,
            "pvalue": float(chdtrc(1, chi)),
        }

    if not group_terms:
        raise ValueError("No groups to test")

    group_codes = _combine([_factor_codes(*filtered(col)) for col in group_cols])

    strat_codes = None
    if strata_vars:
        if len(strata_cols) == 1:
            strat_codes = _factor_codes(*filtered(strata_cols[0]))
        else:
            strat_codes = _combine([_factor_codes(*filtered(col)) for col in strata_cols])

    fit = survdiff_fit(y.columns[:, 0], status, group_codes, strat_codes, rho)
    observed = fit["observed"]
    expected = fit["expected"]
    if observed.ndim == 2:
        otmp = observed.sum(axis=1)
        etmp = expected.sum(axis=1)
    else:
        otmp = observed
        etmp = expected
    present = etmp > 0
    if int(present.sum()) < 2:
        chi = 0.0
    else:
        idx = np.flatnonzero(present)
        temp2 = (otmp - etmp)[idx][1:]
        vv = fit["var"][np.ix_(idx, idx)][1:, 1:]
        chi = float(np.sum(np.linalg.solve(vv, temp2) * temp2))
    df = int(present.sum()) - 1
    if df > 0:
        pvalue = float(chdtrc(df, chi))
    elif df == 0:
        # R: pchisq(0, 0, lower.tail = FALSE) is 1, and chi is 0 when df is 0.
        pvalue = 1.0 if chi == 0 else 0.0
    else:
        pvalue = math.nan

    out: dict[str, Any] = {
        "n": np.unique(np.asarray(group_codes), return_counts=True)[1],
        "obs": observed,
        "exp": expected,
        "var": fit["var"],
        "chisq": chi,
        "pvalue": pvalue,
    }
    if strat_codes is not None:
        out["strata"] = np.unique(np.asarray(strat_codes), return_counts=True)[1]
    return out
