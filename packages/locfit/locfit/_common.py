"""Shared Python representations for the small locfit helper exports."""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any, Mapping

import numpy as np


def expit_array(x: Any) -> np.ndarray:
    a = np.asarray(x, dtype=float)
    out = np.empty_like(a)
    neg = a < 0
    out[neg] = np.exp(a[neg]) / (1.0 + np.exp(a[neg]))
    out[~neg] = 1.0 / (1.0 + np.exp(-a[~neg]))
    return out


def field(obj: Any, name: str, default: Any = None) -> Any:
    if isinstance(obj, Mapping):
        return obj.get(name, default)
    return getattr(obj, name, default)


def dp_values(fit: Any) -> tuple[float, float, float]:
    dp = field(fit, "dp", fit)
    return (float(field(dp, "lk", 0.0)), float(field(dp, "df1", 0.0)),
            float(field(dp, "df2", 0.0)))


def n_observations(fit: Any) -> float:
    mi = field(fit, "mi", fit)
    return float(field(mi, "n", field(fit, "n", 0.0)))


@dataclass
class Evaluation:
    x: np.ndarray
    y: np.ndarray


@dataclass
class LfEvs:
    """Python form of the R list with class ``lf_evs`` (an evaluation spec)."""

    type: str
    xev: float
    mg: float
    cut: float
    ll: np.ndarray
    ur: np.ndarray

    CLASS = "lf_evs"

