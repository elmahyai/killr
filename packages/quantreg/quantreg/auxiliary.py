"""Auxiliary routines of quantreg 6.1: stepfun, rearrange, rqs.fit, untangle.specials.

rqs.fit calls the Barrodale-Roberts Fortran loop once per column of y. Here
each column is the HiGHS point estimate that rq_fit_br returns. The Fortran
warning flags are not reproduced.

R's stepfun records whether right was written as the literal TRUE in its
call. rearrange reads that record, not the value. Here call_right defaults to
right, and rearrange outputs call_right=False, as R's `stepfun(x, y, right =
right)` call does.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from quantreg.fit import rq_fit_br


def _approx_constant(v, x, y, f, ylow, yhigh):
    """R's approx1 with method constant: the bisection and interpolation of stats."""
    if np.isnan(v):
        return np.nan
    n = len(x)
    i = 0
    j = n - 1
    if v < x[i]:
        return ylow
    if v > x[j]:
        return yhigh
    while i < j - 1:
        ij = (i + j) // 2
        if v < x[ij]:
            j = ij
        else:
            i = ij
    if v == x[j]:
        return y[j]
    if v == x[i]:
        return y[i]
    f1 = 1.0 - f
    f2 = f
    return (y[i] * f1 if f1 != 0.0 else 0.0) + (y[j] * f2 if f2 != 0.0 else 0.0)


class StepFun:
    """R stepfun: knots x (sorted, repeats kept) and values y, one longer than x."""

    def __init__(self, x, y, right=False, call_right=None):
        knots = np.asarray(x, dtype=float).reshape(-1)
        values = np.asarray(y, dtype=float).reshape(-1)
        if knots.size and np.any(np.diff(knots) < 0):
            raise ValueError("stepfun: 'x' must be ordered increasingly")
        n = knots.size
        if n < 1:
            raise ValueError("'x' must have length >= 1")
        if values.size != n + 1:
            raise ValueError("'y' must be one longer than 'x'")
        self.right = bool(right)
        self.call_right = self.right if call_right is None else bool(call_right)
        self.x = knots
        self.y_used = values[:-1] if self.right else values[1:]
        self.yleft = values[0]
        self.yright = values[-1]
        self.f = 1.0 if self.right else 0.0

    def __call__(self, v):
        points = np.asarray(v, dtype=float)
        flat = points.reshape(-1)
        out = np.array(
            [_approx_constant(t, self.x, self.y_used, self.f, self.yleft, self.yright) for t in flat],
            dtype=float,
        )
        return out.reshape(points.shape)


def stepfun(x, y, right=False, call_right=None):
    """R stepfun(x, y, right = right)."""
    return StepFun(x, y, right=right, call_right=call_right)


def knots(f):
    """R knots.stepfun: the sorted knots."""
    return f.x.copy()


def rearrange(f, xmin=None, xmax=None):
    """R rearrange: the monotone rearrangement of a stepfun, or of each stepfun in a list."""
    if isinstance(f, (list, tuple)):
        return [rearrange(g) for g in f]
    if not isinstance(f, StepFun):
        raise ValueError("Only stepfuns can be rearranged.")
    right = f.call_right
    x = knots(f)
    n = len(x)
    xmin = x[0] if xmin is None else xmin
    xmax = x[n - 1] if xmax is None else xmax
    x = x[(x >= xmin) & (x <= xmax)]
    x = np.concatenate([[xmin], x, [xmax]])
    n = len(x)
    y = f(x)
    if right:
        o = np.argsort(y[1:], kind="stable") + 2
    else:
        o = np.argsort(y[:-1], kind="stable") + 1
    diffs = np.diff(x)
    steps = diffs[o - int(right) - 1]
    # R's cumsum adds in long double, so the running sum is kept in longdouble here.
    new_x = np.cumsum(np.concatenate([[x[0]], steps]).astype(np.longdouble)).astype(float)
    sorted_y = y[o - 1]
    new_y = np.concatenate([[sorted_y[0]], sorted_y, [sorted_y.max()]])
    return StepFun(new_x, new_y, right=right, call_right=False)


def rqs_fit(x, y, tau=0.5, tol=0.0001):
    """R rqs.fit: one regression quantile per column of y, returned one row per column."""
    del tol
    design = np.asarray(x, dtype=float)
    if design.ndim == 1:
        design = design.reshape(-1, 1)
    responses = np.asarray(y, dtype=float)
    if responses.ndim == 1:
        raise ValueError("y must have one column per response")
    rows = []
    for column in range(responses.shape[1]):
        rows.append(rq_fit_br(design, responses[:, column], tau=tau)["coefficients"])
    return np.array(rows, dtype=float)


@dataclass
class Terms:
    """The parts of an R terms object that untangle.specials reads."""

    variables: list
    factor: np.ndarray
    order: np.ndarray
    specials: dict = field(default_factory=dict)
    term_labels: list = field(default_factory=list)


def _split_top_level(text, separator):
    parts, depth, current = [], 0, ""
    for ch in text:
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        if ch == separator and depth == 0:
            parts.append(current)
            current = ""
        else:
            current += ch
    parts.append(current)
    return parts


def terms_additive(formula, specials=()):
    """Build the subset of an R ``terms`` object used by ``untangle.specials``.

    Despite its historical name, this handles the formula operators needed to
    describe main effects, interactions, nesting, and powers.  Variables are
    retained in first-seen order, while each factor column records the
    variables participating in that term.
    """
    text = str(formula).replace(" ", "")
    if "~" not in text:
        raise ValueError("formula has no ~")
    response, right = text.split("~", 1)
    variables = [response]
    variable_indices = {}

    def atom_index(name):
        if name not in variable_indices:
            variable_indices[name] = len(variables)
            variables.append(name)
        return variable_indices[name]

    def unique(items):
        out = []
        seen = set()
        for item in items:
            key = frozenset(item)
            if key not in seen:
                seen.add(key)
                out.append(item)
        return out

    def combine(left, right):
        out = []
        for a in left:
            for b in right:
                item = tuple(dict.fromkeys(a + b))
                if item:
                    out.append(item)
        return unique(out)

    def matching_outer_parentheses(value):
        if not (value.startswith("(") and value.endswith(")")):
            return False
        depth = 0
        for index, char in enumerate(value):
            if char == "(":
                depth += 1
            elif char == ")":
                depth -= 1
                if depth == 0 and index != len(value) - 1:
                    return False
        return depth == 0

    def split_operator(value, operators):
        depth = 0
        pieces = []
        start = 0
        for index, char in enumerate(value):
            if char == "(":
                depth += 1
            elif char == ")":
                depth -= 1
            elif depth == 0 and char in operators:
                pieces.append((value[start:index], char))
                start = index + 1
        if pieces:
            pieces.append((value[start:], None))
        return pieces

    def parse(value):
        while matching_outer_parentheses(value):
            value = value[1:-1]
        # Formula addition/subtraction has the lowest precedence.
        pieces = split_operator(value, "+-")
        if pieces:
            result = []
            for index, (piece, operator) in enumerate(pieces):
                if not piece:
                    continue
                parsed = parse(piece)
                if index and pieces[index - 1][1] == "-":
                    result = [term for term in result
                              if frozenset(term) not in {frozenset(x) for x in parsed}]
                else:
                    result = unique(result + parsed)
            return result
        # '*' and '/' expand into main effects and interactions.
        pieces = split_operator(value, "*/")
        if pieces:
            result = parse(pieces[0][0])
            for index, (piece, _) in enumerate(pieces[1:], start=1):
                other = parse(piece)
                operator = pieces[index - 1][1]
                if operator == "*":
                    result = unique(result + other + combine(result, other))
                else:
                    result = unique(result + combine(result, other))
            return result
        pieces = split_operator(value, ":")
        if pieces:
            result = parse(pieces[0][0])
            for piece, _ in pieces[1:]:
                result = combine(result, parse(piece))
            return result
        pieces = split_operator(value, "^")
        if pieces:
            base = parse(pieces[0][0])
            try:
                power = int(pieces[1][0])
            except (IndexError, ValueError) as exc:
                raise ValueError("formula powers must be integers") from exc
            result = []
            for term in base:
                if len(term) <= power:
                    result.append(term)
            for left in base:
                for right in base:
                    item = tuple(dict.fromkeys(left + right))
                    if 1 < len(item) <= power:
                        result.append(item)
            return unique(result)
        if value in ("", "1", "0"):
            return []
        return [(atom_index(value),)]

    parsed_terms = parse(right)
    labels = [":".join(variables[index] for index in term) for term in parsed_terms]
    factor = np.zeros((len(variables), len(parsed_terms)), dtype=float)
    for column, term in enumerate(parsed_terms):
        factor[list(term), column] = 1.0
    special_rows = {}
    for name in specials:
        special_rows[name] = [
            index + 1
            for index, variable in enumerate(variables)
            if variable.startswith(name + "(")
        ]
    return Terms(
        variables=variables,
        factor=factor,
        order=np.array([len(term) for term in parsed_terms], dtype=int),
        specials=special_rows,
        term_labels=labels,
    )


def untangle_specials(tt, special, order=1):
    """R untangle.specials: the variables of one special and the terms they enter."""
    spc = list(tt.specials.get(special, []))
    if len(spc) == 0:
        return {"vars": [], "terms": []}
    facs = np.asarray(tt.factor, dtype=float)
    ff = facs[[s - 1 for s in spc], :].sum(axis=0)
    names = [tt.variables[s - 1] for s in spc]
    orders = np.asarray(tt.order)
    orders_wanted = np.atleast_1d(np.asarray(order))
    keep = (ff != 0) & np.isin(orders, orders_wanted)
    terms = [index + 1 for index in range(len(ff)) if keep[index]]
    return {"vars": names, "terms": terms}
