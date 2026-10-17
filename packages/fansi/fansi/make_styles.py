"""CSS rules for fansi color classes, from make_styles in R/tohtml.R."""

from __future__ import annotations

from fansi._args import FansiError
from fansi._const import CLR_256
from fansi._state import Color
from fansi.to_html import check_classes, color_to_html


def col2rgb(color):
    """Three channels in 0..255 for a `#RRGGBB` color."""
    if not isinstance(color, str) or len(color) != 7 or color[0] != "#":
        raise FansiError("col2rgb expects a #RRGGBB color.")
    try:
        red = int(color[1:3], 16)
        green = int(color[3:5], 16)
        blue = int(color[5:7], 16)
    except ValueError as exc:
        raise FansiError("col2rgb expects a #RRGGBB color.") from exc
    return (red, green, blue)


def rgb(values, max_color_value=255):
    """`#RRGGBB` from three channels. `maxColorValue=255` truncates toward zero."""
    if max_color_value != 255:
        scaled = [channel * 255.0 / max_color_value for channel in values]
    else:
        scaled = list(values)
    channels = []
    for channel in scaled:
        if channel < 0 or channel > 255:
            raise FansiError(f"color intensity {channel}, not in 0:255")
        channels.append(int(channel))
    return "#" + "".join(f"{channel:02X}" for channel in channels)


def _as_classes(classes):
    if isinstance(classes, str):
        values = [classes]
    elif isinstance(classes, (list, tuple)) and all(
        item is None or isinstance(item, str) for item in classes
    ):
        values = list(classes)
    else:
        raise FansiError("Argument `classes` is not character.")
    return check_classes(values)


def _as_mix(rgb_mix):
    if rgb_mix is None:
        return [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]]
    if (
        not isinstance(rgb_mix, (list, tuple))
        or len(rgb_mix) != 3
        or any(not isinstance(row, (list, tuple)) or len(row) != 3 for row in rgb_mix)
    ):
        raise FansiError(
            "Argument `rgb.mix` must be a 3 x 3 numeric matrix with no NAs."
        )
    mix = []
    for row in rgb_mix:
        converted = []
        for value in row:
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise FansiError(
                    "Argument `rgb.mix` must be a 3 x 3 numeric matrix with no NAs."
                )
            if value != value:
                raise FansiError(
                    "Argument `rgb.mix` must be a 3 x 3 numeric matrix with no NAs."
                )
            converted.append(float(value))
        mix.append(converted)
    return mix


def _is_identity(mix):
    for row in range(3):
        for col in range(3):
            expected = 1.0 if row == col else 0.0
            if mix[row][col] != expected:
                return False
    return True


def _palette(count):
    """256-color HTML hex for indexes 0..count-1, each repeated for fg and bg."""
    colors = []
    for index in range(count):
        color = Color()
        color.x = 8 | CLR_256
        color.extra[0] = index
        rendered = color_to_html(color)
        colors.append(rendered)
        colors.append(rendered)
    return colors


def make_styles(classes, rgb_mix=None):
    """CSS mapping each class to an 8-bit color, optionally remixed."""
    names = _as_classes(classes)
    mix = _as_mix(rgb_mix)
    colors = _palette(len(names) // 2)
    if not _is_identity(mix):
        remixed = []
        for hex_color in colors:
            red, green, blue = col2rgb(hex_color)
            channels = []
            for column in range(3):
                value = (
                    red * mix[0][column]
                    + green * mix[1][column]
                    + blue * mix[2][column]
                )
                if value > 255:
                    value = 255
                elif value < 0:
                    value = 0
                channels.append(value)
            remixed.append(rgb(channels, max_color_value=255))
        colors = remixed
    kinds = ("color", "background-color")
    return [
        f".{name} {{{kinds[index % 2]}: {hex_color};}}"
        for index, (name, hex_color) in enumerate(zip(names, colors))
    ]
