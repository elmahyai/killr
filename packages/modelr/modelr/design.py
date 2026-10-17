"""Design matrices and least squares.

Character columns are factors with sorted levels. The first factor in a
model with no intercept keeps every level; later factors drop the first.
``poly(x, k)`` is the monomials x through x^k. Those columns span the same
fitted values as R's orthogonal polynomials. Predictions use the same powers.
"""

from __future__ import annotations

import math
import warnings

import numpy as np

from modelr.formula import (
    Bin,
    Call,
    Formula,
    Num,
    Sym,
    Unary,
    all_vars,
    as_formula,
    compile_rhs,
    deparse,
)
from modelr.frame import Factor, as_floats, as_frame, is_na


def na_omit(frame):
    return _drop_incomplete(frame, "omit")


def na_exclude(frame):
    return _drop_incomplete(frame, "exclude")


def na_warn(frame):
    """Drop incomplete rows and warn. Predictions keep a missing value in those rows."""
    missing = _incomplete_count(frame)
    if missing > 0:
        warnings.warn(
            f"Dropping {missing} rows with missing values",
            UserWarning,
            stacklevel=2,
        )
    return _drop_incomplete(frame, "exclude")


def model_matrix(data, formula, **_ignored):
    """Design matrix as a frame. Incomplete rows are dropped, as model.matrix drops them."""
    formula = as_formula(formula)
    frame = as_frame(data)
    names, columns, _levels = _design(frame, formula, None)
    response = _response_values(formula, frame)
    keep = []
    for i in range(frame.nrow):
        if response is not None and is_na(response[i]):
            continue
        if any(is_na(column[i]) for column in columns):
            continue
        keep.append(i)
    from modelr.frame import Frame

    return Frame({name: [column[i] for i in keep] for name, column in zip(names, columns)})


def predictor_vars(model, data=None):
    formula = model.formula if isinstance(model, Lm) else as_formula(model)
    return all_vars(formula.rhs)


def response_var(model, data=None):
    formula = model.formula if isinstance(model, Lm) else as_formula(model)
    if not isinstance(formula.lhs, Sym):
        raise ValueError("the response must be a single name")
    return formula.lhs.name


def response(model, data):
    frame = as_frame(data)
    return as_floats(frame.columns[response_var(model)])


def lm(formula, data, na_action=None, **_ignored):
    """Ordinary least squares. ``na_action`` is ``na_warn`` or ``na_exclude`` to pad predictions."""
    formula = as_formula(formula)
    frame = as_frame(data)
    kind = "omit"
    if na_action is na_warn:
        kind = "exclude"
        missing = _model_missing(formula, frame)
        if missing > 0:
            warnings.warn(
                f"Dropping {missing} rows with missing values",
                UserWarning,
                stacklevel=2,
            )
    elif na_action is na_exclude:
        kind = "exclude"
    elif na_action not in (None, na_omit):
        raise ValueError("na_action must be na_warn, na_exclude, or na_omit")
    names, columns, levels = _design(frame, formula, None)
    y = _response_values(formula, frame)
    if y is None:
        raise ValueError("the formula needs a response")
    kept_rows = []
    kept_y = []
    omitted = []
    for i in range(frame.nrow):
        if is_na(y[i]) or any(is_na(column[i]) for column in columns):
            omitted.append(i + 1)
        else:
            kept_rows.append(i)
            kept_y.append(y[i])
    if not kept_y:
        raise ValueError("0 (non-NA) cases")
    design = np.column_stack([np.asarray(column, dtype=np.float64)[kept_rows] for column in columns])
    coef, _residuals, _rank, _singular = np.linalg.lstsq(
        design, np.asarray(kept_y, dtype=np.float64), rcond=None
    )
    coefficients = {name: float(value) for name, value in zip(names, coef)}
    fitted = design @ np.asarray(coef, dtype=np.float64)
    return Lm(
        formula=formula,
        coefficients=coefficients,
        levels=levels,
        fitted=[float(value) for value in fitted],
        omitted=omitted,
        n=frame.nrow,
        kind=kind,
    )


def predict(model, data=None, type=None):
    if type not in (None, "response"):
        raise ValueError(f"prediction type {type!r} is not supported")
    if not isinstance(model, Lm):
        raise TypeError("predict() needs a model fitted by lm()")
    if data is None:
        if model.kind == "exclude":
            return _pad(model.fitted, model.n, model.omitted)
        return list(model.fitted)
    frame = as_frame(data)
    names, columns, _levels = _design(frame, model.formula, model.levels)
    if names != list(model.coefficients):
        raise ValueError("the design columns do not match the fitted model")
    coef = [model.coefficients[name] for name in names]
    out = []
    for i in range(frame.nrow):
        if any(is_na(column[i]) for column in columns):
            out.append(float("nan"))
            continue
        out.append(sum(column[i] * weight for column, weight in zip(columns, coef)))
    return out


def residuals(model, data):
    observed = response(model, data)
    fitted = predict(model, data)
    if len(observed) != len(fitted):
        raise ValueError("residuals and the response have different lengths")
    out = []
    for actual, fitted_value in zip(observed, fitted):
        if is_na(actual) or is_na(fitted_value):
            out.append(float("nan"))
        else:
            out.append(actual - fitted_value)
    return out


class Lm:
    def __init__(self, formula, coefficients, levels, fitted, omitted, n, kind):
        self.formula = formula
        self.coefficients = coefficients
        self.levels = levels
        self.fitted = fitted
        self.omitted = omitted
        self.n = n
        self.kind = kind

    def __str__(self):
        names = "  ".join(f"{name:>12}" for name in self.coefficients)
        values = "  ".join(f"{value:12.4f}" for value in self.coefficients.values())
        return f"Coefficients:\n{names}\n{values}"

    def __repr__(self):
        return str(self)


def _design(frame, formula, levels):
    intercept, terms = compile_rhs(formula)
    learned = {} if levels is None else {name: list(value) for name, value in levels.items()}
    names = []
    columns = []
    if intercept:
        names.append("(Intercept)")
        columns.append([1.0] * frame.nrow)
    seen_factor = False
    for term in terms:
        term_names, term_columns, seen_factor = _eval_term(
            term, frame, intercept, seen_factor, learned, levels is not None
        )
        names.extend(term_names)
        columns.extend(term_columns)
    return names, columns, learned


def _eval_term(term, frame, intercept, seen_factor, learned, locked):
    current = [("", [1.0] * frame.nrow)]
    for piece in term:
        kind = piece[0]
        if kind == "v":
            current, seen_factor = _apply_variable(
                current, piece[1], frame, intercept, seen_factor, learned, locked
            )
        elif kind == "poly":
            current = _multiply(current, _poly_columns(piece[1], piece[2], frame))
        elif kind == "I":
            values = _arith(piece[1], frame)
            label = "I(" + _arith_label(piece[1]) + ")"
            current = _multiply(current, [(label, values)])
        elif kind == "const":
            current = _multiply(current, [(str(piece[1]), [float(piece[1])] * frame.nrow)])
        elif kind == "bar":
            raise ValueError("random-effect terms are kept in the formula and are not fitted")
        else:
            raise ValueError(f"unsupported term {kind}")
    return [name for name, _values in current], [values for _name, values in current], seen_factor


def _apply_variable(current, name, frame, intercept, seen_factor, learned, locked):
    column = frame.columns[name]
    if isinstance(column, Factor) or _is_character(column):
        levels, values = _factor_levels(name, column, learned, locked)
        drop_first = intercept or seen_factor
        seen_factor = True
        pieces = _dummies(name, values, levels, drop_first)
        return _multiply(current, pieces), seen_factor
    return _multiply(current, [(name, as_floats(column))]), seen_factor


def _factor_levels(name, column, learned, locked):
    if isinstance(column, Factor):
        values = list(column.values)
        if name not in learned:
            if locked:
                raise ValueError(f"factor {name} was not in the fitted model")
            learned[name] = list(column.levels)
        return learned[name], values
    values = list(column)
    if name not in learned:
        if locked:
            raise ValueError(f"column {name} was not in the fitted model")
        learned[name] = sorted({value for value in values if value is not None})
    return learned[name], values


def _dummies(name, values, levels, drop_first):
    used = levels[1:] if drop_first else list(levels)
    known = set(levels)
    pieces = []
    for level in used:
        column = []
        for value in values:
            if value is None or value not in known:
                column.append(float("nan"))
            else:
                column.append(1.0 if value == level else 0.0)
        pieces.append((f"{name}{level}", column))
    return pieces


def _poly_columns(name, degree, frame):
    values = as_floats(frame.columns[name])
    pieces = []
    for power in range(1, degree + 1):
        column = [float("nan") if is_na(value) else value**power for value in values]
        pieces.append((f"poly({name}, {degree}){power}", column))
    return pieces


def _multiply(current, pieces):
    out = []
    for left_name, left_values in current:
        for right_name, right_values in pieces:
            if left_name == "":
                name = right_name
            elif right_name == "":
                name = left_name
            else:
                name = f"{left_name}:{right_name}"
            column = []
            for left, right in zip(left_values, right_values):
                if is_na(left) or is_na(right):
                    column.append(float("nan"))
                else:
                    column.append(left * right)
            out.append((name, column))
    return out


def _arith(node, frame):
    n = frame.nrow
    if isinstance(node, Num):
        return [float(node.value)] * n
    if isinstance(node, Sym):
        return as_floats(frame.columns[node.name])
    if isinstance(node, Unary) and node.op == "-":
        return [-value if not is_na(value) else float("nan") for value in _arith(node.arg, frame)]
    if isinstance(node, Bin):
        left = _arith(node.left, frame)
        right = _arith(node.right, frame)
        out = []
        for a, b in zip(left, right):
            if is_na(a) or is_na(b):
                out.append(float("nan"))
            elif node.op == "+":
                out.append(a + b)
            elif node.op == "-":
                out.append(a - b)
            elif node.op == "*":
                out.append(a * b)
            elif node.op == "/":
                out.append(a / b)
            elif node.op == "^":
                out.append(a**b)
            else:
                raise ValueError(f"I() cannot evaluate {node.op}")
        return out
    if isinstance(node, Call) and node.name in {"log", "exp", "sqrt", "abs"}:
        values = _arith(node.args[0], frame)
        fn = {"log": math.log, "exp": math.exp, "sqrt": math.sqrt, "abs": abs}[node.name]
        return [float("nan") if is_na(value) else fn(value) for value in values]
    raise ValueError("I() has an expression this translation does not evaluate")


def _arith_label(node):
    if isinstance(node, Num):
        value = node.value
        if isinstance(value, int) or (isinstance(value, float) and float(value).is_integer()):
            return str(int(value))
        return format(float(value), ".15g")
    if isinstance(node, Sym):
        return node.name
    if isinstance(node, Unary):
        return f"{node.op}{_arith_label(node.arg)}"
    if isinstance(node, Bin):
        return f"{_arith_label(node.left)} {node.op} {_arith_label(node.right)}"
    if isinstance(node, Call):
        return node.name + "(" + ", ".join(_arith_label(arg) for arg in node.args) + ")"
    return deparse(Formula(None, node))


def _response_values(formula, frame):
    if not isinstance(formula.lhs, Sym):
        return None
    column = frame.columns.get(formula.lhs.name)
    if column is None or isinstance(column, Factor):
        return None
    return as_floats(column)


def _model_missing(formula, frame):
    names, columns, _levels = _design(frame, formula, None)
    response = _response_values(formula, frame)
    missing = 0
    for i in range(frame.nrow):
        if (response is not None and is_na(response[i])) or any(is_na(column[i]) for column in columns):
            missing += 1
    return missing


def _incomplete_count(frame):
    count = 0
    for i in range(frame.nrow):
        for values in frame.columns.values():
            value = values.values[i] if isinstance(values, Factor) else values[i]
            if is_na(value):
                count += 1
                break
    return count


def _drop_incomplete(frame, kind):
    from modelr.frame import Frame

    keep = []
    omitted = []
    for i in range(frame.nrow):
        incomplete = False
        for values in frame.columns.values():
            value = values.values[i] if isinstance(values, Factor) else values[i]
            if is_na(value):
                incomplete = True
                break
        if incomplete:
            omitted.append(i + 1)
        else:
            keep.append(i + 1)
    kept = frame.subset(keep) if keep else Frame({name: [] for name in frame.names()})
    kept.na_action = (kind, omitted)
    return kept


def _is_character(column):
    if isinstance(column, Factor) or not column:
        return False
    return all(value is None or isinstance(value, str) for value in column)


def _pad(values, n, omitted):
    missing = set(omitted)
    out = []
    cursor = 0
    for i in range(1, n + 1):
        if i in missing:
            out.append(float("nan"))
        else:
            out.append(values[cursor])
            cursor += 1
    return out
