"""Plot growth curves colored by group.

Translated from statmod 1.5.2 ``plotGrowthCurves`` in ``R/growthcurve.R``.
"""

from __future__ import annotations

import math
import warnings

import numpy as np

from statmod.compare_growth_curves import (
    _as_character_double,
    _as_matrix,
    _flatten,
    _one_label,
    _r_sort,
    _select_times,
)

# R 4.0+ default palette(), eight colors, recycled by positive index.
_PALETTE = (
    (0, 0, 0),
    (223, 83, 107),
    (97, 208, 79),
    (34, 151, 230),
    (40, 226, 229),
    (205, 11, 188),
    (245, 199, 16),
    (158, 158, 158),
)


def plotGrowthCurves(group, y, levels=None, times=None, col=None, **kwargs):
    """Draw one line per individual, colored by group, with a group legend.

    ``levels`` defaults to the sorted unique labels. Numeric ids are sorted
    as numbers and then converted to character, which is R's default-argument
    order. ``times`` uses 1-based column numbers. The return value holds the
    axis limits in ``par("usr")`` form, the legend anchor, and the line colors.
    """
    raw = _flatten(group)
    labels = [_one_label(value) for value in raw]
    if levels is None:
        lev = _default_levels(raw)
    else:
        lev = [_one_label(value) for value in _flatten(levels)]
    nlev = len(lev)
    if nlev < 2:
        raise ValueError("Less than 2 groups to compare")
    matrix = _as_matrix(y)
    if times is not None:
        matrix = _select_times(matrix, times)
    nrow, ncol = matrix.shape
    if col is None:
        colors = list(range(1, nlev + 1))
    else:
        colors = _color_list(col)
    matched = _match(labels, lev)
    line_specs = [_take(colors, index) for index in matched]
    line_rgb = np.full((nrow, 3), np.nan, dtype=float)
    for i, spec in enumerate(line_specs):
        if spec is None:
            continue
        line_rgb[i, :] = _color_rgb(spec)
    legend_specs = _recycle(colors, nlev)
    legend_rgb = np.array([_color_rgb(spec) for spec in legend_specs], dtype=float)

    xlab = kwargs.pop("xlab", "Time")
    ylab = kwargs.pop("ylab", "Response")
    main = kwargs.pop("main", None)
    log = kwargs.pop("log", "")
    xaxs = kwargs.pop("xaxs", "r")
    yaxs = kwargs.pop("yaxs", "r")
    xlim = kwargs.pop("xlim", None)
    ylim = kwargs.pop("ylim", None)
    if kwargs:
        unknown = ", ".join(repr(name) for name in kwargs)
        raise TypeError(f"unused arguments {unknown}")
    log_x = "x" in str(log)
    log_y = "y" in str(log)

    if xlim is None:
        x_min, x_max = 1.0, float(ncol)
    else:
        x_min, x_max = (float(v) for v in np.asarray(xlim, dtype=float).reshape(-1)[:2])
    if ylim is None:
        finite_y = matrix[np.isfinite(matrix)]
        if finite_y.size == 0:
            raise ValueError("need finite 'ylim' values")
        y_min = float(np.min(finite_y))
        y_max = float(np.max(finite_y))
    else:
        y_min, y_max = (float(v) for v in np.asarray(ylim, dtype=float).reshape(-1)[:2])
    if not math.isfinite(x_min) or not math.isfinite(x_max):
        raise ValueError("need finite 'xlim' values")
    if not math.isfinite(y_min) or not math.isfinite(y_max):
        raise ValueError("need finite 'ylim' values")

    usr_x = _usr_pair(_log_limit(x_min, log_x, "x"), _log_limit(x_max, log_x, "x"), xaxs)
    usr_y = _usr_pair(_log_limit(y_min, log_y, "y"), _log_limit(y_max, log_y, "y"), yaxs)
    data_range = matrix[np.isfinite(matrix)]
    if data_range.size == 0:
        legend_y = float("nan")
    else:
        high = float(np.max(data_range))
        low = float(np.min(data_range))
        legend_y = high - (high - low) / 40.0
    legend_x = 1.0

    import matplotlib

    matplotlib.use("Agg", force=False)
    import matplotlib.pyplot as plt
    from matplotlib.lines import Line2D

    figure, ax = plt.subplots(figsize=(7, 7))
    if log_x:
        ax.set_xscale("log")
    if log_y:
        ax.set_yscale("log")
    ax.set_xlim(_mpl_limit(usr_x, log_x))
    ax.set_ylim(_mpl_limit(usr_y, log_y))
    ax.set_xlabel(xlab)
    ax.set_ylabel(ylab)
    if main is not None:
        ax.set_title(str(main))
    x = np.arange(1, ncol + 1, dtype=float)
    for i in range(nrow):
        if not np.all(np.isfinite(line_rgb[i])):
            continue
        ax.plot(x, matrix[i], color=_hex(line_rgb[i]), linestyle="solid")
    handles = [
        Line2D([0], [0], color=_hex(rgb), linestyle="solid")
        for rgb in legend_rgb
    ]
    anchor_y = legend_y
    ax.legend(
        handles,
        ["" if level is None else str(level) for level in lev],
        loc="upper left",
        bbox_to_anchor=(legend_x, anchor_y),
        bbox_transform=ax.transData,
        frameon=True,
    )
    return {
        "usr": np.array([usr_x[0], usr_x[1], usr_y[0], usr_y[1]], dtype=float),
        "legend_x": legend_x,
        "legend_y": legend_y,
        "y": matrix,
        "line_rgb": line_rgb,
        "legend_rgb": legend_rgb,
        "figure": figure,
    }


def _is_real(value):
    if isinstance(value, (bool, np.bool_)):
        return False
    return isinstance(value, (int, np.integer, float, np.floating))


def _default_levels(raw):
    """``sort(unique(group))`` on the original group, then ``as.character``.

    Numeric ids sort as numbers, so 2 comes before 10. Character ids sort in
    the session collation. Missing ids are dropped, as R's ``sort`` does.
    """
    if raw and all(_is_real(value) or _one_label(value) is None for value in raw):
        finite = [float(value) for value in raw if _is_real(value) and math.isfinite(float(value))]
        unique = np.unique(np.asarray(finite, dtype=float))
        return [_as_character_double(float(value)) for value in unique]
    present = []
    seen = set()
    for value in raw:
        label = _one_label(value)
        if label is None or label in seen:
            continue
        seen.add(label)
        present.append(label)
    return _r_sort(present)


def _color_list(col):
    if isinstance(col, (str, bytes)):
        return [col]
    if isinstance(col, (int, np.integer, float, np.floating)) and np.ndim(col) == 0:
        return [col]
    return list(_flatten(col))


def _match(labels, levels):
    index = {}
    for position, level in enumerate(levels, start=1):
        if level not in index:
            index[level] = position
    return [index.get(label) for label in labels]


def _take(colors, index):
    """R ``col[i]`` without recycling. Out of range is missing."""
    if index is None:
        return None
    if index < 1 or index > len(colors):
        return None
    return colors[index - 1]


def _recycle(colors, n):
    if n == 0:
        return []
    if len(colors) == 0:
        return [None] * n
    return [colors[i % len(colors)] for i in range(n)]


def _color_rgb(spec):
    """RGB 0-255 for an R color number or name."""
    if spec is None:
        return (np.nan, np.nan, np.nan)
    if isinstance(spec, (bool, np.bool_)):
        raise ValueError("invalid color")
    if isinstance(spec, (int, np.integer)) or (
        isinstance(spec, (float, np.floating)) and float(spec).is_integer()
    ):
        number = int(spec)
        if number <= 0:
            raise ValueError("numerical color values must be positive")
        return _PALETTE[(number - 1) % len(_PALETTE)]
    text = spec.decode() if isinstance(spec, (bytes, np.bytes_)) else str(spec)
    if text.startswith("#"):
        return _hex_rgb(text)
    # R coerces a mixed color vector to character, and col2rgb("2") is palette 2.
    if text.isdigit():
        number = int(text)
        if number <= 0:
            raise ValueError("numerical color values must be positive")
        return _PALETTE[(number - 1) % len(_PALETTE)]
    return _named_rgb(text)


def _hex_rgb(text):
    body = text[1:]
    if len(body) == 6:
        return tuple(int(body[i : i + 2], 16) for i in (0, 2, 4))
    if len(body) == 8:
        return tuple(int(body[i : i + 2], 16) for i in (0, 2, 4))
    if len(body) == 3:
        return tuple(int(ch * 2, 16) for ch in body)
    raise ValueError(f"invalid color {text}")


def _named_rgb(name):
    import matplotlib.colors as mcolors

    key = name.lower().replace(" ", "")
    try:
        red, green, blue = mcolors.to_rgb(key)
    except ValueError as exc:
        raise ValueError(f"invalid color {name}") from exc
    return tuple(int(round(channel * 255.0)) for channel in (red, green, blue))


def _hex(rgb):
    red, green, blue = (int(round(float(channel))) for channel in rgb)
    return f"#{red:02x}{green:02x}{blue:02x}"


def _log_limit(value, use_log, axis):
    if not use_log:
        return value
    if value <= 0.0:
        warnings.warn(
            f"1 {axis} value <= 0 omitted from logarithmic plot",
            RuntimeWarning,
            stacklevel=3,
        )
        raise ValueError(f"need finite '{axis}lim' values")
    return math.log10(value)


def _usr_pair(vmin, vmax, axs):
    """R plot-window limits, the two ``par("usr")`` numbers for one axis."""
    if vmin == vmax:
        if vmin == 0.0:
            vmin, vmax = -1.0, 1.0
        else:
            vmin = 0.6 * vmin
            vmax = 1.4 * vmax
        if vmin > vmax:
            vmin, vmax = vmax, vmin
    if axs == "i":
        return vmin, vmax
    temp = 0.04 * (vmax - vmin)
    return vmin - temp, vmax + temp


def _mpl_limit(usr, use_log):
    lo, hi = usr
    if not use_log:
        return lo, hi
    return 10.0**lo, 10.0**hi
