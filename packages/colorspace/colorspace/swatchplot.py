"""Palette swatch plots (colorspace 2.1-4)."""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from functools import lru_cache
from pathlib import Path
from typing import Any

import json

import numpy as np

from colorspace.deutan import _interpolate_cvd_transform, _simulate_cvd, deutan
from colorspace.desaturate import desaturate

_CVD_CHOICES = (
    "deutan",
    "deuteranope",
    "protanope",
    "tritanope",
    "desaturated",
)


class SwatchMatrix:
    """Color matrix returned by ``swatchplot`` with row and column labels."""

    __slots__ = ("values", "rownames", "colnames")

    def __init__(
        self,
        values: np.ndarray,
        rownames: Sequence[str],
        colnames: Sequence[str],
    ) -> None:
        self.values = np.asarray(values, dtype=object)
        self.rownames = list(rownames)
        self.colnames = list(colnames)

    @property
    def shape(self) -> tuple[int, ...]:
        return self.values.shape

    def __repr__(self) -> str:
        return repr(self.values)

_RESERVED = frozenset(
    {
        "nrow",
        "border",
        "sborder",
        "off",
        "mar",
        "line",
        "cex",
        "font",
        "cvd",
        "plot",
        "save_path",
    }
)


@lru_cache(maxsize=1)
def _protanomaly_cvd() -> list[np.ndarray]:
    path = Path(__file__).resolve().parent / "protanomaly_cvd.json"
    raw = json.loads(path.read_text(encoding="utf-8"))
    return [np.asarray(row, dtype=np.float64).reshape(3, 3) for row in raw]


@lru_cache(maxsize=1)
def _tritanomaly_cvd() -> list[np.ndarray]:
    path = Path(__file__).resolve().parent / "tritanomaly_cvd.json"
    raw = json.loads(path.read_text(encoding="utf-8"))
    return [np.asarray(row, dtype=np.float64).reshape(3, 3) for row in raw]


def _protan(colors: Sequence[str]) -> list[str | None]:
    transform = _interpolate_cvd_transform(_protanomaly_cvd(), 1.0)
    out = _simulate_cvd(list(colors), transform, linear=True)
    return list(out)


def _tritan(colors: Sequence[str]) -> list[str | None]:
    transform = _interpolate_cvd_transform(_tritanomaly_cvd(), 1.0)
    out = _simulate_cvd(list(colors), transform, linear=True)
    return list(out)


def _match_cvd_token(token: str) -> str:
    key = token.lower()
    matches = [choice for choice in _CVD_CHOICES if choice.startswith(key)]
    if len(matches) != 1:
        raise ValueError(f"'{token}' is not a valid CVD emulation name")
    if matches[0] == "deutan":
        return "deuteranope"
    return matches[0]


def _cvd_row_names(cvd: bool | Sequence[str]) -> list[str]:
    if cvd is False:
        return []
    if cvd is True:
        tokens = ["deutan", "protan", "tritan", "desaturate"]
    elif isinstance(cvd, str):
        tokens = [cvd]
    else:
        tokens = list(cvd)
    mapped = [_match_cvd_token(t) for t in tokens]
    pretty = [name[0].upper() + name[1:] if name else name for name in mapped]
    return ["Original", *pretty]


def _cvd_transform_row(colors: Sequence[str], row_name: str) -> list[str]:
    as_char = [str(c) for c in colors]
    if row_name == "Original":
        return as_char
    if row_name == "Deuteranope":
        return [str(c) for c in deutan(as_char)]
    if row_name == "Protanope":
        return [str(c) if c is not None else None for c in _protan(as_char)]  # type: ignore[misc]
    if row_name == "Tritanope":
        return [str(c) if c is not None else None for c in _tritan(as_char)]  # type: ignore[misc]
    if row_name == "Desaturated":
        return [str(c) for c in desaturate(as_char)]
    raise ValueError(row_name)


def _as_block_list(x: Any, extra: Sequence[Any], named: Mapping[str, Any]) -> list[tuple[str | None, Any]]:
    blocks: list[tuple[str | None, Any]] = []
    if x is None:
        pass
    elif isinstance(x, dict):
        for key, val in x.items():
            blocks.append((str(key), val))
    elif hasattr(x, "to_numpy") and hasattr(x, "columns"):
        blocks.append((None, x.to_numpy()))
    elif isinstance(x, (list, tuple)):
        for item in x:
            blocks.append((None, item))
    else:
        blocks.append((None, x))
    for item in extra:
        blocks.append((None, item))
    for key, val in named.items():
        blocks.append((key, val))
    return blocks


def _block_ncol(block: Any) -> int:
    arr = np.asarray(block, dtype=object)
    if arr.ndim == 1:
        return arr.shape[0]
    return arr.shape[1]


def _apply_cvd(block: Any, cvd: bool | str | Sequence[str]) -> np.ndarray:
    rows_wanted = _cvd_row_names(cvd)
    return np.asarray([_cvd_transform_row(block, name) for name in rows_wanted], dtype=object)


def _matrix_from_block(block: Any, *, ncol: int) -> tuple[np.ndarray, list[str]]:
    arr = np.asarray(block, dtype=object)
    if arr.ndim == 1:
        arr = arr.reshape(1, -1)
    out = np.empty(arr.shape, dtype=object)
    for idx, val in np.ndenumerate(arr):
        if val is None or (isinstance(val, float) and np.isnan(val)):
            out[idx] = "transparent"
        else:
            out[idx] = str(val)
    if out.shape[1] < ncol:
        pad = np.full((out.shape[0], ncol - out.shape[1]), "transparent", dtype=object)
        out = np.hstack([out, pad])
    rownames = [""] * out.shape[0]
    return out, rownames


def _prepare_matrix(
    blocks: list[tuple[str | None, Any]],
    *,
    cvd: bool | str | Sequence[str],
) -> SwatchMatrix:
    if cvd is not False:
        blocks = [(name, _apply_cvd(val, cvd)) for name, val in blocks]

    ncol = max((_block_ncol(val) for _, val in blocks), default=0)
    pieces: list[tuple[np.ndarray, list[str]]] = []
    for name, block in blocks:
        mat, rownames = _matrix_from_block(block, ncol=ncol)
        if name is not None:
            if mat.shape[0] == 1 and rownames == [""]:
                rownames = [name]
            else:
                header = np.full((1, ncol), "transparent", dtype=object)
                pieces.append((header, [name]))
        pieces.append((mat, rownames))

    if not pieces:
        return SwatchMatrix(np.empty((0, 0), dtype=object), [], [])

    rows_out: list[list[Any]] = []
    rownames_out: list[str] = []
    for mat, rownames in pieces:
        for r in range(mat.shape[0]):
            rows_out.append([mat[r, c] for c in range(ncol)])
            rownames_out.append(rownames[r])
    out = np.asarray(rows_out, dtype=object)
    out[out == None] = "transparent"  # noqa: E711
    colnames = [f"Color {i}" for i in range(1, ncol + 1)]
    return SwatchMatrix(out, rownames_out, colnames)


def _plot_matrix(
    x: SwatchMatrix,
    *,
    nrow: int,
    border: str | None,
    sborder: str | None,
    off: Sequence[float] | None,
    line: float | None,
    cex: float | Sequence[float] | None,
    font: Sequence[int],
    save_path: str | None,
) -> None:
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle

    values = x.values
    rownames = x.rownames
    m, n = values.shape
    rnam = [rownames[i] for i in range(m) if values[i, 0] != "transparent"]

    if cex is None:
        cex_val = 0.7 if m > 15 else 1.0
    else:
        cex_val = float(cex) if not isinstance(cex, (list, tuple)) else float(cex[0])
    if not isinstance(cex, (list, tuple)) or len(cex) < 2:
        cex_pair = (1.0 * cex_val, 1.4 * cex_val)
    else:
        cex_pair = (float(cex[0]), float(cex[1]))

    mcex = np.full(m, cex_pair[0], dtype=np.float64)
    mcex[values[:, 0] == "transparent"] = cex_pair[1]
    mfont = np.full(m, int(font[0]), dtype=np.int64)
    if len(font) >= 2:
        mfont[values[:, 0] == "transparent"] = int(font[1])

    if line is None:
        if rnam:
            lin = cex_pair[0] * (0.5 + max((len(s) for s in rnam), default=0) - 1) / 2.25
        else:
            lin = cex_pair[0] * 0.5
    else:
        lin = float(line)
    lin = max(0.08, lin)

    if m > 1:
        nc = math.ceil(m / nrow)
        nr = math.ceil(m / nc)
    else:
        nc = 1
        nr = 1

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

    border_mat = np.full((m, n), border_color, dtype=object)
    border_mat[values == "transparent"] = "transparent"

    if sborder is None:
        sborder_vec = np.where(
            (border_mat[:, 0] == "transparent") & (off_arr[0] >= 1.0),
            "lightgray",
            "transparent",
        )
    else:
        sborder_vec = np.full(m, sborder, dtype=object)
    transparent_rows = np.all(values == "transparent", axis=1)
    sborder_vec[transparent_rows] = "transparent"

    fig_w = max(7.0, 7.0 * nc * 0.85)
    fig_h = max(5.0, m * 0.45)
    fig, axes = plt.subplots(1, nc, figsize=(fig_w, fig_h), squeeze=False)

    left_margin = 0.08 + lin * 0.12
    fig.subplots_adjust(left=left_margin, right=0.99, top=0.99, bottom=0.01, wspace=0.15)

    for panel in range(nc):
        ax = axes[0, panel]
        rows = np.where(col_idx == panel + 1)[0]
        xi = values[rows, :]
        nri = xi.shape[0]
        ax.set_xlim(0.0, 1.0 - (1.0 - off_arr[0]) / n)
        ax.set_ylim(0.0, 1.0 - (1.0 - off_arr[1]) / nr)
        ax.axis("off")

        y_base = np.arange(nr - 1, nr - nri - 1, -1, dtype=np.float64) / nr
        for row_i in range(nri):
            y0 = y_base[row_i]
            global_row = rows[row_i]
            label = rownames[global_row]
            weight = "bold" if mfont[global_row] == 2 else "normal"
            ax.text(
                -0.02,
                y0 + 0.5 * off_arr[1] / nr,
                label,
                transform=ax.transData,
                ha="right",
                va="center",
                fontsize=9 * mcex[global_row],
                fontweight=weight,
            )
            for col_i in range(n):
                color = xi[row_i, col_i]
                bord = border_mat[global_row, col_i]
                if color == "transparent":
                    face = "none"
                    edge: str | None = "none"
                else:
                    face = str(color)
                    edge = str(bord) if bord != "transparent" else "none"
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
            sb = sborder_vec[global_row]
            if sb != "transparent":
                ax.add_patch(
                    Rectangle(
                        (0.0, y0),
                        1.0,
                        off_arr[1] / nr,
                        facecolor="none",
                        edgecolor=str(sb),
                        linewidth=0.5,
                    )
                )

    if save_path is not None:
        fig.savefig(save_path, format="svg")
        plt.close(fig)
    else:
        plt.show()


def swatchplot(
    x: Any = None,
    /,
    *args: Any,
    nrow: int = 20,
    border: str | None = None,
    sborder: str | None = None,
    off: float | Sequence[float] | None = None,
    mar: Sequence[float] | None = None,
    line: float | None = None,
    cex: float | Sequence[float] | None = None,
    font: Sequence[int] = (1, 2),
    cvd: bool | str | Sequence[str] = False,
    plot: bool = True,
    save_path: str | None = None,
    **kwargs: Any,
) -> SwatchMatrix:
    """Draw palette swatches and return the underlying color matrix."""
    palettes = {k: v for k, v in kwargs.items() if k not in _RESERVED}
    blocks = _as_block_list(x, args, palettes)
    mat = _prepare_matrix(blocks, cvd=cvd)
    if mat.values.size == 0:
        return mat

    if plot:
        off_seq: Sequence[float] | None
        if off is None:
            off_seq = None
        elif isinstance(off, (int, float)):
            off_seq = (float(off),)
        else:
            off_seq = off
        _plot_matrix(
            mat,
            nrow=nrow,
            border=border,
            sborder=sborder,
            off=off_seq,
            line=line,
            cex=cex,
            font=font,
            save_path=save_path,
        )
    return mat


def matrix_to_proof_dict(mat: SwatchMatrix) -> dict[str, Any]:
    """Serialize swatchplot matrix for R comparison proofs."""
    rows = []
    for r in range(mat.values.shape[0]):
        rows.append([None if v == "transparent" else str(v) for v in mat.values[r, :]])
    return {"rownames": list(mat.rownames), "colnames": list(mat.colnames), "rows": rows}
