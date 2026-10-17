"""Translation of sass::sass_bundle."""

from ._common import SassBundle, SassLayer


def _as_layer(value):
    if isinstance(value, SassBundle):
        if len(value.layers) == 1:
            return next(iter(value.layers.values()))
        return SassLayer(rules=value)
    if isinstance(value, SassLayer):
        return value
    if isinstance(value, dict):
        return SassLayer(defaults=value)
    return SassLayer(rules=value)


def sass_bundle(*args, **kwargs):
    layers = list(args) + list(kwargs.values())
    names = [None] * len(args) + list(kwargs)
    return SassBundle({name or "": _as_layer(value) for name, value in zip(names, layers)})
