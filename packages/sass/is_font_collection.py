"""Translation of sass::is_font_collection()."""

from ._common import FontCollection


def is_font_collection(x):
    return isinstance(x, FontCollection)
