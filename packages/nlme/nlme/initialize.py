"""``Initialize`` generic (nlme ``Initialize``): dispatch on the class of ``object``.

R's ``Initialize`` is an S3 generic. Python keeps the dispatch and calls the
module-level ``initialize`` of the method that matches the object's class vector.
Methods for classes not yet translated are not registered, so they raise the
same "no applicable method" error as an unknown class.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

__all__ = ["Initialize"]

# Python dataclass name -> R class name, for objects without a ``classes`` field.
_R_CLASS_BY_TYPE = {
    "CorLin": "corLin",
    "CorRatio": "corRatio",
    "CorSpher": "corSpher",
    "CorSymm": "corSymm",
    "CorCompSymm": "corCompSymm",
    "VarIdent": "varIdent",
    "VarPower": "varPower",
    "CorNatural": "corNatural",
    "CorAR1": "corAR1",
    "CorExp": "corExp",
    "CorGaus": "corGaus",
    "CorCAR1": "corCAR1",
}


def _methods() -> dict[str, Callable[..., Any]]:
    from nlme import corar1, corarma, cornatural, corcompsymm, corlin, corratio, corspher, corsymm, var_ident, var_power
    from nlme import varexp
    from nlme import corexp, corgaus, corcar1
    from nlme import restruct

    return {
        "corNatural": cornatural.initialize,
        "corAR1": corar1.initialize,
        "corARMA": corarma.initialize,
        "reStruct": restruct.initialize,
        "varExp": varexp.initialize,
        "corLin": corlin.initialize,
        "corRatio": corratio.initialize,
        "corSpher": corspher.initialize,
        "corSymm": corsymm.initialize,
        "corCompSymm": corcompsymm.initialize,
        "corExp": corexp.initialize,
        "corGaus": corgaus.initialize,
        "corCAR1": corcar1.initialize,
        "varIdent": var_ident.initialize,
        "varPower": var_power.initialize,
    }


def _class_vector(object: Any) -> tuple[str, ...]:
    classes = getattr(object, "classes", None)
    if classes is not None:
        return tuple(classes)
    name = type(object).__name__
    return (_R_CLASS_BY_TYPE.get(name, name),)


def Initialize(object: Any, data: Any, **kwargs: Any) -> Any:
    """Initialize ``object`` on ``data`` with the method for its first matching class."""
    methods = _methods()
    classes = _class_vector(object)
    for name in classes:
        method = methods.get(name)
        if method is not None:
            return method(object, data, **kwargs)
    if len(classes) == 1:
        shown = f'"{classes[0]}"'
    else:
        shown = "c(" + ", ".join(f"'{name}'" for name in classes) + ")"
    raise TypeError(f"no applicable method for 'Initialize' applied to an object of class {shown}")
