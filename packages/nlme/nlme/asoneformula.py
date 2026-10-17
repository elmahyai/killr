"""Combine formulas into one linear formula (nlme asOneFormula)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Formula:
    """One-sided linear formula, comparable to R's deparse(asOneFormula(...))."""

    terms: tuple[str, ...]

    def __str__(self) -> str:
        if not self.terms or self.terms == ("1",):
            return "~1"
        return "~" + " + ".join(self.terms)


def asOneFormula(*objects, omit=None):
    """Return a one-sided formula with all variables from ``objects``, minus ``omit``."""
    if omit is None:
        omit = (".", "pi")
    omit_set = set(omit)
    names = _unique(_all_vars_rec(objects))
    names = [name for name in names if name not in omit_set]
    if not names:
        return Formula(("1",))
    return Formula(tuple(names))


def _all_vars_rec(object):
    if isinstance(object, (list, tuple)):
        out = []
        for item in object:
            out.extend(_all_vars_rec(item))
        return out
    if isinstance(object, Formula):
        return list(object.terms) if object.terms != ("1",) else []
    return _all_vars(object)


def _all_vars(object):
    if isinstance(object, str):
        return _all_vars_formula(object.strip())
    if hasattr(object, "__formula__"):
        return _all_vars(str(object.__formula__()))
    raise TypeError(f"cannot extract variables from {type(object)!r}")


def _all_vars_formula(text):
    if not text:
        return []
    lhs, rhs, cond = _split_formula(text)
    names = []
    if lhs:
        names.extend(_all_vars_expr(lhs))
    if rhs:
        names.extend(_all_vars_expr(rhs))
    if cond:
        names.extend(_all_vars_expr(cond))
    return names


def _split_formula(text):
    lhs = ""
    rhs = text
    if "~" in text:
        lhs, rhs = text.split("~", 1)
        lhs = lhs.strip()
        rhs = rhs.strip()
    cond = ""
    if "|" in rhs:
        rhs, cond = rhs.split("|", 1)
        rhs = rhs.strip()
        cond = cond.strip()
    return lhs, rhs, cond


def _all_vars_expr(text):
    tokens = _tokenize(text)
    tree, _ = _parse_expr(tokens, 0)
    return _vars_from_node(tree)


def _unique(names):
    seen = set()
    out = []
    for name in names:
        if name not in seen:
            seen.add(name)
            out.append(name)
    return out


def _tokenize(text):
    tokens = []
    index = 0
    length = len(text)
    while index < length:
        char = text[index]
        if char.isspace():
            index += 1
            continue
        if char in "+-*^():~|":
            tokens.append(char)
            index += 1
            continue
        if char in "/":
            tokens.append(char)
            index += 1
            continue
        if char == ":":
            tokens.append(":")
            index += 1
            continue
        if char.isdigit() or (char == "." and index + 1 < length and text[index + 1].isdigit()):
            start = index
            index += 1
            while index < length and (text[index].isdigit() or text[index] == "."):
                index += 1
            tokens.append(("num", text[start:index]))
            continue
        if char.isalpha() or char == "." or char == "_":
            start = index
            index += 1
            while index < length and (text[index].isalnum() or text[index] in "._"):
                index += 1
            tokens.append(("name", text[start:index]))
            continue
        raise ValueError(f"unexpected character {char!r} in formula expression")
    return tokens


def _parse_expr(tokens, pos):
    return _parse_plus(tokens, pos)


def _parse_plus(tokens, pos):
    left, pos = _parse_minus(tokens, pos)
    while pos < len(tokens) and tokens[pos] == "+":
        pos += 1
        right, pos = _parse_minus(tokens, pos)
        left = ("+", left, right)
    return left, pos


def _parse_minus(tokens, pos):
    if pos < len(tokens) and tokens[pos] == "-":
        pos += 1
        right, pos = _parse_minus(tokens, pos)
        return ("u-", None, right), pos
    return _parse_colon(tokens, pos)


def _parse_colon(tokens, pos):
    left, pos = _parse_power(tokens, pos)
    while pos < len(tokens) and tokens[pos] == ":":
        pos += 1
        right, pos = _parse_power(tokens, pos)
        left = (":", left, right)
    return left, pos


def _parse_power(tokens, pos):
    left, pos = _parse_mul(tokens, pos)
    while pos < len(tokens) and tokens[pos] == "^":
        pos += 1
        right, pos = _parse_mul(tokens, pos)
        left = ("^", left, right)
    return left, pos


def _parse_mul(tokens, pos):
    left, pos = _parse_call(tokens, pos)
    while pos < len(tokens) and tokens[pos] in ("*", "/"):
        op = tokens[pos]
        pos += 1
        right, pos = _parse_call(tokens, pos)
        left = (op, left, right)
    return left, pos


def _parse_call(tokens, pos):
    if pos < len(tokens) and isinstance(tokens[pos], tuple) and tokens[pos][0] == "name":
        name = tokens[pos][1]
        pos += 1
        if pos < len(tokens) and tokens[pos] == "(":
            pos += 1
            args = []
            if pos < len(tokens) and tokens[pos] != ")":
                while True:
                    arg, pos = _parse_expr(tokens, pos)
                    args.append(arg)
                    if pos < len(tokens) and tokens[pos] == ",":
                        pos += 1
                        continue
                    break
            if pos >= len(tokens) or tokens[pos] != ")":
                raise ValueError("expected ')' in function call")
            pos += 1
            return ("call", name, tuple(args)), pos
        return ("name", name, None), pos
    if pos < len(tokens) and tokens[pos] == "(":
        pos += 1
        inner, pos = _parse_expr(tokens, pos)
        if pos >= len(tokens) or tokens[pos] != ")":
            raise ValueError("expected ')'")
        pos += 1
        return inner, pos
    if pos < len(tokens) and isinstance(tokens[pos], tuple) and tokens[pos][0] == "num":
        pos += 1
        return ("num", tokens[pos - 1][1], None), pos
    raise ValueError("unexpected token in expression")


def _vars_from_node(node):
    if node is None:
        return []
    kind = node[0]
    if kind == "name":
        return [node[1]]
    if kind == "num":
        return []
    if kind == "call":
        out = []
        for arg in node[2]:
            out.extend(_vars_from_node(arg))
        return out
    if kind in ("+", "-", "*", "/", "^", ":", "u-"):
        left = _vars_from_node(node[1])
        right = _vars_from_node(node[2])
        return left + right
    return []
