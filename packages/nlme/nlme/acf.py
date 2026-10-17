"""Autocorrelation function generic (nlme ``ACF``)."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

import numpy as np

_MISSING = object()
_RES_TYPES = ("pearson", "response", "normalized")


@dataclass(slots=True)
class Lme:
    """Minimal ``lme`` stand-in carrying within-group residuals for ``ACF``."""

    resid_by_group: dict[str, tuple[float, ...]]
    classes: tuple[str, ...] = ("lme",)


class ACFError(ValueError):
    """An R-style ``stop`` from ``ACF`` or its methods."""


@dataclass(frozen=True, slots=True)
class ACFResult:
    """Empirical autocorrelation table with class ``ACF``."""

    lag: np.ndarray
    acf: np.ndarray
    n_used: np.ndarray

    @property
    def ACF(self) -> np.ndarray:
        return self.acf


def ACF(object, maxLag=_MISSING, **kwargs):
    """Dispatch ``ACF`` on the class of ``object``."""
    classes = _class_vector(object)
    if "lme" in classes:
        return _ACF_lme(object, maxLag, **kwargs)
    shown = _show_classes(classes)
    raise ACFError(
        f"no applicable method for 'ACF' applied to an object of class {shown}"
    )


def resid(
    object,
    type: str = "response",
    asList: bool = False,
    **kwargs,
):
    """Extract residuals for ``ACF`` method dispatch (``lme`` stand-in only)."""
    del kwargs
    classes = _class_vector(object)
    if "lme" not in classes:
        raise TypeError(f"no applicable method for 'resid' applied to an object of class {_show_classes(classes)}")
    res_type = _match_arg(type, _RES_TYPES)
    if res_type != "pearson":
        raise NotImplementedError("only pearson residuals are implemented for the lme stand-in")
    grouped = {key: np.asarray(vals, dtype=np.float64) for key, vals in object.resid_by_group.items()}
    if asList:
        return grouped
    return np.concatenate([grouped[key] for key in sorted(grouped, key=str)])


def _ACF_lme(object, maxLag=_MISSING, resType: str = "pearson", **kwargs):
    del kwargs
    res_type = _match_arg(resType, _RES_TYPES)
    res = resid(object, type=res_type, asList=True)
    if maxLag is _MISSING:
        max_l = max(len(el) for el in res.values()) - 1
        maxLag = min(max_l, int(10 * math.log10(max_l + 1)))
    maxLag = int(maxLag)
    blocks = [_acf_block(np.asarray(el, dtype=np.float64), maxLag) for el in res.values()]
    sums = np.stack(blocks, axis=0)
    val0 = np.sum(sums[:, :, 1], axis=0)
    val1 = np.sum(sums[:, :, 0], axis=0) / val0
    val2 = val1 / val1[0]
    return ACFResult(
        lag=np.arange(maxLag + 1, dtype=np.float64),
        acf=np.asarray(val2, dtype=np.float64),
        n_used=np.asarray(val0, dtype=np.float64),
    )


def _acf_block(el: np.ndarray, max_lag: int) -> np.ndarray:
    n = len(el)
    n_cols = max_lag + 1
    tt = np.zeros(n_cols, dtype=np.float64)
    nn = np.zeros(n_cols, dtype=np.float64)
    n_use = min(n_cols, n)
    for i in range(n_use):
        tt[i] = float(np.dot(el[: n - i], el[i:n]))
        nn[i] = float(n - i)
    return np.column_stack((tt, nn))


def _match_arg(value: str, choices: tuple[str, ...]) -> str:
    if not isinstance(value, str):
        raise TypeError("match.arg requires a character vector")
    if value in choices:
        return value
    hits = [choice for choice in choices if choice.startswith(value)]
    if len(hits) == 1:
        return hits[0]
    if len(hits) > 1:
        raise ACFError(f"'{value}' is abbreviated")
    shown = ", ".join(repr(choice) for choice in choices)
    raise ACFError(f"'{value}' should be one of {shown}")


def _class_vector(object: Any) -> tuple[str, ...]:
    classes = getattr(object, "classes", None)
    if classes is not None:
        return tuple(classes)
    return (type(object).__name__,)


def _show_classes(classes: tuple[str, ...]) -> str:
    if len(classes) == 1:
        return f'"{classes[0]}"'
    inner = ", ".join(f"'{name}'" for name in classes)
    return f'"c({inner})"'
