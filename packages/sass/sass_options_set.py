from ._common import _GLOBAL_OPTIONS


def sass_options_set(*args, **kwargs):
    if args and kwargs:
        raise TypeError("options must be supplied as named arguments")
    if len(args) > 1:
        raise TypeError("expected one options mapping")
    if args:
        value = args[0]
        if value is None:
            _GLOBAL_OPTIONS.clear()
        elif isinstance(value, dict):
            _GLOBAL_OPTIONS.clear()
            _GLOBAL_OPTIONS.update(value)
        else:
            raise TypeError("options must be a mapping")
    elif not kwargs:
        raise ValueError("`...` must be non-empty.")
    else:
        _GLOBAL_OPTIONS.clear()
        _GLOBAL_OPTIONS.update(kwargs)
    return None
