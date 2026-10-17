"""Create a default name for an R object (``as_label``)."""

from __future__ import annotations

import re
from typing import Any, Sequence

from rlang.as_string import Symbol, as_string
from rlang.na_or import Character, Complex, Double, Integer, Logical, _Vector

RESERVED_WORDS = frozenset(
    {
        "NULL",
        "NA",
        "TRUE",
        "FALSE",
        "Inf",
        "NaN",
        "NA_integer_",
        "NA_real_",
        "NA_character_",
        "NA_complex_",
        "function",
        "while",
        "repeat",
        "for",
        "if",
        "in",
        "else",
        "next",
        "break",
    }
)

function_sym = Symbol("function")
brace_sym = Symbol("{")
dot_data_sym = Symbol(".data")


class MissingArg:
    """R's missing argument sentinel."""


MISSING = MissingArg()


class Call:
    """R language object (LANGSXP) as a flat call vector."""

    __slots__ = ("_parts",)

    def __init__(self, *parts: Any):
        self._parts = parts

    def __getitem__(self, index: int) -> Any:
        return self._parts[index - 1]

    def __setitem__(self, index: int, value: Any) -> None:
        parts = list(self._parts)
        parts[index - 1] = value
        self._parts = tuple(parts)

    def __len__(self) -> int:
        return len(self._parts)


class Quosure:
    """Minimal quosure wrapper for ``quo_squash``."""

    __slots__ = ("expr",)

    def __init__(self, expr: Any):
        self.expr = expr


def _is_quosure(x: Any) -> bool:
    return isinstance(x, Quosure)


def _maybe_missing(x: Any) -> Any:
    return x


def _is_missing(x: Any) -> bool:
    return x is MISSING


def _typeof(x: Any) -> str:
    if x is None:
        return "NULL"
    if isinstance(x, Symbol):
        return "symbol"
    if isinstance(x, Call):
        return "language"
    if isinstance(x, MissingArg):
        return "symbol"
    if isinstance(x, _Vector):
        if isinstance(x, Logical):
            return "logical"
        if isinstance(x, Integer):
            return "integer"
        if isinstance(x, Double):
            return "double"
        if isinstance(x, Character):
            return "character"
        if isinstance(x, Complex):
            return "complex"
    if isinstance(x, bool):
        return "logical"
    if isinstance(x, int) and not isinstance(x, bool):
        return "integer"
    if isinstance(x, float):
        return "double"
    if isinstance(x, str):
        return "character"
    if isinstance(x, complex):
        return "complex"
    if callable(x) and not isinstance(x, type):
        return "closure"
    if isinstance(x, dict):
        return "environment"
    return "unknown"


def _vector_len(x: Any) -> int:
    if isinstance(x, _Vector):
        return len(x.values)
    if isinstance(x, (str, bytes)):
        return len(x)
    if isinstance(x, (list, tuple)):
        return len(x)
    return 1


def _is_bare_atomic(x: Any, n: int | None = None) -> bool:
    if isinstance(x, (Call, Quosure, MissingArg)):
        return False
    if isinstance(x, _Vector):
        ok = True
    elif isinstance(x, (bool, int, float, str, complex)):
        ok = True
    else:
        return False
    if n is not None and _vector_len(x) != n:
        return False
    return ok


def _rlang_type_sum(x: Any) -> str:
    if isinstance(x, _Vector):
        if isinstance(x, Logical):
            return "lgl"
        if isinstance(x, Integer):
            return "int"
        if isinstance(x, Double):
            return "dbl"
        if isinstance(x, Character):
            return "chr"
        if isinstance(x, Complex):
            return "cpl"
    if isinstance(x, bool):
        return "lgl"
    if isinstance(x, int) and not isinstance(x, bool):
        return "int"
    if isinstance(x, float):
        return "dbl"
    if isinstance(x, str):
        return "chr"
    if isinstance(x, complex):
        return "cpl"
    if callable(x) and not isinstance(x, type):
        return "fn"
    if isinstance(x, dict):
        return "env"
    if isinstance(x, Symbol):
        return "missing" if _is_missing(x) else "sym"
    return type(x).__name__


def _needs_backticks(text: str) -> bool:
    if not text:
        return False
    if text in RESERVED_WORDS:
        return True
    start = text[0]
    if not re.match(r"[[:alpha:].]", start):
        return True
    if len(text) == 1:
        return False
    remaining = text[1:]
    if start == "." and remaining and remaining[0].isdigit():
        return True
    return bool(re.search(r"[^[:alnum:]_.]", remaining))


def _sym_text(sym: Symbol) -> str:
    text = as_string(sym)
    if _needs_backticks(text):
        return f"`{text}`"
    return text


def _quote_string(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def _deparse_lines(expr: Any, width: int = 60, *, backtick: bool = False) -> list[str]:
    if isinstance(expr, Symbol):
        return [_sym_text(expr) if backtick else as_string(expr)]
    if isinstance(expr, Call):
        return [_deparse_call(expr, width, backtick=backtick)]
    if expr is None:
        return ["NULL"]
    if expr is MISSING:
        return [""]
    if isinstance(expr, bool):
        return ["TRUE" if expr else "FALSE"]
    if isinstance(expr, int) and not isinstance(expr, bool):
        return [f"{expr}L"]
    if isinstance(expr, float):
        return [repr(expr)]
    if isinstance(expr, str):
        return [_quote_string(expr)]
    if isinstance(expr, complex):
        return [repr(expr)]
    return [str(expr)]


def _call_head_name(head: Any) -> str | None:
    if isinstance(head, Symbol):
        return head._name
    if isinstance(head, str):
        return head
    return None


def _is_call(x: Any, name: str | Sequence[str] | None = None, n: int | None = None) -> bool:
    if not isinstance(x, Call):
        return False
    if name is None:
        return True
    names = (name,) if isinstance(name, str) else tuple(name)
    head = _call_head_name(x[1])
    if head not in names:
        return False
    if n is not None and len(x) != n + 1:
        return False
    return True


def _deparse_call(expr: Call, width: int, *, backtick: bool) -> str:
    head = expr[1]
    head_name = _call_head_name(head)
    if head_name in ("::", "$", "@", "[[", ":", "+", "-", "*", "/", "^", ">", "<", ">=", "<=", "==", "!=", "&", "|"):
        if len(expr) == 3:
            left = _deparse_lines(expr[2], width, backtick=backtick)[0]
            right = _deparse_lines(expr[3], width, backtick=backtick)[0]
            if head_name in ("::", "$", "@", ":"):
                return f"{left}{head_name}{right}"
            if head_name in ("[[",):
                return f"{left}[[{right}]]"
            return f"{left} {head_name} {right}"
    if head_name == "function" and len(expr) >= 3:
        return _deparse_call(expr, width, backtick=backtick)
    args = []
    for index in range(2, len(expr) + 1):
        args.append(_deparse_lines(expr[index], width, backtick=backtick)[0])
    head_text = _deparse_lines(head, width, backtick=backtick)[0]
    return f"{head_text}({', '.join(args)})"


def _deparse_one(expr: Any) -> str:
    lines = _deparse_lines(expr, 60, backtick=False)
    if len(lines) > 1:
        if _is_call(expr, function_sym):
            expr[3] = Symbol("...")
            lines = _deparse_lines(expr, 60, backtick=False)
        elif _is_call(expr, brace_sym):
            return "{ ... }"
        elif _is_call(expr):
            lines = _deparse_lines(Call(expr[1], Symbol("...")), 60, backtick=False)
        return "\n".join(lines)
    return lines[0]


def _expr_text(expr: Any, width: int = 60) -> str:
    if isinstance(expr, Symbol):
        return _sym_text(expr)
    lines = _deparse_lines(expr, width, backtick=True)
    return "\n".join(lines)


def _is_data_pronoun(x: Any) -> bool:
    return _is_call(x, ("[[", "$"), n=2) and x[2] == dot_data_sym


def _data_pronoun_name(x: Call) -> str | None:
    if _call_head_name(x[1]) == "$":
        arg = x[3]
        if isinstance(arg, Symbol):
            return as_string(arg)
        return None
    return None


def _use_as_label_infix() -> bool:
    return True


def _infix_overflows(_x: Call) -> bool:
    return False


def _as_label_infix(x: Call) -> str:
    return _deparse_one(x)


def _quo_squash_do(x: Any) -> Any:
    while _is_quosure(_maybe_missing(x)):
        x = x.expr
    return x


def _node_squash_call(x: Call) -> None:
    for index in range(1, len(x) + 1):
        part = x[index]
        if isinstance(part, Call):
            _node_squash_call(part)
        elif _is_quosure(part):
            x[index] = _quo_squash_do(part)
        elif isinstance(part, Quosure):
            x[index] = _quo_squash_impl(part.expr)


def _quo_squash_impl(x: Any) -> Any:
    if isinstance(x, Call):
        if _is_quosure(x):
            x = _quo_squash_do(x)
        else:
            _node_squash_call(x)
    return _maybe_missing(x)


def _quo_squash(quo: Any) -> Any:
    if _is_quosure(quo):
        quo = quo.expr
    if _is_missing(quo):
        return MISSING
    return _quo_squash_impl(quo)


def as_label(x: Any) -> str:
    x = _quo_squash(x)

    if _is_missing(x):
        return "<empty>"

    kind = _typeof(x)
    if kind == "NULL":
        return "NULL"
    if kind == "symbol":
        return as_string(x)
    if kind == "language":
        if _is_data_pronoun(x):
            name = _data_pronoun_name(x)
            return name if name is not None else "<unknown>"
        if _use_as_label_infix() and _infix_overflows(x):
            return _as_label_infix(x)
        name = _deparse_one(x)
        name = re.sub(r"\n.*$", "...", name)
        return name
    if _is_bare_atomic(x, n=1):
        name = _expr_text(x)
        name = re.sub(r"\n.*$", "...", name)
        return name
    return f"<{_rlang_type_sum(x)}>"
