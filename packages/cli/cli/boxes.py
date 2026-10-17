"""Box borders and boxx."""

from __future__ import annotations

from cli.ansi_text import ansi_nchar
from cli.layout import _apply_style, _spaces, ansi_align, ansi_strtrim, console_width
from cli.unicode_output import is_utf8_output
from cli.utf8 import _match_arg

BORDER_STYLES = (
    "single",
    "double",
    "round",
    "single-double",
    "double-single",
    "classic",
    "none",
)

_CLASSIC = {
    "top_left": "+",
    "top_right": "+",
    "bottom_right": "+",
    "bottom_left": "+",
    "vertical": "|",
    "horizontal": "-",
}

_NONE = {key: " " for key in _CLASSIC}

_UNICODE = {
    "single": {
        "top_left": "┌",
        "top_right": "┐",
        "bottom_right": "┘",
        "bottom_left": "└",
        "vertical": "│",
        "horizontal": "─",
    },
    "double": {
        "top_left": "╔",
        "top_right": "╗",
        "bottom_right": "╝",
        "bottom_left": "╚",
        "vertical": "║",
        "horizontal": "═",
    },
    "round": {
        "top_left": "╭",
        "top_right": "╮",
        "bottom_right": "╯",
        "bottom_left": "╰",
        "vertical": "│",
        "horizontal": "─",
    },
    "single-double": {
        "top_left": "╓",
        "top_right": "╖",
        "bottom_right": "╜",
        "bottom_left": "╙",
        "vertical": "║",
        "horizontal": "─",
    },
    "double-single": {
        "top_left": "╒",
        "top_right": "╕",
        "bottom_right": "╛",
        "bottom_left": "╘",
        "vertical": "│",
        "horizontal": "═",
    },
    "classic": dict(_CLASSIC),
    "none": dict(_NONE),
}


def _styles() -> dict[str, dict[str, str]]:
    if is_utf8_output():
        return _UNICODE
    return {name: dict(_CLASSIC) if name not in ("classic", "none") else _UNICODE[name] for name in BORDER_STYLES}


def list_border_styles() -> list[str]:
    """Names of the built-in box border styles."""

    return list(BORDER_STYLES)


def _four(value) -> list[int]:
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        amount = int(value)
        return [amount, amount * 3, amount, amount * 3]
    amounts = [int(item) for item in value]
    if len(amounts) != 4:
        raise ValueError("padding and margin need one number or four")
    return amounts


def boxx(
    label,
    header="",
    footer="",
    border_style="single",
    padding=1,
    margin=0,
    float="left",
    col=None,
    background_col=None,
    border_col=None,
    align="left",
    width=None,
):
    """Draw a box around a label. The string contains the newlines."""

    if width is None:
        width = console_width()
    if border_col is None:
        border_col = col
    float = _match_arg(float, ("left", "center", "right"))
    align = _match_arg(align, ("left", "center", "right"))
    if border_style not in BORDER_STYLES:
        raise ValueError("unknown border style")
    lines = label if isinstance(label, (list, tuple)) else [label]
    lines = ["" if item is None else str(item) for item in lines]
    lines = _apply_style(lines, col)
    widest = max([ansi_nchar(item, "width") for item in lines] or [0])
    pad = _four(padding)
    mar = _four(margin)
    lines = ansi_align(lines, align=align, width=widest)
    content_width = widest + pad[1] + pad[3]
    if float == "center":
        mar_left = _spaces((width - content_width) / 2)
    elif float == "right":
        mar_left = _spaces(max(width - content_width - 2, 0))
    else:
        mar_left = _spaces(mar[1])
    lines = [""] * pad[2] + list(lines) + [""] * pad[0]
    chars = _styles()[border_style]
    pad_left = _spaces(pad[1])
    pad_right = [
        _spaces(content_width - ansi_nchar(item, "width") - pad[1]) for item in lines
    ]
    header_text = "" if header is None else str(header)
    footer_text = "" if footer is None else str(footer)
    if header_text != "":
        header_text = " " + ansi_strtrim(header_text, content_width - 2) + " "
    if footer_text != "":
        footer_text = " " + ansi_strtrim(footer_text, content_width - 2) + " "
    hdw = ansi_nchar(header_text, "width") if header_text else 0
    ftw = ansi_nchar(footer_text, "width") if footer_text else 0
    top = _apply_style(
        ("\n" * mar[2])
        + mar_left
        + chars["top_left"]
        + header_text
        + chars["horizontal"] * (content_width - hdw)
        + chars["top_right"],
        border_col,
    )
    bottom = _apply_style(
        mar_left
        + chars["bottom_left"]
        + chars["horizontal"] * (content_width - ftw)
        + footer_text
        + chars["bottom_right"]
        + ("\n" * mar[0]),
        border_col,
    )
    side = _apply_style(chars["vertical"], border_col)
    middle = []
    for item, right in zip(lines, pad_right):
        inner = _apply_style(pad_left + item + right, background_col, bg=True)
        middle.append(mar_left + side + inner + side)
    return top + "\n" + "\n".join(middle) + "\n" + bottom
