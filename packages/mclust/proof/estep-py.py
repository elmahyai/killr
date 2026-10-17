import statistics
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from mclust.estep import estep

X = np.array(
    [
        [0.1, 1.5],
        [1.2, 3.8],
        [-0.4, -1.0],
        [2.9, 2.0],
        [3.3, 0.3],
        [2.2, 2.7],
        [0.7, 1.9],
        [4.1, 3.1],
    ]
)
X1 = X[:, 0]


def m(vals, nrow, ncol):
    """R: matrix(vals, nrow, ncol), filled by column."""
    return np.array(vals, dtype=float).reshape((nrow, ncol), order="F")


MU = m([0.5, 0.2, 3.0, 2.5], 2, 2)
MU1 = np.array([0.5, 3.0])
S = m([1.2, 0.3, 0.3, 0.9], 2, 2)
CHOL = np.linalg.cholesky(S).T  # R chol(S): upper triangular


def ROT(th):
    return m([np.cos(th), np.sin(th), -np.sin(th), np.cos(th)], 2, 2)


O2 = np.zeros((2, 2, 2))
O2[:, :, 0] = ROT(0.3)
O2[:, :, 1] = ROT(-0.5)
U = np.zeros((2, 2, 2))
for g in range(1, 3):
    M = np.diag([1.0 + 0.1 * g, 0.8 + 0.1 * g])
    M[0, 1] = 0.3 * g
    U[:, :, g - 1] = M
SH = m([1.0, 1.5, 2.0, 0.8], 2, 2)
SH2 = m([1.5, 0.6, 0.8, 1.4], 2, 2)


def pars_for(model, pro):
    mean = MU1 if model in ("E", "V") else MU
    variance = {
        "E": {"modelName": "E", "sigmasq": 1.5},
        "V": {"modelName": "V", "sigmasq": np.array([1.5, 0.8])},
        "EII": {"modelName": "EII", "sigmasq": 1.1},
        "VII": {"modelName": "VII", "sigmasq": np.array([1.1, 0.7])},
        "EEI": {"modelName": "EEI", "scale": 0.8, "shape": np.array([1.0, 2.0])},
        "VEI": {"modelName": "VEI", "scale": np.array([0.6, 1.4]), "shape": np.array([1.5, 0.7])},
        "EVI": {"modelName": "EVI", "scale": 0.9, "shape": SH},
        "VVI": {"modelName": "VVI", "scale": np.array([0.6, 1.4]), "shape": SH},
        "EEE": {"modelName": "EEE", "cholSigma": CHOL},
        "EVE": {"modelName": "EVE", "scale": 0.9, "shape": SH2, "orientation": ROT(0.3)},
        "VEE": {"modelName": "VEE", "scale": np.array([1.3, 0.7]), "shape": np.array([1.5, 0.6]), "orientation": ROT(0.3)},
        "VVE": {"modelName": "VVE", "scale": np.array([1.3, 0.7]), "shape": SH2, "orientation": ROT(0.3)},
        "EEV": {"modelName": "EEV", "scale": 0.9, "shape": np.array([1.0, 1.7]), "orientation": O2},
        "VEV": {"modelName": "VEV", "scale": np.array([0.6, 1.4]), "shape": np.array([1.5, 0.7]), "orientation": O2},
        "EVV": {"modelName": "EVV", "scale": 0.9, "shape": SH2, "orientation": O2},
        "VVV": {"modelName": "VVV", "cholsigma": U},
    }[model]
    return {"pro": np.asarray(pro, dtype=float), "mean": mean, "variance": variance}


models = ["E", "V", "EII", "VII", "EEI", "VEI", "EVI", "VVI",
          "EEE", "EVE", "VEE", "VVE", "EEV", "VEV", "EVV", "VVV"]
pros = [np.array([0.4, 0.6]), np.array([0.3, 0.5, 0.2])]


def emit(res):
    return [res["loglik"], res["returnCode"]] + np.asarray(res["z"]).ravel(order="F").tolist()


def one():
    out = []
    for model in models:
        dat = X1 if model in ("E", "V") else X
        for pro in pros:
            out.append(estep(dat, model, pars_for(model, pro)))
    return out


value = one()
for res in value:
    for v in emit(res):
        print("%.17g" % v)
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print("%.17g" % statistics.median(elapsed))
