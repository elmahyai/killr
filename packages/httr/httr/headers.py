"""Add request headers the way httr 1.4.9 does.

``add_headers`` is ``request(headers = c(..., .headers))``. The default
``.headers`` is ``character(0)``, so atomic values are coerced with
``as.character``. ``keep_last`` then drops an earlier header when its name
is repeated. A vector with no names is dropped entirely. Nothing here
sends a request.
"""

from __future__ import annotations

import math
from datetime import datetime
from decimal import ROUND_HALF_EVEN, Context, Decimal, localcontext


class NAType:
    """R's NA. ``None`` remains NULL."""

    def __repr__(self) -> str:
        return "NA"


NA = NAType()

# A missing name. The string ``"NA"`` is a real name.
NA_NAME = object()

_ABSENT = object()
_NOT_CHARACTER = object()

_DECIMAL = Context(prec=1000, rounding=ROUND_HALF_EVEN, Emin=-999999, Emax=999999)

_RANK = {
    "raw": 1,
    "logical": 2,
    "integer": 3,
    "double": 4,
    "complex": 5,
    "character": 6,
    "list": 7,
}

_POSIX_FORMATS = (
    "%Y-%m-%d %H:%M:%S",
    "%Y/%m/%d %H:%M:%S",
    "%Y-%m-%d %H:%M",
    "%Y/%m/%d %H:%M",
    "%Y-%m-%d",
    "%Y/%m/%d",
)
_DATE_FORMATS = ("%Y-%m-%d", "%Y/%m/%d")
_FORMAT_ERROR = "character string is not in a standard unambiguous format"


class Atomic:
    """An R atomic vector. ``names`` is omitted when R's names attribute is NULL.

    A missing value is ``None`` inside the vector. ``NA_NAME`` is a missing
    name. ``dim`` is stored and then ignored by ``c()``, which is how a
    matrix loses its dimensions.
    """

    def __init__(self, values, kind="double", names=None, dim=None, classes=None):
        if kind not in _RANK:
            raise ValueError("kind must be an atomic R type")
        self.values = list(values)
        self.kind = kind
        self.names = None if names is None else list(names)
        self.dim = dim
        self.classes = tuple(classes) if classes else ()

    def __len__(self):
        return len(self.values)


class Factor:
    """An R factor. ``c()`` drops the class and keeps the 1-based codes."""

    def __init__(self, labels, levels, names=None):
        codes = []
        for label in labels:
            if label is NA or label is None:
                codes.append(None)
            else:
                codes.append(levels.index(label) + 1)
        self.codes = codes
        self.names = None if names is None else list(names)

    def __len__(self):
        return len(self.codes)


class POSIXct:
    """Seconds since 1970-01-01 UTC. Used only as an argument to ``c()``."""

    def __init__(self, seconds, tz="UTC", names=None):
        self.seconds = [None if value is NA else value for value in seconds]
        self.tz = tz
        self.names = None if names is None else list(names)
        self.classes = ("POSIXct", "POSIXt")

    def __len__(self):
        return len(self.seconds)


class Date:
    """Days since 1970-01-01. Used only as an argument to ``c()``."""

    def __init__(self, days, names=None):
        self.days = [None if value is NA else value for value in days]
        self.names = None if names is None else list(names)
        self.classes = ("Date",)

    def __len__(self):
        return len(self.days)


class Dot:
    """One argument of R's ``...``, with the name R would have bound."""

    def __init__(self, value, name=None):
        self.value = value
        self.name = name


class Request:
    """The list ``request()`` returns. Only ``headers`` is filled."""

    def __init__(self, headers):
        self.method = None
        self.url = None
        self.headers = headers
        self.fields = None
        self.options = None
        self.auth_token = None
        self.output = None
        self.classes = ("request",)

    def __str__(self) -> str:
        lines = ["<request>"]
        headers = self.headers
        if headers is not None and len(headers.values) > 0:
            lines.append("Headers:")
            for name, value in zip(headers.names, headers.values):
                shown_name = "NA" if name is NA_NAME else name
                shown_value = "NA" if value is None else value
                lines.append(f"* {shown_name}: {shown_value}")
        return "\n".join(lines) + "\n"


def add_headers(*args, **kwargs) -> Request:
    """Return a request whose headers are ``c(..., .headers)`` after ``keep_last``.

    Keyword ``.headers`` is the R formal and is appended after ``...``.
    Any other keyword is one named argument of ``...``. A ``Dot`` carries a
    name for an argument that R would place between other names, which
    Python syntax cannot spell. The default ``.headers`` is an empty
    character vector.
    """

    if ".headers" in kwargs:
        extra = kwargs.pop(".headers")
    else:
        extra = Atomic([], "character")
    pairs = []
    for arg in args:
        if isinstance(arg, Dot):
            pairs.append((arg.name, arg.value))
        else:
            pairs.append((None, arg))
    for name, value in kwargs.items():
        pairs.append((name, value))
    pairs.append((None, extra))
    return _request(_combine(pairs))


def _request(headers):
    if headers is _NOT_CHARACTER:
        raise ValueError("is.character(headers) is not TRUE")
    if headers is None:
        kept = None
    elif isinstance(headers, Atomic) and headers.kind == "character":
        kept = _keep_last(headers)
    else:
        raise ValueError("is.character(headers) is not TRUE")
    return Request(kept)


def _keep_last(headers: Atomic) -> Atomic:
    """``x[!duplicated(names(x), fromLast = TRUE)]``.

    ``NULL`` names make the subscript empty, so every value is dropped.
    A missing name matches another missing name. An empty name matches
    another empty name. The last copy stays where it was.
    """

    if not headers.values or headers.names is None:
        return Atomic([], "character")
    last = {}
    for index, name in enumerate(headers.names):
        key = ("na",) if name is NA_NAME else ("s", name)
        last[key] = index
    chosen = sorted(last.values())
    if not chosen:
        return Atomic([], "character")
    return Atomic(
        [headers.values[index] for index in chosen],
        "character",
        [headers.names[index] for index in chosen],
    )


def _combine(pairs):
    if not pairs:
        return None
    first = pairs[0][1]
    if _inherits(first, "POSIXct"):
        _reject_bad_times(pairs, _POSIX_FORMATS)
        return _NOT_CHARACTER
    if _inherits(first, "Date"):
        _reject_bad_times(pairs, _DATE_FORMATS)
        return _NOT_CHARACTER
    return _combine_default(pairs)


def _inherits(value, which: str) -> bool:
    if which == "POSIXct" and isinstance(value, POSIXct):
        return True
    if which == "Date" and isinstance(value, Date):
        return True
    classes = getattr(value, "classes", ())
    return which in classes


def _reject_bad_times(pairs, formats):
    """``c.POSIXct`` and ``c.Date`` coerce every argument before returning.

    A character string that matches none of the formats stops with R's
    unambiguous-format message. Anything that does coerce is still not
    a character vector, so the caller reports ``is.character`` false.
    """

    for _, value in pairs:
        texts = _character_texts(value)
        if texts is None:
            continue
        if texts and not _one_format_matches(texts, formats):
            raise ValueError(_FORMAT_ERROR)


def _character_texts(value):
    if isinstance(value, str):
        return [value]
    if isinstance(value, Atomic) and value.kind == "character":
        return [item for item in value.values if item is not None]
    return None


def _one_format_matches(texts, formats) -> bool:
    return any(all(_prefix_time(text, fmt) for text in texts) for fmt in formats)


def _prefix_time(text: str, fmt: str) -> bool:
    """R's ``strptime`` accepts a prefix. ``%OS`` also allows a fraction."""

    if "%S" in fmt and "." in text:
        head, _, fraction = text.partition(".")
        if fraction.isdigit() and _prefix_time(head, fmt):
            return True
    limit = _format_width(fmt)
    for size in range(1, len(text) + 1):
        try:
            datetime.strptime(text[:size], fmt)
        except ValueError:
            continue
        if size >= limit:
            return True
    return False


def _format_width(fmt: str) -> int:
    # The numeric formats used here are fixed width once the separators
    # are counted. A shorter prefix must not count as a match.
    token = {
        "%Y": 4,
        "%m": 2,
        "%d": 2,
        "%H": 2,
        "%M": 2,
        "%S": 2,
    }
    width = 0
    index = 0
    while index < len(fmt):
        if fmt[index] == "%" and index + 1 < len(fmt):
            width += token.get(fmt[index : index + 2], 0)
            index += 2
        else:
            width += 1
            index += 1
    return width


def _combine_default(pairs):
    rank = 0
    pieces = []
    for tag, value in pairs:
        part = _classify(value)
        if part is None:
            continue
        kind, values, names = part
        rank = max(rank, _RANK[kind])
        if not values:
            continue
        pieces.append((tag, kind, values, names))
    if rank == 0:
        return None
    if rank != _RANK["character"]:
        return _NOT_CHARACTER
    merged_values = []
    merged_names = []
    saw_name = False
    for tag, kind, values, names in pieces:
        text = _as_character_values(kind, values)
        element_names = _element_names(tag, names, len(text))
        if any(name is not _ABSENT for name in element_names):
            saw_name = True
        merged_values.extend(text)
        merged_names.extend(element_names)
    if not saw_name:
        return Atomic(merged_values, "character")
    resolved = ["" if name is _ABSENT else name for name in merged_names]
    return Atomic(merged_values, "character", resolved)


def _classify(value):
    """Return ``(kind, values, names)`` or ``None`` for NULL.

    A length-zero vector still returns a kind so it can win ``c()``'s
    type. ``names`` is ``None`` when the names attribute is missing.
    """

    if value is None:
        return None
    if value is NA:
        return ("logical", [None], None)
    if isinstance(value, bool):
        return ("logical", [value], None)
    if isinstance(value, int):
        return ("integer", [value], None)
    if isinstance(value, float):
        return ("double", [value], None)
    if isinstance(value, complex):
        return ("complex", [(value.real, value.imag)], None)
    if isinstance(value, str):
        return ("character", [value], None)
    if isinstance(value, (bytes, bytearray)):
        return ("raw", list(value), None)
    if isinstance(value, Factor):
        return ("integer", list(value.codes), value.names)
    if isinstance(value, POSIXct):
        return ("double", [float(item) if item is not None else None for item in value.seconds], value.names)
    if isinstance(value, Date):
        return ("double", [float(item) if item is not None else None for item in value.days], value.names)
    if isinstance(value, Atomic):
        return (value.kind, list(value.values), value.names)
    if isinstance(value, (list, tuple)):
        return ("list", list(value), None)
    return ("list", [value], None)


def _element_names(tag, names, count):
    """Names contributed by one argument of ``c()``.

    A real inner name is pasted as ``tag.name``. A missing inner name
    becomes ``tag.NA``. An empty inner name, or no names attribute, uses
    the tag for one element and ``tag`` plus the 1-based index otherwise.
    """

    result = []
    for index in range(count):
        inner = _ABSENT if names is None else names[index]
        if inner is not _ABSENT and inner is not NA_NAME and inner != "":
            result.append(inner if tag is None else f"{tag}.{inner}")
        elif inner is NA_NAME and tag is not None:
            result.append(f"{tag}.NA")
        elif tag is not None:
            result.append(tag if count == 1 else f"{tag}{index + 1}")
        elif inner is NA_NAME:
            result.append(NA_NAME)
        elif inner == "":
            result.append("")
        else:
            result.append(_ABSENT)
    return result


def _as_character_values(kind, values):
    if kind == "character":
        return [None if item is NA else item for item in values]
    if kind == "logical":
        converted = []
        for item in values:
            if item is None or item is NA:
                converted.append(None)
            else:
                converted.append("TRUE" if item else "FALSE")
        return converted
    if kind == "integer":
        return [None if item is None or item is NA else str(int(item)) for item in values]
    if kind == "double":
        return [_character_double(item) for item in values]
    if kind == "complex":
        return [_character_complex(item) for item in values]
    if kind == "raw":
        return [f"{int(item) & 0xFF:02x}" for item in values]
    return values


def _character_complex(value):
    real, imag = value
    if real is None or imag is None or real is NA or imag is NA:
        return None
    imag_value = float(imag)
    real_text = _character_double(float(real))
    imag_text = _character_double(imag_value)
    # A negative imaginary part already carries its minus sign. NaN and
    # negative zero compare as not less than zero, so they take a plus.
    if not math.isnan(imag_value) and imag_value < 0.0:
        return real_text + imag_text + "i"
    return real_text + "+" + imag_text + "i"


def _character_double(value):
    """R ``as.character`` for one double, at ``scipen`` 0.

    Fifteen significant digits, or sixteen when the magnitude is in
    ``[1e15, 1e16)``. The shorter of the fixed and scientific forms wins.
    On a tie, a one-digit mantissa uses scientific notation when the
    exponent is at most -4 or at least 5. An exact integer keeps its
    digits when that text is shorter than the scientific form.
    """

    if value is None or value is NA:
        return None
    value = float(value)
    if math.isnan(value):
        return "NaN"
    if math.isinf(value):
        return "Inf" if value > 0.0 else "-Inf"
    if value == 0.0:
        return "0"
    negative = math.copysign(1.0, value) < 0.0
    magnitude = abs(value)
    digits = 16 if 1e15 <= magnitude < 1e16 else 15
    with localcontext(_DECIMAL):
        rounded = _round_sig(Decimal(magnitude), digits)
        fixed, scientific = _fixed_and_sci(rounded)
        exponent = rounded.adjusted()
    if magnitude.is_integer():
        exact = str(int(magnitude))
        mantissa = scientific.split("e", 1)[0]
        if len(exact) < len(scientific) or (
            len(exact) == len(scientific) and "." in mantissa
        ):
            chosen = exact
        else:
            chosen = _choose_notation(fixed, scientific, exponent)
    else:
        chosen = _choose_notation(fixed, scientific, exponent)
    if negative:
        return "-" + chosen
    return chosen


def _round_sig(value: Decimal, digits: int) -> Decimal:
    if value == 0:
        return Decimal(0)
    adjusted = value.adjusted()
    quantum = Decimal(f"1e{adjusted - (digits - 1)}")
    rounded = value.quantize(quantum, rounding=ROUND_HALF_EVEN)
    if rounded != 0 and rounded.adjusted() > adjusted:
        adjusted = rounded.adjusted()
        quantum = Decimal(f"1e{adjusted - (digits - 1)}")
        rounded = value.quantize(quantum, rounding=ROUND_HALF_EVEN)
    return rounded


def _fixed_and_sci(rounded: Decimal):
    if rounded == 0:
        return "0", "0e+00"
    text = format(rounded, "f")
    if "." in text:
        whole, frac = text.split(".")
        digits = (whole + frac).lstrip("0").rstrip("0") or "0"
    else:
        digits = text.lstrip("0").rstrip("0") or "0"
    adjusted = rounded.adjusted()
    if adjusted >= 0:
        if adjusted + 1 >= len(digits):
            fixed = digits + ("0" * (adjusted + 1 - len(digits)))
        else:
            fixed = digits[: adjusted + 1] + "." + digits[adjusted + 1 :]
    else:
        fixed = "0." + ("0" * (-adjusted - 1)) + digits
    mantissa = digits if len(digits) == 1 else digits[0] + "." + digits[1:]
    return fixed, f"{mantissa}e{adjusted:+03d}"


def _choose_notation(fixed: str, scientific: str, exponent: int) -> str:
    if len(scientific) < len(fixed):
        return scientific
    if len(scientific) > len(fixed):
        return fixed
    mantissa = scientific.split("e", 1)[0]
    if "." in mantissa:
        return fixed
    if exponent <= -4 or exponent >= 5:
        return scientific
    return fixed
