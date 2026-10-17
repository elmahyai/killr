"""Predict doses for binomial assay models (MASS ``dose.p``)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

from mass.errors import MassError


def _coef(obj: Any) -> np.ndarray:
    if hasattr(obj, "coefficients"):
        return np.asarray(obj.coefficients, dtype=float).reshape(-1)
    if hasattr(obj, "coef"):
        coef = obj.coef
        return np.asarray(coef() if callable(coef) else coef, dtype=float).reshape(-1)
    raise MassError("fitted model must provide coefficients")


def _vcov(obj: Any) -> np.ndarray:
    if hasattr(obj, "vcov_matrix"):
        return np.asarray(obj.vcov_matrix, dtype=float)
    if hasattr(obj, "vcov"):
        vcov = obj.vcov
        return np.asarray(vcov() if callable(vcov) else vcov, dtype=float)
    raise MassError("fitted model must provide vcov")


def _family_linkfun(obj: Any, p: np.ndarray) -> np.ndarray:
    family = getattr(obj, "family", None)
    if family is None:
        raise MassError("fitted model must provide family")
    linkfun = getattr(family, "linkfun", None)
    if linkfun is None and hasattr(family, "link"):
        link = family.link
        linkfun = getattr(link, "linkfun", None)
    if linkfun is None:
        raise MassError("family must provide linkfun")
    return np.asarray(linkfun(p), dtype=float).reshape(-1)


def _format_p(p: float) -> str:
    text = format(float(p), "g")
    if "e" not in text and "." not in text:
        text = text + ".0"
    return text


@dataclass
class GlmDose:
    """Dose predictions at response probabilities (class ``glm.dose``)."""

    dose: np.ndarray
    se: np.ndarray
    p: np.ndarray
    names: list[str]

    def __array__(self, dtype=None):
        return np.asarray(self.dose, dtype=dtype)

    def __len__(self) -> int:
        return int(self.dose.shape[0])

    def __getitem__(self, key):
        return self.dose[key]


def print_glm_dose(x: GlmDose) -> None:
    """Print like ``print.glm.dose``."""
    dose = np.asarray(x.dose, dtype=float).reshape(-1, 1)
    se = np.asarray(x.se, dtype=float).reshape(-1, 1)
    mat = np.column_stack([dose, se])
    row_names = x.names if x.names else [str(i) for i in range(mat.shape[0])]
    col_w = max(len("Dose"), max(len(name) for name in row_names))
    se_w = 12
    print(f"{'':>{col_w}} {'Dose':>12} {'SE':>12}")
    for i, name in enumerate(row_names):
        print(f"{name:>{col_w}} {mat[i, 0]:12.6g} {mat[i, 1]:12.6g}")


def dose_p(obj: Any, cf: list[int] | tuple[int, ...] | None = None, p: float | list[float] | np.ndarray = 0.5) -> GlmDose:
    """Calibrate binomial assays; generalizes LD50 calculation."""
    if cf is None:
        cf = (1, 2)
    cf_idx = [int(i) - 1 for i in cf]
    if len(cf_idx) != 2:
        raise MassError("cf must give exactly two coefficient indices")
    p_arr = np.atleast_1d(np.asarray(p, dtype=float))
    eta = _family_linkfun(obj, p_arr)
    coef = _coef(obj)
    if min(cf_idx) < 0 or max(cf_idx) >= coef.shape[0]:
        raise MassError("cf indices out of range for coefficients")
    b = coef[cf_idx]
    if b[1] == 0:
        raise MassError("zero slope coefficient in cf")
    x_p = (eta - b[0]) / b[1]
    names = [f"p = {_format_p(val)}:" for val in p_arr.reshape(-1)]
    v = _vcov(obj)
    v_sub = v[np.ix_(cf_idx, cf_idx)]
    pd = -np.column_stack([np.ones_like(x_p, dtype=float), x_p]) / b[1]
    se = np.sqrt(np.sum((pd @ v_sub) * pd, axis=1))
    return GlmDose(dose=x_p, se=se, p=p_arr.copy(), names=names)
