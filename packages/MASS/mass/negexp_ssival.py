"""Starting values for negative exponential curves (``negexp.SSival``)."""

from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path
from typing import Any, Mapping

import numpy as np

_pkg = Path(__file__).resolve().parent
if "mass" not in sys.modules:
    _mass = types.ModuleType("mass")
    _mass.__path__ = [str(_pkg)]
    sys.modules["mass"] = _mass
if "mass.errors" not in sys.modules:
    _spec = importlib.util.spec_from_file_location("mass.errors", _pkg / "errors.py")
    _errors = importlib.util.module_from_spec(_spec)
    assert _spec.loader is not None
    sys.modules["mass.errors"] = _errors
    _spec.loader.exec_module(_errors)

from mass.errors import MassError


def _symbol_name(item: Any) -> str:
    if isinstance(item, str):
        return item
    if isinstance(item, (bytes, np.str_)):
        return str(item)
    name = getattr(item, "name", None)
    if isinstance(name, str) and name:
        return name
    text = str(item)
    if text.startswith("<symbol ") and text.endswith(">"):
        return text[8:-1]
    return text


def _eval_in_data(expr: Any, data: Mapping[str, Any]) -> np.ndarray:
    key = _symbol_name(expr)
    if key not in data:
        raise MassError(f"object '{key}' not found")
    return np.asarray(data[key], dtype=float).reshape(-1)


def _lsfit(x: np.ndarray, y: np.ndarray) -> np.ndarray:
    design = np.asarray(x, dtype=float)
    if design.ndim == 1:
        design = design.reshape(-1, 1)
    response = np.asarray(y, dtype=float).reshape(-1)
    augmented = np.column_stack([np.ones(response.shape[0], dtype=float), design])
    coef, *_ = np.linalg.lstsq(augmented, response, rcond=-1)
    return np.asarray(coef, dtype=float).reshape(-1)


def _print_pars(names: list[str], values: np.ndarray) -> None:
    labels = names if names else [str(i) for i in range(values.shape[0])]
    width = max(len(label) for label in labels)
    for label, value in zip(labels, values):
        print(f"{label:>{width}} {value:>12.9g}")


def negexp_ssival(m_call: Any, data: Mapping[str, Any], lhs: Any) -> dict[str, float]:
    """SelfStart-style initial values for ``b0 + b1 * exp(-x/th)``."""
    if isinstance(m_call, Mapping):
        x_expr = m_call["x"]
        name_items = [m_call[key] for key in ("b0", "b1", "th")]
    else:
        x_expr = m_call["x"]  # type: ignore[index]
        name_items = [m_call[key] for key in ("b0", "b1", "th")]  # type: ignore[index]

    x = _eval_in_data(x_expr, data)
    if x.size < 3:
        raise MassError("at least 3 distinct 'x' values are needed")
    y = _eval_in_data(lhs, data)
    mx = float(np.mean(x))
    b = _lsfit(np.column_stack([x - mx, -(x - mx) ** 2 / 2.0]), y)
    rx = np.array([float(np.min(x)), float(np.max(x))], dtype=float)
    xh = mx + b[1] / b[2]
    if float(np.prod(xh - rx)) < 0:
        if xh - rx[0] > rx[1] - xh:
            rx[1] = xh
        else:
            rx[0] = xh
    x0 = np.array([rx[0], float(np.sum(rx) / 2.0), rx[1]], dtype=float)
    dy = np.diff(b[0] + b[1] * (x0 - mx) - (b[2] * (x0 - mx) ** 2) / 2.0)
    th = (x0[1] - x0[0]) / float(np.log(dy[0] / dy[1]))
    b = _lsfit(np.exp(-x / th), y)
    names = [_symbol_name(item) for item in name_items]
    values = np.array([b[0], b[1], th], dtype=float)
    _print_pars(names, values)
    return {name: float(value) for name, value in zip(names, values)}
