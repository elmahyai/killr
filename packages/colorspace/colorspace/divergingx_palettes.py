"""Catalog of flexible diverging HCL palettes (colorspace 2.1-4)."""

from __future__ import annotations

import io
import math
from dataclasses import dataclass
from typing import Any, Iterable, Sequence

import numpy as np

from colorspace.divergingx_hcl import (
    _PAL_KEYS,
    _builtin_divergingx_pals,
    _normalize_palette_name,
    divergingx_hcl,
)

_TYPE_LABEL = "Diverging (flexible)"
_COLUMNS = ("type", *_PAL_KEYS)


@dataclass
class HclPalettes:
    """Tabular catalog of HCL palettes (R ``hcl_palettes`` data frame)."""

    names: tuple[str, ...]
    type: tuple[str, ...]
    h1: np.ndarray
    h2: np.ndarray
    h3: np.ndarray
    c1: np.ndarray
    c2: np.ndarray
    c3: np.ndarray
    l1: np.ndarray
    l2: np.ndarray
    l3: np.ndarray
    p1: np.ndarray
    p2: np.ndarray
    p3: np.ndarray
    p4: np.ndarray
    cmax1: np.ndarray
    cmax2: np.ndarray

    @property
    def nrow(self) -> int:
        return len(self.names)

    def __repr__(self) -> str:
        buf = io.StringIO()
        _print_hcl_palettes(self, file=buf)
        return buf.getvalue().rstrip()

    def _row_arrays(self) -> list[dict[str, float]]:
        rows: list[dict[str, float]] = []
        for i in range(self.nrow):
            row: dict[str, float] = {}
            for key in _PAL_KEYS:
                val = getattr(self, key)[i]
                row[key] = float(val) if not (isinstance(val, float) and math.isnan(val)) else float("nan")
            rows.append(row)
        return rows


def _build_catalog() -> HclPalettes:
    pals = _builtin_divergingx_pals()
    names = tuple(pals.keys())
    n = len(names)
    arrays: dict[str, np.ndarray] = {}
    for key in _PAL_KEYS:
        arrays[key] = np.array([pals[name][key] for name in names], dtype=np.float64)
    return HclPalettes(
        names=names,
        type=(_TYPE_LABEL,) * n,
        **arrays,
    )


def _resolve_palette_keys(
    row_names: Sequence[str], palette: str | Sequence[str]
) -> list[str]:
    namtab = [_normalize_palette_name(name) for name in row_names]
    if isinstance(palette, str):
        palette = [palette]
    resolved: list[str] = []
    for item in palette:
        key = _normalize_palette_name(item)
        if key in namtab:
            resolved.append(key)
            continue
        matches = [tab for tab in namtab if tab.startswith(key)]
        if not matches:
            all_names = ", ".join(row_names)
            raise ValueError(f"Named 'palette' should be one of: {all_names}")
        resolved.append(matches[0])
    return resolved


def _subset_catalog(catalog: HclPalettes, palette: Sequence[str]) -> HclPalettes:
    keys = _resolve_palette_keys(catalog.names, palette)
    namtab = [_normalize_palette_name(name) for name in catalog.names]
    indices = [i for i, tab in enumerate(namtab) if tab in keys]
    if not indices:
        return catalog
    pick = lambda arr: arr[np.array(indices, dtype=np.intp)]
    return HclPalettes(
        names=tuple(catalog.names[i] for i in indices),
        type=tuple(catalog.type[i] for i in indices),
        h1=pick(catalog.h1),
        h2=pick(catalog.h2),
        h3=pick(catalog.h3),
        c1=pick(catalog.c1),
        c2=pick(catalog.c2),
        c3=pick(catalog.c3),
        l1=pick(catalog.l1),
        l2=pick(catalog.l2),
        l3=pick(catalog.l3),
        p1=pick(catalog.p1),
        p2=pick(catalog.p2),
        p3=pick(catalog.p3),
        p4=pick(catalog.p4),
        cmax1=pick(catalog.cmax1),
        cmax2=pick(catalog.cmax2),
    )


def _print_hcl_palettes(x: HclPalettes, *, file: io.TextIOBase | None = None) -> HclPalettes:
    import sys

    out = file if file is not None else sys.stdout
    if x.nrow > 1:
        out.write("HCL palettes\n")
        types = sorted(set(x.type))
        for ty in types:
            out.write(f"\nType:  {ty} \n")
            out.write("Names: ")
            names = [x.names[i] for i in range(x.nrow) if x.type[i] == ty]
            wrapped = _strwrap(", ".join(names), exdent=7)
            out.write(wrapped)
            if not wrapped.endswith("\n"):
                out.write("\n")
    else:
        out.write("HCL palette")
        out.write(f"\nName: {x.names[0]}")
        out.write(f"\nType: {x.type[0]}")
        out.write("\nParameter ranges:\n")
        cols = ("h1", "h2", "h3", "c1", "c2", "c3", "l1", "l2", "l3", "p1")
        header = " ".join(f"{c:>2}" for c in cols)
        out.write(f"  {header}\n")
        values = [getattr(x, c)[0] for c in cols]
        line = " ".join(_format_palette_field(v) for v in values)
        out.write(f"  {line}\n")
    return x


def _format_palette_field(value: float) -> str:
    if isinstance(value, float) and math.isnan(value):
        return f"{'NA':>2}"
    if float(value).is_integer():
        return f"{int(value):>2}"
    return f"{float(value):>2.0f}" if abs(float(value)) >= 10 else f"{float(value):>2}"


def _strwrap(text: str, *, exdent: int = 0, width: int = 60) -> str:
    words = text.split()
    if not words:
        return ""
    lines: list[str] = []
    current = words[0]
    for word in words[1:]:
        candidate = f"{current} {word}"
        if len(candidate) <= width:
            current = candidate
        else:
            lines.append(current)
            current = " " * exdent + word
    lines.append(current)
    return "\n".join(lines)


def _row_colors(row: dict[str, float], *, n: int, fixup: bool) -> list[str]:
    kwargs: dict[str, Any] = {"fixup": fixup}
    for key in _PAL_KEYS:
        kwargs[key] = row[key]
    return divergingx_hcl(n, palette="Geyser", **kwargs)


def _plot_hcl_palettes(
    x: HclPalettes,
    *,
    n: int = 7,
    fixup: bool = True,
    off: Sequence[float] | None = None,
    border: str | None = None,
    nrow: int = 20,
    save_path: str | None = None,
    **_: Any,
) -> None:
    rows = x._row_arrays()
    colors = [_row_colors(row, n=n, fixup=fixup) for row in rows]
    matrix = np.asarray(colors, dtype=object)
    _swatchplot(
        matrix,
        rownames=list(x.names),
        nrow=nrow,
        off=off,
        border=border,
        save_path=save_path,
    )


def _swatchplot(
    x: np.ndarray,
    *,
    rownames: Sequence[str],
    nrow: int = 20,
    off: Sequence[float] | None = None,
    border: str | None = None,
    save_path: str | None = None,
) -> None:
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle

    mat = np.asarray(x, dtype=object)
    mat[mat == None] = "transparent"  # noqa: E711
    m, n = mat.shape

    cex = 0.7 if m > 15 else 1.0
    nc = math.ceil(m / nrow) if m > 1 else 1
    nr = math.ceil(m / nc) if m > 1 else 1
    col_idx = np.resize(np.repeat(np.arange(1, nc + 1), nr), m)

    if off is None:
        off0 = 0.1 if n < 7 else 0.0
    elif len(off) == 0:
        off0 = 0.0
    else:
        off0 = float(off[0])
    off1 = 0.3 if off is None or len(off) < 2 else float(off[1])
    off_arr = (1.0 - off0, 1.0 - off1)

    if border is None:
        border_color = "transparent" if n > 9 else "lightgray"
    else:
        border_color = border

    fig, axes = plt.subplots(1, nc, figsize=(7, max(10, m * 0.45)), squeeze=False)
    for panel in range(nc):
        ax = axes[0, panel]
        rows = np.where(col_idx == panel + 1)[0]
        xi = mat[rows, :]
        nri = xi.shape[0]
        ax.set_xlim(0.0, 1.0 - (1.0 - off_arr[0]) / n)
        ax.set_ylim(0.0, 1.0 - (1.0 - off_arr[1]) / nr)
        ax.axis("off")

        y_base = np.arange(nr - 1, nr - nri - 1, -1, dtype=np.float64) / nr
        for row_i in range(nri):
            y0 = y_base[row_i]
            label = rownames[rows[row_i]]
            ax.text(
                -0.01,
                y0 + 0.5 * off_arr[1] / nr,
                label,
                transform=ax.transData,
                ha="right",
                va="center",
                fontsize=9 * cex,
            )
            for col_i in range(n):
                color = xi[row_i, col_i]
                if color == "transparent":
                    face = "none"
                    edge: str | None = "none"
                else:
                    face = str(color)
                    edge = border_color
                ax.add_patch(
                    Rectangle(
                        (col_i / n, y0),
                        off_arr[0] / n,
                        off_arr[1] / nr,
                        facecolor=face,
                        edgecolor=edge,
                        linewidth=0.5,
                    )
                )

    fig.subplots_adjust(left=0.22, right=0.99, top=0.99, bottom=0.01, wspace=0.1)
    if save_path is not None:
        fig.savefig(save_path, format="svg")
        plt.close(fig)
    else:
        plt.show()


def divergingx_palettes(
    palette: str | Sequence[str] | None = None,
    *,
    plot: bool = False,
    n: int = 7,
    save_path: str | None = None,
    **kwargs: Any,
):
    """Return flexible diverging HCL palette definitions, optionally plotted."""
    catalog = _build_catalog()
    if palette is not None:
        catalog = _subset_catalog(catalog, palette if isinstance(palette, str) else list(palette))
    if plot:
        _plot_hcl_palettes(catalog, n=n, save_path=save_path, **kwargs)
        return catalog
    return catalog


def catalog_to_proof_dict(catalog: HclPalettes) -> dict[str, list[Any]]:
    """Serialize palette table for R comparison proofs."""
    out: dict[str, list[Any]] = {"names": list(catalog.names), "type": list(catalog.type)}
    for key in _PAL_KEYS:
        col: list[Any] = []
        for val in getattr(catalog, key):
            if isinstance(val, float) and math.isnan(val):
                col.append(None)
            else:
                col.append(float(val))
        out[key] = col
    return out
