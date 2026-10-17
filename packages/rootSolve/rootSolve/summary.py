"""``summary.rootSolve``: min, quartiles, mean, max, count, and sample sd."""

import math

import numpy as np


_ROWS = ("Min.", "1st Qu.", "Median", "Mean", "3rd Qu.", "Max.", "N", "sd")


class SummaryFrame:
    """The data frame ``summary.rootSolve`` returns, statistics by variable."""

    def __init__(self, columns):
        self.columns = columns
        self.rows = list(_ROWS)

    def __str__(self):
        names = list(self.columns)
        width = max([6, *(len(str(name)) for name in names)])
        lines = [" " * 8 + " ".join(f"{name:>{width}}" for name in names)]
        for row in self.rows:
            cells = []
            for name in names:
                value = self.columns[name][row]
                if isinstance(value, float) and math.isnan(value):
                    cells.append(f"{'NA':>{width}}")
                elif row == "N":
                    cells.append(f"{int(value):>{width}d}")
                else:
                    cells.append(f"{value:>{width}.7g}")
            lines.append(f"{row:<8}" + " ".join(cells))
        return "\n".join(lines)


def _one(values):
    data = np.asarray(list(values), dtype=float).reshape(-1)
    if data.size == 0:
        nan = float("nan")
        return {
            "Min.": nan, "1st Qu.": nan, "Median": nan, "Mean": nan,
            "3rd Qu.": nan, "Max.": nan, "N": 0, "sd": nan,
        }
    quarts = np.quantile(data, [0.0, 0.25, 0.5, 0.75, 1.0], method="linear")
    deviation = float(np.std(data, ddof=1)) if data.size > 1 else float("nan")
    return {
        "Min.": float(quarts[0]),
        "1st Qu.": float(quarts[1]),
        "Median": float(quarts[2]),
        "Mean": float(np.mean(data)),
        "3rd Qu.": float(quarts[3]),
        "Max.": float(quarts[4]),
        "N": int(data.size),
        "sd": deviation,
    }


def summary_rootsolve(object, **kwargs):
    """Summarise each species, then any extra output on the steady-state list."""
    nspec = object.nspec if object.nspec is not None else 1
    dimens = object.dimens
    if dimens is None:
        dimens = len(object.y) / nspec
    block = int(np.prod(dimens))
    if object.ynames is None:
        varnames = [str(index) for index in range(1, nspec + 1)]
    else:
        varnames = [str(name) for name in object.ynames]
    flat = np.asarray(object.y.values, dtype=float)
    columns = {}
    for index, name in enumerate(varnames):
        piece = flat[index * block:(index + 1) * block]
        columns[name] = _one(piece)
    for name, values in object.extra.items():
        columns[str(name)] = _one(np.ravel(np.asarray(values, dtype=float)))
    return SummaryFrame(columns)
