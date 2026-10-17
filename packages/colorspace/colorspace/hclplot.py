"""Palette trajectories in HCL space (colorspace 2.1-4)."""

from __future__ import annotations

import math
from typing import Any, Sequence

import numpy as np

from colorspace._cspace_convert import as_polar_luv, is_color_object
from colorspace.hex import hex as hex_color
from colorspace.hex2rgb import hex2RGB
from colorspace.polar_luv import polarLUV
from colorspace.specplot import _stats_spline_natural


def _hcl_matrix(color) -> np.ndarray:
    polar = as_polar_luv(color)
    coords = np.asarray(polar.coords, dtype=np.float64)
    return np.column_stack([coords[:, 2], coords[:, 1], coords[:, 0]])


def _pairwise_cor(x: np.ndarray, y: np.ndarray) -> float:
    mask = np.isfinite(x) & np.isfinite(y)
    if mask.sum() < 2:
        return float("nan")
    xv = x[mask]
    yv = y[mask]
    if np.std(xv) == 0 or np.std(yv) == 0:
        return float("nan")
    return float(np.corrcoef(xv, yv)[0, 1])


def _natural_spline(x: np.ndarray, y: np.ndarray, xout: np.ndarray) -> np.ndarray:
    return _stats_spline_natural(x, y, xout)


def hclplot_to_proof_dict(hcl: np.ndarray) -> list[list[float | None]]:
    out: list[list[float | None]] = []
    for row in np.asarray(hcl, dtype=np.float64):
        out.append([None if not math.isfinite(v) else float(v) for v in row])
    return out


def hclplot(
    x: Sequence[str] | Any,
    type: str | None = None,
    h: Sequence[float] | float | None = None,
    c: float | None = None,
    l: Sequence[float] | float | None = None,
    xlab: str | None = None,
    ylab: str | None = None,
    main: str | None = None,
    cex: float = 1.0,
    axes: bool = True,
    bg: str = "white",
    lwd: float = 1.0,
    size: float = 2.5,
    plot: bool = True,
    save_path: str | None = None,
    **_: Any,
) -> np.ndarray:
    """Plot palette coordinates in HCL space; return the HCL matrix."""
    if isinstance(x, (str, bytes)):
        colors = [x]
    elif is_color_object(x):
        colors = hex_color(x)
        hcl_source = x
    else:
        colors = list(x)
        hcl_source = None

    na_idx = [index for index, value in enumerate(colors) if value is None or (
        isinstance(value, float) and math.isnan(value)
    )]
    for index in na_idx:
        colors[index] = "#FFFFFF"

    if hcl_source is None:
        hcl_obj = hex2RGB(colors)
    else:
        hcl_obj = hcl_source
    hexes = colors if hcl_source is None else hex_color(hcl_source)

    hcl = _hcl_matrix(hcl_obj)
    n = hcl.shape[0]

    l_vals = hcl[:, 2]
    lran = float(np.nanmax(l_vals) - np.nanmin(l_vals)) if n else 0.0
    seq_index = np.arange(1, n + 1, dtype=np.float64)
    llin = _pairwise_cor(l_vals, seq_index) ** 2
    tri_target = np.abs(seq_index - (n + 1) / 2.0)
    ltri = _pairwise_cor(l_vals, tri_target) ** 2

    if type is None:
        if ltri > 0.75 and lran > 10:
            palette_type = "diverging"
        elif llin > 0.75 and lran > 10:
            palette_type = "sequential"
        else:
            palette_type = "qualitative"
    else:
        palette_type = type
        if palette_type not in ("diverging", "sequential", "qualitative"):
            raise ValueError(
                f"'{palette_type}' is not a valid choice for type"
            )

    if n > 1:
        for i in range(1, n):
            if np.any(np.isnan(hcl[(i - 1) : i + 1, :])):
                continue
            delta = hcl[i, 0] - hcl[i - 1, 0]
            if abs(delta) > 320:
                hcl[i, 0] -= math.copysign(360.0, delta)
            if abs(hcl[i, 0]) > 360:
                hcl[: i + 1, 0] -= math.copysign(360.0, hcl[i, 0])

        idx = np.flatnonzero(hcl[:, 1] < 8)
        if len(idx) == n:
            hcl[:, 0] = float(np.nanmean(hcl[:, 0]))
        elif len(idx) > 0:
            if n >= 49:
                h = hcl[:, 0]
                h1 = h[np.r_[0, 0, np.arange(0, n - 2)]]
                h2 = h[np.r_[0, np.arange(0, n - 1)]]
                hcl[:, 0] = (h1 + h2 + h) / 3.0
            idx_groups: list[list[int]] = []
            if len(idx):
                group = [int(idx[0])]
                for pos in idx[1:]:
                    if pos == group[-1] + 1:
                        group.append(int(pos))
                    else:
                        idx_groups.append(group)
                        group = [int(pos)]
                idx_groups.append(group)
            idx_set = set(int(i) for i in idx)
            s = 0
            while idx_groups:
                block = idx_groups[0]
                if s in block:
                    e = idx_groups[1][0] - 1 if len(idx_groups) > 1 else n - 1
                else:
                    e = n - 1 if (n - 1) in block else int(round(np.mean([block[0], block[-1]])))
                positions = list(range(s, e + 1))
                in_low = [p for p in positions if p in idx_set]
                out_high = [p for p in positions if p not in idx_set]
                if (
                    in_low
                    and out_high
                    and np.any(np.isfinite(hcl[out_high, 0]))
                ):
                    hcl[in_low, 0] = _natural_spline(
                        np.asarray(out_high, dtype=np.float64),
                        hcl[out_high, 0],
                        np.asarray(in_low, dtype=np.float64),
                    )
                idx_groups.pop(0)
                s = e + 1

    max_chroma_val = (
        int(math.ceil(c))
        if c is not None
        else int(
            max(
                100,
                min(180, math.ceil(float(np.nanmax(hcl[:, 1])) / 20.0) * 20),
            )
        )
    )

    if save_path is not None:
        _save_qualitative_figure(
            hcl,
            hexes,
            max_chroma_val,
            l=l,
            main=main,
            cex=cex,
            axes=axes,
            bg=bg,
            lwd=lwd,
            size=size,
            save_path=save_path,
        )
    elif plot:
        _save_qualitative_figure(
            hcl,
            hexes,
            max_chroma_val,
            l=l,
            main=main,
            cex=cex,
            axes=axes,
            bg=bg,
            lwd=lwd,
            size=size,
            save_path=None,
            show=True,
        )

    return hcl


def _xpos(hue: np.ndarray, chroma: np.ndarray) -> np.ndarray:
    return np.cos(np.radians(hue)) * chroma


def _ypos(hue: np.ndarray, chroma: np.ndarray) -> np.ndarray:
    return np.sin(np.radians(hue)) * chroma


def _save_qualitative_figure(
    hcl: np.ndarray,
    hexes: Sequence[str | None],
    max_chroma: int,
    *,
    l,
    main,
    cex,
    axes,
    bg,
    lwd,
    size,
    save_path: str | None,
    show: bool = False,
) -> None:
    import matplotlib.pyplot as plt

    n = hcl.shape[0]
    nd_h = np.arange(0, 361, 2, dtype=np.float64)
    nd_c = np.arange(0, max_chroma + 1, dtype=np.float64)
    hh, cc = np.meshgrid(nd_h, nd_c)
    l_val = float(np.nanmedian(hcl[:, 2])) if l is None else float(np.ravel(l)[0])
    grid_hex = hex_color(
        polarLUV(L=np.full(hh.size, l_val), C=cc.ravel(), H=hh.ravel()),
        fixup=False,
    )
    grid_hex = np.array(grid_hex, dtype=object)
    grid_hex[(l_val < 1) & (cc.ravel() > 0)] = None

    if main is None:
        main = f"Luminance = {int(round(l_val))}"

    fact = 1.1 + (cex - 1.0) / 10.0
    fig, ax = plt.subplots(figsize=(8, 8))
    ax.set_aspect("equal")
    ax.set_xlim(-max_chroma * fact, max_chroma * fact)
    ax.set_ylim(-max_chroma * fact, max_chroma * fact)
    ax.set_title(main)
    ax.axis("off")

    valid = grid_hex != None  # noqa: E711
    ax.scatter(
        _xpos(hh.ravel()[valid], cc.ravel()[valid]),
        _ypos(hh.ravel()[valid], cc.ravel()[valid]),
        c=[grid_hex[i] for i in np.where(valid)[0]],
        s=30,
        linewidths=0,
    )
    ring_h = np.linspace(0, 360, 361)
    ax.plot(
        _xpos(ring_h, np.full(361, max_chroma)),
        _ypos(ring_h, np.full(361, max_chroma)),
        color="black",
        linewidth=0.5,
    )
    ax.scatter(
        _xpos(hcl[:, 0], hcl[:, 1]),
        _ypos(hcl[:, 0], hcl[:, 1]),
        s=(1.1 * size * cex) ** 2 * 20,
        c=bg,
        linewidths=5 * lwd,
        zorder=3,
    )
    ax.scatter(
        _xpos(hcl[:, 0], hcl[:, 1]),
        _ypos(hcl[:, 0], hcl[:, 1]),
        s=(size * cex) ** 2 * 20,
        facecolors=list(hexes),
        edgecolors="black",
        linewidths=lwd,
        zorder=4,
    )
    if save_path:
        fig.savefig(save_path, bbox_inches="tight")
    if show:
        plt.show()
    plt.close(fig)
