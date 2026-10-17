"""Demo plots for color palettes (colorspace 2.1-4)."""

from __future__ import annotations

import json
import math
from functools import lru_cache
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

_DEMO_TYPES = (
    "map",
    "heatmap",
    "scatter",
    "spine",
    "bar",
    "pie",
    "perspective",
    "mosaic",
    "lines",
)

_DATA_PATH = Path(__file__).resolve().parent


@lru_cache(maxsize=1)
def _example_data() -> dict:
    return json.loads((_DATA_PATH / "demoplot_example.json").read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def _us_south_polygon() -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    raw = json.loads((_DATA_PATH / "us_south_polygon.json").read_text(encoding="utf-8"))
    x = np.array([np.nan if v == "NA" else float(v) for v in raw["x"]], dtype=np.float64)
    y = np.array(
        [np.nan if v == "NA" else float(v) for v in raw["y"]], dtype=np.float64
    )
    z = np.array(
        [np.nan if v == "NA" else float(v) for v in raw["z"]], dtype=np.float64
    )
    return x, y, z


@lru_cache(maxsize=1)
def _volcano() -> np.ndarray:
    return np.loadtxt(_DATA_PATH / "volcano.csv", delimiter=",")


def _as_hex_vector(x) -> list[str]:
    if isinstance(x, str):
        return [x]
    return [str(v) for v in list(x)]


def _r_cut(values: np.ndarray, *, n: int) -> list[int | None]:
    breaks = np.linspace(0.0, 1.0, n + 1)
    out: list[int | None] = []
    for val in values:
        if val <= breaks[0] or val > breaks[-1]:
            out.append(None)
            continue
        placed = None
        for i in range(n):
            left = breaks[i]
            right = breaks[i + 1]
            if i == 0:
                if left < val <= right:
                    placed = i
                    break
            elif val > left and val <= right:
                placed = i
                break
        out.append(placed)
    return out


def _dnorm(x, mean, sd):
    z = (x - mean) / sd
    return np.exp(-0.5 * z * z) / (sd * math.sqrt(2.0 * math.pi))


def demoplot_palette_use(x, type: str = "map") -> dict:
    """Return palette colors each demo plot type would apply (no drawing)."""
    if type not in _DEMO_TYPES:
        raise ValueError(f"type must be one of {_DEMO_TYPES!r}")
    colors = _as_hex_vector(x)
    n = len(colors)
    out: dict = {"type": type}

    if type == "map":
        z = _us_south_polygon()[2]
        z_clean = z[~np.isnan(z)]
        idx = _r_cut(z_clean, n=n)
        out["colors"] = [colors[i] if i is not None else None for i in idx]
    elif type == "heatmap":
        out["colors"] = list(reversed(colors))
    elif type == "scatter":
        clusters = _example_data()["cutree"][n - 1]
        out["colors"] = [colors[int(c) - 1] for c in clusters]
    elif type == "spine":
        out["colors"] = colors * 9
        out["border_black"] = n < 10
    elif type == "bar":
        out["colors"] = colors
        out["matrix"] = _bar_positions(n)
    elif type == "pie":
        out["colors"] = colors
    elif type == "perspective":
        if n > 1:
            cut_entry = _example_data()["perspective_cut"][str(n)]
            codes = cut_entry["codes"]
            rev = list(reversed(colors))
            out["colors"] = [rev[int(c) - 1] for c in codes]
        else:
            out["colors"] = colors
    elif type == "mosaic":
        mat = np.asarray(_example_data()["mosaic"][n - 1], dtype=np.float64)
        out["colors"] = colors
        out["matrix_shape"] = [int(mat.shape[0]), int(mat.shape[1])]
    elif type == "lines":
        rev = list(reversed(colors))
        out["colors"] = colors + rev + rev
    return out


def _bar_positions(n: int) -> list[list[float]]:
    rows = []
    seq = np.arange(1, n + 1, dtype=np.float64)
    vals = np.column_stack(
        [
            1.1 + np.abs(np.sin(0.5 + seq)) / 3.0,
            1.9 + np.abs(np.cos(1.1 + seq)) / 3.0,
            0.7 + np.abs(np.sin(1.5 + seq)) / 3.0,
            0.3 + np.abs(np.cos(0.8 + seq)) / 3.0,
        ]
    )
    for row_idx in range(n):
        base = row_idx + 1.5
        rows.append([base + 8.0 * j for j in range(4)])
    return rows


def demoplot(x, type: str = "map", **kwargs):
    """Draw a palette demo plot; dispatches by ``type`` like R ``demoplot``."""
    if type not in _DEMO_TYPES:
        raise ValueError(
            f"type must be one of {', '.join(_DEMO_TYPES)!r}, not {type!r}"
        )
    dispatch = {
        "map": _plot_map,
        "heatmap": _plot_heatmap,
        "scatter": _plot_scatter,
        "spine": _plot_spine,
        "bar": _plot_bar,
        "pie": _plot_pie,
        "perspective": _plot_perspective,
        "mosaic": _plot_mosaic,
        "lines": _plot_lines,
    }
    return dispatch[type](x, **kwargs)


def _plot_map(x, **kwargs):
    colors = _as_hex_vector(x)
    n = len(colors)
    px, py, pz = _us_south_polygon()
    z_clean = pz[~np.isnan(pz)]
    idx = _r_cut(z_clean, n=n)
    fill = [colors[i] if i is not None else "#FFFFFF" for i in idx]

    fig, ax = plt.subplots()
    ax.set_xlim(-88.5, -78.6)
    ax.set_ylim(30.2, 35.2)
    ax.set_aspect("equal")
    ax.axis("off")

    color_i = 0
    i = 0
    while i < len(px):
        if np.isnan(px[i]):
            i += 1
            chunk_x: list[float] = []
            chunk_y: list[float] = []
            while i < len(px) and not np.isnan(px[i]):
                chunk_x.append(px[i])
                chunk_y.append(py[i])
                i += 1
            if chunk_x and color_i < len(fill):
                ax.fill(chunk_x, chunk_y, color=fill[color_i])
                color_i += 1
        else:
            i += 1
    plt.close(fig)
    return None


def _plot_heatmap(x, **kwargs):
    colors = list(reversed(_as_hex_vector(x)))
    z = _volcano()
    fig, ax = plt.subplots()
    ax.imshow(z, cmap=plt.matplotlib.colors.ListedColormap(colors), aspect="auto")
    ax.axis("off")
    plt.close(fig)
    return None


def _plot_scatter(x, **kwargs):
    colors = _as_hex_vector(x)
    data = _example_data()
    xs = np.asarray(data["x"], dtype=np.float64) + np.asarray(
        data["xerror"], dtype=np.float64
    )
    ys = np.asarray(data["y"], dtype=np.float64) + np.asarray(
        data["yerror"], dtype=np.float64
    )
    clusters = data["cutree"][len(colors) - 1]
    bg = [colors[int(c) - 1] for c in clusters]
    fig, ax = plt.subplots()
    ax.scatter(xs, ys, c="black", facecolors=bg, edgecolors="black", s=80)
    ax.axis("off")
    plt.close(fig)
    return None


def _plot_spine(x, **kwargs):
    colors = _as_hex_vector(x)
    n = len(colors)
    off = 0.015
    widths = [0.05, 0.1, 0.15, 0.1, 0.2, 0.08, 0.12, 0.16, 0.04]
    k = len(widths)
    powers = [2.5, 1.2, 2.7, 1.0, 1.3, 0.7, 0.4, 0.2, 1.7]
    t = np.linspace(0.0, 1.0, n + 1)
    heights = np.column_stack([(t[:-1] ** (1.0 / p)) for p in powers])
    fig, ax = plt.subplots()
    ax.set_xlim(0, sum(widths) + off * (k - 1))
    ax.set_ylim(0, 1)
    ax.axis("off")
    xleft0 = np.concatenate([[0.0], np.cumsum(np.asarray(widths) + off)[:-1]])
    for col_i, w in enumerate(widths):
        x0 = xleft0[col_i]
        for row_i in range(n):
            ax.add_patch(
                plt.Rectangle(
                    (x0, heights[row_i, col_i]),
                    w,
                    heights[row_i + 1, col_i] - heights[row_i, col_i],
                    facecolor=colors[row_i],
                    edgecolor="black" if n < 10 else "none",
                )
            )
    if n >= 10:
        for x0, w in zip(xleft0, widths, strict=True):
            ax.add_patch(plt.Rectangle((x0, 0), w, 1, fill=False, edgecolor="black"))
    plt.close(fig)
    return None


def _plot_bar(x, **kwargs):
    colors = _as_hex_vector(x)
    n = len(colors)
    seq = np.arange(1, n + 1, dtype=np.float64)
    heights = np.column_stack(
        [
            1.1 + np.abs(np.sin(0.5 + seq)) / 3.0,
            1.9 + np.abs(np.cos(1.1 + seq)) / 3.0,
            0.7 + np.abs(np.sin(1.5 + seq)) / 3.0,
            0.3 + np.abs(np.cos(0.8 + seq)) / 3.0,
        ]
    )
    fig, ax = plt.subplots()
    width = 0.8 / 4
    positions = _bar_positions(n)
    for series in range(4):
        xs = [row[series] for row in positions]
        ax.bar(xs, heights[:, series], width=width, color=colors, align="center")
    ax.axis("off")
    plt.close(fig)
    return np.asarray(positions, dtype=np.float64)


def _plot_pie(x, **kwargs):
    colors = _as_hex_vector(x)
    n = len(colors)
    sizes = 0.01 + np.abs(np.sin(0.5 + np.arange(1, n + 1)))
    fig, ax = plt.subplots()
    ax.pie(sizes, colors=colors, radius=1)
    ax.axis("equal")
    plt.close(fig)
    return None


def _plot_perspective(x, **kwargs):
    colors = _as_hex_vector(x)
    n = len(colors)
    grid_n = 31
    x1 = np.linspace(-3, 3, grid_n)
    x2 = np.linspace(-3, 3, grid_n)
    xx, yy = np.meshgrid(x1, x2)
    z = 0.5 * _dnorm(xx, -1, 0.8) * _dnorm(yy, -1, 0.8) + 0.5 * _dnorm(
        xx, 1, 0.72
    ) * _dnorm(yy, 1, 0.72)
    if n > 1:
        cut_entry = _example_data()["perspective_cut"][str(n)]
        codes = cut_entry["codes"]
        rev = list(reversed(colors))
        face = np.asarray([rev[int(c) - 1] for c in codes]).reshape(
            grid_n - 1, grid_n - 1
        )
    else:
        face = colors[0]
    fig = plt.figure()
    ax = fig.add_subplot(111, projection="3d")
    ax.plot_surface(xx, yy, z, facecolors=face if n > 1 else None, color=face if n == 1 else None)
    plt.close(fig)
    return None


def _plot_mosaic(x, **kwargs):
    colors = _as_hex_vector(x)
    mat = np.asarray(_example_data()["mosaic"][len(colors) - 1], dtype=np.float64)
    fig, ax = plt.subplots()
    ax.imshow(mat, cmap=plt.matplotlib.colors.ListedColormap(colors), aspect="auto")
    ax.axis("off")
    plt.close(fig)
    return None


def _plot_lines(x, **kwargs):
    colors = _as_hex_vector(x)
    n = len(colors)
    rev = list(reversed(colors))
    fig, ax = plt.subplots()
    ax.set_xlim(0, 6)
    ax.set_ylim(1.5, n + 1.5)
    ax.axis("off")
    s = np.arange(2, n + 2, dtype=np.float64)
    rev_s = s[::-1]
    lwd = 6 - (n > 5) - (n > 15) - (n > 25)
    for i in range(n):
        si = s[i]
        rsi = rev_s[i]
        ax.plot([1 / si, 2 + 1 / rsi], [si, rsi], color=colors[i], linewidth=lwd)
        ax.plot([2 + 1 / si, 4 - 1 / si], [si, si], color=rev[i], linewidth=lwd)
        ax.plot([4 - 1 / si, 6 - 1 / rsi], [si, rsi], color=rev[i], linewidth=lwd)
    plt.close(fig)
    return None
