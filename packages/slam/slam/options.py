"""slam_options, including the dense-expansion limit."""

_MISSING = object()
_OPTIONS = {"max_dense": 2**24}


def slam_options(option=_MISSING, value=_MISSING):
    """Read or set a slam option. With no arguments, return the list."""
    if option is _MISSING:
        return dict(_OPTIONS)
    if option not in _OPTIONS and value is _MISSING:
        return None
    if value is _MISSING:
        return _OPTIONS[option]
    _OPTIONS[option] = value
    return value
