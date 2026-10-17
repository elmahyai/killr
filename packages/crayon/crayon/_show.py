"""The ANSI color tables show_ansi_colors prints."""

from __future__ import annotations

import math

from crayon._colors import grey, rgb
from crayon._detect import num_colors
from crayon._options import get_option
from crayon._style import _BUILTIN_ORDER, make_style, style
from crayon._ansi import strip_style


def _multicol(items: list[str]) -> str:
    plain = []
    for item in items:
        stripped = strip_style(item)
        plain.append(stripped if isinstance(stripped, str) else "")
    max_len = max(len(item) for item in plain)
    spaces = "            "
    padded = [item + spaces[: max_len - len(raw)] for item, raw in zip(items, plain)]
    width = int(get_option("width", 80))
    columns = int(width // max_len)
    if columns < 1:
        raise ValueError("console width is narrower than one color sample")
    rows = math.ceil(len(padded) / columns)
    padded.extend([""] * (columns * rows - len(padded)))
    lines = []
    for row in range(rows):
        chunk = padded[row * columns : (row + 1) * columns]
        lines.append("".join(chunk) + "\n")
    return "".join(lines)


def _colors_8() -> str:
    samples = []
    for name in _BUILTIN_ORDER:
        painted = style("foobar", name)
        if not isinstance(painted, str):
            painted = str(painted)
        samples.append(f"{name}: {painted} ")
    return _multicol(samples)


def _colors_256() -> str:
    blocks = []
    for red in range(6):
        for green in range(6):
            for blue in range(6):
                label = f"r:{red} g:{green} b:{blue} "
                blocks.append(
                    style(label, "grey", rgb(red, green, blue, maxColorValue=5))
                )
            blocks.append("\n")
    blocks.append("\n")
    for level in range(24):
        label = f" grey {level:2d}    "
        paint = make_style(grey(level / 23), grey=True, bg=True)
        piece = style(label, "grey", paint)
        if (level + 1) % 6:
            blocks.append(piece)
        else:
            blocks.append(piece + "\n")
    return "".join(blocks)


def show_ansi_colors(colors: int | None = None) -> None:
    if colors is None:
        colors = num_colors()
    count = int(colors)
    if count < 8:
        print("Colors are not supported")
        return None
    if count < 256:
        print(_colors_8(), end="")
        return None
    print(_colors_256(), end="")
    return None
