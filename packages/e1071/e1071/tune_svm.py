"""Hyperparameter search for SVMs (e1071 ``tune.svm`` only)."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

import numpy as np

from e1071.svm import _as_matrix, _predict_svm
from e1071.tuning import tune


def _predict_svm_labels(model: Mapping[str, Any], newdata: Any) -> list[Any]:
    vals, _ = _predict_svm(model, _as_matrix(newdata))
    lev = model.get("levels")
    if lev is not None and int(model["type"]) < 3:
        return [lev[int(v) - 1] for v in np.asarray(vals).reshape(-1)]
    return list(np.asarray(vals).reshape(-1))


def _range_entry(value: Any) -> Sequence[Any]:
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        return [value]
    return value


def tune_svm(
    x: Any,
    y: Sequence[Any] | None = None,
    data: Mapping[str, Sequence[Any]] | None = None,
    *,
    degree: Sequence[Any] | None = None,
    gamma: Sequence[Any] | None = None,
    coef0: Sequence[Any] | None = None,
    cost: Sequence[Any] | None = None,
    nu: Sequence[Any] | None = None,
    class_weights: Sequence[Any] | None = None,
    epsilon: Sequence[Any] | None = None,
    tunecontrol: Mapping[str, Any] | None = None,
    **kwargs: Any,
):
    """Tune ``svm`` hyperparameters via ``tune`` (matrix interface only)."""
    if y is None and data is not None:
        raise NotImplementedError("formula interface is not supported")

    ranges: dict[str, Sequence[Any]] = {}
    for name, value in (
        ("degree", degree),
        ("gamma", gamma),
        ("coef0", coef0),
        ("cost", cost),
        ("nu", nu),
        ("class_weights", class_weights),
        ("epsilon", epsilon),
    ):
        if value is not None:
            ranges[name] = _range_entry(value)

    grid = None if not ranges else ranges

    modeltmp = tune(
        "svm",
        x,
        y,
        data=data,
        ranges=grid,
        predict_func=_predict_svm_labels,
        tunecontrol=tunecontrol,
        **kwargs,
    )

    best = modeltmp.get("best.model")
    if best is not None:
        best["call"] = {"function": "best.svm"}

    return modeltmp
