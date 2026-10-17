"""Transform loglm-style formulas for ``terms`` (MASS ``denumerate``)."""

from __future__ import annotations

from typing import Any

from Formula.formula import (
    Bin,
    Call,
    Num,
    RFormula,
    Sym,
    Unary,
    as_r_formula,
    deparse_formula,
)
from mass.errors import MassError


def denumerate(x: Any) -> RFormula:
    """Replace dimension numbers in a formula with ``.vn`` names."""
    if isinstance(x, str):
        x = as_r_formula(x)
    if isinstance(x, RFormula) and "formula" in x.classes:
        return _denumerate_formula(x)
    raise MassError('no applicable method for "denumerate"')


def _denumerate_formula(formula: RFormula) -> RFormula:
    if len(formula) == 2:
        rhs = _denumerate_expr(formula[2])
        return RFormula(("~", rhs), classes=formula.classes, _unset=True)
    lhs = _denumerate_expr(formula[2])
    rhs = _denumerate_expr(formula[3])
    return RFormula(("~", lhs, rhs), classes=formula.classes, _unset=True)


def _denumerate_leaf(node: Sym | Num) -> Sym:
    if isinstance(node, Num):
        return Sym(f".v{node.value}")
    name = node.name
    if name and name[0] in "123456789":
        return Sym(f".v{name}")
    return node


def _denumerate_expr(node: Any) -> Any:
    if isinstance(node, (Sym, Num)):
        return _denumerate_leaf(node)
    if isinstance(node, Bin):
        left = _denumerate_expr(node.left)
        if node.op == "^":
            return Bin(node.op, left, node.right)
        right = _denumerate_expr(node.right)
        return Bin(node.op, left, right)
    if isinstance(node, Unary):
        return Unary(node.op, _denumerate_expr(node.arg))
    if isinstance(node, Call):
        args = list(node.args)
        if args:
            args[0] = _denumerate_expr(args[0])
        if len(args) >= 2 and node.name != "^":
            args[1] = _denumerate_expr(args[1])
        return Call(node.name, tuple(args))
    raise MassError(f"unsupported formula node: {type(node).__name__}")


def denumerate_deparse(x: Any) -> str:
    """Deparse a denumerated formula like R ``deparse(denumerate(x))``."""
    return deparse_formula(denumerate(x))
