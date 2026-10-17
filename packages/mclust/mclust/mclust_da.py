"""MclustDA (EDDA path for cvMclustDA proofs and EDDA fits)."""

from __future__ import annotations

from typing import Any, Mapping, MutableMapping, Sequence

import numpy as np

from mclust._mclust_mutils import unmap
from mclust.bic import bic as _bic
from mclust.em_control import em_control
from mclust.estep import estep as _estep
from mclust.mclust_options import mclust_options
from mclust.mstep_loglik_icl import mstep as _mstep

__all__ = ["mclust_da", "MclustDA"]


def _factor_key(value: str) -> tuple[int, float, str]:
    try:
        return (0, float(value), value)
    except ValueError:
        return (1, 0.0, value)


def _r_factor(values) -> tuple[np.ndarray, list[str]]:
    """R ``as.factor``: sorted levels (numeric levels in numeric order)."""
    text = [str(v) for v in np.asarray(values, dtype=object).reshape(-1)]
    levels = sorted(set(text), key=_factor_key)
    index = {lev: i for i, lev in enumerate(levels)}
    return np.array([index[v] for v in text], dtype=int), levels


def mclust_da(
    data,
    class_,
    *,
    G=None,
    model_names=None,
    model_type: str = "MclustDA",
    prior=None,
    control=None,
    initialization=None,
    warn=None,
    verbose: bool = False,
    **kwargs,
):
    if data is None:
        raise ValueError("no training data provided!")
    data = np.asarray(data, dtype=float)
    if data.ndim == 1:
        data = data.reshape(-1, 1)
    mask = ~np.any(np.isnan(data), axis=1)
    data = data[mask]
    n, d = data.shape
    if class_ is None:
        raise ValueError("class labels for training data must be provided!")
    class_arr = np.asarray(class_, dtype=object)[mask]
    codes, class_label = _r_factor(class_arr)
    ncl = len(class_label)
    prop = np.array([np.sum(codes == i) for i in range(ncl)], dtype=float) / n
    if model_type not in ("MclustDA", "EDDA"):
        raise ValueError("model_type must be 'MclustDA' or 'EDDA'")
    if model_names is None:
        model_names = list(mclust_options("emModelNames")) if d > 1 else ["E", "V"]
    if isinstance(model_names, str):
        model_names = [model_names]
    model_name_list = list(model_names)
    if model_type == "EDDA":
        # R: one M-step per name in unique(unlist(modelNames)), each on z = unmap(class),
        # G = number of classes, BIC with equalPro = TRUE. The last model holding the
        # running maximum BIC is kept.
        union: list[str] = []
        for names in _class_model_names(model_name_list, [int(np.sum(codes == l)) for l in range(len(class_label))], d):
            for name in names:
                if name not in union:
                    union.append(name)
        z = unmap(codes + 1, class_levels=class_label)
        chosen = None
        bics: list[float] = []
        for name in union:
            ms = _mstep(data, name, z, warn=False)
            es = _estep(data, name, ms["parameters"], warn=False)
            value = float(_bic(name, es["loglik"], es["n"], es["d"], es["G"], equalPro=True))
            bics.append(value)
            finite = [b for b in bics if not np.isnan(b)]
            if not np.isnan(value) and value >= max(finite):
                chosen = es
        if chosen is None:
            raise ValueError("No model(s) can be estimated!!")
        models: dict[str, Any] = {}
        for l, label in enumerate(class_label):
            idx = codes == l
            mod = {
                "modelName": chosen["modelName"],
                "n": int(idx.sum()),
                "d": d,
                "G": 1,
                "parameters": _split_class_parameters(chosen["parameters"], l, d, one_d=(d == 1)),
                "classification": np.ones(int(idx.sum()), dtype=int),
                "observations": np.flatnonzero(idx) + 1,
            }
            models[label] = mod
        return _finish_da(
            data, class_arr, class_label, prop, models, model_type, n, d, G, prior, control, initialization, warn, model_name_list
        )
    # modelType == "MclustDA": one mclustBIC fit per class, as R/mclustda.R does.
    from mclust.bic_family import mclustBIC
    from mclust.summary_mclust_bic import summaryMclustBIC

    ncl_ = len(class_label)
    counts = [int(np.sum(codes == l)) for l in range(ncl_)]
    G_per = _class_groups(G, ncl_)
    names_per = _class_model_names(model_name_list, counts, d)
    models: dict[str, Any] = {}
    for l, label in enumerate(class_label):
        idx = codes == l
        sub = data[idx]
        xs = sub[:, 0] if d == 1 else sub
        G_l, M_l = list(G_per[l]), list(names_per[l])
        bic = mclustBIC(xs, G=G_l, modelNames=M_l, prior=prior,
                        control=control, warn=warn)
        # R: while all BIC values are NA, lower G or fall back to a simpler model.
        while np.all(np.isnan(np.asarray(bic["values"], dtype=float))):
            if len(M_l) == 1:
                em = list(mclust_options("emModelNames"))
                j = em.index(M_l[0])
                if j == 0:
                    G_l = [g - 1 for g in G_l]
                else:
                    M_l = [em[j - 1]]
            else:
                G_l = [g - 1 for g in G_l]
            bic = mclustBIC(xs, G=G_l, modelNames=M_l, prior=prior,
                            control=control, warn=warn)
        summ = summaryMclustBIC(bic, data=xs)
        # R: SUMMARY$bic <- BIC, then the element is renamed "BIC".
        fitted: dict[str, Any] = {}
        for key, value in summ.items():
            if key == "bic":
                fitted["BIC"] = bic
            else:
                fitted[key] = value
        if "BIC" not in fitted:
            fitted["BIC"] = bic
        fitted["observations"] = np.flatnonzero(idx) + 1
        models[label] = fitted

    return _finish_da(
        data, class_arr, class_label, prop, models, model_type, n, d, G, prior, control, initialization, warn, model_name_list
    )


def _finish_da(
    data, class_arr, class_label, prop, models, model_type, n, d, G, prior, control, initialization, warn, model_name_list
):
    """R: the MclustDA object, then loglik, df and bic from logLik.MclustDA."""
    from mclust.loglik_mclust_da import logLik_MclustDA

    out = {
        "call": {
            "data": data,
            "class": class_arr,
            "model_type": model_type,
            "model_names": model_name_list,
            "G": G,
            "prior": prior,
            "control": control or em_control(),
            "initialization": initialization,
            "warn": warn,
        },
        "data": data,
        "class": class_arr,
        "type": model_type,
        "n": n,
        "d": d,
        "prop": dict(zip(class_label, prop)),
        "models": models,
        "bic": None,
        "loglik": None,
        "df": None,
    }
    ll = logLik_MclustDA(out, data)
    out["loglik"] = float(ll)
    out["df"] = int(ll.df)
    out["bic"] = 2.0 * out["loglik"] - np.log(n) * out["df"]
    return out


def _class_groups(G, ncl: int) -> list[list[int]]:
    """R: G is 1:5 per class by default, 1 for a single class, else sorted."""
    if ncl == 1:
        return [[1]]
    if G is None:
        return [list(range(1, 6)) for _ in range(ncl)]
    if isinstance(G, (list, tuple)) and G and all(
        isinstance(g, (list, tuple, np.ndarray)) for g in G
    ):
        return [sorted(int(v) for v in g) for g in G]
    vals = sorted(int(v) for v in np.atleast_1d(G))
    if any(v <= 0 for v in vals):
        raise ValueError("G must be positive")
    return [list(vals) for _ in range(ncl)]


def _class_model_names(model_names, counts, d: int) -> list[list[str]]:
    """R: with n_k <= d only the spherical and diagonal models stay."""
    diagonal = ("EII", "VII", "EEI", "VEI", "EVI", "VVI")
    out = []
    for count in counts:
        names = list(model_names)
        if count <= d:
            names = [m for m in names if m in diagonal]
        out.append(names)
    return out


def MclustDA(*args, **kwargs):
    return mclust_da(*args, **kwargs)


def _split_class_parameters(par: Mapping[str, Any], l: int, d: int, *, one_d: bool) -> dict[str, Any]:
    """R: the class-l slice of an EDDA parameter list (pro = 1, G = 1)."""
    out: dict[str, Any] = {"pro": np.array([1.0], dtype=float), "mean": None, "variance": None}
    mean = np.asarray(par["mean"], dtype=float)
    if one_d:
        out["mean"] = np.array([[mean.reshape(-1)[l]]], dtype=float)
    else:
        out["mean"] = np.asarray(mean.reshape(d, -1, order="F")[:, l : l + 1], dtype=float).copy()
    var = dict(par["variance"])
    var["G"] = 1
    if one_d:
        # R: if (length(sigmasq) > 1) sigmasq <- sigmasq[l]
        if "sigmasq" in var and np.size(var["sigmasq"]) > 1:
            var["sigmasq"] = np.asarray(var["sigmasq"], dtype=float).ravel()[l]
    else:
        if "sigma" in var:
            var["sigma"] = np.asarray(var["sigma"], dtype=float)[:, :, l : l + 1].copy()
        if "sigmasq" in var and np.size(var["sigmasq"]) > 1:
            var["sigmasq"] = np.asarray(var["sigmasq"]).ravel()[l]
        if "scale" in var and np.size(var["scale"]) > 1:
            var["scale"] = np.asarray(var["scale"]).ravel()[l]
        if "shape" in var and np.ndim(var["shape"]) > 1:
            var["shape"] = np.asarray(var["shape"])[:, l]
        for key in ("orientation", "cholSigma", "cholsigma"):
            if key in var and np.ndim(var[key]) > 2:
                var[key] = np.asarray(var[key])[:, :, l : l + 1].copy()
    out["variance"] = var
    return out
