"""tune.knn: hyperparameter search for class::knn (e1071 ``tune.knn``)."""

from __future__ import annotations

import importlib
from collections.abc import Mapping, Sequence
from typing import Any

import numpy as np

from e1071.tune_error import with_class_error
from e1071.tune_grid import tune_on_grid


def _class_knn():
    """The class package is imported by name, because ``class`` is a Python keyword."""
    return importlib.import_module("class.knn").knn


def _fit_knn(rows: Any, labels: Sequence[Any], k: Any = 1, l: Any = 0, **_: Any):
    """Hold the training rows, labels, and settings, as e1071's knn.wrapper does."""
    return {"train": np.asarray(rows, dtype=float).tolist(), "cl": list(labels), "k": k, "l": l}


def predict_knn_wrapper(model: Mapping[str, Any], newdata: Any):
    """Label the new rows with the stored training set, as the R predict.func does."""
    knn = _class_knn()
    test = np.asarray(newdata, dtype=float).tolist()
    return knn(model["train"], test, model["cl"], k=model["k"], l=model["l"])


def tune_knn(
    x: Any,
    y: Sequence[Any],
    *,
    k: Sequence[Any] | None = None,
    l: Sequence[Any] | None = None,
    tunecontrol: Mapping[str, Any] | None = None,
    **kwargs: Any,
):
    """Tune class::knn over ``k`` and ``l``. The grid is in R's order."""
    ranges: dict[str, Sequence[Any]] = {}
    if k is not None:
        ranges["k"] = list(k)
    if l is not None:
        ranges["l"] = list(l)
    return tune_on_grid(
        _fit_knn,
        x,
        y,
        ranges=ranges or None,
        predict_func=predict_knn_wrapper,
        tunecontrol=with_class_error(tunecontrol, y),
        **kwargs,
    )
