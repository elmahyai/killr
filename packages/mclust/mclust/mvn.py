"""Single-component multivariate normal fits used by mclust."""

from __future__ import annotations

import numpy as np

__all__ = ["mvn", "mvnX", "mvnXII", "mvnXXI", "mvnXXX"]


def _data(data, *, one_d: bool = False) -> np.ndarray:
    x = np.asarray(data, dtype=float)
    if one_d:
        if x.ndim > 2 or (x.ndim == 2 and 1 not in x.shape):
            raise ValueError("data must be one dimensional")
        return x.reshape(-1)
    if x.ndim != 2 or x.shape[1] < 2:
        raise ValueError("for multidimensional data only")
    return x


def _likelihood(x: np.ndarray, sigma: np.ndarray) -> float:
    n, p = x.shape
    sign, logdet = np.linalg.slogdet(sigma)
    if sign <= 0:
        return float("inf")
    return float(-0.5 * n * (p * np.log(2.0 * np.pi) + logdet + p))


def _result(model: str, x: np.ndarray, mean: np.ndarray, variance: dict,
            loglik: float) -> dict:
    p = x.shape[1]
    return {
        "modelName": model,
        "prior": None,
        "n": int(x.shape[0]),
        "d": p,
        "G": 1,
        "parameters": {
            "pro": 1.0,
            "mean": mean.reshape(p, 1),
            "variance": variance,
        },
        "loglik": loglik,
        "returnCode": 0,
    }


def mvnX(data, prior=None, warn=None, **kwargs):
    """Fit a one-dimensional variable-normal model."""
    if prior is not None:
        raise NotImplementedError("mvnX priors are not translated")
    values = _data(data, one_d=True)
    mean = float(np.mean(values))
    sigmasq = float(np.mean((values - mean) ** 2))
    loglik = _likelihood(values.reshape(-1, 1), np.array([[sigmasq]]))
    variance = {"modelName": "X", "d": 1, "G": 1, "sigmasq": sigmasq}
    return _result("X", values.reshape(-1, 1), np.array([mean]), variance, loglik)


def mvnXII(data, prior=None, warn=None, **kwargs):
    """Fit a spherical multivariate normal model."""
    if prior is not None:
        raise NotImplementedError("mvnXII priors are not translated")
    x = _data(data)
    n, p = x.shape
    mean = np.mean(x, axis=0)
    sigmasq = float(np.sum((x - mean) ** 2) / (n * p))
    sigma = sigmasq * np.eye(p)
    variance = {
        "modelName": "XII", "d": p, "G": 1, "sigmasq": sigmasq,
        "Sigma": sigma, "sigma": sigma[:, :, None], "scale": sigmasq,
    }
    result = _result("XII", x, mean, variance, _likelihood(x, sigma))
    if result["loglik"] > _XMAX_SIGNIF6:
        # R: singular covariance, loglik NA, returnCode -1
        result["loglik"] = float("nan")
        result["returnCode"] = -1
    return result


def mvnXXI(data, prior=None, warn=None, **kwargs):
    """Fit a diagonal multivariate normal model."""
    if prior is not None:
        raise NotImplementedError("mvnXXI priors are not translated")
    x = _data(data)
    n, p = x.shape
    mean = np.mean(x, axis=0)
    diagonal = np.sum((x - mean) ** 2, axis=0) / n
    scale = float(np.prod(diagonal) ** (1.0 / p))
    shape = diagonal / scale
    sigma = np.diag(diagonal)
    variance = {
        "modelName": "XXI", "d": p, "G": 1, "Sigma": sigma,
        "sigma": sigma[:, :, None], "scale": scale, "shape": shape,
    }
    result = _result("XXI", x, mean, variance, _likelihood(x, sigma))
    if result["loglik"] > _XMAX_SIGNIF6:
        # R: singular covariance, loglik NA, returnCode -1
        result["loglik"] = float("nan")
        result["returnCode"] = -1
    return result


_XMAX_SIGNIF6 = 1.797693e308


def mvnXXX(data, prior=None, warn=None, **kwargs):
    """Fit a full multivariate normal model.

    R calls the Fortran ``mvnxxx`` routine (``src/mclust.f``) and keeps its
    upper factor as ``cholSigma``. That factor is built by Givens rotations,
    so the sign of each row is whatever the rotations give; it is not forced
    to a positive diagonal. This function calls the same routine through the
    ``mclust_kernels`` binding and returns its output unchanged.
    """
    import mclust_kernels

    if prior is not None:
        raise NotImplementedError("mvnXXX priors are not translated")
    x = _data(data)
    n, p = x.shape
    out = mclust_kernels.mvnxxx(
        (x.ravel(order="F").tolist(), n, p, [0.0] * p, [0.0] * (p * p), 0.0)
    )
    mean = np.asarray(out[3], dtype=float)
    chol = np.asarray(out[4], dtype=float).reshape((p, p), order="F")
    loglik = float(out[5])
    sigma = chol.T @ chol
    variance = {
        "modelName": "XXX", "d": p, "G": 1, "Sigma": sigma,
        "cholSigma": chol, "cholsigma": chol, "sigma": sigma[:, :, None],
    }
    result = _result("XXX", x, mean, variance, loglik)
    if loglik > _XMAX_SIGNIF6:
        # R: singular covariance, loglik NA, returnCode -1
        result["loglik"] = float("nan")
        result["returnCode"] = -1
    return result


def mvn(modelName, data, prior=None, warn=None, **kwargs):
    """Dispatch mclust model aliases to a one-component normal fit."""
    aliases = {
        "E": "X", "V": "X", "X": "X",
        "Spherical": "XII", "EII": "XII", "VII": "XII", "XII": "XII",
        "Diagonal": "XXI", "EEI": "XXI", "VEI": "XXI", "EVI": "XXI",
        "VVI": "XXI", "XXI": "XXI",
        "Ellipsoidal": "XXX", "EEE": "XXX", "VEE": "XXX", "EVE": "XXX",
        "EVV": "XXX", "VVE": "XXX", "EEV": "XXX", "VEV": "XXX",
        "VVV": "XXX", "XXX": "XXX",
    }
    try:
        canonical = aliases[modelName]
    except KeyError as exc:
        raise ValueError("invalid model name") from exc
    return {"X": mvnX, "XII": mvnXII, "XXI": mvnXXI, "XXX": mvnXXX}[
        canonical
    ](data, prior=prior, warn=warn, **kwargs)
