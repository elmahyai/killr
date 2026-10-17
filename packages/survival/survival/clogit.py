"""Conditional logistic regression (survival::clogit).

clogit rewrites the formula as Surv(1 + 0 * case, case) ~ rhs, maps the
method ("approximate" becomes "breslow"), drops weights for the exact method,
and calls coxph. The Cox fit itself is in survival.coxph.
"""

from __future__ import annotations

import warnings
from typing import Any

from survival.coxph import coxph


_METHOD_CHOICES = ("exact", "approximate", "efron", "breslow")


def _match_method(method: Any) -> str:
    if method is None:
        return "exact"
    if isinstance(method, (list, tuple)):
        method = method[0] if method else None
        if method is None:
            return "exact"
    text = str(method)
    hits = [c for c in _METHOD_CHOICES if c == text or c.startswith(text)]
    if len(hits) == 1:
        return hits[0]
    if len(hits) > 1:
        raise ValueError(f"'{text}' is ambiguous")
    raise ValueError(f"'{text}' should be one of {', '.join(_METHOD_CHOICES)}")


def _split_formula(formula: str) -> tuple[str, str]:
    if "~" not in formula:
        raise ValueError("A formula argument is required")
    lhs, rhs = formula.split("~", 1)
    return lhs.strip(), rhs.strip()


def clogit(
    formula: str,
    data: Any = None,
    weights: Any = None,
    subset: Any = None,
    na_action: Any = None,
    method: Any = None,
    **kwargs: Any,
) -> dict[str, Any]:
    """Conditional logistic regression via a stratified Cox model."""
    if formula is None:
        raise ValueError("A formula argument is required")
    lhs, rhs = _split_formula(str(formula))
    newformula = f"Surv(1 + 0*({lhs}), {lhs}) ~ {rhs}"
    chosen = _match_method(method)
    cox_method = {"exact": "exact", "efron": "efron"}.get(chosen, "breslow")
    if cox_method == "exact" and weights is not None:
        warnings.warn("weights ignored: not possible for the exact method", stacklevel=2)
        weights = None
    fit = coxph(
        newformula,
        data,
        weights=weights,
        subset=subset,
        na_action=na_action,
        method=cox_method,
        **kwargs,
    )
    fit["call"] = {"function": "clogit", "formula": str(formula), "method": chosen}
    fit["userCall"] = fit["call"]
    fit["class_"] = ("clogit", "coxph")
    return fit
