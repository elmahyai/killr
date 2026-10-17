"""checkmate's one-letter rules, qtest / qassert / qtestr / qassertr."""

from __future__ import annotations

import math
import textwrap

from .rtypes import (
    NA,
    CheckError,
    Vec,
    caller_arg,
    find_missing,
    find_missing_frame,
    fmt_g,
    guess_type,
    is_class_array,
    is_class_atomic,
    is_class_atomic_vector,
    is_class_complex,
    is_class_double,
    is_class_environment,
    is_class_factor,
    is_class_frame,
    is_class_integer,
    is_class_list,
    is_class_logical,
    is_class_matrix,
    is_class_numeric,
    is_class_posixct,
    is_class_string,
    is_na_scalar,
    is_null,
    message,
    nchar_bytes,
    ncols,
    nrows,
    wrap,
    xlength,
)
from . import checks as C

CLASS_NAMES = {
    "b": "logical",
    "i": "integer",
    "x": "integerish",
    "n": "numeric",
    "r": "double",
    "s": "string",
    "f": "factor",
    "l": "list",
    "c": "complex",
    "a": "atomic",
    "v": "atomic vector",
    "m": "matrix",
    "d": "data frame",
    "p": "POSIXct",
    "e": "environment",
    "0": "NULL",
}

PREDS = {
    "b": is_class_logical,
    "i": is_class_integer,
    "x": lambda value: C._integerish_ok(value, C.DEFAULT_TOL, True),
    "n": is_class_numeric,
    "r": is_class_double,
    "s": is_class_string,
    "f": is_class_factor,
    "l": is_class_list,
    "c": is_class_complex,
    "a": is_class_atomic,
    "v": is_class_atomic_vector,
    "m": is_class_matrix,
    "d": is_class_frame,
    "p": is_class_posixct,
    "e": is_class_environment,
    "0": is_null,
    "*": lambda value: True,
}

CMP = {"<": "lt", "<=": "le", "==": "eq", ">=": "ge", ">": "gt", "!=": "ne"}


def _missing_pos(obj, letter: str) -> int:
    if letter == "b":
        return find_missing(obj) if is_class_logical(obj) else 0
    if letter == "i" or letter == "f":
        return find_missing(obj) if isinstance(obj, Vec) and obj.mode == "integer" else 0
    if letter == "x":
        if not isinstance(obj, Vec):
            return 0
        if obj.mode in {"logical", "integer", "double"}:
            return find_missing(obj)
        raise CheckError("Error in find_missing_integerish: x must be logical or numeric")
    if letter in {"n", "p"}:
        if isinstance(obj, Vec) and obj.mode in {"integer", "double"}:
            return find_missing(obj)
        return 0
    if letter == "r":
        return find_missing(obj) if is_class_double(obj) else 0
    if letter == "s":
        return find_missing(obj) if is_class_string(obj) else 0
    if letter == "l":
        return find_missing(obj) if is_class_list(obj) else 0
    if letter == "c":
        return find_missing(obj) if is_class_complex(obj) else 0
    if letter in {"a", "v", "m"}:
        return find_missing(obj)
    if letter == "d":
        return find_missing_frame(obj) if is_class_frame(obj) else 0
    return 0


def _parse(rule: str) -> dict:
    if rule == "":
        raise CheckError("Empty rule")
    if rule[0] not in PREDS and rule[0].lower() not in PREDS:
        raise CheckError(f"Unknown class identifier '{rule[0]}'")
    letter = rule[0]
    key = letter.lower() if letter != "0" and letter != "*" else letter
    if key not in PREDS:
        raise CheckError(f"Unknown class identifier '{rule[0]}'")
    parsed = {
        "letter": letter,
        "key": key if letter not in {"0", "*"} else letter,
        "forbid_na": letter.isupper(),
        "pred": PREDS["0" if letter == "0" else "*" if letter == "*" else letter.lower()],
        "len_op": None,
        "len_cmp": None,
        "lower": None,
        "upper": None,
    }
    rest = rule[1:]
    used, rest = _parse_length(rest, parsed)
    _parse_bounds(rest, parsed)
    return parsed


def _parse_length(rule: str, parsed: dict) -> tuple[int, str]:
    if rule == "" or rule[0] in "([]":
        return 0, rule
    if rule[0] == "*":
        return 1, rule[1:]
    if rule[0] == "?":
        parsed["len_op"] = "<="
        parsed["len_cmp"] = 1
        return 1, rule[1:]
    if rule[0] == "+":
        parsed["len_op"] = ">="
        parsed["len_cmp"] = 1
        return 1, rule[1:]
    start = 0
    op = "=="
    if rule[0] == "=":
        op = "=="
        start = 2 if rule[1:2] == "=" else 1
    elif rule[0] == "<":
        if rule[1:2] == "=":
            op = "<="
            start = 2
        else:
            op = "<"
            start = 1
    elif rule[0] == ">":
        if rule[1:2] == "=":
            op = ">="
            start = 2
        else:
            op = ">"
            start = 1
    body = rule[start:]
    digits = ""
    for ch in body:
        if ch.isdigit() or (ch == "-" and not digits):
            digits += ch
        else:
            break
    if not digits or digits == "-":
        raise CheckError(f"Invalid length definition: {rule}")
    cmp = int(digits)
    if cmp >= 2147483647:
        raise CheckError("Cannot handle length >= 2147483647")
    if cmp < 0:
        raise CheckError("Cannot check for negative length")
    parsed["len_op"] = op
    parsed["len_cmp"] = cmp
    return start + len(digits), rule[start + len(digits):]


def _parse_bounds(rule: str, parsed: dict) -> None:
    if rule == "":
        return
    if rule[0] not in "([]":
        raise CheckError(f"Invalid bound definition, missing opening '(' or '[': {rule}")
    lower_op = ">" if rule[0] == "(" else ">="
    rest = rule[1:]
    lower, end = _read_float(rest)
    if lower is None:
        if lower_op == ">":
            parsed["lower"] = ("!=", float("-inf"))
        else:
            parsed["lower"] = None
    else:
        parsed["lower"] = (lower_op, lower)
    if end >= len(rest):
        raise CheckError(f"Invalid bound definition, error parsing lower bound, missing separator ',' or missing closing ')' or ']': {rule}")
    sep = rest[end]
    if sep == ",":
        upper_src = rest[end + 1:]
    elif sep in ")]":
        upper_src = rest[end:]
    else:
        raise CheckError(f"Invalid bound definition, error parsing lower bound, missing separator ',' or missing closing ')' or ']': {rule}")
    if sep == ",":
        upper, uend = _read_float(upper_src)
        if uend >= len(upper_src) or upper_src[uend] not in ")]":
            raise CheckError(f"Invalid bound definition, error parsing upper bound or missing closing ')' or ']': {rule}")
        close = upper_src[uend]
        leftover = upper_src[uend + 1:]
    else:
        upper = None
        close = sep
        leftover = upper_src[1:]
    if leftover:
        raise CheckError("Additional chars found in rule!")
    if close == ")":
        if upper is None:
            parsed["upper"] = ("!=", float("inf"))
        else:
            parsed["upper"] = ("<", upper)
    else:
        if upper is not None:
            parsed["upper"] = ("<=", upper)


def _read_float(text: str) -> tuple[float | None, int]:
    if not text:
        return None, 0
    i = 0
    if text[0] in "+-":
        i = 1
    start = 0
    saw = False
    while i < len(text) and (text[i].isdigit() or text[i] in ".eE"):
        saw = True
        i += 1
    if text[:3].lower() in {"inf", "+inf", "-inf"} or text[:4].lower() in {"+inf", "-inf"}:
        token = text
        for marker in ("inf", "Inf", "INF"):
            pos = text.find(marker)
            if pos == 0 or (pos == 1 and text[0] in "+-"):
                return float(text[: pos + 3]), pos + 3
    if not saw:
        return None, 0
    try:
        return float(text[:i]), i
    except ValueError:
        return None, 0


def _cmp_len(op: str, got: int, want: int) -> bool:
    return {
        "<": got < want,
        "<=": got <= want,
        "==": got == want,
        ">=": got >= want,
        ">": got > want,
    }[op]


def _cmp_num(op: str, got: float, want: float) -> bool:
    return {
        "<": got < want,
        "<=": got <= want,
        ">": got > want,
        ">=": got >= want,
        "!=": got != want,
    }[op]


def _bound_message(op: str, limit: float, kind: str) -> str:
    symbol = op
    if kind == "string":
        return message("All elements must have %s %s chars", symbol, fmt_g(limit))
    if math.isinf(limit) and limit > 0 and op == "!=":
        return message("All elements must be %s Inf", symbol)
    if math.isinf(limit) and limit < 0 and op == "!=":
        return message("All elements must be %s -Inf", symbol)
    return message("All elements must be %s %s", symbol, fmt_g(limit))


def _check_bound(obj, op: str, limit: float) -> str | None:
    if isinstance(obj, Vec) and obj.mode == "double":
        for item in obj.data:
            if not is_na_scalar(item, "double") and not _cmp_num(op, float(item), limit):
                return _bound_message(op, limit, "number")
        return None
    if isinstance(obj, Vec) and obj.mode == "integer" and "factor" not in obj.klass:
        for item in obj.data:
            if item is not NA and not _cmp_num(op, float(item), limit):
                return _bound_message(op, limit, "number")
        return None
    if isinstance(obj, Vec) and obj.mode == "character":
        for item in obj.data:
            size = 0.0 if item is NA else float(nchar_bytes(item))
            if not _cmp_num(op, size, limit):
                return _bound_message(op, limit, "string")
        return None
    if is_class_factor(obj):
        levels = Vec("character", list(obj.levels or []))
        return _check_bound(levels, op, limit)
    raise CheckError(f"Bound checks only possible for numeric variables, strings and factors, not {guess_type(obj)}")


def _check_rule(obj, rule: dict, explain: bool):
    if not rule["pred"](obj):
        if not explain:
            return False
        return message("Must be of class '%s', not '%s'", CLASS_NAMES[rule["key"]], guess_type(obj))
    if rule["forbid_na"]:
        pos = _missing_pos(obj, rule["key"])
        if pos:
            if not explain:
                return False
            if is_class_matrix(obj):
                got = nrows(obj)
                return message(
                    "May not contain missing values, first at column %i, element %i",
                    (pos - 1) // got + 1,
                    (pos - 1) % got + 1,
                )
            if is_class_frame(obj):
                got = nrows(obj)
                col = (pos - 1) // got
                name = obj.names[col] if obj.names else ""
                return message(
                    "May not contain missing values, first at column '%s', element %i",
                    name,
                    (pos - 1) % got + 1,
                )
            return message("May not contain missing values, first at position %i", pos)
    if rule["len_op"] is not None and not _cmp_len(rule["len_op"], xlength(obj), rule["len_cmp"]):
        if not explain:
            return False
        return message(
            "Must be of length %s %i, but has length %s",
            rule["len_op"],
            rule["len_cmp"],
            fmt_g(float(xlength(obj))),
        )
    for bound in (rule["lower"], rule["upper"]):
        if bound is None:
            continue
        hit = _check_bound(obj, bound[0], bound[1])
        if hit:
            return hit if explain else False
    return True


def _rules(rules) -> list[str]:
    if isinstance(rules, str):
        return [rules]
    obj = wrap(rules)
    if not is_class_string(obj):
        raise CheckError("Argument 'rules' must be a string")
    if any(item is NA for item in obj.data):
        raise CheckError("Rule may not be NA")
    return list(obj.data)


def qtest(x, rules) -> bool:
    obj = wrap(x)
    texts = _rules(rules)
    if not texts:
        return True
    parsed = [_parse(text) for text in texts]
    return any(_check_rule(obj, rule, False) is True for rule in parsed)


def qassert(x, rules, var_name=None):
    obj = wrap(x)
    if var_name is None:
        var_name = caller_arg(2)
    texts = _rules(rules)
    if not texts:
        return x
    messages = []
    for text in texts:
        hit = _check_rule(obj, _parse(text), True)
        if hit is True:
            return x
        messages.append(hit)
    raise CheckError(_qmsg(messages, var_name))


def _qmsg(messages: list[str], var_name: str) -> str:
    if len(messages) > 1:
        body = "\n".join(textwrap.wrap(
            " ".join(messages), width=72, initial_indent="", subsequent_indent=""
        ))
        # R's strwrap prefixes each original message, it does not reflow them together.
        lines = [f" * {item}" for item in messages]
        body = "One of the following must apply:\n" + "\n".join(lines)
        return f"Assertion on '{var_name}' failed. {body}."
    return f"Assertion on '{var_name}' failed. {messages[0]}."


def qexpect(x, rules, info=None, label=None):
    from .expectations import makeExpectation

    obj = wrap(x)
    if label is None:
        label = caller_arg(2)
    texts = _rules(rules)
    if not texts:
        return makeExpectation(x, True, info, label)
    messages = []
    for text in texts:
        hit = _check_rule(obj, _parse(text), True)
        if hit is True:
            return makeExpectation(x, True, info, label)
        messages.append(hit)
    return makeExpectation(x, _qmsg(messages, label), info, label)


def qexpectr(x, rules, info=None, label=None):
    from .expectations import makeExpectation

    obj = wrap(x)
    if label is None:
        label = caller_arg(2)
    if not (is_class_list(obj) or is_class_frame(obj)):
        raise CheckError("Argument 'x' must be a list or data.frame")
    texts = _rules(rules)
    if not texts:
        return makeExpectation(x, True, info, label)
    parsed = [_parse(text) for text in texts]
    for index, item in enumerate(obj.data):
        child = item if isinstance(item, Vec) else wrap(item)
        messages = []
        passed = False
        for rule in parsed:
            hit = _check_rule(child, rule, True)
            if hit is True:
                passed = True
                break
            messages.append(hit)
        if not passed:
            return makeExpectation(x, _qrmsg(obj, messages, label, index + 1), info, label)
    return makeExpectation(x, True, info, label)


def qtestr(x, rules, depth=1):
    obj = wrap(x)
    if not (is_class_list(obj) or is_class_frame(obj)):
        raise CheckError("Argument 'x' must be a list or data.frame")
    depth = C._count(depth, "depth")
    texts = _rules(rules)
    parsed = [_parse(text) for text in texts] if texts else []
    return _qtest_list(obj, parsed, depth)


def _qtest_list(obj: Vec, parsed, depth: int) -> bool:
    for item in obj.data:
        child = item if isinstance(item, Vec) else wrap(item)
        if depth > 1 and is_class_list(child):
            if not _qtest_list(child, parsed, depth - 1):
                return False
        else:
            if parsed and not any(_check_rule(child, rule, False) is True for rule in parsed):
                return False
    return True


def qassertr(x, rules, var_name=None):
    obj = wrap(x)
    if var_name is None:
        var_name = caller_arg(2)
    if not (is_class_list(obj) or is_class_frame(obj)):
        raise CheckError("Argument 'x' must be a list or data.frame")
    texts = _rules(rules)
    if not texts:
        return x
    parsed = [_parse(text) for text in texts]
    for index, item in enumerate(obj.data):
        child = item if isinstance(item, Vec) else wrap(item)
        messages = []
        passed = False
        for rule in parsed:
            hit = _check_rule(child, rule, True)
            if hit is True:
                passed = True
                break
            messages.append(hit)
        if not passed:
            raise CheckError(_qrmsg(obj, messages, var_name, index + 1))
    return x


def _qrmsg(obj: Vec, messages: list[str], var_name: str, pos: int) -> str:
    if obj.names:
        item = f", element '{obj.names[pos - 1]}' ({pos}),"
    else:
        item = f", element {pos},"
    if len(messages) > 1:
        lines = "\n".join(f" * {text}" for text in messages)
        body = "One of the following must apply:\n" + lines
    else:
        body = messages[0]
    return f"Assertion on '{var_name}'{item} failed. {body}."
