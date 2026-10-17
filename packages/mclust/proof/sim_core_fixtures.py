"""Fixed parameters shared by the core sim proof scripts. The R twin is sim-core-fixtures.R."""

from __future__ import annotations

import sys

import numpy as np

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/boot")
from boot.rng import unif  # noqa: E402

p = 3
G = 3
_jj = np.arange(1, p + 1, dtype=float)[:, None]
_kk = np.arange(1, G + 1, dtype=float)[None, :]

PRO = np.array([0.2, 0.3, 0.5])
MU1 = np.array([-0.5, 0.2, 1.1])
MU = 0.4 * _kk - 0.25 * _jj + 0.1 * _jj * _kk
SHAPE_V = np.array([1.0, 1.4, 0.6])
SHAPE_M = 0.5 + 0.3 * _jj + 0.2 * _kk
CHOL = np.array([[1.2, 0.3, -0.2], [0.0, 0.8, 0.4], [0.0, 0.0, 1.5]])


def _rz(a: float) -> np.ndarray:
    c, s = np.cos(a), np.sin(a)
    return np.array([[c, -s, 0.0], [s, c, 0.0], [0.0, 0.0, 1.0]])


def _rx(a: float) -> np.ndarray:
    c, s = np.cos(a), np.sin(a)
    return np.array([[1.0, 0.0, 0.0], [0.0, c, -s], [0.0, s, c]])


ORI = np.zeros((p, p, G))
for _k in range(1, G + 1):
    ORI[:, :, _k - 1] = _rz(0.2 * _k) @ _rx(0.14 * _k)

pars_E = {"pro": PRO, "mean": MU1, "variance": {"sigmasq": 0.8}}
pars_E_nopro = {"mean": MU1, "variance": {"sigmasq": 0.8}}
pars_E_zero = {"pro": PRO, "mean": MU1, "variance": {"sigmasq": 0.0}}
pars_E_missing = {**pars_E, "mean": np.nan}

pars_V = {"pro": PRO, "mean": MU1, "variance": {"sigmasq": np.array([0.5, 1.4, 0.9])}}
pars_V_nopro = {"mean": MU1, "variance": {"sigmasq": np.array([0.5, 1.4, 0.9])}}
pars_V_zero = {"pro": PRO, "mean": MU1, "variance": {"sigmasq": np.array([0.5, 0.0, 0.9])}}
pars_V_missing = {**pars_V, "mean": np.nan}

pars_EII = {"pro": PRO, "mean": MU, "variance": {"sigmasq": 0.9}}
pars_EII_nopro = {"mean": MU, "variance": {"sigmasq": 0.9}}
pars_EII_missing = {**pars_EII, "mean": np.nan}

pars_EEI = {"pro": PRO, "mean": MU, "variance": {"scale": 0.9, "shape": SHAPE_V}}
pars_EEI_nopro = {"mean": MU, "variance": {"scale": 0.9, "shape": SHAPE_V}}
pars_EEI_missing = {**pars_EEI, "mean": np.nan}

pars_EEV = {"pro": PRO, "mean": MU, "variance": {"scale": 0.9, "shape": SHAPE_V, "orientation": ORI}}
pars_EEV_nopro = {"mean": MU, "variance": {"scale": 0.9, "shape": SHAPE_V, "orientation": ORI}}
pars_EEV_missing = {**pars_EEV, "mean": np.nan}

pars_EEE = {"pro": PRO, "mean": MU, "variance": {"cholSigma": CHOL}}
pars_EEE_nopro = {"mean": MU, "variance": {"cholSigma": CHOL}}
pars_EEE_sigma = {"pro": PRO, "mean": MU, "variance": {"Sigma": CHOL.T @ CHOL}}
pars_EEE_missing = {**pars_EEE, "mean": np.nan}

pars_EVI = {"pro": PRO, "mean": MU, "variance": {"scale": np.array([0.9, 1.1, 0.7]), "shape": SHAPE_M}}
pars_EVI_nopro = {"mean": MU, "variance": {"scale": np.array([0.9, 1.1, 0.7]), "shape": SHAPE_M}}
pars_EVI_missing = {**pars_EVI, "mean": np.nan}

pars_VEI = {"pro": PRO, "mean": MU, "variance": {"scale": np.array([0.9, 1.3, 0.6]), "shape": SHAPE_V}}
pars_VEI_nopro = {"mean": MU, "variance": {"scale": np.array([0.9, 1.3, 0.6]), "shape": SHAPE_V}}
pars_VEI_missing = {**pars_VEI, "mean": np.nan}


def emit(res) -> list[float]:
    """Dimensions first, then the values in column-major order. NaN is printed as -1e300, as in R."""
    arr = np.asarray(res, dtype=float)
    z = arr.ravel(order="F")
    z = np.where(np.isnan(z), -1e300, z)
    return [float(d) for d in arr.shape] + z.tolist()


def tail_draws(k: int = 2) -> list[float]:
    """runif(k) from the stream the call left behind. It checks how many draws the call used."""
    return [unif() for _ in range(k)]


def print_values(values) -> None:
    for v in values:
        print("%.17g" % float(v))
