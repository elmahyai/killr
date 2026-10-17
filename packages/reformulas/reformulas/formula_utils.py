"""Formula-tree utilities corresponding to reformulas 0.4.4.

The R package operates on language objects.  This port accepts formula text
and ordinary strings as the portable representation used by this repository;
call objects are also accepted when they provide a useful ``str`` rendering.
"""
from __future__ import annotations

import re
from collections import defaultdict
from typing import Any, Iterable


def _s(x: Any) -> str:
    if isinstance(x, str):
        return x.strip()
    if hasattr(x, "deparse"):
        return str(x.deparse)
    return str(x).strip()


def _rhs(x: Any) -> str:
    s = _s(x)
    return s.split("~", 1)[1].strip() if "~" in s else s


def _split_top(s: str, sep: str = "+") -> list[str]:
    out, start, depth, quote = [], 0, 0, None
    i = 0
    while i < len(s):
        c = s[i]
        if quote:
            if c == quote and (i == 0 or s[i - 1] != "\\"):
                quote = None
        elif c in "'\"":
            quote = c
        elif c in "([{":
            depth += 1
        elif c in ")]}":
            depth -= 1
        elif depth == 0 and s.startswith(sep, i):
            out.append(s[start:i].strip())
            start = i + len(sep)
            i += len(sep) - 1
        i += 1
    out.append(s[start:].strip())
    return [x for x in out if x]


def _head(s: str) -> str | None:
    m = re.match(r"^\s*([A-Za-z.][\w.]*)\s*\(", s)
    return m.group(1) if m else None


def _outer(s: str) -> str:
    s = s.strip()
    while s.startswith("(") and s.endswith(")"):
        d = 0
        ok = True
        for i, c in enumerate(s):
            d += c == "("
            d -= c == ")"
            if d == 0 and i != len(s) - 1:
                ok = False
                break
        if ok:
            s = s[1:-1].strip()
        else:
            break
    return s


def _bar(s: str) -> tuple[str, str, str] | None:
    d = 0
    for i, c in enumerate(s):
        if c in "([{":
            d += 1
        elif c in ")]}":
            d -= 1
        elif d == 0:
            if s.startswith("||", i):
                return s[:i].strip(), "||", s[i + 2:].strip()
            if c == "|":
                return s[:i].strip(), "|", s[i + 1:].strip()
    return None


def _join(xs: Iterable[str], op: str = "+") -> str:
    return op.join(x for x in xs if x != "")


def RHSForm(form: Any, as_form: bool = False) -> str:
    s = _s(form)
    if not as_form:
        return _rhs(s)
    return "~" + _rhs(s)


def addForm0(f1: Any, f2: Any) -> str:
    left = _s(f1).split("~", 1)[0].strip() if "~" in _s(f1) else ""
    rhs = _join((_rhs(f1), _rhs(f2)))
    return (left + " ~ " if left else "~") + rhs


def addForm(*forms: Any) -> str:
    if not forms:
        raise TypeError("at least one formula is required")
    result = _s(forms[0])
    for f in forms[1:]:
        result = addForm0(result, f)
    return result


def makeOp(x: Any, y: Any = None, op: Any = None) -> str:
    if op is None:
        return f"{_s(y)}({_s(x)})"
    if y is None:
        return f"{_s(op)}({_s(x)})"
    return f"{_s(x)} {_s(op)} {_s(y)}"


def sumTerms(termList: Iterable[Any]) -> str:
    return _join(_s(x) for x in termList)


def inForm(form: Any, value: Any) -> bool:
    return _s(value) in _s(form) if len(_s(value)) > 1 else bool(re.search(rf"(?<![\w.]){re.escape(_s(value))}(?![\w.])", _s(form)))


def anySpecial(term: Any, specials=("diag", "us", "cs", "ar1", "ou", "exp", "gau", "mat", "toep", "rr", "homdiag", "s"), fast: bool = False) -> bool:
    s = _s(term)
    return any(re.search(rf"(?<![\w.]){re.escape(x)}\s*\(", s) for x in specials)


def extractForm(term: Any, value: Any) -> list[str] | None:
    h = re.escape(_s(value))
    found = re.findall(rf"(?<![\w.]){h}\s*\(([^()]*(?:\([^()]*\)[^()]*)*)\)", _s(term))
    return [f"{_s(value)}({x})" for x in found] or None


def dropHead(term: Any, value: Any) -> str:
    s, v = _s(term), re.escape(_s(value))
    return re.sub(rf"(?<![\w.]){v}\s*\(([^()]*)\)", r"\1", s)


def replaceForm(term: Any, target: Any, repl: Any) -> str:
    return _s(term).replace(_s(target), _s(repl))


def sub_specials(term: Any, specials=("|", "||", "s"), keep_args=(2, 2, None)) -> str:
    s = _s(term)
    for special, keep in zip(specials, keep_args):
        if special in ("|", "||"):
            s = re.sub(r"\|\|?", "+", s)
        elif special == "s":
            s = re.sub(r"\bs\s*\(([^,()]*)[^)]*\)", r"+(\1)", s)
    return s


def subbars(term: Any) -> str:
    return sub_specials(term, ("|", "||"), (2, 2))


def no_specials(term: Any, specials=("|", "||", "s")) -> Any:
    if isinstance(term, (list, tuple)):
        return [no_specials(x, specials) for x in term]
    s = _s(term)
    for special in specials:
        m = re.match(rf"^{re.escape(special)}\s*\((.*)\)$", s)
        if m:
            return s
    return s


def noSpecials(term: Any, delete: bool = True, debug: bool = False, specials=("diag", "us", "cs", "ar1", "ou", "exp", "gau", "mat", "toep", "rr", "homdiag", "s")) -> str:
    s = _s(term)
    if not delete:
        return s
    for sp in specials:
        s = re.sub(rf"\b{re.escape(sp)}\s*\(([^()]*)\)", r"(\1)", s)
    return s


def expandGrpVar(f: Any) -> list[str]:
    s = _outer(_s(f))
    if "/" in s:
        parts = _split_top(s, "/")
        out = []
        for i in range(len(parts), 0, -1):
            p = ":".join(reversed(parts[:i]))
            out.append(p)
        return out
    if "*" in s:
        parts = _split_top(s, "*")
        return parts + [":".join(parts)]
    if "+" in s:
        return _split_top(s)
    return [s]


def expandAllGrpVar(bb: Any) -> list[str]:
    vals = bb if isinstance(bb, (list, tuple)) else [bb]
    out = []
    for raw in vals:
        s = _outer(_s(raw))
        b = _bar(s)
        if not b:
            out.append(s)
            continue
        lhs, op, rhs = b
        for g in expandGrpVar(rhs):
            out.append(f"{lhs} | {g}")
    return out


def expandDoubleVert(term: Any) -> list[str]:
    b = _bar(_outer(_s(term)))
    if not b or b[1] != "||":
        return [_s(term)]
    lhs, _, rhs = b
    pieces = _split_top(lhs)
    if "1" in pieces:
        pieces = ["1"] + [f"0 + {x}" for x in pieces if x != "1"]
    return [f"({x} | {rhs})" for x in pieces]


def expandDoubleVerts(term: Any) -> str:
    s = _s(term)
    for b in re.findall(r"\([^()]*\|\|[^()]*\)", s):
        s = s.replace(b, " + ".join(expandDoubleVert(b)))
    return s


def findbars_x(term: Any, debug: bool = False, specials=(), default_special: str | None = "us", target: str = "|", expand_doublevert_method=("diag_special", "split")) -> list[str] | None:
    s = _rhs(term)
    candidates = re.findall(r"\([^()]*\|\|?[^()]*\)", s)
    if not candidates:
        candidates = [x.strip() for x in _split_top(s) if _bar(_outer(x))]
    out = []
    for x in candidates:
        x = _outer(x)
        b = _bar(x)
        if not b:
            continue
        lhs, op, rhs = b
        if op == "||" and (expand_doublevert_method[0] if isinstance(expand_doublevert_method, (list, tuple)) else expand_doublevert_method) == "split":
            out.extend(f"{default_special}({y})" if default_special else y for y in expandDoubleVert(x))
        elif default_special:
            out.append(f"{default_special}({lhs} | {rhs})")
        else:
            out.append(f"{lhs} | {rhs}")
    return out or None


def findbars(term: Any) -> list[str] | None:
    return findbars_x(term, default_special=None, expand_doublevert_method="split")


def reOnly(f: Any, response: bool = False, bracket: bool = True, doublevert_split: bool = True) -> str:
    bars = findbars_x(f, expand_doublevert_method="split" if doublevert_split else "diag_special") or []
    rhs = _join(f"({x})" if bracket else x for x in bars)
    if response and "~" in _s(f):
        return _s(f).split("~", 1)[0].strip() + " ~ " + rhs
    return "~" + rhs


def splitForm(formula: Any, defaultTerm: str = "us", **kwargs) -> dict[str, Any]:
    bars = findbars_x(formula, specials=kwargs.get("specials", ()), default_special=defaultTerm) or []
    fixed = _s(formula)
    for b in bars:
        fixed = fixed.replace(b, "")
    fixed = re.sub(r"\+\s*\+", "+", fixed).strip()
    return {"fixedFormula": fixed, "reTrmFormulas": bars, "reTrmAddArgs": [f"{defaultTerm}()" for _ in bars], "reTrmClasses": [defaultTerm] * len(bars)}


def drop_special(x: Any, value: Any = "offset", preserve=None) -> str:
    count = 0
    def sub(m):
        nonlocal count
        count += 1
        return m.group(0) if preserve and count in preserve else ""
    return re.sub(rf"\b{re.escape(_s(value))}\s*\([^()]*\)", sub, _s(x))


drop_special.__name__ = "drop.special"
globals()["drop.special"] = drop_special


def isNested(f1: Any, f2: Any) -> bool:
    if len(f1) != len(f2):
        raise ValueError("lengths differ")
    groups = defaultdict(set)
    for a, b in zip(f1, f2):
        groups[a].add(b)
    return all(len(x) <= 1 for x in groups.values())
