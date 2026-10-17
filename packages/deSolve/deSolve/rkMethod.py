"""Butcher tables and coefficients for Runge-Kutta solvers in deSolve."""

from __future__ import annotations

import copy
from typing import Any

import numpy as np

from deSolve.rkMethod_data import METHODS

_KNOWN_ALIASES = ("ode23", "ode45")
_KNOWN_METHODS = tuple(spec["ID"] for spec in METHODS.values()) + _KNOWN_ALIASES


class MethodNames(list):
    """Character vector of implemented Runge-Kutta method names."""

    def __str__(self) -> str:
        chunks: list[str] = []
        for index, name in enumerate(self, start=1):
            prefix = f"[{index}]" if index == 1 or (index - 1) % 7 == 0 else "   "
            chunks.append(f'{prefix} "{name}"')
        return " ".join(chunks)


class RkMethod:
    """Runge-Kutta method specification, mirroring R's ``rkMethod`` list."""

    __slots__ = ("_fields",)

    def __init__(self, fields: dict[str, Any]):
        self._fields = fields

    def __getitem__(self, key: str):
        return self._fields[key]

    def get(self, key: str, default=None):
        return self._fields.get(key, default)

    def keys(self):
        return self._fields.keys()

    def items(self):
        return self._fields.items()

    def __contains__(self, key: str) -> bool:
        return key in self._fields

    def __str__(self) -> str:
        lines: list[str] = []
        for key, value in self._fields.items():
            lines.append(f"${key}")
            lines.extend(_format_value(value))
        return "\n".join(lines)


def _format_value(value: Any) -> list[str]:
    if isinstance(value, np.ndarray):
        if value.ndim == 1:
            text = " ".join(f"{item:11.8g}" for item in value)
            return [f"[1] {text}"]
        rows, cols = value.shape
        lines = [f"     [,1]" + "".join(f" {col + 1:>9}" for col in range(cols))]
        for row in range(rows):
            cells = "".join(f" {value[row, col]:11.8g}" for col in range(cols))
            lines.append(f"[{row + 1},]{cells}")
        return lines
    if isinstance(value, (bool, np.bool_)):
        return [f"[1] {'TRUE' if value else 'FALSE'}"]
    if isinstance(value, str):
        return [f'[1] "{value}"']
    if isinstance(value, (int, np.integer)):
        return [f"[1] {int(value)}"]
    if isinstance(value, (float, np.floating)):
        return [f"[1] {float(value):.8g}"]
    return [repr(value)]


def _match_arg(arg: str, choices: tuple[str, ...]) -> str:
    if arg in choices:
        return arg
    hits = [choice for choice in choices if choice.startswith(arg)]
    if len(hits) == 1:
        return hits[0]
    quoted = ", ".join(f'"{choice}"' for choice in choices)
    raise ValueError(f"'arg' should be one of {quoted}")


def _deep_copy_spec(spec: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in spec.items():
        if isinstance(value, np.ndarray):
            out[key] = np.array(value, copy=True)
        else:
            out[key] = copy.copy(value)
    return out


def _length(value: Any) -> int:
    if value is None:
        return 0
    if isinstance(value, np.ndarray):
        if value.ndim == 0:
            return 1
        return int(value.size)
    if isinstance(value, (int, float, np.integer, np.floating)):
        return 1
    if isinstance(value, (list, tuple)):
        return len(value)
    if isinstance(value, str):
        return 1
    return 1


def _validate(out: dict[str, Any]) -> None:
    stage = out["stage"]
    sl = {key: _length(val) for key, val in out.items()}
    a_val = out["A"]
    if isinstance(a_val, np.ndarray) and a_val.ndim == 2:
        if a_val.shape[0] != stage or a_val.shape[1] < stage - 1 or a_val.shape[1] > stage:
            raise ValueError("Size of matrix A does not match stage")
    else:
        a_len = _length(a_val)
        if a_len != stage:
            raise ValueError("Size of matrix A does not match stage")
    if stage != sl["b1"] or stage != sl["c"]:
        raise ValueError("Wrong rkMethod, length of parameters do not match")
    if out.get("varstep") and out.get("b2") is None:
        raise ValueError("Variable stepsize method needs non-empty b2")
    if out.get("b2") is not None and sl["b2"] != stage:
        raise ValueError("Wrong rkMethod, length of b2 must be empty or equal to stage")
    if out.get("d") is not None and sl["d"] != stage:
        raise ValueError("Wrong rkMethod, length of d must be empty or equal to stage")
    densetype = out.get("densetype")
    if densetype is not None:
        method_id = out.get("ID")
        if densetype == 1 and method_id not in ("rk45dp7", "ode45"):
            raise ValueError("densetype = 1 not implemented for this method")
        if densetype == 2 and method_id not in ("rk45ck",):
            raise ValueError("densetype = 2 not implemented for this method")


def flatten_rk_method(result: MethodNames | RkMethod) -> np.ndarray:
    """Numeric fingerprint of a method table for checks against R."""
    if isinstance(result, list):
        return np.array([], dtype=np.float64)
    out = result._fields
    parts: list[float] = [
        float(out["varstep"]),
        float(out["FSAL"]) if out.get("FSAL") is not None else np.nan,
        float(out["implicit"]) if out.get("implicit") is not None else np.nan,
    ]
    a_val = out["A"]
    if isinstance(a_val, np.ndarray):
        parts.extend(np.ravel(a_val, order="F").tolist())
    else:
        parts.append(float(a_val))
    parts.extend(np.ravel(out["b1"], order="F").tolist())
    if out.get("b2") is not None:
        parts.extend(np.ravel(out["b2"], order="F").tolist())
    parts.extend(np.ravel(out["c"], order="F").tolist())
    if out.get("d") is not None:
        parts.extend(np.ravel(out["d"], order="F").tolist())
    parts.append(float(out["stage"]))
    parts.append(float(out["Qerr"]))
    densetype = out.get("densetype")
    parts.append(float(densetype) if densetype is not None else np.nan)
    return np.asarray(parts, dtype=np.float64)


def rkMethod(method: str | None = None, **kwargs: Any) -> MethodNames | RkMethod:
    """Return Butcher-table parameters for a Runge-Kutta method."""
    method_key: str | None
    if method is not None:
        method_key = _match_arg(method, _KNOWN_METHODS)
        if method_key == "ode23":
            method_key = "rk23bs"
        elif method_key == "ode45":
            method_key = "rk45dp7"
        out = _deep_copy_spec(METHODS[method_key])
    else:
        method_key = None
        out: dict[str, Any] = {}

    for key, value in kwargs.items():
        if isinstance(value, np.ndarray):
            out[key] = np.array(value, copy=True)
        elif isinstance(value, (list, tuple)) and key in ("A", "b1", "b2", "c", "d"):
            out[key] = np.asarray(value, dtype=np.float64)
        else:
            out[key] = value

    if method is None and not kwargs:
        return MethodNames(_KNOWN_METHODS)

    _validate(out)
    return RkMethod(out)
