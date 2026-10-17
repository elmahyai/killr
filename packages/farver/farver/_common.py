"""Shared argument handling for the farver translation.

Colour-space arithmetic stays in the ``farver_kernel`` crate. This module
is the R wrapper: names, white references, and the calls in ``R/*.R``.
"""

from __future__ import annotations

import math

import numpy as np

import farver_kernel

from farver._names import NAMES

COLOURSPACES = (
    "cmy",
    "cmyk",
    "hsl",
    "hsb",
    "hsv",
    "lab",
    "hunterlab",
    "lch",
    "luv",
    "rgb",
    "xyz",
    "yxy",
    "hcl",
    "oklab",
    "oklch",
)

COLOUR_DIMS = {
    "cmy": ("c", "m", "y"),
    "cmyk": ("c", "m", "y", "k"),
    "hsl": ("h", "s", "l"),
    "hsb": ("h", "s", "b"),
    "hsv": ("h", "s", "v"),
    "lab": ("l", "a", "b"),
    "hunterlab": ("l", "a", "b"),
    "lch": ("l", "c", "h"),
    "luv": ("l", "u", "v"),
    "rgb": ("r", "g", "b"),
    "xyz": ("x", "y", "z"),
    "yxy": ("y1", "x", "y2"),
    "hcl": ("h", "c", "l"),
    "oklab": ("l", "a", "b"),
    "oklch": ("l", "c", "h"),
}

CHANNEL_INDEX = {
    space: {name: index + 1 for index, name in enumerate(names)}
    for space, names in COLOUR_DIMS.items()
}

DISTANCES = ("euclidean", "cie1976", "cie94", "cie2000", "cmc")

# R 4 default palette, including the leading transparent swatch.
PALETTE = (
    "transparent",
    "black",
    "#DF536B",
    "#61D04F",
    "#2297E6",
    "#28E2E5",
    "#CD0BBC",
    "#F5C710",
    "gray62",
)

_WHITE = {
    "2": {
        "A": (0.44757, 0.40745),
        "B": (0.34842, 0.35161),
        "C": (0.31006, 0.31616),
        "D50": (0.34567, 0.35850),
        "D55": (0.33242, 0.34743),
        "D65": (0.31271, 0.32902),
        "D75": (0.29902, 0.31485),
        "E": (1 / 3, 1 / 3),
        "F1": (0.31310, 0.33727),
        "F2": (0.37208, 0.37529),
        "F3": (0.40910, 0.39430),
        "F4": (0.44018, 0.40329),
        "F5": (0.31379, 0.34531),
        "F6": (0.37790, 0.38835),
        "F7": (0.31292, 0.32933),
        "F8": (0.34588, 0.35875),
        "F9": (0.37417, 0.37281),
        "F10": (0.34609, 0.35986),
        "F11": (0.38052, 0.37713),
        "F12": (0.43695, 0.40441),
    },
    "10": {
        "A": (0.45117, 0.40594),
        "B": (0.34980, 0.35270),
        "C": (0.31039, 0.31905),
        "D50": (0.34773, 0.35952),
        "D55": (0.33411, 0.34877),
        "D65": (0.31382, 0.33100),
        "D75": (0.29968, 0.31740),
        "E": (1 / 3, 1 / 3),
        "F1": (0.31811, 0.33559),
        "F2": (0.37925, 0.36733),
        "F3": (0.41761, 0.38324),
        "F4": (0.44920, 0.39074),
        "F5": (0.31975, 0.34246),
        "F6": (0.38660, 0.37847),
        "F7": (0.31569, 0.32960),
        "F8": (0.34902, 0.35939),
        "F9": (0.37829, 0.37045),
        "F10": (0.35090, 0.35444),
        "F11": (0.38541, 0.37123),
        "F12": (0.44256, 0.39717),
    },
}

_HEX = "0123456789abcdefABCDEF"
_DUMMY_WHITE = np.array([95.047, 100.0, 108.883], dtype=np.float64)


def colourspace_match(colour) -> int:
    """``colourspace_match``: one-based index, partial and case-insensitive."""
    if isinstance(colour, (list, tuple)) and len(colour) == 1:
        colour = colour[0]
    if not isinstance(colour, str) or colour == "":
        raise ValueError("Unknown colour space")
    name = colour.lower()
    exact = [index for index, space in enumerate(COLOURSPACES) if space == name]
    if len(exact) == 1:
        return exact[0] + 1
    partial = [index for index, space in enumerate(COLOURSPACES) if space.startswith(name)]
    if len(partial) == 1:
        return partial[0] + 1
    raise ValueError("Unknown colour space")


def distance_match(dist) -> int:
    """``distance_match``. Partial names are accepted when they are unique."""
    if isinstance(dist, (list, tuple)) and len(dist) == 1:
        dist = dist[0]
    if not isinstance(dist, str):
        raise ValueError("Unknown distance measure")
    name = dist.lower()
    exact = [index for index, item in enumerate(DISTANCES) if item == name]
    if len(exact) == 1:
        return exact[0] + 1
    partial = [index for index, item in enumerate(DISTANCES) if item.startswith(name)]
    if len(partial) == 1:
        return partial[0] + 1
    raise ValueError("Unknown distance measure")


def space_name(space_id: int) -> str:
    return COLOURSPACES[space_id - 1]


def _is_missing_number(value) -> bool:
    if value is None:
        return True
    if isinstance(value, (float, np.floating)) and math.isnan(float(value)):
        return True
    return False


def _numeric_list(value):
    if isinstance(value, (str, bytes)):
        raise ValueError("White reference must be a numeric vector")
    if isinstance(value, np.ndarray):
        if value.dtype.kind not in "iuf":
            raise ValueError("White reference must be a numeric vector")
        return [float(item) for item in value.ravel()]
    if isinstance(value, (list, tuple)):
        out = []
        for item in value:
            if isinstance(item, (bool, np.bool_)):
                out.append(float(item))
            elif _is_missing_number(item) or isinstance(item, (int, float, np.integer, np.floating)):
                out.append(float("nan") if _is_missing_number(item) else float(item))
            else:
                raise ValueError("White reference must be a numeric vector")
        return out
    if isinstance(value, (bool, np.bool_)):
        return [float(value)]
    if isinstance(value, (int, float, np.integer, np.floating)):
        if _is_missing_number(value):
            return [float("nan")]
        return [float(value)]
    raise ValueError("White reference must be a numeric vector")


def as_white_ref(x, fow=2):
    """Tristimulus white reference normalised to Y=100."""
    if isinstance(x, str) or (
        isinstance(x, (list, tuple, np.ndarray))
        and np.size(x) >= 1
        and isinstance(np.asarray(x).ravel()[0], str)
    ):
        name = x if isinstance(x, str) else str(np.asarray(x).ravel()[0])
        if isinstance(fow, str):
            key = fow
        else:
            key = str(int(fow))
        table = _WHITE.get(key)
        if table is None or name.upper() not in table:
            raise ValueError("Unknown white reference")
        x = table[name.upper()]
    values = _numeric_list(x)
    if len(values) == 2:
        x1, x2 = values
        tmp = 100.0 / x2
        values = [tmp * x1, 100.0, tmp * (1.0 - (x1 + x2))]
    elif len(values) == 3:
        if values[1] != 100.0:
            scale = 100.0 / values[1]
            values = [item * scale for item in values]
    else:
        raise ValueError(
            "White reference must be of length 2 (chromaticity) or 3 (tristimulus)"
        )
    return np.asarray(values, dtype=np.float64)


def _white_for_space(space, white):
    """R converts the white reference only when the text is not exactly ``rgb``."""
    if isinstance(space, str) and space == "rgb":
        return _DUMMY_WHITE
    return as_white_ref(white)


def as_matrix(colour) -> np.ndarray:
    """``as.matrix`` for a numeric colour table. Rows are colours."""
    if isinstance(colour, np.ndarray) and colour.dtype.kind in "iuf":
        array = np.asarray(colour, dtype=np.float64)
    else:
        array = np.asarray(colour, dtype=np.float64)
    if array.ndim == 1:
        array = array.reshape(-1, 1)
    if array.ndim != 2:
        raise ValueError("colour must be a matrix")
    return array


def prepare_alpha(alpha, nrow: int):
    """``encode_c`` alpha scaling. ``None`` means the channel is omitted."""
    if alpha is None:
        return None
    if isinstance(alpha, (str, bytes)):
        raise ValueError("alpha must be numeric")
    if isinstance(alpha, np.ndarray):
        values = [float(item) for item in np.asarray(alpha, dtype=np.float64).ravel()]
    elif isinstance(alpha, (list, tuple)):
        values = []
        for item in alpha:
            values.append(float("nan") if _is_missing_number(item) else float(item))
    elif _is_missing_number(alpha):
        values = [float("nan")]
    else:
        values = [float(alpha)]
    if len(values) == 0:
        return None
    scaled = [item * 255.0 for item in values]
    if len(scaled) == 1:
        only = scaled[0]
        if _is_missing_number(only) or only == 1.0:
            return None
        return np.asarray(scaled, dtype=np.float64)
    if len(scaled) != nrow:
        scaled = [scaled[index % len(scaled)] for index in range(nrow)]
    return np.asarray(scaled, dtype=np.float64)


def _hex_digit(char: str) -> int:
    if char not in _HEX:
        raise ValueError("Invalid hexadecimal digit")
    code = ord(char)
    return (code & 0xF) + (code >> 6) + ((code >> 6) << 3)


def _hex_byte(first: str, second: str | None = None) -> int:
    if second is None:
        value = _hex_digit(first)
        return value * 16 + value
    return _hex_digit(first) * 16 + _hex_digit(second)


def prepare_code(col: str) -> str:
    """``prepare_code``: palette numbers, then spaces stripped and lower-cased."""
    if col and col[0].isdigit():
        number = 0
        for char in col:
            if not char.isdigit():
                break
            number = number * 10 + int(char)
        code = "0" if number == 0 else str(((number - 1) % 8) + 1)
    else:
        code = col
    return code.replace(" ", "").lower()


def _lookup(name: str):
    found = NAMES.get(prepare_code(name))
    if found is None:
        raise ValueError(f"Unknown colour name: {name}")
    return found


def _palette_name(value) -> str:
    if _is_missing_number(value):
        return "NA"
    number = int(math.trunc(float(value)))
    if number <= 0:
        raise ValueError("colours encodes as numbers must be positive")
    if number == 0:
        index = 1
    else:
        index = ((number - 1) % (len(PALETTE) - 1)) + 2
    return PALETTE[index - 1]


def as_colour_list(colour) -> list:
    """``as_colour_code`` as a list of strings or ``None``."""
    if isinstance(colour, str):
        return [colour]
    if isinstance(colour, np.ndarray) and colour.dtype.kind in "iuf":
        values = colour.astype(np.float64).ravel()
        if np.any(values <= 0):
            raise ValueError("colours encodes as numbers must be positive")
        return [_palette_name(item) for item in values]
    if isinstance(colour, (list, tuple)) and colour and not any(
        isinstance(item, str) or item is None for item in colour
    ):
        values = []
        for item in colour:
            if _is_missing_number(item):
                values.append(float("nan"))
            else:
                values.append(float(item))
        if any(item <= 0 for item in values if not math.isnan(item)):
            raise ValueError("colours encodes as numbers must be positive")
        return [_palette_name(item) for item in values]
    if isinstance(colour, (int, float, np.integer, np.floating)) and not isinstance(colour, bool):
        return as_colour_list([colour])
    if isinstance(colour, np.ndarray):
        items = colour.ravel().tolist()
    elif isinstance(colour, (list, tuple)):
        items = list(colour)
    else:
        items = [colour]
    out = []
    for item in items:
        if item is None or _is_missing_number(item):
            out.append(None)
        else:
            out.append(str(item))
    return out


def _parse_hex(text: str, *, short_ok: bool):
    if not text.startswith("#"):
        return None
    length = len(text)
    if short_ok:
        if length not in (4, 5, 7, 9):
            raise ValueError(
                f"Malformed colour string `{text}`. Must contain either 3, 4, 6 or 8 hex values"
            )
        short = length < 7
        has_alpha = length in (5, 9)
    else:
        if length not in (7, 9):
            raise ValueError(
                f"Malformed colour string `{text}`. Must contain either 6 or 8 hex values"
            )
        short = False
        has_alpha = length == 9
    if short:
        red = _hex_byte(text[1])
        green = _hex_byte(text[2])
        blue = _hex_byte(text[3])
        alpha = _hex_byte(text[4]) if has_alpha else None
    else:
        red = _hex_byte(text[1], text[2])
        green = _hex_byte(text[3], text[4])
        blue = _hex_byte(text[5], text[6])
        alpha = _hex_byte(text[7], text[8]) if has_alpha else None
    return red, green, blue, alpha


def parse_colour(text, *, short_ok: bool, na_value=None):
    """One colour string.

    Returns ``(missing, r, g, b, alpha_byte, alpha_unit)``. ``alpha_byte``
    is ``-1`` when the source has no alpha digits to preserve. ``alpha_unit``
    is the 0..1 alpha used by decoding.
    """
    if text is None or text == "NA" or _is_missing_number(text):
        if na_value is None or na_value == "NA" or _is_missing_number(na_value):
            return True, 0, 0, 0, -1, float("nan")
        return parse_colour(str(na_value), short_ok=short_ok, na_value=None)
    if not isinstance(text, str):
        text = str(text)
    parsed = _parse_hex(text, short_ok=short_ok)
    if parsed is not None:
        red, green, blue, alpha = parsed
        if alpha is None:
            return False, red, green, blue, -1, 1.0
        return False, red, green, blue, alpha, alpha / 255.0
    red, green, blue, unit = _lookup(text)
    alpha_byte = -1 if unit == 1 else int(unit * 255)
    return False, red, green, blue, alpha_byte, float(unit)


def channel_index(channel, space_id: int) -> int:
    """Channel number. ``alpha`` is 0. Anything else must name a channel."""
    if channel == "alpha":
        return 0
    space = space_name(space_id)
    index = CHANNEL_INDEX[space].get(channel)
    if index is None:
        raise ValueError("Invalid channel for this colourspace")
    return index


def _recycle(values, n: int):
    if n == 0:
        return []
    if len(values) == 1:
        return values * n
    if len(values) == n:
        return list(values)
    return [values[index % len(values)] for index in range(n)]


def _value_list(value, n: int):
    if isinstance(value, np.ndarray):
        raw = value.astype(np.float64).ravel().tolist()
    elif isinstance(value, (list, tuple)):
        raw = []
        for item in value:
            raw.append(float("nan") if _is_missing_number(item) else float(item))
    elif _is_missing_number(value):
        raw = [float("nan")]
    else:
        raw = [float(value)]
    if len(raw) == 0:
        raise ValueError("`value` must not be empty")
    return _recycle(raw, n)


def modify_channels(colour, channel, value, space="rgb", white="D65", na_value=None, op=1):
    """Shared body of the channel modifiers."""
    codes = as_colour_list(colour)
    if len(codes) == 0:
        return []
    space_id = colourspace_match(space)
    channel_id = channel_index(channel, space_id)
    white_arr = _white_for_space(space, white)
    short_ok = channel_id != 0
    parsed = [parse_colour(code, short_ok=short_ok, na_value=na_value) for code in codes]
    values = _value_list(value, len(codes))
    red, green, blue, alpha_byte, skip, used = [], [], [], [], [], []
    for (missing, r, g, b, byte, _unit), item in zip(parsed, values):
        absent = missing or (channel_id != 0 and _is_missing_number(item))
        red.append(r)
        green.append(g)
        blue.append(b)
        alpha_byte.append(byte)
        skip.append(1 if absent else 0)
        used.append(0.0 if _is_missing_number(item) else item)
    encoded = farver_kernel.modify(
        np.asarray(red, dtype=np.int32),
        np.asarray(green, dtype=np.int32),
        np.asarray(blue, dtype=np.int32),
        np.asarray(alpha_byte, dtype=np.int32),
        np.asarray(used, dtype=np.float64),
        np.asarray(skip, dtype=np.int32),
        channel_id,
        0 if channel_id == 0 else space_id,
        op,
        white_arr,
    )
    return encoded


def get_channels(colour, channel, space="rgb", white="D65", na_value=None):
    """``get_channel``."""
    codes = as_colour_list(colour)
    space_id = colourspace_match(space)
    channel_id = channel_index(channel, space_id)
    white_arr = _white_for_space(space, white)
    parsed = [parse_colour(code, short_ok=False, na_value=na_value) for code in codes]
    if channel_id == 0:
        out = np.empty(len(parsed), dtype=np.float64)
        for index, (missing, _r, _g, _b, _byte, unit) in enumerate(parsed):
            # The C alpha path assigns NA_integer_ into a real vector.
            out[index] = -2147483648.0 if missing else unit
        return out
    if space_id == 10:
        out = np.empty(len(parsed), dtype=np.float64)
        for index, (missing, r, g, b, _byte, _unit) in enumerate(parsed):
            if missing:
                out[index] = float("nan")
            else:
                out[index] = (r, g, b)[channel_id - 1]
        return out
    red, green, blue = [], [], []
    missing_at = []
    for missing, r, g, b, _byte, _unit in parsed:
        missing_at.append(missing)
        red.append(0 if missing else r)
        green.append(0 if missing else g)
        blue.append(0 if missing else b)
    if not parsed:
        return np.empty(0, dtype=np.float64)
    values = farver_kernel.get_channel(
        np.asarray(red, dtype=np.int32),
        np.asarray(green, dtype=np.int32),
        np.asarray(blue, dtype=np.int32),
        channel_id,
        space_id,
        white_arr,
    )
    values = np.asarray(values, dtype=np.float64).copy()
    for index, missing in enumerate(missing_at):
        if missing:
            values[index] = float("nan")
    return values


def decode_colours(colour, alpha=False, to="rgb", white="D65", na_value=None):
    """``decode_colour``."""
    codes = as_colour_list(colour)
    space_id = colourspace_match(to)
    white_arr = _white_for_space(to, white)
    parsed = [parse_colour(code, short_ok=True, na_value=na_value) for code in codes]
    n = len(parsed)
    rgb = np.zeros((n, 3), dtype=np.float64)
    alpha_unit = np.ones(n, dtype=np.float64)
    missing = np.zeros(n, dtype=np.int32)
    for index, (is_missing, r, g, b, _byte, unit) in enumerate(parsed):
        if is_missing:
            missing[index] = 1
        else:
            rgb[index, 0] = r
            rgb[index, 1] = g
            rgb[index, 2] = b
            alpha_unit[index] = unit
    if n == 0:
        columns = 4 if space_id == 2 else 3
        if alpha:
            columns += 1
        return np.zeros((0, columns), dtype=np.float64)
    return farver_kernel.decode(
        rgb,
        alpha_unit,
        missing,
        space_id,
        white_arr,
        alpha is True or alpha is np.True_,
    )


def encode_colours(colour, alpha=None, from_="rgb", white="D65"):
    """``encode_colour``."""
    matrix = as_matrix(colour)
    if matrix.shape[0] == 0:
        return []
    space_id = colourspace_match(from_)
    need = 4 if space_id == 2 else 3
    if matrix.shape[1] < need:
        if space_id == 10:
            raise ValueError("Colour in RGB format must contain at least 3 columns")
        raise ValueError(
            f"Colour in this format must contain at least {need} columns"
        )
    white_arr = _white_for_space(from_, white)
    scaled = prepare_alpha(alpha, matrix.shape[0])
    return farver_kernel.encode(matrix, space_id, white_arr, scaled)


def convert_matrix(colour, from_, to, white_from="D65", white_to=None):
    matrix = as_matrix(colour)
    from_id = colourspace_match(from_)
    to_id = colourspace_match(to)
    if white_to is None:
        white_to = white_from
    return farver_kernel.convert(
        matrix,
        from_id,
        to_id,
        as_white_ref(white_from),
        as_white_ref(white_to),
    )


def compare_matrices(
    colour_from,
    colour_to,
    from_space,
    to_space,
    method,
    white_from,
    white_to,
    lightness,
    chroma,
    symmetric,
):
    return farver_kernel.compare(
        as_matrix(colour_from),
        as_matrix(colour_to),
        colourspace_match(from_space),
        colourspace_match(to_space),
        distance_match(method),
        symmetric,
        as_white_ref(white_from),
        as_white_ref(white_to),
        float(lightness),
        float(chroma),
    )
