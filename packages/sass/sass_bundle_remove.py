"""Translation of sass::sass_bundle_remove."""

from ._common import SassBundle


def sass_bundle_remove(bundle, name):
    if not isinstance(bundle, SassBundle):
        raise TypeError("`bundle` must be a SassBundle.")
    names = [name] if isinstance(name, str) else list(name)
    if not all(isinstance(item, str) and item for item in names):
        raise ValueError("`name` needs to be a character vector containing non-NA and non-empty values")
    for item in names:
        bundle.layers.pop(item, None)
    return bundle
