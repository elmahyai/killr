"""Translation of sass::font_face()."""

from ._sass_values import (
    DISPLAY_CHOICES,
    SASS_VERSION,
    HtmlDep,
    font_dep_name,
    font_face_css,
    match_arg,
    new_font_collection,
    quote_css_font_families,
    r_chr,
)


def _collapse(value, sep):
    if value is None:
        return None
    if isinstance(value, (list, tuple)):
        return sep.join(r_chr(v) for v in value)
    return r_chr(value)


def font_face(family, src, weight=None, style=None, display=DISPLAY_CHOICES,
              stretch=None, variant=None, unicode_range=None):
    family_q = quote_css_font_families(family if isinstance(family, (list, tuple)) else [family])
    display_value = None if display is None else match_arg(display, DISPLAY_CHOICES)
    fields = [
        ("family", family_q),
        ("src", _collapse(src, ", ")),
        ("weight", _collapse(weight, " ")),
        ("style", _collapse(style, " ")),
        ("display", display_value),
        ("stretch", _collapse(stretch, " ")),
        ("variant", _collapse(variant, " ")),
        ("unicode_range", _collapse(unicode_range, ", ")),
    ]
    props = [(name, value) for name, value in fields if value is not None]
    css = font_face_css(props)
    dep = HtmlDep(
        name=font_dep_name(family_q),
        version=SASS_VERSION,
        kind="face",
        stylesheet=css,
    )
    return new_font_collection([family_q], [dep])
