"""Constant plus power variance function constructor (nlme varConstPower)."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field

import numpy as np

from nlme.asoneformula import _all_vars
from nlme.getcovariateformula import _deparse, _parse_bar, _tokenize, getCovariateFormula
from nlme.varcomb import VarFunc


@dataclass(slots=True)
class VarConstPower(VarFunc):
    """Storage for varConstPower parameters and metadata."""

    const: np.ndarray = field(default_factory=lambda: np.array([], dtype=np.float64))
    power: np.ndarray = field(default_factory=lambda: np.array([], dtype=np.float64))
    formula: str = "~fitted(.)"
    which_fix: np.ndarray | None = None
    const_fixed: np.ndarray | None = None
    power_fixed: np.ndarray | None = None
    group_names: tuple[str, ...] | None = None

    @property
    def classes(self) -> tuple[str, ...]:
        return ("varConstPower", "varFunc")


def varConstPower(
    const: float | Sequence[float] | Mapping[str, float] | np.ndarray = (),
    power: float | Sequence[float] | Mapping[str, float] | np.ndarray = (),
    form: str = "~ fitted(.)",
    fixed: Mapping[str, float | Sequence[float] | Mapping[str, float]] | None = None,
) -> VarConstPower:
    """Construct a varConstPower object (constant plus power variance structure)."""
    value = {"const": const, "power": power}
    form_str = _as_one_sided_formula(form)
    cov = getCovariateFormula(form_str)
    if len(_all_vars(cov.text)) == 0:
        raise ValueError("'form' must have a covariate")

    parsed_value, _ = _cp_constr(value, form_str, "Value")
    parsed_fixed, _ = _cp_constr(fixed, form_str, "Fixed")

    const_arr = np.asarray(parsed_value.get("const", []), dtype=np.float64).reshape(-1)
    power_arr = np.asarray(parsed_value.get("power", []), dtype=np.float64).reshape(-1)

    const_fixed = _optional_fixed(parsed_fixed.get("const"))
    power_fixed = _optional_fixed(parsed_fixed.get("power"))

    which_fix: np.ndarray | None
    if _get_groups_formula(form_str) is None:
        which_fix = np.array([[const_fixed is not None], [power_fixed is not None]], dtype=bool)
    else:
        which_fix = None

    return VarConstPower(
        const_arr,
        power_arr,
        form_str,
        which_fix,
        const_fixed,
        power_fixed,
        None,
    )


def _as_one_sided_formula(form) -> str:
    text = str(form).strip()
    if "~" in text:
        lhs, rhs = text.split("~", 1)
        if lhs.strip():
            raise ValueError(f"formula '{text}' must be of the form '~expr'")
        rhs = rhs.strip()
    else:
        rhs = text
    tokens = _tokenize(rhs)
    tree, pos = _parse_bar(tokens, 0)
    if pos != len(tokens):
        raise ValueError("invalid formula")
    return f"~{_deparse(tree)}"


def _get_groups_formula(form_str: str) -> str | None:
    text = form_str.strip()
    if text.startswith("~"):
        text = text[1:].strip()
    tokens = _tokenize(text)
    tree, pos = _parse_bar(tokens, 0)
    if pos != len(tokens):
        raise ValueError("invalid formula")
    if tree[0] == "|":
        return f"~{_deparse(tree[2])}"
    return None


def _cp_constr(
    val,
    form_str: str,
    nam: str,
) -> tuple[dict[str, np.ndarray], tuple[str, ...] | None]:
    if val is None:
        return {}, None
    if isinstance(val, VarConstPower):
        raise TypeError(f"{nam} cannot be a VarConstPower object")

    parsed = _normalize_const_power(val, nam)
    if not parsed:
        return {}, None

    grp_names: tuple[str, ...] | None = None
    if _get_groups_formula(form_str) is not None:
        names: list[str] = []
        for item in parsed.values():
            if isinstance(item, Mapping):
                names.extend(str(key) for key in item)
            elif hasattr(item, "dtype") and item.dtype.names:
                names.extend(str(name) for name in item.dtype.names)
        if names:
            grp_names = tuple(dict.fromkeys(names))
        for key, item in parsed.items():
            arr = np.asarray(item, dtype=np.float64).reshape(-1)
            if arr.size > 1 and not _has_names(item):
                raise ValueError(f"{nam} must have group names in 'varConstPower'")

    const = parsed.get("const", np.array([], dtype=np.float64))
    const = np.asarray(const, dtype=np.float64).reshape(-1)
    if const.size > 0 and np.any(const <= 0):
        raise ValueError('constant in "varConstProp" structure must be > 0')
    if const.size > 0:
        const = np.log(const)

    power = np.asarray(parsed.get("power", np.array([], dtype=np.float64)), dtype=np.float64).reshape(-1)
    return {"const": const, "power": power}, grp_names


def _normalize_const_power(val, nam: str) -> dict[str, object]:
    if isinstance(val, Mapping):
        keys = list(val.keys())
        if len(keys) > 2:
            raise ValueError(f"{nam} can have at most two components")
        out: dict[str, object] = {}
        for key in keys:
            key_str = str(key)
            if key_str not in ("const", "power"):
                raise ValueError(f'{nam} can only have names "const" and "power"')
            out[key_str] = val[key]
        if "const" not in out:
            out["const"] = np.array([], dtype=np.float64)
        if "power" not in out:
            out["power"] = np.array([], dtype=np.float64)
        return out

    arr = np.asarray(val, dtype=np.float64).reshape(-1)
    if arr.size == 0:
        return {}
    if arr.size > 2:
        raise ValueError(f"{nam} can have at most two components")
    if arr.dtype.names:
        out = {str(name): arr[name] for name in arr.dtype.names}
    elif getattr(arr, "names", None):
        names = arr.names
        if names is None:
            names = ("const", "power")[: arr.size]
        out = {str(name): arr[index] for index, name in enumerate(names)}
    else:
        names = ("const", "power")[: arr.size]
        out = {names[index]: arr[index] for index in range(arr.size)}
    for key in list(out):
        if key not in ("const", "power"):
            raise ValueError(f'{nam} can only have names "const" and "power"')
    return out


def _optional_fixed(value) -> np.ndarray | None:
    if value is None:
        return None
    arr = np.asarray(value, dtype=np.float64).reshape(-1)
    if arr.size == 0:
        return None
    return arr


def _has_names(item) -> bool:
    if isinstance(item, Mapping):
        return True
    arr = np.asarray(item)
    return bool(getattr(arr, "names", None)) or bool(arr.dtype.names)


def proof_values(object: VarConstPower) -> np.ndarray:
    """Numeric summary of a varConstPower object for R comparison."""
    parts = [
        np.asarray(object.const, dtype=np.float64).reshape(-1),
        np.asarray(object.power, dtype=np.float64).reshape(-1),
    ]
    if object.which_fix is not None:
        parts.append(object.which_fix.astype(np.float64).reshape(-1))
    if object.const_fixed is not None:
        parts.append(np.asarray(object.const_fixed, dtype=np.float64).reshape(-1))
    if object.power_fixed is not None:
        parts.append(np.asarray(object.power_fixed, dtype=np.float64).reshape(-1))
    parts.append(np.array([sum(map(ord, object.formula))], dtype=np.float64))
    return np.concatenate(parts) if parts else np.array([], dtype=np.float64)
