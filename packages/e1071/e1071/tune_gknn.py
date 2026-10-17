"""tune.gknn and best.gknn: hyperparameter search for gknn (e1071 ``tune.gknn``)."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

import numpy as np

from e1071.gknn import gknn, predict_gknn
from e1071.tune import tune_control
from e1071.tune_error import with_class_error
from e1071.tune_grid import tune_on_grid


def _gknn_method(method: Any):
    """Bind the proxy distance name. tune's own first argument is also named ``method``."""

    def fit(rows: Any, labels: Sequence[Any], k: Any = 1, **kwargs: Any):
        if method is not None:
            kwargs["method"] = method
        return gknn(np.asarray(rows, dtype=float).tolist(), list(labels), k=k, **kwargs)

    return fit


def predict_gknn_wrapper(model: Mapping[str, Any], newdata: Any):
    """Predict the class of each new row, as predict.gknn does by default."""
    return predict_gknn(model, np.asarray(newdata, dtype=float).tolist())


def tune_gknn(
    x: Any,
    y: Sequence[Any] | None = None,
    *,
    k: Sequence[Any] | None = None,
    method: Any = None,
    tunecontrol: Mapping[str, Any] | None = None,
    **kwargs: Any,
):
    """Tune gknn over ``k``. The formula interface is not supported here."""
    ranges = None if k is None else {"k": list(k)}
    return tune_on_grid(
        _gknn_method(method),
        x,
        y,
        ranges=ranges,
        predict_func=predict_gknn_wrapper,
        tunecontrol=with_class_error(tunecontrol, y),
        **kwargs,
    )


def best_gknn(
    x: Any,
    y: Sequence[Any] | None = None,
    *,
    tunecontrol: Mapping[str, Any] | None = None,
    **kwargs: Any,
):
    """Return ``tune.gknn(x, ..., tunecontrol)["best.model"]`` with ``best.model`` forced on."""
    ctrl = dict(tune_control() if tunecontrol is None else tunecontrol)
    ctrl["best_model"] = True
    return tune_gknn(x, y, tunecontrol=ctrl, **kwargs)["best.model"]
