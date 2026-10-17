"""The operator %&&%."""

from rlang import is_null


def null_and(left, right):
    if not is_null(left):
        return right
    return left
