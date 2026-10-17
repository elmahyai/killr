"""Convert WinBUGS dput data files to JAGS dump format.

Translated from coda 0.19-4.1 ``bugs2jags`` in ``R/jags.R``.
"""

from __future__ import annotations

import re
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import numpy as np

_TOKEN_RE = re.compile(
    r"""
    (?P<WS>\s+)
    | (?P<LPAREN>\()
    | (?P<RPAREN>\))
    | (?P<COMMA>,)
    | (?P<EQ>=)
    | (?P<COLON>:)
    | (?P<STRING>"([^"\\]|\\.)*")
    | (?P<INTL>\d+L)
    | (?P<NUMBER>(?:\d+\.\d*|\d+\.|\.\d+|\d+)(?:[eE][+-]?\d+)?)
    | (?P<IDENT>[A-Za-z.][A-Za-z0-9._]*)
    """,
    re.VERBOSE,
)


class _ParseError(ValueError):
    pass


class _Parser:
    def __init__(self, text: str) -> None:
        self._tokens = list(_tokenize(text))
        self._pos = 0

    def _peek(self) -> tuple[str, str] | None:
        while self._pos < len(self._tokens):
            kind, value = self._tokens[self._pos]
            if kind != "WS":
                return kind, value
            self._pos += 1
        return None

    def _accept(self, kind: str) -> str | None:
        tok = self._peek()
        if tok is not None and tok[0] == kind:
            self._pos += 1
            return tok[1]
        return None

    def _expect(self, kind: str) -> str:
        tok = self._peek()
        if tok is None or tok[0] != kind:
            raise _ParseError(f"expected {kind}")
        self._pos += 1
        return tok[1]

    def parse(self) -> Any:
        expr = self._expr()
        if self._peek() is not None:
            raise _ParseError("trailing input")
        return expr

    def _expr(self) -> Any:
        left = self._primary()
        if self._accept("COLON") is not None:
            right = self._primary()
            if not isinstance(left, (int, np.integer)) or not isinstance(
                right, (int, np.integer)
            ):
                raise _ParseError("sequence bounds must be integers")
            start = int(left)
            end = int(right)
            if start <= end:
                return np.arange(start, end + 1, dtype=np.int64)
            return np.arange(start, end - 1, -1, dtype=np.int64)
        return left

    def _primary(self) -> Any:
        tok = self._peek()
        if tok is None:
            raise _ParseError("unexpected end of input")
        kind, value = tok
        if kind == "INTL":
            self._pos += 1
            return np.int64(value[:-1])
        if kind == "NUMBER":
            self._pos += 1
            if "." in value or "e" in value.lower():
                return float(value)
            return np.int64(value)
        if kind == "STRING":
            self._pos += 1
            return bytes(value[1:-1], "utf-8").decode("unicode_escape")
        if kind == "IDENT":
            self._pos += 1
            if self._accept("LPAREN") is not None:
                return self._call(value)
            return value
        if kind == "LPAREN":
            self._pos += 1
            items: list[Any] = []
            if self._accept("RPAREN") is None:
                while True:
                    items.append(self._expr())
                    if self._accept("COMMA") is None:
                        break
                self._expect("RPAREN")
            return items
        raise _ParseError(f"unexpected token {kind}")

    def _call(self, name: str) -> Any:
        args: list[Any] = []
        kwargs: dict[str, Any] = {}
        if self._accept("RPAREN") is None:
            while True:
                tok = self._peek()
                if tok is not None and tok[0] == "IDENT" and self._pos + 1 < len(
                    self._tokens
                ):
                    nxt = self._tokens[self._pos + 1]
                    if nxt[0] == "EQ":
                        key = tok[1]
                        self._pos += 1
                        self._expect("EQ")
                        kwargs[key] = self._expr()
                        if self._accept("COMMA") is None:
                            break
                        continue
                args.append(self._expr())
                if self._accept("COMMA") is None:
                    break
            self._expect("RPAREN")
        if name == "list":
            if kwargs:
                return kwargs
            if len(args) == 1 and isinstance(args[0], dict):
                return args[0]
            raise _ParseError("list() expects named arguments")
        if name == "c":
            flat: list[Any] = []
            for arg in args:
                if isinstance(arg, np.ndarray):
                    flat.extend(arg.ravel(order="C").tolist())
                elif isinstance(arg, list):
                    flat.extend(arg)
                else:
                    flat.append(arg)
            return _RVector(np.asarray(flat, dtype=np.float64))
        if name == "structure":
            data = args[0] if args else kwargs.get("data")
            dim = kwargs.get("dim")
            if dim is None and len(args) > 1:
                dim = args[1]
            if data is None or dim is None:
                raise _ParseError("structure() needs data and dim")
            if isinstance(data, _RVector):
                data = data.values
            if isinstance(dim, np.ndarray):
                shape = tuple(int(x) for x in dim.ravel(order="C"))
            elif isinstance(dim, _RVector):
                shape = tuple(int(x) for x in dim.values)
            elif isinstance(dim, (list, tuple)):
                shape = tuple(int(x) for x in dim)
            else:
                shape = (int(dim),)
            arr = np.asarray(data, dtype=np.float64).ravel(order="C")
            if arr.size != int(np.prod(shape)):
                raise _ParseError("structure data length does not match dim")
            return np.reshape(arr, shape, order="F")
        raise _ParseError(f"unsupported call {name}()")


class _RVector:
    """One-dimensional R vector (``dim`` is NULL, not an array)."""

    __slots__ = ("values",)

    def __init__(self, values: np.ndarray) -> None:
        self.values = np.asarray(values, dtype=np.float64).ravel()


def _tokenize(text: str) -> Iterator[tuple[str, str]]:
    pos = 0
    while pos < len(text):
        match = _TOKEN_RE.match(text, pos)
        if not match:
            raise _ParseError(f"invalid syntax at {pos!r}")
        kind = match.lastgroup
        assert kind is not None
        value = match.group(kind)
        if kind != "WS":
            yield kind, value
        pos = match.end()


def _dget(path: str | Path) -> dict[str, Any]:
    text = Path(path).read_text(encoding="utf-8")
    parsed = _Parser(text).parse()
    if not isinstance(parsed, dict):
        raise _ParseError("dput file must evaluate to a list")
    return parsed


def _reorder_array(arr: np.ndarray) -> np.ndarray:
    if arr.ndim == 0:
        return arr
    rev_shape = tuple(reversed(arr.shape))
    reinterpret = arr.reshape(rev_shape, order="F")
    perm = tuple(reversed(range(reinterpret.ndim)))
    out = np.transpose(reinterpret, perm)
    return np.asfortranarray(out)


def _deparse_value(value: Any) -> list[str]:
    if isinstance(value, _RVector):
        data = value.values
        if data.size == 0:
            return ["c()"]
        parts = [_format_number(float(x)) for x in data]
        return _wrap_c(parts)
    if isinstance(value, (int, np.integer)):
        return [f"{int(value)}L"]
    if isinstance(value, (float, np.floating)):
        return [_format_number(float(value))]
    if isinstance(value, np.ndarray):
        if value.ndim == 0:
            return _deparse_value(value.item())
        flat = value.ravel(order="F")
        parts = [_format_number(float(x)) for x in flat]
        dim_parts = [f"{d}L" for d in value.shape]
        body = _wrap_c(parts)
        if len(body) == 1:
            return [f"structure({body[0]}, dim = c({', '.join(dim_parts)}))"]
        lines = [f"structure({body[0]}"]
        lines.extend(body[1:-1])
        lines.append(f"{body[-1]}, dim = c({', '.join(dim_parts)}))")
        return lines
    raise TypeError(f"unsupported value type {type(value)!r}")


def _format_number(x: float) -> str:
    if np.isfinite(x) and float(int(x)) == x and abs(x) < 1e15:
        return f"{int(x)}L"
    text = repr(float(x))
    if "e" in text.lower():
        return f"{float(x):.17g}"
    return text


def _wrap_c(parts: list[str]) -> list[str]:
    if not parts:
        return ["c()"]
    lines: list[str] = []
    current = "c(" + parts[0]
    for part in parts[1:]:
        candidate = current + ", " + part
        if len(candidate) > 60:
            lines.append(current + ",")
            current = part
        else:
            current = candidate
    lines.append(current + ")")
    return lines


def _dump(names: list[str], data: dict[str, Any], path: str | Path) -> None:
    lines: list[str] = []
    for name in names:
        lines.append(f"{name} <-")
        lines.extend(_deparse_value(data[name]))
    Path(path).write_text("\n".join(lines) + "\n", encoding="utf-8")


def bugs2jags(infile: str | Path, outfile: str | Path) -> None:
    """Convert a WinBUGS dput file to JAGS dump format."""
    bugs_dat = _dget(infile)
    for name in bugs_dat:
        value = bugs_dat[name]
        if isinstance(value, np.ndarray) and value.ndim > 0:
            bugs_dat[name] = _reorder_array(value)
        elif isinstance(value, np.ndarray) and value.ndim == 0:
            bugs_dat[name] = value.item()
    _dump(list(bugs_dat.keys()), bugs_dat, outfile)


def _load_dump(path: str | Path) -> dict[str, Any]:
    """Read a JAGS dump file produced by ``bugs2jags``."""
    lines = Path(path).read_text(encoding="utf-8").splitlines()
    env: dict[str, Any] = {}
    idx = 0
    while idx < len(lines):
        line = lines[idx]
        if line.endswith(" <-"):
            name = line[:-3]
            idx += 1
            expr_lines: list[str] = []
            while idx < len(lines) and not lines[idx].endswith(" <-"):
                expr_lines.append(lines[idx])
                idx += 1
            env[name] = _Parser("\n".join(expr_lines).strip()).parse()
        else:
            idx += 1
    return env
