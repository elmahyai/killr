"""ANSI style functions from cli's create_ansi_style."""

from __future__ import annotations

import json
import math
import re
from functools import lru_cache
from pathlib import Path

from cli.num_ansi_colors import num_ansi_colors, truecolor

_HASH_COLOR = re.compile(r"^#([A-Fa-f0-9]{6}|[A-Fa-f0-9]{8})$")

_FG_RGB = {
    "black": (0, 0, 0),
    "red": (255, 0, 0),
    "green": (0, 255, 0),
    "yellow": (255, 255, 0),
    "blue": (0, 0, 255),
    "magenta": (255, 0, 255),
    "cyan": (0, 255, 255),
    "white": (255, 255, 255),
    "silver": (190, 190, 190),
}
_BG_RGB = {f"bg_{name}": rgb for name, rgb in _FG_RGB.items() if name != "silver"}


def _style_str(codes: int | list[int]) -> str:
    """One CSI sequence per code. paste0 recycles, it does not join with semicolons."""

    if isinstance(codes, int):
        codes = [codes]
    return "".join(f"\x1b[{code}m" for code in codes)


def _palette_idx(code: int) -> int:
    if code < 38:
        return code - 29
    if code < 48:
        return -(code - 39)
    if code < 98:
        return code - 81
    return -(code - 91)


def _entry(open_codes, close_codes, palette: bool):
    opened = open_codes[0] if isinstance(open_codes, list) else open_codes
    return {
        "open": _style_str(open_codes),
        "close": _style_str(close_codes),
        "palette": _palette_idx(opened) if palette else None,
    }


_BUILTIN: dict[str, dict] = {
    "reset": _entry(0, [0, 22, 23, 24, 27, 28, 29, 39, 49], False),
    "bold": _entry(1, 22, False),
    "blurred": _entry(2, 22, False),
    "italic": _entry(3, 23, False),
    "underline": _entry(4, 24, False),
    "inverse": _entry(7, 27, False),
    "hidden": _entry(8, 28, False),
    "strikethrough": _entry(9, 29, False),
    "black": _entry(30, 39, True),
    "red": _entry(31, 39, True),
    "green": _entry(32, 39, True),
    "yellow": _entry(33, 39, True),
    "blue": _entry(34, 39, True),
    "magenta": _entry(35, 39, True),
    "cyan": _entry(36, 39, True),
    "white": _entry(37, 39, True),
    "silver": _entry(90, 39, False),
    "br_black": _entry(90, 39, True),
    "br_red": _entry(91, 39, True),
    "br_green": _entry(92, 39, True),
    "br_yellow": _entry(93, 39, True),
    "br_blue": _entry(94, 39, True),
    "br_magenta": _entry(95, 39, True),
    "br_cyan": _entry(96, 39, True),
    "br_white": _entry(97, 39, True),
    "bg_black": _entry(40, 49, True),
    "bg_red": _entry(41, 49, True),
    "bg_green": _entry(42, 49, True),
    "bg_yellow": _entry(43, 49, True),
    "bg_blue": _entry(44, 49, True),
    "bg_magenta": _entry(45, 49, True),
    "bg_cyan": _entry(46, 49, True),
    "bg_white": _entry(47, 49, True),
    "bg_br_black": _entry(100, 49, True),
    "bg_br_red": _entry(101, 49, True),
    "bg_br_green": _entry(102, 49, True),
    "bg_br_yellow": _entry(103, 49, True),
    "bg_br_blue": _entry(104, 49, True),
    "bg_br_magenta": _entry(105, 49, True),
    "bg_br_cyan": _entry(106, 49, True),
    "bg_br_white": _entry(107, 49, True),
    "no_bold": _entry([0, 23, 24, 27, 28, 29, 39, 49], 22, False),
    "no_blurred": _entry([0, 23, 24, 27, 28, 29, 39, 49], 22, False),
    "no_italic": _entry([0, 22, 24, 27, 28, 29, 39, 49], 23, False),
    "no_underline": _entry([0, 22, 23, 27, 28, 29, 39, 49], 24, False),
    "no_inverse": _entry([0, 22, 23, 24, 28, 29, 39, 49], 27, False),
    "no_hidden": _entry([0, 22, 23, 24, 27, 29, 39, 49], 28, False),
    "no_strikethrough": _entry([0, 22, 23, 24, 27, 28, 39, 49], 29, False),
    "none": _entry([0, 22, 23, 24, 27, 28, 29, 49], 39, False),
    "no_color": _entry([0, 22, 23, 24, 27, 28, 29, 49], 39, False),
    "bg_none": _entry([0, 22, 23, 24, 27, 28, 29, 39], 49, False),
    "no_bg_color": _entry([0, 22, 23, 24, 27, 28, 29, 39], 49, False),
}


class AnsiString(str):
    """Character data that cli would mark as cli_ansi_string."""


class AnsiStyle:
    """A function that wraps text in one or more ANSI styles."""

    def __init__(self, styles: list[dict]):
        self._styles = styles

    def __call__(self, *args):
        return apply_styles(self._styles, args)


def _paste0(args: tuple) -> list[str]:
    columns: list[list[str]] = []
    for arg in args:
        if isinstance(arg, (list, tuple)):
            columns.append(["" if item is None else str(item) for item in arg])
        else:
            columns.append(["" if arg is None else str(arg)])
    if not columns:
        return [""]
    if any(len(column) == 0 for column in columns):
        return []
    width = max(len(column) for column in columns)
    rows = []
    for index in range(width):
        rows.append("".join(column[index % len(column)] for column in columns))
    return rows


def apply_styles(styles: list[dict], args: tuple):
    rows = _paste0(args)
    if not rows:
        return []
    count = num_ansi_colors()
    styled = []
    for text in rows:
        if count > 1:
            # A length-1 string, including "", is styled. An empty vector is not.
            for style in reversed(styles):
                text = (
                    style["open"]
                    + text.replace(style["close"], style["open"])
                    + style["close"]
                )
        styled.append(AnsiString(text))
    if len(styled) == 1:
        return styled[0]
    return styled


def _nearest(rgb: tuple[int, int, int], table: dict[str, tuple[int, int, int]]) -> str:
    best_name = ""
    best = None
    for name, color in table.items():
        dist = sum((color[i] - rgb[i]) ** 2 for i in range(3))
        if best is None or dist < best:
            best = dist
            best_name = name
    return best_name


def _ansi_scale(value: float, to: tuple[float, float] = (0, 5)) -> float:
    return (value - 0) / 255 * (to[1] - to[0]) + to[0]


def _r_round(value: float) -> int:
    return int(round(value))


def _ansi256_color(red: float, green: float, blue: float) -> int:
    gray_possible = True
    sep = 42.5
    gray = False
    while gray_possible:
        if red < sep or green < sep or blue < sep:
            gray = red < sep and green < sep and blue < sep
            gray_possible = False
        sep += 42.5
    if gray:
        return 232 + _r_round((red + green + blue) / 33)
    return (
        16
        + math.floor(6 * red / 256) * 36
        + math.floor(6 * green / 256) * 6
        + math.floor(6 * blue / 256)
    )


def _from_rgb(rgb: tuple[int, int, int], bg: bool, colors: int, grey: bool) -> dict:
    if colors < 256:
        table = _BG_RGB if bg else _FG_RGB
        name = _nearest(rgb, table)
        builtin = _BUILTIN[name]
        return {"open": builtin["open"], "close": builtin["close"], "palette": None}
    if colors < truecolor or grey:
        if grey:
            level = _r_round(_ansi_scale(rgb[0], (0, 23)))
            color = 232 + level
        else:
            color = _ansi256_color(rgb[0], rgb[1], rgb[2])
        opened = f"\x1b[{48 if bg else 38};5;{color}m"
        return {"open": opened, "close": "\x1b[49m" if bg else "\x1b[39m", "palette": None}
    channels = ";".join(str(int(channel)) for channel in rgb[:3])
    if bg:
        return {"open": f"\x1b[48;2;{channels}m", "close": "\x1b[49m", "palette": None}
    return {"open": f"\x1b[38;2;{channels}m", "close": "\x1b[39m", "palette": None}


@lru_cache(maxsize=1)
def _r_colors() -> dict[str, tuple[int, int, int]]:
    path = Path(__file__).resolve().parent / "data" / "r_colors.json"
    raw = json.loads(path.read_text())
    return {name: (int(rgb[0]), int(rgb[1]), int(rgb[2])) for name, rgb in raw.items()}


def _hex_rgb(text: str) -> tuple[int, int, int]:
    digits = text[1:7]
    return (int(digits[0:2], 16), int(digits[2:4], 16), int(digits[4:6], 16))


def _is_rgb(value) -> bool:
    if isinstance(value, (str, bytes)) or isinstance(value, AnsiStyle):
        return False
    try:
        items = list(value)
    except TypeError:
        return False
    return len(items) in (3, 4) and all(isinstance(item, (int, float)) and not isinstance(item, bool) for item in items)


def make_ansi_style(*spec, bg: bool = False, grey: bool = False, colors: int | None = None) -> AnsiStyle:
    """Build a style function from a builtin name, an R color, or RGB."""

    if not spec:
        raise ValueError("style must be an ANSI style")
    style = spec[0]
    if isinstance(style, AnsiStyle):
        return style
    if colors is None:
        colors = num_ansi_colors()
    if style == "dim":
        style = "blurred"
    if isinstance(style, str) and style in _BUILTIN:
        name = style
        if bg and not name.startswith("bg_"):
            name = "bg_" + name
        if name not in _BUILTIN:
            raise ValueError(f"Unknown style specification: {style}")
        return AnsiStyle([dict(_BUILTIN[name])])
    rgb = None
    if isinstance(style, str) and _HASH_COLOR.match(style):
        rgb = _hex_rgb(style)
    elif isinstance(style, str) and style in _r_colors():
        rgb = _r_colors()[style]
    elif _is_rgb(style):
        items = [int(item) for item in list(style)[:3]]
        rgb = (items[0], items[1], items[2])
    if rgb is None:
        raise ValueError(
            "Unknown style specification. It must be a builtin cli style, "
            "an R color name, a #rrggbb string, or three RGB numbers."
        )
    return AnsiStyle([_from_rgb(rgb, bg, int(colors), grey)])


def combine_ansi_styles(*styles) -> AnsiStyle:
    """Combine styles. The right-most style is applied first."""

    collected: list[dict] = []
    for style in styles:
        made = make_ansi_style(style)
        collected.extend(dict(item) for item in made._styles)
    return AnsiStyle(collected)


_EXPORT_KEYS = {
    "bg_black": "bg_black",
    "bg_blue": "bg_blue",
    "bg_cyan": "bg_cyan",
    "bg_green": "bg_green",
    "bg_magenta": "bg_magenta",
    "bg_red": "bg_red",
    "bg_white": "bg_white",
    "bg_yellow": "bg_yellow",
    "bg_none": "no_bg_color",
    "bg_br_black": "bg_br_black",
    "bg_br_blue": "bg_br_blue",
    "bg_br_cyan": "bg_br_cyan",
    "bg_br_green": "bg_br_green",
    "bg_br_magenta": "bg_br_magenta",
    "bg_br_red": "bg_br_red",
    "bg_br_white": "bg_br_white",
    "bg_br_yellow": "bg_br_yellow",
    "col_black": "black",
    "col_blue": "blue",
    "col_cyan": "cyan",
    "col_green": "green",
    "col_magenta": "magenta",
    "col_red": "red",
    "col_white": "white",
    "col_yellow": "yellow",
    "col_grey": "silver",
    "col_silver": "silver",
    "col_none": "no_color",
    "col_br_black": "br_black",
    "col_br_blue": "br_blue",
    "col_br_cyan": "br_cyan",
    "col_br_green": "br_green",
    "col_br_magenta": "br_magenta",
    "col_br_red": "br_red",
    "col_br_white": "br_white",
    "col_br_yellow": "br_yellow",
    "style_dim": "blurred",
    "style_blurred": "blurred",
    "style_bold": "bold",
    "style_hidden": "hidden",
    "style_inverse": "inverse",
    "style_italic": "italic",
    "style_reset": "reset",
    "style_strikethrough": "strikethrough",
    "style_underline": "underline",
    "style_no_bold": "no_bold",
    "style_no_blurred": "no_blurred",
    "style_no_dim": "no_blurred",
    "style_no_italic": "no_italic",
    "style_no_underline": "no_underline",
    "style_no_inverse": "no_inverse",
    "style_no_hidden": "no_hidden",
    "style_no_strikethrough": "no_strikethrough",
    "style_no_color": "no_color",
    "style_no_bg_color": "no_bg_color",
}

for _export, _key in _EXPORT_KEYS.items():
    globals()[_export] = AnsiStyle([dict(_BUILTIN[_key])])
