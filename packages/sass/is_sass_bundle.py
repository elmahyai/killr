"""Translation of sass::is_sass_bundle()."""

from ._common import SassBundle


def is_sass_bundle(x):
    return isinstance(x, SassBundle)
