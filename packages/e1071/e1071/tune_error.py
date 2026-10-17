"""Classification error used by the tune wrappers (R tune's 1 - classAgreement).

R's classAgreement intersects the table levels and sums the diagonal. Each
matched pair of labels adds one to that diagonal, so the error is the share of
pairs that differ. The positional diagonal in tuning.py is not used here.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from e1071.tune import tune_control


def class_error(true_y: Sequence[Any], pred: Sequence[Any]) -> float:
    """Return 1 minus the share of rows where the prediction equals the truth."""
    truth = list(true_y)
    guess = list(pred)
    if len(truth) != len(guess):
        raise ValueError("prediction and truth differ in length")
    matches = sum(1 for t, p in zip(truth, guess, strict=True) if t == p)
    return 1.0 - matches / len(truth)


def with_class_error(tunecontrol: Mapping[str, Any] | None, y: Sequence[Any] | None) -> dict[str, Any]:
    """Return the control with ``error_fun`` set when the response is labels.

    A numeric response keeps the default error. The control is always complete.
    """
    ctrl = dict(tune_control() if tunecontrol is None else tunecontrol)
    if ctrl.get("error_fun") is None and y is not None and any(isinstance(v, str) for v in y):
        ctrl["error_fun"] = class_error
    return ctrl
