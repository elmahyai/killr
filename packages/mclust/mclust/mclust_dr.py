"""Dimension reduction for model-based clustering and classification."""

from __future__ import annotations

import math
import sys
from typing import Any, Mapping, MutableMapping, Sequence

import numpy as np

__all__ = ["mclust_dr"]


def mclust_dr(
    object: Any,
    lambda_: float = 1.0,
    *,
    normalized: bool = True,
    Sigma: np.ndarray | None = None,
    tol: float | None = None,
):
    """GMMDR dimension reduction for ``Mclust`` or ``MclustDA`` fit objects."""
    if tol is None:
        tol = math.sqrt(sys.float_info.epsilon)

    if _is_mclust(object):
        mclust_type = "Mclust"
    elif _is_mclustda(object):
        mclust_type = object.get("type", "MclustDA")
    else:
        raise ValueError(
            "first argument must be an object of class 'Mclust' or 'MclustDA'"
        )

    x = np.asarray(_field(object, "data"), dtype=float)
    if x.ndim == 1:
        x = x.reshape(-1, 1)
    n, p = x.shape
    lambda_ = float(np.clip(lambda_, 0.0, 1.0))

    mu = x.mean(axis=0)
    if Sigma is None:
        Sigma = np.cov(x, rowvar=False, ddof=0)
        if p == 1:
            Sigma = np.array([[float(Sigma)]], dtype=float)
    else:
        Sigma = np.asarray(Sigma, dtype=float)

    if mclust_type == "Mclust":
        g = int(_field(object, "G"))
        model_name = _field(object, "modelName")
        y = np.asarray(_field(object, "classification"))
        cl2mc = np.arange(1, g + 1, dtype=int)
        # R: class <- as.factor(object$classification); the MclustDR field
        # classification holds one label per observation, as the factor codes.
        classification = _factor_codes(y)
        par = _field(object, "parameters")
        f = _mixing_proportions(par, object, g)
        mu_g = np.asarray(par["mean"], dtype=float).reshape(p, g, order="F")
        sigma_g = _component_covariances(par, p, g)
    else:
        models_obj = _field(object, "models")
        if isinstance(models_obj, Mapping):
            class_levels = [str(k) for k in models_obj.keys()]
            models = list(models_obj.values())
        else:
            models = list(models_obj)
            class_levels = _factor_levels(_field(object, "class"), len(models))
        model_name = [m["modelName"] for m in models]
        # R: class <- factor(object$class, levels = names(object$models)), one label per observation.
        class_obs = np.asarray(
            [str(v) for v in np.asarray(_field(object, "class"), dtype=np.object_).reshape(-1)],
            dtype=np.object_,
        )
        classification = class_obs
        y = _mixcomp_from_mclustda(class_obs, class_levels, models, n)
        cl2mc = np.repeat(
            np.arange(1, len(models) + 1, dtype=int),
            [int(m["G"]) for m in models],
        )
        ncomp = np.array([int(m["G"]) for m in models], dtype=int)
        g = int(ncomp.sum())
        counts = np.array([int(m["n"]) for m in models], dtype=float)
        f = np.empty(g, dtype=float)
        mu_g = np.full((p, g), np.nan, dtype=float)
        sigma_g = np.full((p, p, g), np.nan, dtype=float)
        start = 0
        for i, mod in enumerate(models):
            end = start + int(ncomp[i])
            ii = slice(start, end)
            par = mod["parameters"]
            pro = par.get("pro")
            if pro is None:
                pro = 1.0
            pro = np.asarray(pro, dtype=float).ravel()
            f[ii] = pro * counts[i] / counts.sum()
            mu_g[:, ii] = np.asarray(par["mean"], dtype=float).reshape(p, end - start, order="F")
            sigma_g[:, :, ii] = _component_covariances(par, p, end - start)
            start = end

    inv_sqrt_sigma, _ = _inv_sqrt_from_sigma(Sigma, n, p, tol)
    s = np.zeros((p, p), dtype=float)
    for j in range(g):
        s += f[j] * sigma_g[:, :, j]

    centered = mu_g - mu.reshape(p, 1)
    scaled = centered * np.sqrt(f).reshape(1, g)
    m_i = scaled @ scaled.T

    m_ii = np.zeros((p, p), dtype=float)
    if lambda_ < 1.0:
        for j in range(g):
            diff = inv_sqrt_sigma @ (sigma_g[:, :, j] - s)
            m_ii += f[j] * (diff.T @ diff)

    m_kernel = 2.0 * lambda_ * (inv_sqrt_sigma @ m_i).T @ (inv_sqrt_sigma @ m_i)
    m_kernel += 2.0 * (1.0 - lambda_) * m_ii

    eig = _eigen_decomp(m_kernel, inv_sqrt_sigma, invsqrt=True)
    evalues = (eig["l"] + np.abs(eig["l"])) / 2.0
    numdir = min(p, int(np.sum(evalues > math.sqrt(sys.float_info.epsilon))))
    raw_evectors = np.asarray(eig["v"], dtype=float)
    basis = np.asarray(raw_evectors[:, :numdir], dtype=float)
    sdx = np.diag(Sigma)
    std_basis = basis * sdx.reshape(p, 1)
    if normalized:
        basis = basis / np.linalg.norm(basis, axis=0)
        std_basis = std_basis / np.linalg.norm(std_basis, axis=0)

    x_centered = x - mu
    z = np.asarray(x_centered @ basis)

    return MclustDRResult(
        type=mclust_type,
        x=x,
        Sigma=Sigma,
        classification=classification,
        mixcomp=y,
        class2mixcomp=cl2mc,
        G=g,
        modelName=model_name,
        mu=mu_g,
        sigma=sigma_g,
        pro=f,
        M=m_kernel,
        M_I=m_i,
        M_II=m_ii,
        lambda_=lambda_,
        evalues=evalues,
        raw_evectors=raw_evectors,
        basis=np.asarray(basis),
        std_basis=np.asarray(std_basis),
        numdir=numdir,
        dir=z,
    )


class MclustDRResult(MutableMapping):
    """Object of class ``MclustDR``."""

    _KEYS = (
        "type",
        "x",
        "Sigma",
        "classification",
        "mixcomp",
        "class2mixcomp",
        "G",
        "modelName",
        "mu",
        "sigma",
        "pro",
        "M",
        "M.I",
        "M.II",
        "lambda",
        "evalues",
        "raw.evectors",
        "basis",
        "std.basis",
        "numdir",
        "dir",
    )

    def __init__(self, *, lambda_: float, **fields: Any):
        self._store: dict[str, Any] = {
            "type": fields["type"],
            "x": fields["x"],
            "Sigma": fields["Sigma"],
            "classification": fields["classification"],
            "mixcomp": fields["mixcomp"],
            "class2mixcomp": fields["class2mixcomp"],
            "G": fields["G"],
            "modelName": fields["modelName"],
            "mu": fields["mu"],
            "sigma": fields["sigma"],
            "pro": fields["pro"],
            "M": fields["M"],
            "M.I": fields["M_I"],
            "M.II": fields["M_II"],
            "lambda": lambda_,
            "evalues": fields["evalues"],
            "raw.evectors": fields["raw_evectors"],
            "basis": fields["basis"],
            "std.basis": fields["std_basis"],
            "numdir": fields["numdir"],
            "dir": fields["dir"],
        }

    def __getitem__(self, key: str) -> Any:
        return self._store[key]

    def __setitem__(self, key: str, value: Any) -> None:
        self._store[key] = value

    def __delitem__(self, key: str) -> None:
        del self._store[key]

    def __iter__(self):
        return iter(self._store)

    def __len__(self) -> int:
        return len(self._store)

    def keys(self):
        return self._store.keys()


def _is_mclust(obj: Any) -> bool:
    if isinstance(obj, Mapping):
        return (
            "models" not in obj
            and "G" in obj
            and "classification" in obj
            and "parameters" in obj
            and "data" in obj
        )
    return (
        hasattr(obj, "G")
        and hasattr(obj, "classification")
        and hasattr(obj, "parameters")
        and not hasattr(obj, "models")
    )


def _is_mclustda(obj: Any) -> bool:
    if isinstance(obj, Mapping):
        return "models" in obj and "class" in obj
    return hasattr(obj, "models") and hasattr(obj, "class")


def _field(obj: Any, name: str) -> Any:
    if isinstance(obj, Mapping):
        return obj[name]
    return getattr(obj, name)


def _mixing_proportions(par: Mapping[str, Any], obj: Any, g: int) -> np.ndarray:
    pro = par.get("pro")
    if pro is None:
        f = np.array([1.0], dtype=float)
    else:
        f = np.asarray(pro, dtype=float).ravel()
    if f.size == 1 and g > 1:
        f = np.full(g, f[0], dtype=float)
    hypvol = _field(obj, "hypvol") if _has(obj, "hypvol") else np.nan
    if hypvol is not None and not (isinstance(hypvol, float) and math.isnan(hypvol)):
        f = f[:-1]
    return f


def _has(obj: Any, name: str) -> bool:
    if isinstance(obj, Mapping):
        return name in obj
    return hasattr(obj, name)


def _component_covariances(par: Mapping[str, Any], p: int, g: int) -> np.ndarray:
    var = par["variance"]
    if p == 1:
        sig = np.asarray(var["sigmasq"], dtype=float).ravel()
        out = np.zeros((p, p, g), dtype=float)
        for j in range(g):
            out[0, 0, j] = sig[j] if sig.size > 1 else sig[0]
        return out
    return np.asarray(var["sigma"], dtype=float).reshape(p, p, g, order="F")


def _inv_sqrt_from_sigma(
    sigma: np.ndarray, n: int, p: int, tol: float
) -> tuple[np.ndarray, np.ndarray]:
    _, s, vt = np.linalg.svd(sigma, full_matrices=False)
    if s.size == 0:
        raise ValueError("Sigma has no positive singular values")
    threshold = max(tol * s[0], 0.0)
    pos = np.flatnonzero(s > threshold)
    s = s[pos]
    v = vt[pos].T
    inv_sigma = v @ (np.diag(1.0 / s) @ v.T)
    inv_sqrt = v @ (np.diag(1.0 / np.sqrt(s)) @ v.T)
    return inv_sqrt, inv_sigma


def _eigen_decomp(a: np.ndarray, b: np.ndarray, *, invsqrt: bool = False) -> dict[str, np.ndarray]:
    if invsqrt:
        inv_sqrt_b = b
    else:
        inv_sqrt_b, _ = _inv_sqrt_from_sigma(b, b.shape[0], b.shape[0], sys.float_info.epsilon)
    sym = inv_sqrt_b.T @ a @ inv_sqrt_b
    _, s, vt = np.linalg.svd(sym, full_matrices=False)
    vectors = inv_sqrt_b @ vt.T
    return {"l": s, "v": vectors}


def _factor_codes(values: Any) -> np.ndarray:
    """Integer codes of ``as.integer(factor(values))``: rank among the sorted unique labels."""
    arr = np.asarray(values)
    levels = np.unique(arr)
    return (np.searchsorted(levels, arr) + 1).astype(int)


def _factor_levels(values: Any, g: int) -> list[str]:
    arr = np.asarray(values)
    if arr.dtype.kind in ("U", "S", "O"):
        levels = []
        for item in arr:
            text = str(item)
            if text not in levels:
                levels.append(text)
        if len(levels) >= g:
            return levels[:g] if g else levels
        return [str(i + 1) for i in range(g)]
    return [str(i + 1) for i in range(g)]


def _mixcomp_from_mclustda(
    class_obs: np.ndarray, class_levels: Sequence[str], models: Sequence[Mapping[str, Any]], n: int
) -> np.ndarray:
    """R: y[class == level] <- paste(level, classification, sep = ":"); y <- as.numeric(factor(y))."""
    labels = np.empty(n, dtype=object)
    for i, level in enumerate(class_levels):
        mask = class_obs == level
        inner = np.asarray(models[i]["classification"]).reshape(-1)
        labels[mask] = [f"{level}:{part}" for part in inner]
    levels = sorted(set(str(v) for v in labels))
    index = {lev: k + 1 for k, lev in enumerate(levels)}
    return np.asarray([index[str(v)] for v in labels], dtype=float)
