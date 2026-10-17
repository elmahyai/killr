"""Get and set the list of progression handlers."""

from __future__ import annotations

import inspect
import sys
import warnings

from progressr.options import (
    ProgressrError,
    get_option,
    match_arg,
    set_option,
    squote,
    stop_if_not,
)


_GLOBAL_REGISTERED = False
_GLOBAL_ACTIVE = True


def handler_txtprogressbar(*args, **kwargs):
    """The default text bar. Imported lazily so this module does not load the bar at import."""
    from progressr.bars import handler_txtprogressbar as draw

    return draw(*args, **kwargs)


def global_progression_handler(condition=None):
    """Active flag toggled by with_progress. Registration itself is handlers(global_=...)."""
    global _GLOBAL_ACTIVE
    if isinstance(condition, bool):
        _GLOBAL_ACTIVE = condition
        return None
    if not _GLOBAL_ACTIVE:
        return None
    return None


def register_global_progression_handler(action="add"):
    """Record whether the global handler is enabled. Query returns that flag."""
    global _GLOBAL_REGISTERED
    action = match_arg(action, ("add", "remove", "query", "status"))
    if action == "query" or action == "status":
        return _GLOBAL_REGISTERED
    if action == "add":
        _GLOBAL_REGISTERED = True
        return True
    _GLOBAL_REGISTERED = False
    return False


def _formals_length(fn) -> int:
    try:
        signature = inspect.signature(fn)
    except (TypeError, ValueError):
        return 1 if callable(fn) else 0
    count = 0
    for parameter in signature.parameters.values():
        if parameter.kind == inspect.Parameter.POSITIONAL_ONLY and parameter.name == "self":
            continue
        count += 1
    return count


def _lookup_handler(name):
    candidates = (f"handler_{name}", name)
    modules = []
    for module_name, module in list(sys.modules.items()):
        if module is None:
            continue
        if module_name == "progressr" or module_name.startswith("progressr."):
            modules.append(module)
    for candidate in candidates:
        for module in modules:
            found = getattr(module, candidate, None)
            if callable(found):
                return found
    return None


def _normalize_handlers(args):
    if len(args) == 1 and isinstance(args[0], (list, tuple)) and not callable(args[0]):
        values = list(args[0])
        names = list(getattr(args[0], "keys", lambda: [None] * len(values))())
        if isinstance(args[0], dict):
            names = list(args[0].keys())
            values = list(args[0].values())
        elif hasattr(args[0], "_names"):
            names = list(args[0]._names)
        else:
            names = [None] * len(values)
        return values, names
    names = [None] * len(args)
    return list(args), names


def handlers(*args, append=False, on_missing=("error", "warning", "ignore"), default=None, global_=None, **named):
    """Return or replace progression handlers.

    `global_` is R's `global` (a Python keyword). True and False return whether
    the global handler is enabled. float('nan') queries that flag. Keyword
    arguments other than the parameters above are named handlers.
    """
    import math

    query = isinstance(global_, float) and math.isnan(global_)
    stop_if_not(global_ is None or query or isinstance(global_, bool))
    if named:
        args = tuple(args) + tuple(named.values())
    if len(args) == 0:
        if global_ is None:
            if default is None:
                default = handler_txtprogressbar
            if not isinstance(default, list):
                default = [default]
            current = get_option("progressr.handlers", None)
            if current is None:
                return list(default)
            return current
        if query:
            return register_global_progression_handler("query")
        action = "add" if global_ is True else "remove"
        return register_global_progression_handler(action)

    on_missing = match_arg(on_missing, ("error", "warning", "ignore"))
    values, names = _normalize_handlers(args)
    if named and not (len(args) == 1 and isinstance(args[0], (list, tuple)) and not callable(args[0])):
        # Keyword handlers keep the names passed by the caller.
        offset = len(values) - len(named)
        for index, key in enumerate(named):
            names[offset + index] = key
    built = []
    built_names = []
    for index, handler in enumerate(values):
        stop_if_not(not isinstance(handler, (list, tuple)))
        name = names[index] if index < len(names) else None
        if isinstance(handler, str):
            name = handler
            found = _lookup_handler(handler)
            if found is None:
                if on_missing == "error":
                    raise ProgressrError(f"No such progression handler found: {squote(name)}")
                if on_missing == "warning":
                    warnings.warn(
                        f"Ignoring non-existing progression handler: {squote(name)}",
                        stacklevel=2,
                    )
                continue
            handler = found
        stop_if_not(callable(handler))
        stop_if_not(_formals_length(handler) >= 1)
        validator = getattr(handler, "validator", None)
        if callable(validator) and not validator():
            continue
        built.append(handler)
        built_names.append(name)
    if append:
        current = get_option("progressr.handlers", None)
        if current:
            current_names = list(getattr(current, "_names", [None] * len(current)))
            if len(current_names) != len(current):
                current_names = [None] * len(current)
            built = list(current) + built
            built_names = current_names + built_names
    named = _NamedList(built, built_names)
    old = get_option("progressr.handlers", None)
    set_option("progressr.handlers", named)
    if old is None:
        old = _NamedList([], [])
    if global_ is not None and not query:
        action = "add" if global_ is True else "remove"
        register_global_progression_handler(action)
    return old


class _NamedList(list):
    """A handler list that remembers R names."""

    def __init__(self, values, names):
        super().__init__(values)
        self._names = list(names)

    def __add__(self, other):
        names = list(self._names)
        if isinstance(other, _NamedList):
            names.extend(other._names)
        else:
            names.extend([None] * len(other))
        return _NamedList(list(super().__add__(list(other))), names)
