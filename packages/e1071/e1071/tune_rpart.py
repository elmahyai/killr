"""tune.rpart and best.rpart (e1071 ``tune.rpart``). The tree is rpart's anova tree.

The R tuner fits by formula on a data frame. Here the data is a dict of columns,
and the formula is a string such as ``"y ~ x1 + x2"``. The tuner passes the row
numbers as its matrix, so each fit selects the rows that tune asks for.

Only numeric responses are supported, because the translated rpart grows
anova trees. A row with a missing predictor is not supported when predicting.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from typing import Any

import numpy as np

from e1071.tune import tune_control
from e1071.tune_grid import tune_on_grid


def _rpart_api():
    """The rpart package is imported as a module with its own name."""
    import rpart

    return rpart


# Defaults of e1071's rpart.wrapper, in its argument order.
_WRAPPER_DEFAULTS = {
    "minsplit": 20,
    "cp": 0.01,
    "maxcompete": 4,
    "maxsurrogate": 5,
    "usesurrogate": 2,
    "xval": 10,
    "surrogatestyle": 0,
    "maxdepth": 30,
}
_RANGE_ORDER = ("minsplit", "minbucket", "cp", "maxcompete", "maxsurrogate", "usesurrogate", "xval",
                "surrogatestyle", "maxdepth")


def _response_name(formula: str) -> str:
    return formula.split("~", 1)[0].strip()


def _control_from(pars: Mapping[str, Any]) -> dict[str, Any]:
    """rpart.wrapper's defaults, with minbucket = round(minsplit / 3) when not given."""
    values = dict(_WRAPPER_DEFAULTS)
    values.update({k: v for k, v in pars.items() if k in values})
    minsplit = values["minsplit"]
    values["minbucket"] = pars.get("minbucket", round(minsplit / 3))
    return values


def _fit_rpart(data: Mapping[str, Sequence[Any]], formula: str):
    def fit(rows: Any, labels: Any, **pars: Any):
        ids = [int(r) for r in np.asarray(rows)[:, 0]]
        sub = {name: [values[i - 1] for i in ids] for name, values in data.items()}
        control = _control_from(pars)
        rp = _rpart_api()
        return rp.rpart(formula, sub, control=control)

    return fit


def predict_tree(fit: Any, newdata_rows: Sequence[Sequence[float]]) -> list[float]:
    """Leaf means for new rows. Rows follow the order of ``fit.var_names``.

    The frame is in pre-order. Each non-leaf node uses its primary split, then its
    competitors are skipped, and its surrogates follow in the split table.
    """
    frame = fit.frame
    by_id = {node["id"]: node for node in frame}
    primary: dict[int, dict[str, Any]] = {}
    cursor = 0
    for node in frame:
        if node["var"] == "<leaf>":
            continue
        primary[node["id"]] = fit.splits[cursor]
        cursor += node["ncompete"] + 1 + node["nsurrogate"]
    names = list(fit.var_names)
    out: list[float] = []
    for row in newdata_rows:
        node_id = 1
        while by_id[node_id]["var"] != "<leaf>":
            split = primary[node_id]
            value = float(row[names.index(split["var"])])
            if math.isnan(value):
                raise NotImplementedError("surrogate splits for missing values are not in this port")
            node_id = 2 * node_id if value < split["index"] else 2 * node_id + 1
        out.append(float(by_id[node_id]["yval"]))
    return out


def _predict_rows(data: Mapping[str, Sequence[Any]], names: Sequence[str]):
    def predict(model: Any, newdata: Any) -> list[float]:
        ids = [int(r) for r in np.asarray(newdata)[:, 0]]
        rows = [[data[name][i - 1] for name in names] for i in ids]
        return predict_tree(model, rows)

    return predict


def tune_rpart(
    formula: str,
    data: Mapping[str, Sequence[Any]],
    *,
    minsplit: Sequence[Any] | None = None,
    minbucket: Sequence[Any] | None = None,
    cp: Sequence[Any] | None = None,
    maxcompete: Sequence[Any] | None = None,
    maxsurrogate: Sequence[Any] | None = None,
    usesurrogate: Sequence[Any] | None = None,
    xval: Sequence[Any] | None = None,
    surrogatestyle: Sequence[Any] | None = None,
    maxdepth: Sequence[Any] | None = None,
    tunecontrol: Mapping[str, Any] | None = None,
    **kwargs: Any,
):
    """Tune rpart over the control numbers that are given as ranges. The grid is in R's order."""
    given = {
        "minsplit": minsplit,
        "minbucket": minbucket,
        "cp": cp,
        "maxcompete": maxcompete,
        "maxsurrogate": maxsurrogate,
        "usesurrogate": usesurrogate,
        "xval": xval,
        "surrogatestyle": surrogatestyle,
        "maxdepth": maxdepth,
    }
    ranges = {name: list(given[name]) for name in _RANGE_ORDER if given[name] is not None}
    names = list(data.keys())
    response = _response_name(formula)
    if response not in data:
        raise ValueError(f"response {response!r} is not a column of data")
    y = [float(v) for v in data[response]]
    n = len(y)
    index = np.arange(1, n + 1, dtype=float).reshape(-1, 1)
    predictors = [name for name in names if name != response]
    ctrl = dict(tune_control() if tunecontrol is None else tunecontrol)
    return tune_on_grid(
        _fit_rpart(data, formula),
        index,
        y,
        ranges=ranges or None,
        predict_func=_predict_rows(data, predictors),
        tunecontrol=ctrl,
        **kwargs,
    )


def best_rpart(
    formula: str,
    data: Mapping[str, Sequence[Any]],
    *,
    tunecontrol: Mapping[str, Any] | None = None,
    **kwargs: Any,
):
    """Return ``tune.rpart(formula, data, ..., tunecontrol)["best.model"]`` with ``best.model`` forced on."""
    ctrl = dict(tune_control() if tunecontrol is None else tunecontrol)
    ctrl["best_model"] = True
    return tune_rpart(formula, data, tunecontrol=ctrl, **kwargs)["best.model"]
