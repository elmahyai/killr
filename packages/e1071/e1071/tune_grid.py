"""Grid helper shared by the tune wrappers.

R's ``expand.grid`` varies the first parameter fastest. The translated ``tune``
expands its ranges with the last parameter fastest, so the grid order differs
from R. These helpers build the grid in R's order and give ``tune`` one index
parameter. The index maps back to the parameter values before results return.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from typing import Any

import numpy as np

from e1071.tuning import tune


def r_expand_grid(ranges: Mapping[str, Sequence[Any]]) -> list[dict[str, Any]]:
    """Rows of ``expand.grid(ranges)``: the first name changes fastest."""
    rows: list[dict[str, Any]] = [{}]
    for name, values in ranges.items():
        rows = [{**row, name: value} for value in values for row in rows]
    return rows


def subset_rows(x: Any, y: Sequence[Any] | None, subset: Sequence[int] | None):
    """Rows named by ``subset``, which are 1-based as in R. ``None`` keeps every row."""
    rows = np.asarray(x, dtype=float)
    if y is None:
        labels = None
    else:
        labels = list(y)
    if subset is not None:
        index = [int(i) - 1 for i in subset]
        rows = rows[index]
        if labels is not None:
            labels = [labels[i] for i in index]
    return rows, labels


def tune_on_grid(
    fit: Callable[..., Any],
    x: Any,
    y: Sequence[Any] | None,
    *,
    ranges: Mapping[str, Sequence[Any]] | None,
    predict_func: Callable[..., Any],
    tunecontrol: Mapping[str, Any],
    **kwargs: Any,
) -> dict[str, Any]:
    """Run ``tune`` with the grid in R order.

    ``fit(rows, labels, **pars)`` fits one model on already-subsetted data.
    """
    rows_grid = r_expand_grid(ranges) if ranges else [{}]

    def method(x: Any, y: Any = None, subset: Any = None, index: Any = None, **kw: Any):
        rows, labels = subset_rows(x, y, subset)
        pars = rows_grid[int(index) - 1] if index is not None else {}
        return fit(rows, labels, **pars, **kw)

    index_ranges = {"index": list(range(1, len(rows_grid) + 1))} if ranges else None
    result = tune(
        method,
        x,
        y,
        ranges=index_ranges,
        predict_func=predict_func,
        tunecontrol=tunecontrol,
        **kwargs,
    )
    if ranges:
        best = int(result["best.parameters"]["index"])
        result["best.parameters"] = dict(rows_grid[best - 1])
        if result.get("performances") is not None:
            table = []
            for row in result["performances"]:
                table.append({**rows_grid[int(row["index"]) - 1], "error": row["error"], "dispersion": row["dispersion"]})
            result["performances"] = table
    else:
        result["best.parameters"] = {}
    result["nparcomb"] = len(rows_grid)
    return result
