from ._common import _GLOBAL_OPTIONS, options


def sass_options_get(**kwargs):
    values = dict(_GLOBAL_OPTIONS)
    values.update(kwargs)
    return options(**values)
