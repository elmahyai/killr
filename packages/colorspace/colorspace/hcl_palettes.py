"""Catalog of predefined HCL palettes (colorspace 2.1-4)."""

from __future__ import annotations

import io
import json
import math
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Sequence

import numpy as np

from colorspace.diverging_hcl import _VARS_PAL
from colorspace.divergingx_hcl import _PAL_KEYS as _FLEX_KEYS

_PAL_KEYS = _VARS_PAL
_TYPE_LEVELS = (
    "Qualitative",
    "Sequential (single-hue)",
    "Sequential (multi-hue)",
    "Diverging",
)
_CUSTOM_HCL_PALS: dict[str, dict[str, Any]] = {}


@dataclass
class HclPalettes:
    """Tabular catalog of HCL palettes (R ``hcl_palettes`` data frame)."""

    names: tuple[str, ...]
    type: tuple[str, ...]
    h1: np.ndarray
    h2: np.ndarray
    c1: np.ndarray
    c2: np.ndarray
    l1: np.ndarray
    l2: np.ndarray
    p1: np.ndarray
    p2: np.ndarray
    cmax: np.ndarray
    fixup: np.ndarray

    @property
    def nrow(self) -> int:
        return len(self.names)

    def __repr__(self) -> str:
        buf = io.StringIO()
        _print_hcl_palettes(self, file=buf)
        return buf.getvalue().rstrip()


def _fx(name: str) -> str:
    return re.sub(r"[-_,() \.]", "", name.lower())


def _parse_row(raw: dict[str, Any]) -> dict[str, float | bool]:
    out: dict[str, float | bool] = {}
    for key in _PAL_KEYS:
        if key == "fixup":
            out[key] = bool(raw.get("fixup", True))
            continue
        value = raw.get(key)
        if value is None:
            out[key] = float("nan")
        else:
            out[key] = float(value)
    return out


@lru_cache(maxsize=1)
def _builtin_hcl_pals() -> dict[str, dict[str, Any]]:
    path = Path(__file__).resolve().parent / "hcl_palettes.json"
    return json.loads(path.read_text(encoding="utf-8"))


def _build_catalog() -> HclPalettes:
    pals = {**_builtin_hcl_pals(), **_CUSTOM_HCL_PALS}
    names = tuple(pals.keys())
    n = len(names)
    types = tuple(str(pals[name]["type"]) for name in names)
    arrays: dict[str, np.ndarray] = {}
    for key in _PAL_KEYS:
        col: list[float | bool] = []
        for name in names:
            parsed = _parse_row(pals[name])
            val = parsed[key]
            col.append(val)
        if key == "fixup":
            arrays[key] = np.array(col, dtype=bool)
        else:
            arrays[key] = np.array(col, dtype=np.float64)
    return HclPalettes(
        names=names,
        type=types,
        h1=arrays["h1"],
        h2=arrays["h2"],
        c1=arrays["c1"],
        c2=arrays["c2"],
        l1=arrays["l1"],
        l2=arrays["l2"],
        p1=arrays["p1"],
        p2=arrays["p2"],
        cmax=arrays["cmax"],
        fixup=arrays["fixup"],
    )


def add_hcl_pal(*, palette: str, type: str, parameters: dict[str, Any]) -> None:
    """Register a custom palette (R ``add_hcl_pals``)."""
    row: dict[str, Any] = {"type": type}
    row.update(parameters)
    _CUSTOM_HCL_PALS[palette] = row
    _build_catalog.cache_clear()


def _resolve_palette_keys(row_names: Sequence[str], palette: str | Sequence[str]) -> list[str]:
    namtab = [_fx(name) for name in row_names]
    if isinstance(palette, str):
        palette = [palette]
    resolved: list[str] = []
    for item in palette:
        key = _fx(item)
        if key in namtab:
            resolved.append(row_names[namtab.index(key)])
            continue
        matches = [row_names[i] for i, tab in enumerate(namtab) if tab.startswith(key)]
        if not matches:
            all_names = ", ".join(row_names)
            raise ValueError(f"Named 'palette' should be one of: {all_names}")
        resolved.append(matches[0])
    return resolved


def _filter_by_type(catalog: HclPalettes, type_arg: str | Sequence[str]) -> HclPalettes:
    if isinstance(type_arg, str):
        type_arg = [type_arg]
    levels = list(_TYPE_LEVELS)
    tytab = ["sequential"] + [_fx(level) for level in levels]
    matched: list[str] = []
    for ty in type_arg:
        ty_fx = _fx(ty)
        hit = [tab for tab in tytab if tab.startswith(ty_fx)]
        if not hit:
            raise ValueError(
                "Palette 'type' should be one of: "
                + ", ".join(levels)
            )
        tab_match = hit[0]
        if tab_match == "sequential":
            matched.extend(["sequentialsinglehue", "sequentialmultihue"])
        else:
            matched.append(tab_match)
    inner = tytab[1:]
    selected = {levels[i] for i, tab in enumerate(inner) if tab in matched}
    indices = [i for i in range(catalog.nrow) if catalog.type[i] in selected]
    if not indices:
        return _empty_catalog()
    pick = lambda arr: arr[np.array(indices, dtype=np.intp)]
    return HclPalettes(
        names=tuple(catalog.names[i] for i in indices),
        type=tuple(catalog.type[i] for i in indices),
        h1=pick(catalog.h1),
        h2=pick(catalog.h2),
        c1=pick(catalog.c1),
        c2=pick(catalog.c2),
        l1=pick(catalog.l1),
        l2=pick(catalog.l2),
        p1=pick(catalog.p1),
        p2=pick(catalog.p2),
        cmax=pick(catalog.cmax),
        fixup=pick(catalog.fixup),
    )


def _empty_catalog() -> HclPalettes:
    z = np.array([], dtype=np.float64)
    zb = np.array([], dtype=bool)
    return HclPalettes((), (), z, z, z, z, z, z, z, z, z, zb)


def _subset_catalog(catalog: HclPalettes, palette: Sequence[str]) -> HclPalettes:
    keys = _resolve_palette_keys(catalog.names, palette)
    namtab = [_fx(name) for name in catalog.names]
    key_fx = {_fx(k) for k in keys}
    indices = [i for i, tab in enumerate(namtab) if tab in key_fx or catalog.names[i] in keys]
    if not indices:
        return catalog
    pick = lambda arr: arr[np.array(indices, dtype=np.intp)]
    return HclPalettes(
        names=tuple(catalog.names[i] for i in indices),
        type=tuple(catalog.type[i] for i in indices),
        h1=pick(catalog.h1),
        h2=pick(catalog.h2),
        c1=pick(catalog.c1),
        c2=pick(catalog.c2),
        l1=pick(catalog.l1),
        l2=pick(catalog.l2),
        p1=pick(catalog.p1),
        p2=pick(catalog.p2),
        cmax=pick(catalog.cmax),
        fixup=pick(catalog.fixup),
    )


def hcl_palette_parameters(type_label: str, palette: str) -> dict[str, float | bool | None]:
    """First row of ``hcl_palettes(type=..., palette=...)`` as a parameter dict."""
    catalog = _build_catalog()
    catalog = _filter_by_type(catalog, type_label)
    catalog = _subset_catalog(catalog, [palette])
    if catalog.nrow < 1:
        raise ValueError(f"Named 'palette' should be one of: {', '.join(_build_catalog().names)}")
    row: dict[str, float | bool | None] = {}
    for key in _PAL_KEYS:
        val = getattr(catalog, key)[0]
        if key == "fixup":
            row[key] = bool(val)
        elif isinstance(val, float) and math.isnan(val):
            row[key] = float("nan")
        else:
            row[key] = float(val)
    return row


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
    elif x.nrow == 1:
        out.write("HCL palette")
        out.write(f"\nName: {x.names[0]}")
        out.write(f"\nType: {x.type[0]}")
        out.write("\nParameter ranges:\n")
        cols = _PAL_KEYS
        header = " ".join(f"{c:>4}" for c in cols)
        out.write(f"  {header}\n")
        values = [getattr(x, c)[0] for c in cols]
        line = " ".join(_format_palette_field(v, c == "fixup") for v, c in zip(values, cols, strict=True))
        out.write(f"  {line}\n")
    return x


def _format_palette_field(value: float | bool, is_fixup: bool = False) -> str:
    if is_fixup:
        return f"{'TRUE':>4}" if value else f"{'FALSE':>4}"
    if isinstance(value, float) and math.isnan(value):
        return f"{'NA':>4}"
    if float(value).is_integer():
        return f"{int(value):>4}"
    return f"{float(value):>4.0f}" if abs(float(value)) >= 10 else f"{float(value):>4}"


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


def _row_dict(catalog: HclPalettes, index: int) -> dict[str, float | bool]:
    row: dict[str, float | bool] = {}
    for key in _PAL_KEYS:
        val = getattr(catalog, key)[index]
        if key == "fixup":
            row[key] = bool(val)
        elif isinstance(val, float) and math.isnan(val):
            row[key] = float("nan")
        else:
            row[key] = float(val)
    return row


def _plot_hcl_palettes(
    x: HclPalettes,
    *,
    n: int = 7,
    fixup: bool = True,
    off: Sequence[float] | None = None,
    border: str | None = None,
    save_path: str | None = None,
    **_: Any,
) -> None:
    from colorspace.diverging_hcl import diverging_hcl
    from colorspace.divergingx_hcl import divergingx_hcl
    from colorspace.qualitative_hcl import qualitative_hcl
    from colorspace.sequential_hcl import sequential_hcl

    typ = (
        "Qualitative",
        "Sequential (single-hue)",
        "Sequential (multi-hue)",
        "Diverging",
        "Diverging (flexible)",
    )
    panels: dict[str, np.ndarray] = {}
    for ty in typ:
        rows = [i for i in range(x.nrow) if x.type[i] == ty]
        if not rows:
            continue
        colors: list[list[str | None]] = []
        labels: list[str] = []
        for i in rows:
            row = _row_dict(x, i)
            if ty == typ[0]:
                pal = qualitative_hcl(
                    n,
                    h1=row["h1"],
                    h2=row["h2"],
                    c1=row["c1"],
                    l1=row["l1"],
                    fixup=fixup,
                )
            elif ty in (typ[1], typ[2]):
                kwargs: dict[str, Any] = {
                    "n": n,
                    "h1": row["h1"],
                    "c1": row["c1"],
                    "c2": row["c2"],
                    "l1": row["l1"],
                    "l2": row["l2"],
                    "p1": row["p1"],
                    "p2": row["p2"],
                    "cmax": row["cmax"],
                    "fixup": fixup,
                }
                if ty == typ[2]:
                    kwargs["h2"] = row["h2"]
                pal = sequential_hcl(**kwargs)
            elif ty == typ[3]:
                pal = diverging_hcl(
                    n,
                    h1=row["h1"],
                    h2=row["h2"],
                    c1=row["c1"],
                    l1=row["l1"],
                    l2=row["l2"],
                    p1=row["p1"],
                    p2=row["p2"],
                    cmax=row["cmax"],
                    fixup=fixup,
                )
            else:
                flex_row: dict[str, Any] = {}
                for key in _FLEX_KEYS:
                    flex_row[key] = float("nan")
                for key in _PAL_KEYS:
                    if key in flex_row:
                        flex_row[key] = row[key]
                pal = divergingx_hcl(n, palette="Geyser", **flex_row, fixup=fixup)
            colors.append(pal)
            labels.append(x.names[i])
        panels[ty] = np.asarray(colors, dtype=object)
        panels[ty].setflags(write=False)
    _swatchplot_list(panels, n=n, off=off, border=border, save_path=save_path)


def _swatchplot_list(
    panels: dict[str, np.ndarray],
    *,
    n: int,
    off: Sequence[float] | None,
    border: str | None,
    save_path: str | None,
) -> None:
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle

    blocks: list[tuple[str, np.ndarray, list[str]]] = []
    for name, mat in panels.items():
        if mat.size == 0:
            continue
        labels = [f"{name}" if mat.shape[0] == 1 else "" for _ in range(mat.shape[0])]
        blocks.append((name, mat, labels))

    if not blocks:
        return

    if off is None:
        off0 = 0.1 if n < 7 else 0.0
    elif len(off) == 0:
        off0 = 0.0
    else:
        off0 = float(off[0])
    off1 = 0.3 if off is None or len(off) < 2 else float(off[1])
    off_arr = (1.0 - off0, 1.0 - off1)
    border_color = "lightgray" if border is None and n <= 9 else ("transparent" if border is None else border)

    fig_h = sum(max(1, b[1].shape[0]) for b in blocks) * 0.35 + len(blocks) * 0.4
    fig, ax = plt.subplots(figsize=(8, max(6, fig_h)))
    ax.axis("off")
    y_cursor = 1.0
    for title, mat, _ in blocks:
        m, ncol = mat.shape
        ax.text(0.0, y_cursor, title, fontsize=11, fontweight="bold", transform=ax.transAxes, va="top")
        y_cursor -= 0.04
        row_h = 0.8 / max(1, sum(b[1].shape[0] for b in blocks))
        for row_i in range(m):
            y0 = y_cursor - (row_i + 1) * row_h
            for col_i in range(ncol):
                color = mat[row_i, col_i]
                face = "none" if color is None else str(color)
                ax.add_patch(
                    Rectangle(
                        (0.15 + col_i / ncol, y0),
                        off_arr[0] / ncol,
                        row_h * 0.9,
                        facecolor=face,
                        edgecolor=border_color,
                        linewidth=0.5,
                        transform=ax.transAxes,
                    )
                )
        y_cursor -= m * row_h + 0.05
    fig.subplots_adjust(left=0.05, right=0.99, top=0.99, bottom=0.01)
    if save_path is not None:
        fig.savefig(save_path, format="svg")
        plt.close(fig)
    else:
        plt.show()


def hcl_palettes(
    type: str | Sequence[str] | None = None,
    palette: str | Sequence[str] | None = None,
    *,
    plot: bool = False,
    n: int = 7,
    save_path: str | None = None,
    **kwargs: Any,
):
    """Return predefined HCL palette definitions, optionally plotted."""
    catalog = _build_catalog()
    if type is not None:
        catalog = _filter_by_type(catalog, type)
    if palette is not None:
        catalog = _subset_catalog(
            catalog, palette if isinstance(palette, str) else list(palette)
        )
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
            if key == "fixup":
                col.append(bool(val))
            elif isinstance(val, float) and math.isnan(val):
                col.append(None)
            else:
                col.append(float(val))
        out[key] = col
    return out
