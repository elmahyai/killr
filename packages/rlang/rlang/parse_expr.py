"""Parse a single R expression from text (``parse_expr``)."""

from __future__ import annotations

import io
from typing import Any

from evaluate.parse import (
    Binary,
    Call as ParseCall,
    Literal,
    Name,
    Paren,
    Unary,
    _parse_character,
)

from rlang import RLangError, abort, is_character
from rlang.as_label import Call
from rlang.as_string import Symbol
from rlang.check_bool import _format_arg, _obj_type_friendly


def _paste_line(parts: list[str], *, trailing: bool = False) -> str:
    if trailing:
        return "".join(f"{item}\n" for item in parts)
    return "\n".join(parts)


def _node_to_rlang(node: Any) -> Any:
    if isinstance(node, Name):
        return Symbol(node.name)
    if isinstance(node, Literal):
        val = node.value
        if isinstance(val, int) and not isinstance(val, bool):
            if str(node.code).endswith("L"):
                return val
            return float(val)
        return val
    if isinstance(node, Unary):
        return Call(Symbol(node.op), _node_to_rlang(node.expr))
    if isinstance(node, Binary):
        return Call(Symbol(node.op), _node_to_rlang(node.left), _node_to_rlang(node.right))
    if isinstance(node, Paren):
        return _node_to_rlang(node.expr)
    if isinstance(node, ParseCall):
        parts = [_node_to_rlang(node.func)]
        for _name, arg in node.args:
            parts.append(_node_to_rlang(arg))
        return Call(*parts)
    raise RLangError(f"unsupported parsed node type {type(node).__name__}")


def _chr_parse(text: str) -> list[Any]:
    result = _parse_character([text], None, False)
    exprs: list[Any] = []
    for _src, nodes in result.rows:
        exprs.extend(_node_to_rlang(node) for node in nodes)
    return exprs


def _is_connection(x: object) -> bool:
    return isinstance(x, io.IOBase)


def _stop_input_type(x: object, what: str) -> None:
    abort(f"{_format_arg('x')} must be {what}, not {_obj_type_friendly(x)}.")


def _parse_exprs_connection(x: io.IOBase) -> list[Any]:
    must_close = False
    handle = x
    if getattr(x, "closed", False):
        name = getattr(x, "name", None)
        if name is None:
            raise RLangError("connection is closed")
        handle = open(name, encoding=getattr(x, "encoding", None) or "utf-8")
        must_close = True
    try:
        text = handle.read()
    finally:
        if must_close:
            handle.close()
    return _chr_parse(text)


def parse_expr(x: str | list[str] | io.IOBase) -> Any:
    """Parse text containing exactly one R expression."""
    if is_character(x):
        text = x if isinstance(x, str) else _paste_line(list(x))
        exprs = _chr_parse(text)
    elif _is_connection(x):
        exprs = _parse_exprs_connection(x)
    else:
        _stop_input_type(x, "a character vector or an R connection")

    n = len(exprs)
    if n != 1:
        abort(f"{_format_arg('x')} must contain exactly 1 expression, not {n}.")
    return exprs[0]
