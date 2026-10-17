"""The operator := for dynamic dots."""

from rlang import abort, caller_env


def colon_equals(x, y):
    abort("`:=` can only be used within dynamic dots.", call=caller_env())
