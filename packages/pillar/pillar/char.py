"""Character vectors that remember how a tibble column should shorten them.

The strings stay as they are. ``min_chars`` and ``shorten`` are stored on the
pillar attribute, and ``format`` of that attribute is the type label
``vec_ptype_full``. Column drawing, ``format.pillar_char`` and
``pillar_shaft``, is a different function.
"""

from __future__ import annotations

from typing import Any

from pillar._text import paste_atom

_CHOICES = ("back", "front", "mid", "abbreviate")
# The public name "abbreviate" is not in this switch, so it adds nothing.
# "never" and "abbr" are read only when already stored.
_MARKS = {
    "back": ">",
    "front": "<",
    "mid": "|",
    "never": "=",
    "abbr": "&",
}

_CHAR_CLASS = ("pillar_char", "pillar_vctr", "vctrs_vctr", "character")
_ATTR_CLASS = ("pillar_char_attr", "pillar_vctr_attr", "tibble_vec_attr")


class PillarCharAttr:
    """The ``pillar`` attribute: ``min_chars`` and ``shorten``."""

    def __init__(self, min_chars: Any = None, shorten: str | None = None):
        self.min_chars = list(min_chars) if isinstance(min_chars, list) else min_chars
        self.shorten = shorten
        self.classes = _ATTR_CLASS

    def __repr__(self) -> str:
        label = format_pillar_char_attr(self)
        return repr(label)


class PillarChar:
    """Data plus the pillar attribute.

    ``marked`` is true for a result of ``char()``, which carries the
    ``pillar_char`` class. ``set_char_opts`` leaves an ordinary vector unmarked.
    """

    def __init__(self, data: Any, pillar: PillarCharAttr, *, marked: bool):
        self.data = data
        self.pillar = pillar
        self.marked = marked
        self.classes = _CHAR_CLASS if marked else ()

    def __repr__(self) -> str:
        label = format_pillar_char_attr(self.pillar)
        kind = "char" if self.marked else "set_char_opts"
        return f"{kind}({self.data!r}, {label!r})"


def _reject_dots(args: tuple[Any, ...], kwargs: dict[str, Any]) -> None:
    if args or kwargs:
        raise ValueError("`...` must be empty.")


def _is_character(value: Any) -> bool:
    """R ``is.character``. None is a missing string. A list must be all strings."""

    if isinstance(value, PillarChar):
        return _is_character(value.data)
    if value is None or isinstance(value, str):
        return True
    if isinstance(value, list):
        return all(item is None or isinstance(item, str) for item in value)
    return False


def _copy_data(value: Any) -> Any:
    if isinstance(value, list):
        return list(value)
    return value


def _match_shorten(shorten: Any) -> str | None:
    """Exact ``arg_match`` against back, front, mid, and abbreviate.

    A prefix is not a choice. Omitted and None both stay None, which is R's
    NULL, and ``arg_match`` is not called.
    """

    if shorten is None:
        return None
    if not isinstance(shorten, str):
        raise ValueError("`shorten` must be a character vector")
    if shorten in _CHOICES:
        return shorten
    hits = [choice for choice in _CHOICES if choice.startswith(shorten)]
    hint = f' Did you mean "{hits[0]}"?' if len(hits) == 1 else ""
    raise ValueError(
        '`shorten` must be one of "back", "front", "mid", or "abbreviate", '
        f'not "{shorten}".{hint}'
    )


def format_pillar_char_attr(x: PillarCharAttr) -> Any:
    """``format.pillar_char_attr``. This is ``vec_ptype_full`` of a pillar_char.

    ``paste0`` of the unmatched switch result drops it, so ``abbreviate``
    leaves the label unchanged. A vector ``min_chars`` is recycled.
    """

    extra = None
    if x.shorten is not None:
        extra = _MARKS.get(x.shorten)

    if isinstance(x.min_chars, list):
        parts = [f"pillar_char({paste_atom(item)})" for item in x.min_chars]
        if extra is not None:
            parts = [part + extra for part in parts]
        return parts

    out = "pillar_char"
    if x.min_chars is not None:
        out = f"{out}({paste_atom(x.min_chars)})"
    if extra is not None:
        out = out + extra
    return out


def vec_ptype_full(x: PillarChar) -> Any:
    """``format(attr(x, "pillar"))``."""

    return format_pillar_char_attr(x.pillar)


def vec_ptype_abbr(x: PillarChar) -> str:
    """``char``, or ``abbr`` only when the stored shorten is exactly ``abbr``.

    An unmarked ``set_char_opts`` result is still a plain character vector,
    so the abbreviation stays ``chr``.
    """

    if not isinstance(x, PillarChar):
        raise TypeError("vec_ptype_abbr expects the result of char() or set_char_opts()")
    if not x.marked:
        if _is_character(x.data):
            return "chr"
        raise TypeError("vec_ptype_abbr for this value is not a character abbreviation")
    if x.pillar.shorten is not None and x.pillar.shorten == "abbr":
        return "abbr"
    return "char"


def set_char_opts(
    x: Any,
    *args: Any,
    min_chars: Any = None,
    shorten: str | None = None,
    **kwargs: Any,
) -> PillarChar:
    """Attach character options and keep the existing data."""

    _reject_dots(args, kwargs)
    chosen = _match_shorten(shorten)
    if isinstance(x, PillarChar):
        data = _copy_data(x.data)
        marked = x.marked
    else:
        data = _copy_data(x)
        marked = False
    return PillarChar(data, PillarCharAttr(min_chars, chosen), marked=marked)


def char(
    x: Any,
    *args: Any,
    min_chars: Any = None,
    shorten: str | None = None,
    **kwargs: Any,
) -> PillarChar:
    """A character vector with those options, marked as pillar_char."""

    if not _is_character(x):
        raise ValueError("is.character(x) is not TRUE")
    _reject_dots(args, kwargs)
    out = set_char_opts(x, min_chars=min_chars, shorten=shorten)
    out.marked = True
    out.classes = _CHAR_CLASS
    return out
