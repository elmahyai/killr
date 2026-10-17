"""deparse1, str2lang, and str2expression for the expressions the package tests."""

from __future__ import annotations

from backports._values import BackportError

__all__ = [
    "Call",
    "Literal",
    "Name",
    "deparse1",
    "remove_source",
    "str2expression",
    "str2lang",
]


class Name:
    def __init__(self, value: str):
        self.value = value

    def __repr__(self) -> str:
        return f"Name({self.value!r})"


class Literal:
    def __init__(self, text: str):
        self.text = text

    def __repr__(self) -> str:
        return self.text


class Call:
    def __init__(self, head: str, args: list):
        self.head = head
        self.args = list(args)

    def __repr__(self) -> str:
        return deparse1(self)


def deparse1(expr, collapse=" ", width_cutoff=500, backtick=None):
    del width_cutoff
    if backtick is None:
        backtick = isinstance(expr, Call)
    text = _deparse(expr, backtick)
    if isinstance(text, list):
        return collapse.join(text)
    return text


def _deparse(expr, backtick) -> str:
    if isinstance(expr, Name):
        if backtick and not _syntactic(expr.value):
            return f"`{expr.value}`"
        return expr.value
    if isinstance(expr, Literal):
        return expr.text
    if isinstance(expr, Call):
        if expr.head == "[":
            left = _deparse(expr.args[0], True)
            inner = ", ".join(_deparse(arg, True) for arg in expr.args[1:])
            return f"{left}[{inner}]"
        if expr.head in ("<-", "+"):
            left = _deparse(expr.args[0], True)
            right = _deparse(expr.args[1], True)
            return f"{left} {expr.head} {right}"
        if expr.head == "expression":
            inner = ", ".join(_deparse(arg, True) for arg in expr.args)
            return f"expression({inner})"
        inner = ", ".join(_deparse(arg, True) for arg in expr.args)
        return f"{expr.head}({inner})"
    raise BackportError("cannot deparse this object")


def _syntactic(name: str) -> bool:
    if not name:
        return False
    first = name[0]
    if not (first.isalpha() or first == "."):
        return False
    return all(char.isalnum() or char in "._" for char in name)


def str2lang(s):
    if isinstance(s, (list, tuple)) or not isinstance(s, str):
        raise BackportError("length(s) == 1 is not TRUE")
    parsed = _parse_text(s)
    if len(parsed) != 1:
        raise BackportError("length(ex) == 1 is not TRUE")
    return parsed[0]


def str2expression(text):
    if isinstance(text, (list, tuple)):
        parsed = []
        for item in text:
            parsed.extend(_parse_text(item))
        return Call("expression", parsed)
    return Call("expression", _parse_text(text))


def remove_source(fn):
    if isinstance(fn, (Name, Call, Literal)):
        return fn
    if callable(fn):
        return fn
    raise BackportError(f"argument is not a function or language object:{_typeof(fn)}")


def _typeof(value) -> str:
    if isinstance(value, bool):
        return "logical"
    if isinstance(value, str):
        return "character"
    if isinstance(value, int):
        return "integer"
    if isinstance(value, float):
        return "double"
    if value is None:
        return "NULL"
    return type(value).__name__


def _parse_text(text: str):
    if not isinstance(text, str):
        raise BackportError("text must be a character string")
    pieces = [piece.strip() for piece in text.split(";") if piece.strip()]
    if not pieces:
        return []
    parsed = []
    for piece in pieces:
        node, index = _parse_assign(piece, 0)
        index = _skip(piece, index)
        if index != len(piece):
            raise BackportError(f"unexpected input at {piece[index:]!r}")
        parsed.append(node)
    return parsed


def _parse_assign(src, index):
    node, index = _parse_sum(src, index)
    index = _skip(src, index)
    if src.startswith("<-", index):
        right, index = _parse_assign(src, index + 2)
        return Call("<-", [node, right]), index
    return node, index


def _parse_sum(src, index):
    node, index = _parse_postfix(src, index)
    index = _skip(src, index)
    if index < len(src) and src[index] == "+":
        right, index = _parse_sum(src, index + 1)
        return Call("+", [node, right]), index
    return node, index


def _parse_postfix(src, index):
    node, index = _parse_primary(src, index)
    while True:
        index = _skip(src, index)
        if index < len(src) and src[index] == "[":
            inner, index = _parse_assign(src, index + 1)
            index = _skip(src, index)
            if index >= len(src) or src[index] != "]":
                raise BackportError("expected ']'")
            node = Call("[", [node, inner])
            index += 1
            continue
        if index < len(src) and src[index] == "(":
            if not isinstance(node, Name):
                raise BackportError("expected a name before '('")
            args, index = _parse_args(src, index + 1)
            node = Call(node.value, args)
            continue
        return node, index


def _parse_args(src, index):
    args = []
    index = _skip(src, index)
    if index < len(src) and src[index] == ")":
        return args, index + 1
    while True:
        node, index = _parse_assign(src, index)
        args.append(node)
        index = _skip(src, index)
        if index < len(src) and src[index] == ",":
            index += 1
            continue
        if index < len(src) and src[index] == ")":
            return args, index + 1
        raise BackportError("expected ')'")


def _parse_primary(src, index):
    index = _skip(src, index)
    if index >= len(src):
        raise BackportError("unexpected end of input")
    if src[index] == "`":
        end = src.find("`", index + 1)
        if end < 0:
            raise BackportError("unclosed backtick")
        return Name(src[index + 1 : end]), end + 1
    if src[index].isdigit() or (src[index] == "." and index + 1 < len(src) and src[index + 1].isdigit()):
        end = index + 1
        while end < len(src) and (src[end].isdigit() or src[end] == "."):
            end += 1
        return Literal(src[index:end]), end
    if src[index].isalpha() or src[index] in "._":
        end = index + 1
        while end < len(src) and (src[end].isalnum() or src[end] in "._"):
            end += 1
        return Name(src[index:end]), end
    raise BackportError(f"unexpected character {src[index]!r}")


def _skip(src, index):
    while index < len(src) and src[index] in " \t\r\n":
        index += 1
    return index
