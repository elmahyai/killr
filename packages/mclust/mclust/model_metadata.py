"""Model metadata and covariance helpers from mclust."""

from __future__ import annotations

from typing import Any

import numpy as np


_MODELS = (
    "E", "V", "EII", "VII", "EEI", "VEI", "EVI", "VVI",
    "EEE", "EVE", "VEE", "VVE", "EEV", "VEV", "EVV", "VVV",
)
_ALIASES = {"X": "E", "XII": "EII", "XXI": "EEI", "XXX": "EEE"}
_MODEL_TYPES = {
    "E": "univariate, equal variance", "V": "univariate, unequal variance",
    "EII": "spherical, equal volume", "VII": "spherical, varying volume",
    "EEI": "diagonal, equal volume and shape", "VEI": "diagonal, equal shape",
    "EVI": "diagonal, equal volume, varying shape",
    "VVI": "diagonal, varying volume and shape",
    "EEE": "ellipsoidal, equal volume, shape and orientation",
    "EVE": "ellipsoidal, equal volume and orientation",
    "VEE": "ellipsoidal, equal shape and orientation",
    "VVE": "ellipsoidal, equal orientation",
    "EEV": "ellipsoidal, equal volume and shape", "VEV": "ellipsoidal, equal shape",
    "EVV": "ellipsoidal, equal volume",
    "VVV": "ellipsoidal, varying volume, shape, and orientation",
    "X": "univariate normal", "XII": "spherical multivariate normal",
    "XXI": "diagonal multivariate normal", "XXX": "ellipsoidal multivariate normal",
}


def checkModelName(modelName: str) -> bool:
    if modelName not in _MODELS and modelName not in _ALIASES:
        raise ValueError("invalid model name")
    return True


def nVarParams(modelName: str, d: int, G: int, **_: Any) -> int:
    name = _ALIASES.get(modelName, modelName)
    table = {
        "E": 1, "V": G, "EII": 1, "VII": G, "EEI": d,
        "VEI": G + d - 1, "EVI": 1 + G * (d - 1), "VVI": G * d,
        "EEE": d * (d + 1) // 2, "EVE": 1 + G * (d - 1) + d * (d - 1) // 2,
        "VEE": G + d - 1 + d * (d - 1) // 2,
        "VVE": G + G * (d - 1) + d * (d - 1) // 2,
        "EEV": 1 + d - 1 + G * d * (d - 1) // 2,
        "VEV": G + d - 1 + G * d * (d - 1) // 2,
        "EVV": 1 - G + G * d * (d + 1) // 2,
        "VVV": G * d * (d + 1) // 2,
    }
    if name not in table:
        raise ValueError("invalid model name")
    return int(table[name])


def nMclustParams(modelName: str, d: int, G: int, noise: bool = False,
                  equalPro: bool = False, **_: Any) -> int:
    name = _ALIASES.get(modelName, modelName)
    checkModelName(name)
    if G == 0:
        if not noise:
            raise ValueError("undefined model")
        return 1
    ans = nVarParams(name, d, G) + G * d
    if not equalPro:
        ans += G - 1
    if noise:
        ans += 2
    return int(ans)


def mclustModelNames(model: str) -> dict[str, Any]:
    if model not in _MODEL_TYPES:
        raise ValueError("invalid model")
    return {"model": model, "type": _MODEL_TYPES[model]}


def mclustVariance(modelName: str, d: int | None = None, G: int = 2) -> dict[str, Any]:
    x = -1.0
    if len(modelName) == 1:
        if d is not None and d != 1:
            raise ValueError("modelName and d are incompatible")
        if modelName not in ("X", "E", "V"):
            raise ValueError("modelName not recognized")
        return {"modelName": modelName, "d": d, "G": G,
                "sigmasq": x if modelName != "V" else np.full(G, x)}
    if len(modelName) != 3:
        raise ValueError("modelName is misspecified")
    d = 3 if d is None else d
    def tri():
        m = np.full((d, d), x)
        m[np.tril_indices(d, -1)] = 0
        return m
    if modelName in ("XII",):
        out = {"sigmasq": x}
    elif modelName in ("EII",):
        out = {"sigmasq": x, "scale": x, "shape": np.full(d, x)}
    elif modelName == "VII":
        out = {"sigmasq": np.full(G, x), "scale": np.full(G, x), "shape": np.full(d, x)}
    elif modelName in ("XXI", "EEI"):
        out = {"scale": x, "shape": np.full(d, x)}
    elif modelName == "EVI":
        out = {"scale": x, "shape": np.full((d, G), x)}
    elif modelName == "VEI":
        out = {"scale": np.full(G, x), "shape": np.full(d, x)}
    elif modelName == "VVI":
        out = {"scale": np.full(G, x), "shape": np.full((d, G), x)}
    elif modelName in ("XXX", "EEE"):
        out = {"cholSigma": tri()}
    elif modelName == "VEE":
        out = {"scale": np.full(G, x), "shape": np.full(d, x), "orientation": np.full((d, d), x)}
    elif modelName == "VVE":
        out = {"scale": np.full(G, x), "shape": np.full((d, G), x), "orientation": np.full((d, d), x)}
    elif modelName in ("EVE",):
        out = {"scale": x, "shape": np.full((d, G), x), "orientation": np.full((d, d), x)}
    elif modelName in ("EVV", "EEV", "VEV"):
        shape = np.full((d, G), x) if modelName != "EEV" else np.full(d, x)
        out = {"scale": x, "shape": shape, "orientation": np.full((d, d, G), x)}
    elif modelName == "VVV":
        a = np.full((d, d, G), x)
        a[np.tril_indices(d, -1), :] = 0
        out = {"cholsigma": a}
    else:
        raise ValueError("modelName not recognized")
    return {"modelName": modelName, "d": d, "G": G, **out}


def decomp2sigma(d: int | None, G: int | None, scale: Any, shape: Any,
                 orientation: Any = None, **_: Any) -> dict[str, Any]:
    sc = np.asarray(scale, dtype=float).ravel()
    sh = np.asarray(shape, dtype=float)
    if sh.ndim == 1:
        sh = sh[:, None]
    p = sh.shape[0]
    if d is not None and p != d:
        raise ValueError("shape incompatible with d")
    g_shape = sh.shape[1]
    if sc.size != 1:
        if G is not None and G != sc.size:
            raise ValueError("scale incompatibile with G")
        G = sc.size
    if g_shape != 1:
        if G is not None and g_shape != G:
            raise ValueError("shape incompatible with scale")
        G = g_shape
    if orientation is None:
        orient_name = "I"
        G = 1 if G is None else G
        ori = np.repeat(np.eye(p)[:, :, None], G, axis=2)
    else:
        ori = np.asarray(orientation, dtype=float)
        if ori.ndim == 2:
            orient_name, ori = "E", np.repeat(ori[:, :, None], 1 if G is None else G, axis=2)
        elif ori.ndim == 3:
            orient_name = "V"
            if G is None:
                G = ori.shape[2]
        else:
            raise ValueError("orientation improperly specified")
        if ori.shape[:2] != (p, p) or (G is not None and ori.shape[2] != G):
            raise ValueError("orientation incompatible with shape")
    G = 1 if G is None else G
    if G == 1:
        scale_name = shape_name = "X"
    else:
        scale_name = "E" if sc.size == 1 else "V"
        shape_name = "E" if g_shape == 1 else "V"
        sc = np.resize(sc, G)
        sh = np.resize(sh, (p, G))
    sigma = np.empty((p, p, G))
    for k in range(G):
        a = ori[:, :, k] * np.sqrt(sc[k] * sh[:, k])[None, :]
        sigma[:, :, k] = a @ a.T
    return {"sigma": sigma, "modelName": scale_name + shape_name + orient_name,
            "d": p, "G": G, "scale": float(sc[0]) if G == 1 else sc,
            "shape": sh[:, 0] if G == 1 else sh, "orientation": ori[:, :, 0] if G == 1 else ori}


def sigma2decomp(sigma: Any, G: int | None = None,
                 tol: float = np.sqrt(np.finfo(float).eps), **_: Any) -> dict[str, Any]:
    s = np.asarray(sigma, dtype=float)
    if s.ndim not in (2, 3) or s.shape[0] != s.shape[1]:
        raise ValueError("sigma improperly specified")
    d = s.shape[0]
    if s.ndim == 2:
        G = 1 if G is None else G
        s = np.repeat(s[:, :, None], G, axis=2)
    elif G is None:
        G = s.shape[2]
    elif G != s.shape[2]:
        raise ValueError("sigma and G are incompatible")
    scales, shapes, orientations = [], [], []
    for k in range(G):
        vals, vecs = np.linalg.eigh(s[:, :, k])
        logs = np.where(np.isfinite(np.log(vals)), np.log(vals), 0.0)
        ls = logs.mean()
        scales.append(np.exp(ls)); shapes.append(np.exp(logs - ls)); orientations.append(vecs)
    sc = np.asarray(scales); sh = np.stack(shapes, axis=1); ori = np.stack(orientations, axis=2)
    scale_equal = np.max(sc) - np.min(sc) < tol
    if scale_equal: sc = sc[0]
    shape_equal_rows = np.all(np.max(sh, axis=1) - np.min(sh, axis=1) < tol)
    if np.all(shape_equal_rows):
        sh = sh[:, 0]
        shape_name = "I" if np.max(sh) - np.min(sh) < tol else "E"
        if shape_name == "I": sh = np.ones(d)
    else: shape_name = "V"
    eq_ori = all(np.max(np.abs(ori[:, :, 0].T @ ori[:, :, k])) > 1 - tol for k in range(G))
    if eq_ori:
        ori = ori[:, :, 0]
        orient_name = "I" if np.allclose(np.abs(ori), np.eye(d), atol=tol) else "E"
    else: orient_name = "V"
    model = ("E" if scale_equal else "V") + shape_name + orient_name
    return {"sigma": s, "d": d, "modelName": model, "G": G, "scale": sc,
            "shape": sh, "orientation": ori}


def partconv(x: Any, consec: bool = True) -> np.ndarray:
    arr = np.asarray(x)
    y = np.zeros(arr.size, dtype=int)
    if consec:
        for i, value in enumerate(dict.fromkeys(arr.tolist()), 1):
            y[arr == value] = i
    else:
        for value in dict.fromkeys(arr.tolist()):
            mask = arr == value
            y[mask] = np.flatnonzero(mask)[0] + 1
    return y


def partuniq(x: Any) -> np.ndarray:
    arr = np.asarray(x)
    if arr.ndim == 1: arr = arr[:, None]
    seen: dict[tuple[Any, ...], int] = {}
    out = np.arange(1, len(arr) + 1)
    for i, row in enumerate(arr):
        key = tuple(row.tolist())
        if key in seen: out[i] = seen[key]
        else: seen[key] = i + 1
    return out


def priorControl(functionName: str = "defaultPrior", **kwargs: Any) -> dict[str, Any]:
    return {"functionName": functionName, **kwargs}


def defaultPrior(data: Any, G: int, modelName: str, **kwargs: Any) -> dict[str, Any]:
    x = np.asarray(data, dtype=float)
    shrink = kwargs.get("shrinkage", 0.01)
    if shrink is None or (isinstance(shrink, float) and np.isnan(shrink)) or not shrink: shrink = 0
    if shrink < 0: raise ValueError("negative value given for shrinkage")
    mean = np.mean(x, axis=0) if x.ndim > 1 else np.mean(x)
    if "mean" in kwargs:
        if np.any(np.isnan(kwargs["mean"])):
            if shrink: raise ValueError("positive shrinkage with no prior mean specified")
        else:
            if not shrink: raise ValueError("prior mean specified but not shrinkage")
            mean = np.asarray(kwargs["mean"], dtype=float)
    if modelName in ("E", "V", "X"):
        scale = kwargs.get("scale", np.var(x, ddof=1) / G**2)
        return {"shrinkage": shrink, "mean": mean, "dof": 3, "scale": scale}
    if modelName in ("EII", "VII", "XII", "EEI", "EVI", "VEI", "VVI", "XXI"):
        p = x.shape[1]; fac = (1 / G) ** (2 / p)
        scale = kwargs.get("scale", fac * np.sum(np.var(x, axis=0, ddof=1)) / p)
        return {"shrinkage": shrink, "mean": mean, "dof": p + 2, "scale": scale}
    if modelName in ("EEE", "EVE", "VEE", "VVE", "EEV", "VEV", "EVV", "VVV", "XXX"):
        p = x.shape[1]; fac = (1 / G) ** (2 / p)
        scale = kwargs.get("scale", fac * (np.cov(x, rowvar=False) if len(x) > p else np.diag(np.var(x, axis=0, ddof=1))))
        return {"shrinkage": shrink, "mean": mean, "dof": p + 2, "scale": scale}
    raise ValueError("no default prior for this model")


_KMNS = None


def _kmeans_hartigan_wong(rows, centers):
    """R ``kmeans(x, centers)`` with the default Hartigan-Wong algorithm, ``iter.max = 10``.

    The Hartigan-Wong routine (R ``stats`` ``kmns.f``, AS 136) has a Python port in
    ``packages/e1071`` (``_kmns.py``); it is loaded from that file, not copied.
    """
    global _KMNS
    if _KMNS is None:
        import importlib.util
        from pathlib import Path

        path = Path(__file__).resolve().parents[2] / "e1071" / "e1071" / "_kmns.py"
        spec = importlib.util.spec_from_file_location("_e1071_kmns", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        _KMNS = module.kmeans_hartigan_wong
    return _KMNS(rows, centers, iter_max=10)


def dupPartition(data: Any) -> np.ndarray:
    """R ``dupPartition``: 1:n when rows are distinct, else kmeans on the distinct rows.

    ``duplicated`` marks the repeated rows; ``kmeans(data, centers = data[!dup, ])``
    gives the class of every row. A vector is one column, as in R.
    """
    x = np.asarray(data, dtype=float)
    rows = x.reshape(-1, 1) if x.ndim == 1 else x.reshape(x.shape[0], -1)
    n = rows.shape[0]
    first: dict[tuple, int] = {}
    keep: list[int] = []
    dup = np.zeros(n, dtype=bool)
    for i, key in enumerate(map(tuple, rows.tolist())):
        if key in first:
            dup[i] = True
        else:
            first[key] = i
            keep.append(i)
    if not dup.any():
        return np.arange(1, n + 1)
    centers = rows[keep].tolist()
    out = _kmeans_hartigan_wong(rows.tolist(), centers)
    return np.asarray(out["cluster"], dtype=int)


def mclustModel(data: Any, BICvalues: Any, G: Any = None,
                modelNames: Any = None, **kwargs: Any) -> dict[str, Any]:
    """Select the maximum-BIC model from an array or mapping of BIC values."""
    if isinstance(BICvalues, dict):
        key = max(BICvalues, key=BICvalues.get)
        best = float(BICvalues[key])
        model = key if isinstance(key, str) else str(key)
    else:
        vals = np.asarray(BICvalues, dtype=float)
        idx = np.unravel_index(np.nanargmax(vals), vals.shape)
        best = float(vals[idx])
        models = list(modelNames) if modelNames is not None else list(_MODELS)
        model = models[idx[-1]] if models else None
    return {"modelName": model, "G": G, "BIC": best, "data": np.asarray(data)}

