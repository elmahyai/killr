"""Mark text as HTML, from htmltools 0.5.9.

``HTML`` concatenates ``text`` and the extra arguments with a space and
marks the result so later tag code will not escape it. The text argument
is pasted element by element. Each extra argument is one element of
``as.character(dots_list(...))``, so a vector longer than one is the
deparsed ``c(...)`` text rather than its pasted elements. ``.noWS`` is
stored and is not checked.
"""

from __future__ import annotations

import math

from htmltools.escape import NA, _character_double, is_na

_MISSING = object()
_ABSENT = object()

_IGNORE_CHOICES = ("trailing", "none", "all")
_HOMONYM_CHOICES = ("keep", "first", "last", "error")
_RESERVED_NAMES = {
    "if",
    "else",
    "repeat",
    "while",
    "function",
    "for",
    "in",
    "next",
    "break",
    "TRUE",
    "FALSE",
    "NULL",
    "Inf",
    "NaN",
    "NA",
    "NA_integer_",
    "NA_real_",
    "NA_complex_",
    "NA_character_",
    "...",
}

_IGNORE_NOPE = (
    '`.ignore_empty` must be one of "trailing", "none", or "all", not "nope".\n'
    '\u2139 Did you mean "none"?'
)
_HOMONYM_NOPE = (
    '`.homonyms` must be one of "keep", "first", "last", or "error", not\n'
    '"nope".'
)
_LOGICAL_CHARACTER = "LOGICAL() can only be applied to a 'logical', not a 'character'"


class Html(str):
    """A length-one character string with class ``c("html", "character")``."""

    def __new__(cls, text, no_ws=None):
        obj = str.__new__(cls, text)
        obj.html = True
        obj.noWS = no_ws
        obj.r_class = ("html", "character")
        return obj


def _is_scalar(value) -> bool:
    if value is None or is_na(value):
        return True
    if isinstance(value, (str, bool, int, float, complex)):
        return True
    return False


def _is_atomic(values) -> bool:
    return all(_is_scalar(item) and not isinstance(item, dict) for item in values) and all(
        not isinstance(item, (list, tuple)) for item in values
    )


def _mode(values) -> str:
    if any(isinstance(item, str) for item in values):
        return "character"
    if any(isinstance(item, complex) for item in values):
        return "complex"
    if any(isinstance(item, float) for item in values):
        return "double"
    if any(isinstance(item, int) and not isinstance(item, bool) for item in values):
        return "integer"
    return "logical"


def _complex_token(value: complex) -> str:
    real = _character_double(float(value.real))
    imag = float(value.imag)
    if imag < 0.0 or (imag == 0.0 and math.copysign(1.0, imag) < 0.0):
        return real + "-" + _character_double(abs(imag)) + "i"
    return real + "+" + _character_double(imag) + "i"


def _as_complex(value) -> complex:
    if isinstance(value, complex):
        return value
    if isinstance(value, bool):
        return complex(1.0 if value else 0.0, 0.0)
    if isinstance(value, (int, float)):
        return complex(float(value), 0.0)
    raise ValueError("argument is not a character vector")


def _paste_token(value, mode: str) -> str:
    """One element of ``paste(..., collapse = " ")``."""

    if is_na(value):
        return "NA"
    if mode == "character":
        if isinstance(value, str):
            return value
        if isinstance(value, bool):
            return "TRUE" if value else "FALSE"
        if isinstance(value, complex):
            return _complex_token(value)
        if isinstance(value, float):
            return _character_double(value)
        if isinstance(value, int):
            return str(value)
        return str(value)
    if mode == "logical":
        return "TRUE" if value else "FALSE"
    if mode == "integer":
        if isinstance(value, bool):
            return "1" if value else "0"
        return str(value)
    if mode == "double":
        if isinstance(value, bool):
            return "1" if value else "0"
        if isinstance(value, int):
            return _character_double(float(value))
        return _character_double(value)
    return _complex_token(_as_complex(value))


def _quote(text: str) -> str:
    """R deparse of one string: escapes, then double quotes."""

    parts = ['"']
    for char in text:
        if char == "\\":
            parts.append("\\\\")
        elif char == '"':
            parts.append('\\"')
        elif char == "\n":
            parts.append("\\n")
        elif char == "\r":
            parts.append("\\r")
        elif char == "\t":
            parts.append("\\t")
        elif char == "\a":
            parts.append("\\a")
        elif char == "\b":
            parts.append("\\b")
        elif char == "\f":
            parts.append("\\f")
        elif char == "\v":
            parts.append("\\v")
        else:
            code = ord(char)
            if code < 32 or code == 127:
                parts.append("\\%03o" % code)
            else:
                parts.append(char)
    parts.append('"')
    return "".join(parts)


def _syntactic(name: str) -> bool:
    if not name or name in _RESERVED_NAMES:
        return False
    first = name[0]
    if first == ".":
        if len(name) > 1 and name[1].isdigit():
            return False
    elif not ("A" <= first <= "Z" or "a" <= first <= "z"):
        return False
    for char in name[1:]:
        if not (
            "A" <= char <= "Z" or "a" <= char <= "z" or "0" <= char <= "9" or char in "._"
        ):
            return False
    return True


def _fmt_name(name: str) -> str:
    if _syntactic(name):
        return name
    return "`" + name.replace("\\", "\\\\").replace("`", "\\`") + "`"


def _deparse_token(value, mode: str) -> str:
    """One element inside ``c()`` or ``list()``."""

    if mode == "character":
        if is_na(value):
            return "NA"
        return _quote(_paste_token(value, "character"))
    if is_na(value):
        return "NA"
    return _paste_token(value, mode)


def _is_colon(values) -> bool:
    if len(values) < 2:
        return False
    numbers = []
    for value in values:
        if is_na(value):
            return False
        if isinstance(value, bool):
            numbers.append(1 if value else 0)
        elif isinstance(value, int):
            numbers.append(value)
        else:
            return False
    step = numbers[1] - numbers[0]
    if step not in (1, -1):
        return False
    for previous, current in zip(numbers, numbers[1:]):
        if current - previous != step:
            return False
    return True


def _deparse_atomic(values) -> str:
    if len(values) == 0:
        # An empty Python list is an empty character vector.
        return "character(0)"
    mode = _mode(values)
    if mode == "integer" and _is_colon(values):
        start = _paste_token(values[0], "integer")
        end = _paste_token(values[-1], "integer")
        return start + ":" + end
    tokens = [_deparse_token(value, mode) for value in values]
    return "c(" + ", ".join(tokens) + ")"


def _deparse_inside(value) -> str:
    if isinstance(value, dict):
        return _deparse_dict(value)
    if isinstance(value, (list, tuple)):
        if _is_atomic(value):
            if len(value) == 1:
                return _deparse_token(value[0], _mode(value))
            return _deparse_atomic(value)
        parts = [_deparse_inside(item) for item in value]
        return "list(" + ", ".join(parts) + ")"
    if value is None:
        return "NULL"
    if isinstance(value, str):
        return _quote(value) if not is_na(value) else "NA"
    mode = _mode([value])
    return _deparse_token(value, mode)


def _deparse_dict(value: dict) -> str:
    parts = []
    for key, item in value.items():
        token = _deparse_inside(item)
        if key == "":
            parts.append(token)
        else:
            parts.append(_fmt_name(str(key)) + " = " + token)
    return "list(" + ", ".join(parts) + ")"


def _as_character_dot(value) -> str:
    """``as.character`` of one element of the dots list.

    A length-one atomic value is its ordinary character form, so a string
    is not quoted again. Anything longer is deparsed, which is why
    ``c("x", "y")`` becomes the text ``c("x", "y")``.
    """

    if value is None:
        return "NULL"
    if isinstance(value, dict):
        return _deparse_dict(value)
    if isinstance(value, (list, tuple)):
        if not _is_atomic(value):
            parts = [_deparse_inside(item) for item in value]
            return "list(" + ", ".join(parts) + ")"
        if len(value) == 1:
            return _paste_token(value[0], _mode(value))
        return _deparse_atomic(value)
    if _is_scalar(value):
        return _paste_token(value, _mode([value]))
    raise ValueError("argument is not a character vector")


def _text_pieces(text) -> list:
    if text is None:
        return []
    if isinstance(text, dict) or (
        isinstance(text, (list, tuple)) and not _is_atomic(text)
    ):
        raise ValueError("argument is not a character vector")
    if isinstance(text, (list, tuple)):
        mode = _mode(text)
        return [_paste_token(item, mode) for item in text]
    if _is_scalar(text):
        return [_paste_token(text, _mode([text]))]
    raise ValueError("argument is not a character vector")


def _require_flag(value, label: str) -> None:
    if isinstance(value, bool) or is_na(value):
        return
    if isinstance(value, str):
        raise ValueError(_LOGICAL_CHARACTER)
    raise ValueError(_LOGICAL_CHARACTER)


def _consume_formals(kwargs: dict) -> None:
    """Names that ``dots_list`` takes itself are not concatenated."""

    named = kwargs.pop(".named", _ABSENT)
    ignore = kwargs.pop(".ignore_empty", _ABSENT)
    preserve = kwargs.pop(".preserve_empty", _ABSENT)
    homonyms = kwargs.pop(".homonyms", _ABSENT)
    check_assign = kwargs.pop(".check_assign", _ABSENT)
    if named is not _ABSENT and not isinstance(named, bool):
        raise ValueError("`.named` must be a logical value.")
    if ignore is not _ABSENT and ignore not in _IGNORE_CHOICES:
        if ignore == "nope":
            raise ValueError(_IGNORE_NOPE)
        shown = ignore
        raise ValueError(
            f'`.ignore_empty` must be one of "trailing", "none", or "all", not "{shown}".'
        )
    if homonyms is not _ABSENT and homonyms not in _HOMONYM_CHOICES:
        if homonyms == "nope":
            raise ValueError(_HOMONYM_NOPE)
        raise ValueError(
            "`.homonyms` must be one of \"keep\", \"first\", \"last\", or \"error\", not "
            f'"{homonyms}".'
        )
    if preserve is not _ABSENT:
        _require_flag(preserve, ".preserve_empty")
    if check_assign is not _ABSENT:
        _require_flag(check_assign, ".check_assign")


def HTML(text=_MISSING, *args, noWS=None, **kwargs):
    """Mark ``text`` as HTML and join every piece with a space.

    ``text`` is an atomic vector: a string, number, or logical, or a flat
    list of those. ``None`` is ``NULL``. A list of lists, or a dict, is an
    R list and is rejected. Extra positional arguments and other keywords
    are appended after ``as.character``. ``noWS`` is R's ``.noWS`` and is
    stored on the result. Keywords ``.named``, ``.ignore_empty``,
    ``.preserve_empty``, ``.homonyms``, and ``.check_assign`` belong to
    ``dots_list`` and are not pasted.
    """

    if text is _MISSING:
        raise ValueError('argument "text" is missing, with no default')
    extra = dict(kwargs)
    _consume_formals(extra)
    pieces = _text_pieces(text)
    for arg in args:
        pieces.append(_as_character_dot(arg))
    for value in extra.values():
        pieces.append(_as_character_dot(value))
    if not pieces:
        collapsed = ""
    else:
        collapsed = " ".join(pieces)
    return Html(collapsed, noWS)
