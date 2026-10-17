"""Temporary pass-through from survfitcoxph.fit to coxsurv.fit.

survival::survfitcoxph.fit rebuilds a call to coxsurv.fit. vartype is accepted
and ignored. survtype 1, 2, and 3 map to (stype, ctype) = (1, 1), (2, 1), and
(2, 2). newrisk is forwarded as risk2, and id is forwarded as id2.
"""

from __future__ import annotations

from typing import Any

from survival.coxsurv_fit import coxsurv_fit


_MISSING = object()


def survfitcoxph_fit(
    y: Any = _MISSING,
    x: Any = _MISSING,
    wt: Any = _MISSING,
    x2: Any = _MISSING,
    risk: Any = _MISSING,
    newrisk: Any = _MISSING,
    strata: Any = _MISSING,
    se_fit: Any = _MISSING,
    survtype: Any = _MISSING,
    vartype: Any = _MISSING,
    varmat: Any = _MISSING,
    id: Any = _MISSING,
    y2: Any = _MISSING,
    strata2: Any = _MISSING,
    unlist: bool = True,
) -> Any:
    """Baseline survival from a Cox fit, with the old survfitcoxph.fit argument names."""
    del vartype
    required = (
        ("y", y),
        ("x", x),
        ("wt", wt),
        ("x2", x2),
        ("risk", risk),
        ("newrisk", newrisk),
        ("se.fit", se_fit),
        ("varmat", varmat),
    )
    for name, value in required:
        if value is _MISSING:
            raise TypeError(f"argument '{name}' is missing, with no default")
    if survtype is _MISSING:
        stype, ctype = 1, 1
    else:
        surv_i = int(survtype)
        stype = (1, 2, 2)[surv_i - 1]
        ctype = (1, 1, 2)[surv_i - 1]
    return coxsurv_fit(
        ctype,
        stype,
        se_fit,
        varmat,
        None,
        y,
        x,
        wt,
        risk,
        None,
        None if strata is _MISSING else strata,
        None,
        None if y2 is _MISSING else y2,
        x2,
        newrisk,
        None if strata2 is _MISSING else strata2,
        None if id is _MISSING else id,
        unlist,
    )
