"""Formula method for survival curves (survival::survfit.formula).

The formula is read as `Surv(...) ~ terms`. Each right-hand term is a column
or an expression of columns, and the curves are one per combination of the
term levels. `strata(x)` is accepted as a term and labelled as R does. Left and
interval censoring go through `survfit`, which waits on survfitTurnbull.

Factor levels are sorted as R's `factor()` sorts them, not in order of first
appearance. Labels for the second and later variables are padded to a common
width, as R's `format()` pads them.
"""

from __future__ import annotations

import math
import re
from typing import Any

import numpy as np

from survival.fromtimeline import Categorical, TimelineFrame, _surv2counting
from survival.pyears import _eval_expr, _has_interaction, _split_terms
from survival.strata import StrataFactor
from survival.surv import aeqSurv, is_Surv
from survival.surv2 import Surv2Object
from survival.survcheck import _apply_na_action, _build_response, _parse_surv_lhs, _survcheck2
from survival.surv_split import _apply_subset, _as_table
from survival.survfit import survfit

_STRATA_RE = re.compile(r"^strata\s*\((.*)\)$", re.DOTALL)
_SPECIAL_RE = re.compile(r"^(cluster|tt)\s*\(", re.IGNORECASE)
_LEFT_INTERVAL_RE = re.compile(r"type\s*=\s*['\"](left|interval|interval2)['\"]")


def _missing(value: Any) -> bool:
    return value is None or (isinstance(value, float) and math.isnan(value))


def _frame_column(col: Any) -> Any:
    """Store a column so that model-frame row operations can read it."""
    if isinstance(col, StrataFactor):
        return Categorical([None if c is None else col.levels[c - 1] for c in col.codes], col.levels)
    if isinstance(col, Categorical) or is_Surv(col) or isinstance(col, Surv2Object):
        return col
    if isinstance(col, np.ndarray):
        if col.dtype.kind == "f":
            return col
        return col.tolist()
    if isinstance(col, (str, bytes)):
        raise ValueError("a formula variable must have one value per row")
    return list(col)


def _sort_key(value: Any) -> tuple[int, str, float]:
    if isinstance(value, str):
        return (1, value, 0.0)
    return (0, "", float(value))


def _r_label(value: Any) -> str:
    """as.character() for one factor level."""
    if isinstance(value, (bool, np.bool_)):
        return "TRUE" if value else "FALSE"
    if isinstance(value, str):
        return value
    number = float(value)
    if number == int(number) and abs(number) < 1e15:
        return str(int(number))
    return f"{number:.15g}"


def _factor_of(col: Any) -> StrataFactor:
    """R factor(): the levels are the sorted unique values, or the given levels."""
    if isinstance(col, Categorical):
        levels = list(col.levels)
        index = {level: code for code, level in enumerate(levels, start=1)}
        return StrataFactor([None if _missing(v) else index[v] for v in col.values], levels)
    values = list(col)
    keys = sorted({v for v in values if not _missing(v)}, key=_sort_key)
    index = {key: code for code, key in enumerate(keys, start=1)}
    return StrataFactor([None if _missing(v) else index[v] for v in values], [_r_label(k) for k in keys])


def _combine(names: list[str], factors: list[StrataFactor]) -> StrataFactor:
    """R strata(mf[ll]) with named arguments: labels `name=level`, padded after the first."""
    labs = [f"{names[0]}={level}" for level in factors[0].levels]
    levs = [None if c is None else c - 1 for c in factors[0].codes]
    for name, factor in zip(names[1:], factors[1:]):
        wlab = [f"{name}={level}" for level in factor.levels]
        width = max((len(item) for item in wlab), default=0)
        wlab = [item.ljust(width) for item in wlab]
        wlev = [None if c is None else c - 1 for c in factor.codes]
        levs = [None if a is None or b is None else b + a * len(wlab) for a, b in zip(levs, wlev)]
        labs = [f"{a}, {b}" for a in labs for b in wlab]
    present = sorted({item for item in levs if item is not None})
    index = {code: pos for pos, code in enumerate(present, start=1)}
    return StrataFactor([None if item is None else index[item] for item in levs], [labs[code] for code in present])


def _rhs_terms(rhs: str) -> list[str]:
    text = rhs.strip()
    if text == ".":
        raise NotImplementedError("formula dot is not supported yet")
    if text in ("1", ""):
        return []
    terms = []
    for term in _split_terms(text):
        if term == "1":
            continue
        if term == ".":
            raise NotImplementedError("formula dot is not supported yet")
        if _has_interaction(term):
            raise ValueError("Interaction terms are not valid for this function")
        if _SPECIAL_RE.match(term):
            raise NotImplementedError(f"{term.split('(', 1)[0]}() terms are not supported yet in survfit.formula")
        terms.append(term)
    return terms


def _eval_term(term: str, table: dict[str, Any]) -> Any:
    expr = term
    match = _STRATA_RE.match(term)
    if match:
        inner = match.group(1).strip()
        if "," in inner:
            raise NotImplementedError("strata() with more than one variable is not supported yet")
        expr = inner
    try:
        return _frame_column(_eval_expr(expr, table))
    except NameError as exc:
        raise ValueError(f"object '{exc.args[0]}' not found") from exc


def survfit_formula(
    formula,
    data=None,
    weights=None,
    subset=None,
    na_action=None,
    stype=1,
    ctype=1,
    id=None,
    cluster=None,
    robust=None,
    istate=None,
    timefix=True,
    entry=False,
    time0=False,
    **kwargs,
):
    """Survival curves from a formula (survival::survfit.formula).

    `formula` is a string such as `"Surv(time, status) ~ group"`, and `data` is
    a mapping of column names to values. `weights`, `id`, `cluster`, and
    `istate` may be column names or vectors. Extra keyword arguments go to
    `survfit` (for example `conf_int`, `conf_type`, `start_time`).
    """
    if formula is None or "~" not in str(formula):
        raise ValueError("a formula argument is required")
    if data is None:
        raise ValueError("data argument is required")
    if not isinstance(time0, (bool, np.bool_)):
        raise ValueError("time0 must be TRUE/FALSE")
    if not isinstance(timefix, (bool, np.bool_)):
        raise ValueError("invalid value for timefix option")

    text = str(formula)
    lhs, rhs = text.split("~", 1)
    if _LEFT_INTERVAL_RE.search(lhs):
        raise NotImplementedError("waiting on survfitTurnbull")
    is_surv2, lhs_names = _parse_surv_lhs(lhs)
    table = dict(_as_table(data))
    for name in lhs_names:
        if name not in table:
            raise ValueError(f"object '{name}' not found")
    terms = _rhs_terms(rhs)

    extras: dict[str, Any] = {}
    for label, arg in (("(weights)", weights), ("(id)", id), ("(cluster)", cluster), ("(istate)", istate)):
        if arg is None:
            continue
        if isinstance(arg, str):
            if arg not in table:
                raise ValueError(f"object '{arg}' not found")
            arg = table[arg]
        extras[label] = _frame_column(arg)
    table.update(extras)
    table = {key: _frame_column(value) if isinstance(value, StrataFactor) else value for key, value in table.items()}

    table, _ = _apply_subset(table, subset)
    response = _build_response(table, is_surv2, lhs_names)
    if not (is_Surv(response) or isinstance(response, Surv2Object)):
        raise ValueError("response must be a survival object")

    names = [lhs.strip()]
    columns: list[Any] = [response]
    for term in terms:
        names.append(term)
        columns.append(_eval_term(term, table))
    n_terms = len(terms)
    for label in ("(id)", "(istate)", "(weights)", "(cluster)"):
        if label in table:
            names.append(label)
            columns.append(table[label])
    specials = {"id": table["(id)"]} if "(id)" in table else {}
    mf = TimelineFrame(names, columns, specials)

    if isinstance(response, Surv2Object):
        mf = _surv2counting(mf)
    mf, omit = _apply_na_action(mf, na_action)
    if len(mf) == 0:
        raise ValueError("data set has no non-missing observations")

    def column(label: str) -> Any:
        return mf.columns[mf.names.index(label)] if label in mf.names else None

    y = mf.columns[0]
    if timefix:
        y = aeqSurv(y)
    n = len(y)
    id_col = column("(id)")
    istate_col = column("(istate)")
    cluster_col = column("(cluster)")
    weight_col = column("(weights)")

    if y.type == "mcounting":
        if id_col is None:
            raise ValueError("id statement is required")
        check_id = list(id_col)
        check_istate = None if istate_col is None else list(istate_col)
        flags = _survcheck2(y, check_id, check_istate)["flag"]
        if any(float(value) > 0 for value in flags.values()):
            raise ValueError("data set fails survcheck for one or more subjects")

    if weight_col is None:
        casewt = np.ones(n, dtype=float)
    else:
        values = np.asarray(weight_col)
        if values.dtype.kind not in "iuf":
            raise ValueError("weights must be numeric")
        casewt = values.astype(float)
        if not np.all(np.isfinite(casewt)):
            raise ValueError("weights must be finite")
        if np.any(casewt < 0):
            raise ValueError("weights must be non-negative")

    if n_terms == 0:
        x_factor = StrataFactor([1] * n, ["1"])
    else:
        factors = [_factor_of(mf.columns[1 + j]) for j in range(n_terms)]
        x_factor = _combine(terms, factors)

    out = survfit(
        x_factor,
        y,
        weights=casewt,
        stype=stype,
        ctype=ctype,
        id=None if id_col is None else list(id_col),
        cluster=None if cluster_col is None else list(cluster_col),
        robust=robust,
        istate=None if istate_col is None else list(istate_col),
        entry=entry,
        time0=time0,
        **kwargs,
    )

    if out.get("strata") is not None:
        strata_counts = np.asarray(out["strata"], dtype=float)
        keep = strata_counts > 0
        out["strata"] = strata_counts[keep]
        if out.get("strata.names") is not None:
            out["strata.names"] = [label for label, flag in zip(out["strata.names"], keep) if flag]
    if omit is not None and len(omit):
        out["na.action"] = [int(index) for index in omit]
    out["call"] = {"function": "survfit", "formula": text}
    return out
