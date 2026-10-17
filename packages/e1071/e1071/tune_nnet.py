"""tune.nnet and best.nnet (e1071 ``tune.nnet``). The fit is nnet's translated network.

The R tuner stops on a factor response, because nnet.default needs a numeric
response. This port does the same. Labels are a numeric 0/1 or a numeric matrix.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

import numpy as np

from e1071.tune import tune_control
from e1071.tune_grid import tune_on_grid


def _nnet_api():
    """The nnet package is imported as a module with its own name."""
    import nnet

    return nnet


def predict_nnet(model: Mapping[str, Any], newdata: Any) -> np.ndarray:
    """Raw network outputs for each new row, as predict.nnet with type raw. A single output is 1-D."""
    from nnet.engine import Net

    weights = np.asarray(model["wts"], dtype=float).reshape(-1)
    engine = Net()
    engine.set_net(
        model["n"],
        model["nconn"],
        model["conn"],
        [0.0] * len(weights),
        model["nsunits"],
        model["entropy"],
        model["softmax"],
        model["censored"],
    )
    values = engine.predict(np.asarray(newdata, dtype=float), weights)
    if values.shape[1] == 1:
        return values[:, 0]
    return values


def _fit_nnet(rows: Any, labels: Any, **args: Any):
    """Fit one network. A numeric response becomes a one-column matrix, as in R."""
    nn = _nnet_api()
    y = np.asarray(labels, dtype=float).reshape(-1, 1)
    return nn.nnet_default(np.asarray(rows, dtype=float), y, **args)


def _check_response(y: Sequence[Any] | None) -> None:
    if y is None:
        raise NotImplementedError("formula interface is not supported")
    if any(isinstance(v, str) for v in y):
        raise ValueError("nnet.default needs a numeric response; a factor is not accepted")


def tune_nnet(
    x: Any,
    y: Sequence[Any] | None = None,
    *,
    size: Sequence[Any] | None = None,
    decay: Sequence[Any] | None = None,
    trace: bool = False,
    tunecontrol: Mapping[str, Any] | None = None,
    **kwargs: Any,
):
    """Tune nnet over ``size`` and ``decay``. The default control has five repeats."""
    _check_response(y)
    ranges: dict[str, Sequence[Any]] = {}
    if size is not None:
        ranges["size"] = list(size)
    if decay is not None:
        ranges["decay"] = list(decay)
    ctrl = dict(tune_control(nrepeat=5) if tunecontrol is None else tunecontrol)
    return tune_on_grid(
        _fit_nnet,
        x,
        y,
        ranges=ranges or None,
        predict_func=predict_nnet,
        tunecontrol=ctrl,
        trace=trace,
        **kwargs,
    )


def best_nnet(
    x: Any,
    y: Sequence[Any] | None = None,
    *,
    tunecontrol: Mapping[str, Any] | None = None,
    **kwargs: Any,
):
    """Return ``tune.nnet(x, ..., tunecontrol)["best.model"]`` with ``best.model`` forced on."""
    ctrl = dict(tune_control(nrepeat=5) if tunecontrol is None else tunecontrol)
    ctrl["best_model"] = True
    return tune_nnet(x, y, tunecontrol=ctrl, **kwargs)["best.model"]
