"""Define an expression-substitution macro (gtools 3.9.5 ``defmacro``)."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

_PACKAGES_ROOT = Path(__file__).resolve().parents[2]
for _name in ("rlang", "evaluate"):
    _root = _PACKAGES_ROOT / _name
    if str(_root) not in sys.path:
        sys.path.insert(0, str(_root))

from rlang.as_label import Call  # noqa: E402
from rlang.as_string import Symbol  # noqa: E402
from rlang.eval_bare import eval_bare  # noqa: E402
from rlang.parse_expr import parse_expr  # noqa: E402

__all__ = ["defmacro"]

_DOTS = object()
_REQUIRED = object()


def _as_name(arg: Any) -> str:
    if isinstance(arg, Symbol):
        return arg._name
    if isinstance(arg, str):
        return arg
    return str(arg)


def _as_expr(value: Any) -> Any:
    if isinstance(value, (Call, Symbol)):
        return value
    if isinstance(value, str):
        return parse_expr(value)
    return value


def _substitute(expr: Any, mapping: dict[str, Any]) -> Any:
    if isinstance(expr, Symbol):
        replacement = mapping.get(expr._name)
        if replacement is not None:
            return replacement
        return expr
    if isinstance(expr, Call):
        return Call(*(_substitute(part, mapping) for part in expr._parts))
    if isinstance(expr, list):
        return [_substitute(item, mapping) for item in expr]
    return expr


def _deparse(expr: Any) -> str:
    if isinstance(expr, Symbol):
        return expr._name
    if isinstance(expr, Call):
        head = expr[1]
        if isinstance(head, Symbol) and head._name in {"{", "(", "["}:
            inner = ", ".join(_deparse(expr[index]) for index in range(2, len(expr) + 1))
            if head._name == "{":
                return "{\n    " + inner + "\n}"
            return head._name + inner + ("]" if head._name == "[" else ")")
        if len(expr._parts) == 3 and isinstance(head, Symbol):
            left = _deparse(expr[2])
            right = _deparse(expr[3])
            return f"{left} {head._name} {right}"
        parts = ", ".join(_deparse(expr[index]) for index in range(2, len(expr) + 1))
        return f"{_deparse(head)}({parts})"
    if isinstance(expr, str):
        return repr(expr)
    return str(expr)


def _caller_env(depth: int = 2) -> dict[str, Any]:
    frame = sys._getframe(depth)
    env = dict(frame.f_globals)
    env.update(frame.f_locals)
    return env


def _macro_source_line(formal_names: list[str]) -> str:
    return "macro(" + ", ".join(formal_names) + ")"


class _MacroFunction:
    __slots__ = ("_body", "_defaults", "_formal_names", "source")

    def __init__(
        self,
        body: Any,
        formal_names: list[str],
        defaults: dict[str, Any],
        source: list[str],
    ) -> None:
        self._body = body
        self._formal_names = formal_names
        self._defaults = defaults
        self.source = source

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        mapping: dict[str, Any] = {}
        names = list(self._formal_names)
        pos = 0
        kw = dict(kwargs)

        for name in names:
            if name == "...":
                tail = [_as_expr(value) for value in args[pos:]]
                tail.extend(_as_expr(value) for value in kw.values())
                kw.clear()
                if tail:
                    mapping["..."] = tail[0] if len(tail) == 1 else Call(Symbol("c"), *tail)
                break
            if pos < len(args):
                mapping[name] = _as_expr(args[pos])
                pos += 1
                continue
            if name in kw:
                mapping[name] = _as_expr(kw.pop(name))
                continue
            default = self._defaults.get(name, _REQUIRED)
            if default is _REQUIRED:
                raise RuntimeError(f"{name} not supplied")
            mapping[name] = default

        if kw:
            raise TypeError(f"unexpected keyword argument(s): {', '.join(kw)}")
        if pos < len(args) and "..." not in names:
            raise TypeError("too many positional arguments")

        tmp = _substitute(self._body, mapping)
        return eval_bare(tmp, _caller_env(2))


def defmacro(*macro_args: Any, expr: Any, **macro_formals: Any) -> _MacroFunction:
    """Build a macro that substitutes call arguments into ``expr`` then evaluates."""
    body = _as_expr(expr)

    formal_names: list[str] = []
    defaults: dict[str, Any] = {}

    for arg in macro_args:
        name = _as_name(arg)
        if name == "DOTS":
            name = "..."
            defaults[name] = _DOTS
        else:
            defaults[name] = _REQUIRED
        formal_names.append(name)

    for name, default in macro_formals.items():
        key = "..." if name == "DOTS" else name
        if key == "...":
            defaults[key] = _DOTS
        else:
            defaults[key] = default
        formal_names.append(key)

    source = [_macro_source_line(formal_names), _deparse(body)]
    return _MacroFunction(body, formal_names, defaults, source)
