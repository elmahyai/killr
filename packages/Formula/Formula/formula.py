"""Construct a Formula object from a formula.

From Formula 1.2-6 ``R/Formula.R``. ``split_formula`` lives in the same
file and is inlined here because ``Formula()`` calls it.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from Formula.is_formula import FormulaError

_TOKEN = re.compile(
    r"\s+"
    r"|(?:[0-9]+\.[0-9]*|\.[0-9]+|[0-9]+)(?:[eE][+-]?[0-9]+)?"
    r"|[A-Za-z.][A-Za-z0-9._]*"
    r"|~|\||\+|\-|\*|\/|:|\^|\(|\)|,"
)

_PREC = {"|": 2, "+": 3, "-": 3, "*": 4, "/": 4, ":": 5, "^": 6}


@dataclass(frozen=True, slots=True)
class Sym:
    name: str


@dataclass(frozen=True, slots=True)
class Num:
    value: int | float


@dataclass(frozen=True, slots=True)
class Call:
    name: str
    args: tuple


@dataclass(frozen=True, slots=True)
class Unary:
    op: str
    arg: object


@dataclass(frozen=True, slots=True)
class Bin:
    op: str
    left: object
    right: object


class RFormula:
    """An R ``formula`` or ``Formula`` object."""

    __slots__ = ("elements", "classes", "lhs", "rhs")

    def __init__(self, elements, classes=("formula",), lhs=None, rhs=None, _unset=False):
        self.elements = tuple(elements)
        self.classes = tuple(classes)
        if _unset:
            self.lhs = None
            self.rhs = None
        else:
            self.lhs = None if lhs is None else tuple(lhs)
            self.rhs = None if rhs is None else tuple(rhs)

    def __len__(self) -> int:
        return len(self.elements)

    def __getitem__(self, index: int):
        return self.elements[index - 1]


def Formula(object):  # noqa: N802 — R name
    """Return ``object`` when it is already Formula; else split a formula."""
    if _inherits(object, "Formula"):
        return object
    if not _inherits(object, "formula"):
        raise FormulaError('inherits(object, "formula") is not TRUE')
    split = _split_formula(object)
    return RFormula(
        object.elements,
        classes=("Formula", "formula"),
        lhs=split["lhs"],
        rhs=split["rhs"],
    )


def as_r_formula(text: str) -> RFormula:
    """Parse a formula string into a plain R ``formula`` object."""
    return _Parser(text).formula()


def formula_length(value: RFormula) -> tuple[int, int]:
    """``length.Formula``: lhs and rhs part counts."""
    lhs = value.lhs
    rhs = value.rhs
    lhs_len = 0 if lhs is None else len(lhs)
    rhs_len = 0 if rhs is None else len(rhs)
    return lhs_len, rhs_len


def deparse_formula(value: RFormula) -> str:
    if len(value) > 2:
        return f"{_deparse_expr(value[2])} ~ {_deparse_expr(value[3])}"
    return f"~{_deparse_expr(value[2])}"


def deparse_part(node) -> str:
    return _deparse_expr(node)


def fingerprint(value: RFormula) -> str:
    cls = ",".join(value.classes)
    flen = len(value)
    body = deparse_formula(value) if flen >= 2 else ""
    lhs = value.lhs
    rhs = value.rhs
    lhs_len = -1 if lhs is None else len(lhs)
    rhs_len = -1 if rhs is None else len(rhs)
    lhs_parts = () if lhs is None else tuple(deparse_part(part) for part in lhs)
    rhs_parts = () if rhs is None else tuple(deparse_part(part) for part in rhs)
    ll = formula_length(value) if "Formula" in value.classes else (-1, -1)
    return "|".join(
        [
            cls,
            str(flen),
            body,
            str(lhs_len),
            str(rhs_len),
            ";".join(lhs_parts),
            ";".join(rhs_parts),
            f"{ll[0]},{ll[1]}",
        ]
    )


def _inherits(value, name: str) -> bool:
    return isinstance(value, RFormula) and name in value.classes


def _split_formula(formula: RFormula) -> dict:
    if len(formula) > 2:
        rhs = formula[3]
        lhs = formula[2]
    else:
        rhs = formula[2]
        lhs = None
    return {"lhs": _extract_parts(lhs), "rhs": _extract_parts(rhs)}


def _extract_parts(node, sep="|"):
    if node is None:
        return None
    parts: list = []
    while isinstance(node, Bin) and node.op == sep:
        parts.insert(0, node.right)
        node = node.left
    return [node, *parts]


def _deparse_expr(node, parent_prec=0, side="left") -> str:
    if isinstance(node, Sym):
        return node.name
    if isinstance(node, Num):
        value = node.value
        if isinstance(value, float):
            if value.is_integer() and abs(value) < 1e15:
                return str(int(value))
            text = format(value, ".15g")
            if "e" in text or "." in text:
                return text
            return f"{text}.0" if "." not in text else text
        return str(value)
    if isinstance(node, Call):
        args = ", ".join(_deparse_expr(arg, 0, "left") for arg in node.args)
        return f"{node.name}({args})"
    if isinstance(node, Unary):
        arg = _deparse_expr(node.arg, 7, "right")
        if isinstance(node.arg, Bin):
            return f"-({arg})"
        return f"-{arg}"
    if isinstance(node, Bin):
        prec = _PREC[node.op]
        left = _deparse_expr(node.left, prec, "left")
        right = _deparse_expr(node.right, prec, "right")
        if node.op == "/":
            return f"{left}/{right}"
        if node.op == "^":
            return f"{left}^{right}"
        text = f"{left} {node.op} {right}"
        if prec < parent_prec or (prec == parent_prec and side == "right"):
            return f"({text})"
        return text
    raise TypeError(f"cannot deparse {type(node).__name__}")


class _Parser:
    def __init__(self, text: str):
        self.tokens = [token for token in _TOKEN.findall(text) if not token.isspace()]
        self.index = 0

    def peek(self):
        if self.index >= len(self.tokens):
            return None
        return self.tokens[self.index]

    def pop(self):
        token = self.peek()
        self.index += 1
        return token

    def formula(self) -> RFormula:
        if self.peek() == "~":
            self.pop()
            rhs = self._pipe()
            return RFormula(("~", rhs), _unset=True)
        left = self._pipe()
        if self.peek() != "~":
            raise ValueError("expected a formula")
        self.pop()
        rhs = self._pipe()
        return RFormula(("~", left, rhs), _unset=True)

    def _pipe(self):
        node = self._add()
        while self.peek() == "|":
            self.pop()
            node = Bin("|", node, self._add())
        return node

    def _add(self):
        node = self._mul()
        while self.peek() in {"+", "-"}:
            op = self.pop()
            node = Bin(op, node, self._mul())
        return node

    def _mul(self):
        node = self._colon()
        while self.peek() in {"*", "/"}:
            op = self.pop()
            node = Bin(op, node, self._colon())
        return node

    def _colon(self):
        node = self._pow()
        while self.peek() == ":":
            self.pop()
            node = Bin(":", node, self._pow())
        return node

    def _pow(self):
        node = self._unary()
        if self.peek() == "^":
            self.pop()
            node = Bin("^", node, self._pow())
        return node

    def _unary(self):
        if self.peek() == "-":
            nxt = self.tokens[self.index + 1] if self.index + 1 < len(self.tokens) else None
            if nxt is not None:
                self.pop()
                return Unary("-", self._unary())
        return self._primary()

    def _primary(self):
        token = self.pop()
        if token is None:
            raise ValueError("unexpected end of formula")
        if token == "(":
            node = self._pipe()
            if self.pop() != ")":
                raise ValueError("expected ')'")
            return node
        if _is_number(token):
            return Num(_number(token))
        if _is_name(token):
            if self.peek() == "(":
                self.pop()
                args = []
                if self.peek() != ")":
                    args.append(self._pipe())
                    while self.peek() == ",":
                        self.pop()
                        args.append(self._pipe())
                if self.pop() != ")":
                    raise ValueError("expected ')'")
                return Call(token, tuple(args))
            return Sym(token)
        raise ValueError(f"unexpected token {token!r}")


def _is_number(token: str) -> bool:
    return token[0].isdigit() or (token[0] == "." and len(token) > 1 and token[1].isdigit())


def _is_name(token: str) -> bool:
    return token[:1].isalpha() or token[:1] == "."


def _number(token: str) -> int | float:
    if any(mark in token for mark in ".eE"):
        return float(token)
    return int(token)
