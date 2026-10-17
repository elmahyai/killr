"""cvMclustDA cross-validation for MclustDA classifiers."""

from __future__ import annotations

import warnings
from typing import Any, Mapping, MutableMapping, Sequence

import numpy as np

from mclust._mclust_mutils import as_factor, balanced_folds, brier_score
from mclust.mclust_da import mclust_da
from mclust.predict_mclust_da import predict_mclust_da

__all__ = ["cv_mclust_da", "cvMclustDA"]


def cv_mclust_da(
    fit_object: Mapping[str, Any],
    nfold: int = 10,
    prop: Sequence[float] | Mapping[str, float] | None = None,
    verbose: bool = False,
    **kwargs,
):
    if kwargs.get("metric") is not None:
        warnings.warn("'metric' argument is deprecated! Ignored.", stacklevel=2)
    nfold = int(nfold)
    data = np.asarray(fit_object["data"], dtype=float)
    class_arr = np.asarray(fit_object["class"], dtype=object)
    codes, levels = as_factor(class_arr)
    n = len(codes)
    if prop is None:
        prop = fit_object.get("prop")
    g_list = [mod["G"] for mod in fit_object["models"].values()]
    model_names = [[mod["modelName"]] for mod in fit_object["models"].values()]
    call = dict(fit_object.get("call") or {})
    if nfold == n:
        folds = [np.array([i + 1], dtype=int) for i in range(n)]
    else:
        folds = balanced_folds(class_arr, nfolds=nfold)
    nfold = len(folds)
    folds_size = np.array([len(f) for f in folds], dtype=float)
    metric_cv = np.full((nfold, 2), np.nan, dtype=float)
    class_cv = np.empty(n, dtype=object)
    prob_cv = np.full((n, len(levels)), np.nan, dtype=float)
    for i, fold in enumerate(folds):
        keep = np.ones(n, dtype=bool)
        keep[fold - 1] = False
        x = data[keep]
        y = class_arr[keep]
        fit_kwargs = {
            "data": x,
            "class_": y,
            "G": g_list,
            "model_names": model_names[0] if fit_object["type"] == "EDDA" else model_names,
            "model_type": fit_object["type"],
            "verbose": False,
        }
        for key in ("prior", "control", "initialization", "warn"):
            if key in call:
                fit_kwargs[key] = call[key]
        mod = mclust_da(**fit_kwargs)
        while mod is None or isinstance(mod, Exception):
            g_list = [[max(1, g - 1) for g in gl] for gl in g_list]
            fit_kwargs["G"] = g_list
            try:
                mod = mclust_da(**fit_kwargs)
            except NotImplementedError:
                raise
        pred_test = predict_mclust_da(mod, newdata=data[fold - 1], prop=prop)
        metric_cv[i, 0] = _classification_error(
            pred_test["classification"], class_arr[fold - 1]
        )
        metric_cv[i, 1] = brier_score(pred_test["z"], class_arr[fold - 1], levels)
        class_cv[fold - 1] = pred_test["classification"]
        prob_cv[fold - 1, :] = pred_test["z"]
    cv = np.array(
        [
            np.sum(metric_cv[:, m] * folds_size) / np.sum(folds_size)
            for m in range(2)
        ],
        dtype=float,
    )
    se = np.array(
        [
            np.sqrt(
                (np.sum((metric_cv[:, m] - cv[m]) ** 2 * folds_size))
                / (np.sum(folds_size) * (nfold - 1) / nfold)
                / nfold
            )
            for m in range(2)
        ],
        dtype=float,
    )
    return {
        "classification": class_cv,
        "z": prob_cv,
        "ce": float(cv[0]),
        "se.ce": float(se[0]),
        "brier": float(cv[1]),
        "se.brier": float(se[1]),
    }


def cvMclustDA(*args, **kwargs):
    return cv_mclust_da(*args, **kwargs)


def _classification_error(pred, truth) -> float:
    pred = np.asarray(pred, dtype=object)
    truth = np.asarray(truth, dtype=object)
    return 1.0 - np.sum(pred == truth) / len(truth)
