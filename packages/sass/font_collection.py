"""Translation of sass::font_collection().

R takes its fonts through `...` in one order, and a named font is a call like
font_collection("Open Sans", google = list(...), "serif"). Python cannot write
a positional argument after a keyword argument, so a named font in the middle
of the list is written as Named("google", value):

    font_collection("Open Sans", Named("google", {...}), "serif")

The families and html dependencies come out in the order the fonts were given.
Keyword arguments (face = {...}, link = {...}) are accepted for the one-named
case, and they follow the positional fonts in the order they were written.

Named helpers are google, link, face, and collection, as in R's
known_font_helpers. A value that is a dict is passed as keyword arguments,
a list or tuple as positional arguments, and anything else as one argument.
"""

from ._common import FontCollection
from ._sass_values import new_font_collection
from .font_face import font_face
from .font_google import font_google
from .font_link import font_link


class Named:
    """A named font argument, the Python form of R's name = value in `...`."""

    def __init__(self, name, value):
        self.name = name
        self.value = value


def _collection_helper(*args, **kwargs):
    return font_collection(*args, **kwargs)


_HELPERS = {
    "google": font_google,
    "link": font_link,
    "face": font_face,
    "collection": _collection_helper,
}


def _call_helper(name, value):
    func = _HELPERS.get(name)
    if func is None:
        raise ValueError(
            f"Unsupported argument name: {name}.\n"
            f"Did you want to try one of these names instead: {', '.join(_HELPERS)}?"
        )
    if isinstance(value, dict):
        return func(**value)
    if isinstance(value, (list, tuple)):
        return func(*value)
    return func(value)


def font_collection(*dots, default_flag=True, quote=True, **named):
    items = []
    for item in dots:
        if isinstance(item, Named):
            items.append((item.name, item.value))
        else:
            items.append(("", item))
    items += list(named.items())

    values = []
    for name, value in items:
        if value is None:
            continue
        values.append(value if name == "" else _call_helper(name, value))

    families = []
    deps = []
    for value in values:
        if isinstance(value, FontCollection):
            families.extend(value.families)
            deps.extend(value.html_deps)
        elif isinstance(value, str) and value != "":
            families.append(value)
        else:
            raise TypeError(
                "`font_collection()` expects a collection of `font_google()`, "
                "`font_link()`, `font_face()`, and/or non-empty character strings."
            )
    return new_font_collection(families, deps, default_flag=default_flag is True, quote=quote)
