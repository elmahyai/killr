"""Plot methods for Lorenz curves and Pen's parade.

Ports ``plot.Lc``, ``lines.Lc``, ``plot.theorLc``, ``lines.theorLc``, and
``Pen`` from ineq 0.2-13. A Lorenz curve is a line with the diagonal of
equality. Pen's parade is a step line, or histogram-like bars when
segments are requested. Matplotlib draws both. The graphics and grDevices
packages are not translated.
"""

from __future__ import annotations

import numpy as np

_GRID = np.arange(1001, dtype=np.float64) * 0.001


def plot_lc(
    x,
    general=False,
    lwd=2,
    xlabel="p",
    ylabel="L(p)",
    main="Lorenz curve",
    ax=None,
):
    """Draw an empirical Lorenz curve and the diagonal through its top.

    ``general`` selects ``L.general`` instead of ``L``. The diagonal runs
    from (0, 0) to (1, max(y)), which is ``abline(0, max(L))`` in R.
    Returns the coordinates that were drawn.
    """
    p, y = _lc_coordinates(x, general)
    axes = _axes(ax, fresh=True)
    axes.plot(p, y, color="black", linewidth=lwd)
    top = float(np.max(y))
    axes.plot([0.0, 1.0], [0.0, top], color="black", linewidth=1)
    _frame_curve(axes, p, y, xlabel, ylabel, main)
    return {"p": p, "y": y}


def lines_lc(x, general=False, lwd=2, ax=None, **style):
    """Add an empirical Lorenz curve to the current axes.

    Unlike ``plot_lc``, this does not draw the diagonal. ``style`` is
    passed through to the line, so ``color`` overrides the default black.
    Returns the same coordinate dict as ``plot_lc``.
    """
    p, y = _lc_coordinates(x, general)
    axes = _axes(ax, fresh=False)
    options = {"color": "black", "linewidth": lwd}
    options.update(style)
    axes.plot(p, y, **options)
    return {"p": p, "y": y}


def plot_theor_lc(fn, parameter=None, xlabel="p", ylabel="L(p)", lwd=2, ax=None):
    """Draw a theoretical Lorenz curve on the unit grid and the diagonal.

    The grid is ``(0:1000) * 0.001`` (1001 points). ``parameter is None``
    calls ``fn(grid)``. Any other value calls ``fn(grid, parameter=parameter)``,
    which is how ``lc_lognorm`` and the other distribution curves are used.
    A curve built by ``theorLc`` already holds its parameters, so leave
    ``parameter`` unset. The diagonal is the unit line ``abline(0, 1)``.
    """
    p, y = _theor_coordinates(fn, parameter)
    axes = _axes(ax, fresh=True)
    axes.plot(p, y, color="black", linewidth=lwd)
    axes.plot([0.0, 1.0], [0.0, 1.0], color="black", linewidth=1)
    _frame_curve(axes, p, y, xlabel, ylabel, main=None)
    return {"p": p, "y": y}


def lines_theor_lc(fn, parameter=None, lwd=2, color="C1", ax=None):
    """Add a theoretical Lorenz curve to the current axes.

    Uses the same grid and calling rule as ``plot_theor_lc``. The default
    color is Matplotlib's second cycle color, standing in for R's ``col=2``.
    """
    p, y = _theor_coordinates(fn, parameter)
    axes = _axes(ax, fresh=False)
    axes.plot(p, y, color=color, linewidth=lwd)
    return {"p": p, "y": y}


def Pen(
    x,
    n=None,
    group=None,
    scaled=True,
    abline=True,
    add=False,
    segments=None,
    main="Pen's Parade",
    ylabel=None,
    xlabel=None,
    color=None,
    lwd=None,
    fill=None,
    ax=None,
):
    """Draw Pen's parade of ``x``.

    Missing values in ``x`` are dropped, and ``n`` and ``group`` stay
    aligned with the values that remain. The remaining observations are
    ordered from smallest to largest. When ``scaled`` is true, heights are
    divided by the unweighted mean of those ordered values. The returned
    ``p`` is the cumulative population share, starting at 0. ``y`` is the
    ordered heights. ``mean`` is the mean of those heights, which is the
    height of the dotted horizontal line.

    A grouping variable turns on histogram-like bars unless ``segments``
    is set explicitly. Each group is filled with a Matplotlib gray. Without
    groups or a fill, the parade is a thick blue step. With bars or a fill,
    the outline is a thin black line.
    """
    values, weights, labels, permutation = _pen_inputs(x, n, group)
    if labels is not None:
        if segments is None:
            segments = True
        if fill is None and segments:
            fill = _group_grays(labels)
    elif segments is None:
        segments = False

    if color is None:
        color = "black" if segments or fill is not None else "blue"
    if lwd is None:
        lwd = 1 if segments or fill is not None else 2
    if segments:
        color = _recycle_ordered(color, permutation)
        fill = _recycle_ordered(fill, permutation)

    values = values[permutation]
    weights = weights[permutation]
    if scaled:
        values = values / np.mean(values)
    mean_line = float(np.mean(values))
    shares = _cumulative_shares(weights)

    if ylabel is None:
        ylabel = r"$x_{(i)}/\bar{x}$" if scaled else r"$x_{(i)}$"
    if xlabel is None:
        xlabel = _pen_xlabel(weights)

    axes = _axes(ax, fresh=not add)
    if add:
        axes.autoscale(False)
    if segments:
        _draw_bars(axes, shares, values, color, fill, lwd)
    else:
        _draw_step(axes, shares, values, color, fill, lwd)
    if not add:
        _frame_parade(axes, values, xlabel, ylabel, main)
    if abline and not add:
        axes.axhline(mean_line, color="black", linestyle=":", linewidth=1)
    return {"p": shares, "y": values, "mean": mean_line}


def _lc_coordinates(x, general):
    p = np.asarray(x["p"], dtype=np.float64).reshape(-1)
    key = "L.general" if general else "L"
    y = np.asarray(x[key], dtype=np.float64).reshape(-1)
    return p, y


def _theor_coordinates(fn, parameter):
    grid = _GRID.copy()
    if parameter is None:
        values = fn(grid)
    else:
        values = fn(grid, parameter=parameter)
    return grid, np.asarray(values, dtype=np.float64).reshape(-1)


def _pen_inputs(x, n, group):
    values = np.asarray(x, dtype=np.float64).reshape(-1)
    if n is None:
        weights = np.ones(values.shape[0], dtype=np.float64)
    else:
        weights = np.asarray(n, dtype=np.float64).reshape(-1)
        if weights.shape[0] != values.shape[0]:
            raise ValueError("n must be the same length as x")
    keep = ~np.isnan(values)
    values = values[keep]
    weights = weights[keep]
    labels = None
    if group is not None:
        labels = np.asarray(group).reshape(-1)
        if labels.shape[0] != keep.shape[0]:
            raise ValueError("group must be the same length as x")
        labels = labels[keep]
    permutation = np.argsort(values, kind="mergesort")
    return values, weights, labels, permutation


def _cumulative_shares(weights):
    total = np.sum(weights)
    steps = np.concatenate((np.array([0.0], dtype=np.float64), weights))
    return np.cumsum(steps) / total


def _pen_xlabel(weights):
    ones = np.ones(weights.shape[0], dtype=np.float64)
    if np.allclose(weights, ones, rtol=1.5e-8, atol=1.5e-8):
        return r"$i/n$"
    return r"$\sum_i (n_{(i)}/n)$"


def _group_grays(labels):
    """Gray for each observation, in the order of ``labels``.

    Levels follow R's ``as.factor``: sorted unique labels. The gray levels
    run from 0.3 to 0.9 through the same power spacing as ``grey()`` in
    ``Pen``.
    """
    text = np.array([_level_name(value) for value in labels])
    levels = sorted(set(text.tolist()))
    count = len(levels)
    compressed = np.linspace(0.3 ** 2.2, 0.9 ** 2.2, count)
    shades = compressed ** (1.0 / 2.2)
    index = {level: position for position, level in enumerate(levels)}
    return [(_shade(shades[index[name]])) for name in text]


def _level_name(value):
    if isinstance(value, (bool, np.bool_)):
        return str(value)
    if isinstance(value, (int, np.integer)):
        return str(int(value))
    if isinstance(value, (float, np.floating)) and float(value).is_integer():
        return str(int(value))
    return str(value)


def _shade(level):
    return f"{float(level):.8f}"


def _recycle_ordered(value, permutation):
    """Recycle a color and reorder it with the data, as ``Pen`` does for bars.

    A single color is left unchanged. ``permutation`` is the argsort of the
    unsorted observations, so a vector supplied in input order follows the
    ordered parade.
    """
    if value is None or _is_single_color(value):
        return value
    recycled = [value[i % len(value)] for i in range(permutation.shape[0])]
    return [recycled[int(i)] for i in permutation]


def _is_single_color(value):
    if isinstance(value, (str, bytes, int, float, np.floating, np.integer)):
        return True
    if isinstance(value, tuple) and 3 <= len(value) <= 4:
        return all(isinstance(channel, (int, float, np.floating)) for channel in value)
    return False


def _draw_bars(axes, shares, heights, color, fill, lwd):
    widths = np.diff(shares)
    face = "none" if fill is None else fill
    edge = "black" if color is None else color
    axes.bar(
        shares[:-1],
        heights,
        width=widths,
        align="edge",
        color=face,
        edgecolor=edge,
        linewidth=lwd,
    )


def _draw_step(axes, shares, heights, color, fill, lwd):
    abscissa = np.concatenate((np.repeat(shares[:-1], 2), shares[-1:]))
    ordinate = np.concatenate((np.array([0.0], dtype=np.float64), np.repeat(heights, 2)))
    if fill is not None:
        face = fill[0] if not _is_single_color(fill) else fill
        closed_x = np.concatenate((abscissa, np.array([1.0, 0.0])))
        closed_y = np.concatenate((ordinate, np.array([0.0, 0.0])))
        axes.fill(closed_x, closed_y, facecolor=face, edgecolor=color, linewidth=lwd)
    axes.plot(abscissa, ordinate, color=color, linewidth=lwd)


def _frame_curve(axes, p, y, xlabel, ylabel, main):
    finite_x = p[np.isfinite(p)]
    finite_y = y[np.isfinite(y)]
    axes.set_xlim(_span(finite_x))
    axes.set_ylim(_span(finite_y))
    axes.margins(0)
    axes.set_xlabel(xlabel)
    axes.set_ylabel(ylabel)
    if main is not None:
        axes.set_title(main)
    axes.autoscale(False)


def _frame_parade(axes, heights, xlabel, ylabel, main):
    top = float(np.max(heights)) if heights.size else 1.0
    if top == 0.0:
        top = 1.0
    axes.set_xlim(0.0, 1.0)
    axes.set_ylim(0.0, top)
    axes.margins(0)
    axes.set_xlabel(xlabel)
    axes.set_ylabel(ylabel)
    axes.set_title(main)
    axes.autoscale(False)


def _span(values):
    low = float(np.min(values))
    high = float(np.max(values))
    if low == high:
        high = low + 1.0
    return low, high


def _axes(ax, fresh):
    plt = _pyplot()
    if ax is not None:
        return ax
    if fresh:
        _, created = plt.subplots()
        return created
    return plt.gca()


def _pyplot():
    import matplotlib.pyplot as plt

    return plt
