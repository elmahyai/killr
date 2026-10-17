"""Extraction helpers for multiple-imputation results."""

from typing import Callable


def MIextract(results, expr=None, fun: Callable | None = None):
    """Extract one value from each result using an expression or callable."""
    if expr is not None:
        if callable(expr):
            return [expr(result) for result in results]
        if isinstance(expr, str):
            return [result[expr] for result in results]
        raise TypeError("expr must be callable or a field name")
    if fun is None:
        raise TypeError("one of expr or fun must be supplied")
    return [fun(result) for result in results]
