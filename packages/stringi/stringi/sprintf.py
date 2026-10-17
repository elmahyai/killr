"""Unicode-aware sprintf from stringi 1.8.9.

Finite numbers go through Python's printf conversion, which matches
``std::snprintf`` for the specifiers exercised here. Missing values stay
missing when ``na_string`` is ``NA``. Width of a string uses
``stri_width`` unless ``use_length`` is true. The string ``"NA"`` is text.
"""

from __future__ import annotations

import ctypes
import math
import sys
import warnings
from pathlib import Path

_LIBC = ctypes.CDLL(None, use_errno=True)

from stringi._na import NA
from stringi.join import (
    _prepare_integer,
    _prepare_logical_1,
    _prepare_string,
    _prepare_string_1,
)
from stringi.length import stri_width

_NOT_GIVEN = object()
_MISSING = object()
_TYPES = set("dioxXfeEgGaAs")
_ACCEPTED = set("dioxXfeEgGaAs-+ 0#.*$0123456789")
_INT_SPEC = set("dioxX")
_FLOAT_SPEC = set("feEgGaA")
_ACCEPTED_TEXT = "dioxXfeEgGaAs-+ 0#.*$0123456789"


def _warn(message: str) -> None:
    warnings.warn(message, UserWarning, stacklevel=3)


def _vector(value):
    if value is None:
        return []
    if isinstance(value, (str, bytes)):
        return [value]
    if isinstance(value, (list, tuple)):
        return list(value)
    return [value]


def _prepare_double(value):
    items = _vector(value)
    result = []
    coerced = False
    for item in items:
        if item is NA or item is None:
            result.append(NA)
            continue
        if isinstance(item, bool):
            result.append(1.0 if item else 0.0)
            continue
        if isinstance(item, int):
            result.append(float(item))
            continue
        if isinstance(item, float):
            result.append(item)
            continue
        if isinstance(item, str):
            stripped = item.strip()
            if stripped in ("", "NA"):
                coerced = stripped == ""
                result.append(NA)
                continue
            try:
                if stripped.lower() == "nan":
                    result.append(float("nan"))
                elif stripped in ("Inf", "+Inf"):
                    result.append(float("inf"))
                elif stripped == "-Inf":
                    result.append(float("-inf"))
                else:
                    result.append(float(stripped))
            except ValueError:
                coerced = True
                result.append(NA)
            continue
        raise ValueError(
            "argument `...` should be a numeric vector (or an object coercible to)"
        )
    if coerced:
        _warn("NAs introduced by coercion")
    return result


def _specifier_error(body: str, extra: str = "") -> ValueError:
    message = f"conversion specifier '%{body}' is not valid"
    if extra:
        message = f"{message}; {extra}"
    return ValueError(message)


def _find_type(fmt: str, start: int) -> int:
    index = start
    while True:
        if index >= len(fmt):
            raise _specifier_error(fmt[start:])
        char = fmt[index]
        if char in _TYPES:
            return index
        if char not in _ACCEPTED:
            raise _specifier_error(
                fmt[start:],
                f"expected a character in [{_ACCEPTED_TEXT}]",
            )
        index += 1


def _atoi_delim(fmt, index, end, delim, throw, origin):
    if index >= end or not fmt[index].isdigit():
        if throw:
            raise _specifier_error(
                fmt[origin:end + 1], "expected a nonnegative numeric value"
            )
        return _MISSING, index
    value = 0
    cursor = index
    while True:
        if cursor < len(fmt) and fmt[cursor] == delim:
            return value, cursor + 1
        if cursor >= end or not fmt[cursor].isdigit():
            if throw:
                raise _specifier_error(fmt[origin:end + 1])
            return _MISSING, index
        value = value * 10 + (ord(fmt[cursor]) - 48)
        if value > 99999:
            raise _specifier_error(fmt[origin:end + 1], "value too large")
        cursor += 1


def _atoi_other(fmt, index, end, origin):
    if index >= end or not fmt[index].isdigit():
        raise _specifier_error(
            fmt[origin:end + 1], "expected a nonnegative numeric value"
        )
    value = 0
    while index < end and fmt[index].isdigit():
        value = value * 10 + (ord(fmt[index]) - 48)
        if value > 99999:
            raise _specifier_error(fmt[origin:end + 1], "value too large")
        index += 1
    return value, index


def _trim_text(text: str, precision, use_length: bool) -> str:
    if precision is _MISSING or precision is NA:
        return text
    if use_length:
        return text[:precision]
    kept = []
    for char in text:
        trial = "".join(kept) + char
        width = stri_width(trial) if trial else 0
        if width > precision:
            break
        kept.append(char)
    return "".join(kept)


def _snprintf(picture: str, value, kind: str) -> str:
    """Format one finite number the way glibc snprintf does.

    stringi sends dioxX and feEgGaA through std::snprintf. Python's ``%``
    operator treats ``%a`` as ``ascii()`` and rejects ``%A``.
    """

    width = 128
    if picture:
        width += len(picture) * 4
    encoded = picture.encode("ascii")
    while True:
        buffer = ctypes.create_string_buffer(width)
        if kind == "int":
            written = _LIBC.snprintf(buffer, width, encoded, ctypes.c_int(int(value)))
        else:
            written = _LIBC.snprintf(buffer, width, encoded, ctypes.c_double(float(value)))
        if written < 0:
            raise ValueError(f"conversion specifier '{picture}' is not valid")
        if written < width:
            return buffer.value.decode("ascii")
        width = written + 1


def _pad(text: str, min_width, pad_right: bool, use_length: bool) -> str:
    if not isinstance(min_width, int) or min_width <= 0:
        return text
    size = len(text) if use_length else (stri_width(text) if text else 0)
    if size >= min_width:
        return text
    spaces = " " * (min_width - size)
    if pad_right:
        return text + spaces
    return spaces + text


class _Provider:
    def __init__(self, vectors, caches, index):
        self.vectors = vectors
        self.caches = caches
        self.index = index
        self.cursor = 0

    def _slot(self, which):
        if which is _MISSING:
            which = self.cursor
            self.cursor += 1
        if not isinstance(which, int) or which < 0:
            raise ValueError("value too small")
        if which >= len(self.vectors):
            raise ValueError("too few arguments")
        return which

    def _mark(self, slot, kind, prepared):
        cache = self.caches[slot]
        cache["used"] = True
        cache[kind] = prepared
        return prepared[self.index % len(prepared)]

    def integer(self, which=_MISSING):
        slot = self._slot(which)
        cache = self.caches[slot]
        if cache["int"] is None:
            prepared = _prepare_integer(self.vectors[slot], "...")
            if len(prepared) == 0:
                raise ValueError("argument `...` should be an integer vector")
            return self._mark(slot, "int", prepared)
        cache["used"] = True
        return cache["int"][self.index % len(cache["int"])]

    def real(self, which=_MISSING):
        slot = self._slot(which)
        cache = self.caches[slot]
        if cache["float"] is None:
            prepared = _prepare_double(self.vectors[slot])
            if len(prepared) == 0:
                raise ValueError("argument `...` should be a numeric vector")
            return self._mark(slot, "float", prepared)
        cache["used"] = True
        return cache["float"][self.index % len(cache["float"])]

    def text(self, which=_MISSING):
        slot = self._slot(which)
        cache = self.caches[slot]
        if cache["str"] is None:
            prepared = _prepare_string(self.vectors[slot], "...")
            if len(prepared) == 0:
                raise ValueError("argument `...` should be a character vector")
            return self._mark(slot, "str", prepared)
        cache["used"] = True
        return cache["str"][self.index % len(cache["str"])]


class _Spec:
    def __init__(self, fmt, start, stop, provider, na_string, inf_string, nan_string, use_length):
        self.provider = provider
        self.na_string = na_string
        self.inf_string = inf_string
        self.nan_string = nan_string
        self.use_length = use_length
        self.spec = fmt[stop]
        if self.spec in _INT_SPEC:
            self.kind = "int"
        elif self.spec in _FLOAT_SPEC:
            self.kind = "float"
        else:
            self.kind = "str"
        self.pad_right = False
        self.pad_zero = False
        self.sign_space = False
        self.sign_plus = False
        self.alternate = False
        self.min_width = _MISSING
        self.precision = _MISSING
        self.which = _MISSING
        cursor = start
        if cursor < stop and fmt[cursor].isdigit():
            which, next_cursor = _atoi_delim(fmt, cursor, stop, "$", False, start)
            if which is not _MISSING:
                self.which = which - 1
                cursor = next_cursor
        while cursor < stop:
            char = fmt[cursor]
            if char == " ":
                self.sign_space = True
            elif char == "+":
                self.sign_plus = True
            elif char == "0":
                self.pad_zero = True
            elif char == "-":
                self.pad_right = True
            elif char == "#":
                self.alternate = True
            else:
                break
            cursor += 1
        if cursor < stop and "1" <= fmt[cursor] <= "9":
            self.min_width, cursor = _atoi_other(fmt, cursor, stop, start)
        elif cursor < stop and fmt[cursor] == "*":
            cursor += 1
            which_width = _MISSING
            if cursor < stop and fmt[cursor].isdigit():
                which_width, cursor = _atoi_delim(fmt, cursor, stop, "$", True, start)
                if which_width is not _MISSING:
                    which_width -= 1
            self.min_width = provider.integer(which_width)
        if cursor < stop and fmt[cursor] == ".":
            cursor += 1
            if cursor == stop:
                self.precision = 0
            elif fmt[cursor].isdigit():
                self.precision, cursor = _atoi_other(fmt, cursor, stop, start)
            elif fmt[cursor] == "*":
                cursor += 1
                which_precision = _MISSING
                if cursor < stop and fmt[cursor].isdigit():
                    which_precision, cursor = _atoi_delim(
                        fmt, cursor, stop, "$", True, start
                    )
                    if which_precision is not _MISSING:
                        which_precision -= 1
                self.precision = provider.integer(which_precision)
            else:
                raise _specifier_error(fmt[start:stop + 1])
        if cursor != stop:
            raise _specifier_error(fmt[start:stop + 1])
        self._normalise()

    def _normalise(self):
        if self.spec == "i":
            self.spec = "d"
        if self.min_width is NA:
            pass
        elif self.min_width is _MISSING:
            pass
        elif self.min_width == 0:
            self.min_width = _MISSING
        elif isinstance(self.min_width, int) and self.min_width < 0:
            self.min_width = -self.min_width
            self.pad_right = True
        if self.precision is NA:
            pass
        elif self.precision is _MISSING:
            pass
        elif isinstance(self.precision, int) and self.precision < 0:
            self.precision = _MISSING
        if self.pad_right:
            self.pad_zero = False
        if self.sign_plus:
            self.sign_space = False
        if self.kind == "str":
            self.pad_zero = False
            self.sign_plus = False
            self.sign_space = False
            self.alternate = False
        elif self.kind == "int" and self.spec != "d":
            self.sign_plus = False
            self.sign_space = False

    def _picture(self):
        self._normalise()
        pieces = ["%"]
        if self.alternate:
            pieces.append("#")
        if self.sign_space:
            pieces.append(" ")
        if self.sign_plus:
            pieces.append("+")
        if self.pad_right:
            pieces.append("-")
        if self.pad_zero:
            pieces.append("0")
        if isinstance(self.min_width, int) and self.min_width > 0:
            pieces.append(str(self.min_width))
        if isinstance(self.precision, int) and self.precision >= 0:
            pieces.append(".")
            pieces.append(str(self.precision))
        pieces.append(self.spec)
        return "".join(pieces)

    def _special(self, body: str, signed_minus: bool, nan_like: bool) -> str:
        prefix = ""
        if nan_like:
            if self.sign_plus or self.sign_space:
                prefix = " "
        elif signed_minus:
            prefix = "-"
        elif self.sign_plus:
            prefix = "+"
        elif self.sign_space:
            prefix = " "
        return _pad(prefix + body, self.min_width, self.pad_right, self.use_length)

    def apply(self):
        if self.kind == "int":
            datum = self.provider.integer(self.which)
            missing = datum is NA or self.min_width is NA or self.precision is NA
            if not missing:
                return _snprintf(self._picture(), datum, "int")
            if self.na_string is NA:
                return NA
            return self._special(self.na_string, False, True)
        if self.kind == "float":
            datum = self.provider.real(self.which)
            missing = datum is NA or self.min_width is NA or self.precision is NA
            finite = (
                datum is not NA
                and isinstance(datum, float)
                and math.isfinite(datum)
            )
            if finite and not missing:
                return _snprintf(self._picture(), datum, "float")
            if (self.na_string is NA and missing) or (
                datum is not NA and isinstance(datum, float) and math.isnan(datum) and self.nan_string is NA
            ) or (
                datum is not NA and isinstance(datum, float) and math.isinf(datum) and self.inf_string is NA
            ):
                return NA
            if missing or (isinstance(datum, float) and math.isnan(datum)):
                body = self.na_string if missing else self.nan_string
                return self._special(body, False, True)
            negative = isinstance(datum, float) and math.copysign(1.0, datum) < 0
            return self._special(self.inf_string, negative, False)
        datum = self.provider.text(self.which)
        missing = datum is NA or self.min_width is NA or self.precision is NA
        if not missing:
            body = _trim_text(datum, self.precision, self.use_length)
            return _pad(body, self.min_width, self.pad_right, self.use_length)
        if self.na_string is NA:
            return NA
        body = _trim_text(self.na_string, self.precision, self.use_length)
        return _pad(body, self.min_width, self.pad_right, self.use_length)


def _format_one(pattern, provider, na_string, inf_string, nan_string, use_length):
    pieces = []
    index = 0
    size = len(pattern)
    while index < size:
        if pattern[index] != "%":
            pieces.append(pattern[index])
            index += 1
            continue
        index += 1
        if index >= size:
            raise ValueError("conversion specifier '%' is not valid")
        if pattern[index] == "%":
            pieces.append("%")
            index += 1
            continue
        start = index
        stop = _find_type(pattern, index)
        index = stop + 1
        spec = _Spec(
            pattern, start, stop, provider, na_string, inf_string, nan_string, use_length
        )
        formatted = spec.apply()
        if formatted is NA:
            return NA
        pieces.append(formatted)
    return "".join(pieces)


def stri_sprintf(
    format,
    *args,
    na_string=NA,
    inf_string="Inf",
    nan_string="NaN",
    use_length=False,
):
    """Format strings with ``%`` specifiers.

    Vectorized over ``format`` and every argument. A missing value in an
    argument makes that output missing when ``na_string`` is ``NA``.
    ``%s``, ``%d`` / ``%i`` / ``%o`` / ``%x`` / ``%X``, and
    ``%f`` / ``%e`` / ``%E`` / ``%g`` / ``%G`` / ``%a`` / ``%A`` are supported.
    """

    by_length = _prepare_logical_1(use_length, "use_length", allow_na=False)
    formats = _prepare_string(format, "format")
    na = _prepare_string_1(na_string, "na_string")
    inf = _prepare_string_1(inf_string, "inf_string")
    nan = _prepare_string_1(nan_string, "nan_string")
    vectors = [_vector(arg) for arg in args]
    length = len(formats)
    for vector in vectors:
        if len(vector) == 0:
            length = 0
            continue
        if length > 0 and length < len(vector):
            length = len(vector)
    if length <= 0:
        return []
    if length % len(formats) != 0:
        _warn("longer object length is not a multiple of shorter object length")
    for vector in vectors:
        if length % len(vector) != 0:
            _warn("longer object length is not a multiple of shorter object length")
    caches = [{"int": None, "float": None, "str": None, "used": False} for _ in vectors]
    result = []
    for index in range(length):
        pattern = formats[index % len(formats)]
        if pattern is NA:
            result.append(NA)
            continue
        provider = _Provider(vectors, caches, index)
        result.append(_format_one(pattern, provider, na, inf, nan, bool(by_length)))
    unused = sum(1 for cache in caches if not cache["used"])
    if unused == 1:
        _warn("one argument has not been used")
    elif unused > 1:
        _warn(f"{unused} arguments have not been used")
    return result


stri_string_format = stri_sprintf


def _show(value) -> str:
    if value is NA:
        return "NA"
    return value


def _cat_text(parts, sep: str) -> str:
    # cat() inserts sep between elements. When sep contains a newline, R
    # also terminates the output with a newline, including for an empty vector.
    shown = [_show(item) for item in parts]
    if "\n" in sep:
        if not shown:
            return "\n"
        return sep.join(shown) + "\n"
    return sep.join(shown)


def stri_printf(
    format,
    *args,
    file="",
    sep="\n",
    append=False,
    na_string="NA",
    inf_string="Inf",
    nan_string="NaN",
    use_length=False,
):
    """Format strings and write them, separated by ``sep``.

    The default missing-value text is the string ``"NA"``. ``file=""``
    writes to standard output. A path is encoded as UTF-8. Returns ``None``.
    """

    formatted = stri_sprintf(
        format,
        *args,
        na_string=na_string,
        inf_string=inf_string,
        nan_string=nan_string,
        use_length=use_length,
    )
    separator = sep if isinstance(sep, str) else str(sep)
    text = _cat_text(formatted, separator)
    if file is None or file == "":
        sys.stdout.write(text)
        return None
    payload = text.encode("utf-8")
    if hasattr(file, "write"):
        mode_text = False
        file.write(payload if "b" in getattr(file, "mode", "b") else text)
        return None
    path = Path(file)
    if append and path.exists():
        with path.open("ab") as handle:
            handle.write(payload)
    else:
        path.write_bytes(payload)
    return None


def s_dollar(e1, e2):
    """Format ``e1`` with ``stri_sprintf``.

    This is ``%s$%``. A tuple, or a list that itself contains lists, is the
    argument list. Any other value is one vector. Missing values stay missing.
    """

    if isinstance(e2, tuple) or (
        isinstance(e2, list) and any(isinstance(item, (list, tuple)) for item in e2)
    ):
        args = list(e2)
    else:
        args = [e2]
    return stri_sprintf(
        e1, *args, na_string=NA, inf_string="Inf", nan_string="NaN", use_length=False
    )


stri_dollar = s_dollar
