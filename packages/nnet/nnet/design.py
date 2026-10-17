"""Formulas, treatment contrasts, and R's qr rank for nnet and multinom."""

from __future__ import annotations

import math
import re

import numpy as np

_TOKEN = re.compile(
    r"\s+"
    r"|cbind"
    r"|offset"
    r"|[A-Za-z.][A-Za-z0-9._]*"
    r"|[0-9]+\.[0-9]*|\.[0-9]+|[0-9]+"
    r"|\^|[:~+\-*/,()]"
)


class Factor:
    """A column with an explicit level order, matching R's factor."""

    def __init__(self, values, levels=None):
        self.values = [_label(v) for v in values]
        if levels is None:
            self.levels = sorted({v for v in self.values if v is not None})
        else:
            self.levels = [_label(v) for v in levels]


def _label(value):
    if _missing(value):
        return None
    return str(value)


def _missing(value):
    if value is None:
        return True
    if isinstance(value, float) and math.isnan(value):
        return True
    if isinstance(value, np.floating) and np.isnan(value):
        return True
    return False


def _r_number(value):
    value = float(value)
    if math.isfinite(value) and value == math.trunc(value) and abs(value) < 2**53:
        return str(int(value))
    text = format(value, ".15g")
    return text


class _Num:
    def __init__(self, value):
        self.value = value


class _Sym:
    def __init__(self, name):
        self.name = name


class _Call:
    def __init__(self, name, args):
        self.name = name
        self.args = args


class _Unary:
    def __init__(self, op, arg):
        self.op = op
        self.arg = arg


class _Bin:
    def __init__(self, op, left, right):
        self.op = op
        self.left = left
        self.right = right


def _tokens(text):
    parts = []
    for match in _TOKEN.finditer(text):
        piece = match.group(0)
        if piece.strip():
            parts.append(piece)
    if not parts:
        raise ValueError(f"cannot parse formula {text}")
    return parts


class _Parser:
    def __init__(self, tokens):
        self.tokens = tokens
        self.index = 0

    def peek(self):
        if self.index >= len(self.tokens):
            return None
        return self.tokens[self.index]

    def take(self):
        token = self.peek()
        self.index += 1
        return token

    def parse(self):
        if self.peek() == "~":
            self.take()
            left = None
        else:
            left = self.union()
            if self.take() != "~":
                raise ValueError("formula has no ~")
        right = self.union()
        if self.peek() is not None:
            raise ValueError(f"unexpected formula text near {self.peek()!r}")
        return left, right

    def union(self):
        if self.peek() == "-":
            self.take()
            node = _Unary("-", self.product())
        else:
            if self.peek() == "+":
                self.take()
            node = self.product()
        while self.peek() in {"+", "-"}:
            op = self.take()
            node = _Bin(op, node, self.product())
        return node

    def product(self):
        node = self.colon()
        while self.peek() == "*":
            self.take()
            node = _Bin("*", node, self.colon())
        return node

    def colon(self):
        node = self.power()
        while self.peek() == ":":
            self.take()
            node = _Bin(":", node, self.power())
        return node

    def power(self):
        node = self.primary()
        if self.peek() == "^":
            self.take()
            power = self.primary()
            node = _Bin("^", node, power)
        return node

    def primary(self):
        token = self.take()
        if token is None:
            raise ValueError("formula ended early")
        if token == "(":
            node = self.union()
            if self.take() != ")":
                raise ValueError("formula is missing )")
            return node
        if token in {"cbind", "offset"}:
            if self.take() != "(":
                raise ValueError(f"{token} needs parentheses")
            args = [self.union()]
            while self.peek() == ",":
                self.take()
                args.append(self.union())
            if self.take() != ")":
                raise ValueError(f"{token} is missing )")
            return _Call(token, args)
        if re.fullmatch(r"[0-9]+\.[0-9]*|\.[0-9]+|[0-9]+", token):
            return _Num(float(token))
        if re.fullmatch(r"[A-Za-z.][A-Za-z0-9._]*", token):
            return _Sym(token)
        raise ValueError(f"cannot parse formula token {token!r}")


def _response_names(node):
    if node is None:
        return []
    if isinstance(node, _Sym):
        return [node.name]
    if isinstance(node, _Call) and node.name == "cbind":
        names = []
        for arg in node.args:
            if not isinstance(arg, _Sym):
                raise ValueError("cbind() in a formula needs column names")
            names.append(arg.name)
        return names
    raise ValueError("formula response must be a name or cbind()")


def _is_one(node):
    return isinstance(node, _Num) and node.value == 1


def _is_zero(node):
    return isinstance(node, _Num) and node.value == 0


class _Spec:
    def __init__(self, data_names, response):
        self.data_names = list(data_names)
        self.response = list(response)
        self.intercept = True
        self.terms = []
        self.seen = []
        self.offsets = []

    def see(self, name):
        if name not in self.seen:
            self.seen.append(name)

    def term(self, names):
        for name in names:
            self.see(name)
        ordered = tuple(sorted(set(names), key=self.seen.index))
        return ordered

    def expand(self, node):
        if isinstance(node, _Num):
            return []
        if isinstance(node, _Sym):
            if node.name == ".":
                names = [
                    name
                    for name in self.data_names
                    if name not in self.response and name not in self.offsets
                ]
                return [self.term((name,)) for name in names]
            return [self.term((node.name,))]
        if isinstance(node, _Call) and node.name == "offset":
            if len(node.args) != 1 or not isinstance(node.args[0], _Sym):
                raise ValueError("offset() needs one column name")
            self.offsets.append(node.args[0].name)
            return []
        if isinstance(node, _Unary):
            return self.expand(node.arg)
        if isinstance(node, _Bin) and node.op == "*":
            left = self.expand(node.left)
            right = self.expand(node.right)
            crossed = []
            for a in left:
                for b in right:
                    crossed.append(self.term(a + b))
            return _unique(left + right + crossed)
        if isinstance(node, _Bin) and node.op == ":":
            left = self.expand(node.left)
            right = self.expand(node.right)
            return _unique([self.term(a + b) for a in left for b in right])
        if isinstance(node, _Bin) and node.op == "^":
            if not isinstance(node.right, _Num):
                raise ValueError("formula power must be a number")
            base = self.expand(node.left)
            limit = int(node.right.value)
            return _power(base, limit, self)
        if isinstance(node, _Bin) and node.op in {"+", "-"}:
            return _unique(self.expand(node.left) + self.expand(node.right))
        raise ValueError("cannot expand this formula")

    def apply(self, node, sign):
        if _is_one(node) or (isinstance(node, _Unary) and _is_one(node.arg)):
            self.intercept = sign > 0
            return
        if _is_zero(node) or (isinstance(node, _Unary) and _is_zero(node.arg)):
            self.intercept = sign < 0
            return
        if isinstance(node, _Unary) and node.op == "-":
            self.apply(node.arg, -sign)
            return
        for term in self.expand(node):
            if sign > 0:
                if term not in self.terms:
                    self.terms.append(term)
            elif term in self.terms:
                self.terms.remove(term)

    def walk(self, node):
        if isinstance(node, _Bin) and node.op in {"+", "-"}:
            self.walk(node.left)
            self.apply(node.right, 1 if node.op == "+" else -1)
            return
        if isinstance(node, _Unary) and node.op == "-":
            self.apply(node.arg, -1)
            return
        self.apply(node, 1)

    def finish(self):
        def key(term):
            return (len(term), tuple(self.seen.index(name) for name in term))

        self.terms.sort(key=key)


def _unique(terms):
    result = []
    for term in terms:
        if term not in result:
            result.append(term)
    return result


def _power(base, limit, spec):
    if limit < 1:
        raise ValueError("formula power must be at least 1")
    variables = []
    for term in base:
        for name in term:
            if name not in variables:
                variables.append(name)
    chosen = []
    for mask in range(1, 2 ** len(variables)):
        names = [variables[i] for i in range(len(variables)) if mask & (1 << i)]
        if len(names) <= limit:
            chosen.append(spec.term(tuple(names)))
    return _unique(chosen)


def _column_dict(data):
    if isinstance(data, dict):
        return data
    raise TypeError("data must be a dict of columns")


def _kind(values):
    if isinstance(values, Factor):
        return "factor"
    array = np.asarray(values)
    if array.dtype.kind == "b":
        return "numeric"
    if array.dtype.kind in "iuf":
        return "numeric"
    return "factor"


def _factor_of(values):
    if isinstance(values, Factor):
        return values
    array = np.asarray(values, dtype=object)
    if array.dtype.kind in "iuf":
        labels = [_r_number(v) if not _missing(v) else None for v in array.tolist()]
        levels = sorted({label for label in labels if label is not None}, key=_level_key)
        return Factor(labels, levels)
    return Factor([None if _missing(v) else v for v in array.tolist()])


def _level_key(label):
    try:
        return (0, float(label))
    except ValueError:
        return (1, label)


def _numeric_of(values):
    if isinstance(values, Factor):
        raise ValueError("expected a numeric column")
    array = np.asarray(values, dtype=np.float64)
    return array.reshape(-1)


def _row_count(columns):
    count = None
    for values in columns.values():
        n = len(values.values) if isinstance(values, Factor) else len(values)
        if count is None:
            count = n
        elif n != count:
            raise ValueError("columns in data have different lengths")
    if count is None:
        raise ValueError("data has no columns")
    return count


def _subset_rows(n, subset):
    if subset is None:
        return list(range(n))
    values = list(subset)
    if not values:
        return []
    if all(isinstance(v, (bool, np.bool_)) for v in values):
        if len(values) != n:
            raise ValueError("subset length does not match the data")
        return [i for i, keep in enumerate(values) if bool(keep)]
    return [int(v) - 1 for v in values]


def _row_missing(columns, index, names):
    for name in names:
        values = columns[name]
        if isinstance(values, Factor):
            if values.values[index] is None:
                return True
        else:
            item = values[index]
            if _missing(item):
                return True
    return False


def _factor_columns(name, labels, levels, full):
    used = list(levels) if full else list(levels[1:])
    if not labels:
        return [], np.zeros((0, len(used)))
    columns = []
    names = []
    for level in used:
        names.append(f"{name}{level}")
        columns.append(np.array([1.0 if label == level else 0.0 for label in labels]))
    if not columns:
        return [], np.zeros((len(labels), 0))
    return names, np.column_stack(columns)


def _numeric_column(name, values):
    return [name], np.asarray(values, dtype=np.float64).reshape(-1, 1)


def _combine(parts):
    names = [""]
    matrix = None
    n = parts[0][1].shape[0]
    current = np.ones((n, 1), dtype=np.float64)
    for col_names, cols in parts:
        new_names = []
        blocks = []
        for j, col_name in enumerate(col_names):
            for i, old in enumerate(names):
                new_names.append(col_name if old == "" else f"{old}:{col_name}")
                blocks.append(current[:, i] * cols[:, j])
        names = new_names
        current = np.column_stack(blocks) if blocks else np.zeros((n, 0))
        matrix = current
    return names, matrix


def model_parts(formula, data, weights=None, subset=None, na_action="na.omit"):
    """Design matrix the way model.matrix builds it, intercept included."""
    text = str(formula).strip()
    left, right = _Parser(_tokens(text)).parse()
    columns = _column_dict(data)
    response = _response_names(left)
    spec = _Spec(list(columns), response)
    spec.walk(right)
    spec.finish()
    n = _row_count(columns)
    rows = _subset_rows(n, subset)
    if isinstance(weights, str):
        weight_values = _numeric_of(columns[weights])
    elif weights is None:
        weight_values = np.ones(n, dtype=np.float64)
    else:
        weight_values = np.asarray(weights, dtype=np.float64).reshape(-1)
        if weight_values.shape[0] != n:
            raise ValueError("weights have a different length from the data")
    needed = list(response)
    for term in spec.terms:
        for name in term:
            if name not in needed:
                needed.append(name)
    for name in spec.offsets:
        if name not in needed:
            needed.append(name)
    for name in needed:
        if name not in columns:
            raise ValueError(f"object '{name}' not found")
    kept = []
    for index in rows:
        if _row_missing(columns, index, needed) or _missing(weight_values[index]):
            if na_action in {"na.fail", "fail"}:
                raise ValueError("missing values in object")
            continue
        kept.append(index)
    if isinstance(left, _Call) and left.name == "cbind":
        y_kind = "matrix"
        y_values = np.column_stack([_numeric_of(columns[name])[kept] for name in response])
        y_levels = None
    else:
        raw = columns[response[0]]
        if _kind(raw) == "factor":
            factor = _factor_of(raw)
            y_kind = "factor"
            y_values = [factor.values[i] for i in kept]
            y_levels = list(factor.levels)
        else:
            y_kind = "numeric"
            y_values = _numeric_of(raw)[kept]
            y_levels = None
    kinds = {}
    prepared = {}
    for name in {name for term in spec.terms for name in term}:
        raw = columns[name]
        if _kind(raw) == "factor":
            factor = _factor_of(raw)
            kinds[name] = "factor"
            prepared[name] = ([factor.values[i] for i in kept], list(factor.levels))
        else:
            kinds[name] = "numeric"
            prepared[name] = _numeric_of(raw)[kept]
    term_set = set(spec.terms)
    gave_full = spec.intercept
    blocks = []
    names = []
    if spec.intercept:
        blocks.append(np.ones(len(kept), dtype=np.float64))
        names.append("(Intercept)")
    for term in spec.terms:
        parts = []
        if len(term) == 1:
            name = term[0]
            if kinds[name] == "factor":
                labels, levels = prepared[name]
                full = not gave_full
                if full:
                    gave_full = True
                col_names, cols = _factor_columns(name, labels, levels, full)
            else:
                col_names, cols = _numeric_column(name, prepared[name])
            parts.append((col_names, cols))
        else:
            for name in term:
                if kinds[name] != "factor":
                    parts.append(_numeric_column(name, prepared[name]))
                    continue
                marginal = tuple(other for other in term if other != name)
                full = marginal not in term_set
                labels, levels = prepared[name]
                parts.append((*_factor_columns(name, labels, levels, full),))
        col_names, cols = _combine(parts)
        for col_name, column in zip(col_names, cols.T):
            names.append(col_name)
            blocks.append(column)
    if blocks:
        design = np.column_stack(blocks)
    else:
        design = np.zeros((len(kept), 0), dtype=np.float64)
    offset = None
    if spec.offsets:
        offset = np.column_stack([_numeric_of(columns[name])[kept] for name in spec.offsets])
        if offset.shape[1] == 1:
            offset = offset.reshape(-1)
    return {
        "x": design,
        "names": names,
        "y_kind": y_kind,
        "y": y_values,
        "levels": y_levels,
        "weights": weight_values[kept],
        "offset": offset,
        "intercept": spec.intercept,
        "terms": spec.terms,
    }


def qr_rank(x, tol=1e-7):
    """Rank from R's dqrdc2, the LINPACK rank used by qr()."""
    matrix = np.array(x, dtype=np.float64, copy=True)
    if matrix.ndim == 1:
        matrix = matrix.reshape(-1, 1)
    n, p = matrix.shape
    if n == 0 or p == 0:
        return 0
    qraux = [0.0] * p
    work1 = [0.0] * p
    work2 = [0.0] * p
    for j in range(p):
        qraux[j] = _dnrm2(matrix[:, j])
        work1[j] = qraux[j]
        work2[j] = qraux[j] if qraux[j] != 0.0 else 1.0
    lup = min(n, p)
    k = p + 1
    for col in range(lup):
        while (col + 1) < k and qraux[col] < work2[col] * tol:
            block = matrix[:, col:p].copy()
            matrix[:, col : p - 1] = block[:, 1:]
            matrix[:, p - 1] = block[:, 0]
            saved_q, saved_1, saved_2 = qraux[col], work1[col], work2[col]
            for j in range(col, p - 1):
                qraux[j] = qraux[j + 1]
                work1[j] = work1[j + 1]
                work2[j] = work2[j + 1]
            qraux[p - 1] = saved_q
            work1[p - 1] = saved_1
            work2[p - 1] = saved_2
            k -= 1
        if (col + 1) != n:
            nrmxl = _dnrm2(matrix[col:, col])
            if nrmxl != 0.0:
                pivot = float(matrix[col, col])
                if pivot != 0.0:
                    nrmxl = math.copysign(nrmxl, pivot)
                matrix[col:, col] = matrix[col:, col] / nrmxl
                matrix[col, col] = 1.0 + float(matrix[col, col])
                if p >= col + 2:
                    for j in range(col + 1, p):
                        dot = _ddot(matrix[col:, col], matrix[col:, j])
                        scale = -dot / float(matrix[col, col])
                        matrix[col:, j] = matrix[col:, j] + scale * matrix[col:, col]
                        if qraux[j] != 0.0:
                            entry = abs(float(matrix[col, j])) / qraux[j]
                            tt = 1.0 - entry * entry
                            if tt < 0.0:
                                tt = 0.0
                            if abs(tt) >= 1e-6:
                                qraux[j] = qraux[j] * math.sqrt(tt)
                            else:
                                qraux[j] = _dnrm2(matrix[col + 1 :, j])
                                work1[j] = qraux[j]
                qraux[col] = float(matrix[col, col])
                matrix[col, col] = -nrmxl
    return int(min(k - 1, n))


def _dnrm2(values):
    scale = 0.0
    ssq = 1.0
    for value in values:
        value = float(value)
        if value != 0.0:
            absxi = abs(value)
            if scale < absxi:
                ratio = scale / absxi
                ssq = 1.0 + ssq * ratio * ratio
                scale = absxi
            else:
                ratio = absxi / scale
                ssq = ssq + ratio * ratio
    return scale * math.sqrt(ssq)


def _ddot(left, right):
    total = 0.0
    for a, b in zip(left, right):
        total += float(a) * float(b)
    return total
