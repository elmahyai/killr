"""EEE Gaussian mixture steps (mstep, estep, cdens, dens) via cvmclustda."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import numpy as np

from mclust._mclust_mutils import logsumexp_rows, mclust_bic, unmap

try:
    from cvmclustda import eseee, mseee, uncholf
except ImportError:
    sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "crates" / "cvmclustda"))
    from cvmclustda import eseee, mseee, uncholf


def _f64(x: np.ndarray) -> np.ndarray:
    return np.asfortranarray(np.asarray(x, dtype=float))


def mstep_eee(data: np.ndarray, z: np.ndarray, *, warn: bool = False) -> dict[str, Any]:
    data = _f64(data)
    z = _f64(z)
    n, p = data.shape
    g = z.shape[1]
    mu_flat, u_flat, pro, p_i, g_i, _n_i = mseee(data, z)
    p_i, g_i = int(p_i), int(g_i)
    mu = _f64(np.asarray(mu_flat, dtype=float).reshape(p_i, g_i, order="F"))
    chol_sigma = _f64(np.asarray(u_flat, dtype=float).reshape(p_i, p_i, order="F"))
    sigma = uncholf(True, chol_sigma)
    sigma = _f64(sigma)
    sigma_arr = np.zeros((p, p, g), dtype=float, order="F")
    for k in range(g):
        sigma_arr[:, :, k] = sigma
    variance = {
        "modelName": "EEE",
        "d": p,
        "G": g,
        "sigma": sigma_arr,
        "Sigma": sigma,
        "cholSigma": chol_sigma,
    }
    parameters = {"pro": np.asarray(pro, dtype=float), "mean": mu, "variance": variance}
    return {
        "modelName": "EEE",
        "prior": None,
        "n": n,
        "d": p,
        "G": g,
        "z": z,
        "parameters": parameters,
    }


def estep_eee(data: np.ndarray, parameters: dict[str, Any], *, warn: bool = False) -> dict[str, Any]:
    data = _f64(data)
    n, p = data.shape
    pro = np.asarray(parameters["pro"], dtype=float)
    pro = pro / pro.sum()
    mu = _f64(np.asarray(parameters["mean"], dtype=float))
    g = mu.shape[1]
    chol = _f64(np.asarray(parameters["variance"]["cholSigma"], dtype=float))
    lap_info, loglik, z_flat, n_i, k_i = eseee(True, data, mu, chol, pro, -1.0)
    z = np.asarray(z_flat, dtype=float).reshape(int(n_i), int(k_i), order="F")
    if lap_info != 0:
        loglik = float("nan")
    return {
        "modelName": "EEE",
        "n": n,
        "d": p,
        "G": g,
        "z": z,
        "parameters": parameters,
        "loglik": float(loglik),
    }


def cdens_eee(
    data: np.ndarray, parameters: dict[str, Any], *, logarithm: bool = False, warn: bool = False
) -> np.ndarray:
    data = _f64(data)
    n, p = data.shape
    mu = _f64(np.asarray(parameters["mean"], dtype=float))
    g = mu.shape[1]
    chol = _f64(np.asarray(parameters["variance"]["cholSigma"], dtype=float))
    pro = np.array([-1.0] * g, dtype=float)
    lap_info, _, z_flat, n_i, k_i = eseee(True, data, mu, chol, pro, -1.0)
    z = np.asarray(z_flat, dtype=float).reshape(int(n_i), int(k_i), order="F")
    if lap_info != 0:
        z[:] = np.nan
    elif not logarithm:
        z = np.exp(z)
    return z


def dens_eee(
    data: np.ndarray,
    parameters: dict[str, Any],
    *,
    logarithm: bool = False,
    warn: bool = False,
) -> np.ndarray:
    log_cden = cdens_eee(data, parameters, logarithm=True, warn=warn)
    pro = np.asarray(parameters["pro"], dtype=float)
    pro = pro / pro.sum()
    logden = logsumexp_rows(log_cden, np.log(pro))
    return logden if logarithm else np.exp(logden)


def edda_fit_model(
    data: np.ndarray, class_levels: list[str], class_codes: np.ndarray, model_name: str
) -> dict[str, Any]:
    z = unmap(class_codes + 1, class_levels=class_levels)
    mstep = mstep_eee(data, z, warn=False)
    estep = estep_eee(data, mstep["parameters"], warn=False)
    bic = mclust_bic(
        model_name, estep["loglik"], estep["n"], estep["d"], estep["G"], equal_pro=True
    )
    estep["BIC"] = bic
    return estep
