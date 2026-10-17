"""The grDevices color names, rgb(), grey(), and col2rgb() that make_style calls."""

from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path

_HASH = re.compile(r"^#([A-Fa-f0-9]{6}|[A-Fa-f0-9]{8})$")
_DATA = Path(__file__).resolve().parent / "data"


@lru_cache(maxsize=1)
def r_colors() -> dict[str, tuple[int, int, int]]:
    raw = json.loads((_DATA / "r_colors.json").read_text())
    return {name: (int(rgb[0]), int(rgb[1]), int(rgb[2])) for name, rgb in raw.items()}


def colors() -> list[str]:
    return list(r_colors())


def is_r_color(value: object) -> bool:
    if not isinstance(value, str):
        return False
    return value in r_colors() or _HASH.match(value) is not None


def _channel(value: float, maximum: float) -> int:
    if value < 0 or value > maximum:
        raise ValueError(f"color intensity {value}, not in [0,{maximum}]")
    return int(value * 255 / maximum + 0.5)


def rgb(red: float, green: float, blue: float, alpha: float | None = None, maxColorValue: float = 1) -> str:
    """R's rgb(). A missing alpha is omitted, so the string is #RRGGBB."""

    red_i = _channel(red, maxColorValue)
    green_i = _channel(green, maxColorValue)
    blue_i = _channel(blue, maxColorValue)
    if alpha is None:
        return f"#{red_i:02X}{green_i:02X}{blue_i:02X}"
    alpha_i = _channel(alpha, maxColorValue)
    return f"#{red_i:02X}{green_i:02X}{blue_i:02X}{alpha_i:02X}"


def grey(level: float, alpha: float | None = None, maxColorValue: float = 1) -> str:
    return rgb(level, level, level, alpha=alpha, maxColorValue=maxColorValue)


gray = grey


def col2rgb(color: str) -> tuple[int, int, int]:
    if not isinstance(color, str):
        raise TypeError("col2rgb expects a color name or a #rrggbb string")
    if color in r_colors():
        return r_colors()[color]
    match = _HASH.match(color)
    if match is None:
        raise ValueError(f"invalid color: {color}")
    digits = match.group(1)[:6]
    return (
        int(digits[0:2], 16),
        int(digits[2:4], 16),
        int(digits[4:6], 16),
    )


def r_round(value: float) -> int:
    """R's round(): ties go to the even integer."""

    return int(round(value))


def scale(value: float, from_: tuple[float, float] = (0, 255), to: tuple[float, float] = (0, 5)) -> int:
    y = (value - from_[0]) / (from_[1] - from_[0]) * (to[1] - to[0]) + to[0]
    return r_round(y)
