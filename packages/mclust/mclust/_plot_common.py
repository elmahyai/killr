"""Shared drawing helpers for the mclust plot translations.

The R plot functions draw through base graphics. This module gives the
Python translations the same primitives with the same arguments, and a
``Canvas`` that writes every primitive to a log in R's call order. The
proofs compare that log with the log R writes through ``trace()`` on
``plot.window``, ``plot.xy``, ``image.default``, ``contour.default``,
``matplot``, ``plot.histogram`` and ``bxp``.

Matplotlib draws the figure. The logged numbers are the data, not the pixels.
"""

from __future__ import annotations

import math
from typing import Any, Sequence

from mclust.mclust_options import mclust_options

import numpy as np

__all__ = [
    "Canvas",
    "R_COLOR_HEX",
    "boxplot_stats",
    "class_colors",
    "class_symbols",
    "extendrange",
    "fivenum",
    "hist_density",
    "nclass_sturges",
    "pretty",
    "usr_r",
]

DBL_EPS = 2.220446049250313e-16
DBL_MIN = 2.2250738585072014e-308

# R colour names used by mclust.options(), with the hex values R reports.
R_COLOR_HEX = {
    "dodgerblue2": "#1C86EE",
    "red3": "#CD0000",
    "green3": "#00CD00",
    "slateblue": "#6A5ACD",
    "darkorange": "#FF8C00",
    "skyblue1": "#87CEFF",
    "violetred4": "#8B2252",
    "forestgreen": "#228B22",
    "steelblue4": "#36648B",
    "slategrey": "#708090",
    "brown": "#A52A2A",
    "black": "#000000",
    "darkseagreen": "#8FBC8F",
    "darkgoldenrod3": "#CD950C",
    "olivedrab": "#6B8E23",
    "royalblue": "#4169E1",
    "tomato4": "#8B3626",
    "cyan2": "#00EEEE",
    "springgreen2": "#00EE76",
    "gray": "#BEBEBE",
    "grey": "#BEBEBE",
    "darkgray": "#A9A9A9",
    "red": "#FF0000",
    "blue": "#0000FF",
    "green": "#00FF00",
    "white": "#FFFFFF",
}

# R pch codes to Matplotlib markers. Only the drawn shape depends on this.
_PCH_MARKER = {
    0: "s", 1: "o", 2: "^", 3: "+", 4: "x", 5: "D", 6: "v", 7: "x", 8: "*",
    9: "D", 10: "o", 11: "x", 12: "s", 13: "o", 14: "^", 15: "s", 16: "o",
    17: "^", 18: "D", 19: "o", 20: "o",
}


def _hex(color: str) -> str:
    return R_COLOR_HEX.get(color, color)


def _marker(pch: Any) -> str:
    if isinstance(pch, str):
        return "|" if pch == "|" else "o"
    return _PCH_MARKER.get(int(pch), "o")


def usr_r(lim: Sequence[float], xaxs: str = "r") -> tuple[float, float]:
    """Return the axis limits R draws for a data range.

    With ``xaxs = "r"`` (the default) R extends the range by 4% on each side.
    With ``"i"`` the limits are the range itself.
    """
    lo, hi = float(lim[0]), float(lim[1])
    if lo == hi:
        # R's GScale: a zero-width range is opened first, then extended as usual.
        if lo == 0.0:
            lo, hi = -1.0, 1.0
        else:
            temp = 0.4 * abs(lo)
            lo, hi = lo - temp, hi + temp
    if xaxs == "i":
        return lo, hi
    d = hi - lo
    return lo - 0.04 * d, hi + 0.04 * d


def extendrange(x: Any, f: float = 0.05) -> np.ndarray:
    """``grDevices::extendrange(x, f = 0.05)``: the range widened by ``f`` on each side."""
    arr = np.asarray(x, dtype=float).ravel()
    lo, hi = float(np.nanmin(arr)), float(np.nanmax(arr))
    d = hi - lo
    return np.array([lo - f * d, hi + f * d])


def nclass_sturges(x: Any) -> int:
    """``grDevices::nclass.Sturges``."""
    n = int(np.asarray(x).size)
    return int(math.ceil(math.log2(n) + 1))


def pretty(x: Any, n: int = 5, min_n: int | None = None) -> np.ndarray:
    """``base::pretty(x, n, min.n)``; ``min.n`` defaults to ``n %/% 3`` as in R."""
    arr = np.asarray(x, dtype=float).ravel()
    lo, up = float(np.nanmin(arr)), float(np.nanmax(arr))
    if min_n is None:
        min_n = n // 3
    shrink = 0.75
    h = 1.5
    h5 = 0.5 + 1.5 * h
    ndiv = n
    dx = up - lo
    if dx == 0 and up == 0:
        cell = 1.0
        i_small = True
    else:
        cell = max(abs(lo), abs(up))
        u = 1.0 + (1.0 / (1.0 + h) if h5 >= 1.5 * h + 0.5 else 1.5 / (1.0 + h5))
        u *= max(1, ndiv) * DBL_EPS
        i_small = dx < cell * u * 3
    if i_small:
        if cell > 10:
            cell = 9 + cell / 10
        cell *= shrink
        if min_n > 1:
            cell /= min_n
    else:
        cell = dx
        if ndiv > 1:
            cell /= ndiv
    if cell < 20 * DBL_MIN:
        cell = 20 * DBL_MIN
    base = 10.0 ** math.floor(math.log10(cell))
    unit = base
    if 2 * base - cell < h * (cell - unit):
        unit = 2 * base
        if 5 * base - cell < h5 * (cell - unit):
            unit = 5 * base
            if 10 * base - cell < h * (cell - unit):
                unit = 10 * base
    ns = math.floor(lo / unit + 1e-7)
    nu = math.ceil(up / unit - 1e-7)
    eps = 1e-10
    while ns * unit > lo + eps * unit:
        ns -= 1
    while nu * unit < up - eps * unit:
        nu += 1
    k = int(0.5 + nu - ns)
    if k < min_n:
        k = min_n - k
        if ns >= 0:
            nu += k // 2
            ns -= k // 2 + k % 2
        else:
            ns -= k // 2
            nu += k // 2 + k % 2
        ndiv = min_n
    else:
        ndiv = k
    lo_u, up_u = ns * unit, nu * unit
    s = np.linspace(lo_u, up_u, ndiv + 1)
    delta = abs(up_u - lo_u) / ndiv if ndiv else 0.0
    if ndiv:
        small = np.abs(s) < 1e-14 * delta
        s[small] = 0.0
    return s


def hist_density(x: Any, breaks: Any) -> dict[str, np.ndarray]:
    """``hist(x, breaks, plot = FALSE)`` with ``right = TRUE`` and ``include.lowest = TRUE``."""
    values = np.asarray(x, dtype=float).ravel()
    b = np.asarray(breaks, dtype=float).ravel()
    nb = len(b) - 1
    counts = np.zeros(nb, dtype=float)
    for v in values:
        for i in range(nb):
            if (v > b[i] or (i == 0 and v == b[i])) and v <= b[i + 1]:
                counts[i] += 1
                break
    density = counts / (values.size * np.diff(b))
    return {"breaks": b, "counts": counts, "density": density}


def fivenum(x: Any) -> np.ndarray:
    """Tukey's five-number summary, as ``stats::fivenum``."""
    arr = np.sort(np.asarray(x, dtype=float).ravel())
    arr = arr[~np.isnan(arr)]
    n = arr.size
    if n == 0:
        return np.full(5, np.nan)
    n4 = math.floor((n + 3) / 2) / 2
    d = np.array([1, n4, (n + 1) / 2, n + 1 - n4, n])
    return 0.5 * (arr[np.floor(d).astype(int) - 1] + arr[np.ceil(d).astype(int) - 1])


def boxplot_stats(x: Any, coef: float = 1.5) -> np.ndarray:
    """``grDevices::boxplot.stats(x)$stats``: whiskers at the last point inside ``coef`` IQRs."""
    arr = np.asarray(x, dtype=float).ravel()
    arr = arr[~np.isnan(arr)]
    stats = fivenum(arr)
    if coef > 0:
        iqr = stats[3] - stats[1]
        out = (arr < stats[1] - coef * iqr) | (arr > stats[3] + coef * iqr)
        inside = arr[~out]
        if inside.size:
            stats[0] = inside.min()
            stats[4] = inside.max()
    return stats


def class_symbols(levels: int, options: Sequence[Any]) -> list[Any]:
    """The ``symbols`` default used by ``clPairs`` and ``mclust2Dplot``."""
    if levels <= len(options):
        return list(options[:levels])
    return [16] * levels


def class_colors(levels: int, options: Sequence[str]) -> list[str]:
    """The ``colors`` default: the first ``levels`` entries of ``classPlotColors``."""
    if levels <= len(options):
        return list(options[:levels])
    return ["black"] * levels


class Canvas:
    """Draws onto Matplotlib axes and logs each R primitive.

    Every method returns after recording the call, so the log is the same
    sequence R produces. ``log`` holds ``(tag, fields)`` tuples. The proof
    writes them out in the same format R does.
    """

    def __init__(self) -> None:
        self.log: list[tuple[str, list[Any]]] = []

    def window(self, ax: Any, xlim: Sequence[float], ylim: Sequence[float],
               xaxs: str = "r", yaxs: str = "r") -> tuple[float, float, float, float]:
        """``plot.window``: set the axis limits and log the usr box."""
        ux = usr_r(xlim, xaxs)
        uy = usr_r(ylim, yaxs)
        if ax is not None:
            ax.set_xlim(*ux)
            ax.set_ylim(*uy)
        usr = (ux[0], ux[1], uy[0], uy[1])
        self.log.append(("W", [usr]))
        return usr

    def xy(self, ax: Any, x: Any, y: Any, type: str = "p", pch: Any = None,
           col: Any = "black") -> None:
        """``plot.xy``: the call behind ``plot``, ``points`` and ``lines``.

        ``type = "n"`` draws nothing and is not logged, as in R. ``pch`` is
        ``None`` when the R call did not pass one.
        """
        if type == "n":
            return
        xs = np.asarray(x, dtype=float).ravel()
        ys = np.asarray(y, dtype=float).ravel()
        pch_list = None if pch is None else (
            list(pch) if isinstance(pch, (list, tuple, np.ndarray)) else [pch])
        col_list = list(col) if isinstance(col, (list, tuple, np.ndarray)) else [col]
        self.log.append(("P", [xs, ys, [type],
                               pch_list if pch_list is not None else ["NA"], col_list]))
        if ax is None or xs.size == 0:
            return
        n = xs.size
        col_n = [col_list[i % len(col_list)] for i in range(n)]
        if type in ("l", "b"):
            ax.plot(xs, ys, color=_hex(col_n[0]), linestyle="-")
        if type in ("p", "b"):
            pch_n = [pch_list[i % len(pch_list)] for i in range(n)] if pch_list else [1] * n
            for i in range(n):
                ax.scatter([xs[i]], [ys[i]], marker=_marker(pch_n[i]), s=18,
                           c=[_hex(col_n[i])], linewidths=1.0)

    def points(self, ax: Any, x: Any, y: Any, pch: Any = 1, col: Any = "black") -> None:
        """``points``: ``xy`` with type ``"p"``."""
        self.xy(ax, x, y, type="p", pch=pch, col=col)

    def image(self, ax: Any, x: Any, y: Any, z: Any, col: Any = None,
              breaks: Any = None) -> None:
        """``image``: log the grid, palette and breaks, then the window it sets, then the cells.

        R's ``image.default`` logs its arguments on entry and sets the window
        (``xaxs = "i"``, ``yaxs = "i"``) inside the call.
        """
        xs = np.asarray(x, dtype=float).ravel()
        ys = np.asarray(y, dtype=float).ravel()
        zz = np.asarray(z, dtype=float)
        pal = list(col) if col is not None else []
        brk = np.asarray(breaks, dtype=float).ravel() if breaks is not None else np.array([])
        self.log.append(("I", [xs, ys, zz.ravel(order="F"), pal, brk]))
        # image.default reads x and y as cell centres and widens them to cell edges.
        self.window(ax, _cell_edges(xs), _cell_edges(ys), xaxs="i", yaxs="i")
        if ax is not None and zz.size:
            ax.pcolormesh(xs, ys, zz.T, shading="nearest")

    def value(self, name: str, values: Any) -> None:
        """Log a quantity the R function returns or computes, by name."""
        arr = np.asarray(values, dtype=float).ravel()
        self.log.append(("V", [[name], arr]))

    def contour(self, ax: Any, x: Any, y: Any, z: Any, levels: Any) -> None:
        """``contour``: log the grid and the levels, then draw the lines."""
        xs = np.asarray(x, dtype=float).ravel()
        ys = np.asarray(y, dtype=float).ravel()
        zz = np.asarray(z, dtype=float)
        lv = np.asarray(levels, dtype=float).ravel()
        self.log.append(("C", [xs, ys, zz.ravel(order="F"), lv]))
        if ax is not None and zz.size and lv.size:
            ax.contour(xs, ys, zz.T, levels=lv)

    def hist(self, ax: Any, breaks: Any, density: Any, xlim: Any = None,
             add: bool = False) -> None:
        """``plot.histogram``: log the breaks and densities, then the window (unless ``add``), then the bars.

        With ``add`` the bars go on the current axes and no window is set, as R does.
        """
        b = np.asarray(breaks, dtype=float).ravel()
        d = np.asarray(density, dtype=float).ravel()
        self.log.append(("H", [b, d]))
        if not add:
            xl = xlim if xlim is not None else (b[0], b[-1])
            self.window(ax, xl, (min(0.0, float(d.min())), max(0.0, float(d.max()))))
        if ax is not None:
            ax.stairs(d, b, fill=True, alpha=0.5)

    def matplot(self, ax: Any, x: Any, y: Any, pch: Any, col: Any,
                xlim: Any, ylim: Any, xaxs: str = "r") -> None:
        """``matplot(x, y, type = "b")``: a window, then one ``type = "b"`` line per column.

        R draws the first column with ``plot`` and the rest with ``lines``.
        Both go through ``plot.xy``, so each column is one logged ``P`` entry.
        """
        xs = np.asarray(x, dtype=float).ravel()
        ym = np.asarray(y, dtype=float)
        self.window(ax, xlim, ylim, xaxs=xaxs)
        for j in range(ym.shape[1]):
            self.xy(ax, xs, ym[:, j], type="b", pch=pch[j], col=col[j])

    def boxplot(self, ax: Any, stats: Any, names: Any) -> None:
        """``bxp``: log the five-number stats per group."""
        st = np.asarray(stats, dtype=float)
        self.log.append(("B", [st.ravel(order="F"), list(names)]))
        if ax is not None:
            for j in range(st.shape[1]):
                ax.plot([j + 1] * 5, st[:, j], "k_")

    def segments(self, ax: Any, x0: float, y0: float, x1: float, y1: float,
                 col: Any = "black") -> None:
        """``segments(x0, y0, x1, y1)``: one logged ``S`` entry, one line drawn."""
        self.log.append(("S", [[x0, y0, x1, y1]]))
        if ax is not None:
            ax.plot([x0, x1], [y0, y1], color=_hex(col) if isinstance(col, str) else "black")

    def lines(self, ax: Any, x: Any, y: Any, col: Any = "black", type: str = "l",
              pch: Any = None) -> None:
        """``lines``: ``xy`` with type ``"l"`` (or ``"b"`` when given)."""
        self.xy(ax, x, y, type=type, pch=pch, col=col)


def adjustcolor_hex(color: str, alpha: float) -> str:
    """``grDevices::adjustcolor(color, alpha.f = alpha)`` as a ``#RRGGBBAA`` string."""
    hexval = _hex(color).lstrip("#")
    a = int(alpha * 255 + 0.5)
    return f"#{hexval.upper()}{a:02X}"


def gray_colors(n: int, start: float = 0.0, end: float = 1.0, gamma: float = 2.2) -> list[str]:
    """``grDevices::gray.colors(n, start, end)``."""
    levels = np.linspace(start ** gamma, end ** gamma, n) ** (1.0 / gamma)
    out = []
    for lv in levels:
        v = int(255 * lv + 0.5)
        out.append(f"#{v:02X}{v:02X}{v:02X}")
    return out


def _killplot_pairs_grid() -> Any:
    """Return ``killplot.pairs_grid``, adding the workspace ``killplot`` folder to the path if needed."""
    try:
        from killplot import pairs_grid
    except ImportError:
        import sys
        from pathlib import Path

        root = Path(__file__).resolve().parents[3] / "killplot"
        if str(root) not in sys.path:
            sys.path.insert(0, str(root))
        from killplot import pairs_grid
    return pairs_grid


def pairs_panels(canvas: Canvas, fig: Any, data: Any, pch: Any, col: Any,
                 gap: float = 0.2) -> list[list[Any]]:
    """Draw the ``pairs()`` layout: a window per panel, points off the diagonal.

    R loops over the x column ``j`` (outer) and the y column ``i`` (inner).
    The diagonal panel is a window with no points. Returns the axes grid.
    """
    pairs_grid = _killplot_pairs_grid()

    x = np.asarray(data, dtype=float)
    d = x.shape[1]
    axes = pairs_grid(fig, d, gap=gap) if fig is not None else None
    for j in range(d):
        for i in range(d):
            ax = axes[i][j] if axes is not None else None
            canvas.window(ax, _range(x[:, j]), _range(x[:, i]))
            if i != j:
                canvas.points(ax, x[:, j], x[:, i], pch=pch, col=col)
    return axes


def _range(v: Any) -> tuple[float, float]:
    arr = np.asarray(v, dtype=float).ravel()
    return float(np.nanmin(arr)), float(np.nanmax(arr))


def _cell_edges(centres: Any) -> tuple[float, float]:
    """The range of cell edges for cell centres, as ``image.default`` computes it.

    Each end is moved out by half the neighbouring cell width.
    """
    c = np.asarray(centres, dtype=float).ravel()
    if c.size < 2:
        return float(c[0]), float(c[0])
    half = np.diff(c) / 2.0
    return float(c[0] - half[0]), float(c[-1] + half[-1])


_LETTER_SYMBOLS = [chr(ord("A") + i) for i in range(26)]


def cl_pairs(canvas: Canvas, fig: Any, data: Any, classification: Any,
             symbols: Any = None, colors: Any = None, gap: float = 0.2) -> None:
    """``clPairs(data, classification)``: points coloured and shaped by class.

    Defaults follow ``mclust.options("classPlotSymbols")`` and ``classPlotColors``.
    More than two columns draw the ``pairs()`` layout. Two columns draw one
    plot, and anything below two is not handled here.
    """
    x = np.asarray(data, dtype=float)
    if x.ndim == 1:
        x = x.reshape(-1, 1)
    labels = np.asarray(classification).astype(str)
    levels = sorted(set(labels.tolist()))
    n_lev = len(levels)
    index = np.array([levels.index(v) for v in labels.tolist()])
    if symbols is None:
        opt_sym = mclust_options("classPlotSymbols")
        if n_lev <= len(opt_sym):
            symbols = list(opt_sym)
        elif n_lev <= 9:
            symbols = [str(i + 1) for i in range(9)]
        elif n_lev <= 26:
            symbols = _LETTER_SYMBOLS[:n_lev]
        else:
            symbols = [16] * n_lev
    symbols = list(symbols)
    if len(symbols) == 1:
        symbols = symbols * n_lev
    if len(symbols) < n_lev:
        symbols = [16] * n_lev
    if colors is None:
        opt_col = mclust_options("classPlotColors")
        colors = list(opt_col[:n_lev]) if n_lev <= len(opt_col) else None
    if colors is None:
        colors = ["black"] * n_lev
    colors = list(colors)
    if len(colors) == 1:
        colors = colors * n_lev
    if len(colors) < n_lev:
        colors = ["black"] * n_lev
    pch = [symbols[i] for i in index]
    col = [colors[i] for i in index]
    d = x.shape[1]
    if d > 2:
        pairs_panels(canvas, fig, x, pch=pch, col=col, gap=gap)
    elif d == 2:
        ax = fig.add_subplot(111) if fig is not None else None
        canvas.window(ax, _range(x[:, 0]), _range(x[:, 1]))
        canvas.points(ax, x[:, 0], x[:, 1], pch=pch, col=col)
    else:
        raise ValueError("cl_pairs needs at least two columns")
