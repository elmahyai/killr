"""Recording drawing layer for the mclust plot translations.

Each plot translation writes the same primitive log as the R function it
ports. ``PlotLog`` extends ``Canvas`` from ``_plot_common`` with the
primitives that Canvas does not cover: arrows, polygons, legends and the
per-panel usr box. ``log_lines`` writes the log in the format that
``proof/plot_record.R`` writes, so the proofs compare the two logs token by
token.

Matplotlib draws the figure. The logged numbers are the data, not the pixels.
Colours are compared as strings, so ``adjustcolor`` reproduces R's hex output.
"""

from __future__ import annotations

import math
from typing import Any, Sequence

import matplotlib.colors as mcolors
import numpy as np
from matplotlib.lines import Line2D

from ._plot_common import Canvas, R_COLOR_HEX, _marker as _plot_common_marker
from ._plot_common import extendrange, pretty, usr_r

__all__ = [
    "PlotLog",
    "adjustcolor",
    "bubble",
    "class_levels",
    "grid1",
    "grid2",
    "log_lines",
    "r_seq_by",
    "r_seq_len",
    "rgb255",
    "symb2fill",
    "symb2open",
    "extendrange",
    "pretty",
    "usr_r",
]

EPS = float(np.finfo(float).eps)
SQRT_EPS = math.sqrt(EPS)

# Colours that mclust's defaults and proofs use, with R's col2rgb values.
_EXTRA_COLORS = {
    "black": "#000000",
    "white": "#FFFFFF",
    "grey30": "#4D4D4D",
    "gray30": "#4D4D4D",
    "gray75": "#BFBFBF",
    "grey75": "#BFBFBF",
    "gray50": "#7F7F7F",
    "grey50": "#7F7F7F",
    "grey40": "#666666",
    "gray40": "#666666",
}

# Canvas.xy resolves colour names through R_COLOR_HEX, so the extras go there too.
R_COLOR_HEX.update(_EXTRA_COLORS)


def _hex_of(name: str) -> str:
    if name in _EXTRA_COLORS:
        return _EXTRA_COLORS[name]
    if name in R_COLOR_HEX:
        return R_COLOR_HEX[name]
    return name


def rgb255(col: str) -> tuple[int, int, int]:
    """R's col2rgb for a colour name or a hex string."""
    hexval = _hex_of(str(col))
    if hexval.startswith("#"):
        r, g, b = (int(hexval[i:i + 2], 16) for i in (1, 3, 5))
        return r, g, b
    rgb = mcolors.to_rgb(hexval)
    return tuple(int(round(v * 255)) for v in rgb)


def adjustcolor(col: str, alpha_f: float) -> str:
    """``grDevices::adjustcolor(col, alpha.f = alpha_f)`` as a '#RRGGBBAA' string."""
    r, g, b = rgb255(col)
    a = int(255.0 * float(alpha_f) + 0.5)
    return f"#{r:02X}{g:02X}{b:02X}{a:02X}"


def rgba_of(col: str) -> tuple[float, float, float, float]:
    """A Matplotlib RGBA tuple for an R colour string."""
    text = str(col)
    if text.startswith("#") and len(text) == 9:
        return mcolors.to_rgba(text)
    if text.startswith("#"):
        return mcolors.to_rgba(text)
    r, g, b = rgb255(text)
    return r / 255.0, g / 255.0, b / 255.0, 1.0


def r_seq_by(frm: float, to: float, by: float) -> np.ndarray:
    """``seq(from, to, by)`` as R's seq.default computes it."""
    if by == 0:
        return np.array([frm], dtype=float)
    n = int(((to - frm) / by) + 1e-10)
    x = frm + np.arange(n + 1, dtype=float) * by
    return np.minimum(x, to) if by > 0 else np.maximum(x, to)


def r_seq_len(frm: float, to: float, n: int) -> np.ndarray:
    """``seq(from, to, length.out = n)`` as R's seq.default computes it."""
    if n == 1:
        return np.array([frm], dtype=float)
    by = (to - frm) / (n - 1)
    out = np.empty(n, dtype=float)
    out[0] = frm
    out[1:n - 1] = frm + np.arange(1, n - 1, dtype=float) * by
    out[n - 1] = to
    return out


def grid1(n: int, rng: Sequence[float], edge: bool = True) -> np.ndarray:
    """mclust's ``grid1``: n points spanning ``rng`` (edge) or cell midpoints."""
    if n < 0:
        raise ValueError("n must be nonpositive and integer")
    lo, hi = min(rng), max(rng)
    if edge:
        return r_seq_by(lo, hi, abs(hi - lo) / (n - 1))
    lj = abs(hi - lo)
    incr = lj / (2 * n)
    return r_seq_by(lo + incr, hi - incr, 2 * incr)


def grid2(x: Sequence[float], y: Sequence[float]) -> np.ndarray:
    """mclust's ``grid2``: all (x, y) pairs, x varying fastest."""
    xs = np.asarray(x, dtype=float)
    ys = np.asarray(y, dtype=float)
    gx, gy = np.meshgrid(xs, ys)
    return np.column_stack([gx.ravel(), gy.ravel()])


def bubble(x: Sequence[float], cex=(0.2, 3.0), alpha=(0.1, 1.0)) -> dict[str, np.ndarray]:
    """mclust's ``bubble``: point sizes and alphas from a rescaled uncertainty."""
    x = np.asarray(x, dtype=float).ravel()
    cex = np.asarray([c for c in cex if not math.isnan(c)], dtype=float)
    alpha = np.asarray([a for a in alpha if not math.isnan(a)], dtype=float)
    x = (x - x.min()) / (x.max() - x.min() + SQRT_EPS)
    r = np.sqrt(x / math.pi)
    r = (r - r.min()) / (r.max() - r.min() + SQRT_EPS)
    cex_out = r * (cex.max() - cex.min()) + cex.min()
    alpha_out = x * (alpha.max() - alpha.min()) + alpha.min()
    return {"cex": cex_out, "alpha": alpha_out}


def symb2open(x: Sequence[int]) -> list[int]:
    """mclust's ``symb2open``: the open symbol for each pch code."""
    symb = list(range(19))
    open_ = list(range(15)) + [0, 1, 2, 5]
    return [open_[symb.index(int(v))] for v in x]


def symb2fill(x: Sequence[int]) -> list[int]:
    """mclust's ``symb2fill``: the filled symbol for each pch code."""
    symb = list(range(19))
    fill = [15, 16, 17, 3, 4, 23, 25, 7, 8, 9, 20, 11, 12, 13, 14, 15, 16, 17, 18]
    return [fill[symb.index(int(v))] for v in x]


def _as_char(value: Any) -> str:
    if isinstance(value, (bool, np.bool_)):
        return "TRUE" if value else "FALSE"
    if isinstance(value, (int, np.integer)):
        return str(int(value))
    if isinstance(value, (float, np.floating)):
        v = float(value)
        if v.is_integer():
            return str(int(v))
        return repr(v)
    return str(value)


def class_levels(values: Sequence[Any]) -> tuple[np.ndarray, list[str]]:
    """``as.character(x)`` and ``sort(unique(...))`` of a classification."""
    chars = np.array([_as_char(v) for v in values], dtype=object)
    levels = sorted(set(chars.tolist()))
    return chars, levels


def log_lines(log: "PlotLog") -> list[str]:
    """Format a log the way ``proof/plot_record.R`` writes it."""
    out = []
    for tag, fields in log.log:
        tokens = [tag]
        for field in fields:
            items = _flatten(field)
            tokens.append(str(len(items)))
            for item in items:
                if isinstance(item, str):
                    tokens.append(item)
                else:
                    tokens.append("%.17g" % float(item))
        out.append(" ".join(tokens))
    return out


def _flatten(field: Any) -> list[Any]:
    if field is None:
        return []
    if isinstance(field, str):
        return [field]
    if isinstance(field, np.ndarray):
        return field.ravel().tolist()
    if isinstance(field, (list, tuple)):
        out: list[Any] = []
        for item in field:
            out.extend(_flatten(item))
        return out
    return [field]


class PlotLog(Canvas):
    """Canvas with the extra primitives and the per-panel usr record.

    ``panel`` is the (row, column) of the current panel, 1-based, as R's
    ``par("mfg")`` reports it. The usr record ``U`` follows every points call,
    so the axis limits of each drawn set of points are compared as well.
    """

    def __init__(self, panel: tuple[int, int] = (1, 1)) -> None:
        super().__init__()
        self.panel = panel

    @staticmethod
    def _usr(ax: Any) -> list[float]:
        return [float(v) for v in (*ax.get_xlim(), *ax.get_ylim())]

    def points(self, ax: Any, x: Any, y: Any, pch: Any = 1, col: Any = "black") -> None:
        super().points(ax, x, y, pch, col)
        if ax is not None:
            self.log.append(("U", [self._usr(ax), list(self.panel)]))

    def arrows(self, ax: Any, x0: Any, y0: Any, x1: Any, y1: Any, code: int = 2) -> None:
        """``arrows``: log the shaft end points and draw one arrow per row."""
        arrays = [np.asarray(v, dtype=float).ravel() for v in (x0, y0, x1, y1)]
        self.log.append(("A", arrays))
        if ax is None:
            return
        style = {1: "<|-", 2: "-|>", 3: "<|-|>"}.get(int(code), "-|>")
        for a, b, c, d in zip(*arrays):
            ax.annotate("", xy=(c, d), xytext=(a, b),
                        arrowprops=dict(arrowstyle=style, color="black", lw=0.8,
                                        shrinkA=0, shrinkB=0))

    def polygon(self, ax: Any, x: Any, y: Any, col: str) -> None:
        """``polygon``: log the vertices and the fill colour, then fill."""
        xs = np.asarray(x, dtype=float).ravel()
        ys = np.asarray(y, dtype=float).ravel()
        self.log.append(("Y", [xs, ys, [col]]))
        if ax is not None and xs.size:
            ax.fill(xs, ys, facecolor=rgba_of(col), edgecolor="none")

    def legend(self, ax: Any, x: Any, y: Any, labels: Sequence[str],
               pch: Any, col: Any, cex: float = 1.0) -> None:
        """``legend``: log the anchor, labels, symbols and colours, then draw.

        The anchor is the top-left corner of the box in user coordinates. R's
        legend geometry depends on the device's font metrics, so the box size
        is not logged.
        """
        pch_list = list(pch) if isinstance(pch, (list, tuple, np.ndarray)) else [pch]
        col_list = list(col) if isinstance(col, (list, tuple, np.ndarray)) else [col]
        self.log.append(("G", [[x], [y], list(labels), pch_list, col_list]))
        if ax is None or not len(labels):
            return
        handles = []
        for k, _ in enumerate(labels):
            p = pch_list[k % len(pch_list)]
            c = col_list[k % len(col_list)]
            color = rgba_of(c) if isinstance(c, str) else "black"
            handles.append(Line2D([], [], marker=_marker_for(p), linestyle="none",
                                  markersize=6 * float(cex), color=color))
        ax.legend(handles, list(labels), loc="upper left",
                  bbox_to_anchor=(float(x), float(y)), bbox_transform=ax.transData,
                  frameon=True, handletextpad=0.5, borderaxespad=0.0)

    def filled_contour(self, ax: Any, x: Any, y: Any, z: Any, levels: Any, col: Any) -> None:
        """``.filled.contour``: log the grid and the levels, then fill the bands."""
        xs = np.asarray(x, dtype=float).ravel()
        ys = np.asarray(y, dtype=float).ravel()
        zz = np.asarray(z, dtype=float)
        lv = np.asarray(levels, dtype=float).ravel()
        self.log.append(("C", [xs, ys, zz.ravel(order="F"), lv]))
        if ax is not None and zz.size and lv.size > 1:
            colors = [rgba_of(c) for c in list(col)[: lv.size - 1]]
            ax.contourf(xs, ys, zz.T, levels=lv, colors=colors)

    def window_xy(self, ax: Any, x: Any, y: Any, xlim: Any = None, ylim: Any = None,
                  xaxs: str = "r", yaxs: str = "r") -> tuple[float, float, float, float]:
        """``plot.window`` with R's default limits: the range of x and y."""
        xs = np.asarray(x, dtype=float).ravel()
        ys = np.asarray(y, dtype=float).ravel()
        xl = (float(np.nanmin(xs)), float(np.nanmax(xs))) if xlim is None else xlim
        yl = (float(np.nanmin(ys)), float(np.nanmax(ys))) if ylim is None else ylim
        return self.window(ax, xl, yl, xaxs=xaxs, yaxs=yaxs)


def _marker_for(pch: Any) -> str:
    return _plot_common_marker(pch)
