"""Fixed inputs shared by the cdens proof scripts. The R twin is cdens-fixtures.R."""

from __future__ import annotations

import copy

import numpy as np

n = 60
p = 3
G = 3
i1 = np.arange(1, n + 1, dtype=float)
x1 = np.sin(0.7 * i1) + 0.5 * np.cos(0.31 * i1 * i1)
_i = i1[:, None]
_j = np.arange(1, p + 1, dtype=float)[None, :]
X = np.sin(0.7 * _i + 1.3 * _j) + 0.5 * np.cos(0.31 * _i * _j)
_jj = np.arange(1, p + 1, dtype=float)[:, None]
_kk = np.arange(1, G + 1, dtype=float)[None, :]
MU = 0.4 * _kk - 0.25 * _jj + 0.1 * _jj * _kk
MU1 = np.array([-0.5, 0.2, 1.1])
PRO = np.array([0.2, 0.3, 0.5])
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

pars_E = {"pro": PRO, "mean": MU1, "variance": {"modelName": "E", "sigmasq": 0.8}}
pars_E_missing = copy.deepcopy(pars_E)
pars_E_missing["mean"][1] = np.nan
pars_E_vanish = {"pro": PRO, "mean": MU1, "variance": {"modelName": "E", "sigmasq": 0.0}}

pars_EII = {"pro": PRO, "mean": MU, "variance": {"modelName": "EII", "sigmasq": 0.9}}
pars_EII_missing = copy.deepcopy(pars_EII)
pars_EII_missing["mean"][0, 0] = np.nan
pars_EII_vanish = {"pro": PRO, "mean": MU, "variance": {"modelName": "EII", "sigmasq": 0.0}}

pars_EEI = {"pro": PRO, "mean": MU, "variance": {"modelName": "EEI", "scale": 0.9, "shape": SHAPE_V}}
pars_EEI_missing = copy.deepcopy(pars_EEI)
pars_EEI_missing["mean"][0, 0] = np.nan

pars_EVI = {"pro": PRO, "mean": MU, "variance": {"modelName": "EVI", "scale": 0.9, "shape": SHAPE_M}}
pars_EVI_missing = copy.deepcopy(pars_EVI)
pars_EVI_missing["mean"][0, 0] = np.nan

pars_EEV = {
    "pro": PRO,
    "mean": MU,
    "variance": {"modelName": "EEV", "scale": 0.9, "shape": SHAPE_V, "orientation": ORI},
}
pars_EEV_missing = copy.deepcopy(pars_EEV)
pars_EEV_missing["mean"][0, 0] = np.nan

pars_EEE = {"pro": PRO, "mean": MU, "variance": {"modelName": "EEE", "cholSigma": CHOL}}
pars_EEE_missing = copy.deepcopy(pars_EEE)
pars_EEE_missing["mean"][0, 0] = np.nan


def emit(res: dict) -> list[float]:
    """Return code first, then z in column-major order. NaN is printed as -1e300, as in R."""
    z = np.asarray(res["z"], dtype=float).ravel(order="F")
    z = np.where(np.isnan(z), -1e300, z)
    return [float(res["returnCode"])] + z.tolist()


def print_values(values) -> None:
    for v in values:
        print("%.17g" % v)
