"""tune.randomForest and best.randomForest (e1071 ``tune.randomForest``)."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

import numpy as np

from e1071.tune import tune_control
from e1071.tune_error import with_class_error
from e1071.tune_grid import tune_on_grid


def _randomforest_api():
    """The randomForest package is imported as a module with its own name."""
    import randomForest

    return randomForest


def _fit_forest(rows: Any, labels: Sequence[Any], **args: Any):
    """Grow one forest on the given rows, as randomForest() does in R."""
    return _randomforest_api().random_forest(np.asarray(rows, dtype=float), list(labels), **args)


def predict_forest(model: Any, newdata: Any):
    """Predict with the forest, as predict.randomForest does by default."""
    return _randomforest_api().predict(model, np.asarray(newdata, dtype=float))


def tune_random_forest(
    x: Any,
    y: Sequence[Any] | None = None,
    *,
    nodesize: Sequence[Any] | None = None,
    mtry: Sequence[Any] | None = None,
    ntree: Sequence[Any] | None = None,
    tunecontrol: Mapping[str, Any] | None = None,
    **kwargs: Any,
):
    """Tune randomForest over ``nodesize``, ``mtry``, and ``ntree``. The grid is in R's order."""
    ranges: dict[str, Sequence[Any]] = {}
    for name, value in (("nodesize", nodesize), ("mtry", mtry), ("ntree", ntree)):
        if value is not None:
            ranges[name] = list(value)
    return tune_on_grid(
        _fit_forest,
        x,
        y,
        ranges=ranges or None,
        predict_func=predict_forest,
        tunecontrol=with_class_error(tunecontrol, y),
        **kwargs,
    )


def best_random_forest(
    x: Any,
    y: Sequence[Any] | None = None,
    *,
    tunecontrol: Mapping[str, Any] | None = None,
    **kwargs: Any,
):
    """Return ``tune.randomForest(x, y, ..., tunecontrol)["best.model"]``, with the best model on."""
    ctrl = dict(tune_control() if tunecontrol is None else tunecontrol)
    ctrl["best_model"] = True
    return tune_random_forest(x, y, tunecontrol=ctrl, **kwargs)["best.model"]
