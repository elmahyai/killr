"""Coerce objects to Formula.

From Formula 1.2-6 ``R/Formula.R``. ``paste_formula`` is inlined here because
``as.Formula.formula`` calls it.
"""

from __future__ import annotations

from Formula.formula import (
    Bin,
    Formula,
    Num,
    RFormula,
    as_r_formula,
    _inherits,
    _split_formula,
)
from Formula.is_formula import FormulaError


def as_Formula(*args, **kwargs):  # noqa: N802 — R name
    """Coerce ``x`` to ``Formula``, optionally merging several formulas."""
    x, extras, env, env_given = _match_x(args, kwargs)
    if _inherits(x, "Formula"):
        return x
    if _inherits(x, "formula"):
        return _as_formula_formula(x, extras, env, env_given)
    return _as_formula_default(x, env)


def _as_formula_default(x, env):
    del env  # R attaches ``env``; ``RFormula`` carries no environment.
    return Formula(_as_formula(x))


def _as_formula_formula(x, extras, env, env_given):
    del env, env_given
    formulas = [x, *extras]
    converted = [_as_formula(item) for item in formulas]
    splits = [_split_formula(item) for item in converted]
    lhs = _concat_lists(part["lhs"] for part in splits)
    rhs = _concat_lists(part["rhs"] for part in splits)
    combined = _paste_formula(lhs, rhs)
    return Formula(combined)


def _as_formula(value) -> RFormula:
    if isinstance(value, str):
        return as_r_formula(value)
    if isinstance(value, RFormula) and _inherits(value, "formula"):
        if _inherits(value, "Formula"):
            return RFormula(value.elements, classes=("formula",), _unset=True)
        return value
    raise FormulaError("invalid formula")


def _concat_lists(parts):
    out = []
    for part in parts:
        if part is None:
            continue
        out.extend(part)
    return out


def _paste_formula(lhs, rhs, lsep="|", rsep="|"):
    lhs_list = list(lhs)
    rhs_list = list(rhs)
    lval = _join_parts(lhs_list, lsep)
    if rhs_list:
        rval = rhs_list[0]
        for index in range(1, len(rhs_list)):
            sep = rsep[index - 1] if isinstance(rsep, (list, tuple)) else rsep
            rval = _c_formula(rval, rhs_list[index], sep)
    else:
        rval = Num(0)
    return _c_formula(lval, rval, "~")


def _join_parts(parts, sep):
    if not parts:
        return None
    node = parts[0]
    for index in range(1, len(parts)):
        ch = sep[index - 1] if isinstance(sep, (list, tuple)) else sep
        node = _c_formula(node, parts[index], ch)
    return node


def _c_formula(f1, f2, sep):
    if sep == "~":
        if f1 is None:
            return RFormula(("~", f2), _unset=True)
        return RFormula(("~", f1, f2), _unset=True)
    return Bin(sep, f1, f2)


def _match_x(args, kwargs):
    supplied = [(None, value) for value in args]
    supplied.extend(kwargs.items())
    env = None
    env_given = False
    env_indexes = [
        index for index, (name, _) in enumerate(supplied) if name == "env"
    ]
    if len(env_indexes) > 1:
        raise FormulaError('formal argument "env" matched by multiple actual arguments')
    if env_indexes:
        env_given = True
        env = supplied[env_indexes[0]][1]
        supplied = [pair for index, pair in enumerate(supplied) if index not in env_indexes]

    exact = [index for index, (name, _) in enumerate(supplied) if name == "x"]
    if len(exact) > 1:
        raise FormulaError('formal argument "x" matched by multiple actual arguments')
    partials = [
        index
        for index, (name, _) in enumerate(supplied)
        if name is not None and name != "x" and _is_prefix(name, "x")
    ]
    matched = exact[0] if exact else None
    if matched is None:
        if len(partials) > 1:
            raise FormulaError('formal argument "x" matched by multiple actual arguments')
        if len(partials) == 1:
            matched = partials[0]
        else:
            for index, (name, _) in enumerate(supplied):
                if name is None:
                    matched = index
                    break
    if matched is None:
        raise FormulaError('argument "x" is missing, with no default')
    x = supplied[matched][1]
    extras = [value for index, (_, value) in enumerate(supplied) if index != matched]
    return x, extras, env, env_given


def _is_prefix(name: str, formal: str) -> bool:
    return bool(name) and formal.startswith(name)
