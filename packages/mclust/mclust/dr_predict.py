"""Prediction and discriminant-coordinate helpers for mclust."""

from __future__ import annotations

from typing import Any, Mapping

import numpy as np

from mclust._mclust_em_for_ssc import em_cdens
from mclust.dmvnorm import dmvnorm
from mclust.logsumexp import logsumexp
from mclust.mclust_dr import _field
from mclust.projpar_mclust_dr import projpar_MclustDR
from mclust.softmax import softmax

__all__ = ["predict_MclustSSC", "predict_MclustDR", "predict2D_MclustDR", "crimcoords"]


def predict_MclustSSC(object: Any, newdata: Any | None = None, **_: Any) -> dict[str, Any]:
    """Predict classes and posterior probabilities from an ``MclustSSC`` fit."""
    data = np.asarray(_field(object, "data"), dtype=float)
    if newdata is None:
        newdata = data
    x = np.asarray(newdata, dtype=float)
    if x.ndim == 1:
        x = x.reshape(1, -1)
    if x.shape[1] != data.shape[1]:
        raise ValueError("newdata must match ncol of object data")
    pars = _field(object, "parameters")
    scores = em_cdens(x, {**dict(object), "data": x}, logarithm=True)
    pro = np.asarray(pars.get("pro", 1.0), dtype=float).ravel()
    if pro.size == 1:
        pro = np.repeat(pro, scores.shape[1])
    z = softmax(scores, np.log(pro) - np.log(np.sum(pro)))
    classes = np.asarray(_field(object, "classification"), dtype=np.dtype("O"))
    levels = list(dict.fromkeys(str(v) for v in classes if v is not None and str(v) != "nan"))
    if len(levels) < z.shape[1]:
        levels.extend(f"class{i}" for i in range(len(levels) + 1, z.shape[1] + 1))
    labels = np.asarray([levels[i] for i in np.argmax(z, axis=1)], dtype=np.dtype("O"))
    return {"classification": labels, "z": z}


def predict_MclustDR(
    object: Any,
    dim: Any = None,
    newdata: Any | None = None,
    eval_points: Any | None = None,
    **_: Any,
) -> dict[str, Any]:
    """Predict density, posterior classes, and uncertainty in DR coordinates."""
    numdir = int(_field(object, "numdir"))
    dims = np.arange(1, numdir + 1) if dim is None else np.asarray(dim, dtype=int).ravel()
    dims = dims[dims <= numdir]
    if newdata is None and eval_points is None:
        directions = np.asarray(_field(object, "dir"))[:, dims - 1]
    elif newdata is not None:
        x = np.asarray(newdata, dtype=float)
        if x.ndim == 1:
            x = x.reshape(1, -1)
        directions = (x - np.asarray(_field(object, "x")).mean(axis=0)) @ np.asarray(_field(object, "basis"))[:, dims - 1]
    else:
        directions = np.asarray(eval_points, dtype=float)
        if directions.ndim == 1:
            directions = directions.reshape(1, -1)
    par = projpar_MclustDR(object, dims)
    g = int(_field(object, "G"))
    logz = np.column_stack([dmvnorm(directions, par["mean"][j], par["variance"][:, :, j], log=True) for j in range(g)])
    logden = logsumexp(logz, np.log(np.asarray(_field(object, "pro"), dtype=float)))
    zmix = softmax(logz, np.log(np.asarray(_field(object, "pro"), dtype=float)))
    class_map = np.asarray(_field(object, "class2mixcomp"), dtype=int)
    # R: nclass <- nlevels(object$classification); the levels of an Mclust
    # result are the distinct per-observation labels.
    if str(_field(object, "type")) == "Mclust":
        levels = np.unique(np.asarray(_field(object, "classification")))
        classes = np.asarray([str(v) for v in levels], dtype=np.dtype("O"))
    else:
        classes = np.asarray(_field(object, "classification"), dtype=np.dtype("O"))
    nclass = len(classes)
    z = np.column_stack([zmix[:, class_map == (j + 1)].sum(axis=1) for j in range(nclass)])
    labels = classes[np.argmax(z, axis=1)]
    return {"dir": directions, "density": np.exp(logden), "z": z,
            "uncertainty": 1.0 - np.max(z, axis=1), "classification": labels}


def predict2D_MclustDR(object: Any, dim: Any = (1, 2), ngrid: int = 100,
                       xlim: Any | None = None, ylim: Any | None = None) -> dict[str, Any]:
    """Evaluate a two-dimensional DR prediction on a regular grid."""
    dims = np.asarray(dim, dtype=int).ravel()[:2]
    directions = np.asarray(_field(object, "dir"))[:, dims - 1]
    if xlim is None:
        xlim = (directions[:, 0].min(), directions[:, 0].max())
    if ylim is None:
        ylim = (directions[:, 1].min(), directions[:, 1].max())
    x = np.linspace(xlim[0], xlim[1], ngrid)
    y = np.linspace(ylim[0], ylim[1], ngrid)
    grid = np.column_stack([np.repeat(x, ngrid), np.tile(y, ngrid)])
    pred = predict_MclustDR(object, dims, eval_points=grid)
    return {"x": x, "y": y, "density": pred["density"].reshape(ngrid, ngrid),
            "z": pred["z"].reshape(ngrid, ngrid, -1),
            "uncertainty": pred["uncertainty"].reshape(ngrid, ngrid),
            "classification": pred["classification"].reshape(ngrid, ngrid)}


def crimcoords(data: Any, classification: Any, numdir: int | None = None,
               unbiased: bool = False, **_: Any) -> dict[str, Any]:
    """Compute canonical discriminant coordinates."""
    x = np.asarray(data, dtype=float)
    if x.ndim == 1:
        x = x[:, None]
    labels = np.asarray(classification)
    if labels.size != x.shape[0]:
        raise ValueError("length(classification) == nrow(data) is not TRUE")
    levels, codes = np.unique(labels, return_inverse=True)
    z = np.eye(len(levels))[codes]
    nk = z.sum(axis=0)
    means = (z.T @ x) / nk[:, None]
    zm = z @ means
    grand = x.mean(axis=0)
    w = (x - zm).T @ (x - zm) / (x.shape[0] - len(levels) if unbiased else x.shape[0])
    b = (zm - grand).T @ (zm - grand) / (len(levels) - 1 if unbiased else len(levels))
    invsqrt = _inverse_sqrt(w)
    vals, vec = np.linalg.eigh(invsqrt @ b @ invsqrt)
    order = np.argsort(vals)[::-1]
    vals, vec = vals[order], vec[:, order]
    basis = invsqrt @ vec
    vals = np.maximum(vals, 0.0)
    nd = min(x.shape[1], int(np.sum(vals > np.sqrt(np.finfo(float).eps))) if numdir is None else int(numdir))
    basis = basis[:, :nd]
    projection = x @ basis
    signs = np.sign(np.median(projection, axis=0))
    signs[signs == 0] = 1
    basis *= signs
    projection *= signs
    return {"means": means, "B": b, "W": w, "evalues": vals, "basis": basis,
            "projection": projection, "classification": labels}


def _inverse_sqrt(matrix: np.ndarray) -> np.ndarray:
    vals, vec = np.linalg.eigh(np.asarray(matrix, dtype=float))
    keep = vals > np.finfo(float).eps * max(vals.max(), 1.0)
    return (vec[:, keep] / np.sqrt(vals[keep])) @ vec[:, keep].T
