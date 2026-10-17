"""Constant plus proportional variance function constructor (nlme ``varConstProp``)."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field

import numpy as np

from nlme.asoneformula import _all_vars
from nlme.getcovariateformula import getCovariateFormula
from nlme.varcomb import VarFunc
from nlme.varconstpower import _as_one_sided_formula, _get_groups_formula


@dataclass(slots=True)
class VarConstProp(VarFunc):
    """Storage for varConstProp parameters: ``const`` is on the log scale, ``prop`` is raw."""

    const: np.ndarray = field(default_factory=lambda: np.array([], dtype=np.float64))
    prop: np.ndarray = field(default_factory=lambda: np.array([], dtype=np.float64))
    formula: str = "~fitted(.)"
    which_fix: np.ndarray | None = None
    const_fixed: np.ndarray | None = None
    prop_fixed: np.ndarray | None = None
    group_names: tuple[str, ...] | None = None

    @property
    def classes(self) -> tuple[str, ...]:
        return ("varConstProp", "varFunc")


def varConstProp(
    const=(),
    prop=(),
    form: str = "~ fitted(.)",
    fixed: Mapping[str, object] | None = None,
) -> VarConstProp:
    """Construct a varConstProp object (``const + prop * covariate`` standard deviations)."""
    form_str = _as_one_sided_formula(form)
    if len(_all_vars(getCovariateFormula(form_str).text)) == 0:
        raise ValueError("'form' must have a covariate")

    parsed_value = _cp_constr({"const": const, "prop": prop}, form_str, "Value")
    parsed_fixed = _cp_constr(fixed or {}, form_str, "Fixed")

    const_arr = np.asarray(parsed_value.get("const", []), dtype=np.float64).reshape(-1)
    prop_arr = np.asarray(parsed_value.get("prop", []), dtype=np.float64).reshape(-1)
    const_fixed = _optional_fixed(parsed_fixed.get("const"))
    prop_fixed = _optional_fixed(parsed_fixed.get("prop"))

    which_fix: np.ndarray | None
    if _get_groups_formula(form_str) is None:
        which_fix = np.array([[const_fixed is not None], [prop_fixed is not None]], dtype=bool)
    else:
        which_fix = None

    return VarConstProp(const_arr, prop_arr, form_str, which_fix, const_fixed, prop_fixed, None)


def _cp_constr(val, form_str: str, nam: str) -> dict[str, np.ndarray]:
    """Port of the ``CPconstr`` helper inside R's ``varConstProp``."""
    if isinstance(val, Mapping):
        items = dict(val)
    else:
        arr = np.asarray(val, dtype=np.float64).reshape(-1)
        if arr.size == 0:
            return {}
        if arr.size > 2:
            raise ValueError(f"{nam} can have at most two components")
        items = {name: arr[index] for index, name in enumerate(("const", "prop")[: arr.size])}
    if not items:
        return {}
    if len(items) > 2:
        raise ValueError(f"{nam} can have at most two components")
    for key in items:
        if key not in ("const", "prop"):
            raise ValueError(f'{nam} can only have names "const" and "prop"')

    out: dict[str, np.ndarray] = {}
    for key, item in items.items():
        out[key] = np.asarray(item, dtype=np.float64).reshape(-1)

    if "const" in out and out["const"].size > 0:
        if np.any(out["const"] <= 0):
            raise ValueError('constant in "varConstProp" structure must be > 0')
        out["const"] = np.log(out["const"])
    return out


def _optional_fixed(value) -> np.ndarray | None:
    if value is None:
        return None
    arr = np.asarray(value, dtype=np.float64).reshape(-1)
    if arr.size == 0:
        return None
    return arr


def proof_values(object: VarConstProp) -> np.ndarray:
    """Numeric summary of a varConstProp object for R comparison."""
    parts = [
        np.asarray(object.const, dtype=np.float64).reshape(-1),
        np.asarray(object.prop, dtype=np.float64).reshape(-1),
    ]
    if object.which_fix is not None:
        parts.append(object.which_fix.astype(np.float64).reshape(-1))
    if object.const_fixed is not None:
        parts.append(np.asarray(object.const_fixed, dtype=np.float64).reshape(-1))
    if object.prop_fixed is not None:
        parts.append(np.asarray(object.prop_fixed, dtype=np.float64).reshape(-1))
    parts.append(np.array([sum(map(ord, object.formula))], dtype=np.float64))
    return np.concatenate(parts)
