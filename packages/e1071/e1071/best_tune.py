"""best.tune: the best model that ``tune`` finds (e1071 ``best.tune``)."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from e1071.svm import svm
from e1071.tune_error import with_class_error
from e1071.tune_grid import tune_on_grid
from e1071.tune_svm import _predict_svm_labels


def best_tune(
    method: Any,
    train_x: Any,
    train_y: Sequence[Any] | None = None,
    *,
    data: Mapping[str, Sequence[Any]] | None = None,
    ranges: Mapping[str, Sequence[Any]] | None = None,
    predict_func: Any = None,
    tunecontrol: Mapping[str, Any] | None = None,
    **kwargs: Any,
):
    """Return ``tune(...)["best.model"]``. ``method`` is ``"svm"`` or a fitting function.

    With ``"svm"`` the svm label predictor is the default. A callable method is
    fitted as ``method(rows, labels, **parameters)``, and ``predict_func`` is required.
    """
    if train_y is None and data is not None:
        raise NotImplementedError("formula interface is not supported")
    if isinstance(method, str):
        if method != "svm":
            raise ValueError(f"unknown METHOD {method!r}")
        fit = svm
        if predict_func is None:
            predict_func = _predict_svm_labels
    else:
        fit = method
        if predict_func is None:
            raise ValueError("predict_func is required for a callable method")

    modeltmp = tune_on_grid(
        fit,
        train_x,
        train_y,
        ranges=ranges,
        predict_func=predict_func,
        tunecontrol=with_class_error(tunecontrol, train_y),
        **kwargs,
    )
    return modeltmp["best.model"]
