"""Person-years of follow-up (survival::pyears)."""

from __future__ import annotations

import ast
import math
import warnings
from dataclasses import dataclass
from typing import Any, Mapping, Sequence

import numpy as np

from survival.fromtimeline import Categorical
from survival.surv import Surv, SurvObject, is_Surv


class Tcut:
    """Time-dependent cutpoints (survival::tcut), private to pyears until tcut is exported."""

    __slots__ = ("values", "cutpoints", "labels")

    def __init__(self, values, cutpoints, labels):
        self.values = np.asarray(values, dtype=float).reshape(-1)
        self.cutpoints = np.asarray(cutpoints, dtype=float)
        self.labels = list(labels)


def _match_arg(value, choices):
    if isinstance(value, (list, tuple)) and list(value) == list(choices):
        return choices[0]
    text = value[0] if isinstance(value, (list, tuple)) else value
    if text in choices:
        return text
    hits = [c for c in choices if c.startswith(str(text))]
    if len(hits) == 1:
        return hits[0]
    raise ValueError(f"'{value}' should be one of {choices}")


def _as_array(x):
    if isinstance(x, (list, tuple)):
        return np.asarray(x, dtype=float)
    if isinstance(x, np.ndarray):
        return np.asarray(x, dtype=float)
    return np.asarray([x], dtype=float)


def _cut(x, breaks, labels=None):
    x = np.asarray(x, dtype=float).reshape(-1)
    breaks = np.asarray(breaks, dtype=float)
    if breaks.size == 1:
        raise ValueError("Must specify at least one interval")
    if np.any(np.diff(breaks) < 0) or np.any(np.isnan(breaks)):
        raise ValueError("breaks must be given in ascending order and contain no NA's")
    nint = breaks.size - 1
    if labels is None:
        labels = [f"({breaks[i]},{breaks[i + 1]}]" for i in range(nint)]
    elif len(labels) != nint:
        raise ValueError("Number of labels must be 1 less than number of break points")
    codes = np.searchsorted(breaks, x, side="right")
    values = []
    for xi, code in zip(x, codes):
        if np.isnan(xi):
            values.append(None)
        else:
            code = int(np.clip(code, 1, nint))
            values.append(labels[code - 1])
    return Categorical(values, labels)


def _tcut(x, breaks, labels=None, scale=1.0):
    x = np.asarray(x, dtype=float).reshape(-1)
    breaks = np.asarray(breaks, dtype=float)
    if breaks.size == 1:
        nb = int(breaks[0])
        if nb < 1:
            raise ValueError("Must specify at least one interval")
        finite = x[np.isfinite(x)]
        if finite.size:
            r0, r1 = float(np.min(finite)), float(np.max(finite))
        else:
            r0, r1 = 1.0, 1.0
        if r1 == r0:
            r1 = r0 + 1.0
        d = r1 - r0
        breaks = np.linspace(r0 - 0.01 * d, r1 + 0.01 * d, nb + 1)
        if labels is None:
            labels = [f"Range {i + 1}" for i in range(nb)]
        elif len(labels) != nb:
            raise ValueError("Number of labels must equal number of intervals")
    else:
        if np.any(np.diff(breaks) < 0) or np.any(np.isnan(breaks)):
            raise ValueError("breaks must be given in ascending order and contain no NA's")
        if labels is None:
            labels = [f"{breaks[i]}+ thru {breaks[i + 1]}" for i in range(breaks.size - 1)]
        elif len(labels) != breaks.size - 1:
            raise ValueError("Number of labels must be 1 less than number of break points")
    return Tcut(x * scale, breaks * scale, labels)


def _factor(x, levels=None):
    if isinstance(x, Categorical):
        return x
    if isinstance(x, Tcut):
        raise TypeError("cannot coerce tcut to factor")
    values = list(x) if not isinstance(x, np.ndarray) else x.tolist()
    if levels is None:
        seen = []
        for item in values:
            if item is None or (isinstance(item, float) and math.isnan(item)):
                continue
            if item not in seen:
                seen.append(item)
        levels = seen
    out = []
    for item in values:
        if item is None or (isinstance(item, float) and math.isnan(item)):
            out.append(None)
        elif item in levels:
            out.append(item)
        else:
            out.append(None)
    return Categorical(out, list(levels))


def _c(*args):
    if len(args) == 1 and isinstance(args[0], (list, tuple, np.ndarray)):
        return _as_array(args[0])
    return _as_array(args)


class _FormulaEval(ast.NodeVisitor):
    def __init__(self, env):
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
            if func == "cut":
                return _cut(*args, **kwargs)
            if func == "tcut":
                return _tcut(*args, **kwargs)
            if func == "factor":
                return _factor(*args, **kwargs)
            if func == "c":
                return _c(*args)
            if func == "I":
                return args[0]
            raise ValueError(f"unsupported function {func} in formula")
        raise ValueError("unsupported expression in formula")


def _eval_expr(text: str, env: dict):
    tree = ast.parse(text.strip(), mode="eval")
    return _FormulaEval(env).visit(tree)


def _split_terms(rhs: str) -> list[str]:
    parts = []
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
    return [p for p in parts if p]


def _has_interaction(rhs: str) -> bool:
    depth = 0
    for i, ch in enumerate(rhs):
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        elif depth == 0 and ch in (":", "*"):
            return True
    return False


@dataclass
class _PyearsFrame:
    response: Any
    weights: np.ndarray
    terms: list[str]
    columns: dict[str, Any]
    n: int


def _build_frame(
    formula: str,
    data: Mapping[str, Any],
    weights=None,
    subset=None,
    na_action=None,
):
    if formula is None or "~" not in formula:
        raise ValueError("A formula argument is required")
    lhs, rhs = formula.split("~", 1)
    lhs = lhs.strip()
    rhs = rhs.strip()
    if _has_interaction(rhs):
        raise ValueError("Pyears cannot have interaction terms")
    env = dict(data)
    n = len(next(iter(data.values())))
    if subset is not None:
        if callable(subset):
            keep = np.asarray(subset(dict(data)), dtype=bool)
        else:
            keep = np.asarray(subset, dtype=bool)
    else:
        keep = np.ones(n, dtype=bool)
    sub_env = {}
    for key, col in data.items():
        if isinstance(col, Categorical):
            sub_env[key] = Categorical([col.values[i] for i in range(n) if keep[i]], col.levels)
        elif isinstance(col, np.ndarray):
            sub_env[key] = col[keep]
        elif isinstance(col, Tcut):
            sub_env[key] = Tcut(col.values[keep], col.cutpoints, col.labels)
        else:
            sub_env[key] = [col[i] for i in range(n) if keep[i]]
    n = len(next(iter(sub_env.values())))
    env = sub_env
    response = _eval_expr(lhs, env)
    term_names = _split_terms(rhs)
    columns = {}
    for name in term_names:
        columns[name] = _eval_expr(name, env)
    wt = weights
    if wt is not None:
        if isinstance(wt, str):
            wt = env[wt]
        wt = np.asarray(wt, dtype=float).reshape(-1)
        if wt.size != n:
            raise ValueError("weights length mismatch")
    else:
        wt = np.ones(n, dtype=float)
    if na_action is not None:
        raise NotImplementedError("na.action is not supported yet")
    return _PyearsFrame(response=response, weights=wt, terms=term_names, columns=columns, n=n)


def _response_matrix(Y):
    if is_Surv(Y):
        mat = Y.matrix()
        stype = Y.type
        return mat, stype, True
    Y = np.asarray(Y, dtype=float)
    if Y.ndim == 1:
        Y = Y.reshape(-1, 1)
    if np.any(Y < 0):
        raise ValueError("Negative follow up time")
    if Y.shape[1] > 2:
        raise ValueError("Y has too many columns")
    return Y, "raw", False


def _pystep(nc, data, fac, dims, cuts, step, edge):
    index = 0
    index2 = 0
    wt = 1.0
    shortfall = 0.0
    maxtime = step
    kk = 1
    for i in range(nc):
        if fac[i] == 1:
            index += int(data[i] - 1) * kk
        else:
            if fac[i] > 1:
                dtemp = 1 + (fac[i] - 1) * dims[i]
            else:
                dtemp = dims[i]
            j = 0
            while j < dtemp and data[i] < cuts[i][j]:
                j += 1
            if j == 0:
                temp = cuts[i][j] - data[i]
                if edge == 0 and temp > shortfall:
                    shortfall = min(step, temp)
                if temp < maxtime:
                    maxtime = temp
            elif j == dtemp:
                if edge == 0:
                    temp = cuts[i][j] - data[i]
                    if temp <= 0:
                        shortfall = step
                    elif temp < maxtime:
                        maxtime = temp
                if fac[i] > 1:
                    j = dims[i] - 1
                else:
                    j -= 1
            else:
                temp = cuts[i][j] - data[i]
                if temp < maxtime:
                    maxtime = temp
                j -= 1
                if fac[i] > 1:
                    wt = 1.0 - (j % fac[i]) / float(fac[i])
                    j //= fac[i]
                    index2 = kk
            index += j * kk
        kk *= dims[i]
    index2 += index
    if shortfall == 0:
        return maxtime, index, index2, wt
    return shortfall, -1, index2, wt


def _compute_eps(n, start, stop, dostart):
    eps = 0.0
    found = False
    for i in range(n):
        timeleft = stop[i] - start[i] if dostart else stop[i]
        if timeleft > 0:
            eps = timeleft
            found = True
            break
    if not found:
        return 0.0
    for j in range(i, n):
        timeleft = stop[j] - start[j] if dostart else stop[j]
        if 0 < timeleft < eps:
            eps = timeleft
    return eps * 1e-8


def _pyears2(n, ny, doevent, y, wt, odim, ofac, odims, ocut_flat, odata, osize):
    pyears = np.zeros(osize, dtype=float)
    pn = np.zeros(osize, dtype=float)
    pcount = np.zeros(osize if doevent else 1, dtype=float)
    offtable = 0.0
    start = y[:, 0] if ny >= 2 else None
    if ny == 3 or (ny == 2 and not doevent):
        stop = y[:, 1]
        dostart = True
        event = y[:, 2] if ny == 3 else y[:, 1]
    else:
        stop = y[:, 0]
        dostart = False
        event = y[:, 1] if ny >= 2 else np.zeros(n)
    ocut = []
    pos = 0
    for i in range(odim):
        ocut.append(np.asarray(ocut_flat[pos : pos + odims[i] + 1], dtype=float))
        if ofac[i] == 0:
            pos += odims[i] + 1
    eps = _compute_eps(n, start if dostart else stop, stop, dostart)
    data = np.zeros(odim, dtype=float)
    for i in range(n):
        for j in range(odim):
            if ofac[j] == 1 or not dostart:
                data[j] = odata[j, i]
            else:
                data[j] = odata[j, i] + start[i]
        timeleft = stop[i] - start[i] if dostart else stop[i]
        index = -1
        if timeleft <= eps and doevent:
            _, index, _, _ = _pystep(odim, data, ofac, odims, ocut, 1.0, 0)
        while timeleft > eps:
            thiscell, index, _, _ = _pystep(odim, data, ofac, odims, ocut, timeleft, 0)
            if index >= 0:
                pyears[index] += thiscell * wt[i]
                pn[index] += 1
            else:
                offtable += thiscell * wt[i]
            for j in range(odim):
                if ofac[j] == 0:
                    data[j] += thiscell
            timeleft -= thiscell
        if index >= 0 and doevent:
            pcount[index if doevent else 0] += event[i] * wt[i]
    return pyears, pn, pcount, offtable


def _pyears1(
    n,
    ny,
    doevent,
    y,
    weight,
    edim,
    efac,
    edims,
    ecut_flat,
    expect_arr,
    edata,
    odim,
    ofac,
    odims,
    ocut_flat,
    method,
    odata,
    osize,
):
    pyears = np.zeros(osize, dtype=float)
    pn = np.zeros(osize, dtype=float)
    pcount = np.zeros(osize if doevent else 1, dtype=float)
    pexpect = np.zeros(osize, dtype=float)
    offtable = 0.0
    if ny == 3 or (ny == 2 and not doevent):
        start = y[:, 0]
        stop = y[:, 1]
        dostart = True
        event = y[:, 2] if ny == 3 else y[:, 1]
    else:
        start = None
        stop = y[:, 0]
        dostart = False
        event = y[:, 1] if y.shape[1] >= 2 else np.zeros(n)
    ecut = []
    pos = 0
    for i in range(edim):
        if efac[i] == 0:
            ecut.append(np.asarray(ecut_flat[pos : pos + edims[i]], dtype=float))
            pos += edims[i]
        elif efac[i] > 1:
            ecut.append(np.asarray(ecut_flat[pos : pos + 1 + (efac[i] - 1) * edims[i]], dtype=float))
            pos += 1 + (efac[i] - 1) * edims[i]
        else:
            ecut.append(np.asarray([], dtype=float))
    ocut = []
    pos = 0
    for i in range(odim):
        if ofac[i] == 0:
            ocut.append(np.asarray(ocut_flat[pos : pos + odims[i] + 1], dtype=float))
            pos += odims[i] + 1
        else:
            ocut.append(np.asarray([], dtype=float))
    eps = _compute_eps(n, start if dostart else stop, stop, dostart)
    data = np.zeros(odim, dtype=float)
    data2 = np.zeros(edim, dtype=float)
    expect = np.asarray(expect_arr, dtype=float).reshape(-1)
    for i in range(n):
        for j in range(odim):
            if ofac[j] == 1 or not dostart:
                data[j] = odata[j, i]
            else:
                data[j] = odata[j, i] + (start[i] if start is not None else 0.0)
        for j in range(edim):
            if efac[j] == 1 or not dostart:
                data2[j] = edata[j, i]
            else:
                data2[j] = edata[j, i] + (start[i] if start is not None else 0.0)
        timeleft = stop[i] - start[i] if dostart else stop[i]
        cumhaz = 0.0
        index = -1
        if timeleft <= eps and doevent:
            _, index, _, _ = _pystep(odim, data, ofac, odims, ocut, 1.0, 0)
        while timeleft > eps:
            thiscell, index, indx2, lwt = _pystep(odim, data, ofac, odims, ocut, timeleft, 0)
            if index >= 0:
                pyears[index] += thiscell * weight[i]
                pn[index] += 1
                etime = thiscell
                hazard = 0.0
                temp = 0.0
                while etime > 0:
                    et2, indx, indx2b, lwt2 = _pystep(edim, data2, efac, edims, ecut, etime, 1)
                    if lwt2 < 1:
                        lam = lwt2 * expect[indx] + (1 - lwt2) * expect[indx2b]
                    else:
                        lam = expect[indx]
                    if method == 0:
                        temp += math.exp(-hazard) * (1 - math.exp(-lam * et2)) / lam
                    hazard += lam * et2
                    for j in range(edim):
                        if efac[j] != 1:
                            data2[j] += et2
                    etime -= et2
                if method == 1:
                    pexpect[index] += hazard * weight[i]
                else:
                    pexpect[index] += math.exp(-cumhaz) * temp * weight[i]
                cumhaz += hazard
            else:
                offtable += thiscell * weight[i]
                for j in range(edim):
                    if efac[j] != 1:
                        data2[j] += thiscell
            for j in range(odim):
                if ofac[j] == 0:
                    data[j] += thiscell
            timeleft -= thiscell
        if index >= 0 and doevent:
            pcount[index] += event[i] * weight[i]
    return pyears, pn, pcount, pexpect, offtable


def _is_ratetable(x):
    if not isinstance(x, dict) or x.get("class") != "ratetable":
        return False
    att = x
    if "dim" not in att or "cutpoints" not in att:
        return False
    return True


def _ratetable_date(x):
    if isinstance(x, np.ndarray):
        return np.asarray(x, dtype=float)
    return x


def _match_ratetable(rdata, ratetable):
    if not _is_ratetable(ratetable):
        raise ValueError("Invalid rate table")
    dimid = list(ratetable.get("dimnames_names") or ratetable.get("dimid") or [])
    rtype = ratetable.get("type")
    if rtype is None:
        rfac = ratetable["factor"]
        rtype = [1 if f == 1 else (4 if f > 1 else 2) for f in rfac]
    names = list(rdata.keys())
    ord_idx = [names.index(d) if d in names else -1 for d in dimid]
    if any(i < 0 for i in ord_idx):
        missing = [dimid[i] for i, v in enumerate(ord_idx) if v < 0]
        raise ValueError(f"Argument '{missing[0]}' needed by the ratetable was not found in the data")
    cols = []
    for i in ord_idx:
        col = rdata[names[i]]
        if isinstance(col, Categorical):
            lev = col.levels
            dnames = ratetable["dimnames"][i]
            temp = []
            for level in lev:
                hits = [j + 1 for j, d in enumerate(dnames) if d.lower().startswith(str(level).lower())]
                if len(hits) != 1:
                    raise ValueError(f"Levels do not match for ratetable() variable {dimid[i]}")
                temp.append(hits[0])
            codes = []
            for v in col.values:
                if v is None:
                    codes.append(np.nan)
                else:
                    codes.append(temp[lev.index(v)])
            cols.append(np.asarray(codes, dtype=float))
        else:
            cols.append(np.asarray(col, dtype=float))
    R = np.column_stack(cols)
    cutpoints = [ _ratetable_date(cp) for cp in ratetable["cutpoints"] ]
    summ = ratetable.get("summary")
    out = {"R": R, "cutpoints": cutpoints}
    if summ is not None:
        out["summ"] = summ(R)
    return out


def _coxph_ratetable_matrix(ratetable, rdata):
    raise ValueError("Invalid rate table")


def pyears(
    formula,
    data=None,
    weights=None,
    subset=None,
    na_action=None,
    rmap=None,
    ratetable=None,
    scale=365.25,
    expect=("event", "pyears"),
    model=False,
    x=False,
    y=False,
    data_frame=False,
):
    """Compute person-years stratified by grouping variables."""
    expect = _match_arg(expect, ("event", "pyears"))
    mf = _build_frame(formula, data, weights=weights, subset=subset, na_action=na_action)
    Y, stype, is_surv = _response_matrix(mf.response)
    if is_surv:
        if stype == "right":
            if np.any(Y[:, 0] < 0):
                raise ValueError("Negative survival time")
            nzero = int(np.sum((Y[:, 0] == 0) & (Y[:, 1] == 1)))
            if nzero > 0:
                warnings.warn(
                    f"{nzero} observations with an event and 0 follow-up time, "
                    "any rate calculations are statistically questionable"
                )
        elif stype != "counting":
            raise ValueError("Only right-censored and counting process survival types are supported")
    n = mf.n
    if n == 0:
        raise ValueError("Data set has 0 observations")
    weights_arr = mf.weights
    has_ratetable = ratetable is not None or rmap is not None
    rtemp = None
    if has_ratetable:
        if ratetable is None:
            raise ValueError("No rate table specified")
        if rmap is not None:
            rdata = {k: mf.columns.get(k, data[k]) for k in rmap}
            for key, expr in rmap.items():
                if key == "list":
                    continue
                env = dict(data)
                env.update(mf.columns)
                rdata[key] = expr if not isinstance(expr, str) else _eval_expr(expr, env)
        else:
            rdata = {}
        if _is_ratetable(ratetable):
            israte = True
            rtemp = _match_ratetable(rdata, ratetable)
            R = rtemp["R"]
        elif isinstance(ratetable, dict) and "coxph" in ratetable.get("class_", ()):
            israte = False
            R = _coxph_ratetable_matrix(ratetable, rdata)
        else:
            raise ValueError("Invalid rate table")
    ovars = mf.terms
    if len(ovars) == 0:
        X = np.ones(n, dtype=float)
        odim = 1
        ofac = np.array([1.0])
        odims = np.array([1.0])
        ocut = np.array([0.0])
        outdname = {}
    else:
        odim = len(ovars)
        ocut_list = []
        odims = []
        ofac = []
        X = np.zeros((n, odim), dtype=float)
        outdname = {}
        for i, var in enumerate(ovars):
            temp = mf.columns[var]
            if isinstance(temp, Tcut):
                X[:, i] = temp.values
                temp2 = temp.cutpoints
                odims.append(len(temp2) - 1)
                ocut_list.extend(temp2.tolist())
                ofac.append(0)
                outdname[var] = temp.labels
            else:
                if isinstance(temp, Categorical):
                    temp2 = temp
                else:
                    temp2 = _factor(temp)
                codes = []
                for v in temp2.values:
                    if v is None:
                        codes.append(np.nan)
                    else:
                        codes.append(temp2.levels.index(v) + 1)
                X[:, i] = codes
                temp3 = temp2.levels
                odims.append(len(temp3))
                ofac.append(1)
                outdname[var] = temp3
        ocut = np.asarray(ocut_list + [0.0], dtype=float)
        odims_arr = np.asarray(odims, dtype=float)
        ofac_arr = np.asarray(ofac, dtype=float)
    if len(ovars) == 0:
        odims_arr = odims
        ofac_arr = ofac
    osize = int(np.prod(odims_arr))
    odata = X.T if len(ovars) else X.reshape(1, n)
    if has_ratetable:
        atts = ratetable
        cuts = rtemp["cutpoints"]
        if atts.get("type") is None:
            rfac = np.asarray(atts["factor"], dtype=int)
            us_special = rfac > 1
        else:
            rfac = (np.asarray(atts["type"], dtype=int) == 1).astype(int)
            us_special = np.asarray(atts["type"], dtype=int) == 4
        if np.any(us_special):
            if int(np.sum(us_special)) > 1:
                raise ValueError("more than one type=4 in a rate table")
            dimid = atts.get("dimid") or atts.get("dimnames_names")
            cols = [list(dimid).index("age"), list(dimid).index("year")]
            bdate = R[:, cols[1]] - R[:, cols[0]]
            byear = np.floor(bdate / 365.25)  # approximate; R uses Date format
            offset = bdate - byear * 365.25
            R = np.array(R, copy=True)
            R[:, cols[1]] = R[:, cols[1]] - offset
        docount = is_surv
        method = 1 if expect == "event" else 0
        efac = np.asarray(atts.get("factor") if atts.get("type") is None else (np.asarray(atts["type"]) == 1).astype(int))
        edims = np.asarray(atts["dim"], dtype=int)
        ecut_flat = np.concatenate([np.asarray(c, dtype=float).reshape(-1) for c in cuts])
        py, pn, pcount, pexpect, offt = _pyears1(
            n,
            Y.shape[1],
            is_surv,
            Y,
            weights_arr,
            len(edims),
            efac,
            edims,
            ecut_flat,
            atts["data"],
            R.T,
            odim,
            ofac_arr,
            odims_arr.astype(int),
            ocut,
            method,
            odata,
            osize,
        )
        temp = {"pyears": py, "pn": pn, "pcount": pcount, "pexpect": pexpect, "offtable": offt}
    else:
        docount = int(Y.shape[1] > 1) if not is_surv else is_surv
        if is_surv:
            docount = True
        py, pn, pcount, offt = _pyears2(
            n,
            Y.shape[1],
            docount,
            Y,
            weights_arr,
            odim,
            ofac_arr.astype(int),
            odims_arr.astype(int),
            ocut,
            odata,
            osize,
        )
        temp = {"pyears": py, "pn": pn, "pcount": pcount, "offtable": offt}
    has_tcut = any(isinstance(mf.columns[v], Tcut) for v in ovars)
    odims_list = odims_arr.astype(int).tolist()
    if data_frame:
        raise NotImplementedError("data.frame=TRUE is not implemented")
    if int(np.prod(odims_arr)) == 1:
        out = {
            "pyears": float(temp["pyears"][0]) / scale,
            "n": float(temp["pn"][0]),
            "offtable": float(temp["offtable"]) / scale,
            "tcut": has_tcut,
            "observations": n,
        }
        if has_ratetable:
            out["expected"] = temp["pexpect"][0]
            if expect == "pyears":
                out["expected"] /= scale
            if rtemp and rtemp.get("summ") is not None:
                out["summary"] = rtemp["summ"]
        if docount:
            out["event"] = float(temp["pcount"][0])
    else:
        out = {
            "pyears": (temp["pyears"] / scale).reshape(odims_list, order="F"),
            "n": temp["pn"].reshape(odims_list, order="F"),
            "offtable": float(temp["offtable"]) / scale,
            "tcut": has_tcut,
            "observations": n,
        }
        if has_ratetable:
            exp_arr = temp["pexpect"].reshape(odims_list, order="F")
            if expect == "pyears":
                exp_arr = exp_arr / scale
            out["expected"] = exp_arr
            if rtemp and rtemp.get("summ") is not None:
                out["summary"] = rtemp["summ"]
        if docount:
            out["event"] = temp["pcount"].reshape(odims_list, order="F")
    if model:
        out["model"] = mf
    else:
        if x:
            out["x"] = X
        if y:
            out["y"] = Y
    out["class_"] = ("pyears",)
    return out
