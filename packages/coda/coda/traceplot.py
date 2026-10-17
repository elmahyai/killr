"""Trace plots of MCMC output.

Translated from coda 0.19-4.1 ``traceplot`` in ``R/output.R``.
Each variable is one Matplotlib panel, and each chain is one line.
``smooth=True`` draws ``stats::lowess`` through each chain.
"""

from __future__ import annotations

import numpy as np

from coda.mcmc_list import mcmc_list
from coda.nchain import nchain
from coda.varnames import varnames

_PALETTE = (
    "#000000",
    "#DF536B",
    "#61D04F",
    "#2297E6",
    "#28E2E5",
    "#CD0BBC",
    "#F5C710",
    "#9E9E9E",
)

_LTY = {
    1: "solid",
    2: "dashed",
    3: "dotted",
    4: "dashdot",
    5: (0, (8, 2)),
    6: (0, (3, 1, 1, 1, 3, 1)),
}


def traceplot(
    x,
    smooth=False,
    col=None,
    type="l",
    xlab="Iterations",
    ylab="",
    **kwargs,
):
    """Plot iterations against sampled values, one panel per variable.

    ``x`` is an ``Mcmc`` chain or an ``McmcList``. Chains are columns of
    each panel. A title ``Trace of <name>`` is added when variable names
    exist and ``main`` was not passed.
    """
    has_main = "main" in kwargs
    main = kwargs.get("main")
    lty = kwargs.get("lty", (1, 2, 3, 4, 5))
    obj = mcmc_list(x)
    names = varnames(obj)
    n_var = _nvar(obj)
    n_chains = int(nchain(obj))
    xp = _iteration_time(obj.chains[0])
    colors = [_color(item) for item in _recycle(_as_list(col, list(range(1, 7))), n_chains)]
    styles = [_linestyle(item) for item in _recycle(_as_list(lty, [1, 2, 3, 4, 5]), n_chains)]
    panels = []
    for index in range(n_var):
        if n_var > 1:
            columns = [_column(chain, index) for chain in obj.chains]
        else:
            columns = [_series(chain) for chain in obj.chains]
        y = np.column_stack(columns) if columns else np.zeros((xp.size, 0))
        if names is not None and not has_main:
            title = f"Trace of {names[index]}"
        elif has_main:
            title = None if main is None else str(main)
        else:
            title = None
        smooth_lines = []
        if smooth:
            for chain_index in range(y.shape[1]):
                smooth_x, smooth_y = _lowess(xp, y[:, chain_index])
                smooth_lines.append((smooth_x, smooth_y))
        panels.append(
            {
                "x": xp,
                "y": y,
                "title": title,
                "xlab": xlab,
                "ylab": ylab,
                "colors": colors,
                "lty": styles,
                "smooth": smooth_lines,
            }
        )
    figure = _draw(panels, type)
    return {"panels": panels, "figure": figure}


def proof_values(result):
    """Flatten plotted coordinates and titles for a check against R."""
    values = []
    for panel in result["panels"]:
        values.extend(float(item) for item in np.asarray(panel["x"], dtype=np.float64))
        values.extend(
            float(item) for item in np.ravel(np.asarray(panel["y"], dtype=np.float64), order="F")
        )
        title = panel["title"]
        if title is None:
            values.append(0.0)
        else:
            values.append(-1.0)
            values.append(float(len(title)))
            values.extend(float(ord(char)) for char in title)
        for _smooth_x, smooth_y in panel["smooth"]:
            values.extend(float(item) for item in np.asarray(smooth_y, dtype=np.float64))
    return values


def _nvar(obj):
    data = np.asarray(obj.chains[0].data)
    if data.ndim >= 2:
        return int(data.shape[1])
    return 1


def _series(chain):
    data = np.asarray(chain.data, dtype=np.float64)
    if data.ndim <= 1:
        return data.reshape(-1)
    return np.ascontiguousarray(data[:, 0])


def _column(chain, index):
    data = np.asarray(chain.data, dtype=np.float64)
    if data.ndim <= 1:
        return data.reshape(-1)
    return np.ascontiguousarray(data[:, index])


def _iteration_time(chain):
    start = float(chain.start)
    end = float(chain.end)
    step = float(chain.thin)
    count = int(np.floor((end - start) / step + 1e-10)) + 1
    return start + step * np.arange(count, dtype=np.float64)


def _as_list(value, default):
    if value is None:
        value = default
    if isinstance(value, (str, bytes)):
        return [value]
    if isinstance(value, (int, float, np.integer, np.floating)):
        return [value]
    return list(value)


def _recycle(values, count):
    if count <= 0 or not values:
        return []
    return [values[index % len(values)] for index in range(count)]


def _color(value):
    if isinstance(value, (int, np.integer)):
        index = int(value)
        if index <= 0:
            return "#00000000"
        return _PALETTE[(index - 1) % len(_PALETTE)]
    return value


def _linestyle(value):
    if isinstance(value, (int, np.integer)):
        return _LTY.get(int(value), "solid")
    return value


def _draw(panels, type):
    import matplotlib

    matplotlib.use("Agg", force=False)
    import matplotlib.pyplot as plt

    count = max(len(panels), 1)
    figure, axes = plt.subplots(
        count,
        1,
        figsize=(7, max(3.0, 3.0 * count)),
        squeeze=False,
    )
    for axis, panel in zip(axes[:, 0], panels):
        y = np.asarray(panel["y"], dtype=np.float64)
        x = np.asarray(panel["x"], dtype=np.float64)
        for chain_index in range(y.shape[1]):
            _draw_series(
                axis,
                x,
                y[:, chain_index],
                color=panel["colors"][chain_index],
                linestyle=panel["lty"][chain_index],
                type=type,
            )
        for chain_index, (smooth_x, smooth_y) in enumerate(panel["smooth"]):
            axis.plot(
                np.asarray(smooth_x, dtype=np.float64),
                np.asarray(smooth_y, dtype=np.float64),
                color=panel["colors"][chain_index],
                linestyle="solid",
                linewidth=1.0,
            )
        axis.set_xlabel(panel["xlab"])
        axis.set_ylabel(panel["ylab"])
        axis.margins(x=0.04, y=0.04)
        if panel["title"] is not None:
            axis.set_title(panel["title"])
    figure.tight_layout()
    return figure


def _draw_series(axis, x, y, color, linestyle, type):
    marker = "o" if type in {"p", "b", "o"} else None
    line = type not in {"p", "n", "h"}
    if type == "h":
        axis.vlines(x, 0.0, y, colors=color, linewidth=1.0)
        return
    if type in {"s", "S"}:
        axis.step(x, y, where="pre" if type == "S" else "post", color=color, linestyle=linestyle)
        return
    if type == "n":
        return
    axis.plot(
        x,
        y,
        color=color,
        linestyle=linestyle if line else "none",
        marker=marker,
        linewidth=1.0,
        markersize=3,
    )


def _lowess(x, y, f=2.0 / 3.0, nsteps=3, delta=None):
    """Cleveland robust locally weighted regression, matching ``stats::lowess``."""
    x = np.asarray(x, dtype=np.float64).reshape(-1)
    y = np.asarray(y, dtype=np.float64).reshape(-1)
    order = np.argsort(x, kind="mergesort")
    x = x[order].copy()
    y = y[order].copy()
    n = int(x.size)
    if delta is None:
        span = float(x[-1] - x[0]) if n else 0.0
        delta = 0.01 * span
    ys = np.empty(n, dtype=np.float64)
    if n == 0:
        return x, ys
    if n < 2:
        ys[0] = y[0]
        return x, ys
    ns = max(2, min(n, int(f * n + 1e-7)))
    rw = np.ones(n, dtype=np.float64)
    weights = np.zeros(n, dtype=np.float64)
    for iteration in range(int(nsteps) + 1):
        nleft = 0
        nright = ns - 1
        last = -1
        index = 0
        while True:
            while nright < n - 1:
                left_gap = x[index] - x[nleft]
                right_gap = x[nright + 1] - x[index]
                if left_gap <= right_gap:
                    break
                nleft += 1
                nright += 1
            fitted = _lowest(
                x,
                y,
                float(x[index]),
                nleft,
                nright,
                weights,
                rw,
                iteration > 0,
            )
            ys[index] = y[index] if fitted is None else fitted
            if last < index - 1:
                denom = x[index] - x[last]
                for gap in range(last + 1, index):
                    alpha = (x[gap] - x[last]) / denom
                    ys[gap] = alpha * ys[index] + (1.0 - alpha) * ys[last]
            last = index
            cut = x[last] + delta
            index = last + 1
            while index < n:
                if x[index] > cut:
                    break
                if x[index] == x[last]:
                    ys[index] = ys[last]
                    last = index
                index += 1
            index = max(last + 1, index - 1)
            if last >= n - 1:
                break
        residual = y - ys
        if iteration == int(nsteps):
            break
        cmad = _cmad(residual)
        c9 = 0.999 * cmad
        c1 = 0.001 * cmad
        for point in range(n):
            magnitude = abs(float(residual[point]))
            if magnitude <= c1:
                rw[point] = 1.0
            elif magnitude <= c9:
                ratio = magnitude / cmad
                rw[point] = (1.0 - ratio ** 2) ** 2
            else:
                rw[point] = 0.0
    return x, ys


def _cmad(residual):
    magnitude = np.abs(np.asarray(residual, dtype=np.float64))
    n = int(magnitude.size)
    m1 = n // 2
    ordered = np.partition(magnitude, m1)
    if n % 2 == 0:
        left = np.partition(ordered[:m1], m1 - 1)
        return 3.0 * (float(left[m1 - 1]) + float(ordered[m1]))
    return 6.0 * float(ordered[m1])


def _lowest(x, y, xs, nleft, nright, weights, rw, userw):
    h = max(xs - float(x[nleft]), float(x[nright]) - xs)
    h9 = 0.999 * h
    h1 = 0.001 * h
    total = 0.0
    for point in range(nleft, nright + 1):
        distance = abs(float(x[point]) - xs)
        weight = 0.0
        if distance <= h9:
            if distance <= h1:
                weight = 1.0
            else:
                weight = (1.0 - (distance / h) ** 3) ** 3
            if userw:
                weight *= float(rw[point])
            total += weight
        weights[point] = weight
    if total <= 0.0:
        return None
    for point in range(nleft, nright + 1):
        weights[point] /= total
    if h > 0.0:
        center = 0.0
        for point in range(nleft, nright + 1):
            center += float(weights[point]) * float(x[point])
        slope = xs - center
        square = 0.0
        for point in range(nleft, nright + 1):
            square += float(weights[point]) * (float(x[point]) - center) ** 2
        span = float(x[-1] - x[0])
        if square ** 0.5 > 0.001 * span:
            slope /= square
            for point in range(nleft, nright + 1):
                weights[point] *= slope * (float(x[point]) - center) + 1.0
    fitted = 0.0
    for point in range(nleft, nright + 1):
        fitted += float(weights[point]) * float(y[point])
    return fitted
