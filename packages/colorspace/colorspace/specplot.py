"""Color spectrum plot (colorspace 2.1-4)."""

from __future__ import annotations

import colorsys
import math
from dataclasses import dataclass
from typing import Any, Sequence

import numpy as np

from colorspace._cspace_convert import as_polar_luv, hex_from_srgb
from colorspace.hex import hex as hex_color
from colorspace.hex2rgb import hex2RGB
from colorspace.srgb import sRGB

_DEFAULT_HCL_LEGEND = ("#E16A86", "#50A315", "#009ADE")
_DEFAULT_RGB_LEGEND = ("#CC0000", "#00CC00", "#0000CC")

_MISSING = object()


@dataclass
class SpecplotResult:
    HCL: np.ndarray
    RGB: np.ndarray
    hex: list[str | None]


def _r_sign(values: np.ndarray | float) -> np.ndarray | float:
    if isinstance(values, (float, int)):
        if values > 0:
            return 1.0
        if values < 0:
            return -1.0
        return 0.0
    out = np.zeros_like(values, dtype=np.float64)
    out[values > 0] = 1.0
    out[values < 0] = -1.0
    return out


def _stats_spline_natural(x: np.ndarray, y: np.ndarray, xout: np.ndarray) -> np.ndarray:
    """Natural cubic spline matching R ``stats::spline(..., method='natural')``."""
    x = np.asarray(x, dtype=np.float64)
    y = np.asarray(y, dtype=np.float64)
    xout = np.asarray(xout, dtype=np.float64)
    n = x.size
    if n < 2:
        return np.full(xout.shape, np.nan, dtype=np.float64)
    h = np.diff(x)
    if np.any(h <= 0):
        raise ValueError("x must be strictly increasing")
    # Second-derivative system for interior knots (natural: endpoints zero).
    mat = np.zeros((n, n), dtype=np.float64)
    rhs = np.zeros(n, dtype=np.float64)
    mat[0, 0] = 1.0
    mat[n - 1, n - 1] = 1.0
    for i in range(1, n - 1):
        mat[i, i - 1] = h[i - 1]
        mat[i, i] = 2.0 * (h[i - 1] + h[i])
        mat[i, i + 1] = h[i]
        rhs[i] = 6.0 * ((y[i + 1] - y[i]) / h[i] - (y[i] - y[i - 1]) / h[i - 1])
    m = np.linalg.solve(mat, rhs)
    left_slope = (y[1] - y[0]) / h[0] - h[0] * m[1] / 6.0
    right_slope = (y[n - 1] - y[n - 2]) / h[n - 2] + h[n - 2] * m[n - 2] / 6.0
    out = np.empty(xout.shape, dtype=np.float64)
    for j, xq in enumerate(xout):
        if xq < x[0]:
            out[j] = y[0] + left_slope * (xq - x[0])
            continue
        if xq > x[n - 1]:
            out[j] = y[n - 1] + right_slope * (xq - x[n - 1])
            continue
        i = int(np.searchsorted(x, xq, side="right") - 1)
        hi = h[i]
        dx = xq - x[i]
        dx1 = x[i + 1] - xq
        out[j] = (
            m[i] * dx1 * dx1 * dx1 / (6.0 * hi)
            + m[i + 1] * dx * dx * dx / (6.0 * hi)
            + (y[i] - m[i] * hi * hi / 6.0) * dx1 / hi
            + (y[i + 1] - m[i + 1] * hi * hi / 6.0) * dx / hi
        )
    return out


def _split_runs(indices: np.ndarray) -> list[np.ndarray]:
    if indices.size == 0:
        return []
    breaks = np.concatenate(([1], np.diff(indices) > 1))
    group_ids = np.cumsum(breaks) - 1
    groups: list[np.ndarray] = []
    for gid in range(int(group_ids[-1]) + 1):
        groups.append(indices[group_ids == gid])
    return groups


def _fix_hcl(HCL: np.ndarray, x_na: np.ndarray) -> None:
    n = HCL.shape[0]
    if n <= 1:
        return
    h_diff = HCL[1:, 0] - HCL[:-1, 0]
    md = float(np.nanmedian(h_diff))
    for i in range(1, n):
        if np.any(np.isnan(HCL[(i - 1) : i + 1, :])):
            continue
        d = float(HCL[i, 0] - HCL[i - 1, 0])
        if abs(d) > 300 or abs(d + 360 - md) < 4 or abs(d - 360 - md) < 4:
            HCL[i, 0] = HCL[i, 0] - _r_sign(d) * 360
        if abs(HCL[i, 0]) > 360:
            HCL[: i + 1, 0] = HCL[: i + 1, 0] - _r_sign(HCL[i, 0]) * 360

    idx = np.where(HCL[:, 1] < 8)[0]
    if idx.size == n:
        HCL[:, 0] = np.nanmean(HCL[:, 0])
        return
    if idx.size == 0:
        return

    extreme = (HCL[:, 2] < 2) | (HCL[:, 2] > 98)
    ix_true = np.where(extreme)[0]
    ix_false = np.where(~extreme)[0]
    if ix_true.size and ix_false.size:
        for i in ix_true:
            nearest = ix_false[np.argmin(np.abs(ix_false - i))]
            HCL[i, 0] = HCL[nearest, 0]

    if n >= 49:
        h_smooth = np.column_stack(
            [
                HCL[np.concatenate(([0, 0], np.arange(0, n - 2))), 0],
                HCL[np.concatenate(([0], np.arange(0, n - 1))), 0],
                HCL[:, 0],
            ]
        )
        HCL[:, 0] = np.nanmean(h_smooth, axis=1)
        if x_na.size:
            HCL[x_na, 0] = np.nan

    idx_pos = idx + 1
    x_na_pos = x_na + 1 if x_na.size else x_na
    idxs = _split_runs(idx_pos)
    s = 1
    while idxs:
        block = idxs[0]
        if np.any(s == block):
            if len(idxs) > 1:
                e = int(idxs[1][0] - 1)
            else:
                e = n
        elif n in block:
            e = n
        else:
            e = int(round(np.mean([block[0], block[-1]])))
        span = np.arange(min(s, e), max(s, e) + 1)
        in_idx = np.isin(span, idx_pos)
        in_na = np.isin(span, x_na_pos)
        io_false = span[~(in_idx | in_na)]
        io_true = span[in_idx | in_na]
        if io_true.size and io_false.size > 1:
            h_obs = HCL[io_false - 1, 0]
            if np.sum(~np.isnan(h_obs)) > 0:
                design = np.column_stack([np.ones(io_false.size), io_false.astype(np.float64)])
                coef, _, _, _ = np.linalg.lstsq(design, h_obs, rcond=None)
                residuals = h_obs - design @ coef
                if float(np.std(residuals, ddof=1)) < 1.3 if residuals.size > 1 else 0.0 < 1.3:
                    pred = np.column_stack([np.ones(io_true.size), io_true.astype(np.float64)]) @ coef
                    HCL[io_true - 1, 0] = pred
                else:
                    order = np.argsort(io_false)
                    x_f = io_false[order].astype(np.float64)
                    y_f = h_obs[order]
                    HCL[io_true - 1, 0] = _stats_spline_natural(
                        x_f, y_f, io_true.astype(np.float64)
                    )
                if x_na.size:
                    HCL[x_na, 0] = np.nan
        idxs = idxs[1:]
        s = e + 1


def _compute_specplot(x: Sequence[str | None], *, fix: bool) -> SpecplotResult:
    texts = list(x)
    x_na = np.array([i for i, v in enumerate(texts) if v is None or (isinstance(v, float) and math.isnan(v))], dtype=np.int64)
    work = list(texts)
    for i in x_na:
        work[i] = "#ffffff"
    rgb_obj = hex2RGB(work)
    polar = as_polar_luv(rgb_obj)
    rgb = np.asarray(rgb_obj.coords, dtype=np.float64).copy()
    hcl = np.asarray(polar.coords, dtype=np.float64).copy()
    hcl = hcl[:, [2, 1, 0]]
    hcl[np.isnan(hcl)] = 0.0
    if x_na.size:
        for col in range(3):
            hcl[x_na, col] = np.nan
            rgb[x_na, col] = np.nan
    if fix:
        _fix_hcl(hcl, x_na)
    hex_out: list[str | None] = []
    for i, value in enumerate(texts):
        if i in x_na:
            hex_out.append(None)
        else:
            hex_out.append(str(value))
    return SpecplotResult(HCL=hcl, RGB=rgb, hex=hex_out)


def _resolve_legend(value: Any, default: tuple[str, ...]) -> tuple[str, ...] | bool:
    if value is False:
        return False
    if value is True:
        return default
    if isinstance(value, str):
        return (value,)
    return tuple(str(v) for v in value)


def _r_rainbow(n: int) -> list[str]:
    h = np.linspace(0, 1, n) % 1.0
    rows = [colorsys.hsv_to_rgb(float(hi), 1.0, 1.0) for hi in h]
    return hex_from_srgb(np.asarray(rows, dtype=np.float64))


def _plot_specplot(
    x: Sequence[str | None],
    result: SpecplotResult,
    *,
    yspec: SpecplotResult | None,
    rgb: tuple[str, ...] | bool,
    hcl: tuple[str, ...] | bool,
    cex: float,
    type_: str,
    lwd: Sequence[float],
    lty: Sequence[float],
    pch: Sequence[Any] | None,
    mar: Any,
    oma: Any,
    main: str | None,
    legend: bool,
    palette: bool,
    save_path: str | None,
) -> None:
    import matplotlib.gridspec as gridspec
    import matplotlib.pyplot as plt

    x_na = [i for i, v in enumerate(x) if v is None or (isinstance(v, float) and math.isnan(v))]
    show_rgb = rgb is not False
    show_hcl = hcl is not False
    has_y = yspec is not None
    nr = int(show_rgb) + int(palette) + int(palette and has_y) + int(show_hcl)
    if nr == 0:
        return

    if len(x_na) == len(x):
        fig, ax = plt.subplots(figsize=(6, 2))
        ax.set_xlim(-1, 1)
        ax.set_ylim(-1, 1)
        ax.axis("off")
        ax.text(0, 0, "All colors NA\nCannot draw spectrum", ha="center", va="center", color="red")
        if save_path:
            fig.savefig(save_path, format="svg", bbox_inches="tight")
            plt.close(fig)
        else:
            plt.show()
        return

    height_ratios: list[float] = []
    if show_rgb:
        height_ratios.append(10)
    if palette:
        height_ratios.append(2)
    if palette and has_y:
        height_ratios.append(2)
    if show_hcl:
        height_ratios.append(10)

    fig = plt.figure(figsize=(8, 2 + 0.25 * sum(height_ratios)))
    gs = gridspec.GridSpec(nr, 1, height_ratios=height_ratios, hspace=0.35)
    row = 0
    n = len(x)
    lwd3 = list(lwd)[:3]
    lty3 = list(lty)[:3]
    type3 = [type_] * 3 if isinstance(type_, str) else list(type_)[:3]
    if pch is None:
        pch3 = [None if t == "l" else "o" for t in type3]
    else:
        pch3 = list(pch)[:3]

    if show_rgb:
        ax = fig.add_subplot(gs[row, 0])
        row += 1
        xs = np.arange(1, n + 1)
        ax.set_xlim(1, n)
        ax.set_ylim(0, 1)
        ax.set_xticks([])
        for channel, col, lw, lt, tp, pc in zip(
            range(3), rgb, lwd3, lty3, type3, pch3, strict=True
        ):
            ax.plot(
                xs,
                result.RGB[:, channel],
                color=col,
                linewidth=lw,
                linestyle="-" if lt == 1 else "--",
                marker=None if tp == "l" else "o",
                markersize=3 if pc else 0,
            )
            if has_y and yspec is not None:
                ax.plot(
                    xs,
                    yspec.RGB[:, channel],
                    color=col,
                    linewidth=lw,
                    linestyle="--" if lt == 1 else "-.",
                    marker=None if tp == "l" else "o",
                    markersize=3 if pc else 0,
                )
        if legend:
            ax.legend(["Red", "Green", "Blue"], loc="upper left", ncol=3, frameon=False)
        ax.set_title("RGB Spectrum", fontsize=9 * cex, pad=2)
        ax.set_ylabel("Red / Green / Blue", fontsize=8 * cex)
        if main:
            fig.suptitle(main, fontsize=12 * cex, y=0.98)
            main = None

    def _palette_strip(ax, colors: Sequence[str | None]) -> None:
        from matplotlib.colors import ListedColormap

        cols = [c if c is not None else "#ffffff" for c in colors]
        data = np.arange(len(cols)).reshape(-1, 1)
        ax.imshow(
            data,
            aspect="auto",
            cmap=ListedColormap(cols),
            vmin=0,
            vmax=max(len(cols) - 1, 1),
            origin="lower",
        )
        ax.set_xticks([])
        ax.set_yticks([])

    if palette:
        ax = fig.add_subplot(gs[row, 0])
        row += 1
        _palette_strip(ax, x)
        if main:
            ax.set_title(main, fontsize=12 * cex)

    if palette and has_y and yspec is not None:
        ax = fig.add_subplot(gs[row, 0])
        row += 1
        _palette_strip(ax, yspec.hex)

    if show_hcl:
        ax = fig.add_subplot(gs[row, 0])
        HCL = result.HCL
        ymax = max(float(np.nanmax(HCL[:, 1]) * 1.005), 100.0)
        yrad = 360.0 / ymax
        ax.set_xlim(1, n)
        ax.set_ylim(0, ymax)
        xs = np.arange(1, n + 1)
        h_min = float(np.nanmin(HCL[:, 0]))
        if h_min >= -1:
            labels = np.linspace(0, 360, 5)
            ax2 = ax.twinx()
            ax2.set_ylim(0, ymax)
            ax2.set_yticks(labels / yrad)
            ax2.set_yticklabels([str(int(round(v))) for v in labels])
            ax2.set_ylabel("Hue", fontsize=8 * cex)
            hue_y = HCL[:, 0] / yrad
        else:
            labels = np.linspace(-360, 360, 5)
            ax2 = ax.twinx()
            ax2.set_ylim(0, ymax)
            ax2.set_yticks(labels / (2 * yrad) + ymax / 2)
            ax2.set_yticklabels([str(int(round(v))) for v in labels])
            ax2.set_ylabel("Hue", fontsize=8 * cex)
            hue_y = (HCL[:, 0] + 360) / (2 * yrad)
        ax.plot(xs, hue_y, color=hcl[0], linewidth=lwd3[0], linestyle="-" if lty3[0] == 1 else "--")
        ax.plot(xs, HCL[:, 1], color=hcl[1], linewidth=lwd3[1], linestyle="-" if lty3[1] == 1 else "--")
        ax.plot(xs, HCL[:, 2], color=hcl[2], linewidth=lwd3[2], linestyle="-" if lty3[2] == 1 else "--")
        if has_y and yspec is not None:
            yH = yspec.HCL
            if h_min >= -1:
                y_hue = yH[:, 0] / yrad
            else:
                y_hue = (yH[:, 0] + 360) / (2 * yrad)
            ax.plot(xs, y_hue, color=hcl[0], linewidth=lwd3[0], linestyle="--")
            ax.plot(xs, yH[:, 1], color=hcl[1], linewidth=lwd3[1], linestyle="--")
            ax.plot(xs, yH[:, 2], color=hcl[2], linewidth=lwd3[2], linestyle="--")
        ax.legend(
            ["Hue", "Chroma", "Luminance"][::-1],
            loc="lower left",
            ncol=3,
            frameon=False,
        )
        ax.set_xlabel("HCL Spectrum", fontsize=9 * cex)
        ax.set_ylabel("Luminance / Chroma", fontsize=8 * cex)
        if main:
            ax.set_title(main, fontsize=12 * cex)

    if save_path:
        fig.savefig(save_path, format="svg", bbox_inches="tight")
        plt.close(fig)
    else:
        plt.show()


def specplot(
    x: Sequence[str | None],
    y: Sequence[str | None] | None = None,
    *,
    rgb: Any = False,
    hcl: Any = True,
    fix: bool = True,
    cex: float = 1.0,
    type: str = "l",
    lwd: float | Sequence[float] = _MISSING,
    lty: float | Sequence[float] = 1,
    pch: Sequence[Any] | None = None,
    mar: Any = None,
    oma: Any = None,
    main: str | None = None,
    legend: bool = True,
    palette: bool = True,
    plot: bool = True,
    save_path: str | None = None,
    **kwargs: Any,
) -> SpecplotResult:
    if lwd is _MISSING:
        lwd_val = 2 * cex
    else:
        lwd_val = lwd
    lwd_arr = np.ravel(np.asarray(lwd_val, dtype=np.float64))
    lty_arr = np.ravel(np.asarray(lty, dtype=np.float64))
    if lwd_arr.size == 1:
        lwd_arr = np.repeat(lwd_arr, 3)
    if lty_arr.size == 1:
        lty_arr = np.repeat(lty_arr, 3)

    if rgb is True:
        rgb_spec = tuple(
            hex_color(
                sRGB([0.8, 0, 0], [0, 0.8, 0], [0, 0, 0.8]),
            )
        )
    else:
        rgb_spec = _resolve_legend(rgb, _DEFAULT_RGB_LEGEND)
    if hcl is True:
        hcl_spec: tuple[str, ...] | bool = _DEFAULT_HCL_LEGEND
    else:
        hcl_spec = _resolve_legend(hcl, _DEFAULT_HCL_LEGEND)

    result = _compute_specplot(x, fix=fix)
    yspec: SpecplotResult | None = None
    if y is not None:
        yspec = _compute_specplot(y, fix=fix)

    if plot:
        _plot_specplot(
            x,
            result,
            yspec=yspec,
            rgb=rgb_spec,
            hcl=hcl_spec,
            cex=cex,
            type_=type,
            lwd=tuple(float(v) for v in lwd_arr[:3]),
            lty=tuple(float(v) for v in lty_arr[:3]),
            pch=pch,
            mar=mar,
            oma=oma,
            main=main,
            legend=legend,
            palette=palette,
            save_path=save_path,
        )
    return result


def specplot_to_proof_dict(result: SpecplotResult) -> dict[str, Any]:
    hcl = result.HCL
    rgb = result.RGB
    return {
        "HCL": [
            [None if math.isnan(v) else float(v) for v in row]
            for row in hcl
        ],
        "RGB": [
            [None if math.isnan(v) else float(v) for v in row]
            for row in rgb
        ],
        "hex": [None if v is None else str(v) for v in result.hex],
    }
