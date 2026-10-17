"""O'Brien time-dependent covariate data (survival::survobrien)."""

from __future__ import annotations

import ast
import math
import re
from dataclasses import dataclass, field
from typing import Any, Callable, Mapping

import numpy as np

from survival.fromtimeline import Categorical
from survival.strata import StrataFactor, strata as strata_fn
from survival.surv import Surv, SurvObject, is_Surv
from survival.surv_split import _apply_subset, _as_table, _column_len
from survival.untangle_specials import untangle_specials


class AsIs:
    """R base::I / AsIs wrapper."""

    __slots__ = ("values",)

    def __init__(self, values):
        self.values = values


@dataclass
class SurvobrienFrame:
    names: list[str]
    columns: list[Any]
    specials: dict[str, Any] = field(default_factory=dict)

    def __len__(self) -> int:
        return len(self.columns[0]) if self.columns else 0


def _split_terms(rhs: str) -> list[str]:
    parts: list[str] = []
    depth = 0
    start = 0
    for i, ch in enumerate(rhs):
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        elif ch == "+" and depth == 0:
            parts.append(rhs[start:i].strip())
            start = i + 1
    parts.append(rhs[start:].strip())
    return [part for part in parts if part]


def _factor(values, levels=None):
    if levels is not None:
        out: list[Any] = []
        for item in values:
            if item is None or (isinstance(item, float) and math.isnan(item)):
                out.append(None)
            else:
                out.append(levels[int(item) - 1] if isinstance(item, (int, np.integer)) else item)
        return Categorical(out, list(levels))
    seen: dict[str, None] = {}
    level_list: list[str] = []
    codes: list[Any] = []
    for item in values:
        if item is None or (isinstance(item, float) and math.isnan(item)):
            codes.append(None)
            continue
        text = str(item)
        if text not in seen:
            seen[text] = None
            level_list.append(text)
        codes.append(text)
    return Categorical(codes, level_list)


class _FormulaEval(ast.NodeVisitor):
    def __init__(self, env: dict[str, Any]):
        self.env = env

    def visit(self, node):
        if isinstance(node, ast.Expression):
            return self.visit(node.body)
        if isinstance(node, ast.Constant):
            if isinstance(node.value, str):
                return node.value
            return float(node.value)
        if isinstance(node, ast.Name):
            if node.id not in self.env:
                raise NameError(node.id)
            return self.env[node.id]
        if isinstance(node, ast.Attribute):
            if isinstance(node.value, ast.Name):
                key = f"{node.value.id}.{node.attr}"
                if key in self.env:
                    return self.env[key]
            value = self.visit(node.value)
            if isinstance(value, dict):
                return value[node.attr]
            return getattr(value, node.attr)
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
            return -self.visit(node.operand)
        if isinstance(node, ast.BinOp):
            left = self.visit(node.left)
            right = self.visit(node.right)
            if isinstance(node.op, ast.Add):
                return np.asarray(left, dtype=float) + np.asarray(right, dtype=float)
            if isinstance(node.op, ast.Sub):
                return np.asarray(left, dtype=float) - np.asarray(right, dtype=float)
            if isinstance(node.op, ast.Mult):
                return np.asarray(left, dtype=float) * np.asarray(right, dtype=float)
            if isinstance(node.op, ast.Div):
                return np.asarray(left, dtype=float) / np.asarray(right, dtype=float)
        if isinstance(node, ast.Call):
            func = node.func.id if isinstance(node.func, ast.Name) else None
            if func is None:
                raise ValueError("invalid call in formula")
            args = [self.visit(a) for a in node.args]
            kwargs = {kw.arg: self.visit(kw.value) for kw in node.keywords}
            if func == "Surv":
                if len(args) == 2 and not kwargs:
                    return Surv(args[0], event=args[1])
                if len(args) == 3 and not kwargs:
                    return Surv(args[0], args[1], event=args[2])
                return Surv(*args, **kwargs)
            if func == "factor":
                return _factor(*args, **kwargs)
            if func == "I":
                return AsIs(args[0])
            raise ValueError(f"unsupported function {func} in formula")
        raise ValueError("unsupported expression in formula")


def _eval_expr(text: str, env: dict[str, Any]) -> Any:
    tree = ast.parse(text.strip(), mode="eval")
    return _FormulaEval(env).visit(tree)


def _parse_call_args(term: str, name: str) -> list[str]:
    m = re.match(rf"{name}\s*\((.*)\)\s*$", term.strip(), flags=re.IGNORECASE)
    if not m:
        return []
    inner = m.group(1).strip()
    if not inner:
        return []
    depth = 0
    args: list[str] = []
    start = 0
    for i, ch in enumerate(inner):
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        elif ch == "," and depth == 0:
            args.append(inner[start:i].strip())
            start = i + 1
    args.append(inner[start:].strip())
    return [arg for arg in args if arg]


def _all_vars(text: str) -> list[str]:
    tree = ast.parse(text, mode="eval")
    names: list[str] = []

    def walk(node):
        if isinstance(node, ast.Call):
            for arg in node.args:
                walk(arg)
            for kw in node.keywords:
                walk(kw.value)
            return
        if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):
            names.append(f"{node.value.id}.{node.attr}")
            return
        if isinstance(node, ast.Name):
            names.append(node.id)
            return
        for child in ast.iter_child_nodes(node):
            walk(child)

    walk(tree)
    return names


def _is_factor_col(col: Any) -> bool:
    return isinstance(col, (Categorical, StrataFactor))


def _is_asis(col: Any) -> bool:
    return isinstance(col, AsIs)


def _column_values(col: Any) -> list[Any]:
    if isinstance(col, AsIs):
        col = col.values
    if isinstance(col, Categorical):
        return list(col.values)
    if isinstance(col, StrataFactor):
        return list(col.codes)
    if isinstance(col, np.ndarray):
        return col.tolist()
    if isinstance(col, (list, tuple)):
        return list(col)
    return [col]


def _row_any_na(cols: list[Any]) -> np.ndarray:
    n = _column_len(cols[0])
    miss = np.zeros(n, dtype=bool)
    for col in cols:
        if isinstance(col, (SurvObject,)):
            mat = col.matrix()
            miss |= np.any(np.isnan(mat), axis=1)
        elif isinstance(col, AsIs):
            miss |= _row_any_na([col.values])
        elif isinstance(col, Categorical):
            miss |= np.array([v is None for v in col.values])
        elif isinstance(col, StrataFactor):
            miss |= np.array([c is None for c in col.codes])
        elif isinstance(col, np.ndarray):
            if col.dtype.kind == "f":
                miss |= np.isnan(col)
        else:
            miss |= np.array([v is None or (isinstance(v, float) and math.isnan(v)) for v in col])
    return miss


def _subset_cols(names: list[str], cols: list[Any], keep: np.ndarray) -> tuple[list[str], list[Any]]:
    out_cols: list[Any] = []
    for col in cols:
        if isinstance(col, SurvObject):
            out_cols.append(SurvObject(col.matrix()[keep], col.type, col.states, col.clabel))
        elif isinstance(col, AsIs):
            inner = col.values
            if isinstance(inner, np.ndarray):
                out_cols.append(AsIs(inner[keep]))
            else:
                out_cols.append(AsIs([inner[i] for i, k in enumerate(keep) if k]))
        elif isinstance(col, Categorical):
            out_cols.append(Categorical([col.values[i] for i, k in enumerate(keep) if k], col.levels))
        elif isinstance(col, StrataFactor):
            out_cols.append(
                StrataFactor([col.codes[i] for i, k in enumerate(keep) if k], list(col.levels))
            )
        elif isinstance(col, np.ndarray):
            out_cols.append(np.array(col[keep], copy=True))
        else:
            out_cols.append([col[i] for i, k in enumerate(keep) if k])
    return names, out_cols


def _default_na_action(names: list[str], cols: list[Any]) -> tuple[list[str], list[Any]]:
    keep = ~_row_any_na(cols)
    if np.all(keep):
        return names, cols
    return _subset_cols(names, cols, keep)


def _apply_na_action(names: list[str], cols: list[Any], na_action: Any) -> tuple[list[str], list[Any]]:
    if na_action is None or na_action == "na.omit" or na_action is True:
        return _default_na_action(names, cols)
    if na_action == "na.pass":
        return names, cols
    if callable(na_action):
        frame = SurvobrienFrame(names, cols)
        result = na_action(frame)
        if isinstance(result, SurvobrienFrame):
            return result.names, result.columns
        raise ValueError("na.action must return a model frame")
    raise ValueError("unsupported na.action")


def _build_terms(mf_names: list[str], term_labels: list[str], specials: dict[str, list[int]]) -> dict[str, Any]:
    covars = mf_names[1:]
    nrows = len(covars) + 1
    matrix = [[0] * len(term_labels) for _ in range(nrows)]
    for j, label in enumerate(term_labels):
        if label in covars:
            row = covars.index(label) + 1
            matrix[row][j] = 1
        else:
            for i, name in enumerate(covars):
                if name == label or label in name:
                    matrix[i + 1][j] = 1
                    break
    return {
        "response": 1,
        "order": [1] * len(term_labels),
        "term.labels": list(term_labels),
        "factors": {"matrix": matrix, "rownames": [mf_names[0], *covars], "colnames": term_labels},
        "specials": specials,
    }


def _drop_term(terms: dict[str, Any], index: int) -> dict[str, Any]:
    """Drop one term column from an R-style terms object (1-based index)."""
    labels = list(terms["term.labels"])
    if index < 1 or index > len(labels):
        return terms
    drop = index - 1
    new_labels = [label for i, label in enumerate(labels) if i != drop]
    matrix = terms["factors"]["matrix"]
    new_matrix = [row[:drop] + row[drop + 1 :] for row in matrix]
    rownames = terms["factors"]["rownames"]
    new_rownames = [name for i, name in enumerate(rownames) if i != drop + 1]
    specials = {}
    for key, indices in terms.get("specials", {}).items():
        adjusted = [idx - 1 if idx > index else idx for idx in indices if idx != index]
        if adjusted:
            specials[key] = adjusted
    return {
        "response": terms["response"],
        "order": [1] * len(new_labels),
        "term.labels": new_labels,
        "factors": {"matrix": new_matrix, "rownames": new_rownames, "colnames": new_labels},
        "specials": specials,
    }


def _build_model_frame(
    formula: str,
    data: Mapping[str, Any],
    *,
    subset=None,
    na_action=None,
) -> tuple[list[str], list[Any], dict[str, Any]]:
    if formula is None or "~" not in str(formula):
        raise ValueError("A formula argument is required")
    formula_text = str(formula)
    lhs, rhs = formula_text.split("~", 1)
    lhs = lhs.strip()
    rhs = rhs.strip()
    table = _as_table(data)
    table, _ = _apply_subset(table, subset)
    env = dict(table)
    response = _eval_expr(lhs, env)
    term_exprs = _split_terms(rhs)
    term_labels: list[str] = []
    mf_names = [lhs]
    mf_cols: list[Any] = [response]
    specials: dict[str, list[int]] = {}
    for j, term in enumerate(term_exprs):
        term_labels.append(term)
        lower = term.lower()
        if lower.startswith("strata("):
            args = _parse_call_args(term, "strata")
            if len(args) == 1:
                col = strata_fn(env[args[0]])
            else:
                col = strata_fn(*[env[a] for a in args], shortlabel=True)
            mf_names.append(term)
            mf_cols.append(col)
            specials.setdefault("strata", []).append(len(mf_names))
            continue
        if lower.startswith("cluster("):
            col = _eval_expr(term, env)
            mf_names.append(term)
            mf_cols.append(col)
            specials.setdefault("cluster", []).append(len(mf_names))
            continue
        if lower.startswith("tt("):
            col = _eval_expr(term, env)
            mf_names.append(term)
            mf_cols.append(col)
            specials.setdefault("tt", []).append(len(mf_names))
            continue
        col = _eval_expr(term, env)
        mf_names.append(term)
        mf_cols.append(col)
    mf_names, mf_cols = _apply_na_action(mf_names, mf_cols, na_action)
    terms = _build_terms(mf_names, term_labels, specials)
    return mf_names, mf_cols, terms


def _rank(x: list[Any]) -> list[float]:
    """R rank(x, na.last='keep', ties.method='average')."""
    ranks = [math.nan] * len(x)
    valid = [
        (i, v)
        for i, v in enumerate(x)
        if v is not None and not (isinstance(v, float) and math.isnan(v))
    ]
    valid.sort(key=lambda item: item[1])
    i = 0
    while i < len(valid):
        j = i + 1
        while j < len(valid) and valid[j][1] == valid[i][1]:
            j += 1
        avg = (i + 1 + j) / 2.0
        for k in range(i, j):
            ranks[valid[k][0]] = avg
        i = j
    return ranks


def _default_transform(values: list[Any]) -> list[float]:
    r = _rank(values)
    denom = sum(1 for ri in r if not math.isnan(ri))
    out: list[float] = []
    for ri in r:
        if math.isnan(ri) or denom == 0:
            out.append(math.nan)
            continue
        temp = (ri - 0.5) / denom
        out.append(math.log(temp / (1.0 - temp)))
    return out


def _take(data: Mapping[str, Any], name: str, indices: list[int]) -> list[Any]:
    col = data[name]
    if isinstance(col, np.ndarray):
        idx = np.asarray(indices, dtype=int)
        return col[idx].tolist()
    return [col[i] for i in indices]


def survobrien(
    formula,
    data=None,
    subset=None,
    na_action=None,
    transform=None,
):
    """Build O'Brien time-dependent covariate rows for a Cox model."""
    if transform is None:
        transform = _default_transform
    else:
        probe = transform(list(range(1, 11)))
        if len(probe) != 10:
            raise ValueError("Transform function must be 1 to 1")
    if data is None:
        raise ValueError("data argument is required")
    mf_names, mf_cols, Terms = _build_model_frame(formula, data, subset=subset, na_action=na_action)
    if len(mf_cols) == 0 or _column_len(mf_cols[0]) == 0:
        raise ValueError("No (non-missing) observations")
    n = _column_len(mf_cols[0])
    y = mf_cols[0]
    if not is_Surv(y):
        raise ValueError("Response must be a survival object")
    if y.type not in ("right", "counting"):
        raise ValueError("Response must be right censored or (start, stop] data")

    name_to_col = {name: col for name, col in zip(mf_names, mf_cols)}
    cluster = untangle_specials(Terms, "cluster")
    cluster_vars = cluster.get("vars") or []
    if len(cluster_vars) > 1:
        raise ValueError("Can have only 1 cluster term")
    if cluster_vars:
        idvar = _column_values(name_to_col[cluster_vars[0]])
        Terms2 = _drop_term(Terms, cluster["tvar"])  # type: ignore[arg-type]
    else:
        idvar = list(range(1, n + 1))
        Terms2 = Terms

    strata_keep = None
    stemp: dict[str, Any] = {"vars": [], "terms": []}
    if Terms2.get("specials", {}).get("strata"):
        stemp = untangle_specials(Terms2, "strata", 1)
        if stemp.get("terms"):
            Terms2 = _drop_terms_by_index(Terms2, stemp["terms"])
        varnames = stemp.get("vars") or []
        if len(varnames) == 1:
            strata_keep = _column_values(name_to_col[varnames[0]])
        else:
            cols = [name_to_col[v] for v in varnames]
            strata_keep = _column_values(strata_fn(*cols, shortlabel=True))

    order = Terms2.get("order") or []
    if any(int(o) > 1 for o in order):
        raise ValueError("This function cannot deal with iteraction terms")

    myvars = list(Terms2.get("term.labels") or [])
    factors = [_is_factor_col(name_to_col[name]) for name in myvars]
    protected = [_is_asis(name_to_col[name]) for name in myvars]
    keepers = [f or p for f, p in zip(factors, protected)]
    if keepers and all(keepers):
        raise ValueError("No continuous variables to modify")

    ymat = y.matrix()
    ncol_y = ymat.shape[1]

    if ncol_y == 3:
        if strata_keep is None:
            event_rows = ymat[:, 2] == 1
            etime = sorted(set(ymat[event_rows, 1].tolist()))
            indx = [[i for i in range(n) if ymat[i, 0] < t and ymat[i, 1] >= t] for t in etime]
        else:
            temp = _unique_event_strata(ymat[:, 1], ymat[:, 2], strata_keep)
            etime = [p[0] for p in temp]
            indx = []
            for t, st in temp:
                rows = [
                    i
                    for i in range(n)
                    if ymat[i, 0] < t and ymat[i, 1] >= t and strata_keep[i] == st
                ]
                indx.append(rows)
    else:
        if strata_keep is None:
            event_rows = ymat[:, 1] == 1
            etime = sorted(set(ymat[event_rows, 0].tolist()))
            indx = [[i for i in range(n) if ymat[i, 0] >= t] for t in etime]
        else:
            temp = _unique_event_strata(ymat[:, 0], ymat[:, 1], strata_keep)
            etime = [p[0] for p in temp]
            indx = []
            for t, st in temp:
                rows = [i for i in range(n) if ymat[i, 1] >= t and strata_keep[i] == st]
                indx.append(rows)

    indx2 = [i for group in indx for i in group]
    nrisk = [len(group) for group in indx]

    col_names = ["time", "status"] if ncol_y == 2 else ["start", "stop", "status"]
    newdata: dict[str, list[Any]] = {}
    if ncol_y == 3:
        newdata[col_names[0]] = ymat[indx2, 0].tolist()
        newdata[col_names[1]] = ymat[indx2, 1].tolist()
        rep_etime = [t for t, k in zip(etime, nrisk) for _ in range(k)]
        newdata[col_names[2]] = [
            1 if newdata[col_names[1]][j] == rep_etime[j] and ymat[indx2[j], 2] == 1 else 0
            for j in range(len(indx2))
        ]
    else:
        newdata[col_names[0]] = ymat[indx2, 0].tolist()
        rep_etime = [t for t, k in zip(etime, nrisk) for _ in range(k)]
        newdata[col_names[1]] = [
            1 if newdata[col_names[0]][j] == rep_etime[j] and ymat[indx2[j], 1] == 1 else 0
            for j in range(len(indx2))
        ]

    knames: list[str] = []
    if any(keepers):
        for label, keep in zip(myvars, keepers):
            if keep:
                knames.extend(_all_vars(label))
    if strata_keep is not None and stemp.get("vars"):
        for var in stemp["vars"]:
            knames.extend(_all_vars(var))
    if knames:
        seen: set[str] = set()
        for name in knames:
            if name in seen:
                continue
            seen.add(name)
            newdata[name] = _take(data, name, indx2)

    if cluster_vars:
        clname = _all_vars(cluster_vars[0])
        for name in clname:
            newdata[name] = _take(data, name, indx2)
    else:
        newdata[".id."] = [idvar[i] for i in indx2]

    tvars = [name for name, keep in zip(myvars, keepers) if not keep]
    newx: dict[str, list[float]] = {}
    for tvar in tvars:
        z = _column_values(name_to_col[tvar])
        transformed: list[float] = []
        for group in indx:
            transformed.extend(transform([z[i] for i in group]))
        newx[tvar] = transformed

    strata_out: list[int] = []
    for s, k in enumerate(nrisk, start=1):
        strata_out.extend([s] * k)

    out_names = list(newdata.keys()) + list(newx.keys()) + [".strata."]
    out_cols = [newdata[k] for k in newdata] + [newx[k] for k in newx] + [strata_out]
    return SurvobrienFrame(out_names, out_cols)


def _unique_event_strata(
    times: np.ndarray,
    event: np.ndarray,
    strata: list[Any],
) -> list[tuple[float, Any]]:
    seen: set[tuple[float, Any]] = set()
    out: list[tuple[float, Any]] = []
    for i in range(len(times)):
        if event[i] != 1:
            continue
        key = (float(times[i]), strata[i])
        if key not in seen:
            seen.add(key)
            out.append(key)
    return out


def _drop_terms_by_index(terms: dict[str, Any], term_indices: list[int]) -> dict[str, Any]:
    out = terms
    for idx in sorted(term_indices, reverse=True):
        out = _drop_term(out, idx)
    return out
