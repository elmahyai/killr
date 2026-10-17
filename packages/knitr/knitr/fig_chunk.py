"""Figure filenames for a chunk, matching knitr::fig_chunk.

``fig_chunk`` calls ``fig_path`` with the label and ``fig.path`` and no
``fig.cur``. A missing figure number is therefore 1. An explicit ``None``
is R's NULL and leaves the number out, so the name is ``figure/foo.png``.
A zero-length number is not NULL: ``paste0`` recycles it as an empty
string and the name is ``figure/foo-.png``.

``fig_path`` is the R argument ``fig.path``. The default is read from
``opts_chunk`` when the call omits it, which starts as ``figure/``.
"""

from __future__ import annotations

import ctypes
import math
import warnings

_libc = ctypes.CDLL(None)
_libc.iswalnum.argtypes = [ctypes.c_uint32]
_libc.iswalnum.restype = ctypes.c_int

_MISSING = object()
_KEPT = set("~:_.\\/-")


class _NA:
    """R's NA. ``None`` is NULL, and a float NaN stays NaN."""

    def __repr__(self) -> str:
        return "NA"


NA = _NA()


class _OptionStore:
    """Minimal ``new_defaults`` store: get, set, and restore."""

    def __init__(self, initial=None):
        self._initial = dict(initial or {})
        self._values = dict(self._initial)

    def get(self, name=None):
        if name is None:
            return dict(self._values)
        return self._values.get(name, None)

    def set(self, **kwargs):
        self._values.update(kwargs)

    def restore(self):
        self._values = dict(self._initial)


opts_chunk = _OptionStore({"fig.path": "figure/"})
opts_knit = _OptionStore()

# getOption("knitr.sanitize.paths"). A missing key uses the output format.
knitr_options: dict = {}


def fig_chunk(label, ext="", number=_MISSING, fig_path=_MISSING):
    """Filenames for the figures produced by a chunk.

    ``ext`` is the file extension. A value that does not already start with
    ``.`` gains one, so ``png`` is ``.png``. ``number`` selects the figures.
    One omitted number is 1. The result is a list of filenames.
    """

    if fig_path is _MISSING:
        fig_path = opts_chunk.get("fig.path")
    return _fig_path(ext, {"fig.path": fig_path, "label": label}, number)


def _fig_path(suffix, options, number):
    suffix = _dot_extension(suffix)
    if number is _MISSING:
        # options has no fig.cur, and %n% replaces that NULL with 1.
        current = options.get("fig.cur")
        number = 1 if current is None else current
    if number is not None:
        suffix = _paste0("-", number, suffix)
    path = _valid_path(options.get("fig.path"), options.get("label"))
    if _sanitize_paths():
        path = _sanitize(path)
    return _paste0(path, suffix)


def _dot_extension(suffix):
    """``sub('^([^.])', '.\\\\1', suffix)``. NULL becomes character(0)."""

    if suffix is None:
        return []
    out = []
    for item in _elements(suffix):
        if item is NA:
            out.append(NA)
            continue
        text = item if isinstance(item, str) else _paste_piece(item)
        if text is NA:
            out.append(NA)
        elif text == "" or text.startswith("."):
            out.append(text)
        else:
            out.append("." + text)
    return out


def _valid_path(prefix, label):
    """Blank an empty, missing, or ``\"NA\"`` prefix, then paste the label."""

    if prefix is None:
        chosen = [""]
    else:
        parts = _elements(prefix)
        if len(parts) == 0:
            chosen = [""]
        elif len(parts) > 1:
            raise ValueError(
                f"'length = {len(parts)}' in coercion to 'logical(1)'"
            )
        else:
            one = parts[0]
            if _missing(one) or one == "NA":
                chosen = [""]
            else:
                chosen = [one]
    return _paste0(chosen, label)


def _sanitize_paths():
    """``getOption('knitr.sanitize.paths', out_format(c('latex', 'sweave', 'listings')))``."""

    if "knitr.sanitize.paths" in knitr_options:
        value = knitr_options["knitr.sanitize.paths"]
        if value is None:
            raise ValueError("argument is of length zero")
        return _flag(value)
    return _out_format(("latex", "sweave", "listings"))


def _out_format(formats):
    fmt = opts_knit.get("out.format")
    if fmt is None:
        return False
    if isinstance(fmt, (list, tuple)):
        if len(fmt) == 0:
            raise ValueError("argument is of length zero")
        if len(fmt) > 1:
            raise ValueError(
                f"'length = {len(fmt)}' in coercion to 'logical(1)'"
            )
        fmt = fmt[0]
    if fmt is None:
        return False
    return fmt in formats


def _flag(value):
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value != 0
    if isinstance(value, float):
        if math.isnan(value):
            raise ValueError("missing value where TRUE/FALSE needed")
        return value != 0.0
    if isinstance(value, (list, tuple)):
        if len(value) == 0:
            raise ValueError("argument is of length zero")
        if len(value) > 1:
            raise ValueError(
                f"'length = {len(value)}' in coercion to 'logical(1)'"
            )
        return _flag(value[0])
    raise ValueError("missing value where TRUE/FALSE needed")


def _sanitize(path, warn=True):
    cleaned = ["".join(ch if _kept(ch) else "_" for ch in text) for text in path]
    if not warn:
        return cleaned
    if len(path) == 0:
        raise ValueError("argument is of length zero")
    if len(path) > 1:
        raise ValueError(f"'length = {len(path)}' in coercion to 'logical(1)'")
    if cleaned[0] != path[0]:
        warnings.warn(
            "Replaced special characters in figure filename "
            f"'{path[0]}' -> '{cleaned[0]}'",
            UserWarning,
            stacklevel=4,
        )
    return cleaned


def _kept(char):
    return char in _KEPT or bool(_libc.iswalnum(ord(char)))


def _elements(value):
    """One R vector. A string is one element, not a sequence of characters."""

    if isinstance(value, (list, tuple)):
        return list(value)
    return [value]


def _missing(value):
    return value is NA or (isinstance(value, float) and math.isnan(value))


def _paste0(*args):
    """R ``paste0`` with ``recycle0 = FALSE``. NULL arguments are dropped.

    A zero-length argument is an empty string when another argument has a
    length, and the result is empty only when every argument is empty.
    """

    parts = []
    for arg in args:
        if arg is None:
            continue
        parts.append(_elements(arg) if not isinstance(arg, list) else arg)
    if not parts or all(len(part) == 0 for part in parts):
        return []
    width = max(len(part) for part in parts)
    result = []
    for index in range(width):
        pieces = []
        for part in parts:
            if len(part) == 0:
                pieces.append("")
            else:
                pieces.append(_paste_piece(part[index % len(part)]))
        result.append("".join(pieces))
    return result


def _paste_piece(value):
    """One ``paste`` element. Missing values become the letters NA."""

    if value is None or value is NA:
        return "NA"
    if isinstance(value, str):
        return value
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        if math.isnan(value):
            return "NaN"
        return _character_double(value)
    return str(value)


def _character_double(value):
    """R's ``as.character`` for a double.

    Fifteen significant digits. Scientific notation is used when it is
    shorter than fixed notation. A tie keeps the fixed form. The exponent
    has a sign and at least two digits.
    """

    if math.isnan(value):
        return "NaN"
    if math.isinf(value):
        return "Inf" if value > 0 else "-Inf"
    if value == 0.0:
        return "0"
    negative = value < 0
    scientific = format(abs(value), ".14e")
    mantissa, exponent_text = scientific.split("e")
    exponent = int(exponent_text)
    whole, frac = mantissa.split(".")
    frac = frac.rstrip("0")
    mant = whole if frac == "" else f"{whole}.{frac}"
    digits = whole + frac
    sci = f"{mant}e{exponent:+03d}"
    if exponent >= 0:
        point = len(whole) + exponent
        if point >= len(digits):
            fixed = digits + ("0" * (point - len(digits)))
        else:
            fixed = digits[:point] + "." + digits[point:]
    else:
        zeros = -exponent - len(whole)
        if zeros >= 0:
            fixed = "0." + ("0" * zeros) + digits
        else:
            point = len(digits) + zeros
            fixed = digits[:point] + "." + digits[point:]
    if negative:
        sci = "-" + sci
        fixed = "-" + fixed
    if len(sci) < len(fixed):
        return sci
    return fixed
