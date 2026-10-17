"""A small R expression language for see_if, assert_that, and validate_that.

Messages quote the expression the way deparse does, so the parser keeps the
tokens. Evaluation looks in the supplied environment and then in BUILTINS.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

from assertthat.objects import NA, NA_character_, NA_integer_, NA_real_, Vector

BUILTINS: dict[str, Any] = {}

_CMP = ("<=", ">=", "==", "!=")
_WIDTH = 60


@dataclass
class Name:
    value: str


@dataclass
class Literal:
    value: Any
    text: str


@dataclass
class Neg:
    value: Any


@dataclass
class Sum:
    terms: list[Any]


@dataclass
class Infix:
    op: str
    left: Any
    right: Any


@dataclass
class Arg:
    name: str | None
    value: Any


@dataclass
class Call:
    fn: Name
    args: list[Arg]


@dataclass
class Matched:
    """A call after match.call. Index 1 is the function, as in R."""

    fn: str
    pairs: list[tuple[str | None, Any]]

    def __getitem__(self, key: int | str) -> Any:
        if isinstance(key, int):
            if key == 1:
                return Name(self.fn)
            return self.pairs[key - 2][1]
        for name, value in self.pairs:
            if name == key:
                return value
        return None


class ParseError(Exception):
    pass


class _Tokens:
    def __init__(self, text: str) -> None:
        self.text = text
        self.n = len(text)
        self.i = 0

    def peek(self) -> str:
        self._skip()
        if self.i >= self.n:
            return ""
        return self.text[self.i]

    def _skip(self) -> None:
        while self.i < self.n and self.text[self.i] in " \t\r\n":
            self.i += 1

    def take(self, word: str) -> bool:
        self._skip()
        if not self.text.startswith(word, self.i):
            return False
        nxt = self.i + len(word)
        if word in {"=", "<", ">", "!"} and nxt < self.n and self.text[nxt] == "=":
            return False
        self.i = nxt
        return True

    def identifier(self) -> str | None:
        self._skip()
        start = self.i
        if start >= self.n:
            return None
        char = self.text[start]
        if not (char.isalpha() or char in "._"):
            return None
        self.i += 1
        while self.i < self.n and (self.text[self.i].isalnum() or self.text[self.i] in "._"):
            self.i += 1
        return self.text[start:self.i]

    def number(self) -> str | None:
        self._skip()
        start = self.i
        if start >= self.n or not (self.text[start].isdigit() or self.text[start] == "."):
            return None
        if self.text[start] == "." and (start + 1 >= self.n or not self.text[start + 1].isdigit()):
            return None
        self.i += 1
        while self.i < self.n and (self.text[self.i].isdigit() or self.text[self.i] == "."):
            self.i += 1
        if self.i < self.n and self.text[self.i] in "eE":
            self.i += 1
            if self.i < self.n and self.text[self.i] in "+-":
                self.i += 1
            while self.i < self.n and self.text[self.i].isdigit():
                self.i += 1
        return self.text[start:self.i]

    def string(self) -> str | None:
        self._skip()
        if self.i >= self.n or self.text[self.i] not in "\"'":
            return None
        quote = self.text[self.i]
        self.i += 1
        chars: list[str] = []
        while self.i < self.n:
            char = self.text[self.i]
            self.i += 1
            if char == "\\":
                if self.i >= self.n:
                    break
                escaped = self.text[self.i]
                self.i += 1
                chars.append({"n": "\n", "t": "\t", "\\": "\\", "'": "'", '"': '"'}.get(escaped, escaped))
            elif char == quote:
                return "".join(chars)
            else:
                chars.append(char)
        raise ParseError("unterminated string")

    def percent(self) -> str | None:
        self._skip()
        if self.peek() != "%":
            return None
        end = self.text.find("%", self.i + 1)
        if end < 0:
            return None
        op = self.text[self.i : end + 1]
        self.i = end + 1
        return op

    def backtick(self) -> str | None:
        self._skip()
        if self.peek() != "`":
            return None
        self.i += 1
        end = self.text.find("`", self.i)
        if end < 0:
            raise ParseError("unterminated name")
        name = self.text[self.i:end]
        self.i = end + 1
        return name


def parse(text: str) -> Any:
    tokens = _Tokens(text)
    node = _parse_or(tokens)
    if tokens.peek():
        raise ParseError(f"unexpected {tokens.peek()!r} in {text!r}")
    return node


def _parse_or(tokens: _Tokens) -> Any:
    left = _parse_and(tokens)
    while tokens.take("||"):
        left = Infix("||", left, _parse_and(tokens))
    return left


def _parse_and(tokens: _Tokens) -> Any:
    left = _parse_not(tokens)
    while tokens.take("&&"):
        left = Infix("&&", left, _parse_not(tokens))
    return left


def _parse_not(tokens: _Tokens) -> Any:
    if tokens.take("!"):
        return Call(Name("!"), [Arg(None, _parse_not(tokens))])
    return _parse_cmp(tokens)


def _parse_cmp(tokens: _Tokens) -> Any:
    left = _parse_sum(tokens)
    while True:
        op = next((item for item in _CMP if tokens.take(item)), None)
        if op is None and tokens.take("<"):
            op = "<"
        elif op is None and tokens.take(">"):
            op = ">"
        if op is None:
            return left
        left = Infix(op, left, _parse_sum(tokens))


def _parse_sum(tokens: _Tokens) -> Any:
    left = _parse_product(tokens)
    terms = None
    while True:
        if tokens.peek() == "+" and tokens.take("+"):
            right = _parse_product(tokens)
            if terms is None:
                terms = [left, right]
                left = Sum(terms)
            else:
                terms.append(right)
            continue
        if tokens.peek() == "-" and tokens.take("-"):
            right = _parse_product(tokens)
            left = Infix("-", left if terms is None else Sum(terms), right)
            terms = None
            continue
        return left


def _parse_product(tokens: _Tokens) -> Any:
    left = _parse_colon(tokens)
    while True:
        op = tokens.percent()
        if op is None and tokens.peek() in {"*", "/"}:
            op = tokens.text[tokens.i]
            tokens.i += 1
        if op is None:
            return left
        left = Infix(op, left, _parse_colon(tokens))


def _parse_colon(tokens: _Tokens) -> Any:
    left = _parse_unary(tokens)
    while tokens.take(":"):
        left = Infix(":", left, _parse_unary(tokens))
    return left


def _parse_unary(tokens: _Tokens) -> Any:
    if tokens.take("-"):
        return Neg(_parse_unary(tokens))
    if tokens.take("+"):
        return _parse_unary(tokens)
    return _parse_postfix(tokens)


def _parse_postfix(tokens: _Tokens) -> Any:
    node = _parse_primary(tokens)
    while tokens.take("("):
        if not isinstance(node, Name):
            raise ParseError("call of a non-name")
        node = Call(node, _parse_args(tokens))
    return node


def _parse_args(tokens: _Tokens) -> list[Arg]:
    args: list[Arg] = []
    if tokens.take(")"):
        return args
    while True:
        name = None
        mark = tokens.i
        ident = tokens.identifier()
        if ident is not None and tokens.take("="):
            name = ident
        else:
            tokens.i = mark
        args.append(Arg(name, _parse_or(tokens)))
        if tokens.take(")"):
            return args
        if not tokens.take(","):
            raise ParseError("expected , or )")


def _parse_primary(tokens: _Tokens) -> Any:
    if tokens.take("("):
        node = _parse_or(tokens)
        if not tokens.take(")"):
            raise ParseError("expected )")
        return node
    quoted = tokens.backtick()
    if quoted is not None:
        return Name(quoted)
    text = tokens.string()
    if text is not None:
        return Literal(text, _render_string(text))
    number = tokens.number()
    if number is not None:
        value = float(number) if "." in number or "e" in number.lower() else int(number)
        return Literal(value, number)
    word = tokens.identifier()
    if word is None:
        raise ParseError(f"expected an expression at {tokens.text[tokens.i:]!r}")
    if word == "TRUE":
        return Literal(True, "TRUE")
    if word == "FALSE":
        return Literal(False, "FALSE")
    if word == "NULL":
        return Literal(None, "NULL")
    if word == "NA":
        return Literal(NA, "NA")
    if word == "NA_real_":
        return Literal(NA_real_, "NA_real_")
    if word == "NA_integer_":
        return Literal(NA_integer_, "NA_integer_")
    if word == "NA_character_":
        return Literal(NA_character_, "NA_character_")
    return Name(word)


def _render_string(text: str) -> str:
    return '"' + text.replace("\\", "\\\\").replace('"', '\\"') + '"'


def _syntactic(name: str) -> bool:
    if not name:
        return False
    first, rest = name[0], name[1:]
    if not (first.isalpha() or first == "."):
        return False
    return all(char.isalnum() or char in "._" for char in rest)


def render_fn(name: str) -> str:
    return name if _syntactic(name) else f"`{name}`"


def render(node: Any) -> str:
    if isinstance(node, Name):
        return node.value if _syntactic(node.value) else f"`{node.value}`"
    if isinstance(node, Literal):
        return node.text
    if isinstance(node, Neg):
        return "-" + render(node.value)
    if isinstance(node, Sum):
        return " + ".join(render(term) for term in node.terms)
    if isinstance(node, Infix):
        if node.op == ":":
            return f"{render(node.left)}:{render(node.right)}"
        return f"{render(node.left)} {node.op} {render(node.right)}"
    if isinstance(node, Call):
        return render_fn(node.fn.value) + "(" + ", ".join(_render_arg(arg) for arg in node.args) + ")"
    if isinstance(node, Matched):
        return _render_matched(node)[0]
    return str(node)


def _render_arg(arg: Arg) -> str:
    body = render(arg.value)
    if arg.name is None:
        return body
    return f"{arg.name} = {body}"


def deparse_lines(node: Any) -> list[str]:
    if isinstance(node, Matched):
        return _render_matched(node)
    text = render(node)
    return text.split("\n") if text else [""]


def _render_matched(node: Matched) -> list[str]:
    prefix = render_fn(node.fn) + "("
    if len(node.pairs) == 1 and isinstance(node.pairs[0][1], Sum):
        name, value = node.pairs[0]
        head = prefix + (f"{name} = " if name else "")
        return _pack_sum(head, value.terms)
    parts = []
    for name, value in node.pairs:
        body = render(value)
        parts.append(body if name is None else f"{name} = {body}")
    return [prefix + ", ".join(parts) + ")"]


def _pack_sum(prefix: str, terms: list[Any]) -> list[str]:
    line = prefix + render(terms[0])
    lines: list[str] = []
    for term in terms[1:]:
        piece = render(term)
        if len(line + " + " + piece) > _WIDTH:
            lines.append(line + " + ")
            line = "    " + piece
        else:
            line += " + " + piece
    lines.append(line + ")")
    return lines


def fail_default(call: Any, env: dict[str, Any]) -> str:
    del env
    lines = deparse_lines(call)
    text = lines[0] + ("..." if len(lines) > 1 else "")
    return text + " is not TRUE"


def formals_of(fn: Any) -> list[str]:
    recorded = getattr(fn, "r_formals", None)
    if recorded is not None:
        return list(recorded)
    import inspect

    names: list[str] = []
    for param in inspect.signature(fn).parameters.values():
        if param.kind in (
            inspect.Parameter.VAR_POSITIONAL,
            inspect.Parameter.VAR_KEYWORD,
        ):
            names.append("...")
        else:
            names.append(param.name)
    return names


def _resolve_formal(name: str, formals: list[str]) -> str:
    if name in formals:
        return name
    matches = [formal for formal in formals if formal.startswith(name) and formal != "..."]
    if len(matches) == 1:
        return matches[0]
    return name


def match_call(fn: Any, node: Any) -> Matched:
    if isinstance(node, Infix):
        node = Call(Name(node.op), [Arg(None, node.left), Arg(None, node.right)])
    if isinstance(node, Call) and getattr(fn, "r_primitive", False):
        return Matched(node.fn.value, [(arg.name, arg.value) for arg in node.args])
    if not isinstance(node, Call):
        return Matched(render(node), [])
    formals = formals_of(fn)
    bound: dict[str, Any] = {}
    used: set[str] = set()
    positional: list[Any] = []
    dots: list[tuple[str | None, Any]] = []
    for arg in node.args:
        if arg.name is None:
            positional.append(arg.value)
            continue
        formal = _resolve_formal(arg.name, formals)
        if formal == "..." or formal not in formals:
            dots.append((arg.name, arg.value))
        else:
            bound[formal] = arg.value
            used.add(formal)
    index = 0
    for value in positional:
        while index < len(formals) and formals[index] in used:
            index += 1
        if index >= len(formals):
            dots.append((None, value))
            continue
        formal = formals[index]
        if formal == "...":
            dots.append((None, value))
            continue
        bound[formal] = value
        used.add(formal)
        index += 1
    pairs: list[tuple[str | None, Any]] = []
    for formal in formals:
        if formal == "...":
            pairs.extend(dots)
            dots = []
        elif formal in bound:
            pairs.append((formal, bound[formal]))
    pairs.extend(dots)
    return Matched(node.fn.value, pairs)


def lookup(name: str, env: dict[str, Any]) -> Any:
    if name in env:
        return env[name]
    if name in BUILTINS:
        return BUILTINS[name]
    if name == "Inf":
        return math.inf
    if name == "NaN":
        return math.nan
    raise NameError(f"object '{name}' not found")


def evaluate(node: Any, env: dict[str, Any]) -> Any:
    if isinstance(node, Literal):
        return node.value
    if isinstance(node, Name):
        return lookup(node.value, env)
    if isinstance(node, Neg):
        return -evaluate(node.value, env)
    if isinstance(node, Sum):
        total = evaluate(node.terms[0], env)
        for term in node.terms[1:]:
            total = total + evaluate(term, env)
        return total
    if isinstance(node, Infix):
        if node.op == "&&":
            left = evaluate(node.left, env)
            if left is False:
                return False
            return _and(left, evaluate(node.right, env))
        if node.op == "||":
            left = evaluate(node.left, env)
            if left is True:
                return True
            right = evaluate(node.right, env)
            return True if right is True else left if right is False else right
        if node.op == ":":
            return _colon(evaluate(node.left, env), evaluate(node.right, env))
        function = lookup(node.op, env)
        return function(evaluate(node.left, env), evaluate(node.right, env))
    if isinstance(node, Call):
        function = evaluate(node.fn, env)
        positional = []
        keywords = {}
        for arg in node.args:
            value = evaluate(arg.value, env)
            if arg.name is None:
                positional.append(value)
            else:
                keywords[arg.name] = value
        return function(*positional, **keywords)
    raise TypeError(f"cannot evaluate {node!r}")


def _and(left: Any, right: Any) -> Any:
    from assertthat.objects import r_and

    return r_and(left, right)


def _colon(left: Any, right: Any) -> Vector:
    start = int(left)
    stop = int(right)
    step = 1 if stop >= start else -1
    return Vector(list(range(start, stop + step, step)), "integer")


def register(name: str, fn: Any, formals: list[str], primitive: bool = False) -> Any:
    fn.r_formals = formals
    fn.r_primitive = primitive
    fn.r_name = name
    BUILTINS[name] = fn
    return fn
