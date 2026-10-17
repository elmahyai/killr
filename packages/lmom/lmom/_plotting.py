"""Helpers shared by the lmom drawing functions (lmrd, lmrdpoints, evplot, evpoints).

These reproduce the small R rules the drawing code depends on: ``make.words``,
``pmatch``, the 4 percent extension R applies to the plot region (``xaxs = "r"``),
``ppoints`` and the point symbols. Drawing itself uses Matplotlib.
"""

from __future__ import annotations

from collections.abc import Mapping

import numpy as np

# R point symbol (pch) to (Matplotlib marker, filled).
_PCH_TO_MARKER = {
    0: ("s", False),
    1: ("o", False),
    2: ("^", False),
    3: ("+", False),
    4: ("x", False),
    5: ("D", False),
    15: ("s", True),
    16: ("o", True),
    17: ("^", True),
}
_MARKER_TO_PCH = {v: k for k, v in _PCH_TO_MARKER.items()}

# R line type (lty) to Matplotlib linestyle, for the two types used here.
LTY_TO_LINESTYLE = {"solid": "-", "longdash": "--", "1": "-", "2": "--"}
LINESTYLE_TO_LTY = {"-": "solid", "--": "longdash"}

def make_words(value) -> list[str]:
    """R's ``make.words``: split on single spaces and drop empty pieces."""
    if isinstance(value, str):
        pieces = [value]
    elif isinstance(value, bool):
        pieces = ["TRUE" if value else "FALSE"]
    else:
        pieces = [str(v) if not isinstance(v, bool) else ("TRUE" if v else "FALSE")
                  for v in value]
    words: list[str] = []
    for piece in pieces:
        words.extend(w for w in piece.split(" ") if w != "")
    return words


def unique_in_order(items) -> list:
    seen = set()
    out = []
    for item in items:
        if item not in seen:
            seen.add(item)
            out.append(item)
    return out


def pmatch(items, table) -> list[int | None]:
    """R's ``pmatch``: exact match, else a unique partial match. 1-based; None is NA."""
    out: list[int | None] = []
    for item in items:
        if item in table:
            out.append(table.index(item) + 1)
            continue
        hits = [i for i, t in enumerate(table) if item != "" and t.startswith(item)]
        out.append(hits[0] + 1 if len(hits) == 1 else None)
    return out


def as_logical_false(value) -> bool:
    """True when R's ``identical(as.logical(value), FALSE)`` holds."""
    if isinstance(value, bool):
        return value is False
    if isinstance(value, str):
        return value in ("F", "FALSE", "false", "False")
    return False


def extend_range(lo: float, hi: float) -> tuple[float, float]:
    """The plot-region limits R uses for a requested range (``xaxs = "r"``).

    R adds 4 percent of the range to each side. A zero-width range is widened
    the way R's GScale widens it.
    """
    if lo == hi:
        if lo == 0:
            return -1.0, 1.0
        temp = 0.4 * abs(lo)
        return lo - temp, hi + temp
    d = hi - lo
    return lo - 0.04 * d, hi + 0.04 * d


def ppoints(n: int, a: float) -> np.ndarray:
    """R's ``ppoints(n, a)``: (1:n - a) / (n + 1 - 2a)."""
    if n <= 0:
        return np.empty(0)
    return (np.arange(1, n + 1, dtype=float) - a) / (n + 1 - 2 * a)


def r_number_string(value: float) -> str:
    """R's ``as.character`` for a whole number: fixed or scientific, whichever is shorter."""
    value = float(value)
    if not value.is_integer():
        return repr(value)
    fixed = str(int(value))
    mantissa, exponent = f"{value:e}".split("e")
    mantissa = mantissa.rstrip("0").rstrip(".")
    sci = f"{mantissa}e{int(exponent):+03d}"
    return sci if len(sci) < len(fixed) else fixed


def point_input(x, y=None, *, allow_missing_x: bool = False):
    """Read the L-skewness and L-kurtosis pair from the arguments, as lmrdpoints does.

    ``y`` given: use ``x`` and ``y`` as the two coordinates.
    ``y`` absent: ``x`` must be a mapping with names ``t_3``/``t_4`` or
    ``tau_3``/``tau_4`` (R's named vector). Anything else is an error,
    as in R. A 2-d array has no names, so it is an error here too.
    """
    if y is not None:
        return np.asarray(x, dtype=float).ravel(), np.asarray(y, dtype=float).ravel()
    if isinstance(x, Mapping):
        for first, second in (("t_3", "t_4"), ("tau_3", "tau_4")):
            if first in x and second in x:
                return (np.asarray([x[first]], dtype=float),
                        np.asarray([x[second]], dtype=float))
    raise ValueError("could not find L-skewness and L-kurtosis values in 'x'")


def pin_ratio(ax) -> float:
    """R's ``par("pin")[1] / par("pin")[2]`` for the Matplotlib axes."""
    return float(ax.bbox.width / ax.bbox.height)


def current_axes(ax=None):
    """The axes R would draw on: ``ax`` if given, else the current axes."""
    if ax is not None:
        return ax
    import matplotlib.pyplot as plt

    return plt.gca()


def draw_points(ax, x, y, type_: str = "p", pch: int = 1, col="black", label="points", **kwargs):
    """R's ``points(x, y, type, pch, col)`` on a Matplotlib axes."""
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    if type_ == "n":
        return []
    if type_ not in ("p", "l", "b", "o"):
        raise NotImplementedError(f"point type {type_!r} is not translated")
    marker, filled = _PCH_TO_MARKER[int(pch)]
    if type_ == "p":
        return ax.plot(x, y, linestyle="none", marker=marker, color=col,
                       markerfacecolor=col if filled else "none", label=label, **kwargs)
    if type_ == "l":
        return ax.plot(x, y, linestyle="-", color=col, label=label, **kwargs)
    return ax.plot(x, y, linestyle="-", marker=marker, color=col,
                   markerfacecolor=col if filled else "none", label=label, **kwargs)


def recycle(values, n: int) -> list:
    """R's ``rep_len(values, n)`` for a list."""
    values = list(values)
    if n == 0:
        return []
    return [values[i % len(values)] for i in range(n)]


def finite_range(values, *extra) -> tuple[float, float]:
    """R's ``range(extra..., values, na.rm = TRUE)``."""
    pieces = [np.asarray(v, dtype=float).ravel() for v in (*extra, values)]
    flat = np.concatenate(pieces) if pieces else np.empty(0)
    flat = flat[~np.isnan(flat)]
    return float(flat.min()), float(flat.max())


def sorted_non_missing(y) -> np.ndarray:
    arr = np.asarray(y, dtype=float).ravel()
    return np.sort(arr[~np.isnan(arr)])
