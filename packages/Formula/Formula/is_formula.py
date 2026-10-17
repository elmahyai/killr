"""Whether an object inherits from class Formula.

From Formula 1.2-6 ``R/Formula.R``. The body is ``inherits(object, "Formula")``.
"""

from __future__ import annotations


class FormulaError(Exception):
    """An R error raised while matching the ``object`` argument."""


class RClassed:
    """An R value with a class vector and an optional S4 bit.

    ``classes`` is ``class()``. ``None`` is a missing class name. ``s4``
    is the S4 bit. ``extends`` is the chain ``methods::extends`` would
    return for the primary class; an S3 object does not consult it.
    """

    def __init__(self, classes=(), s4=False, extends=None):
        self.classes = tuple(classes)
        self.s4 = bool(s4)
        self.extends = None if extends is None else tuple(extends)


def is_Formula(*args, **kwargs):
    """True when ``object`` inherits from class Formula.

    The formal is ``object``. A unique prefix matches it. An S3 class
    matches when the string ``Formula`` appears anywhere in the class
    vector. An S4 object matches when its first class is ``Formula``,
    or when that class's extends chain contains ``Formula``. A later
    class string on an S4 object does not.
    """
    value = _match_object(args, kwargs)
    return _inherits_formula(value)


def _inherits_formula(value) -> bool:
    if not isinstance(value, RClassed):
        return False
    if value.s4:
        if not value.classes or value.classes[0] is None:
            return False
        if value.classes[0] == "Formula":
            return True
        return value.extends is not None and "Formula" in value.extends
    return any(item == "Formula" for item in value.classes)


def _match_object(args, kwargs):
    supplied = [(None, value) for value in args]
    supplied.extend(kwargs.items())
    exact = [index for index, (name, _) in enumerate(supplied) if name == "object"]
    if len(exact) > 1:
        raise FormulaError(
            'formal argument "object" matched by multiple actual arguments'
        )
    partials = [
        index
        for index, (name, _) in enumerate(supplied)
        if name is not None and name != "object" and _is_prefix(name, "object")
    ]
    matched = exact[0] if exact else None
    if matched is None:
        if len(partials) > 1:
            raise FormulaError(
                'formal argument "object" matched by multiple actual arguments'
            )
        if len(partials) == 1:
            matched = partials[0]
        else:
            for index, (name, _) in enumerate(supplied):
                if name is None:
                    matched = index
                    break
    unused = [pair for index, pair in enumerate(supplied) if index != matched]
    if unused:
        rendered = [_render_unused(name, value) for name, value in unused]
        if len(rendered) == 1:
            raise FormulaError(f"unused argument ({rendered[0]})")
        raise FormulaError("unused arguments (" + ", ".join(rendered) + ")")
    if matched is None:
        raise FormulaError('argument "object" is missing, with no default')
    return supplied[matched][1]


def _is_prefix(name: str, formal: str) -> bool:
    return bool(name) and formal.startswith(name)


def _render_unused(name, value) -> str:
    text = _deparse(value)
    if name is None:
        return text
    return f"{name} = {text}"


def _deparse(value) -> str:
    if value is True:
        return "TRUE"
    if value is False:
        return "FALSE"
    if isinstance(value, int):
        return str(value)
    raise FormulaError(f"unused argument is not a literal ({type(value).__name__})")
