"""Split a formula's right-hand side on a separator (nlme ``splitFormula``)."""

from __future__ import annotations

import re
from dataclasses import dataclass

_TOKEN = re.compile(
    r"\s*(?:(?P<num>\d+(?:\.\d*)?(?:[eE][-+]?\d+)?)"
    r"|(?P<name>[A-Za-z.][A-Za-z0-9._]*)"
    r"|(?P<op>%[^%]*%|[-+*/:^()~|,]))"
)

# R operator precedence, lowest first.  ``:`` binds tighter than ``*`` and ``/``,
# and unary minus sits between ``:`` and ``^``.
_BINARY_LEVELS: tuple[tuple[str, ...], ...] = (
    ("|",),
    ("+", "-"),
    ("*", "/"),
    ("%",),  # any %op%
    (":",),
)
_NO_SPACE_OPS = frozenset({"/", ":", "^"})


@dataclass(frozen=True, slots=True)
class _Node:
    kind: str  # "name", "num", "call", "paren", "unary", "bin"
    text: str = ""
    args: tuple["_Node", ...] = ()
    op: str = ""


def splitFormula(form: str, sep: str = "/") -> list[str]:
    """Split the right-hand side of ``form`` on ``sep`` into one-sided formulas.

    ``form`` is a formula string (``"y ~ a/b"``) or an expression (``"a/b/c"``).
    Each separator-joined piece becomes one one-sided formula string such as
    ``"~a"``.  Parenthesised groups are unwrapped first, as in R.
    """
    text = str(form).strip()
    if "~" in text:
        text = text.split("~", 1)[1].strip()
    if not text:
        return []
    tokens = _tokenize(text)
    parser = _Parser(tokens)
    tree = parser.parse_binary(0)
    if parser.pos != len(tokens):
        raise ValueError("invalid formula")
    return _split_node(tree, sep)


def _split_node(node: _Node, sep: str) -> list[str]:
    if node.kind == "bin" and node.op == sep:
        left, right = node.args
        return _split_node(left, sep) + _split_node(right, sep)
    if node.kind == "paren":
        return _split_node(node.args[0], sep)
    return ["~" + _deparse(node)]


def _tokenize(text: str) -> list[tuple[str, str]]:
    tokens: list[tuple[str, str]] = []
    pos = 0
    text = text.rstrip()
    while pos < len(text):
        match = _TOKEN.match(text, pos)
        if match is None or match.end() == pos:
            raise ValueError(f"unexpected character in formula at {text[pos:]!r}")
        pos = match.end()
        if match.group("num") is not None:
            tokens.append(("num", match.group("num")))
        elif match.group("name") is not None:
            tokens.append(("name", match.group("name")))
        else:
            tokens.append(("op", match.group("op")))
    return tokens


class _Parser:
    def __init__(self, tokens: list[tuple[str, str]]) -> None:
        self.tokens = tokens
        self.pos = 0

    def _peek(self) -> tuple[str, str] | None:
        return self.tokens[self.pos] if self.pos < len(self.tokens) else None

    def parse_binary(self, level: int) -> _Node:
        if level >= len(_BINARY_LEVELS):
            return self.parse_unary()
        ops = _BINARY_LEVELS[level]
        left = self.parse_binary(level + 1)
        while True:
            token = self._peek()
            if token is None or token[0] != "op" or not _is_op_at_level(token[1], ops):
                return left
            self.pos += 1
            right = self.parse_binary(level + 1)
            left = _Node("bin", op=token[1], args=(left, right))

    def parse_unary(self) -> _Node:
        token = self._peek()
        if token is not None and token[0] == "op" and token[1] in ("-", "+"):
            self.pos += 1
            return _Node("unary", op=token[1], args=(self.parse_unary(),))
        return self.parse_power()

    def parse_power(self) -> _Node:
        base = self.parse_primary()
        token = self._peek()
        if token is not None and token == ("op", "^"):
            self.pos += 1
            return _Node("bin", op="^", args=(base, self.parse_unary()))
        return base

    def parse_primary(self) -> _Node:
        token = self._peek()
        if token is None:
            raise ValueError("unexpected end of formula")
        kind, text = token
        if kind == "num":
            self.pos += 1
            return _Node("num", text=text)
        if kind == "name":
            self.pos += 1
            if self._peek() == ("op", "("):
                self.pos += 1
                args: list[_Node] = []
                if self._peek() != ("op", ")"):
                    while True:
                        args.append(self.parse_binary(0))
                        if self._peek() == ("op", ","):
                            self.pos += 1
                            continue
                        break
                if self._peek() != ("op", ")"):
                    raise ValueError("expected ')' in function call")
                self.pos += 1
                return _Node("call", text=text, args=tuple(args))
            return _Node("name", text=text)
        if token == ("op", "("):
            self.pos += 1
            inner = self.parse_binary(0)
            if self._peek() != ("op", ")"):
                raise ValueError("expected ')'")
            self.pos += 1
            return _Node("paren", args=(inner,))
        raise ValueError(f"unexpected token {text!r} in formula")


def _is_op_at_level(op: str, ops: tuple[str, ...]) -> bool:
    if "%" in ops:
        return op.startswith("%") and op.endswith("%") and len(op) >= 2
    return op in ops


def _deparse(node: _Node) -> str:
    """Deparse with R's spacing: ``a + b``, ``a * b``, but ``a/b``, ``a:b``, ``a^b``."""
    if node.kind in ("name", "num"):
        return node.text
    if node.kind == "call":
        return f"{node.text}({', '.join(_deparse(arg) for arg in node.args)})"
    if node.kind == "paren":
        return f"({_deparse(node.args[0])})"
    if node.kind == "unary":
        return f"{node.op}{_deparse(node.args[0])}"
    left, right = (_deparse(arg) for arg in node.args)
    if node.op in _NO_SPACE_OPS:
        return f"{left}{node.op}{right}"
    return f"{left} {node.op} {right}"


def proof_values(pieces: list[str]) -> list[float]:
    """Count, then (length, character-sum) for each piece, for R comparison."""
    out: list[float] = [float(len(pieces))]
    for piece in pieces:
        out.append(float(len(piece)))
        out.append(float(sum(map(ord, piece))))
    return out
