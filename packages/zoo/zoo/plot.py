"""plot.zoo, lines.zoo, points.zoo, make.par.list, and xblocks.

Matplotlib draws the figure. The returned records are the coordinates
passed to the panel or to rect, which is what the checks compare.
"""

from __future__ import annotations

import math
import warnings
from typing import Any

import numpy as np

from zoo.series import Zoo

# First entry of palette() in a fresh R 4.5 session (palette "R4").
_PALETTE = [
    "black",
    "#DF536B",
    "#61D04F",
    "#2297E6",
    "#28E2E5",
    "#CD0BBC",
    "#F5C710",
    "gray62",
]

_LTY = {
    0: "none",
    1: "solid",
    2: (0, (4, 1.5)),
    3: (0, (1, 1.5)),
    4: (0, (4, 1.5, 1, 1.5)),
    5: (0, (8, 1.5)),
    6: (0, (6, 1.5, 1, 1.5)),
    "solid": "solid",
    "dashed": (0, (4, 1.5)),
    "dotted": (0, (1, 1.5)),
    "dotdash": (0, (4, 1.5, 1, 1.5)),
    "longdash": (0, (8, 1.5)),
    "twodash": (0, (6, 1.5, 1, 1.5)),
    "blank": "none",
}

_PCH = {
    1: ("o", False),
    2: ("^", False),
    3: ("+", False),
    4: ("x", False),
    5: ("D", False),
    6: ("v", False),
    7: ("s", False),
    8: ("*", False),
    15: ("s", True),
    16: ("o", True),
    19: ("o", True),
    20: (".", True),
}


class PanelEnv:
    """Values plot.zoo stores for a custom panel, as parent.frame() does."""

    panel_number = None
    series_number = None
    series_within_screen = None
    nser = None
    nr = None
    ngraph = None


panel_env = PanelEnv()


def _is_na(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, (bool, np.bool_)):
        return False
    if isinstance(value, (float, np.floating)):
        return math.isnan(float(value))
    return False


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float, np.integer, np.floating)) and not isinstance(
        value, (bool, np.bool_)
    )


def _ncol(obj: Zoo) -> int:
    data = np.asarray(obj.data)
    if data.ndim <= 1:
        return 1
    return int(data.shape[1])


def _nrow(obj: Zoo) -> int:
    data = np.asarray(obj.data)
    if data.ndim == 0:
        return 1
    return int(data.shape[0])


def _colnames(obj: Zoo) -> list[str]:
    names = getattr(obj, "colnames", None)
    nser = _ncol(obj)
    if names is None:
        return [f"V{i}" for i in range(1, nser + 1)]
    return [str(name) for name in list(names)]


def _index_array(obj: Zoo) -> np.ndarray:
    index = obj.index
    if isinstance(index, np.ndarray) and np.issubdtype(index.dtype, np.number):
        return np.asarray(index, dtype=float).reshape(-1)
    values = []
    for item in list(index):
        if _is_na(item):
            values.append(np.nan)
        else:
            values.append(float(item))
    return np.asarray(values, dtype=float)


def _column(obj: Zoo, which: int) -> np.ndarray:
    data = np.asarray(obj.data, dtype=float)
    if data.ndim <= 1:
        return np.asarray(data, dtype=float).reshape(-1)
    return np.asarray(data[:, which], dtype=float).reshape(-1)


def _core(obj: Any) -> Any:
    if isinstance(obj, Zoo):
        return obj.data
    return obj


def _is_pair_list(value: Any) -> bool:
    if not isinstance(value, (list, tuple)) or len(value) == 0:
        return False
    for item in value:
        if not (isinstance(item, tuple) and len(item) == 2 and (item[0] is None or isinstance(item[0], str))):
            return False
    return True


def _is_nested_list(value: Any) -> bool:
    if not isinstance(value, (list, tuple)) or len(value) == 0:
        return False
    if _is_pair_list(value):
        return False
    return any(isinstance(item, (list, tuple, np.ndarray)) or item is None for item in value) and any(
        isinstance(item, (list, tuple, np.ndarray)) for item in value
    )


def _atomic_parts(value: Any) -> list[Any]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, np.ndarray):
        if value.ndim == 0:
            return [value.item()]
        flat = value.reshape(-1)
        return [flat[i].item() if not isinstance(flat[i], np.ndarray) else flat[i] for i in range(flat.size)]
    if isinstance(value, (list, tuple)):
        return list(value)
    return [value]


def _interpret(value: Any, m: int) -> list[tuple[str, Any]]:
    """Turn a Python value into R's list of (name, element) pairs."""
    if isinstance(value, dict):
        return [(str(key), item) for key, item in value.items()]
    if _is_pair_list(value):
        return [("" if name is None else str(name), item) for name, item in value]
    if _is_nested_list(value):
        return [("", item) for item in value]
    if m == 1:
        return [("", value)]
    return [("", item) for item in _atomic_parts(value)]


def _element_length(value: Any) -> int:
    if value is None:
        return 0
    if isinstance(value, str) or _is_number(value) or isinstance(value, (bool, np.bool_)):
        return 1
    if isinstance(value, np.ndarray):
        return int(value.size)
    if isinstance(value, (list, tuple)):
        return len(value)
    return 1


def _as_sequence(value: Any) -> list[Any]:
    if isinstance(value, str) or _is_number(value) or isinstance(value, (bool, np.bool_)):
        return [value]
    if isinstance(value, np.ndarray):
        if value.ndim == 0:
            return [value.item()]
        return [value.reshape(-1)[i].item() for i in range(value.size)]
    if isinstance(value, (list, tuple)):
        return list(value)
    return [value]


def _copy_value(value: Any) -> Any:
    if isinstance(value, np.ndarray):
        return value.copy()
    if isinstance(value, list):
        return list(value)
    return value


def _recycle_within(value: Any, n: int) -> Any:
    """Length 1 stays length 1. Anything else is rep(..., length.out = n)."""
    if value is None:
        warnings.warn("'x' is NULL so the result will be NULL", RuntimeWarning, stacklevel=3)
        return None
    if _element_length(value) == 1:
        seq = _as_sequence(value)
        return seq[0]
    seq = _as_sequence(value)
    if len(seq) == 0:
        return [float("nan")] * n
    return [seq[i % len(seq)] for i in range(n)]


def _rep_elements(items: list[Any], length_out: int) -> list[Any]:
    if length_out == 0:
        return []
    if len(items) == 0:
        return []
    return [_copy_value(items[i % len(items)]) for i in range(length_out)]


def _def_cells(def_: Any, n_names: int) -> list[Any] | None:
    """y[] <- def. NULL clears the list. An atomic def is recycled across cells."""
    if def_ is None:
        return None
    parts = _atomic_parts(def_)
    if isinstance(def_, str) or _is_number(def_) or isinstance(def_, (bool, np.bool_)):
        parts = [def_]
    if len(parts) == 0:
        raise ValueError("replacement has length zero")
    if n_names % len(parts) != 0:
        warnings.warn(
            "number of items to replace is not a multiple of replacement length",
            RuntimeWarning,
            stacklevel=3,
        )
    return [parts[i % len(parts)] for i in range(n_names)]


def make_par_list(nams, x, n, m, def_=1, recycle=None):
    """Distribute a parameter vector or list across series.

    This is make.par.list. A length-1 value stays length 1. A longer value
    is recycled to ``n`` rows. ``recycle`` defaults to true when ``x`` has
    an unnamed element. ``def_=None`` follows ``y[] <- NULL``, which drops
    the names and leaves unspecified series as NULL.
    """
    nams = [str(name) for name in list(nams)]
    items = _interpret(x, m)
    names = [name for name, _ in items]
    if len(items) == 0 or all(name == "" for name in names) and not isinstance(x, dict):
        # as.list of an atomic has NULL names, so every element is unnamed.
        # A dict is named even if a key is empty, which R cannot store that way.
        if not isinstance(x, dict) and not _is_pair_list(x) and not _is_nested_list(x):
            unnamed = [True] * len(items)
        elif _is_nested_list(x):
            unnamed = [True] * len(items)
        else:
            unnamed = [name == "" for name in names]
    else:
        unnamed = [name == "" for name in names]
    if isinstance(x, dict):
        unnamed = [False] * len(items)
    if recycle is None:
        recycle = sum(unnamed) > 0
    else:
        recycle = bool(recycle)

    in_x = []
    for name in nams:
        in_x.append(any(item_name == name and item_name != "" for item_name, _ in items) or (
            name == "" and any(item_name == "" for item_name in names) and False
        ))
        # Column names match named elements only. An empty name is not a series.
        in_x[-1] = any(item_name == name for item_name, _ in items) and name != ""

    named_value = {}
    for item_name, item in items:
        if item_name != "" and item_name not in named_value:
            named_value[item_name] = item

    values: list[Any] = [None] * len(nams)
    out_names = list(nams)
    if not recycle:
        cells = _def_cells(def_, len(nams))
        if cells is None:
            out_names = [""] * len(nams)
            values = [None] * len(nams)
        else:
            values = cells

    for i, name in enumerate(nams):
        if in_x[i]:
            values[i] = _copy_value(named_value[name])

    unnamed_values = [item for flag, (_, item) in zip(unnamed, items) if flag]
    if recycle:
        if sum(unnamed) <= 0:
            raise ValueError("sum(unnamed) > 0 is not TRUE")
        missing = [i for i, flag in enumerate(in_x) if not flag]
        for index, filled in zip(missing, _rep_elements(unnamed_values, len(missing))):
            values[index] = filled
    else:
        missing = [i for i, flag in enumerate(in_x) if not flag]
        count = sum(unnamed)
        if count > len(missing):
            raise ValueError("NAs are not allowed in subscripted assignments")
        for index, filled in zip(missing[:count], unnamed_values[:count]):
            values[index] = _copy_value(filled)

    recycled = [_recycle_within(value, n) for value in values]
    return list(zip(out_names, recycled))


def _screen_label(value: Any) -> str:
    if isinstance(value, str):
        return value
    if _element_length(value) != 1:
        raise ValueError("each series screen must be a single value")
    scalar = _as_sequence(value)[0]
    if isinstance(scalar, str):
        return scalar
    number = float(scalar)
    if number.is_integer():
        return str(int(number))
    return format(number, ".15g")


def _factor(values: list[Any]) -> tuple[list[str], list[str]]:
    labels = [_screen_label(value) for value in values]
    if all(_is_number(_as_sequence(value)[0] if _element_length(value) == 1 else value) or _is_number(value) for value in values):
        levels = sorted(set(labels), key=float)
    else:
        levels = sorted(set(labels))
    return labels, levels


def _match_arg(arg: str, choices: list[str]) -> str:
    hits = [choice for choice in choices if choice.startswith(arg)]
    if len(hits) == 1:
        return hits[0]
    quoted = ", ".join(f'"{choice}"' for choice in choices)
    raise ValueError(f"'{arg}' should be one of {quoted}")


def _finite_range(values: list[float]) -> list[float]:
    finite = [float(value) for value in values if math.isfinite(float(value))]
    if not finite:
        warnings.warn(
            "no non-missing arguments to min; returning Inf",
            RuntimeWarning,
            stacklevel=3,
        )
        return [float("inf"), float("-inf")]
    return [min(finite), max(finite)]


def _range_values(values: list[float], na_rm: bool = True) -> list[float]:
    if not na_rm and any(_is_na(value) for value in values):
        return [float("nan"), float("nan")]
    return _finite_range(values)


def _range2(value: Any, na_rm: bool = True) -> list[float]:
    """range2: a length-2 value is kept, including order and NA."""
    if value is None:
        warnings.warn(
            "no non-missing arguments to min; returning Inf",
            RuntimeWarning,
            stacklevel=3,
        )
        return [float("inf"), float("-inf")]
    seq = [float(item) for item in _as_sequence(value)]
    if len(seq) == 2:
        return seq
    return _range_values(seq, na_rm=na_rm)


def _na_omit(values: list[float]) -> list[float]:
    return [value for value in values if not _is_na(value) and math.isfinite(value) or (
        not _is_na(value) and not isinstance(value, float)
    )]


def _clean_ylim(value: Any) -> list[float] | None:
    if value is None:
        return None
    seq = [float(item) for item in _as_sequence(value)]
    kept = [item for item in seq if not math.isnan(item)]
    if len(kept) == 0:
        return None
    return _range2(seq, na_rm=True)


def _float_list(values: Any) -> list[float]:
    return [float(item) if not _is_na(item) else float("nan") for item in np.asarray(values, dtype=float).reshape(-1)]


def _index_keys(index: np.ndarray) -> list[float]:
    return [float(item) for item in index]


def _has_duplicate(keys: list[float]) -> bool:
    seen = set()
    for key in keys:
        marker = ("na",) if math.isnan(key) else ("v", key)
        if marker in seen:
            return True
        seen.add(marker)
    return False


def _merge_keys(x: Zoo, y: Zoo, how: str) -> tuple[list[float], list[float], list[float]]:
    x_index = _index_keys(_index_array(x))
    y_index = _index_keys(_index_array(y))
    if _has_duplicate(x_index) or _has_duplicate(y_index):
        raise ValueError("series cannot be merged with non-unique index entries in a series")
    x_value = _column(x, 0)
    y_value = _column(y, 0)
    x_map = {key: float(val) for key, val in zip(x_index, x_value)}
    y_map = {key: float(val) for key, val in zip(y_index, y_value)}
    if how == "inner":
        keys = sorted(set(x_map) & set(y_map))
    else:
        keys = sorted(set(x_map) | set(y_map))
    xs = [x_map.get(key, float("nan")) for key in keys]
    ys = [y_map.get(key, float("nan")) for key in keys]
    return keys, xs, ys


def index2char(index: Any) -> list[str]:
    """Labels for a plain numeric index. Whole numbers print without a decimal."""
    labels = []
    for item in np.asarray(index, dtype=float).reshape(-1):
        if math.isnan(float(item)):
            labels.append("NA")
        elif float(item).is_integer() and abs(float(item)) < 1e15:
            labels.append(str(int(float(item))))
        else:
            labels.append(format(float(item), ".15g"))
    return labels


def _color(value: Any) -> Any:
    if isinstance(value, str) or value is None:
        return "none" if value is None else value
    if _is_number(value):
        number = int(value)
        if number <= 0:
            return "none"
        return _PALETTE[(number - 1) % len(_PALETTE)]
    return value


def _colors(value: Any, n: int) -> list[Any]:
    if isinstance(value, str) or _is_number(value) or value is None:
        return [_color(value)] * n
    seq = _as_sequence(value)
    if len(seq) == 0:
        return ["black"] * n
    return [_color(seq[i % len(seq)]) for i in range(n)]


def _lty(value: Any) -> Any:
    if isinstance(value, str):
        return _LTY.get(value, value)
    if _is_number(value):
        return _LTY.get(int(value), "solid")
    return "solid"


def _marker(value: Any) -> tuple[str, bool]:
    if _is_number(value):
        return _PCH.get(int(value), ("o", False))
    return ("o", False)


def _draw_type(ax, x, y, type_: str, col, pch, lty, lwd) -> None:
    x_arr = np.asarray(x, dtype=float)
    y_arr = np.asarray(y, dtype=float)
    mask = ~(np.isfinite(x_arr) & np.isfinite(y_arr))
    x_m = np.ma.array(x_arr, mask=mask)
    y_m = np.ma.array(y_arr, mask=mask)
    width = float(lwd) if _is_number(lwd) else 1.0
    style = _lty(lty if _element_length(lty) == 1 else _as_sequence(lty)[0])
    color = _colors(col, len(x_arr))
    line_color = color[0]
    kind = type_ if isinstance(type_, str) else str(_as_sequence(type_)[0])
    if kind in {"l", "b", "c", "o"}:
        ax.plot(x_m, y_m, color=line_color, linestyle=style, linewidth=width, solid_capstyle="butt")
    if kind == "s":
        ax.step(x_m, y_m, where="post", color=line_color, linestyle=style, linewidth=width)
    if kind == "S":
        ax.step(x_m, y_m, where="pre", color=line_color, linestyle=style, linewidth=width)
    if kind == "h":
        zeros = np.ma.array(np.zeros(len(x_arr)), mask=mask)
        ax.vlines(x_arr, zeros, y_arr, colors=line_color, linestyles=style, linewidth=width)
    if kind in {"p", "b", "o"}:
        pch_seq = pch if _element_length(pch) != 1 else [pch] * len(x_arr)
        if _element_length(pch) != 1:
            pch_seq = _as_sequence(pch)
            pch_seq = [pch_seq[i % len(pch_seq)] for i in range(len(x_arr))]
        else:
            pch_seq = [pch] * len(x_arr)
        for i in range(len(x_arr)):
            if mask[i]:
                continue
            marker, filled = _marker(pch_seq[i])
            face = color[i] if filled else "none"
            ax.plot(
                [x_arr[i]],
                [y_arr[i]],
                linestyle="none",
                marker=marker,
                markerfacecolor=face,
                markeredgecolor=color[i],
                markersize=6 if marker != "." else 3,
            )


def lines_zoo(x, y=None, type="l", col=1, pch=1, lty=1, lwd=1, ax=None, draw=True, **kwargs):
    """lines.zoo. A second series is drawn against the first after an outer join."""
    if y is None:
        if _ncol(x) != 1:
            raise ValueError("Can't plot lines for multivariate zoo object")
        xs = _float_list(_index_array(x))
        ys = _float_list(_column(x, 0))
    else:
        if not isinstance(y, Zoo):
            raise TypeError("y must be a zoo series")
        _keys, xs, ys = _merge_keys(x, y, "outer")
    record = {"x": xs, "y": ys, "type": type, "col": col, "pch": pch, "lty": lty, "lwd": lwd}
    if draw:
        import matplotlib.pyplot as plt

        if ax is None:
            _fig, ax = plt.subplots()
            record["figure"] = _fig
            record["axes"] = ax
        else:
            record["axes"] = ax
        _draw_type(ax, xs, ys, type if isinstance(type, str) else "l", col, pch, lty, lwd)
    return record


def points_zoo(x, y=None, type="p", col=1, pch=1, lty=1, lwd=1, ax=None, draw=True, **kwargs):
    """points.zoo. The same call as lines.zoo with type ``p``."""
    return lines_zoo(x, y, type=type, col=col, pch=pch, lty=lty, lwd=lwd, ax=ax, draw=draw, **kwargs)


def _points_only(type_: Any) -> bool:
    if isinstance(type_, str):
        return type_ == "p"
    seq = _as_sequence(type_)
    return bool(seq) and all(item == "p" for item in seq)


def _prepare_ylim(ylim, names: list[str], nser: int) -> list[Any] | None:
    if ylim is None:
        return None
    if _is_nested_list(ylim) or isinstance(ylim, dict) or _is_pair_list(ylim):
        elements = [item for _, item in _interpret(ylim, nser)]
        ranged = [_range2(item, na_rm=True) for item in elements]
        rows = make_par_list(names, [("", item) for item in ranged], 2, nser, None)
    else:
        rows = make_par_list(names, [("", _range2(ylim, na_rm=True))], 2, nser, None)
    return [_clean_ylim(value) for _name, value in rows]


def _series_record(piece: Zoo, type_, col, pch, lty, lwd, draw: bool, ax) -> dict[str, Any]:
    if _points_only(type_):
        drawn = points_zoo(piece, type="p", col=col, pch=pch, lty=lty, lwd=lwd, ax=ax, draw=draw)
    else:
        drawn = lines_zoo(
            piece,
            type=type_ if isinstance(type_, str) else _as_sequence(type_)[0],
            col=col,
            pch=pch,
            lty=lty,
            lwd=lwd,
            ax=ax,
            draw=draw,
        )
    return {
        "type": type_,
        "lty": lty,
        "lwd": lwd,
        "col": col,
        "pch": pch,
        "x": drawn["x"],
        "y": drawn["y"],
    }


def _apply_log(ax, log: str) -> None:
    if log and "x" in log:
        ax.set_xscale("log")
    if log and "y" in log:
        ax.set_yscale("log")


def _set_ylim(ax, ylim) -> None:
    if ylim is None:
        return
    lo, hi = float(ylim[0]), float(ylim[1])
    if not math.isfinite(lo) or not math.isfinite(hi):
        return
    ax.set_ylim(lo, hi)


def plot_zoo(
    x,
    y=None,
    screens=None,
    plot_type=None,
    panel=None,
    xlab=None,
    ylab=None,
    main=None,
    xlim=None,
    ylim=None,
    xy_labels=False,
    xy_lines=None,
    yax_flip=False,
    oma=None,
    mar=None,
    col=1,
    lty=1,
    lwd=1,
    pch=1,
    type=None,
    log="",
    nc=None,
    widths=1,
    heights=1,
    draw=True,
    ax=None,
    par_pch=1,
    xname="x",
    yname="y",
    screens_missing=None,
    plot_type_missing=None,
    type_missing=None,
    xlab_missing=None,
    **kwargs,
):
    """plot.zoo. Returns the panel or scatter coordinates and, when drawing, a figure.

    ``screens``, ``plot_type``, and ``type`` use None for the R missing
    argument. Pass ``screens_missing=False`` only when None itself was
    supplied, which these arguments never are in R.
    """
    if screens_missing is None:
        screens_missing = screens is None
    if plot_type_missing is None:
        plot_type_missing = plot_type is None
    if type_missing is None:
        type_missing = type is None
    if xlab_missing is None:
        xlab_missing = xlab is None
    if type is None:
        type = "l"
    if xlab is None:
        xlab = "Index"
    if oma is None:
        oma = [6, 0, 5, 0]
    if mar is None:
        mar = [0, 5.1, 0, 5.1 if yax_flip else 2.1]

    if y is not None:
        return _plot_scatter(
            x,
            y,
            xlab=xlab,
            ylab=ylab,
            main=main,
            xlim=xlim,
            ylim=ylim,
            xy_labels=xy_labels,
            xy_lines=xy_lines,
            col=col,
            lty=lty,
            lwd=lwd,
            pch=pch,
            type=type,
            type_missing=type_missing,
            xlab_missing=xlab_missing,
            log=log,
            draw=draw,
            ax=ax,
            xname=xname,
            yname=yname,
        )

    nser = _ncol(x)
    nrow = _nrow(x)
    names = _colnames(x)
    if plot_type_missing:
        if screens_missing:
            plot_type = "multiple"
        elif len(_atomic_parts(screens)) > 0:
            # length(unique(screens) == 1) is the length of that comparison.
            plot_type = "single"
        else:
            plot_type = "multiple"
    plot_type = _match_arg(str(plot_type), ["multiple", "single"])
    if screens_missing:
        screens = 1 if plot_type == "single" else list(range(1, nser + 1))

    screen_rows = make_par_list(names, screens, nrow, nser, 1)
    labels, levels = _factor([value for _name, value in screen_rows])
    ngraph = len(levels)
    multiple = nser > 1 and (plot_type == "multiple" or ngraph > 1)
    if multiple and ngraph == 1:
        labels = [str(i) for i in range(1, nser + 1)]
        levels = list(labels)
        ngraph = nser

    index = _index_array(x)
    lty_values = _as_sequence(lty)
    lwd_values = _as_sequence(lwd)
    lty_series = [lty_values[i % len(lty_values)] for i in range(nser)]
    lwd_series = [lwd_values[i % len(lwd_values)] for i in range(nser)]
    col_rows = make_par_list(names, col, nrow, nser, 1)
    pch_rows = make_par_list(names, pch, nrow, nser, par_pch)
    type_rows = make_par_list(names, type, nrow, nser, "l")
    within = []
    seen_counts: dict[str, int] = {}
    for label in labels:
        seen_counts[label] = seen_counts.get(label, 0) + 1
        within.append(seen_counts[label])

    if multiple:
        if nc is None:
            nc = 2 if ngraph > 4 else 1
        nr = int(math.ceil(ngraph / nc))
        ylim_values = _prepare_ylim(ylim, names, nser)
        panels = []
        for j, level in enumerate(levels, start=1):
            members = [i for i, label in enumerate(labels) if label == level]
            panel_ylim = None if ylim_values is None else ylim_values[j - 1]
            series = []
            for i in members:
                piece = Zoo(_column(x, i), index, frequency=x.frequency, regular=x.regular)
                panel_env.panel_number = j
                panel_env.series_number = i + 1
                panel_env.series_within_screen = within[i]
                panel_env.nser = nser
                panel_env.nr = nr
                panel_env.ngraph = ngraph
                if panel is None:
                    drawn = _series_record(
                        piece,
                        type_rows[i][1],
                        col_rows[i][1],
                        pch_rows[i][1],
                        lty_series[i],
                        lwd_series[i],
                        draw=False,
                        ax=None,
                    )
                else:
                    panel(index, _column(x, i), col=col_rows[i][1], pch=pch_rows[i][1],
                          lty=lty_series[i], lwd=lwd_series[i], type=type_rows[i][1])
                    drawn = {
                        "type": type_rows[i][1],
                        "lty": lty_series[i],
                        "lwd": lwd_series[i],
                        "col": col_rows[i][1],
                        "pch": pch_rows[i][1],
                        "x": _float_list(index),
                        "y": _float_list(_column(x, i)),
                    }
                drawn["series"] = i + 1
                drawn["within"] = within[i]
                series.append(drawn)
            panels.append({"ylim": panel_ylim, "series": series})
        result: dict[str, Any] = {
            "kind": "series",
            "mode": "multiple",
            "nser": nser,
            "ngraph": ngraph,
            "nr": nr,
            "nc": nc,
            "panels": panels,
            "xlab": xlab,
            "ylab": _multiple_ylab(ylab, names, labels, ngraph, xname),
            "main": xname if main is None else main,
            "log": log,
            "yax_flip": yax_flip,
        }
        if draw:
            _draw_multiple(result)
        return result

    if ylim is None:
        flat = _column(x, 0) if nser == 1 else np.asarray(x.data, dtype=float).reshape(-1, order="F")
        ylim_single = _range_values(_float_list(flat), na_rm=True)
    else:
        if _is_nested_list(ylim) or isinstance(ylim, dict) or _is_pair_list(ylim):
            flat_ylim = []
            for _name, item in _interpret(ylim, nser):
                if item is None:
                    continue
                flat_ylim.extend(float(v) for v in _as_sequence(item))
            ylim_single = _range2(flat_ylim if flat_ylim else None, na_rm=True)
        else:
            ylim_single = _range2(ylim, na_rm=True)
    series = []
    for i in range(nser):
        piece = Zoo(_column(x, i), index, frequency=x.frequency, regular=x.regular)
        if panel is None:
            drawn = _series_record(
                piece,
                type_rows[i][1],
                col_rows[i][1],
                pch_rows[i][1],
                lty_series[i],
                lwd_series[i],
                draw=False,
                ax=None,
            )
        else:
            panel(index, _column(x, i), col=col_rows[i][1], pch=pch_rows[i][1],
                  lty=lty_series[i], lwd=lwd_series[i], type=type_rows[i][1])
            drawn = {
                "type": type_rows[i][1],
                "lty": lty_series[i],
                "lwd": lwd_series[i],
                "col": col_rows[i][1],
                "pch": pch_rows[i][1],
                "x": _float_list(index),
                "y": _float_list(_column(x, i)),
            }
        drawn["series"] = i + 1
        series.append(drawn)
    single_ylab = ylab
    if single_ylab is None:
        single_ylab = xname
    elif isinstance(single_ylab, (list, tuple)):
        single_ylab = single_ylab[0]
    result = {
        "kind": "series",
        "mode": "single",
        "nser": nser,
        "ylim": ylim_single,
        "series": series,
        "xlab": xlab,
        "ylab": single_ylab,
        "main": "" if main is None else main,
        "log": log,
        "xlim": xlim,
    }
    if draw:
        _draw_single(result, ax=ax)
    return result


def _multiple_ylab(ylab, names, labels, ngraph, xname):
    if ylab is None:
        seen = set()
        auto = []
        for i, label in enumerate(labels):
            if label not in seen:
                seen.add(label)
                if names and not all(name.startswith("V") and name[1:].isdigit() for name in names):
                    auto.append(names[i])
                else:
                    auto.append(f"Series {i + 1}")
        # colnames NULL uses Series <which>. A real colnames vector is used above
        # only when the caller set colnames. V1, V2 is the internal name, and
        # plot.zoo then falls through because colnames(x) is NULL.
        if all(name.startswith("V") and name[1:].isdigit() for name in names):
            auto = []
            seen = set()
            for i, label in enumerate(labels):
                if label not in seen:
                    seen.add(label)
                    auto.append(f"Series {i + 1}")
        ylab = auto
    if isinstance(ylab, str):
        ylab = [ylab]
    ylab = list(ylab)
    if len(ylab) == 0:
        ylab = [xname]
    return [ylab[i % len(ylab)] for i in range(ngraph)]


def _draw_multiple(result: dict[str, Any]) -> None:
    import matplotlib.pyplot as plt

    nr = result["nr"]
    nc = result["nc"]
    fig, axes = plt.subplots(nr, nc, figsize=(6.2, 2.15 * nr), squeeze=False, sharex=False)
    result["figure"] = fig
    fig.subplots_adjust(hspace=0.35, top=0.88 if result["main"] else 0.95)
    if result["main"]:
        fig.suptitle(result["main"])
    ngraph = result["ngraph"]
    for j, panel in enumerate(result["panels"], start=1):
        row = (j - 1) % nr
        col_i = (j - 1) // nr
        axis = axes[row][col_i]
        _apply_log(axis, result["log"])
        _set_ylim(axis, panel["ylim"])
        show_x = (j % nr == 0) or j == ngraph
        if not show_x:
            axis.tick_params(axis="x", labelbottom=False)
        else:
            axis.set_xlabel(result["xlab"])
        side = "left"
        if result["yax_flip"] and j % 2 == 0:
            side = "right"
            axis.yaxis.tick_right()
            axis.yaxis.set_label_position("right")
        axis.set_ylabel(result["ylab"][j - 1])
        for series in panel["series"]:
            _draw_type(
                axis,
                series["x"],
                series["y"],
                series["type"] if isinstance(series["type"], str) else "l",
                series["col"],
                series["pch"],
                series["lty"],
                series["lwd"],
            )
        axis.spines["top"].set_visible(True)
        axis.spines["right"].set_visible(True)
    for extra in range(ngraph, nr * nc):
        row = extra % nr
        col_i = extra // nr
        axes[row][col_i].set_visible(False)


def _draw_single(result: dict[str, Any], ax=None) -> None:
    import matplotlib.pyplot as plt

    if ax is None:
        fig, ax = plt.subplots(figsize=(6.2, 4.0))
        result["figure"] = fig
    else:
        result["axes"] = ax
    _apply_log(ax, result["log"])
    _set_ylim(ax, result["ylim"])
    if result["xlim"] is not None:
        ax.set_xlim(float(result["xlim"][0]), float(result["xlim"][1]))
    ax.set_xlabel(result["xlab"])
    ax.set_ylabel(result["ylab"])
    if result["main"]:
        ax.set_title(result["main"])
    for series in result["series"]:
        _draw_type(
            ax,
            series["x"],
            series["y"],
            series["type"] if isinstance(series["type"], str) else "l",
            series["col"],
            series["pch"],
            series["lty"],
            series["lwd"],
        )


def _plot_scatter(
    x,
    y,
    xlab,
    ylab,
    main,
    xlim,
    ylim,
    xy_labels,
    xy_lines,
    col,
    lty,
    lwd,
    pch,
    type,
    type_missing,
    xlab_missing,
    log,
    draw,
    ax,
    xname,
    yname,
):
    if _ncol(x) > 1 or _ncol(y) > 1:
        raise ValueError("scatter plots only for univariate zoo series")
    keys, xs, ys = _merge_keys(x, y, "inner")
    if xlab_missing:
        xlab = xname
    if ylab is None:
        ylab = yname
    if xlim is None:
        xlim = _finite_range(xs)
    else:
        xlim = [float(v) for v in _as_sequence(xlim)]
    if ylim is None:
        ylim = _finite_range(ys)
    else:
        ylim = [float(v) for v in _as_sequence(ylim)]
    if main is None:
        main = ""
    do_lab = xy_labels if isinstance(xy_labels, (bool, np.bool_)) else True
    if xy_lines is None:
        xy_lines = bool(do_lab)
    if do_lab:
        ptype = "n"
    elif type_missing:
        ptype = "p"
    else:
        ptype = type
    if do_lab:
        labels = list(xy_labels) if not isinstance(xy_labels, (bool, np.bool_)) else index2char(keys)
    else:
        labels = None
    linetype = ("c" if do_lab else "l") if xy_lines else None
    result = {
        "kind": "scatter",
        "x": xs,
        "y": ys,
        "ptype": ptype,
        "lines": bool(xy_lines),
        "linetype": linetype,
        "labels": labels,
        "xlim": xlim,
        "ylim": ylim,
        "col": col,
        "pch": pch,
        "lty": lty,
        "lwd": lwd,
        "xlab": xlab,
        "ylab": ylab,
        "main": main,
        "log": log,
        "index": keys,
    }
    if draw:
        import matplotlib.pyplot as plt

        if ax is None:
            fig, ax = plt.subplots(figsize=(6.2, 4.0))
            result["figure"] = fig
        _apply_log(ax, log)
        ax.set_xlim(float(xlim[0]), float(xlim[1]))
        ax.set_ylim(float(ylim[0]), float(ylim[1]))
        ax.set_xlabel(xlab)
        ax.set_ylabel(ylab)
        if main:
            ax.set_title(main)
        if ptype != "n":
            _draw_type(ax, xs, ys, ptype, col, pch, lty, lwd)
        if do_lab and labels is not None:
            colors = _colors(col, len(xs))
            for i, (xv, yv, lab) in enumerate(zip(xs, ys, labels)):
                if math.isfinite(xv) and math.isfinite(yv):
                    ax.text(xv, yv, str(lab), color=colors[i], fontsize=9)
        if xy_lines:
            _draw_type(ax, xs, ys, linetype or "l", col, pch, lty, lwd)
    return result


def _kind(y: Any) -> str:
    if isinstance(y, np.ndarray) and y.dtype == bool:
        return "logical"
    if isinstance(y, (list, tuple)) and len(y) > 0 and all(isinstance(item, (bool, np.bool_)) or item is None for item in y):
        if any(isinstance(item, (bool, np.bool_)) for item in y):
            return "logical"
    if isinstance(y, (bool, np.bool_)):
        return "logical"
    if isinstance(y, np.ndarray) and np.issubdtype(y.dtype, np.number):
        return "numeric"
    if isinstance(y, (list, tuple)) and all(item is None or _is_number(item) for item in y):
        return "numeric"
    if _is_number(y):
        return "numeric"
    return "character"


def _as_logical(y: Any) -> list[Any]:
    if isinstance(y, np.ndarray):
        return [None if _is_na(item) else bool(item) for item in y.reshape(-1)]
    if isinstance(y, (list, tuple)):
        return [None if _is_na(item) else bool(item) for item in y]
    return [None if _is_na(y) else bool(y)]


def _as_character(y: Any) -> list[Any]:
    if isinstance(y, np.ndarray):
        items = list(y.reshape(-1))
    elif isinstance(y, (list, tuple)):
        items = list(y)
    else:
        items = [y]
    out = []
    for item in items:
        if item is None or _is_na(item):
            out.append(None)
        else:
            out.append(str(item))
    return out


def _rle(values: list[Any]) -> tuple[list[Any], list[int]]:
    if not values:
        return [], []
    runs = [values[0]]
    lengths = [1]
    for item in values[1:]:
        if item == runs[-1]:
            lengths[-1] += 1
        else:
            runs.append(item)
            lengths.append(1)
    return runs, lengths


def _resolve_vertical(ybottom, ytop, height, ylog, ax):
    scale_log = ylog
    if scale_log is None:
        scale_log = bool(ax is not None and ax.get_yscale() == "log")
    if ybottom is None or ytop is None:
        if ybottom is None or height is None and ytop is None:
            if ax is None and (ybottom is None or ytop is None and height is None):
                if ybottom is None or (ytop is None and height is None):
                    raise ValueError("xblocks needs ybottom and ytop, or an open axes")
        if ax is not None and (ybottom is None or (ytop is None and height is None)):
            lo, hi = ax.get_ylim()
            if scale_log:
                lo, hi = math.log10(lo), math.log10(hi)
            if ybottom is None:
                ybottom = lo
            if height is None and ytop is None:
                height = hi - lo
    if ytop is None:
        ytop = float(ybottom) + float(height)
    ybottom = float(ybottom)
    ytop = float(ytop)
    if scale_log:
        ybottom = 10 ** ybottom
        ytop = 10 ** ytop
    return ybottom, ytop


def xblocks_default(
    x,
    y,
    col=None,
    border=None,
    ybottom=None,
    ytop=None,
    height=None,
    last_step=None,
    ylog=False,
    ax=None,
    draw=True,
    **kwargs,
):
    """xblocks.default. Returns the rect coordinates, and draws them when asked.

    ``ylog`` is par(\"ylog\"). The default vertical position is the open
    axes. The checks pass ``ybottom`` and ``ytop`` so the timed call is the
    block arithmetic.
    """
    if callable(y):
        y = y(x)
    x_vals = [float(item) if not _is_na(item) else float("nan") for item in np.asarray(x, dtype=float).reshape(-1)]
    if len(x_vals) == 0:
        return None
    if _is_unsorted(x_vals):
        raise ValueError("'x' should be ordered (increasing)")
    if last_step is None:
        last_step = _r_median(_diff(_tail(x_vals, 6)))
    if _is_na(last_step):
        last_step = 0.0
    last_step = float(last_step)

    kind = _kind(y)
    if kind == "numeric":
        raw = _as_sequence(y) if not isinstance(y, np.ndarray) else list(np.asarray(y, dtype=float).reshape(-1))
        logical = [not _is_na(item) for item in raw]
        kind = "logical"
        prepared = logical
    elif kind == "logical":
        prepared = _as_logical(y)
    else:
        prepared = _as_character(y)

    naval = False if kind == "logical" else ""
    cleaned = [naval if item is None or _is_na(item) else item for item in prepared]
    runs, lengths = _rle(cleaned)
    block_col: list[Any] = [None if run == naval else run for run in runs]
    if kind == "logical" and col is None:
        col = _PALETTE[0]
    if col is not None and _element_length(col) > 0:
        colors = _as_sequence(col)
        if colors and all(isinstance(item, str) or item is None for item in colors):
            colors = [None if item == "" else item for item in colors]
        ok = [i for i, item in enumerate(block_col) if item is not None and not _is_na(item)]
        for pos, color_i in enumerate(ok):
            block_col[color_i] = colors[pos % len(colors)]

    bounds = [1]
    total = 1
    for length in lengths:
        total += length
        bounds.append(total)
    idx_start = bounds[:-1]
    idx_end = bounds[1:]
    if idx_end:
        idx_end[-1] = len(prepared)
    left = [x_vals[i - 1] for i in idx_start]
    right = [x_vals[i - 1] for i in idx_end]
    if right:
        right[-1] = right[-1] + last_step
    bottom, top = _resolve_vertical(ybottom, ytop, height, ylog, ax)
    record = {
        "empty": False,
        "left": left,
        "right": right,
        "bottom": bottom,
        "top": top,
        "col": block_col,
        "border": border,
    }
    if draw:
        _draw_blocks(record, ax=ax)
    return record


def _is_unsorted(values: list[float]) -> bool:
    clean = [value for value in values if not math.isnan(value)]
    return any(b < a for a, b in zip(clean, clean[1:]))


def _tail(values: list[float], n: int = 6) -> list[float]:
    if n >= len(values):
        return list(values)
    return list(values[-n:])


def _diff(values: list[float]) -> list[float]:
    return [values[i + 1] - values[i] for i in range(len(values) - 1)]


def _r_median(values: list[float]) -> float:
    if any(math.isnan(value) for value in values):
        return float("nan")
    if not values:
        return float("nan")
    ordered = sorted(values)
    count = len(ordered)
    mid = count // 2
    if count % 2:
        return float(ordered[mid])
    return (float(ordered[mid - 1]) + float(ordered[mid])) / 2.0


def _draw_blocks(record: dict[str, Any], ax=None) -> None:
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle

    created = False
    if ax is None:
        fig, ax = plt.subplots(figsize=(6.2, 4.0))
        record["figure"] = fig
        created = True
    record["axes"] = ax
    bottom = record["bottom"]
    height = record["top"] - record["bottom"]
    for x0, x1, color in zip(record["left"], record["right"], record["col"]):
        if not math.isfinite(x0) or not math.isfinite(x1):
            continue
        face = "none" if color is None or _is_na(color) else _color(color) if _is_number(color) else color
        edge = "none" if record["border"] is None or _is_na(record["border"]) else record["border"]
        ax.add_patch(
            Rectangle(
                (x0, bottom),
                x1 - x0,
                height,
                facecolor=face,
                edgecolor=edge,
                linewidth=0.8,
            )
        )
    if created:
        finite_left = [v for v in record["left"] if math.isfinite(v)]
        finite_right = [v for v in record["right"] if math.isfinite(v)]
        if finite_left and finite_right:
            span = max(finite_right) - min(finite_left)
            pad = 0.04 * span if span else 0.5
            ax.set_xlim(min(finite_left) - pad, max(finite_right) + pad)
        ax.set_ylim(bottom, record["top"])
    ax.set_xlabel("Index")


def xblocks_zoo(x, y=None, **kwargs):
    """xblocks.zoo. Blocks follow index(x); y defaults to the series itself."""
    if y is None:
        y = x
    if not callable(y):
        y = _core(y)
    return xblocks_default(_index_array(x), y, **kwargs)


def xblocks(x, y=None, **kwargs):
    """xblocks. A zoo series uses the zoo method. Anything else uses the default."""
    if isinstance(x, Zoo):
        if y is None:
            y = x
        return xblocks_zoo(x, y, **kwargs)
    if y is None:
        raise TypeError('argument "y" is missing, with no default')
    return xblocks_default(x, y, **kwargs)
