"""best.svm: the best svm that ``tune.svm`` finds (e1071 ``best.svm``)."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from e1071.svm import svm
from e1071.tune_error import with_class_error
from e1071.tune_grid import tune_on_grid
from e1071.tune_svm import _predict_svm_labels, _range_entry


def best_svm(
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
    """Return ``tune.svm(x, y, ..., tunecontrol)["best.model"]`` with ``best.model`` forced on.

    The matrix interface only, as in ``tune_svm``. The grid uses R's order.
    """
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
            ranges[name] = list(_range_entry(value))
    ctrl = with_class_error(tunecontrol, y)
    ctrl["best_model"] = True

    def fit(rows: Any, labels: Any, **args: Any):
        return svm(rows, labels, **args)

    modeltmp = tune_on_grid(
        fit,
        x,
        y,
        ranges=ranges or None,
        predict_func=_predict_svm_labels,
        tunecontrol=ctrl,
        **kwargs,
    )
    best = modeltmp.get("best.model")
    if best is not None:
        best["call"] = {"function": "best.svm"}
    return best
