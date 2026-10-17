"""Pad strings to a display width, the way stringi 1.8.9 does.

``stri_pad`` is the wrapper. It picks ``left``, ``right``, or ``both``
with R's ``match.arg`` and calls ``stri_pad_left``, ``stri_pad_right``,
or ``stri_pad_both``. Width is display width from ``stri_width`` unless
``use_length`` is true, in which case each code point counts as 1.
The default width is 72, which is ``floor(0.9 * 80)``, Rscript's
``floor(0.9 * getOption("width"))``.

A missing character is ``stringi._na.NA``. The string ``"NA"`` is text.
An odd ``both`` pad puts the extra copy on the right.
"""

from __future__ import annotations

import math
import warnings

from stringi._na import NA, is_na
from stringi.length import _prepare, stri_width

_DEFAULT_WIDTH = 72
_INT_MIN = -2147483647
_INT_MAX = 2147483647
_SIDES = ("left", "right", "both")
_SIDE_ERROR = "'arg' should be one of “left”, “right”, “both”"


def _warn(message: str) -> None:
    warnings.warn(message, UserWarning, stacklevel=2)


def _vector(value) -> bool:
    return isinstance(value, (list, tuple, range))


def _finish(result: list, scalar: bool):
    if scalar and len(result) == 1:
        return result[0]
    return result


def _recycle(lengths: list[int]) -> int:
    if any(n <= 0 for n in lengths):
        return 0
    longest = max(lengths)
    if any(longest % n != 0 for n in lengths):
        _warn("longer object length is not a multiple of shorter object length")
    return longest


def _one_integer(value):
    if is_na(value):
        return NA, False
    if isinstance(value, bool):
        return int(value), False
    if isinstance(value, int):
        if _INT_MIN <= value <= _INT_MAX:
            return value, False
        return NA, True
    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            return NA, True
        truncated = math.trunc(value)
        if truncated < _INT_MIN or truncated > _INT_MAX:
            return NA, True
        return int(truncated), False
    if isinstance(value, str):
        token = value[1:] if value.startswith(("+", "-")) else value
        if token.isdigit() and value not in ("+", "-"):
            number = int(value)
            if _INT_MIN <= number <= _INT_MAX:
                return number, False
        return NA, True
    raise TypeError(
        "argument `width` should be an integer vector (or an object coercible to)"
    )


def _prepare_integer(value) -> list:
    if value is None:
        return []
    if isinstance(value, range):
        items = list(value)
    elif isinstance(value, (list, tuple)):
        items = list(value)
    else:
        items = [value]
    result = []
    introduced = False
    for item in items:
        number, coerced = _one_integer(item)
        if coerced:
            introduced = True
        result.append(number)
    if introduced:
        _warn("NAs introduced by coercion")
    return result


def _logical_1(value, name: str) -> bool:
    if isinstance(value, (list, tuple)):
        if len(value) == 0:
            raise ValueError(f"argument `{name}` should be a non-empty vector")
        if len(value) > 1:
            _warn(
                f"argument `{name}` should be a single logical value; "
                "only the first element is used"
            )
        value = value[0]
    if is_na(value):
        raise ValueError(f"missing values in argument `{name}` is not supported")
    if isinstance(value, bool):
        return value
    raise TypeError(f"argument `{name}` should be a single logical value")


def _match_side(side) -> str:
    if isinstance(side, (list, tuple)):
        if list(side) == list(_SIDES):
            return "left"
        if len(side) != 1:
            raise ValueError(_SIDE_ERROR)
        side = side[0]
    if is_na(side) or not isinstance(side, str):
        raise ValueError(_SIDE_ERROR)
    if side in _SIDES:
        return side
    hits = [name for name in _SIDES if name.startswith(side)]
    if len(hits) == 1:
        return hits[0]
    raise ValueError(_SIDE_ERROR)


def _measure(text: str, use_length: bool) -> int:
    if use_length:
        return len(text)
    return stri_width(text)


def _check_pad(pad: str, use_length: bool) -> None:
    if use_length:
        if len(pad) != 1:
            raise ValueError(
                "each string in `pad` should consist of exactly 1 code points"
            )
        return
    if stri_width(pad) != 1:
        raise ValueError(
            "each string in `pad` should consist of code points of total width 1"
        )


def _apply(text: str, width: int, pad: str, side: str) -> str:
    if side == "left":
        return pad * width + text
    if side == "right":
        return text + pad * width
    left = width // 2
    return pad * left + text + pad * (width - left)


def _pad(str, width, pad, side: str, use_length) -> object:
    texts, str_scalar = _prepare(str)
    widths = _prepare_integer(width)
    pads, pad_scalar = _prepare(pad)
    use_code_points = _logical_1(use_length, "use_length")
    count = _recycle([len(texts), len(widths), len(pads)])
    if count == 0:
        return []
    scalar = str_scalar and pad_scalar and not _vector(width)
    result = []
    for index in range(count):
        text = texts[index % len(texts)]
        wide = widths[index % len(widths)]
        filler = pads[index % len(pads)]
        if is_na(text) or is_na(wide) or is_na(filler):
            result.append(NA)
            continue
        _check_pad(filler, use_code_points)
        current = _measure(text, use_code_points)
        if current >= wide:
            result.append(text)
            continue
        result.append(_apply(text, wide - current, filler, side))
    return _finish(result, scalar)


def stri_pad_left(str, width=_DEFAULT_WIDTH, pad=" ", use_length=False):
    """Add ``pad`` on the left until each string reaches ``width``.

    ``width`` is display width unless ``use_length`` is true. A string that
    is already wide enough is unchanged. A missing string, width, or pad
    yields a missing result.
    """

    return _pad(str, width, pad, "left", use_length)


def stri_pad_right(str, width=_DEFAULT_WIDTH, pad=" ", use_length=False):
    """Add ``pad`` on the right until each string reaches ``width``.

    ``width`` is display width unless ``use_length`` is true. A string that
    is already wide enough is unchanged. A missing string, width, or pad
    yields a missing result.
    """

    return _pad(str, width, pad, "right", use_length)


def stri_pad_both(str, width=_DEFAULT_WIDTH, pad=" ", use_length=False):
    """Add ``pad`` on both sides until each string reaches ``width``.

    The extra pad of an odd gap goes on the right. ``width`` is display
    width unless ``use_length`` is true. A missing string, width, or pad
    yields a missing result.
    """

    return _pad(str, width, pad, "both", use_length)


def stri_pad(str, width=_DEFAULT_WIDTH, side="left", pad=" ", use_length=False):
    """Pad on the side chosen by ``match.arg``.

    ``left`` is the default. A unique prefix such as ``"r"`` or ``"b"``
    selects ``right`` or ``both``. The call then uses ``stri_pad_left``,
    ``stri_pad_right``, or ``stri_pad_both``.
    """

    chosen = _match_side(side)
    if chosen == "both":
        return stri_pad_both(str, width, pad, use_length)
    if chosen == "right":
        return stri_pad_right(str, width, pad, use_length)
    return stri_pad_left(str, width, pad, use_length)
