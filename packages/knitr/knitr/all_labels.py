"""Return chunk labels, matching knitr::all_labels.

Conditions are R expressions written as strings. Python evaluates arguments
before the call, so ``all_labels(engine == "Rcpp")`` is not the R call.
Pass ``all_labels('engine == "Rcpp"')`` instead. A name that cannot be
resolved is false, and an expression result is evaluated once more.
"""

from __future__ import annotations

import math


class _Missing:
    """R's NA. It is not Python None, which is NULL."""

    def __repr__(self):
        return "NA"


NA = _Missing()

_BASE = {
    "T": True,
    "F": False,
    "NA_character_": NA,
    "NA_real_": NA,
    "NA_integer_": NA,
    "NA_complex_": NA,
    "pi": math.pi,
}


class _Empty:
    """R's logical(0), including the result of comparing NULL."""


class _Expression:
    def __init__(self, args):
        self.args = args


class _Name:
    def __init__(self, name):
        self.name = name


class _Literal:
    def __init__(self, value):
        self.value = value


class _Unary:
    def __init__(self, op, arg):
        self.op = op
        self.arg = arg


class _Binary:
    def __init__(self, op, left, right):
        self.op = op
        self.left = left
        self.right = right


class _Call:
    def __init__(self, name, args):
        self.name = name
        self.args = args


class _CodeStore:
    """Chunk registry read by all_labels.

    ``knit_code$get()`` in R. ``enclosure`` is ``knit_global()``, which is
    the global environment when nothing is being knitted.
    """

    def __init__(self):
        self._chunks = {}
        self.enclosure = {}

    def restore(self):
        self._chunks = {}

    def set(self, **chunks):
        for label, value in chunks.items():
            self._chunks[label] = value

    def get(self, name=None):
        if name is None:
            return self._chunks
        return self._chunks[name]


knit_code = _CodeStore()


def chunk(code="", **opts):
    """One code chunk. ``opts`` are the local chunk options."""

    if isinstance(code, str):
        lines = [code]
    elif code is None:
        lines = []
    else:
        lines = list(code)
    return {"code": lines, "chunk_opts": opts}


def all_labels(*conditions):
    """Labels of stored chunks whose local options satisfy every condition.

    With no conditions, every stored label is returned. An empty registry
    is R's NULL. A condition that errors, including a missing option, is
    false for that chunk. Later conditions are not evaluated once a chunk
    has already failed.
    """

    code = knit_code.get()
    labels = list(code) if code else None
    if len(conditions) == 0:
        return labels
    if labels is None:
        return None

    parsed = [_parse_condition(cond) for cond in conditions]
    params = [_chunk_opts(code[label]) for label in labels]
    idx = [True] * len(labels)
    for cond in parsed:
        for j, opts in enumerate(params):
            if idx[j] is True:
                res = _try_eval(cond, opts)
                if isinstance(res, _Expression):
                    res = _try_eval(res, opts)
                _assign(idx, j, res)
            elif idx[j] is False:
                continue
            else:
                raise ValueError("missing value where TRUE/FALSE needed")
    return _subset(labels, idx)


def _chunk_opts(value):
    if isinstance(value, dict) and "chunk_opts" in value:
        return value["chunk_opts"]
    return None


def _parse_condition(cond):
    if not isinstance(cond, str):
        raise TypeError("a condition is an R expression written as a string")
    tokens = _tokenize(cond)
    parser = _Parser(tokens)
    node = parser.parse_or()
    if parser.peek() is not None:
        raise ValueError(f"unexpected {parser.peek()[1]!r} in condition")
    return node


def _tokenize(text):
    tokens = []
    i = 0
    n = len(text)
    while i < n:
        c = text[i]
        if c.isspace():
            i += 1
            continue
        two = text[i : i + 2]
        if two in {"||", "&&", "==", "!=", "<=", ">="}:
            tokens.append(("op", two))
            i += 2
            continue
        if c in "!<>(),":
            tokens.append(("op", c))
            i += 1
            continue
        if c in "\"'":
            i, value = _scan_string(text, i)
            tokens.append(("string", value))
            continue
        if c.isdigit() or (c == "." and i + 1 < n and text[i + 1].isdigit()):
            i, value = _scan_number(text, i)
            tokens.append(("number", value))
            continue
        if c.isalpha() or c == "." or c == "_":
            start = i
            i += 1
            while i < n and (text[i].isalnum() or text[i] in "._"):
                i += 1
            word = text[start:i]
            tokens.append(("word", word))
            continue
        raise ValueError(f"unexpected {c!r} in condition")
    return tokens


def _scan_string(text, i):
    quote = text[i]
    i += 1
    chars = []
    n = len(text)
    while i < n:
        c = text[i]
        if c == "\\":
            if i + 1 >= n:
                raise ValueError("unfinished escape in condition")
            nxt = text[i + 1]
            chars.append({"n": "\n", "t": "\t", "r": "\r", "\\": "\\", "'": "'", '"': '"'}.get(nxt, nxt))
            i += 2
            continue
        if c == quote:
            return i + 1, "".join(chars)
        chars.append(c)
        i += 1
    raise ValueError("unfinished string in condition")


def _scan_number(text, i):
    start = i
    n = len(text)
    while i < n and text[i].isdigit():
        i += 1
    if i < n and text[i] == ".":
        i += 1
        while i < n and text[i].isdigit():
            i += 1
    if i < n and text[i] in "eE":
        i += 1
        if i < n and text[i] in "+-":
            i += 1
        while i < n and text[i].isdigit():
            i += 1
    if i < n and text[i] in "Ll":
        i += 1
    return i, float(text[start:i].rstrip("Ll"))


_COMPARE = {
    ("op", "=="),
    ("op", "!="),
    ("op", "<"),
    ("op", ">"),
    ("op", "<="),
    ("op", ">="),
}


class _Parser:
    def __init__(self, tokens):
        self.tokens = tokens
        self.i = 0

    def peek(self):
        if self.i >= len(self.tokens):
            return None
        return self.tokens[self.i]

    def eat(self):
        token = self.peek()
        if token is None:
            raise ValueError("unexpected end of condition")
        self.i += 1
        return token

    def parse_or(self):
        left = self.parse_and()
        while self.peek() == ("op", "||"):
            self.eat()
            left = _Binary("||", left, self.parse_and())
        return left

    def parse_and(self):
        left = self.parse_not()
        while self.peek() == ("op", "&&"):
            self.eat()
            left = _Binary("&&", left, self.parse_not())
        return left

    def parse_not(self):
        if self.peek() == ("op", "!"):
            self.eat()
            return _Unary("!", self.parse_not())
        return self.parse_cmp()

    def parse_cmp(self):
        left = self.parse_primary()
        if self.peek() not in _COMPARE:
            return left
        op = self.eat()[1]
        right = self.parse_primary()
        if self.peek() in _COMPARE:
            raise ValueError("unexpected comparison in condition")
        return _Binary(op, left, right)

    def parse_primary(self):
        token = self.peek()
        if token is None:
            raise ValueError("unexpected end of condition")
        if token == ("op", "("):
            self.eat()
            node = self.parse_or()
            if self.peek() != ("op", ")"):
                raise ValueError("expected ')' in condition")
            self.eat()
            return node
        kind, value = self.eat()
        if kind == "string":
            return _Literal(value)
        if kind == "number":
            return _Literal(value)
        if kind != "word":
            raise ValueError(f"unexpected {value!r} in condition")
        if value == "TRUE":
            literal = _Literal(True)
        elif value == "FALSE":
            literal = _Literal(False)
        elif value == "NULL":
            literal = _Literal(None)
        elif value == "NA":
            literal = _Literal(NA)
        elif value == "Inf":
            literal = _Literal(math.inf)
        elif value == "NaN":
            literal = _Literal(math.nan)
        else:
            literal = None
        if self.peek() == ("op", "("):
            if literal is not None:
                raise ValueError(f"unexpected call {value}")
            self.eat()
            args = []
            if self.peek() != ("op", ")"):
                args.append(self.parse_or())
                while self.peek() == ("op", ","):
                    self.eat()
                    if self.peek() == ("op", ")"):
                        break
                    args.append(self.parse_or())
            if self.peek() != ("op", ")"):
                raise ValueError("expected ')' in condition")
            self.eat()
            return _Call(value, args)
        if literal is not None:
            return literal
        return _Name(value)


def _try_eval(node, opts):
    try:
        return _eval_node(node, opts, knit_code.enclosure)
    except Exception:
        return False


def _eval_node(node, envir, enclos):
    if isinstance(node, _Expression):
        value = None
        for arg in node.args:
            value = _eval_node(arg, envir, enclos)
        return value
    if isinstance(node, _Literal):
        return node.value
    if isinstance(node, _Name):
        return _lookup(node.name, envir, enclos)
    if isinstance(node, _Unary):
        return _negate(_eval_node(node.arg, envir, enclos))
    if isinstance(node, _Call):
        if node.name == "expression":
            return _Expression(node.args)
        raise NameError(f"could not find function \"{node.name}\"")
    if isinstance(node, _Binary):
        if node.op == "&&":
            return _and(node, envir, enclos)
        if node.op == "||":
            return _or(node, envir, enclos)
        left = _eval_node(node.left, envir, enclos)
        right = _eval_node(node.right, envir, enclos)
        return _compare(node.op, left, right)
    raise TypeError("invalid condition")


def _lookup(name, envir, enclos):
    if isinstance(envir, dict) and name in envir:
        return envir[name]
    if name in enclos:
        return enclos[name]
    if name in _BASE:
        return _BASE[name]
    raise NameError(f"object '{name}' not found")


def _negate(value):
    if value is True:
        return False
    if value is False:
        return True
    if value is NA:
        return NA
    if value is None or isinstance(value, _Empty):
        return _Empty()
    raise TypeError("invalid argument to !")


def _and(node, envir, enclos):
    left = _as_flag(_eval_node(node.left, envir, enclos))
    if left is False:
        return False
    right = _as_flag(_eval_node(node.right, envir, enclos))
    if left is True:
        return right
    if right is False:
        return False
    return NA


def _or(node, envir, enclos):
    left = _as_flag(_eval_node(node.left, envir, enclos))
    if left is True:
        return True
    right = _as_flag(_eval_node(node.right, envir, enclos))
    if left is False:
        return right
    if right is True:
        return True
    return NA


def _as_flag(value):
    if value is True or value is False or value is NA:
        return value
    raise TypeError("invalid 'x' type in 'x && y'")


def _compare(op, left, right):
    if left is None or right is None or isinstance(left, _Empty) or isinstance(right, _Empty):
        return _Empty()
    if left is NA or right is NA or _is_nan(left) or _is_nan(right):
        return NA
    if op in {"==", "!="}:
        same = _equal(left, right)
        return same if op == "==" else not same
    if isinstance(left, str) or isinstance(right, str):
        return _order(op, _as_character(left), _as_character(right))
    return _order(op, _as_number(left), _as_number(right))


def _order(op, left, right):
    if op == "<":
        return left < right
    if op == ">":
        return left > right
    if op == "<=":
        return left <= right
    if op == ">=":
        return left >= right
    raise ValueError(f"unknown operator {op}")


def _is_nan(value):
    return isinstance(value, float) and math.isnan(value)


def _equal(left, right):
    if isinstance(left, str) or isinstance(right, str):
        return _as_character(left) == _as_character(right)
    return _as_number(left) == _as_number(right)


def _as_character(value):
    if value is True:
        return "TRUE"
    if value is False:
        return "FALSE"
    if isinstance(value, str):
        return value
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


def _as_number(value):
    if value is True:
        return 1.0
    if value is False:
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)
    raise TypeError("comparison is not meaningful")


def _assign(idx, j, res):
    if res is None or isinstance(res, _Empty):
        raise ValueError("replacement has length zero")
    if isinstance(res, _Expression):
        raise ValueError("incompatible types")
    if res is not True and res is not False and res is not NA:
        raise TypeError("condition was not TRUE or FALSE")
    idx[j] = res


def _subset(labels, idx):
    if labels is None:
        return None
    out = []
    for flag, label in zip(idx, labels, strict=True):
        if flag is True:
            out.append(label)
        elif flag is NA:
            out.append(None)
        elif flag is not False:
            raise TypeError("invalid subscript")
    return out
