"""HTML tag helpers and the tag-stripping width used by HTML styles."""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence

_TAG = re.compile(r"<[^>]*>")
_ENTITY = re.compile(r"&(?:[a-z\d]+|#\d+|#x[a-f\d]+);")


def _character_vector(x, name: str) -> list[str]:
    if isinstance(x, str):
        return [x]
    if isinstance(x, Sequence) and not isinstance(x, (bytes, bytearray)):
        out: list[str] = []
        for item in x:
            if not isinstance(item, str):
                raise TypeError(f"Argument `{name}` must be character")
            out.append(item)
        return out
    raise TypeError(f"Argument `{name}` must be character")


def _class_text(class_: str | Sequence[str]) -> str:
    classes = _character_vector(class_, "class")
    if not classes:
        return ""
    return " " + " ".join(classes)


def _style_text(style: Mapping[str, str] | Sequence[str]) -> str:
    if isinstance(style, str):
        raise TypeError("Argument `style` must be a named character vector")
    if isinstance(style, Mapping):
        if not style:
            return ""
        parts = [f"{name}: {value}" for name, value in style.items()]
        return " style='" + "; ".join(parts) + ";'"
    values = _character_vector(style, "style")
    if not values:
        return ""
    parts = [f"NA: {value}" for value in values]
    return " style='" + "; ".join(parts) + ";'"


def tag_f(tag: str, class_: str | Sequence[str] | None = None, style: Mapping[str, str] | Sequence[str] | None = None):
    """Return a function that wraps each string in ``tag``."""

    if class_ is None:
        class_ = []
    if style is None:
        style = []
    if not isinstance(tag, str):
        raise TypeError("Argument `tag` must be character(1L) and not NA")
    class_text = _class_text(class_)
    # `_class_text` adds a leading space. The tag form wants ` class='...'`
    # only when there is at least one class, without doubling the space.
    classes = class_text[1:] if class_text else ""
    style_text = _style_text(style)
    class_attr = f" class='{classes}'" if classes else ""

    def wrap(x):
        if isinstance(x, str):
            values = [x]
            scalar = True
        else:
            values = _character_vector(x, "x")
            scalar = False
        if not values:
            return []
        wrapped = [
            f"<{tag}{class_attr}{style_text}>{item}</{tag}>" for item in values
        ]
        if scalar:
            return wrapped[0]
        return wrapped

    return wrap


def div_f(class_: str | Sequence[str] | None = None, style: Mapping[str, str] | Sequence[str] | None = None):
    """``tag_f`` for ``div``."""

    if class_ is None:
        class_ = []
    if style is None:
        style = []
    return tag_f("div", class_, style)


def span_f(class_: str | Sequence[str] | None = None, style: Mapping[str, str] | Sequence[str] | None = None):
    """``tag_f`` for ``span``."""

    if class_ is None:
        class_ = []
    if style is None:
        style = []
    return tag_f("span", class_, style)


def cont_f(class_: str | Sequence[str] | None = None):
    """Wrap the whole vector in one ``diffobj-container`` div."""

    if class_ is None:
        class_ = []
    extra = _class_text(class_)

    def wrap(x):
        values = [x] if isinstance(x, str) else _character_vector(x, "x")
        body = "".join(values)
        return (
            f"<div class='diffobj-container{extra}'>"
            f"<pre class='diffobj-content'>{body}</pre></div>"
        )

    return wrap


def nchar_html(x, *_args) -> int | list[int]:
    """Character count after tags are removed and entities become one column."""

    scalar = isinstance(x, str)
    values = [x] if scalar else _character_vector(x, "x")
    counts: list[int] = []
    for item in values:
        tagless = _TAG.sub("", item)
        plain = _ENTITY.sub("X", tagless)
        counts.append(len(plain))
    if scalar:
        return counts[0]
    return counts
