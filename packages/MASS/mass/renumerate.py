"""Restore loglm-style formula names from ``.vn`` (MASS ``renumerate``)."""

from __future__ import annotations

from typing import Any

from Formula.formula import (
    Bin,
    Call,
    Num,
    RFormula,
    Sym,
    Unary,
    _PREC,
    as_r_formula,
)
from mass.errors import MassError


def renumerate(x: Any) -> RFormula:
    """Replace ``.vn`` names in a formula with the original dimension labels."""
    if isinstance(x, str):
        x = as_r_formula(x)
    if isinstance(x, RFormula) and "formula" in x.classes:
        return _renumerate_formula(x)
    raise MassError('no applicable method for "renumerate"')


def _renumerate_formula(formula: RFormula) -> RFormula:
    if len(formula) == 2:
        rhs = _renumerate_expr(formula[2])
        return RFormula(("~", rhs), classes=formula.classes, _unset=True)
    lhs = _renumerate_expr(formula[2])
    rhs = _renumerate_expr(formula[3])
    return RFormula(("~", lhs, rhs), classes=formula.classes, _unset=True)


def _renumerate_leaf(node: Sym | Num) -> Sym | Num:
    if not isinstance(node, Sym):
        return node
    name = node.name
    if len(name) > 2 and name[:2] == ".v":
        return Sym(name[2:])
    return node


def _renumerate_expr(node: Any) -> Any:
    if isinstance(node, (Sym, Num)):
        return _renumerate_leaf(node)
    if isinstance(node, Bin):
        left = _renumerate_expr(node.left)
        if node.op == "^":
            return Bin(node.op, left, node.right)
        right = _renumerate_expr(node.right)
        return Bin(node.op, left, right)
    if isinstance(node, Unary):
        return Unary(node.op, _renumerate_expr(node.arg))
    if isinstance(node, Call):
        args = list(node.args)
        if args:
            args[0] = _renumerate_expr(args[0])
        if len(args) >= 2 and node.name != "^":
            args[1] = _renumerate_expr(args[1])
        return Call(node.name, tuple(args))
    raise MassError(f"unsupported formula node: {type(node).__name__}")


def _sym_deparse(name: str) -> str:
    if not name:
        return name
    if name[0].isdigit() or not (name[0].isalpha() or name[0] == "."):
        return f"`{name}`"
    if name[0] == "." and (len(name) == 1 or not name[1].isalpha()):
        return f"`{name}`"
    return name


def _deparse_renumerated_expr(node, parent_prec=0, side="left") -> str:
    if isinstance(node, Sym):
        return _sym_deparse(node.name)
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
        args = ", ".join(_deparse_renumerated_expr(arg, 0, "left") for arg in node.args)
        return f"{node.name}({args})"
    if isinstance(node, Unary):
        arg = _deparse_renumerated_expr(node.arg, 7, "right")
        if isinstance(node.arg, Bin):
            return f"-({arg})"
        return f"-{arg}"
    if isinstance(node, Bin):
        prec = _PREC[node.op]
        left = _deparse_renumerated_expr(node.left, prec, "left")
        right = _deparse_renumerated_expr(node.right, prec, "right")
        if node.op == "/":
            return f"{left}/{right}"
        if node.op == "^":
            return f"{left}^{right}"
        text = f"{left} {node.op} {right}"
        if prec < parent_prec or (prec == parent_prec and side == "right"):
            return f"({text})"
        return text
    raise TypeError(f"cannot deparse {type(node).__name__}")


def _deparse_renumerated(value: RFormula) -> str:
    if len(value) > 2:
        return f"{_deparse_renumerated_expr(value[2])} ~ {_deparse_renumerated_expr(value[3])}"
    return f"~{_deparse_renumerated_expr(value[2])}"


def renumerate_deparse(x: Any) -> str:
    """Deparse a renumerated formula like R ``deparse(renumerate(x))``."""
    return _deparse_renumerated(renumerate(x))
