"""Combine coefficient vectors from nlme model components (allCoef)."""

from __future__ import annotations

import inspect
from dataclasses import dataclass
from types import FrameType

import numpy as np

from nlme.corar1 import CorAR1, corAR1, _coef_cor_ar1
from nlme.varcomb import VarFunc


@dataclass(slots=True)
class VarPower(VarFunc):
    """Power-of-covariate variance function parameter storage."""

    values: np.ndarray
    which_fix: np.ndarray
    fixed: np.ndarray | None = None
    group_names: tuple[str, ...] | None = None

    @property
    def classes(self) -> tuple[str, ...]:
        return ("varPower", "varFunc")


class AllCoefResult:
    """Coefficient vector with the same ``map`` attribute as R's ``allCoef``."""

    __slots__ = ("values", "map", "map_colnames")

    def __init__(self, values: np.ndarray, map_: np.ndarray, map_colnames: tuple[str, ...]):
        self.values = np.asarray(values, dtype=np.float64)
        self.map = map_
        self.map_colnames = map_colnames

    def __array__(self, dtype=None, copy=None):
        if dtype is None:
            dtype = np.float64
        return np.asarray(self.values, dtype=dtype, copy=copy)

    def __len__(self) -> int:
        return len(self.values)

    def __iter__(self):
        return iter(self.values)


def varPower(value=(), form=None, fixed=None) -> VarPower:
    """Build a varPower stand-in for ``allCoef`` checks."""
    if isinstance(value, (int, float)):
        arr = np.array([float(value)], dtype=np.float64)
    else:
        arr = np.asarray(value, dtype=np.float64).ravel()
    if fixed is None:
        which_fix = np.array([False], dtype=bool)
        fixed_arr = None
    else:
        fixed_arr = np.asarray(fixed, dtype=np.float64).ravel()
        which_fix = np.array([True], dtype=bool)
    if len(arr) != int(np.sum(~which_fix)):
        raise ValueError("cannot extract parameters of uninitialized object")
    return VarPower(arr, which_fix, fixed_arr)


def coef(object, unconstrained: bool = True, allCoef: bool = False, **_ignored):
    """Extract coefficients from corAR1 or varPower stand-ins."""
    if isinstance(object, CorAR1):
        return _coef_cor_ar1(object, unconstrained=unconstrained)
    if isinstance(object, VarPower):
        return _coef_var_power(object, unconstrained=unconstrained, allCoef=allCoef)
    raise TypeError(f"do not know how to get coefficients for object of type {type(object)!r}")


def allCoef(*objects, extract=coef) -> AllCoefResult:
    """Apply ``extract`` to each object and concatenate the coefficients."""
    theta = [_coef_vector(extract(obj)) for obj in objects]
    lengths = [len(part.values) for part in theta]
    num = np.arange(1, len(objects) + 1, dtype=np.intp)
    if sum(lengths) > 0:
        rep_num = np.repeat(num, lengths)
        which = rep_num[:, None] == num[None, :]
    else:
        which = np.zeros((1, len(objects)), dtype=bool)

    caller = inspect.currentframe()
    try:
        call_frame = caller.f_back if caller is not None else None
    finally:
        del caller
    colnames = _object_names_from_caller(objects, call_frame)
    values = np.concatenate([part.values for part in theta]) if theta else np.array([], dtype=np.float64)
    return AllCoefResult(values, which, colnames)


@dataclass(frozen=True, slots=True)
class _CoefVector:
    values: np.ndarray
    names: tuple[str | None, ...]


def _coef_var_power(object: VarPower, unconstrained: bool, allCoef: bool) -> _CoefVector:
    w_par = object.which_fix
    if w_par is None:
        return _CoefVector(np.array([], dtype=np.float64), ())
    if not unconstrained:
        raise ValueError('do not know how to get coefficients for "varPower" object')
    val = np.zeros(len(w_par), dtype=np.float64)
    if np.any(w_par):
        val[w_par] = object.fixed
    if np.any(~w_par):
        val[~w_par] = object.values
    if object.group_names is not None:
        names = tuple(object.group_names)
    else:
        names = ("power",) * len(val)
    if not allCoef:
        keep = ~w_par
        val = val[keep]
        names = tuple(name for name, keep_flag in zip(names, keep, strict=True) if keep_flag)
    return _CoefVector(val, names)


def _coef_vector(extracted) -> _CoefVector:
    if isinstance(extracted, _CoefVector):
        return extracted
    if hasattr(extracted, "values") and hasattr(extracted, "names"):
        values = np.asarray(extracted.values, dtype=np.float64).ravel()
        return _CoefVector(values, tuple(extracted.names))
    values = np.asarray(extracted, dtype=np.float64).ravel()
    return _CoefVector(values, (None,) * len(values))


def _object_names_from_caller(
    objects: tuple[object, ...], caller: FrameType | None
) -> tuple[str, ...]:
    if caller is None:
        return tuple("" for _ in objects)
    names: list[str] = []
    for obj in objects:
        label = ""
        for key, val in caller.f_locals.items():
            if val is obj:
                label = key
                break
        names.append(label)
    return tuple(names)
