"""Summary method for ``MclustDA`` objects."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import numpy as np

from .brier_score import BrierScore
from .get_parameters_mclust_da import getParameters_MclustDA
from .predict_mclust_da import predict_mclust_da

__all__ = ["summary_mclust_da"]


def _get(obj: Any, key: str, default: Any = None) -> Any:
    if isinstance(obj, Mapping):
        return obj.get(key, default)
    return getattr(obj, key, default)


def summary_mclust_da(
    object: Mapping[str, Any],
    parameters: bool = False,
    newdata: Any = None,
    newclass: Any = None,
    **kwargs: Any,
) -> dict[str, Any]:
    """Build the data returned by R's ``summary.MclustDA`` method.

    ``newdata`` and ``newclass`` are treated as supplied only when both are
    non-``None``, matching the R method's ``missing`` checks.
    """
    models = _get(object, "models")
    model_items = list(models.items()) if isinstance(models, Mapping) else list(enumerate(models))
    n = np.asarray([_get(model, "n") for _, model in model_items], dtype=int)
    groups = np.asarray([_get(model, "G") for _, model in model_items], dtype=int)
    model_names = [str(_get(model, "modelName")) for _, model in model_items]
    classes = [str(name) for name, _ in model_items]

    par = getParameters_MclustDA(object)
    class_values = _get(object, "class")
    data = _get(object, "data")
    pred = predict_mclust_da(object, newdata=data, **kwargs)
    classification = np.asarray(pred["classification"], dtype=str)
    class_array = np.asarray(class_values, dtype=str).ravel()
    ce = float(np.mean(class_array != classification))
    brier = BrierScore(pred["z"], class_values)

    tab = _confusion(class_array, classification, classes)
    tab_newdata = ce_newdata = brier_newdata = None
    if newdata is not None and newclass is not None:
        pred_new = predict_mclust_da(object, newdata=newdata, **kwargs)
        predicted_new = np.asarray(pred_new["classification"], dtype=str)
        newclass_array = np.asarray(newclass, dtype=str).ravel()
        tab_newdata = _confusion(newclass_array, predicted_new, classes)
        ce_newdata = float(np.mean(newclass_array != predicted_new))
        brier_newdata = BrierScore(pred_new["z"], newclass)

    return {
        "type": _get(object, "type"),
        "n": n,
        "d": _get(object, "d"),
        "loglik": _get(object, "loglik"),
        "df": _get(object, "df"),
        "bic": _get(object, "bic"),
        "nclass": len(model_items),
        "classes": classes,
        "G": groups,
        "modelName": model_names,
        "prop": _get(object, "prop"),
        "parameters": par,
        "prior": _get(object, "prior"),
        "tab": tab,
        "ce": ce,
        "brier": brier,
        "tab.newdata": tab_newdata,
        "ce.newdata": ce_newdata,
        "brier.newdata": brier_newdata,
        "printParameters": bool(parameters),
    }


def _confusion(actual: np.ndarray, predicted: np.ndarray, classes: list[str]) -> dict[str, Any]:
    """Represent R's table(class, prediction) with explicit zero cells."""
    levels = list(classes)
    counts = np.zeros((len(levels), len(levels)), dtype=int)
    lookup = {value: i for i, value in enumerate(levels)}
    for observed, fitted in zip(actual, predicted):
        if observed in lookup and fitted in lookup:
            counts[lookup[observed], lookup[fitted]] += 1
    return {
        "values": counts,
        "dimnames": {"Classes": levels, "Predicted": levels},
    }
