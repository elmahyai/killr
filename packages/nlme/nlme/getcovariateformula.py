"""Extract the covariate side of a model formula (nlme getCovariateFormula)."""

from __future__ import annotations

from dataclasses import dataclass

from nlme.asoneformula import Formula, _tokenize


@dataclass(frozen=True, slots=True)
class CovariateFormula:
    """One-sided formula for the primary covariates."""

    text: str

    def __str__(self) -> str:
        return self.text


def getCovariateFormula(object) -> CovariateFormula:
    """Return the covariate expression from ``formula(object)`` without ``|`` groups."""
    text = _formula_text(object)
    if text is None:
        raise ValueError("formula(object) must return a formula")
    _, rhs = text.split("~", 1)
    rhs = rhs.strip()
    tokens = _tokenize(rhs)
    tree, pos = _parse_bar(tokens, 0)
    if pos != len(tokens):
        raise ValueError("invalid formula")
    if tree[0] == "|":
        tree = tree[1]
    return CovariateFormula(_one_sided(tree))


def _formula_text(object) -> str | None:
    if isinstance(object, CovariateFormula):
        return object.text
    if isinstance(object, Formula):
        return str(object)
    if hasattr(object, "formula"):
        value = object.formula
        if isinstance(value, str) and "~" in value:
            return value.strip()
    if isinstance(object, str):
        stripped = object.strip()
        if "~" in stripped:
            return stripped
    return None


def _parse_bar(tokens, pos):
    left, pos = _parse_plus(tokens, pos)
    if pos < len(tokens) and tokens[pos] == "|":
        pos += 1
        right, pos = _parse_bar(tokens, pos)
        return ("|", left, right), pos
    return left, pos


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
                    arg, pos = _parse_plus(tokens, pos)
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
        inner, pos = _parse_bar(tokens, pos)
        if pos >= len(tokens) or tokens[pos] != ")":
            raise ValueError("expected ')'")
        pos += 1
        return ("paren", inner, None), pos
    if pos < len(tokens) and isinstance(tokens[pos], tuple) and tokens[pos][0] == "num":
        pos += 1
        return ("num", tokens[pos - 1][1], None), pos
    raise ValueError("unexpected token in expression")


def _one_sided(node) -> str:
    if node[0] == "name":
        return f"~{node[1]}"
    if node[0] == "paren":
        return f"~({_deparse(node[1])})"
    if node[0] == "|":
        return f"~({_deparse(node)})"
    return f"~{_deparse(node)}"


def _deparse(node) -> str:
    if node is None:
        return ""
    kind = node[0]
    if kind == "name":
        return node[1]
    if kind == "num":
        return node[1]
    if kind == "call":
        args = ", ".join(_deparse(arg) for arg in node[2])
        return f"{node[1]}({args})"
    if kind == "u-":
        return f"-{_deparse(node[2])}"
    if kind == "paren":
        return f"({_deparse(node[1])})"
    if kind == "|":
        return f"{_deparse(node[1])} | {_deparse(node[2])}"
    if kind in ("+", "-", "*", "/", "^", ":"):
        left = _deparse(node[1])
        right = _deparse(node[2])
        return f"{left} {kind} {right}"
    raise ValueError("invalid formula")
