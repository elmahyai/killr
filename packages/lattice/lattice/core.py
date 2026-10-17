"""Formula packets, scale padding, and the charts nlme asks lattice to draw."""

from __future__ import annotations

import math
import re
import statistics

_NUMERIC_PAD = 0.07
_FACTOR_PAD = 0.6
_SUPERPOSE = (
    "#0072B2",
    "#E69F00",
    "#009E73",
    "#D55E00",
    "#56B4E9",
    "#F0E442",
    "#CC79A7",
)


class Trellis:
    """One conditioned plot. ``draw`` writes a Matplotlib figure."""

    def __init__(self, kind, packets, x_limits, y_limits, xlab, ylab, horizontal=False):
        self.kind = kind
        self.packets = packets
        self.x_limits = x_limits
        self.y_limits = y_limits
        self.xlab = xlab
        self.ylab = ylab
        self.horizontal = horizontal

    def __str__(self):
        limits = " ".join(f"{value:.6g}" for value in _flat_limits(self.y_limits))
        return f"{self.kind}: {len(self.packets)} panel(s), y {limits}"

    def draw(self, path):
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        count = len(self.packets)
        fig, axes = plt.subplots(1, count, figsize=(4 * count, 3.2), squeeze=False)
        for panel, axis in zip(self.packets, axes[0]):
            _draw_panel(axis, self, panel)
        fig.tight_layout()
        fig.savefig(path, format="svg")
        plt.close(fig)


def xyplot(formula, data):
    """Scatter of a formula. A bar introduces conditioning panels."""
    parsed = lattice_parse_formula(formula, data)
    packets = _packets(parsed, numeric_x=True)
    x_limits = _extend(_finite(parsed["right"]))
    y_limits = _extend(_finite(parsed["left"]))
    return Trellis("xyplot", packets, x_limits, y_limits, parsed["right_name"], parsed["left_name"])


def bwplot(formula, data, horizontal=None):
    """Box plot. A factor on the right stands the boxes upright."""
    parsed = lattice_parse_formula(formula, data)
    if horizontal is None:
        horizontal = not (parsed["right_factor"] and _all_numeric(parsed["left"]))
    if horizontal:
        parsed = _swap(parsed)
    packets = _packets(parsed, numeric_x=not parsed["right_factor"])
    if parsed["right_factor"]:
        x_limits = list(parsed["right_levels"])
    else:
        x_limits = _extend(_finite(parsed["right"]))
    y_limits = _extend(_finite(parsed["left"]))
    return Trellis(
        "bwplot",
        packets,
        x_limits,
        y_limits,
        parsed["right_name"],
        parsed["left_name"],
        horizontal=horizontal,
    )


def lattice_parse_formula(model, data, subset=None):
    """Split ``y ~ x | a * b`` and evaluate each name in ``data``."""
    if "~" not in model:
        raise ValueError("model must be a formula object")
    left_text, right_text = (part.strip() for part in model.split("~", 1))
    condition_text = ""
    if "|" in right_text:
        right_text, condition_text = (part.strip() for part in right_text.split("|", 1))
    n = _nrow(data)
    keep = [True] * n if subset is None else [bool(value) for value in subset]
    left = _eval_term(left_text, data) if left_text else None
    right = _eval_term(right_text, data)
    if left is not None:
        left = _subset(left, keep)
    right = _subset(right, keep)
    conditions = []
    condition_values = []
    levels = []
    for piece in _split_condition(condition_text):
        values = _subset(_eval_term(piece, data), keep)
        codes, labels = _as_factor(values["values"])
        conditions.append(codes)
        condition_values.append(values["values"])
        levels.append(labels)
    return {
        "left": None if left is None else left["values"],
        "right": right["values"],
        "right_factor": right["factor"],
        "right_levels": right["levels"],
        "left_name": left_text,
        "right_name": right_text,
        "conditions": conditions,
        "condition_values": condition_values,
        "condlevels": levels,
    }


def prepanel_default_xyplot(x, y, groups=None):
    """Raw ranges and consecutive differences after sorting x."""
    x = [float(value) for value in x]
    y = [float(value) for value in y]
    if not any(math.isfinite(value) for value in x) or not any(math.isfinite(value) for value in y):
        return {"xlim": [math.nan, math.nan], "ylim": [math.nan, math.nan], "dx": [], "dy": []}
    order = sorted(range(len(x)), key=lambda index: x[index])
    if groups is None:
        dx = [x[order[i]] - x[order[i - 1]] for i in range(1, len(order))]
        dy = [y[order[i]] - y[order[i - 1]] for i in range(1, len(order))]
    else:
        dx, dy = [], []
        grouped = {}
        for index in order:
            grouped.setdefault(groups[index], []).append(index)
        for indexes in grouped.values():
            dx.extend(x[indexes[i]] - x[indexes[i - 1]] for i in range(1, len(indexes)))
            dy.extend(y[indexes[i]] - y[indexes[i - 1]] for i in range(1, len(indexes)))
    return {"xlim": _range(x), "ylim": _range(y), "dx": dx, "dy": dy}


def panel_xyplot(x, y, type="p"):
    """Points, or the step polyline lattice builds for type ``s``."""
    x = [float(value) for value in x]
    y = [float(value) for value in y]
    if "s" not in type:
        return {"x": x, "y": y}
    order = sorted(range(len(x)), key=lambda index: x[index])
    step_x = []
    step_y = []
    for position, index in enumerate(order):
        step_x.append(x[index])
        step_y.append(y[index])
        if position < len(order) - 1:
            step_x.append(x[order[position + 1]])
            step_y.append(y[index])
    return {"x": step_x, "y": step_y}


def panel_lmline(x, y):
    """Intercept and slope of the least-squares line."""
    x = [float(value) for value in x]
    y = [float(value) for value in y]
    n = len(x)
    if n < 2:
        return [math.nan, math.nan]
    x_bar = sum(x) / n
    y_bar = sum(y) / n
    ss = sum((value - x_bar) ** 2 for value in x)
    slope = sum((x[i] - x_bar) * (y[i] - y_bar) for i in range(n)) / ss
    return [y_bar - slope * x_bar, slope]


def panel_bwplot(x, y, coef=1.5):
    """Tukey five-number summaries, one row per sorted level of x."""
    x = [float(value) for value in x]
    y = [float(value) for value in y]
    levels = sorted(set(x))
    stats = []
    for level in levels:
        sample = [y[i] for i in range(len(y)) if x[i] == level]
        stats.extend(_boxplot_stats(sample, coef))
    return stats


def do_breaks(endpoints, nint):
    """Equally spaced breaks from the first endpoint through the second."""
    if len(endpoints) != 2:
        raise ValueError("error")
    span = endpoints[1] - endpoints[0]
    return [endpoints[0] + span * i / nint for i in range(int(nint) + 1)]


class Shingle:
    """Numeric vector with zero-width interval levels, as lattice shingles."""

    __slots__ = ("data", "levels")

    def __init__(self, data, levels):
        self.data = list(data)
        self.levels = [list(level) for level in levels]


class _FactorOrShingle:
    __slots__ = ("codes", "levels")

    def __init__(self, codes, levels):
        self.codes = list(codes)
        self.levels = list(levels)


def as_factor_or_shingle(x, subset=True, drop=False):
    """Factor for non-numeric ``x``, shingle for numeric, then ``subset`` and ``drop``."""
    if _is_numeric_like(x):
        converted = _as_shingle_for_factor_or_shingle(x)
    else:
        converted = _factor_or_shingle_factor(_vectorize(x))
    return _apply_factor_or_shingle_subset(converted, subset, drop)


def _vectorize(x):
    if isinstance(x, (list, tuple)):
        return list(x)
    if isinstance(x, str):
        return [x]
    return list(x)


def _is_numeric_like(x):
    values = _vectorize(x)
    if not values:
        return True
    return all(isinstance(value, (int, float)) and not isinstance(value, bool) for value in values)


def _as_shingle_for_factor_or_shingle(x):
    if isinstance(x, Shingle):
        return x
    values = _vectorize(x)
    intervals = sorted(set(values))
    levels = [[value, value] for value in intervals]
    return Shingle(values, levels)


def _factor_or_shingle_factor(values):
    codes, labels = _as_factor(values)
    return _FactorOrShingle(codes, labels)


def _apply_factor_or_shingle_subset(x, subset, drop):
    if isinstance(x, Shingle):
        return _subset_shingle(x, subset, drop)
    return _subset_factor_or_shingle(x, subset, drop)


def _subset_index(subset, n):
    if subset is True:
        return [True] * n
    if subset is False:
        return [False] * n
    if isinstance(subset, bool):
        return [subset] * n
    flags = [bool(value) for value in subset]
    return [flags[index % len(flags)] for index in range(n)]


def _subset_shingle(shingle, subset, drop):
    keep = _subset_index(subset, len(shingle.data))
    data = [value for value, flag in zip(shingle.data, keep) if flag]
    counts = [_shingle_level_count(data, level) for level in shingle.levels]
    levels = shingle.levels
    if drop:
        levels = [level for level, count in zip(levels, counts) if count > 0]
    return Shingle(data, levels)


def _shingle_level_count(data, level):
    low, high = level[0], level[1]
    if low == high:
        return sum(1 for value in data if value == low)
    return sum(1 for value in data if low <= value <= high)


def _subset_factor_or_shingle(factor, subset, drop):
    keep = _subset_index(subset, len(factor.codes))
    codes = [code for code, flag in zip(factor.codes, keep) if flag]
    labels = factor.levels
    if drop:
        used = set(codes)
        labels = [label for index, label in enumerate(labels, start=1) if index in used]
        labels_by_old = factor.levels
        codes = [labels.index(labels_by_old[code - 1]) + 1 for code in codes]
    return _FactorOrShingle(codes, labels)


def banking(dx, dy=1):
    """Median absolute slope from consecutive ``dx`` and ``dy`` segments."""
    if _is_r_list(dx):
        if isinstance(dx, dict):
            parts = list(dx.values())
            dy = parts[1]
            dx = parts[0]
        else:
            dy = dx[1]
            dx = dx[0]
    dx = list(dx)
    dy = list(dy) if isinstance(dy, (list, tuple)) else [dy]
    if len(dx) != len(dy):
        raise ValueError("Non matching lengths")
    slopes = []
    for xstep, ystep in zip(dx, dy):
        if xstep == 0 or ystep == 0 or _is_na(xstep) or _is_na(ystep):
            continue
        slopes.append(abs(xstep / ystep))
    if slopes:
        return statistics.median(slopes)
    return 1


def rows(x, which):
    """Recycle each component, then keep the 1-based positions in ``which``."""
    which = [int(value) for value in which]
    width = max(max(which), len(which))
    out = {}
    for key, value in x.items():
        series = value if isinstance(value, (list, tuple)) else [value]
        recycled = [series[i % len(series)] for i in range(width)]
        out[key] = [recycled[index - 1] for index in which]
    return out


def trellis_par_get(name=None):
    """The default theme entries a panel reads. Colors are the Okabe-Ito set."""
    symbol = {"pch": [1], "col": ["#0072B2"], "cex": [0.8]}
    line = {"col": ["#0072B2"], "lty": [1], "lwd": [1]}
    superpose_symbol = {"pch": [1], "col": list(_SUPERPOSE), "cex": [0.8]}
    superpose_line = {"col": list(_SUPERPOSE), "lty": [1], "lwd": [1]}
    theme = {
        "plot.symbol": symbol,
        "plot.line": line,
        "superpose.symbol": superpose_symbol,
        "superpose.line": superpose_line,
    }
    if name is None:
        return theme
    return theme[name]


def _packets(parsed, numeric_x):
    n = len(parsed["right"])
    conditions = parsed["conditions"] or [[1] * n]
    level_counts = [max(codes) for codes in conditions]
    current = [1] * len(conditions)
    packets = []
    for _ in range(math.prod(level_counts)):
        chosen = []
        for index in range(n):
            if all(conditions[j][index] == current[j] for j in range(len(conditions))):
                chosen.append(index)
        x_values = parsed["right"]
        if parsed["right_factor"]:
            x_values = _as_factor(parsed["right"])[0]
        label = ""
        if parsed["condlevels"]:
            label = " | ".join(
                parsed["condlevels"][j][current[j] - 1] for j in range(len(parsed["condlevels"]))
            )
        packets.append(
            {
                "x": [x_values[i] for i in chosen],
                "y": [parsed["left"][i] for i in chosen],
                "label": label,
            }
        )
        current = _cupdate(current, level_counts)
    return packets


def _cupdate(index, maxim):
    index = list(index)
    index[0] += 1
    if index[0] > maxim[0] and len(maxim) > 1:
        return [1] + _cupdate(index[1:], maxim[1:])
    return index


def _eval_term(text, data):
    match = re.fullmatch(r"factor\(([^)]+)\)", text)
    if match:
        values = list(data[match.group(1).strip()])
        _codes, levels = _as_factor(values)
        return {"values": values, "factor": True, "levels": levels}
    return {"values": [float(value) for value in data[text]], "factor": False, "levels": []}


def _as_factor(values):
    levels = sorted(set(values), key=lambda value: (isinstance(value, str), value))
    labels = [str(value) if not isinstance(value, str) else value for value in levels]
    # Numeric levels sort numerically; their labels are the shortest decimal R would print
    # only when the value is an integer. Keep the Python str of the number otherwise.
    if levels and all(isinstance(value, (int, float)) and float(value).is_integer() for value in levels):
        labels = [str(int(value)) for value in levels]
    codes = [levels.index(value) + 1 for value in values]
    return codes, labels


def _subset(term, keep):
    values = [term["values"][i] for i in range(len(keep)) if keep[i]]
    return {"values": values, "factor": term["factor"], "levels": term["levels"]}


def _split_condition(text):
    if not text:
        return []
    return [piece.strip() for piece in re.split(r"[*+]", text) if piece.strip()]


def _swap(parsed):
    swapped = dict(parsed)
    swapped["left"], swapped["right"] = parsed["right"], parsed["left"]
    swapped["left_name"], swapped["right_name"] = parsed["right_name"], parsed["left_name"]
    swapped["right_factor"] = False
    swapped["right_levels"] = []
    return swapped


def _extend(values, axs="r"):
    if not values:
        return [math.nan, math.nan]
    low, high = min(values), max(values)
    if low == high:
        return [low - 0.5, high + 0.5]
    pad = 0 if axs == "i" else _NUMERIC_PAD
    span = high - low
    return [low - pad * span, high + pad * span]


def _boxplot_stats(sample, coef):
    ordered = sorted(value for value in sample if math.isfinite(value))
    stats = _fivenum(ordered)
    iqr = stats[3] - stats[1]
    lower = stats[1] - coef * iqr
    upper = stats[3] + coef * iqr
    inside = [value for value in ordered if lower <= value <= upper]
    if inside:
        stats[0] = inside[0]
        stats[4] = inside[-1]
    return stats


def _fivenum(ordered):
    n = len(ordered)
    if n == 0:
        return [math.nan] * 5
    n4 = math.floor((n + 3) / 2) / 2
    hinges = [1, n4, (n + 1) / 2, n + 1 - n4, n]
    return [0.5 * (ordered[math.floor(hinge) - 1] + ordered[math.ceil(hinge) - 1]) for hinge in hinges]


def _finite(values):
    return [float(value) for value in values if math.isfinite(float(value))]


def _range(values):
    finite = _finite(values)
    return [min(finite), max(finite)]


def _all_numeric(values):
    try:
        [float(value) for value in values]
    except (TypeError, ValueError):
        return False
    return True


def _nrow(data):
    return len(next(iter(data.values())))


def _flat_limits(limits):
    if limits and isinstance(limits[0], str):
        return []
    return limits


def _is_na(value):
    return value is None or (isinstance(value, float) and math.isnan(value))


def _is_r_list(obj):
    if isinstance(obj, dict):
        return True
    if isinstance(obj, list):
        return not all(_is_atomic_scalar(item) for item in obj)
    return False


def _is_atomic_scalar(value):
    if isinstance(value, float):
        return True
    return isinstance(value, (str, bool, int)) or value is None


def _draw_panel(axis, plot, panel):
    if plot.kind == "bwplot" and plot.x_limits and isinstance(plot.x_limits[0], str):
        stats = panel_bwplot(panel["x"], panel["y"])
        levels = sorted(set(panel["x"]))
        for index, level in enumerate(levels):
            row = stats[index * 5 : (index + 1) * 5]
            axis.plot([level, level], [row[0], row[1]], color="#0072B2")
            axis.plot([level, level], [row[3], row[4]], color="#0072B2")
            axis.add_patch(
                __import__("matplotlib").patches.Rectangle(
                    (level - 0.2, row[1]), 0.4, row[3] - row[1], fill=False, edgecolor="#0072B2"
                )
            )
            axis.plot([level - 0.2, level + 0.2], [row[2], row[2]], color="#0072B2")
        axis.set_xticks(levels)
        axis.set_xticklabels(plot.x_limits)
    else:
        axis.plot(panel["x"], panel["y"], linestyle="none", marker="o", color="#0072B2")
        axis.set_xlim(plot.x_limits)
    if plot.y_limits and isinstance(plot.y_limits[0], float):
        axis.set_ylim(plot.y_limits)
    if panel["label"]:
        axis.set_title(panel["label"])
    axis.set_xlabel(plot.xlab)
    axis.set_ylabel(plot.ylab)
