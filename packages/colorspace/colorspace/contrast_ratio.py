"""W3C and APCA contrast ratios between colors (colorspace 2.1-4)."""

from __future__ import annotations

import json
from collections.abc import Sequence
from functools import lru_cache
from pathlib import Path

import numpy as np

_ALGORITHMS = ("WCAG", "APCA")
_WCAG_COEF = np.array([0.2126, 0.7152, 0.0722], dtype=np.float64)
_APCA_COEF = np.array(
    [0.2126478133913640, 0.7151791475336150, 0.0721730390750208],
    dtype=np.float64,
)
_HEX_DIGITS = frozenset("0123456789abcdefABCDEF")
_DEFAULT_PALETTE = (
    "black",
    "#DF536B",
    "#61D04F",
    "#2297E6",
    "#28E2E5",
    "#CD0BBC",
    "#F5C710",
    "gray62",
)


@lru_cache(maxsize=1)
def _r_colors() -> dict[str, tuple[int, int, int]]:
    path = Path(__file__).resolve().parent / "r_colors.json"
    raw = json.loads(path.read_text(encoding="utf-8"))
    return {name: (int(rgb[0]), int(rgb[1]), int(rgb[2])) for name, rgb in raw.items()}


def contrast_ratio(
    col,
    col2="white",
    algorithm="WCAG",
    plot=False,
    border=False,
    cex=2,
    off=0.05,
    mar=(0.5, 0.5, 0.5, 0.5),
    digits=2,
    **kwargs,
):
    """Contrast ratio for pairs of colors under WCAG or APCA."""
    col_vec = _color_vector(col)
    col2_vec = _color_vector(col2)
    if len(col_vec) < 1 or len(col2_vec) < 1:
        raise ValueError("both 'col' and 'col2' need to specify at least one color")

    algorithm = _match_algorithm(algorithm)
    n = max(len(col_vec), len(col2_vec))
    if not (len(col_vec) == n and len(col2_vec) == n):
        col_vec = _rep_len(col_vec, n)
        col2_vec = _rep_len(col2_vec, n)

    lum = _relative_luminance(col_vec, algorithm)
    lum2 = _relative_luminance(col2_vec, algorithm)

    if algorithm == "WCAG":
        ratio = (lum + 0.05) / (lum2 + 0.05)
        flip = ratio < 1
        ratio[flip] = 1.0 / ratio[flip]
    else:
        normal = _apca_polarity(lum, lum2)
        reverse = _apca_polarity(lum2, lum)
        ratio = np.column_stack((normal, reverse))

    plot_flags = _rep_len_plot(plot, 2)
    if any(plot_flags):
        _plot_swatches(
            col_vec,
            col2_vec,
            ratio,
            algorithm,
            plot_flags,
            border,
            cex,
            off,
            mar,
            digits,
            kwargs,
        )
    return ratio


def _relative_luminance(colors, algorithm):
    rgb = _col2rgb_matrix(colors) / 255.0
    if algorithm == "WCAG":
        rgb = np.where(
            rgb <= 0.03928,
            rgb / 12.92,
            np.power((rgb + 0.055) / 1.055, 2.4),
        )
        coef = _WCAG_COEF
    else:
        rgb = np.power(rgb, 2.4)
        coef = _APCA_COEF
    rlum = rgb @ coef
    if algorithm == "APCA":
        clamp = rlum <= 0.022
        rlum = rlum.copy()
        rlum[clamp] = rlum[clamp] + np.power(0.022 - rlum[clamp], 1.414)
    return rlum


def _apca_polarity(txt, bg):
    ratio = (np.power(bg, 0.56) - np.power(txt, 0.57)) * 1.14
    ratio = np.where(ratio < 0.1, 0.0, ratio - 0.027)
    rev = bg <= txt
    rev_ratio = (np.power(bg[rev], 0.65) - np.power(txt[rev], 0.62)) * 1.14
    rev_ratio = np.where(rev_ratio > -0.1, 0.0, rev_ratio + 0.027)
    ratio = ratio.copy()
    ratio[rev] = rev_ratio
    ratio[np.abs(bg - txt) < 0.0005] = 0.0
    return ratio * 100.0


def _col2rgb_matrix(colors):
    rows = [_col2rgb_one(color) for color in colors]
    return np.array(rows, dtype=np.float64)


def _col2rgb_one(color):
    if isinstance(color, (bool, np.bool_)):
        raise ValueError(f"invalid color: {color}")
    if isinstance(color, (int, np.integer)) or (
        isinstance(color, (float, np.floating)) and float(color).is_integer()
    ):
        index = int(color) - 1
        if index < 0 or index >= len(_DEFAULT_PALETTE):
            raise ValueError(f"invalid palette index: {color}")
        color = _DEFAULT_PALETTE[index]
    if not isinstance(color, str):
        raise ValueError(f"invalid color: {color}")
    if color in ("NA", "transparent"):
        return (255, 255, 255)
    if color.startswith("#"):
        red, green, blue = _parse_hex(color)
        return red, green, blue
    key = color.replace(" ", "").lower()
    try:
        return _r_colors()[key]
    except KeyError as exc:
        raise ValueError(f"invalid color name '{color}'") from exc


def _parse_hex(color):
    body = color[1:]
    size = len(body)
    if size not in (3, 4, 6, 8):
        raise ValueError("invalid RGB specification")
    if any(character not in _HEX_DIGITS for character in body):
        raise ValueError("invalid RGB specification")
    if size <= 4:
        body = "".join(character * 2 for character in body)
    red = int(body[0:2], 16)
    green = int(body[2:4], 16)
    blue = int(body[4:6], 16)
    return red, green, blue


def _color_vector(x):
    if isinstance(x, str):
        return [x]
    if isinstance(x, (int, np.integer)):
        return [int(x)]
    if isinstance(x, (float, np.floating)):
        if float(x).is_integer():
            return [int(x)]
        raise ValueError(f"invalid color: {x}")
    if isinstance(x, np.ndarray):
        if x.ndim == 0:
            item = x.item()
            return _color_vector(item)
        if x.dtype.kind in "iuf":
            return [int(v) if float(v).is_integer() else v for v in x.tolist()]
        return list(x.tolist())
    if isinstance(x, Sequence):
        if len(x) == 0:
            return []
        out = []
        for item in x:
            out.extend(_color_vector(item))
        return out
    raise ValueError(f"invalid color: {x}")


def _rep_len(values, n):
    if len(values) == n:
        return values
    if len(values) == 1:
        return values * n
    return [values[i % len(values)] for i in range(n)]


def _rep_len_plot(plot, n):
    if isinstance(plot, (bool, np.bool_)):
        return [bool(plot)] * n
    if isinstance(plot, (int, np.integer)):
        return [bool(plot)] * n
    flags = [bool(v) for v in plot]
    if len(flags) == 1:
        return flags * n
    if len(flags) < n:
        return [flags[i % len(flags)] for i in range(n)]
    return flags[:n]


def _match_algorithm(value):
    if value is None:
        raise ValueError("algorithm must be WCAG or APCA")
    text = str(value)
    for choice in _ALGORITHMS:
        if text == choice or text.startswith(choice):
            return choice
    raise ValueError(f"'{value}' is not a valid algorithm")


def _plot_swatches(
    col,
    col2,
    ratio,
    algorithm,
    plot_flags,
    border,
    cex,
    off,
    mar,
    digits,
    kwargs,
):
    import matplotlib.pyplot as plt

    n = len(col)
    if border is False:
        border_color = "none"
    elif border is True:
        border_color = None
    else:
        border_color = border
    if np.ndim(off) == 0 or len(off) == 1:
        off_y, off_x = float(off), 0.0
    else:
        off_y, off_x = float(off[0]), float(off[1])

    width = float(sum(plot_flags))
    fig, ax = plt.subplots(figsize=(max(width, 1.0), max(n, 1.0)))
    fig.subplots_adjust(
        left=mar[1] / 10.0,
        right=1.0 - mar[3] / 10.0,
        bottom=mar[2] / 10.0,
        top=1.0 - mar[0] / 10.0,
    )
    ax.set_xlim(0, width)
    ax.set_ylim(0, n)
    ax.axis("off")

    for row in range(n):
        y0 = n - row - 1
        y1 = y0 + 1 - off_y
        if plot_flags[0]:
            label = _format_ratio(ratio, algorithm, row, digits, normal=True)
            edge = col[row] if border is True else border_color
            ax.add_patch(
                plt.Rectangle(
                    (0 + off_x / 2, y0),
                    1 - off_x,
                    y1 - y0,
                    facecolor=_matplotlib_color(col2[row]),
                    edgecolor=edge if edge is not None else _matplotlib_color(col[row]),
                )
            )
            ax.text(
                (1 - off_x) / 2,
                y0 + (y1 - y0) / 2,
                label,
                ha="center",
                va="center",
                color=_matplotlib_color(col[row]),
                fontsize=cex * 6,
            )
        if plot_flags[1]:
            label = _format_ratio(ratio, algorithm, row, digits, normal=False)
            edge = col2[row] if border is True else border_color
            x_shift = plot_flags[0]
            ax.add_patch(
                plt.Rectangle(
                    (x_shift + off_x / 2, y0),
                    1 - off_x,
                    y1 - y0,
                    facecolor=_matplotlib_color(col[row]),
                    edgecolor=edge if edge is not None else _matplotlib_color(col2[row]),
                )
            )
            ax.text(
                x_shift + (1 - off_x) / 2,
                y0 + (y1 - y0) / 2,
                label,
                ha="center",
                va="center",
                color=_matplotlib_color(col2[row]),
                fontsize=cex * 6,
            )
    for key, value in kwargs.items():
        getattr(ax, f"set_{key}", lambda *_a, **_k: None)(value)
    plt.show()


def _matplotlib_color(color):
    red, green, blue = _col2rgb_one(color)
    return f"#{red:02x}{green:02x}{blue:02x}"


def _format_ratio(ratio, algorithm, row, digits, normal):
    if algorithm == "WCAG":
        value = float(ratio[row])
    elif normal:
        value = float(ratio[row, 0])
    else:
        value = float(ratio[row, 1])
    return format(round(value, digits), f".{digits}f")
