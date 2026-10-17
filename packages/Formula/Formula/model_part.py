"""model.part and terms helpers for Formula objects.

From Formula 1.2-6 ``R/Formula.R`` (``model.part`` and non-dot ``terms.Formula``).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from Formula.formula import (
    Bin,
    Call,
    Formula,
    FormulaError,
    Num,
    RFormula,
    Sym,
    _deparse_expr,
    _inherits,
)
@dataclass
class RFrame:
    """Minimal R ``data.frame`` for model.part checks."""

    columns: dict[str, list]
    row_names: list[str | int] | None = None
    attrs: dict = field(default_factory=dict)

    @property
    def names(self) -> list[str]:
        return list(self.columns.keys())

    def __getitem__(self, key):
        if isinstance(key, str):
            return self.columns[key]
        if isinstance(key, list):
            return self._subset(key, drop=False)
        raise TypeError(key)

    def _subset(self, cols: list[str], drop: bool):
        if not cols:
            return RFrame({}, row_names=self.row_names, attrs=dict(self.attrs))
        if len(cols) == 1 and drop:
            name = cols[0]
            values = self.columns[name]
            rn = self.row_names or list(range(1, len(values) + 1))
            return RVector(values, names=[str(x) for x in rn])
        out_cols = {name: self.columns[name] for name in cols}
        return RFrame(out_cols, row_names=self.row_names, attrs=dict(self.attrs))


@dataclass
class RVector:
    values: list
    names: list[str]

    def __iter__(self):
        return iter(self.values)


def model_part(object, data=None, **kwargs):
    """Generic ``model.part``; dispatches on formula or Formula."""
    if isinstance(object, RFormula) and _inherits(object, "Formula"):
        return _model_part_formula(object, data, **kwargs)
    if isinstance(object, RFormula) and _inherits(object, "formula"):
        raise FormulaError("no method to invoke")
    if isinstance(object, str):
        from Formula.formula import as_r_formula

        return model_part(as_r_formula(object), data, **kwargs)
    raise FormulaError('object must inherit from "formula"')


def _model_part_formula(
    object: RFormula,
    data,
    lhs=0,
    rhs=0,
    drop=False,
    terms=False,
    dot=None,
    **_,
):
    if data is None:
        raise FormulaError("argument \"data\" is missing, with no default")

    if _all_zero(lhs) and _all_zero(rhs):
        raise FormulaError("Either some 'lhs' or 'rhs' has to be selected.")

    dot_val = _resolve_dot(dot, data)

    obj = object
    terms_attr = data.attrs.get("terms") if isinstance(data, RFrame) else None
    if (
        terms_attr is not None
        and isinstance(terms_attr, RTerms)
        and terms_attr.formula_with_dot is not None
        and _has_dot(object)
        and dot_val == terms_attr.dot
        and _deparse_formula(_simplify_to_formula(object, lhs=lhs, rhs=rhs))
        == _deparse_formula(
            _simplify_to_formula(terms_attr.formula_with_dot, lhs=lhs, rhs=rhs)
        )
    ):
        obj = terms_attr.formula_without_dot

    mt = _terms_formula(obj, lhs=lhs, rhs=rhs, dot=dot_val, data=data)
    ix = mt.variables
    if not ix:
        cols: list[str] = []
    else:
        cols = list(ix)
        missing = [name for name in cols if name not in data.names]
        if missing:
            quoted = ", ".join(f"'{name}'" for name in missing)
            raise FormulaError(
                "'data' does not seem to be an appropriate 'model.frame': "
                f"{quoted} not found"
            )

    if not cols:
        rval = data._subset([], drop=drop)
    else:
        rval = data._subset(cols, drop=drop)

    if terms:
        if isinstance(rval, RFrame):
            rval.attrs["terms"] = mt
    return rval


def _all_zero(which) -> bool:
    if which is None:
        return False
    vals = which if isinstance(which, (list, tuple)) else [which]
    if not vals:
        return True
    try:
        nums = [float(v) for v in vals]
    except (TypeError, ValueError):
        return False
    return all(v == 0.0 for v in nums)


def _resolve_dot(dot, data) -> str:
    if dot is None:
        terms_attr = data.attrs.get("terms") if isinstance(data, RFrame) else None
        if isinstance(terms_attr, RTerms) and terms_attr.dot is not None:
            return terms_attr.dot
        return "separate"
    choices = ("separate", "sequential", "previous")
    if dot not in choices:
        raise FormulaError(f"'{dot}' should be one of {', '.join(choices)}")
    return dot


@dataclass
class RTerms:
    variables: list[str]
    dot: str | None = None
    formula_with_dot: RFormula | None = None
    formula_without_dot: RFormula | None = None


def _terms_formula(
    x: RFormula,
    lhs=None,
    rhs=None,
    dot: str = "separate",
    data=None,
    **__,
) -> RTerms:
    form = _simplify_to_formula(x, lhs=lhs, rhs=rhs)
    if _has_dot(form):
        return _terms_formula_with_dot(x, form, lhs=lhs, rhs=rhs, dot=dot, data=data)
    variables = _terms_variables(form, data)
    return RTerms(variables=variables)


def _terms_variables(form: RFormula, data) -> list[str]:
    del data  # R uses data for variable reordering; column names match deparse.
    if len(form) == 2:
        rhs = form[2]
        return [_deparse_expr(part) for part in _split_plus(rhs)]
    lhs, rhs = form[2], form[3]
    if _is_zero(rhs):
        return [_deparse_expr(lhs)]
    out: list[str] = []
    if not _is_null(lhs):
        out.append(_deparse_expr(lhs))
    for part in _split_plus(rhs):
        name = _deparse_expr(part)
        if name not in out:
            out.append(name)
    return out


def _terms_formula_with_dot(x, form, lhs, rhs, dot, data):
    del x, form, lhs, rhs, dot, data
    raise FormulaError("Formula dot expansion is not implemented")


def _has_dot(form: RFormula) -> bool:
    return _expression_has_dot(form)


def _expression_has_dot(node) -> bool:
    if isinstance(node, Sym) and node.name == ".":
        return True
    if isinstance(node, Bin):
        return _expression_has_dot(node.left) or _expression_has_dot(node.right)
    if isinstance(node, Call):
        return any(_expression_has_dot(arg) for arg in node.args)
    if isinstance(node, RFormula):
        return _expression_has_dot(node.elements)
    if isinstance(node, tuple):
        return any(_expression_has_dot(x) for x in node)
    return False


def _simplify_to_formula(Formula_obj: RFormula, lhs=None, rhs=None) -> RFormula:
    form = _formula_part(Formula_obj, lhs=lhs, rhs=rhs, collapse=(False, False), drop=True)
    Form = Formula(form)
    ext_lhs = _is_lhs_extended(Form)
    if ext_lhs or _is_rhs_extended(Form):
        if ext_lhs:
            rhs_parts = Form.rhs or ()
            if len(rhs_parts) == 1 and _is_zero(rhs_parts[0]):
                form = _paste_formula([], list(Form.lhs or ()), lsep="|", rsep="+")
            else:
                combined = list(Form.lhs or ()) + list(Form.rhs or ())
                form = _paste_formula([], combined, lsep="|", rsep="+")
        else:
            form = _paste_formula(
                list(Form.lhs or ()),
                list(Form.rhs or ()),
                lsep="|",
                rsep="+",
            )
    return form


def _is_lhs_extended(Form: RFormula) -> bool:
    lhs = Form.lhs
    if lhs is None:
        return False
    if len(lhs) > 1:
        return True
    if len(lhs) < 1:
        return False
    pasted = _paste_formula([], list(lhs), lsep="|", rsep="+")
    labels = _term_labels(pasted)
    return len(labels) > 1


def _is_rhs_extended(Form: RFormula) -> bool:
    rhs = Form.rhs
    return rhs is not None and len(rhs) > 1


def _term_labels(form: RFormula) -> list[str]:
    if len(form) == 2:
        return [_deparse_expr(part) for part in _split_plus(form[2])]
    lhs, rhs = form[2], form[3]
    if _is_zero(rhs):
        return [_deparse_expr(lhs)]
    out = [_deparse_expr(lhs)]
    out.extend(_deparse_expr(part) for part in _split_plus(rhs))
    return out


def _formula_part(
    x: RFormula,
    lhs=None,
    rhs=None,
    collapse=(False, False),
    drop=True,
) -> RFormula:
    lhs_parts = list(x.lhs or ())
    rhs_parts = list(x.rhs or ())
    lpart = list(range(1, len(lhs_parts) + 1))
    rpart = list(range(1, len(rhs_parts) + 1))

    lhs_idx = _r_index(lhs, lpart)
    rhs_idx = _r_index(rhs, rpart)

    collapse = (bool(collapse[0]), bool(collapse[1]))
    lhs_nodes = [lhs_parts[i - 1] for i in lhs_idx]
    rhs_nodes = [rhs_parts[i - 1] for i in rhs_idx]

    lsep = "+" if collapse[0] else "|"
    rsep = "+" if collapse[1] else "|"
    rval = _paste_formula(lhs_nodes, rhs_nodes, lsep=lsep, rsep=rsep)
    if not drop:
        return Formula(rval)
    return rval


def _r_index(which, parts: list[int]) -> list[int]:
    if which is None:
        return parts
    keys = which if isinstance(which, (list, tuple)) else [which]
    out: list[int] = []
    for key in keys:
        key = int(key)
        if key == 0:
            continue
        if 1 <= key <= len(parts):
            out.append(parts[key - 1])
    return out


def _paste_formula(lhs, rhs, lsep="|", rsep="|"):
    lhs = list(lhs or [])
    rhs = list(rhs or [])
    lseps = [lsep] * max(0, len(lhs) - 1)
    rseps = [rsep] * max(0, len(rhs) - 1)
    lval = None
    if lhs:
        lval = lhs[0]
        for i in range(1, len(lhs)):
            lval = _c_formula(lval, lhs[i], sep=lseps[i - 1])
    rval = Num(0) if not rhs else rhs[0]
    if len(rhs) > 1:
        for i in range(1, len(rhs)):
            rval = _c_formula(rval, rhs[i], sep=rseps[i - 1])
    return _c_formula(lval, rval, sep="~")


def _c_formula(f1, f2, sep="~") -> RFormula:
    if sep not in ("~", "+", "-", "|", "&"):
        raise ValueError("invalid separator")
    if sep == "~":
        if f1 is None:
            return RFormula(("~", f2), _unset=True)
        return RFormula(("~", f1, f2), _unset=True)
    inner = Bin(sep, f1, f2)
    return RFormula(("~", inner), _unset=True)


def _split_plus(node):
    parts: list = []
    cur = node
    while isinstance(cur, Bin) and cur.op == "+":
        parts.insert(0, cur.right)
        cur = cur.left
    parts.insert(0, cur)
    return parts


def _is_zero(node) -> bool:
    return isinstance(node, Num) and node.value == 0


def _is_null(node) -> bool:
    return node is None


def _deparse_formula(form: RFormula) -> str:
    if len(form) == 2:
        return f"~{_deparse_expr(form[2])}"
    return f"{_deparse_expr(form[2])} ~ {_deparse_expr(form[3])}"


def fingerprint_part(value) -> str:
    if isinstance(value, RVector):
        nums = ",".join(_format_scalar(v) for v in value.values)
        names = ",".join(value.names)
        return f"NUM|{nums}|NAMES|{names}"
    if isinstance(value, RFrame):
        bits = []
        for name in value.names:
            col = value.columns[name]
            cells = ",".join(_format_scalar(v) for v in col)
            bits.append(f"{name}={cells}")
        return "DF|" + ";".join(bits)
    if isinstance(value, FormulaError):
        return "ERR " + str(value)
    return "OTHER|" + repr(value)


def _format_scalar(val) -> str:
    if val is None:
        return "NA"
    if isinstance(val, float):
        return format(val, ".17g")
    if isinstance(val, str):
        return val
    return str(val)
