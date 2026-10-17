"""Semi-supervised classification (MclustSSC)."""

from __future__ import annotations

import warnings
from typing import Sequence

import numpy as np

from mclust._mclust_em_for_ssc import em_cdens, em_dens, em_estep, em_mstep, map_z
from mclust._mclust_mutils import n_var_params
from mclust.em_control import em_control
from mclust.mclust_options import mclust_options

__all__ = ["mclust_ssc", "MclustSSC"]

_EM_MODELS_REMOVE_HIGH_D = ("EEE", "EEV", "VEV", "VVV")


def mclust_ssc(
    data,
    class_,
    *,
    G=None,
    model_names=None,
    prior=None,
    control=None,
    warn=None,
    verbose: bool = False,
    **kwargs,
):
    data = np.asarray(data, dtype=float)
    if data.ndim == 1:
        data = data.reshape(-1, 1)
    mask = ~np.any(np.isnan(data), axis=1)
    data = data[mask]
    n, d = data.shape
    class_arr = np.asarray(class_, dtype=object)[mask]
    na_mask = np.array(
        [
            v is None
            or (isinstance(v, float) and np.isnan(v))
            or (isinstance(v, str) and v == "NA")
            for v in class_arr
        ]
    )
    if not np.any(na_mask):
        warnings.warn(
            "No obs with unknown class encoded as NA. Reverting to MclustDA() ...",
            stacklevel=2,
        )
        from mclust.mclust_da import mclust_da

        return mclust_da(
            data,
            class_arr,
            G=G,
            model_names=model_names,
            prior=prior,
            control=control,
            warn=warn,
            verbose=verbose,
            **kwargs,
        )
    class_levels = _class_levels(class_arr)
    nclass = len(class_levels)
    one_d = d == 1
    if G is None:
        g_val = nclass
    else:
        g_seq = np.atleast_1d(np.asarray(G, dtype=int))
        if np.any(g_seq < nclass):
            raise ValueError("G cannot be smaller than the number of classes")
        g_val = int(g_seq[g_seq >= nclass][0])
    if model_names is None:
        model_names = list(mclust_options("emModelNames")) if not one_d else ["E", "V"]
    if isinstance(model_names, str):
        model_names = [model_names]
    model_name_list = list(model_names)
    if n <= d:
        em_names = list(mclust_options("emModelNames"))
        drop = [m for m in _EM_MODELS_REMOVE_HIGH_D if m in em_names]
        model_name_list = [m for m in model_name_list if m not in drop]
    if control is None:
        control = em_control()
    if warn is None:
        warn = mclust_options("warn")
    fit_args = {"data": data, "class_": class_arr, "G": g_val, **kwargs}
    model = None
    bic_vec = np.full(len(model_name_list), np.nan, dtype=float)
    for m_idx, model_name in enumerate(model_name_list):
        try:
            mod = mclust_ssc_fit(
                data,
                class_arr,
                G=g_val,
                model_name=model_name,
                prior=prior,
                control=control,
                warn=warn,
                **kwargs,
            )
        except Exception:
            continue
        bic_vec[m_idx] = mod["bic"]
        if not np.isnan(bic_vec[m_idx]) and bic_vec[m_idx] >= np.nanmax(bic_vec):
            model = mod
    if np.all(np.isnan(bic_vec)):
        warnings.warn("No model(s) can be estimated!!", stacklevel=2)
        return None
    bic_mat = bic_vec.reshape(1, -1)
    out = {
        "call": {"data": data, "class": class_arr, "G": g_val, "model_names": model_name_list, "prior": prior, "control": control, "warn": warn},
        "data": data,
        "class": class_arr,
        "BIC": bic_mat,
        "control": control,
    }
    if model is not None:
        out.update(model)
    ordered = [
        "call",
        "data",
        "class",
        "modelName",
        "G",
        "n",
        "d",
        "BIC",
        "loglik",
        "df",
        "bic",
        "parameters",
        "z",
        "classification",
        "prior",
        "control",
    ]
    return {k: out[k] for k in ordered if k in out}


def mclust_ssc_fit(
    data: np.ndarray,
    class_,
    *,
    G: int | None = None,
    model_name: str,
    prior=None,
    control=None,
    warn=None,
    _verbose: bool = False,
    **kwargs,
):
    data = np.asarray(data, dtype=float)
    if data.ndim == 1:
        data = data.reshape(-1, 1)
    n, d = data.shape
    class_arr = np.asarray(class_, dtype=object)
    class_levels = _class_levels(class_arr)
    class_codes = np.empty(n, dtype=object)
    for i, v in enumerate(class_arr):
        if v is None or (isinstance(v, float) and np.isnan(v)):
            class_codes[i] = np.nan
        else:
            class_codes[i] = str(v)
    nclass = len(class_levels)
    known = np.array([not (c is np.nan or (isinstance(c, float) and np.isnan(c))) for c in class_codes])
    unknown = ~known
    if G is None:
        G = nclass
    g = int(G)
    z = np.zeros((n, g), dtype=float)
    for k, lab in enumerate(class_levels):
        z[class_codes == lab, k] = 1.0
    z0 = z[known, :].copy()
    if g > nclass:
        km = _kmeans_init(data[unknown, :], centers=g, nstart=25, iter_max=100)
        sizes = np.array(km["size"], dtype=float)
        z[unknown, :] = (sizes / sizes.sum())[None, :]
    else:
        z[unknown, :] = 1.0 / g
    if control is None:
        control = em_control()
    if warn is None:
        warn = False
    loglik0 = -np.inf
    criterion = True
    iter_count = 0
    itmax = control["itmax"][0] if isinstance(control["itmax"], (list, tuple)) else control["itmax"]
    tol = control["tol"][0] if isinstance(control["tol"], (list, tuple)) else control["tol"]
    fit_m = None
    while criterion:
        iter_count += 1
        fit_m = em_mstep(data, z, model_name=model_name, prior=prior, control=control, warn=warn)
        fit_e = em_estep(data, fit_m, control=control, warn=warn)
        z = np.asarray(fit_e["z"], dtype=float)
        z[known, :] = z0
        ldens = em_dens(data[unknown, :], fit_m, logarithm=True, warn=warn)
        lcdens = em_cdens(data[known, :], fit_m, logarithm=True, warn=warn)
        pro = np.asarray(fit_m["parameters"]["pro"], dtype=float)
        log_pro = np.log(pro)
        lcdens = lcdens + log_pro.reshape(1, -1)
        loglik = float(np.sum(ldens) + np.sum(lcdens * z0))
        criterion = iter_count < itmax and (loglik - loglik0) > tol
        loglik0 = loglik
    assert fit_m is not None
    fit_m["loglik"] = loglik
    _align_components_to_class_levels(fit_m, class_levels, class_codes, known)
    cl_idx = map_z(fit_m["z"], warn=False)
    labels = list(class_levels)
    if g > nclass:
        labels.extend([f"class{i}" for i in range(nclass + 1, g + 1)])
    classification = np.array([labels[i - 1] for i in cl_idx], dtype=object)
    fit_m["classification"] = classification
    fit_m["df"] = (g - 1) + d * nclass + n_var_params(fit_m["modelName"], d, nclass)
    fit_m["bic"] = 2.0 * loglik - fit_m["df"] * np.log(n)
    return fit_m


def _class_levels(class_arr: np.ndarray) -> list[str]:
    labels: set[str] = set()
    for v in class_arr:
        if v is None or (isinstance(v, float) and np.isnan(v)):
            continue
        labels.add(str(v))

    def _sort_key(text: str):
        try:
            return (0, float(text))
        except ValueError:
            return (1, text)

    return sorted(labels, key=_sort_key)


def _align_components_to_class_levels(
    fit_m: dict,
    class_levels: Sequence[str],
    class_codes: np.ndarray,
    known: np.ndarray,
) -> None:
    z = np.asarray(fit_m["z"], dtype=float)
    g = z.shape[1]
    perm = []
    used: set[int] = set()
    for lab in class_levels:
        mask = known & (class_codes == lab)
        if not np.any(mask):
            continue
        scores = [float(z[mask, j].sum()) for j in range(g)]
        j_best = max(range(g), key=lambda j: scores[j] if j not in used else -1.0)
        used.add(j_best)
        perm.append(j_best)
    for j in range(g):
        if j not in used:
            perm.append(j)
    if perm == list(range(g)):
        return
    fit_m["z"] = z[:, perm]
    pro = np.asarray(fit_m["parameters"]["pro"], dtype=float)[perm]
    fit_m["parameters"]["pro"] = pro
    fit_m["parameters"]["mean"] = np.asarray(fit_m["parameters"]["mean"], dtype=float)[:, perm]
    var = fit_m["parameters"]["variance"]
    if "sigmasq" in var and np.ndim(var["sigmasq"]) > 0 and len(var["sigmasq"]) == g:
        var["sigmasq"] = np.asarray(var["sigmasq"], dtype=float)[perm]
    if "scale" in var and np.ndim(var["scale"]) > 0 and len(np.atleast_1d(var["scale"])) == g:
        var["scale"] = np.asarray(var["scale"], dtype=float)[perm]
    if "shape" in var and np.ndim(var["shape"]) > 1 and var["shape"].shape[1] == g:
        var["shape"] = np.asarray(var["shape"], dtype=float)[:, perm]
    if "sigma" in var and np.ndim(var["sigma"]) == 3 and var["sigma"].shape[2] == g:
        var["sigma"] = var["sigma"][:, :, perm]


def _kmeans_init(data: np.ndarray, *, centers: int, nstart: int, iter_max: int):
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "e1071"))
    from e1071._kmns import kmeans_hartigan_wong

    x = data.tolist()
    return kmeans_hartigan_wong(x, centers, iter_max=iter_max, nstart=nstart)


def MclustSSC(*args, **kwargs):
    return mclust_ssc(*args, **kwargs)
