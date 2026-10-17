"""Formulas, merged the way modelr merges them.

``^`` is not a square. ``x^2`` is ``x``, and ``(a + b)^2`` is ``a + b + a:b``.
``*`` is the crossing ``a + b + a:b``. Later formulas() arguments can see
earlier ones when the value is an expression string.
"""

from __future__ import annotations

import re

_TOKEN = re.compile(
    r"\s+"
    r"|(?:[0-9]+\.[0-9]*|\.[0-9]+|[0-9]+)(?:[eE][+-]?[0-9]+)?"
    r"|[A-Za-z.][A-Za-z0-9._]*"
    r"|~|\||\+|\-|\*|\/|:|\^|\(|\)|,"
)

_PREC = {"|": 2, "+": 3, "-": 3, "*": 4, "/": 4, ":": 5, "^": 6}


class Env:
    """A chain of bindings. ``parent is None`` is the empty environment."""

    def __init__(self, bindings=None, parent=None):
        self.bindings = {} if bindings is None else dict(bindings)
        self.parent = parent


DEFAULT_ENV = Env()


class Num:
    def __init__(self, value):
        self.value = value


class Sym:
    def __init__(self, name):
        self.name = name


class Call:
    def __init__(self, name, args):
        self.name = name
        self.args = list(args)


class Unary:
    def __init__(self, op, arg):
        self.op = op
        self.arg = arg


class Bin:
    def __init__(self, op, left, right):
        self.op = op
        self.left = left
        self.right = right


class Formula:
    def __init__(self, lhs, rhs, env=None):
        self.lhs = lhs
        self.rhs = rhs
        self.env = DEFAULT_ENV if env is None else env

    def __str__(self):
        return deparse(self)

    def __repr__(self):
        return f"Formula({deparse(self)})"


def deparse(formula):
    rhs = _deparse_expr(formula.rhs, 0, "left")
    if formula.lhs is None:
        return f"~{rhs}"
    return f"{_deparse_expr(formula.lhs, 0, 'left')} ~ {rhs}"


def _deparse_expr(node, parent_prec, side):
    if isinstance(node, Num):
        value = node.value
        if isinstance(value, int) or (isinstance(value, float) and value.is_integer() and abs(value) < 1e15):
            return str(int(value))
        return format(float(value), ".15g")
    if isinstance(node, Sym):
        return node.name
    if isinstance(node, Call):
        args = ", ".join(_deparse_expr(arg, 0, "left") for arg in node.args)
        return f"{node.name}({args})"
    if isinstance(node, Unary):
        arg = _deparse_expr(node.arg, 7, "right")
        return f"{node.op}{arg}"
    if isinstance(node, Bin):
        prec = _PREC[node.op]
        left = _deparse_expr(node.left, prec, "left")
        right = _deparse_expr(node.right, prec, "right")
        text = f"{left} {node.op} {right}"
        if prec < parent_prec or (prec == parent_prec and side == "right"):
            return f"({text})"
        return text
    raise TypeError(f"cannot deparse {type(node).__name__}")


def parse_formula(text):
    parser = _Parser(text)
    formula = parser.formula()
    if parser.peek() is not None:
        raise ValueError(f"unexpected formula text near {parser.peek()!r}")
    return formula


def as_formula(value):
    if isinstance(value, Formula):
        return value
    if isinstance(value, str):
        return parse_formula(value)
    raise TypeError("expected a formula")


def all_vars(node):
    found = []

    def walk(item):
        if isinstance(item, Sym):
            if item.name not in found:
                found.append(item.name)
        elif isinstance(item, Call):
            for arg in item.args:
                walk(arg)
        elif isinstance(item, Bin):
            walk(item.left)
            walk(item.right)
        elif isinstance(item, Unary):
            walk(item.arg)

    walk(node)
    return found


def find_symbols(formula):
    symbols = []
    if formula.lhs is not None:
        symbols.extend(all_vars(formula.lhs))
    symbols.extend(all_vars(formula.rhs))
    return list(dict.fromkeys(symbols))


def _find_binding_env(symbol, env):
    if env is None:
        return None
    if symbol in env.bindings:
        return env
    return _find_binding_env(symbol, env.parent)


def _find_env_conflicts(symbol, f1, f2):
    env1 = _find_binding_env(symbol, f1.env)
    env2 = _find_binding_env(symbol, f2.env)
    if env1 is None or env2 is None:
        return env1 if env1 is not None else env2
    if env1 is not env2:
        raise ValueError(
            "Cannot merge formulas as their scopes conflict for the symbol '"
            + symbol
            + "'"
        )
    return env1


def _find_env_nonconflicts(symbol, f1, f2):
    env1 = _find_binding_env(symbol, f1.env)
    env2 = _find_binding_env(symbol, f2.env)
    return env1 if env1 is not None else env2


def _reduce_common_env(envs):
    acc = envs[0]
    for env in envs[1:]:
        if env is not acc:
            raise ValueError("Cannot merge formulas as their scopes conflict across symbols")
        acc = env
    return acc


def merge_envs(f1, f2):
    symbols_f1 = find_symbols(f1)
    symbols_f2 = find_symbols(f2)
    conflict_names = [name for name in symbols_f1 if name in symbols_f2]
    conflict_set = set(conflict_names)
    envs = []
    for symbol in conflict_names:
        env = _find_env_conflicts(symbol, f1, f2)
        if env is not None:
            envs.append(env)
    for symbol in list(dict.fromkeys(symbols_f1 + symbols_f2)):
        if symbol in conflict_set:
            continue
        env = _find_env_nonconflicts(symbol, f1, f2)
        if env is not None:
            envs.append(env)
    if not envs:
        return f1.env
    return _reduce_common_env(envs)


def _same_expr(left, right):
    return _deparse_expr(left, 0, "left") == _deparse_expr(right, 0, "left")


def _reduce_common_expr(nodes):
    acc = nodes[0]
    for node in nodes[1:]:
        if not _same_expr(acc, node):
            raise ValueError("Left-hand sides must be identical")
        acc = node
    return acc


def zap_lhs(formula):
    return Formula(None, formula.rhs, formula.env)


def merge_formulas(f1, f2, fun="+"):
    rhs = Bin(fun, f1.rhs, f2.rhs)
    sides = [formula.lhs for formula in (f1, f2) if formula.lhs is not None]
    lhs = None if not sides else _reduce_common_expr(sides)
    return Formula(lhs, rhs, merge_envs(f1, f2))


def add_predictors(f, *others, fun="+"):
    """Merge right-hand sides onto ``f``. Left-hand sides in ``others`` are ignored."""
    base = as_formula(f)
    pieces = [zap_lhs(as_formula(item)) for item in (base, *others)]
    merged = pieces[0]
    for piece in pieces[1:]:
        merged = merge_formulas(merged, piece, fun)
    return Formula(base.lhs, merged.rhs, merge_envs(base, merged))


def _resolve_spec(spec, env):
    if isinstance(spec, Formula):
        return spec
    if callable(spec):
        return as_formula(spec(env))
    if isinstance(spec, str):
        text = spec.strip()
        if text.startswith("~") or "~" in text and not text.startswith("add_predictors"):
            return parse_formula(text)
        value = eval(  # noqa: S307 - sequential formula expressions are the R dots
            text,
            {"__builtins__": {}},
            {"add_predictors": add_predictors, **env},
        )
        return as_formula(value)
    raise TypeError("'...' must contain only formulas")


def formulas(response, **named):
    """Build two-sided formulas that share ``response`` as the left-hand side.

    A string that starts with ``~`` is a formula. Any other string is
    evaluated after the previous formulas have been stored, so it can call
    ``add_predictors`` on an earlier name.
    """
    response = as_formula(response)
    if response.lhs is not None:
        raise ValueError(".response must be a one-sided formula")
    if not named:
        raise ValueError("No formula provided")
    env = {}
    out = {}
    for name, spec in named.items():
        try:
            formula = _resolve_spec(spec, env)
        except TypeError:
            raise
        except ValueError as exc:
            if "formula" in str(exc).lower() or "unexpected" in str(exc).lower():
                raise ValueError("'...' must contain only formulas") from exc
            raise
        if not isinstance(formula, Formula):
            raise ValueError("'...' must contain only formulas")
        stored = Formula(response.rhs, formula.rhs, merge_envs(response, formula))
        out[name] = stored
        env[name] = stored
    return out


formulae = formulas


def fit_with(data, f, formulas, **args):
    """Fit each formula with ``f``. A dict of formulas keeps its names."""
    if isinstance(formulas, dict):
        return {name: f(formula, data=data, **args) for name, formula in formulas.items()}
    return [f(formula, data=data, **args) for formula in formulas]


def _validate_formulas_arg(spec):
    if spec is None or (not isinstance(spec, (Formula, str)) and not callable(spec)):
        raise ValueError("'...' must contain only formulas")


class _Parser:
    def __init__(self, text):
        self.tokens = [token for token in _TOKEN.findall(text) if not token.isspace()]
        self.index = 0

    def peek(self):
        if self.index >= len(self.tokens):
            return None
        return self.tokens[self.index]

    def pop(self):
        token = self.peek()
        self.index += 1
        return token

    def formula(self):
        if self.peek() == "~":
            self.pop()
            return Formula(None, self._pipe(), DEFAULT_ENV)
        left = self._pipe()
        if self.peek() != "~":
            raise ValueError("expected a formula")
        self.pop()
        return Formula(left, self._pipe(), DEFAULT_ENV)

    def _pipe(self):
        node = self._add()
        while self.peek() == "|":
            self.pop()
            node = Bin("|", node, self._add())
        return node

    def _add(self):
        node = self._mul()
        while self.peek() in {"+", "-"}:
            op = self.pop()
            node = Bin(op, node, self._mul())
        return node

    def _mul(self):
        node = self._colon()
        while self.peek() in {"*", "/"}:
            op = self.pop()
            node = Bin(op, node, self._colon())
        return node

    def _colon(self):
        node = self._pow()
        while self.peek() == ":":
            self.pop()
            node = Bin(":", node, self._pow())
        return node

    def _pow(self):
        node = self._unary()
        if self.peek() == "^":
            self.pop()
            node = Bin("^", node, self._pow())
        return node

    def _unary(self):
        if self.peek() == "-":
            # A leading minus is unary. Binary minus is handled in _add.
            nxt = self.tokens[self.index + 1] if self.index + 1 < len(self.tokens) else None
            if nxt is not None:
                self.pop()
                return Unary("-", self._unary())
        return self._primary()

    def _primary(self):
        token = self.pop()
        if token is None:
            raise ValueError("unexpected end of formula")
        if token == "(":
            node = self._pipe()
            if self.pop() != ")":
                raise ValueError("expected ')'")
            return node
        if _is_number(token):
            return Num(_number(token))
        if _is_name(token):
            if self.peek() == "(":
                self.pop()
                args = []
                if self.peek() != ")":
                    args.append(self._pipe())
                    while self.peek() == ",":
                        self.pop()
                        args.append(self._pipe())
                if self.pop() != ")":
                    raise ValueError("expected ')'")
                return Call(token, args)
            return Sym(token)
        raise ValueError(f"unexpected token {token!r}")


def _is_number(token):
    if token is None:
        return False
    return token[0].isdigit() or (token[0] == "." and len(token) > 1 and token[1].isdigit())


def _is_name(token):
    return token[:1].isalpha() or token[:1] == "."


def _number(token):
    if any(mark in token for mark in ".eE"):
        return float(token)
    return int(token)


def expand(node):
    """Turn a right-hand side into an intercept flag and a list of terms.

    A term is a tuple of pieces. A piece is ``("v", name)``, ``("poly", name, degree)``,
    ``("I", node)``, or ``("const", number)``. ``^`` keeps interactions up to
    that order. It does not square a column.
    """
    if isinstance(node, Sym):
        return _Spec(None, [(("v", node.name),)])
    if isinstance(node, Num):
        if node.value == 0:
            return _Spec(False, [])
        if node.value == 1:
            return _Spec(True, [])
        return _Spec(None, [(("const", float(node.value)),)])
    if isinstance(node, Unary):
        if node.op == "-" and isinstance(node.arg, Num) and node.arg.value == 1:
            return _Spec(False, [])
        raise ValueError("unsupported formula")
    if isinstance(node, Call):
        if node.name == "poly":
            var, degree = node.args[0], node.args[1]
            if not isinstance(var, Sym) or not isinstance(degree, Num):
                raise ValueError("poly() needs a name and a degree")
            return _Spec(None, [(("poly", var.name, int(degree.value)),)])
        if node.name == "I":
            return _Spec(None, [(("I", node.args[0]),)])
        raise ValueError(f"unsupported function {node.name}() in a formula")
    if isinstance(node, Bin):
        if node.op == "+":
            return _add_spec(expand(node.left), expand(node.right))
        if node.op == "-":
            return _sub_spec(expand(node.left), expand(node.right))
        if node.op == "*":
            return _cross_spec(expand(node.left), expand(node.right))
        if node.op == ":":
            return _colon_spec(expand(node.left), expand(node.right))
        if node.op == "^":
            if not isinstance(node.right, Num):
                raise ValueError("formula power must be a number")
            return _power_spec(expand(node.left), int(node.right.value))
        if node.op == "|":
            return _Spec(None, [(("bar", node),)])
        if node.op == "/":
            raise ValueError("nested formulas with / are not supported")
    raise ValueError("unsupported formula")


class _Spec:
    def __init__(self, intercept, terms):
        self.intercept = intercept
        self.terms = list(terms)


def _add_spec(left, right):
    intercept = left.intercept if right.intercept is None else right.intercept
    terms = list(left.terms)
    have = set(terms)
    for term in right.terms:
        if term not in have:
            terms.append(term)
            have.add(term)
    return _Spec(intercept, terms)


def _sub_spec(left, right):
    if right.intercept is True and not right.terms:
        return _Spec(False, list(left.terms))
    terms = [term for term in left.terms if term not in set(right.terms)]
    intercept = False if right.intercept is True else left.intercept
    return _Spec(intercept, terms)


def _cross_spec(left, right):
    merged = _add_spec(left, right)
    terms = list(merged.terms)
    have = set(terms)
    for a in left.terms:
        for b in right.terms:
            term = a + b
            if term not in have:
                terms.append(term)
                have.add(term)
    return _Spec(merged.intercept, terms)


def _colon_spec(left, right):
    terms = []
    have = set()
    for a in left.terms:
        for b in right.terms:
            term = a + b
            if term not in have:
                terms.append(term)
                have.add(term)
    return _Spec(None, terms)


def _power_spec(spec, degree):
    if degree < 1:
        raise ValueError("'degree' must be at least 1")
    from itertools import combinations

    terms = []
    have = set()
    for order in range(1, degree + 1):
        for combo in combinations(spec.terms, order):
            term = tuple(piece for item in combo for piece in item)
            if term not in have:
                terms.append(term)
                have.add(term)
    return _Spec(spec.intercept, terms)


def compile_rhs(formula):
    """Intercept flag and terms, main effects before interactions."""
    spec = expand(formula.rhs)
    intercept = True if spec.intercept is None else spec.intercept
    terms = sorted(spec.terms, key=_degree)
    return intercept, terms


def _degree(term):
    count = sum(1 for piece in term if piece[0] == "v")
    return count if count else 1
