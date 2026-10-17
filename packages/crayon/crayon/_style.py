"""Builtin styles, make_style, and the functions that apply them."""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any

from crayon._colors import col2rgb, is_r_color, r_round, scale
from crayon._detect import has_color, num_ansi_colors, num_colors
from crayon._options import get_option
from crayon._text import mypaste, one_or_many

_DATA = Path(__file__).resolve().parent / "data"
_PALETTE_CACHE: dict[str, dict[str, dict[str, Any]]] = {}


def _tag(codes: int | list[int]) -> str:
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


def _record(open_code: int | list[int], close_code: int | list[int], palette: int | None) -> dict[str, Any]:
    return {"open": _tag(open_code), "close": _tag(close_code), "palette": palette}


def _copy(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "open": record["open"],
        "close": record["close"],
        "palette": record.get("palette"),
    }


def _plain(open_code: int | list[int], close_code: int | list[int]) -> dict[str, Any]:
    return _record(open_code, close_code, None)


def _colored(open_code: int, close_code: int) -> dict[str, Any]:
    return _record(open_code, close_code, _palette_idx(open_code))


_BUILTIN_ORDER = [
    "reset",
    "bold",
    "blurred",
    "italic",
    "underline",
    "inverse",
    "hidden",
    "strikethrough",
    "black",
    "red",
    "green",
    "yellow",
    "blue",
    "magenta",
    "cyan",
    "white",
    "silver",
    "bgBlack",
    "bgRed",
    "bgGreen",
    "bgYellow",
    "bgBlue",
    "bgMagenta",
    "bgCyan",
    "bgWhite",
]

_BUILTINS: dict[str, dict[str, Any]] = {
    "reset": _plain(0, [0, 22, 23, 24, 27, 28, 29, 39, 49]),
    "bold": _plain(1, 22),
    "blurred": _plain(2, 22),
    "italic": _plain(3, 23),
    "underline": _plain(4, 24),
    "inverse": _plain(7, 27),
    "hidden": _plain(8, 28),
    "strikethrough": _plain(9, 29),
    "black": _colored(30, 39),
    "red": _colored(31, 39),
    "green": _colored(32, 39),
    "yellow": _colored(33, 39),
    "blue": _colored(34, 39),
    "magenta": _colored(35, 39),
    "cyan": _colored(36, 39),
    "white": _colored(37, 39),
    "silver": _colored(90, 39),
    "bgBlack": _colored(40, 49),
    "bgRed": _colored(41, 49),
    "bgGreen": _colored(42, 49),
    "bgYellow": _colored(43, 49),
    "bgBlue": _colored(44, 49),
    "bgMagenta": _colored(45, 49),
    "bgCyan": _colored(46, 49),
    "bgWhite": _colored(47, 49),
}

_FG_NAMES = {
    "black": "black",
    "red": "red",
    "green": "green",
    "yellow": "yellow",
    "blue": "blue",
    "magenta": "magenta",
    "cyan": "cyan",
    "white": "white",
    "silver": "grey",
}
_BG_NAMES = {
    "bgBlack": "black",
    "bgRed": "red",
    "bgGreen": "green",
    "bgYellow": "yellow",
    "bgBlue": "blue",
    "bgMagenta": "magenta",
    "bgCyan": "cyan",
    "bgWhite": "white",
}


def _load_palettes() -> dict[str, list[str]]:
    tables: dict[str, list[str]] = {}
    for name in ("ansi-palettes.txt", "ansi-iterm-palettes.txt"):
        for line in (_DATA / name).read_text().splitlines():
            stripped = line.split(";", 1)[0].strip()
            if stripped == "":
                continue
            fields = stripped.split()
            if len(fields) == 17:
                tables[fields[0]] = fields[1:]
    return tables


_PALETTES = _load_palettes()
_REGISTRY: dict[str, dict[str, Any]] = {}


def _fg_table() -> list[tuple[str, tuple[int, int, int]]]:
    return [(name, col2rgb(color)) for name, color in _FG_NAMES.items()]


def _bg_table() -> list[tuple[str, tuple[int, int, int]]]:
    return [(name, col2rgb(color)) for name, color in _BG_NAMES.items()]


def _channels(style: Any) -> list[int]:
    if isinstance(style, (list, tuple)) and style and isinstance(style[0], (list, tuple)):
        return [int(column[0]) for column in style]
    return [int(item) for item in style]


def _style_8(rgb: list[int], bg: bool) -> dict[str, Any]:
    table = _bg_table() if bg else _fg_table()
    flat: list[int] = []
    for _name, color in table:
        flat.extend(color)
    distance = [0] * len(table)
    for index, channel in enumerate(flat):
        delta = channel - rgb[index % len(rgb)]
        distance[index // 3] += delta * delta
    best = min(range(len(distance)), key=lambda item: distance[item])
    return _copy(_BUILTINS[table[best][0]])


def _ansi256_index(red: float, green: float, blue: float) -> int:
    gray_possible = True
    sep = 42.5
    gray = False
    while gray_possible:
        if red < sep or green < sep or blue < sep:
            gray = red < sep and green < sep and blue < sep
            gray_possible = False
        sep += 42.5
    if gray:
        return 232 + r_round((red + green + blue) / 33) + 1
    return (
        16
        + math.floor(6 * red / 256) * 36
        + math.floor(6 * green / 256) * 6
        + math.floor(6 * blue / 256)
        + 1
    )


def _ansi256(rgb: list[int], bg: bool = False, grey: bool = False) -> dict[str, Any]:
    if grey:
        color = 232 + scale(rgb[0], to=(0, 23))
    else:
        color = _ansi256_index(rgb[0], rgb[1], rgb[2]) - 1
    opened = 48 if bg else 38
    closed = 49 if bg else 39
    return {"open": f"\x1b[{opened};5;{color}m", "close": f"\x1b[{closed}m", "palette": None}


def _from_rgb(rgb: list[int], bg: bool, colors: int, grey: bool) -> dict[str, Any]:
    if colors < 256:
        return _style_8(rgb, bg)
    return _ansi256(rgb, bg, grey)


def _capitalize(text: str) -> str:
    if text == "":
        return text
    return text[0].upper() + text[1:]


def _is_rgb(style: Any) -> bool:
    if isinstance(style, (str, bytes)) or isinstance(style, Style):
        return False
    if not isinstance(style, (list, tuple)):
        return False
    if style and isinstance(style[0], (list, tuple)):
        return len(style) in {3, 4} and all(
            len(column) == 1 and isinstance(column[0], (int, float)) and not isinstance(column[0], bool)
            for column in style
        )
    return len(style) in {3, 4} and all(
        isinstance(item, (int, float)) and not isinstance(item, bool) for item in style
    )


class Style:
    """A crayon style function. Attribute access combines another named style."""

    def __init__(self, styles: list[dict[str, Any]], names: list[str] | None = None, identity: bool = False):
        self._styles = styles
        self._names = list(names or [])
        self._identity = identity

    def __call__(self, *args: Any, sep: str = " ") -> Any:
        if self._identity:
            if len(args) == 1:
                return args[0]
            return one_or_many(mypaste(args, sep))
        rows = mypaste(args, sep)
        return one_or_many([_apply(self._styles, row) for row in rows])

    def __getattr__(self, name: str) -> Style:
        if name.startswith("_"):
            raise AttributeError(name)
        record = _REGISTRY.get(name)
        if record is None:
            raise AttributeError(f"no crayon style named {name}")
        return Style(self._styles + [_copy(record)], self._names + [name])

    def __neg__(self) -> Style:
        styles = []
        enabled = has_color()
        for record in self._styles:
            item = _copy(record)
            if enabled:
                item["open"] = item["close"]
            styles.append(item)
        return Style(styles, list(self._names))

    def __repr__(self) -> str:
        label = ", ".join(self._names) if self._names else "identity"
        return f"Crayon style function, {label}"


def _apply(styles: list[dict[str, Any]], text: str) -> str:
    count = num_ansi_colors()
    if count <= 1:
        return text
    for record in reversed(styles):
        current = record
        if record.get("palette") is not None:
            current = _palette_color(record, count)
        text = current["open"] + text.replace(current["close"], current["open"]) + current["close"]
    return text


def _palette_color(record: dict[str, Any], colors: int) -> dict[str, Any]:
    option = get_option("cli.palette")
    if option is None or colors < 256:
        return record
    return _cache_palette(option, record["palette"], colors)


def _cache_palette(pal: Any, idx: int, colors: int) -> dict[str, Any]:
    if isinstance(pal, str):
        if pal not in _PALETTES:
            raise ValueError(f"Cannot find cli ANSI palette '{pal}'.")
        row = _PALETTES[pal]
    else:
        row = list(pal)
    background = idx < 0
    index = abs(idx)
    color = row[index - 1]
    bucket = str(colors)
    key = f"{color}{background}"
    cached = _PALETTE_CACHE.setdefault(bucket, {})
    if key in cached:
        return cached[key]
    value = _from_rgb(list(col2rgb(color)), background, colors, False)
    cached[key] = value
    return value


def styles() -> dict[str, dict[str, Any]]:
    return {name: _copy(record) for name, record in _REGISTRY.items()}


def drop_style(style: str) -> None:
    _REGISTRY.pop(style, None)


def _define(name: str, record: dict[str, Any]) -> None:
    _REGISTRY[name] = _copy(record)


def make_style(*args: Any, bg: bool = False, grey: bool = False, colors: int | None = None, **named: Any) -> Style:
    if (len(args) + len(named)) != 1:
        raise ValueError("make_style() expects one style")
    if not isinstance(bg, bool):
        raise TypeError("bg must be TRUE or FALSE")
    if colors is None:
        colors = num_colors()
    if isinstance(colors, bool) or not isinstance(colors, (int, float)):
        raise TypeError("colors must be a number")
    count = int(colors)
    if named:
        orig_name, spec = next(iter(named.items()))
        style_name: str | None = orig_name
    else:
        orig_name = None
        spec = args[0]
        style_name = None
    record = _resolve_spec(spec, bg, grey, count, style_name)
    style_name = record.pop("_name")
    if orig_name is not None:
        _define(orig_name, record)
        style_name = orig_name
    return Style([_copy(record)], [style_name] if style_name else [])


def _resolve_spec(spec: Any, bg: bool, grey: bool, colors: int, style_name: str | None) -> dict[str, Any]:
    if isinstance(spec, str) and spec in _BUILTINS:
        name = spec
        if bg and not name.startswith("bg"):
            name = "bg" + _capitalize(name)
        if name not in _BUILTINS:
            raise ValueError(f"Unknown style specification: {spec}")
        if style_name is None:
            style_name = name
        record = _copy(_BUILTINS[name])
        record["_name"] = style_name
        return record
    if is_r_color(spec):
        if style_name is None:
            style_name = str(spec)
        record = _from_rgb(list(col2rgb(spec)), bg, colors, grey)
        record["_name"] = style_name
        return record
    if _is_rgb(spec):
        record = _from_rgb(_channels(spec), bg, colors, grey)
        record["_name"] = style_name or ""
        return record
    raise ValueError(f"Unknown style specification: {spec}")


def use_or_make_style(style: Any, bg: bool = False) -> Style:
    if style is None:
        return Style([], identity=True)
    if isinstance(style, Style):
        return style
    if isinstance(style, str) and style in _REGISTRY:
        return Style([_copy(_REGISTRY[style])], [style])
    return make_style(style, bg=bg)


def style(string: Any, as_: Any = None, bg: Any = None, **kwargs: Any) -> Any:
    """Apply a foreground style and a background style. `as_` is R's argument `as`."""

    if "as" in kwargs:
        as_ = kwargs.pop("as")
    if kwargs:
        unexpected = ", ".join(kwargs)
        raise TypeError(f"unexpected arguments: {unexpected}")
    foreground = use_or_make_style(as_)
    background = use_or_make_style(bg, bg=True)
    if not isinstance(foreground, Style):
        raise TypeError("Cannot make style from 'as'")
    if not isinstance(background, Style):
        raise TypeError("Cannot make style from 'bg'")
    return foreground(background(string))


def combine_styles(*items: Any) -> Style:
    records: list[dict[str, Any]] = []
    names: list[str] = []
    for item in items:
        made = use_or_make_style(item)
        records.extend(_copy(record) for record in made._styles)
        names.extend(made._names)
    return Style(records, names)


def start(x: Style, *args: Any) -> str:
    del args
    if not isinstance(x, Style):
        raise TypeError("start() expects a crayon style")
    if not has_color():
        return ""
    return "".join(record["open"] for record in x._styles)


def finish(x: Style, *args: Any) -> str:
    del args
    if not isinstance(x, Style):
        raise TypeError("finish() expects a crayon style")
    if not has_color():
        return ""
    return "".join(record["close"] for record in reversed(x._styles))


def chr(x: Any, *args: Any, **kwargs: Any) -> Any:
    del args, kwargs
    if isinstance(x, Style):
        return start(x)
    from crayon._text import character_vector, one_or_many as pack

    return pack(character_vector(x))


def _install() -> None:
    for name in _BUILTIN_ORDER:
        record = _BUILTINS[name]
        _REGISTRY[name] = _copy(record)
        globals()[name] = Style([_copy(record)], [name])


_install()

reset = globals()["reset"]
bold = globals()["bold"]
blurred = globals()["blurred"]
italic = globals()["italic"]
underline = globals()["underline"]
inverse = globals()["inverse"]
hidden = globals()["hidden"]
strikethrough = globals()["strikethrough"]
black = globals()["black"]
red = globals()["red"]
green = globals()["green"]
yellow = globals()["yellow"]
blue = globals()["blue"]
magenta = globals()["magenta"]
cyan = globals()["cyan"]
white = globals()["white"]
silver = globals()["silver"]
bgBlack = globals()["bgBlack"]
bgRed = globals()["bgRed"]
bgGreen = globals()["bgGreen"]
bgYellow = globals()["bgYellow"]
bgBlue = globals()["bgBlue"]
bgMagenta = globals()["bgMagenta"]
bgCyan = globals()["bgCyan"]
bgWhite = globals()["bgWhite"]
