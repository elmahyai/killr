"""Parse R source the way evaluate::parse_all does.

Comments and blank lines stay in ``src``. Expressions that share a line,
including several statements joined by ``;``, stay in one row. A comment
inside a brace is part of that brace's line span, not its own row.
"""

from __future__ import annotations

import inspect
import io
import textwrap
from dataclasses import dataclass


class ParseError(Exception):
    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


@dataclass
class Node:
    start: int
    end: int


@dataclass
class Literal(Node):
    value: object
    code: str


@dataclass
class Name(Node):
    name: str


@dataclass
class Unary(Node):
    op: str
    expr: Node


@dataclass
class Binary(Node):
    op: str
    left: Node
    right: Node


@dataclass
class Call(Node):
    func: Node
    args: list


@dataclass
class Brace(Node):
    body: list


@dataclass
class Paren(Node):
    expr: Node


@dataclass
class Function(Node):
    params: list
    body: Node


@dataclass
class If(Node):
    cond: Node
    then: Node
    else_: Node | None


@dataclass
class For(Node):
    var: str
    seq: Node
    body: Node


@dataclass
class Tok:
    kind: str
    text: str
    line: int


class ParseResult:
    def __init__(self, rows: list[tuple[str, list]], error: ParseError | None = None) -> None:
        self.rows = rows
        self.error = error

    @property
    def src(self) -> list[str]:
        return [src for src, _exprs in self.rows]

    @property
    def expr(self) -> list[list]:
        return [exprs for _src, exprs in self.rows]

    def __getitem__(self, key: str):
        if key == "src":
            return self.src
        if key == "expr":
            return self.expr
        raise KeyError(key)

    def __eq__(self, other) -> bool:
        return isinstance(other, ParseResult) and self.rows == other.rows and self.error == other.error


def deparse(node, width: int = 500) -> str:
    if node is None:
        return "NULL"
    text = getattr(node, "text", None)
    if text is not None and node.__class__.__name__ == "Sentinel":
        return text
    if isinstance(node, str):
        return node
    if isinstance(node, Literal):
        return node.code
    if isinstance(node, Name):
        return node.name
    if isinstance(node, Unary):
        return f"{node.op}{deparse(node.expr, width)}"
    if isinstance(node, Binary):
        left = deparse(node.left, width)
        right = deparse(node.right, width)
        if node.op == ":":
            return f"{left}:{right}"
        return f"{left} {node.op} {right}"
    if isinstance(node, Paren):
        return f"({deparse(node.expr, width)})"
    if isinstance(node, Brace):
        if not node.body:
            return "{\n}"
        inner = "; ".join(deparse(expr, width) for expr in node.body)
        return "{ " + inner + " }"
    if isinstance(node, Call):
        fn = deparse(node.func, width)
        parts = []
        for name, arg in node.args:
            bit = deparse(arg, width)
            if name:
                bit = f"{name} = {bit}"
            parts.append(bit)
        return f"{fn}({', '.join(parts)})"
    if isinstance(node, Function):
        params = []
        for name, default in node.params:
            if default is None:
                params.append(name)
            else:
                params.append(f"{name} = {deparse(default, width)}")
        return f"function({', '.join(params)}) {deparse(node.body, width)}"
    if isinstance(node, If):
        text = f"if ({deparse(node.cond, width)}) {deparse(node.then, width)}"
        if node.else_ is not None:
            text += f" else {deparse(node.else_, width)}"
        return text
    if isinstance(node, For):
        return f"for ({node.var} in {deparse(node.seq, width)}) {deparse(node.body, width)}"
    return str(node)


def expr_label(nodes: list) -> str:
    if not nodes:
        return "expression()"
    return "expression(" + ", ".join(deparse(node) for node in nodes) + ")"


def parse_all(x, filename: str | None = None, allow_error: bool = False):
    if isinstance(x, str):
        return _parse_character([x], filename, allow_error)
    if isinstance(x, (list, tuple)) and all(isinstance(item, str) for item in x):
        return _parse_character(list(x), filename, allow_error)
    if isinstance(x, io.IOBase):
        return _parse_connection(x, filename, allow_error)
    if isinstance(x, Node):
        return _parse_character([deparse(x)], filename, allow_error)
    if callable(x):
        body = _function_body(x)
        return _parse_character(body if isinstance(body, list) else [body], filename or "<filename>", allow_error)
    raise TypeError("parse_all() expects a string, a list of strings, a file, a function, or a call")


def parse_expr(text: str) -> Node:
    result = _parse_character([text], None, False)
    exprs = result.expr[0] if result.expr else []
    if len(exprs) != 1:
        raise ParseError(f"expected one expression, got {len(exprs)}")
    return exprs[0]


def _parse_connection(handle, filename, allow_error: bool) -> ParseResult:
    opened = False
    if getattr(handle, "closed", False):
        raise ValueError("connection is closed")
    text = handle.read()
    if opened:
        handle.close()
    name = filename or getattr(handle, "name", None) or ""
    lines = text.splitlines()
    return _parse_character(lines, name, allow_error)


def _function_body(fn):
    source = inspect.getsource(fn)
    lines = source.splitlines()
    header = 0
    while header < len(lines) and not lines[header].rstrip().endswith(":"):
        header += 1
    body = lines[header + 1 :]
    if not body:
        rest = lines[header].split(":", 1)[1].strip()
        return rest
    dedented = textwrap.dedent("\n".join(body)).splitlines()
    if dedented == ["pass"]:
        return []
    return dedented


def _parse_character(chars: list[str], filename: str | None, allow_error: bool) -> ParseResult:
    lines = _to_lines(chars)
    try:
        exprs = _parse_lines(lines)
    except ParseError as exc:
        if not allow_error:
            raise
        src = "\n".join(lines)
        return ParseResult([(src, [])], error=exc)
    rows = _assemble(lines, exprs)
    return ParseResult(rows)


def _to_lines(chars: list[str]) -> list[str]:
    if any("\n" in item for item in chars):
        expanded = ["\n" if item == "" else item for item in chars]
        lines: list[str] = []
        for item in expanded:
            lines.extend(_r_strsplit(item))
        return lines
    return list(chars)


def _r_strsplit(text: str) -> list[str]:
    parts = text.split("\n")
    if text.endswith("\n"):
        parts = parts[:-1]
    return parts


def _assemble(lines: list[str], exprs: list[Node]) -> list[tuple[str, list]]:
    n = len(lines)
    groups = _group(exprs)
    tles = []
    for group in groups:
        start = group[0].start
        end = group[-1].end
        src = "\n".join(lines[start - 1 : end])
        tles.append((start, src, group))
    gaps = _gap_lines([(expr.start, expr.end) for expr in exprs], n)
    comments = [(line, lines[line - 1], []) for line in gaps]
    rows = tles + comments
    rows.sort(key=lambda item: item[0])
    finished = []
    for _line, src, group in rows:
        finished.append((src + "\n", group))
    return finished


def _group(exprs: list[Node]) -> list[list[Node]]:
    if not exprs:
        return []
    groups: list[list[Node]] = []
    current: list[Node] = []
    for index, expr in enumerate(exprs):
        fresh = index == 0 or expr.start != exprs[index - 1].end
        if fresh and current:
            groups.append(current)
            current = []
        current.append(expr)
    if current:
        groups.append(current)
    return groups


def _gap_lines(spans: list[tuple[int, int]], n: int) -> list[int]:
    starts = [1] + [end + 1 for _start, end in spans]
    ends = [start - 1 for start, _end in spans] + [n]
    lines: list[int] = []
    for start, end in zip(starts, ends):
        if start <= end:
            lines.extend(range(start, end + 1))
    return lines


def _parse_lines(lines: list[str]) -> list[Node]:
    tokens = _tokenize("\n".join(lines) if lines else "")
    parser = _Parser(tokens, lines)
    return parser.parse_top()


def _tokenize(text: str) -> list[Tok]:
    tokens: list[Tok] = []
    i = 0
    line = 1
    n = len(text)
    while i < n:
        ch = text[i]
        if ch == "\n":
            tokens.append(Tok("NL", "\n", line))
            line += 1
            i += 1
            continue
        if ch in " \t\r":
            i += 1
            continue
        if ch == "#":
            while i < n and text[i] != "\n":
                i += 1
            continue
        if ch in "\"'":
            token, i, line = _read_string(text, i, line)
            tokens.append(token)
            continue
        if ch.isdigit() or (ch == "." and i + 1 < n and text[i + 1].isdigit()):
            token, i = _read_number(text, i, line)
            tokens.append(token)
            continue
        if ch == "." and text.startswith("...", i):
            tokens.append(Tok("NAME", "...", line))
            i += 3
            continue
        if ch.isalpha() or ch in "._" or (ch.isalpha() is False and _is_name_start(ch)):
            start = i
            i += 1
            while i < n and _is_name_cont(text[i]):
                i += 1
            tokens.append(Tok("NAME", text[start:i], line))
            continue
        op, size = _read_op(text, i)
        if op is not None:
            kind = {
                "(": "LP",
                ")": "RP",
                "{": "LB",
                "}": "RB",
                "[": "LS",
                "]": "RS",
                ",": "COMMA",
                ";": "SEMI",
            }.get(op, "OP")
            tokens.append(Tok(kind, op, line))
            i += size
            continue
        raise ParseError(f"unexpected character {ch!r} on line {line}")
    tokens.append(Tok("END", "", line))
    return tokens


def _is_name_start(ch: str) -> bool:
    return ch.isalpha() or ch in "._"


def _is_name_cont(ch: str) -> bool:
    return ch.isalnum() or ch in "._"


def _read_op(text: str, i: int) -> tuple[str | None, int]:
    if text.startswith("%", i):
        end = text.find("%", i + 1)
        if end == -1:
            raise ParseError("unclosed % operator")
        return text[i : end + 1], end + 1 - i
    three = text[i : i + 3]
    if three in {"<<-", "->>"}:
        return three, 3
    two = text[i : i + 2]
    if two in {"<-", "->", "<=", ">=", "==", "!=", "&&", "||", ".."}:
        return two, 2
    one = text[i]
    if one in "(){}[],;+-*/^<>=!~:&|?$@":
        return one, 1
    return None, 0


def _read_number(text: str, i: int, line: int) -> tuple[Tok, int]:
    start = i
    while i < len(text) and text[i].isdigit():
        i += 1
    if i < len(text) and text[i] == ".":
        i += 1
        while i < len(text) and text[i].isdigit():
            i += 1
    if i < len(text) and text[i] in "eE":
        j = i + 1
        if j < len(text) and text[j] in "+-":
            j += 1
        if j < len(text) and text[j].isdigit():
            i = j + 1
            while i < len(text) and text[i].isdigit():
                i += 1
    raw = text[start:i]
    if any(ch in raw for ch in ".eE"):
        value = float(raw)
    else:
        value = int(raw)
    return Tok("NUM", raw, line), i if False else i


def _read_string(text: str, i: int, line: int) -> tuple[Tok, int, int]:
    quote = text[i]
    i += 1
    chars: list[str] = []
    while i < len(text):
        ch = text[i]
        if ch == "\n":
            line += 1
            chars.append(ch)
            i += 1
            continue
        if ch == "\\":
            i += 1
            if i >= len(text):
                break
            esc = text[i]
            chars.append({"n": "\n", "t": "\t", "r": "\r", "\\": "\\", "'": "'", '"': '"'}.get(esc, esc))
            i += 1
            continue
        if ch == quote:
            i += 1
            value = "".join(chars)
            code = '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'
            token = Tok("STR", code, line)
            token.value = value  # type: ignore[attr-defined]
            return token, i, line
        chars.append(ch)
        i += 1
    raise ParseError("unclosed string")


_INFIX = {
    "<-": (1, True),
    "<<-": (1, True),
    "=": (1, True),
    "->": (1, False),
    "->>": (1, False),
    "~": (2, False),
    "|": (3, False),
    "||": (3, False),
    "&": (4, False),
    "&&": (4, False),
    "==": (6, False),
    "!=": (6, False),
    "<": (6, False),
    ">": (6, False),
    "<=": (6, False),
    ">=": (6, False),
    "+": (10, False),
    "-": (10, False),
    "*": (20, False),
    "/": (20, False),
    ":": (30, False),
    "^": (40, True),
}


class _Parser:
    def __init__(self, tokens: list[Tok], lines: list[str]) -> None:
        self.tokens = tokens
        self.lines = lines
        self.i = 0
        self.depth = 0

    def parse_top(self) -> list[Node]:
        exprs = []
        while not self._done():
            self._skip_separators()
            if self._done():
                break
            exprs.append(self._expr(0))
            if self._peek().kind == "SEMI" and self.depth == 0:
                self._advance()
        return exprs

    def _done(self) -> bool:
        return self._peek().kind == "END"

    def _peek(self) -> Tok:
        return self.tokens[self.i]

    def _advance(self) -> Tok:
        token = self.tokens[self.i]
        self.i += 1
        return token

    def _skip_separators(self) -> None:
        while self._peek().kind in {"NL", "SEMI"}:
            self._advance()

    def _skip_nl(self) -> None:
        while self._peek().kind == "NL":
            self._advance()

    def _expr(self, min_bp: int) -> Node:
        self._skip_nl()
        token = self._peek()
        if token.kind == "END":
            self._fail()
        left = self._nud()
        while True:
            nxt = self._peek()
            if nxt.kind == "NL" and self.depth == 0:
                break
            if nxt.kind == "SEMI" and self.depth == 0:
                break
            if nxt.kind == "NL":
                self._skip_nl()
                nxt = self._peek()
            if nxt.kind == "OP" and (nxt.text in _INFIX or nxt.text.startswith("%")):
                if nxt.text.startswith("%"):
                    bp, right_assoc = 25, False
                else:
                    bp, right_assoc = _INFIX[nxt.text]
                if bp < min_bp or (bp == min_bp and not right_assoc):
                    break
                op = self._advance()
                rhs_bp = bp if right_assoc else bp + 1
                # A newline after an infix operator is still inside the expression.
                self._skip_nl()
                right_node = self._expr(rhs_bp)
                left = Binary(left.start, right_node.end, op.text, left, right_node)
                continue
            if nxt.kind == "LP":
                call = self._call(left)
                left = call
                continue
            break
        return left

    def _nud(self) -> Node:
        token = self._advance()
        if token.kind == "NUM":
            raw = token.text
            value = float(raw) if any(ch in raw for ch in ".eE") else int(raw)
            return Literal(token.line, token.line, value, raw)
        if token.kind == "STR":
            return Literal(token.line, token.line, token.value, token.text)  # type: ignore[attr-defined]
        if token.kind == "NAME":
            if token.text == "function":
                return self._function(token)
            if token.text == "if":
                return self._if(token)
            if token.text == "for":
                return self._for(token)
            return Name(token.line, token.line, token.text)
        if token.kind == "OP" and token.text in {"+", "-", "!"}:
            self._skip_nl()
            expr = self._expr(35 if token.text != "!" else 15)
            return Unary(token.line, expr.end, token.text, expr)
        if token.kind == "LP":
            self.depth += 1
            self._skip_nl()
            if self._peek().kind == "RP":
                end = self._advance()
                self.depth -= 1
                return Paren(token.line, end.line, Literal(token.line, end.line, None, "NULL"))
            expr = self._expr(0)
            self._skip_nl()
            end = self._expect("RP")
            self.depth -= 1
            return Paren(token.line, end.line, expr)
        if token.kind == "LB":
            return self._brace(token)
        self.i -= 1
        self._fail()
        raise AssertionError

    def _brace(self, opening: Tok) -> Brace:
        self.depth += 1
        body = []
        while True:
            self._skip_nl()
            if self._peek().kind == "RB":
                break
            if self._peek().kind == "END":
                self._fail()
            body.append(self._expr(0))
            if self._peek().kind == "SEMI":
                self._advance()
        end = self._expect("RB")
        self.depth -= 1
        return Brace(opening.line, end.line, body)

    def _function(self, token: Tok) -> Function:
        self._skip_nl()
        self._expect("LP")
        self.depth += 1
        params = []
        while self._peek().kind != "RP":
            self._skip_nl()
            if self._peek().kind != "NAME":
                self._fail()
            name = self._advance().text
            default = None
            if self._peek().kind == "OP" and self._peek().text == "=":
                self._advance()
                default = self._expr(0)
            params.append((name, default))
            self._skip_nl()
            if self._peek().kind == "COMMA":
                self._advance()
                continue
            break
        self._expect("RP")
        self.depth -= 1
        self._skip_nl()
        body = self._expr(0)
        return Function(token.line, body.end, params, body)

    def _if(self, token: Tok) -> If:
        self._skip_nl()
        self._expect("LP")
        self.depth += 1
        cond = self._expr(0)
        self._expect("RP")
        self.depth -= 1
        self._skip_nl()
        then = self._expr(0)
        else_ = None
        saved = self.i
        self._skip_nl()
        nxt = self._peek()
        if nxt.kind == "NAME" and nxt.text == "else":
            self._advance()
            self._skip_nl()
            else_ = self._expr(0)
        else:
            self.i = saved
        end = else_.end if else_ is not None else then.end
        return If(token.line, end, cond, then, else_)

    def _for(self, token: Tok) -> For:
        self._skip_nl()
        self._expect("LP")
        self.depth += 1
        if self._peek().kind != "NAME":
            self._fail()
        var = self._advance().text
        keyword = self._peek()
        if not (keyword.kind == "NAME" and keyword.text == "in"):
            self._fail()
        self._advance()
        seq = self._expr(0)
        self._expect("RP")
        self.depth -= 1
        self._skip_nl()
        body = self._expr(0)
        return For(token.line, body.end, var, seq, body)

    def _call(self, func: Node) -> Call:
        self._expect("LP")
        self.depth += 1
        args = []
        while True:
            self._skip_nl()
            if self._peek().kind == "RP":
                break
            name = None
            if self._peek().kind == "NAME":
                look = self.tokens[self.i + 1]
                if look.kind == "OP" and look.text == "=":
                    name = self._advance().text
                    self._advance()
                    self._skip_nl()
            args.append((name, self._expr(0)))
            self._skip_nl()
            if self._peek().kind == "COMMA":
                self._advance()
                continue
            break
        end = self._expect("RP")
        self.depth -= 1
        return Call(func.start, end.line, func, args)

    def _expect(self, kind: str) -> Tok:
        self._skip_nl()
        token = self._peek()
        if token.kind != kind:
            self._fail()
        return self._advance()

    def _fail(self) -> None:
        filename = "<text>"
        lines = self.lines or [""]
        n = len(lines)
        last = lines[-1]
        message = f"{filename}:{n + 1}:0: unexpected end of input\n{n}: {last}\n   ^"
        raise ParseError(message)
